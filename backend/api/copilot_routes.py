"""Copilot 工作台核心 API

提供：内容解析、一键生成全案、流式对话修改 三大核心接口。
"""

import json
import logging
import os
import re
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from api.auth_routes import get_admin_user, get_current_user
from models.persona import (
    Persona,
    GenerationHistory,
    ContentColumn,
    PromptTemplateCategory,
    PromptTemplate,
    PromptTemplateVersion,
    ReversalDramaHistory,
    DramaCastPreset,
    CharacterProfile,
    UserAccount,
    AdminOperationLog,
    GenerationActionEvent,
    AIModelConfig,
    GenerationRecord,
    GenerationTask,
    UnifiedAsset,
    ShortVideoProject,
    StoryboardRecord,
    VideoAipProject,
    VideoAipStepTask,
)
from services.ai_service import AIProviderError, AIService, safe_parse_ai_json
from services.content_parser import extract_from_url, extract_from_text, extract_from_file
from services.model_security import decrypt_secret, encrypt_secret
from video_engine import runtime as video_runtime
from prompts.ip_creation_prompts import (
    EXTRACT_CONTENT_SYSTEM, EXTRACT_CONTENT_USER,
    GENERATE_SCRIPT_SYSTEM, GENERATE_SCRIPT_USER,
    GENERATE_VIDEO_PROMPTS_SYSTEM, GENERATE_VIDEO_PROMPTS_USER,
    GENERATE_COVER_SYSTEM, GENERATE_COVER_USER,
    COPILOT_MODIFY_SYSTEM, COPILOT_MODIFY_USER,
    GENERATE_TOPICS_SYSTEM, GENERATE_TOPICS_USER,
    OPTIMIZE_HOOKS_SYSTEM, OPTIMIZE_HOOKS_USER,
    GENERATE_PUBLISH_PACKAGE_SYSTEM, GENERATE_PUBLISH_PACKAGE_USER,
    QUALITY_CHECK_SYSTEM, QUALITY_CHECK_USER,
)
from prompts.reversal_drama_prompts import (
    REVERSAL_DRAMA_USER,
    build_cast_block,
    build_drama_system_prompt,
    build_reversal_pattern_instruction,
)
from services.drama_script_service import get_drama_template, list_drama_templates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/copilot", tags=["Copilot工作台"])


# ─── Pydantic Schemas ─────────────────────────────────────────

class ParseRequest(BaseModel):
    url: Optional[str] = Field(None, description="文章链接")
    text: Optional[str] = Field(None, description="直接粘贴的文本")


class GenerateRequest(BaseModel):
    extracted_content: str = Field(..., description="提取后的核心内容")
    persona_id: int = Field(..., description="IP 人设 ID")
    target_platform: str = Field("veo", description="目标视频平台：veo/doubao/jimeng")
    extra_requirements: str = Field("", description="额外要求")
    cover_style: str = Field("竖版9:16，科技感", description="封面风格偏好")
    column_id: int = Field(0, description="栏目 ID")
    prompt_template_id: int = Field(0, description="口播提示词模板 ID")
    prompt_template_key: str = Field("", description="口播提示词模板 Key")
    prompt_template_category: str = Field("", description="口播提示词模板分类 Key")
    text_model_config_id: int = Field(0, description="文本模型配置 ID")
    cover_prompt_template_id: int = Field(0, description="封面提示词模板 ID")
    cover_model_config_id: int = Field(0, description="封面模型配置 ID")
    video_prompt_template_id: int = Field(0, description="视频提示词模板 ID")
    video_model_config_id: int = Field(0, description="视频模型配置 ID")
    cover_aspect_ratio: str = Field("9:16", description="封面比例")
    cover_title: str = Field("", description="封面主标题")
    video_aspect_ratio: str = Field("9:16", description="视频比例")
    video_duration: str = Field("15秒", description="视频时长")
    video_workflow_type: str = Field("standard", description="视频链路：standard/product_tvc/drama")


class ModifyRequest(BaseModel):
    content_type: str = Field(..., description="内容类型：script/video_prompts/cover_prompt/reversal_drama")
    current_content: str = Field(..., description="当前内容")
    user_instruction: str = Field(..., description="用户修改指令")
    persona_id: int = Field(0, description="IP 人设 ID")
    template_key: str = Field("", description="短剧模板 key（reversal_drama 改稿上下文）")
    cast_summary: str = Field("", description="角色组摘要（reversal_drama 改稿上下文）")


class GenerationActionEventCreate(BaseModel):
    history_id: int = Field(..., ge=1, description="生成历史 ID")
    event_type: str = Field(..., max_length=60, description="edited/saved/teleprompter_opened")
    content_type: str = Field("", max_length=60, description="script/video/cover/publish 等")
    metadata: dict = Field(default_factory=dict, description="事件附加信息")


class ColumnCreate(BaseModel):
    name: str = Field(..., max_length=100, description="栏目名称")
    persona_id: int = Field(0, description="绑定 IP 人设 ID")
    goal: str = Field("涨粉", description="栏目目标")
    target_platform: str = Field("视频号+抖音", description="推荐平台")
    duration: str = Field("30-60秒", description="推荐时长")
    structure: str = Field("", description="固定内容结构")
    opening_style: str = Field("痛点直击型", description="默认开头类型")
    cta: str = Field("", description="默认 CTA")
    default_template: str = Field("1080x1920/image_default.html", description="默认模板")
    default_voice: str = Field("zh-CN-YunjianNeural", description="默认音色")
    default_bgm: str = Field("", description="默认 BGM")
    notes: str = Field("", description="备注")
    sort_order: int = Field(0, description="排序")


class ColumnUpdate(ColumnCreate):
    is_active: bool = Field(True, description="是否启用")


class PromptTemplateCategoryCreate(BaseModel):
    key: str = Field(..., max_length=80, description="分类唯一 Key")
    template_type: str = Field("text_script", max_length=50, description="模板类型")
    name: str = Field(..., max_length=100, description="分类名称")
    description: str = Field("", description="分类说明")
    sort_order: int = Field(0, description="排序")


class PromptTemplateCategoryUpdate(PromptTemplateCategoryCreate):
    is_active: bool = Field(True, description="是否启用")


class PromptTemplateCreate(BaseModel):
    key: str = Field(..., max_length=100, description="模板唯一 Key")
    template_type: str = Field("text_script", max_length=50, description="模板类型")
    category_key: str = Field(..., max_length=80, description="所属分类 Key")
    platform: str = Field("", max_length=80, description="适用平台")
    scene: str = Field("", max_length=120, description="业务场景")
    step: str = Field("", max_length=120, description="生成步骤")
    name: str = Field(..., max_length=100, description="模板名称")
    description: str = Field("", description="模板说明")
    scenario: str = Field("", description="适用场景")
    output_structure: str = Field("", description="输出结构")
    writing_rules: list[str] = Field(default_factory=list, description="写作规则")
    prompt_body: str = Field("", description="后台控制的完整提示词正文")
    user_prompt_hint: str = Field("", description="前端展示的用户补充提示建议")
    default_params_json: str = Field("{}", description="默认生成参数 JSON")
    default_model_config_id: int = Field(0, description="默认模型配置 ID")
    version: str = Field("1.0.0", max_length=30, description="模板版本")
    is_default: bool = Field(False, description="是否分类默认模板")
    sort_order: int = Field(0, description="排序")
    change_note: str = Field("", description="版本变更说明")


class PromptTemplateUpdate(PromptTemplateCreate):
    is_active: bool = Field(True, description="是否启用")


class AIModelConfigCreate(BaseModel):
    name: str = Field(..., max_length=120, description="模型显示名称")
    model_type: str = Field("text", max_length=50, description="text/image/video/multimodal")
    provider: str = Field("custom", max_length=80, description="供应商")
    api_key: str = Field("", description="API Key")
    base_url: str = Field("https://api.openai.com/v1", max_length=500, description="Base URL")
    model_id: str = Field("", max_length=160, description="模型 ID")
    is_openai_compatible: bool = Field(True, description="是否 OpenAI 兼容")
    is_default: bool = Field(False, description="是否类型默认")
    timeout_seconds: int = Field(180, ge=10, le=600, description="超时时间")
    max_retries: int = Field(2, ge=0, le=5, description="最大重试次数")
    sort_order: int = Field(0, description="排序")
    notes: str = Field("", description="备注")


class AIModelConfigUpdate(AIModelConfigCreate):
    is_active: bool = Field(True, description="是否启用")


class TopicPlanRequest(BaseModel):
    extracted_content: str = Field(..., description="核心素材")
    persona_id: int = Field(0, description="IP 人设 ID")
    column_id: int = Field(0, description="栏目 ID")
    count: int = Field(6, ge=1, le=20, description="选题数量")
    extra_requirements: str = Field("", description="额外要求")


class HookOptimizeRequest(BaseModel):
    script_content: str = Field(..., description="口播文案")
    persona_id: int = Field(0, description="IP 人设 ID")
    column_id: int = Field(0, description="栏目 ID")
    count: int = Field(5, ge=1, le=10, description="开头数量")


class PublishPackageRequest(BaseModel):
    script_content: str = Field(..., description="口播文案")
    cover_prompt: str = Field("", description="封面提示词")
    target_platform: str = Field("视频号+抖音", description="目标平台")
    persona_id: int = Field(0, description="IP 人设 ID")
    column_id: int = Field(0, description="栏目 ID")


class QualityCheckRequest(BaseModel):
    script_content: str = Field(..., description="口播文案")
    cover_prompt: str = Field("", description="封面提示词")
    publish_copy: str = Field("", description="发布文案")
    persona_id: int = Field(0, description="IP 人设 ID")
    column_id: int = Field(0, description="栏目 ID")


class VideoAipPlanRequest(BaseModel):
    workflow_type: str = Field("product_tvc", description="product_tvc/drama/standard")
    source_content: str = Field("", description="素材解析结果或用户原始需求")
    script_content: str = Field("", description="口播/剧情脚本")
    product_name: str = Field("", description="产品名")
    character_notes: str = Field("", description="人物/角色关系说明")
    media_notes: list[str] = Field(default_factory=list, description="已上传媒体素材说明")
    source_assets: list[dict] = Field(default_factory=list, description="已上传媒体素材结构化引用")
    aspect_ratio: str = Field("9:16", description="视频比例")
    duration: str = Field("15秒", description="视频时长")
    style: str = Field("高级、真实、有记忆点", description="画面风格")
    user_requirements: str = Field("", description="用户补充要求")
    text_model_config_id: int = Field(0, description="剧本文本步骤模型配置 ID")
    video_prompt_template_id: int = Field(0, description="视频模板 ID")
    video_model_config_id: int = Field(0, description="视频模型配置 ID")


class VideoAipProjectCreate(VideoAipPlanRequest):
    title: str = Field("", max_length=200, description="项目标题")
    source_type: str = Field("manual", max_length=80, description="来源类型")
    source_ref_id: int = Field(0, description="来源记录 ID")


class VideoAipBridgeCreateRequest(BaseModel):
    title: str = Field("", max_length=200, description="可选覆盖 AIP 项目标题")
    workflow_type: str = Field("", description="可选覆盖：standard/product_tvc/drama")


class VideoAipStepStatusUpdate(BaseModel):
    status: str = Field(..., description="pending/running/succeeded/failed")
    output: dict = Field(default_factory=dict, description="步骤输出")
    error_message: str = Field("", description="错误信息")


class VideoAipStepRunRequest(BaseModel):
    workflow: str = Field("", description="可选 Pixelle media 工作流 key")
    media_type: str = Field("", description="可选覆盖：image/video")
    width: int = Field(0, description="可选覆盖生成宽度")
    height: int = Field(0, description="可选覆盖生成高度")
    duration: float = Field(0, description="可选覆盖视频秒数")
    negative_prompt: str = Field("", description="可选负面提示词")
    extra: dict = Field(default_factory=dict, description="透传给 media workflow 的其它参数")


class ReversalCharacter(BaseModel):
    name: str = Field("", description="人物名字")
    gender: str = Field("", description="性别")
    role: str = Field("", description="岗位/身份")
    personality: str = Field("", description="性格底色")
    catchphrase: str = Field("", description="口头禅")
    speaking_style: str = Field("", description="说话风格")
    drama_role: str = Field("", description="剧情功能：pressure/buffer/reversal_carrier/product_introducer/other")
    character_id: int = Field(0, description="关联 IP 项目角色 ID")


class ReversalDramaRequest(BaseModel):
    product_name: str = Field(..., description="推销产品名")
    product_function: str = Field(..., description="产品一句话功能")
    pain_point: str = Field(..., description="要打的痛点")
    template_key: str = Field("workplace_reversal", description="剧本类型 key")
    reversal_pattern: str = Field("auto", description="反转套路：auto/A/B/C")
    cast_source: str = Field("default", description="角色来源：default/preset/ip_project/manual")
    cast_preset_id: int = Field(0, description="角色组预设 ID")
    project_id: int = Field(0, description="IP 项目 ID（角色来源为 ip_project 时）")
    characters: Optional[list[ReversalCharacter]] = Field(
        None, description="自定义人物，留空走模板默认角色组"
    )
    platform: str = Field("视频号+抖音", description="发布平台")
    duration: str = Field("30-60秒", description="时长偏好")
    extra_requirements: str = Field("", description="额外要求")


class DramaCastPresetPayload(BaseModel):
    name: str = Field(..., max_length=120, description="角色组名称")
    project_id: int = Field(0, description="关联 IP 项目，0 表示临时组")
    characters: list[ReversalCharacter] = Field(default_factory=list, description="角色列表")
    relationship_hint: str = Field("", description="人物关系一句话")
    is_default: bool = Field(False, description="是否默认角色组")


# ─── 后台提示词模板配置（MVP 静态配置，后续可迁移到数据库） ──────────────

PROMPT_TEMPLATE_CATEGORIES = [
    {
        "key": "knowledge_talk",
        "name": "知识口播",
        "description": "干货分享、观点表达、专业 IP",
        "sort_order": 10,
    },
    {
        "key": "product_seed",
        "name": "带货种草",
        "description": "商品卖点、测评推荐、直播预热",
        "sort_order": 20,
    },
    {
        "key": "personal_ip",
        "name": "个人 IP",
        "description": "人设表达、经历故事、专家观点",
        "sort_order": 30,
    },
    {
        "key": "reversal_hook",
        "name": "反转钩子",
        "description": "反常识开场、冲突转折、结尾互动",
        "sort_order": 40,
    },
    {
        "key": "live_script",
        "name": "直播话术",
        "description": "直播间引流、开场、促单和福利预告",
        "sort_order": 50,
    },
    {
        "key": "brand_promo",
        "template_type": "text_script",
        "name": "品牌宣传",
        "description": "企业介绍、服务说明、案例包装",
        "sort_order": 60,
    },
    {
        "key": "wechat_article_rewrite",
        "template_type": "wechat_article",
        "name": "公众号二创文章",
        "description": "链接、粘贴原文或主题输入后生成公众号结构化文章",
        "sort_order": 70,
    },
    {
        "key": "cover_ip_portrait",
        "template_type": "image_cover",
        "name": "人物口播封面",
        "description": "人物参考图、标题文字和视频主题结合生成封面提示词",
        "sort_order": 110,
    },
    {
        "key": "character_consistency",
        "template_type": "image_character",
        "name": "人物一致性设定",
        "description": "上传人物图后生成角色设定、三视图或四视图提示词",
        "sort_order": 210,
    },
    {
        "key": "product_tvc_flow",
        "template_type": "video_clip",
        "name": "产品宣传大片 AIP",
        "description": "产品主体抠图、多视图、九/三十六宫格分镜到视频提示词",
        "sort_order": 310,
    },
    {
        "key": "drama_character_flow",
        "template_type": "video_clip",
        "name": "人物短剧 AIP",
        "description": "多人物四视图、剧情提示词、图片分镜和短剧视频提示词",
        "sort_order": 320,
    },
]

PROMPT_TEMPLATES = [
    {
        "id": 1,
        "key": "three_part_knowledge",
        "category_key": "knowledge_talk",
        "name": "三段式干货",
        "description": "适合专业观点、方法拆解和知识分享。",
        "scenario": "干货分享",
        "output_structure": "黄金3秒钩子 -> 核心观点 -> 三点方法 -> 总结金句 -> 互动 CTA",
        "writing_rules": ["开头必须给出明确痛点或反常识判断", "每个方法点都要有具体解释", "避免空泛鸡汤"],
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 10,
    },
    {
        "id": 2,
        "key": "pain_solution_seed",
        "category_key": "product_seed",
        "name": "痛点种草",
        "description": "从用户痛点切入，转化到产品卖点和行动建议。",
        "scenario": "产品种草",
        "output_structure": "痛点场景 -> 错误做法 -> 产品/方案价值 -> 使用建议 -> 转化 CTA",
        "writing_rules": ["先讲用户问题，不要直接硬广", "卖点必须对应具体场景", "不得做绝对效果承诺"],
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 20,
    },
    {
        "id": 3,
        "key": "expert_trust_ip",
        "category_key": "personal_ip",
        "name": "专家信任背书",
        "description": "适合专家 IP、创始人 IP 和顾问型账号建立信任。",
        "scenario": "个人 IP 表达",
        "output_structure": "身份/经历切入 -> 真实观察 -> 专业判断 -> 建议清单 -> 私信/关注 CTA",
        "writing_rules": ["表达要像真人经验，不要像百科说明", "保留专业判断边界", "可加入一处个人经历或案例"],
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 30,
    },
    {
        "id": 4,
        "key": "conflict_reversal",
        "category_key": "reversal_hook",
        "name": "冲突反转",
        "description": "用反常识或冲突开头提升完播率。",
        "scenario": "强钩子短视频",
        "output_structure": "反常识开场 -> 冲突解释 -> 真相揭示 -> 方法/观点 -> 评论互动",
        "writing_rules": ["第一句话必须有冲突感", "反转不能为了夸张牺牲事实", "结尾要引导评论讨论"],
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 40,
    },
    {
        "id": 5,
        "key": "live_preview_conversion",
        "category_key": "live_script",
        "name": "直播预热促单",
        "description": "适合直播预热视频、福利预告和开播提醒。",
        "scenario": "直播引流",
        "output_structure": "开播利益点 -> 适合人群 -> 福利/内容预告 -> 时间提醒 -> 进入直播 CTA",
        "writing_rules": ["利益点要具体", "福利表达避免虚假或夸大", "时间和行动指令要清楚"],
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 50,
    },
    {
        "id": 6,
        "key": "case_brand_story",
        "category_key": "brand_promo",
        "name": "案例型品牌宣传",
        "description": "通过客户案例、服务流程和结果复盘呈现品牌价值。",
        "scenario": "品牌宣传",
        "output_structure": "客户场景 -> 问题挑战 -> 服务过程 -> 结果变化 -> 品牌主张 CTA",
        "writing_rules": ["优先讲案例，不要堆企业口号", "结果表达要留有边界", "品牌主张要自然收束"],
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 60,
    },
    {
        "id": 70,
        "key": "wechat_deep_rewrite_json",
        "template_type": "wechat_article",
        "category_key": "wechat_article_rewrite",
        "name": "公众号深度二创 JSON",
        "description": "把链接、粘贴原文或主题生成标题、摘要、正文、封面提示词和正文插图建议。",
        "scenario": "公众号二创/原创文章",
        "output_structure": "JSON：title, subtitle, author, summary, cover_prompt, content_html_or_delta, markdown_snapshot, image_slots, tags, compliance_risks",
        "writing_rules": ["必须输出合法 JSON 对象", "正文适合公众号阅读，结构清晰", "必须给出封面提示词和 2-4 个插图位置建议", "避免广告法绝对化和未经证实承诺"],
        "prompt_body": "生成适合微信公众号的结构化图文稿。正文要有小标题、重点段落、结尾引导；image_slots 要说明插图位置、用途和图片提示词；compliance_risks 要指出医疗、金融、教育、广告法、版权等风险。",
        "user_prompt_hint": "补充账号定位、目标读者、文章风格、是否偏专业干货或情绪共鸣。",
        "default_params_json": json.dumps({"platform": "wechat", "format": "json", "image_slots": 3}, ensure_ascii=False),
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 70,
    },
    {
        "id": 101,
        "key": "ip_cover_big_title",
        "template_type": "image_cover",
        "category_key": "cover_ip_portrait",
        "name": "人物大字封面",
        "description": "用人物参考图、标题和内容摘要生成强点击封面提示词。",
        "scenario": "口播/知识/观点视频封面",
        "output_structure": "主体人物 -> 背景氛围 -> 主标题排版 -> 副标题/贴片 -> 禁止事项",
        "writing_rules": ["保持人物脸型和气质一致", "标题文字要清晰可读", "避免过度堆字和虚假承诺"],
        "user_prompt_hint": "补充封面标题、人物表情、背景风格、文字排版和比例要求。",
        "default_params_json": json.dumps({"aspect_ratio": "9:16", "style": "知识博主大字封面"}, ensure_ascii=False),
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 110,
    },
    {
        "id": 201,
        "key": "character_four_view",
        "template_type": "image_character",
        "category_key": "character_consistency",
        "name": "人物四视图设定",
        "description": "根据上传人物图生成正面、侧面、背面、半身细节四视图提示词。",
        "scenario": "人物一致性建模",
        "output_structure": "角色锚点 -> 四视图要求 -> 服装/五官/发型一致性 -> 背景和光线 -> 禁止事项",
        "writing_rules": ["保持脸型五官、发型、服装和年龄感一致", "四视图背景保持纯净", "禁止换脸、改年龄、多余肢体"],
        "user_prompt_hint": "补充人物身份、服装、场景、姿态和一致性强度。",
        "default_params_json": json.dumps({"view_count": "4", "aspect_ratio": "1:1", "consistency": "strong"}, ensure_ascii=False),
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 210,
    },
    {
        "id": 301,
        "key": "product_tvc_aip_chain",
        "template_type": "video_clip",
        "category_key": "product_tvc_flow",
        "name": "产品宣传大片四步链路",
        "description": "产品图上传后，串联主体抠图、三/四视图、九/三十六宫格分镜和最终视频提示词。",
        "scenario": "产品广告/TVC/带货短片",
        "output_structure": "1主体清理 -> 2三/四视图 -> 3九/三十六宫格分镜 -> 4最终视频提示词",
        "writing_rules": ["产品包装、Logo、标签文字和材质必须一致", "每个分镜要说明叙事功能", "最终提示词必须包含禁止改字、变形和错包装"],
        "user_prompt_hint": "补充产品卖点、目标平台、画面比例、视频时长、情绪基调和想要的大片效果。",
        "default_params_json": json.dumps({"workflow": "product_tvc", "aspect_ratio": "9:16", "duration": "15秒", "storyboard_grid": "9"}, ensure_ascii=False),
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 310,
    },
    {
        "id": 302,
        "key": "drama_character_aip_chain",
        "template_type": "video_clip",
        "category_key": "drama_character_flow",
        "name": "人物短剧多角色链路",
        "description": "多人物上传后，分别生成角色四视图、剧情提示词、图片分镜和最终短剧视频提示词。",
        "scenario": "短剧/反转剧/人物剧情短片",
        "output_structure": "多角色一致性 -> 剧情脚本 -> 图片分镜 -> 最终视频提示词",
        "writing_rules": ["每个角色都要有独立一致性锚点", "剧情和分镜一一对应", "禁止串脸、换衣、角色关系混乱"],
        "user_prompt_hint": "补充人物关系、冲突点、剧情反转、视频时长、画面风格和平台。",
        "default_params_json": json.dumps({"workflow": "drama", "aspect_ratio": "9:16", "duration": "30秒", "storyboard_grid": "9"}, ensure_ascii=False),
        "version": "1.0.0",
        "is_default": True,
        "is_active": True,
        "sort_order": 320,
    },
]


def _persona_profile(db: Session, persona_id: int, default: str = "无特定人设，使用专业中性风格") -> str:
    if persona_id:
        persona = db.query(Persona).filter(Persona.id == persona_id).first()
        if persona:
            return persona.to_profile_text()
    return default


def _column_profile(db: Session, column_id: int) -> str:
    if column_id:
        column = db.query(ContentColumn).filter(ContentColumn.id == column_id).first()
        if column:
            return column.to_context_text()
    return "未选择固定栏目，按通用短视频结构处理"


def _ensure_prompt_templates_seeded(db: Session) -> None:
    for category_data in PROMPT_TEMPLATE_CATEGORIES:
        category = db.query(PromptTemplateCategory).filter(
            PromptTemplateCategory.key == category_data["key"]
        ).first()
        if not category:
            db.add(PromptTemplateCategory(**category_data))

    for template_data in PROMPT_TEMPLATES:
        template = db.query(PromptTemplate).filter(PromptTemplate.key == template_data["key"]).first()
        if template:
            if not db.query(PromptTemplateVersion).filter(PromptTemplateVersion.template_id == template.id).first():
                _snapshot_prompt_template_version(db, template, "补齐内置模板版本历史")
            continue
        data = {key: value for key, value in template_data.items() if key not in ["id", "writing_rules"]}
        data["writing_rules_json"] = json.dumps(template_data.get("writing_rules") or [], ensure_ascii=False)
        data.setdefault("prompt_body", "")
        template = PromptTemplate(**data)
        db.add(template)
        db.flush()
        _snapshot_prompt_template_version(db, template, "系统内置模板初始化")
    db.commit()


def _snapshot_prompt_template_version(db: Session, template: PromptTemplate, change_note: str = "") -> PromptTemplateVersion:
    db.query(PromptTemplateVersion).filter(PromptTemplateVersion.template_id == template.id).update(
        {PromptTemplateVersion.is_active: False}, synchronize_session=False
    )
    version = PromptTemplateVersion(
        template_id=template.id,
        template_key=template.key,
        version=template.version,
        platform=template.platform or "",
        scene=template.scene or template.scenario or "",
        step=template.step or "",
        prompt_body=template.prompt_body or "",
        output_structure=template.output_structure or "",
        writing_rules_json=template.writing_rules_json or "[]",
        default_params_json=template.default_params_json or "{}",
        change_note=change_note,
        is_active=True,
    )
    db.add(version)
    db.flush()
    return version


def _active_prompt_categories(db: Session, template_type: str = "") -> list[dict]:
    try:
        _ensure_prompt_templates_seeded(db)
        categories = db.query(PromptTemplateCategory).filter(
            PromptTemplateCategory.is_active == True
        )
        if template_type:
            categories = categories.filter(PromptTemplateCategory.template_type == template_type)
        categories = categories.order_by(PromptTemplateCategory.sort_order, PromptTemplateCategory.id).all()
        return [category.to_dict() for category in categories]
    except Exception as exc:
        db.rollback()
        logger.warning("读取提示词分类失败，使用静态默认配置: %s", exc)
        categories = PROMPT_TEMPLATE_CATEGORIES
        if template_type:
            categories = [item for item in categories if item.get("template_type", "text_script") == template_type]
        return sorted(categories, key=lambda item: item["sort_order"])


def _active_prompt_templates(db: Session, category_key: str = "", template_type: str = "", include_prompt_body: bool = False) -> list[dict]:
    try:
        _ensure_prompt_templates_seeded(db)
        query = db.query(PromptTemplate).filter(PromptTemplate.is_active == True)
        if category_key:
            query = query.filter(PromptTemplate.category_key == category_key)
        if template_type:
            query = query.filter(PromptTemplate.template_type == template_type)
        templates = query.order_by(PromptTemplate.sort_order, PromptTemplate.id).all()
        return [template.to_dict(include_prompt_body=include_prompt_body) for template in templates]
    except Exception as exc:
        db.rollback()
        logger.warning("读取提示词模板失败，使用静态默认配置: %s", exc)
        templates = [template for template in PROMPT_TEMPLATES if template.get("is_active", True)]
        if category_key:
            templates = [template for template in templates if template["category_key"] == category_key]
        if template_type:
            templates = [template for template in templates if template.get("template_type", "text_script") == template_type]
        templates = sorted(templates, key=lambda item: item["sort_order"])
        if not include_prompt_body:
            return [{key: value for key, value in template.items() if key != "prompt_body"} for template in templates]
        return templates


def _prompt_template_by_id_or_key(db: Session, template_id: int = 0, template_key: str = "", template_type: str = "") -> Optional[dict]:
    for template in _active_prompt_templates(db, template_type=template_type, include_prompt_body=True):
        if template_id and template["id"] == template_id:
            return template
        if template_key and template["key"] == template_key:
            return template
    return None


def _prompt_template_snapshot(template: Optional[dict]) -> Optional[dict]:
    if not template:
        return None
    return {key: value for key, value in template.items() if key != "prompt_body"}


def _template_metric_key(template_type: str, template_id: int) -> str:
    return f"{template_type}:{template_id}"


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _prompt_template_usage_metrics(db: Session, template_type: str = "") -> list[dict]:
    metric_specs = [
        ("text_script", GenerationHistory.prompt_template_id),
        ("image_cover", GenerationHistory.cover_prompt_template_id),
        ("video_clip", GenerationHistory.video_prompt_template_id),
    ]
    metrics: dict[str, dict] = {}
    for current_type, column in metric_specs:
        if template_type and current_type != template_type:
            continue
        rows = (
            db.query(
                column.label("template_id"),
                func.count(GenerationHistory.id).label("generation_count"),
                func.max(GenerationHistory.created_at).label("last_generated_at"),
            )
            .filter(column > 0)
            .group_by(column)
            .all()
        )
        for row in rows:
            template_id = int(row.template_id)
            generation_count = int(row.generation_count or 0)
            history_ids = db.query(GenerationHistory.id).filter(column == template_id)
            event_rows = (
                db.query(
                    GenerationActionEvent.event_type,
                    func.count(func.distinct(GenerationActionEvent.history_id)).label("event_count"),
                )
                .filter(
                    GenerationActionEvent.history_id.in_(history_ids),
                    GenerationActionEvent.event_type.in_(["edited", "saved", "teleprompter_opened"]),
                )
                .group_by(GenerationActionEvent.event_type)
                .all()
            )
            event_counts = {event_type: int(event_count or 0) for event_type, event_count in event_rows}
            metrics[_template_metric_key(current_type, int(row.template_id))] = {
                "templateId": template_id,
                "templateType": current_type,
                "generationCount": generation_count,
                "editedCount": event_counts.get("edited", 0),
                "savedCount": event_counts.get("saved", 0),
                "teleprompterOpenedCount": event_counts.get("teleprompter_opened", 0),
                "editRate": _rate(event_counts.get("edited", 0), generation_count),
                "saveRate": _rate(event_counts.get("saved", 0), generation_count),
                "teleprompterRate": _rate(event_counts.get("teleprompter_opened", 0), generation_count),
                "lastGeneratedAt": row.last_generated_at.isoformat() if row.last_generated_at else None,
            }
    return list(metrics.values())


def _prompt_template_profile(db: Session, template: Optional[dict], category_key: str = "") -> str:
    if not template:
        if category_key:
            category = next((item for item in _active_prompt_categories(db) if item["key"] == category_key), None)
            if category:
                return f"已选择提示词分类：{category['name']}。未选择具体模板时，按该分类的通用口播结构生成。"
        return "未选择具体提示词模板，按通用高质量口播文案结构生成。"

    category = next((item for item in _active_prompt_categories(db) if item["key"] == template["category_key"]), None)
    rules = "；".join(template.get("writing_rules") or [])
    parts = [
        f"模板分类：{category['name'] if category else template['category_key']}",
        f"模板名称：{template['name']}（{template['key']}，版本 {template['version']}）",
        f"适用场景：{template['scenario']}",
        f"模板说明：{template['description']}",
        f"输出结构：{template['output_structure']}",
        f"写作规则：{rules or '无'}",
    ]
    if template.get("prompt_body"):
        parts.extend(["后台模板正文：", template["prompt_body"]])
    return "\n".join(parts)


def _audit_payload(value) -> str:
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False, default=str)


def _record_admin_operation(
    db: Session,
    request: Request,
    current_user: UserAccount,
    action: str,
    resource_type: str,
    resource_id: int = 0,
    resource_key: str = "",
    before: Optional[dict] = None,
    after: Optional[dict] = None,
) -> None:
    db.add(AdminOperationLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id or 0,
        resource_key=resource_key or "",
        before_json=_audit_payload(before),
        after_json=_audit_payload(after),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:500],
    ))


def _prompt_template_security_findings(data: PromptTemplateCreate | PromptTemplateUpdate) -> list[dict]:
    text = "\n".join([
        data.name or "",
        data.description or "",
        data.output_structure or "",
        "\n".join(data.writing_rules or []),
        data.prompt_body or "",
    ])
    lower = text.lower()
    findings: list[dict] = []
    checks = [
        ("secret_like_value", "疑似密钥或令牌", re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{24,}")),
        ("openai_secret_key", "疑似 OpenAI/API 密钥", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ]
    for code, message, pattern in checks:
        if pattern.search(text):
            findings.append({"code": code, "severity": "high", "message": message})
    blocked_phrases = [
        ("ignore previous instructions", "要求模型忽略上文/系统指令"),
        ("ignore all previous instructions", "要求模型忽略上文/系统指令"),
        ("reveal system prompt", "要求泄露系统提示词"),
        ("print system prompt", "要求输出系统提示词"),
        ("bypass safety", "要求绕过安全策略"),
        ("jailbreak", "疑似越狱提示词"),
        ("忽略之前", "要求模型忽略上文/系统指令"),
        ("忽略以上", "要求模型忽略上文/系统指令"),
        ("泄露系统提示词", "要求泄露系统提示词"),
        ("输出系统提示词", "要求输出系统提示词"),
        ("绕过安全", "要求绕过安全策略"),
        ("越狱", "疑似越狱提示词"),
    ]
    for phrase, message in blocked_phrases:
        if phrase in lower:
            findings.append({"code": "prompt_injection_instruction", "severity": "high", "message": message, "match": phrase})
    return findings


def _assert_prompt_template_safe(data: PromptTemplateCreate | PromptTemplateUpdate) -> None:
    findings = _prompt_template_security_findings(data)
    if not findings:
        return
    messages = "；".join(item["message"] for item in findings[:3])
    raise HTTPException(
        status_code=400,
        detail={
            "code": "PROMPT_TEMPLATE_SECURITY_RISK",
            "message": f"提示词模板存在高风险内容：{messages}",
            "findings": findings,
        },
    )


def _active_model_configs(db: Session, user: UserAccount, model_type: str = "") -> list[dict]:
    query = db.query(AIModelConfig).filter(AIModelConfig.is_active == True)
    if not user.is_admin:
        query = query.filter(or_(AIModelConfig.user_id == 0, AIModelConfig.user_id == user.id))
    if model_type:
        query = query.filter(AIModelConfig.model_type.in_([model_type, "multimodal"]))
    configs = query.order_by(AIModelConfig.sort_order, AIModelConfig.id).all()
    return [config.to_dict() for config in configs]


def _model_config_by_id(db: Session, config_id: int = 0, user: Optional[UserAccount] = None, user_id: int = 0) -> Optional[AIModelConfig]:
    if not config_id:
        return None
    config = db.query(AIModelConfig).filter(
        AIModelConfig.id == config_id,
        AIModelConfig.is_active == True,
    ).first()
    if not config:
        return None
    owner_id = user.id if user else user_id
    if owner_id and (config.user_id or 0) in (0, owner_id):
        return config
    return None


def _default_model_config(db: Session, model_type: str) -> Optional[AIModelConfig]:
    default_model = db.query(AIModelConfig).filter(
        AIModelConfig.model_type == model_type,
        AIModelConfig.is_default == True,
        AIModelConfig.is_active == True,
        AIModelConfig.user_id == 0,
    ).order_by(AIModelConfig.sort_order, AIModelConfig.id).first()
    if default_model:
        return default_model
    return db.query(AIModelConfig).filter(
        AIModelConfig.model_type.in_([model_type, "multimodal"]),
        AIModelConfig.is_active == True,
        AIModelConfig.user_id == 0,
    ).order_by(AIModelConfig.sort_order, AIModelConfig.id).first()


async def _chat_with_optional_model_config(
    ai: AIService,
    model_config: Optional[AIModelConfig],
    messages: list,
    prompt_name: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    api_key = decrypt_secret(model_config.api_key) if model_config else ""
    if model_config and api_key and model_config.base_url and model_config.model_id:
        return await ai._call_provider(
            base_url=model_config.base_url.rstrip("/"),
            api_key=api_key,
            model=model_config.model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name=model_config.provider or model_config.name,
        )
    return await ai.chat(messages, prompt_name=prompt_name, temperature=temperature, max_tokens=max_tokens)


def _build_product_tvc_aip_plan(data: VideoAipPlanRequest, video_template: Optional[dict], model_config: Optional[AIModelConfig]) -> dict:
    product_name = data.product_name or "用户上传产品"
    base_context = data.source_content or data.script_content or "用户上传了产品图，需要生成产品宣传短视频。"
    template_name = video_template["name"] if video_template else "产品宣传大片四步链路"
    model_name = model_config.name if model_config else "未选择真实视频模型，先生成可复制提示词"
    consistency = "保持产品外形、包装结构、标签文字、品牌标识、颜色、材质、比例、反光和纹理一致；禁止改字、加字、改包装、变形。"

    steps = [
        {
            "key": "subject_cleanup",
            "title": "第 1 步：主体清理 / 抠完整主体图",
            "goal": "从产品图中提取完整干净主体，为后续视图和分镜建立统一参考。",
            "task_type": "image",
            "artifact_type": "subject_cutout",
            "default_media_type": "image",
            "default_width": 1024,
            "default_height": 1024,
            "prompt": f"""请基于用户上传的产品图，清理出完整产品主体图。
主体：{product_name}
要求：保留完整包装轮廓、Logo、标签文字、材质反光和颜色；背景干净；产品不能变形。
一致性约束：{consistency}
素材理解：{base_context}
输出：直接生成一张干净完整的产品主体图，可用于继续生成三视图/四视图；不要输出文字说明或提示词。""",
        },
        {
            "key": "multi_view",
            "title": "第 2 步：三视图 / 四视图",
            "goal": "生成产品正面、侧面、背面和细节视图，锁定产品一致性。",
            "task_type": "image",
            "artifact_type": "four_view",
            "default_media_type": "image",
            "default_width": 1536,
            "default_height": 1024,
            "prompt": f"""根据已清理的产品主体图，为 {product_name} 生成产品四视图提示词。
视图：正面、45度侧面、背面、包装/材质细节特写。
比例：1:1 或 4:5，背景统一为高级棚拍浅色背景。
一致性约束：{consistency}
输出：直接生成一张四宫格产品四视图图片，每格分别为正面、45度侧面、背面、包装/材质细节特写；不要输出文字说明或提示词。""",
        },
        {
            "key": "storyboard_grid",
            "title": "第 3 步：九宫格 / 三十六宫格分镜",
            "goal": "把产品卖点、情绪和转化路径拆成连续镜头。",
            "task_type": "image",
            "artifact_type": "storyboard_grid",
            "default_media_type": "image",
            "default_width": 1536,
            "default_height": 1536,
            "prompt": f"""请为 {product_name} 生成产品宣传大片分镜。
视频比例：{data.aspect_ratio}
视频时长：{data.duration}
画面风格：{data.style}
用户要求：{data.user_requirements or '突出产品质感、卖点和记忆点'}
模板：{template_name}
九宫格结构：1开场环境，2主体登场，3细节特写，4动作开始，5核心卖点，6视觉高潮，7体验反应，8结果呈现，9品牌收尾。
如果用户要求更细，请扩展为三十六宫格，每 4 格对应一个九宫格镜头的细分动作。
一致性约束：{consistency}
输出：直接生成一张九宫格产品广告分镜图；每格画面连续、产品一致、镜头顺序清晰，可作为最终视频生成参考；不要输出文字说明或提示词。""",
        },
        {
            "key": "final_video_prompt",
            "title": "第 4 步：最终视频生成提示词",
            "goal": "整合主体图、四视图、分镜和用户要求，形成可提交给视频模型的提示词。",
            "task_type": "video",
            "artifact_type": "final_video",
            "default_media_type": "video",
            "default_width": 1080,
            "default_height": 1920,
            "prompt": f"""【视频类型】产品宣传大片 / Product TVC
【主体一致性】{consistency}
【参考图片说明】使用主体清理图、产品四视图、九宫格/三十六宫格分镜作为参考。
【产品】{product_name}
【画面比例】{data.aspect_ratio}
【视频时长】{data.duration}
【画面风格】{data.style}
【用户要求】{data.user_requirements or '高级真实、有商业广告质感、前3秒有吸引力'}
【动态脚本】严格按分镜镜头顺序生成，镜头连续，产品始终真实稳定。
【运镜要求】开场轻推，细节微距，高潮慢动作或环绕，收尾定格品牌记忆点。
【声音氛围】高级清爽、节奏明确，可加轻微环境音和产品质感音效。
【模型】{model_name}
【输出要求】直接生成最终视频，不要输出文字说明或提示词。
【禁止事项】禁止改包装文字、错误 Logo、产品变形、凭空添加卖点、画面前后不一致。""",
        },
    ]
    return {
        "workflow_type": "product_tvc",
        "title": f"{product_name} 产品宣传大片 AIP 链路",
        "summary": "先锁产品主体一致性，再生成多视图和分镜，最后提交真实视频生成任务。",
        "template": video_template,
        "model": model_config.to_dict() if model_config else None,
        "steps": steps,
        "handoff": "保存为 AIP 项目后，可逐步执行真实图片/视频模型任务，并把生成产物回写到步骤输出。",
    }


def _build_drama_aip_plan(data: VideoAipPlanRequest, video_template: Optional[dict], model_config: Optional[AIModelConfig]) -> dict:
    character_notes = data.character_notes or "用户上传了多个人物图片，需要保持每个角色一致并生成短剧。"
    base_context = data.source_content or data.script_content or "根据人物图片和剧情需求生成短剧。"
    template_name = video_template["name"] if video_template else "人物短剧多角色链路"
    model_name = model_config.name if model_config else "未选择真实视频模型，先生成可复制提示词"
    consistency = "每个角色都要保持脸型、五官、发型、肤色、体型、服装、配饰、年龄感和气质一致；禁止串脸、换脸、改衣服、角色关系混乱。"

    steps = [
        {
            "key": "character_views",
            "title": "第 1 步：多人物四视图",
            "goal": "为每个上传人物建立独立角色一致性锚点。",
            "task_type": "image",
            "artifact_type": "character_four_view",
            "default_media_type": "image",
            "default_width": 1536,
            "default_height": 1024,
            "prompt": f"""请根据上传的人物图片，为每个角色生成四视图设定提示词。
人物关系：{character_notes}
四视图：正面、侧面、背面、半身表情细节。
一致性约束：{consistency}
输出：直接生成一张多角色四视图设定图，每个角色保持独立一致性锚点；不要输出文字说明或提示词。""",
        },
        {
            "key": "drama_script",
            "title": "第 2 步：剧情提示词 / 剧本结构",
            "goal": "把人物关系、冲突点和反转点组织成可拍摄短剧。",
            "task_type": "text",
            "artifact_type": "drama_script",
            "prompt": f"""请生成 {data.duration} 人物短剧剧情提示词。
视频比例：{data.aspect_ratio}
画面风格：{data.style}
人物关系：{character_notes}
素材理解：{base_context}
用户要求：{data.user_requirements or '要有冲突、反转和结尾记忆点'}
模板：{template_name}
输出：剧情梗概、角色台词、冲突点、反转点、结尾 CTA、合规风险提醒。""",
        },
        {
            "key": "image_storyboard",
            "title": "第 3 步：图片分镜图",
            "goal": "把剧本拆成每镜可生成图片的分镜提示词。",
            "task_type": "image",
            "artifact_type": "storyboard_grid",
            "default_media_type": "image",
            "default_width": 1536,
            "default_height": 1536,
            "prompt": f"""请根据剧本生成九宫格图片分镜提示词。
九宫格结构：1环境建立，2主角出场，3矛盾出现，4对话推进，5冲突升级，6反转揭示，7角色反应，8结果呈现，9结尾记忆点。
一致性约束：{consistency}
输出：直接生成一张九宫格短剧图片分镜图，角色、动作、表情和镜头顺序清晰；不要输出文字说明或提示词。""",
        },
        {
            "key": "final_video_prompt",
            "title": "第 4 步：最终短剧视频提示词",
            "goal": "整合剧本、角色四视图和图片分镜，生成视频模型提示词。",
            "task_type": "video",
            "artifact_type": "final_video",
            "default_media_type": "video",
            "default_width": 1080,
            "default_height": 1920,
            "prompt": f"""【视频类型】人物短剧 / 剧情反转短片
【角色一致性】{consistency}
【参考图片说明】使用每个角色四视图和九宫格图片分镜作为参考。
【人物关系】{character_notes}
【画面比例】{data.aspect_ratio}
【视频时长】{data.duration}
【画面风格】{data.style}
【动态脚本】严格按剧本和图片分镜顺序生成，角色位置、表情、台词一致。
【声音氛围】根据剧情节奏加入环境声、停顿、反转音效和字幕重点。
【模型】{model_name}
【输出要求】直接生成最终短剧视频，不要输出文字说明或提示词。
【禁止事项】禁止串脸、换衣、错误人物关系、台词错位、镜头断裂、多余肢体。""",
        },
    ]
    return {
        "workflow_type": "drama",
        "title": "人物短剧 AIP 链路",
        "summary": "先分别锁定多角色一致性，再生成剧情、图片分镜和最终真实视频任务。",
        "template": video_template,
        "model": model_config.to_dict() if model_config else None,
        "steps": steps,
        "handoff": "保存为 AIP 项目后，可逐步执行真实图片/视频模型任务，并把生成产物回写到步骤输出。",
    }


def _video_aip_project_with_steps(db: Session, project: VideoAipProject) -> dict:
    data = project.to_dict(include_plan=True)
    data["source"] = _video_aip_source_summary(db, project)
    steps = db.query(VideoAipStepTask).filter(
        VideoAipStepTask.project_id == project.id
    ).order_by(VideoAipStepTask.sort_order, VideoAipStepTask.id).all()
    data["steps"] = [step.to_dict() for step in steps]
    return data


def _video_aip_source_summary(db: Session, project: VideoAipProject) -> dict:
    if not project.source_type or project.source_type == "manual" or not project.source_ref_id:
        return {"type": "manual", "refId": 0, "label": "手动创建", "title": "", "status": "", "anchor": "#ip"}
    if project.source_type == "short_video_project":
        source = db.query(ShortVideoProject).filter(
            ShortVideoProject.id == project.source_ref_id,
            ShortVideoProject.user_id == project.user_id,
        ).first()
        if not source:
            return {"type": project.source_type, "refId": project.source_ref_id, "label": "短视频工作流", "title": "来源已删除", "status": "missing", "anchor": "#ip"}
        return {
            "type": project.source_type,
            "refId": source.id,
            "label": "短视频工作流",
            "title": source.title,
            "status": "active" if source.is_active else "deleted",
            "meta": source.intent_label or source.intent_key,
            "anchor": "#ip",
        }
    if project.source_type == "storyboard_record":
        source = db.query(StoryboardRecord).filter(
            StoryboardRecord.id == project.source_ref_id,
            StoryboardRecord.user_id == project.user_id,
        ).first()
        if not source:
            return {"type": project.source_type, "refId": project.source_ref_id, "label": "分镜记录", "title": "来源已删除", "status": "missing", "anchor": "#platform"}
        return {
            "type": project.source_type,
            "refId": source.id,
            "label": "分镜记录",
            "title": source.title,
            "status": source.status,
            "meta": source.storyboard_type,
            "anchor": "#platform",
        }
    return {"type": project.source_type, "refId": project.source_ref_id, "label": project.source_type, "title": "", "status": "", "anchor": "#ip"}


def _ensure_video_aip_source_allowed(db: Session, data: VideoAipProjectCreate, user: UserAccount) -> None:
    source_type = (data.source_type or "manual").strip()
    source_ref_id = int(data.source_ref_id or 0)
    if not source_type or source_type == "manual" or not source_ref_id:
        return
    if source_type == "short_video_project":
        exists = db.query(ShortVideoProject.id).filter(
            ShortVideoProject.id == source_ref_id,
            ShortVideoProject.user_id == user.id,
            ShortVideoProject.is_active == True,
        ).first()
        if exists:
            return
    elif source_type == "storyboard_record":
        exists = db.query(StoryboardRecord.id).filter(
            StoryboardRecord.id == source_ref_id,
            StoryboardRecord.user_id == user.id,
            StoryboardRecord.is_active == True,
        ).first()
        if exists:
            return
    raise HTTPException(status_code=404, detail="来源不存在或无权访问")


def _persist_video_aip_project(db: Session, data: VideoAipProjectCreate, plan: dict, user_id: int = 0) -> VideoAipProject:
    title = data.title.strip() or plan.get("title") or "未命名视频 AIP 项目"
    project = VideoAipProject(
        user_id=user_id,
        title=title[:200],
        workflow_type=plan.get("workflow_type") or data.workflow_type,
        status="planned",
        source_content=data.source_content,
        script_content=data.script_content,
        product_name=data.product_name,
        character_notes=data.character_notes,
        source_type=data.source_type or "manual",
        source_ref_id=data.source_ref_id,
        source_assets_json=json.dumps(data.source_assets, ensure_ascii=False),
        params_json=json.dumps(data.model_dump(), ensure_ascii=False),
        plan_json=json.dumps(plan, ensure_ascii=False),
        current_step_key=plan.get("steps", [{}])[0].get("key", "") if plan.get("steps") else "",
    )
    db.add(project)
    db.flush()
    for idx, step in enumerate(plan.get("steps") or [], start=1):
        db.add(VideoAipStepTask(
            project_id=project.id,
            step_key=step.get("key", ""),
            title=step.get("title", ""),
            goal=step.get("goal", ""),
            prompt=step.get("prompt", ""),
            status="pending",
            output_json=json.dumps({
                "task_type": step.get("task_type", "text"),
                "artifact_type": step.get("artifact_type", ""),
                "default_media_type": step.get("default_media_type", ""),
                "default_width": step.get("default_width", 0),
                "default_height": step.get("default_height", 0),
            }, ensure_ascii=False),
            sort_order=idx,
        ))
    db.commit()
    db.refresh(project)
    return project


def _aip_workflow_type_from_short_video(intent_key: str, override: str = "") -> str:
    if override in {"standard", "product_tvc", "drama"}:
        return override
    if intent_key == "product_tvc":
        return "product_tvc"
    if intent_key in {"ip_character", "pet_vlog", "lifestyle", "space_store"}:
        return "drama"
    return "standard"


def _aip_workflow_type_from_storyboard(storyboard_type: str, override: str = "") -> str:
    if override in {"standard", "product_tvc", "drama"}:
        return override
    if storyboard_type in {"cinematic", "product_tvc", "tvc"}:
        return "product_tvc"
    if storyboard_type in {"drama", "short_drama", "scripted"}:
        return "drama"
    return "standard"


def _short_video_workflow_text(project: ShortVideoProject, workflow: dict) -> str:
    steps = workflow.get("steps") if isinstance(workflow, dict) else []
    lines = [project.archive_markdown or "", "", "【短视频工作流提示词】"]
    for idx, step in enumerate(steps or [], 1):
        if not isinstance(step, dict):
            continue
        lines.append(f"{idx}. {step.get('label') or step.get('key')}\n{step.get('prompt') or ''}")
    return "\n\n".join([line for line in lines if line])


def _storyboard_record_text(storyboard: StoryboardRecord, frames: list[dict]) -> str:
    lines = [f"分镜标题：{storyboard.title}", f"分镜类型：{storyboard.storyboard_type}", "", "【分镜表】"]
    for idx, frame in enumerate(frames or [], 1):
        if not isinstance(frame, dict):
            continue
        visual = frame.get("visual") or frame.get("画面") or frame.get("scene") or ""
        dialogue = frame.get("dialogue") or frame.get("台词") or frame.get("copy") or ""
        duration = frame.get("duration") or frame.get("时长") or ""
        camera = frame.get("camera") or frame.get("运镜") or ""
        lines.append(f"{idx}. 时长：{duration}；画面：{visual}；台词/字幕：{dialogue}；运镜：{camera}")
    return "\n".join(lines)


def _load_json(value: str, fallback):
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _duration_seconds(value: str, fallback: float = 15.0) -> float:
    match = re.search(r"\d+(?:\.\d+)?", value or "")
    if not match:
        return fallback
    duration = float(match.group(0))
    return max(1.0, min(duration, 120.0))


def _aspect_dimensions(aspect_ratio: str, media_type: str) -> tuple[int, int]:
    if aspect_ratio == "16:9":
        return (1280, 720) if media_type == "video" else (1344, 768)
    if aspect_ratio == "1:1":
        return (1024, 1024)
    if aspect_ratio == "4:5":
        return (1024, 1280)
    return (1080, 1920) if media_type == "video" else (1024, 1536)


def _step_plan_meta(project: VideoAipProject, step: VideoAipStepTask) -> dict:
    plan = _load_json(project.plan_json, {})
    for item in plan.get("steps") or []:
        if item.get("key") == step.step_key:
            return item
    return {}


def _step_execution_defaults(project: VideoAipProject, step: VideoAipStepTask, overrides: VideoAipStepRunRequest) -> dict:
    params = _load_json(project.params_json, {})
    saved_output = _load_json(step.output_json, {})
    meta = {**_step_plan_meta(project, step), **saved_output}
    step_key = step.step_key
    media_type = overrides.media_type or meta.get("default_media_type") or meta.get("task_type")
    artifact_type = meta.get("artifact_type") or step_key

    if not media_type:
        if step_key in {"final_video_prompt", "final_prompt"}:
            media_type = "video"
        elif step_key in {"subject_cleanup", "clean_subject", "multi_view", "four_views", "character_views", "storyboard_grid", "image_storyboard", "storyboard"}:
            media_type = "image"
        else:
            media_type = "text"

    if media_type == "text":
        raise HTTPException(status_code=400, detail="该步骤是文本编排步骤，无需提交图片/视频模型任务")
    if media_type not in {"image", "video"}:
        raise HTTPException(status_code=400, detail="media_type must be image or video")

    width = overrides.width or int(meta.get("default_width") or 0)
    height = overrides.height or int(meta.get("default_height") or 0)
    if not width or not height:
        width, height = _aspect_dimensions(params.get("aspect_ratio", "9:16"), media_type)

    duration = overrides.duration or ( _duration_seconds(params.get("duration", "15秒")) if media_type == "video" else 0 )
    return {
        "media_type": media_type,
        "artifact_type": artifact_type,
        "workflow": overrides.workflow or "",
        "width": width,
        "height": height,
        "duration": duration,
        "negative_prompt": overrides.negative_prompt or "低清晰度、变形、文字错误、Logo 错误、多余肢体、主体不一致、画面断裂",
        "extra": overrides.extra or {},
    }


def _video_aip_step_task_type(project: VideoAipProject, step: VideoAipStepTask) -> str:
    saved_output = _load_json(step.output_json, {})
    meta = {**_step_plan_meta(project, step), **saved_output}
    return meta.get("task_type") or meta.get("default_media_type") or "text"


def _previous_aip_artifacts(db: Session, project_id: int, before_sort_order: int) -> list[dict]:
    previous_steps = db.query(VideoAipStepTask).filter(
        VideoAipStepTask.project_id == project_id,
        VideoAipStepTask.sort_order < before_sort_order,
    ).order_by(VideoAipStepTask.sort_order, VideoAipStepTask.id).all()
    artifacts = []
    for previous in previous_steps:
        output = _load_json(previous.output_json, {})
        media_url = output.get("media_url") or output.get("media_file_url")
        if media_url:
            artifacts.append({
                "step_key": previous.step_key,
                "title": previous.title,
                "artifact_type": output.get("artifact_type", ""),
                "media_type": output.get("media_type", ""),
                "media_url": media_url,
            })
        text_output = output.get("generated_script") or output.get("raw_markdown") or output.get("message")
        if text_output and output.get("artifact_type") in {"drama_script", "script"}:
            artifacts.append({
                "step_key": previous.step_key,
                "title": previous.title,
                "artifact_type": output.get("artifact_type", "drama_script"),
                "media_type": "text",
                "text_excerpt": str(text_output)[:2000],
            })
    return artifacts


def _source_assets_from_project(project: VideoAipProject) -> list[dict]:
    params = _load_json(project.params_json, {})
    assets = params.get("source_assets") or _load_json(getattr(project, "source_assets_json", "[]"), [])
    return assets if isinstance(assets, list) else []


def _source_asset_lines(assets: list[dict]) -> list[str]:
    lines = []
    for idx, asset in enumerate(assets, 1):
        if not isinstance(asset, dict):
            continue
        filename = asset.get("filename") or asset.get("name") or f"素材{idx}"
        asset_type = asset.get("type") or asset.get("asset_type") or "unknown"
        path = asset.get("path") or asset.get("url") or asset.get("storagePath") or ""
        description = asset.get("description") or asset.get("summary") or ""
        lines.append(f"{idx}. {filename}（{asset_type}）：{description}；引用：{path}")
    return lines


def _prompt_with_previous_artifacts(prompt: str, artifacts: list[dict], source_assets: list[dict] | None = None) -> str:
    source_asset_lines = _source_asset_lines(source_assets or [])
    if not artifacts:
        if not source_asset_lines:
            return prompt
        return "\n".join([prompt, "", "【原始上传素材】", *source_asset_lines, "请优先参考原始素材，保持产品/人物主体一致。"])
    lines = [prompt, "", "【上游真实生成产物】"]
    for idx, artifact in enumerate(artifacts, 1):
        if artifact.get("media_type") == "text":
            lines.append(f"{idx}. {artifact.get('title') or artifact.get('step_key')}：{artifact.get('text_excerpt')}")
        else:
            lines.append(f"{idx}. {artifact.get('title') or artifact.get('step_key')}：{artifact.get('media_url')}")
    if source_asset_lines:
        lines.extend(["", "【原始上传素材】", *source_asset_lines])
    lines.append("请以上游产物作为一致性参考，保持主体、角色、包装、视图和分镜连续。")
    return "\n".join(lines)


def _require_video_runtime_ready() -> None:
    if not video_runtime.ENGINE_STATE.ready:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "video_engine_unavailable",
                "reason": video_runtime.ENGINE_STATE.error or "engine not initialized",
                "hint": "请先完成 backend/video_engine/config.yaml、RunningHub 或本地 ComfyUI 配置。",
            },
        )


def _has_video_runtime_runninghub_key() -> bool:
    if os.getenv("RUNNINGHUB_API_KEY"):
        return True
    try:
        engine = video_runtime._engine()
        for service_name in ("media", "image_analysis", "video_analysis", "tts"):
            service = getattr(engine, service_name, None)
            config = getattr(service, "global_config", {}) or {}
            if config.get("runninghub_api_key"):
                return True
    except Exception:
        return False
    return False


def _require_media_workflow_credentials(workflow: str = "") -> None:
    try:
        engine = video_runtime._engine()
        workflow_info = engine.media._resolve_workflow(workflow=workflow or None)
    except Exception:
        return
    if workflow_info.get("source") == "runninghub" and not _has_video_runtime_runninghub_key():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "runninghub_api_key_missing",
                "message": "RunningHub API Key 未配置，无法执行真实出图/出视频任务。",
                "hint": "填写 backend/video_engine/config.yaml 的 comfyui.runninghub_api_key，或设置 RUNNINGHUB_API_KEY；如使用本地 ComfyUI，请把默认 workflow 改成 selfhost/* 并启动 127.0.0.1:8188。",
            },
        )


def _media_file_url(task_id: str) -> str:
    return f"/api/video/tasks/{task_id}/media-file"


def _task_record_output(record, existing: dict) -> dict:
    existing = existing or {}
    output = {
        **(existing or {}),
        "task_id": record.task_id,
        "task_status": record.status,
        "progress": record.progress,
        "current_event": record.current_event,
        "media_type": record.media_type or existing.get("media_type"),
        "media_url": record.media_url,
        "media_path": record.media_path,
        "media_file_url": _media_file_url(record.task_id) if (record.media_path or record.video_path) else record.media_url,
        "video_path": record.video_path,
        "duration": record.duration or existing.get("duration"),
        "file_size": record.file_size,
        "completed_at": datetime.utcnow().isoformat() if record.status in {"succeeded", "failed"} else None,
    }
    return output


def _create_video_aip_generation_task(
    db: Session,
    project: VideoAipProject,
    step: VideoAipStepTask,
    prompt: str,
    defaults: dict,
    previous_artifacts: list[dict],
) -> GenerationTask | None:
    if not project.user_id:
        return None
    task = GenerationTask(
        user_id=project.user_id,
        project_id=0,
        task_type=f"video_aip_{defaults['media_type']}_generate",
        status="running",
        progress=0,
        started_at=datetime.utcnow(),
        input_snapshot_json=json.dumps({
            "videoAipProjectId": project.id,
            "videoAipStepId": step.id,
            "stepKey": step.step_key,
            "prompt": prompt,
            "defaults": defaults,
            "previousArtifacts": previous_artifacts,
            "sourceAssets": _source_assets_from_project(project),
        }, ensure_ascii=False),
    )
    db.add(task)
    db.flush()
    db.add(GenerationRecord(
        task_id=task.id,
        user_id=project.user_id,
        project_id=0,
        prompt_snapshot_json=json.dumps({
            "videoAipProjectId": project.id,
            "videoAipStepId": step.id,
            "stepKey": step.step_key,
            "prompt": prompt,
        }, ensure_ascii=False),
        model_config_id=_load_json(project.params_json, {}).get("video_model_config_id") or 0,
        model_snapshot_json=json.dumps((_load_json(project.plan_json, {}).get("model") or {}), ensure_ascii=False),
        params_json=json.dumps(defaults, ensure_ascii=False),
        raw_request_json=json.dumps({"workflow": defaults.get("workflow"), "mediaType": defaults.get("media_type")}, ensure_ascii=False),
        parsed_output_json=json.dumps({"status": "submitted"}, ensure_ascii=False),
    ))
    return task


def _sync_video_aip_generation_task_and_asset(db: Session, project: VideoAipProject, step: VideoAipStepTask, output: dict, record) -> None:
    generation_task_id = int(output.get("generation_task_id") or 0)
    if generation_task_id:
        task = db.query(GenerationTask).filter(
            GenerationTask.id == generation_task_id,
            GenerationTask.user_id == project.user_id,
        ).first()
        if task:
            task.status = "succeeded" if record.status == "succeeded" else "failed"
            task.progress = int((record.progress or 0) * 100)
            task.output_snapshot_json = json.dumps(output, ensure_ascii=False)
            task.error_message = record.error or ""
            task.raw_response_excerpt = json.dumps(record.to_dict(), ensure_ascii=False)[:2000]
            task.finished_at = datetime.utcnow()
    media_url = output.get("media_url") or output.get("media_file_url")
    storage_path = output.get("media_path") or output.get("video_path") or ""
    if record.status != "succeeded" or not project.user_id or not (media_url or storage_path):
        return
    asset = UnifiedAsset(
        user_id=project.user_id,
        asset_type=output.get("media_type") or record.media_type or "image",
        source_type="video_aip_step_generated",
        url=media_url or "",
        storage_path=storage_path,
        title=f"{project.title} · {step.title}"[:240],
        metadata_json=json.dumps({
            "videoAipProjectId": project.id,
            "videoAipStepId": step.id,
            "stepKey": step.step_key,
            "taskId": record.task_id,
            "generationTaskId": generation_task_id,
            "artifactType": output.get("artifact_type", ""),
        }, ensure_ascii=False),
        tags_json=json.dumps(["video-aip", step.step_key], ensure_ascii=False),
    )
    db.add(asset)
    db.flush()
    output["asset_id"] = asset.id


def _refresh_video_aip_project_status(db: Session, project_id: int) -> None:
    project = db.query(VideoAipProject).filter(VideoAipProject.id == project_id).first()
    if not project:
        return
    steps = db.query(VideoAipStepTask).filter(VideoAipStepTask.project_id == project_id).all()
    if not steps:
        project.status = "planned"
        return
    if any(step.status == "failed" for step in steps):
        project.status = "failed"
    elif any(step.status == "running" for step in steps):
        project.status = "running"
    elif all(step.status == "succeeded" for step in steps):
        project.status = "succeeded"
    elif any(step.status == "succeeded" for step in steps):
        project.status = "running"
    else:
        project.status = "planned"


def _persist_media_task_result(project_id: int, step_id: int, record) -> None:
    with SessionLocal() as db:
        step = db.query(VideoAipStepTask).filter(
            VideoAipStepTask.id == step_id,
            VideoAipStepTask.project_id == project_id,
        ).first()
        if not step:
            return
        project = db.query(VideoAipProject).filter(VideoAipProject.id == project_id).first()
        if not project:
            return
        existing = _load_json(step.output_json, {})
        output = _task_record_output(record, existing)
        _sync_video_aip_generation_task_and_asset(db, project, step, output, record)
        step.output_json = json.dumps(output, ensure_ascii=False)
        step.status = "succeeded" if record.status == "succeeded" else "failed"
        step.error_message = record.error or ""
        _refresh_video_aip_project_status(db, project_id)
        db.commit()


async def _generate_video_aip_text_step(db: Session, project: VideoAipProject, step: VideoAipStepTask) -> None:
    prompt = _prompt_with_previous_artifacts(
        step.prompt,
        _previous_aip_artifacts(db, project.id, step.sort_order),
        _source_assets_from_project(project),
    )
    params = _load_json(project.params_json, {})
    model_config = _model_config_by_id(db, int(params.get("text_model_config_id") or 0), user_id=project.user_id) or _default_model_config(db, "text")
    ai = AIService(module_code="ip_system", db_session=db)
    messages = [
        {"role": "system", "content": "你是短剧编剧和 AI 视频导演。请把用户的人物关系、素材和要求整理成可直接给分镜和视频模型使用的结构化剧本。"},
        {"role": "user", "content": prompt},
    ]
    try:
        response = await _chat_with_optional_model_config(
            ai,
            model_config,
            messages,
            prompt_name="video_aip_text_step",
            temperature=0.75,
            max_tokens=4096,
        )
        raw_text = response.content or ""
    except (AIProviderError, Exception) as exc:
        raise _ai_unavailable_error(exc, "视频 AIP 剧本文本步骤生成")

    parsed = _parse_reversal_drama_markdown(raw_text)
    output = {
        **_load_json(step.output_json, {}),
        "task_status": "succeeded",
        "media_type": "text",
        "task_type": "text",
        "artifact_type": "drama_script",
        "completed_at": datetime.utcnow().isoformat(),
        "prompt": prompt,
        "generated_script": raw_text,
        "structured_script": parsed,
        "model": model_config.to_dict() if model_config else None,
        "message": "文本编排步骤已调用文本模型生成，后续媒体步骤会引用该剧本产物。",
    }
    step.status = "succeeded"
    step.error_message = ""
    step.output_json = json.dumps(output, ensure_ascii=False)
    project.current_step_key = step.step_key


def _mark_text_step_succeeded(db: Session, project: VideoAipProject, step: VideoAipStepTask) -> None:
    output = {
        **_load_json(step.output_json, {}),
        "task_status": "succeeded",
        "completed_at": datetime.utcnow().isoformat(),
        "message": "文本编排步骤已自动通过，后续媒体步骤会引用该提示词内容。",
        "prompt": step.prompt,
    }
    step.status = "succeeded"
    step.error_message = ""
    step.output_json = json.dumps(output, ensure_ascii=False)
    project.current_step_key = step.step_key


def _next_pending_or_failed_step(db: Session, project_id: int) -> Optional[VideoAipStepTask]:
    return db.query(VideoAipStepTask).filter(
        VideoAipStepTask.project_id == project_id,
        VideoAipStepTask.status.in_(["pending", "failed"]),
    ).order_by(VideoAipStepTask.sort_order, VideoAipStepTask.id).first()


def _submit_video_aip_media_step(
    db: Session,
    project: VideoAipProject,
    step: VideoAipStepTask,
    data: VideoAipStepRunRequest,
):
    defaults = _step_execution_defaults(project, step, data)
    _require_media_workflow_credentials(defaults["workflow"])
    previous_artifacts = _previous_aip_artifacts(db, project.id, step.sort_order)
    source_assets = _source_assets_from_project(project)
    prompt = _prompt_with_previous_artifacts(step.prompt, previous_artifacts, source_assets)
    media_kwargs = {
        "width": defaults["width"],
        "height": defaults["height"],
        "negative_prompt": defaults["negative_prompt"],
        **defaults["extra"],
    }
    if defaults["media_type"] == "video" and defaults["duration"]:
        media_kwargs["duration"] = defaults["duration"]

    generation_task = _create_video_aip_generation_task(db, project, step, prompt, defaults, previous_artifacts)

    record = video_runtime.submit_media_task(
        prompt=prompt,
        media_type=defaults["media_type"],
        workflow=defaults["workflow"] or None,
        user_id=project.user_id,
        on_complete=lambda finished_record: _persist_media_task_result(project.id, step.id, finished_record),
        **media_kwargs,
    )

    output = {
        **_load_json(step.output_json, {}),
        "task_id": record.task_id,
        "task_status": record.status,
        "task_type": defaults["media_type"],
        "media_type": defaults["media_type"],
        "artifact_type": defaults["artifact_type"],
        "workflow": defaults["workflow"],
        "width": defaults["width"],
        "height": defaults["height"],
        "duration": defaults["duration"] or None,
        "previous_artifacts": previous_artifacts,
        "source_assets": source_assets,
        "generation_task_id": generation_task.id if generation_task else 0,
        "prompt": prompt,
        "submitted_at": datetime.utcnow().isoformat(),
    }
    step.status = "running"
    step.error_message = ""
    step.output_json = json.dumps(output, ensure_ascii=False)
    project.status = "running"
    project.current_step_key = step.step_key
    return record


async def _run_video_aip_project_sequence(project_id: int) -> None:
    while True:
        with SessionLocal() as db:
            project = db.query(VideoAipProject).filter(VideoAipProject.id == project_id).first()
            if not project:
                return
            step = _next_pending_or_failed_step(db, project_id)
            if not step:
                _refresh_video_aip_project_status(db, project_id)
                db.commit()
                return
            try:
                defaults = _step_execution_defaults(project, step, VideoAipStepRunRequest())
            except HTTPException as exc:
                if "文本编排步骤" not in str(exc.detail):
                    raise
                await _generate_video_aip_text_step(db, project, step)
                _refresh_video_aip_project_status(db, project_id)
                db.commit()
                continue
            record = _submit_video_aip_media_step(db, project, step, VideoAipStepRunRequest())
            db.commit()

        if record.asyncio_task is not None:
            await record.asyncio_task
        if record.status == "failed":
            return


def _ai_unavailable_error(exc: Exception, action: str = "AI 生成") -> HTTPException:
    logger.error("%s失败: %s", action, exc)
    return HTTPException(
        status_code=503,
        detail={
            "error": "ai_provider_unavailable",
            "message": f"{action}服务暂不可用，请检查 AI 模型、Base URL 或 API Key 配置。",
            "reason": str(exc),
        },
    )


async def _json_ai_response(
    messages: list,
    prompt_name: str,
    db: Session,
    temperature: float = 0.75,
    max_tokens: int = 4096,
    default: Optional[dict] = None,
) -> dict:
    ai = AIService(module_code="ip_system", db_session=db)
    response = await ai.chat(
        messages,
        prompt_name=prompt_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    data, _ = safe_parse_ai_json(response.content, default or {})
    return data


async def _refine_extracted_content(raw_text: str) -> str:
    """Use AI to refine extracted text, but never block content extraction too long."""
    if len(raw_text.strip()) > 5000:
        logger.info("提取内容较长，跳过 AI 精炼，直接返回原文")
        return raw_text

    ai = AIService(module_code="ip_system")
    messages = [
        {"role": "system", "content": EXTRACT_CONTENT_SYSTEM},
        {"role": "user", "content": EXTRACT_CONTENT_USER.format(raw_content=raw_text)},
    ]
    try:
        response = await asyncio.wait_for(
            ai.chat(messages, prompt_name="extract_content", max_tokens=2048),
            timeout=45,
        )
        return response.content or raw_text
    except Exception as e:
        logger.warning("AI 内容精炼失败或超时，使用原始提取内容: %s", e)
        return raw_text


# ─── 1. 内容解析 ─────────────────────────────────────────────

@router.post("/parse", summary="解析输入内容（链接/文本）")
async def parse_content(data: ParseRequest):
    """从 URL 或纯文本中提取核心内容"""
    if data.url:
        try:
            raw_text = await extract_from_url(data.url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif data.text:
        raw_text = extract_from_text(data.text)
    else:
        raise HTTPException(status_code=400, detail="请提供 url 或 text 参数")

    if not raw_text or len(raw_text.strip()) < 5:
        raise HTTPException(status_code=400, detail="提取的内容过短，请检查链接或手动粘贴内容")

    extracted = raw_text if data.url else await _refine_extracted_content(raw_text)

    return {
        "code": 0,
        "data": {
            "raw_text": raw_text,
            "extracted_content": extracted,
        }
    }


@router.post("/parse-file", summary="解析上传的文件")
async def parse_file(file: UploadFile = File(...)):
    """从上传的文件中提取内容"""
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB 限制
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

    try:
        raw_text = await extract_from_file(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    extracted = await _refine_extracted_content(raw_text)

    return {
        "code": 0,
        "data": {
            "raw_text": raw_text,
            "extracted_content": extracted,
        }
    }


# ─── 2. 一键生成全案 ─────────────────────────────────────────

@router.get("/prompt-template-categories", summary="获取口播提示词模板分类")
async def list_prompt_template_categories(template_type: str = "", db: Session = Depends(get_db)):
    return {"code": 0, "data": _active_prompt_categories(db, template_type)}


@router.post("/prompt-template-categories", summary="创建口播提示词模板分类")
async def create_prompt_template_category(
    data: PromptTemplateCategoryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    _ensure_prompt_templates_seeded(db)
    exists = db.query(PromptTemplateCategory).filter(PromptTemplateCategory.key == data.key).first()
    if exists:
        raise HTTPException(status_code=409, detail="提示词分类 Key 已存在")
    category = PromptTemplateCategory(**data.model_dump())
    db.add(category)
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="prompt_category.create",
        resource_type="prompt_template_category",
        resource_id=category.id,
        resource_key=category.key,
        after=category.to_dict(),
    )
    db.commit()
    db.refresh(category)
    return {"code": 0, "data": category.to_dict(), "message": "创建成功"}


@router.put("/prompt-template-categories/{category_key}", summary="更新口播提示词模板分类")
async def update_prompt_template_category(
    category_key: str,
    data: PromptTemplateCategoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    _ensure_prompt_templates_seeded(db)
    category = db.query(PromptTemplateCategory).filter(PromptTemplateCategory.key == category_key).first()
    if not category:
        raise HTTPException(status_code=404, detail="提示词分类不存在")
    before = category.to_dict()
    if data.key != category_key:
        key_exists = db.query(PromptTemplateCategory).filter(PromptTemplateCategory.key == data.key).first()
        if key_exists:
            raise HTTPException(status_code=409, detail="提示词分类 Key 已存在")
        db.query(PromptTemplate).filter(PromptTemplate.category_key == category_key).update(
            {PromptTemplate.category_key: data.key}, synchronize_session=False
        )
    for key, value in data.model_dump().items():
        setattr(category, key, value)
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="prompt_category.update",
        resource_type="prompt_template_category",
        resource_id=category.id,
        resource_key=category.key,
        before=before,
        after=category.to_dict(),
    )
    db.commit()
    db.refresh(category)
    return {"code": 0, "data": category.to_dict(), "message": "更新成功"}


@router.delete("/prompt-template-categories/{category_key}", summary="停用口播提示词模板分类")
async def delete_prompt_template_category(
    category_key: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    _ensure_prompt_templates_seeded(db)
    category = db.query(PromptTemplateCategory).filter(PromptTemplateCategory.key == category_key).first()
    if not category:
        raise HTTPException(status_code=404, detail="提示词分类不存在")
    before = category.to_dict()
    category.is_active = False
    db.query(PromptTemplate).filter(PromptTemplate.category_key == category_key).update(
        {PromptTemplate.is_active: False}, synchronize_session=False
    )
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="prompt_category.disable",
        resource_type="prompt_template_category",
        resource_id=category.id,
        resource_key=category.key,
        before=before,
        after=category.to_dict(),
    )
    db.commit()
    return {"code": 0, "message": "停用成功"}


@router.get("/prompt-templates", summary="获取口播提示词模板")
async def list_prompt_templates(category_key: str = "", template_type: str = "", db: Session = Depends(get_db)):
    return {"code": 0, "data": _active_prompt_templates(db, category_key, template_type)}


@router.get("/prompt-templates/metrics", summary="获取提示词模板使用指标")
async def list_prompt_template_metrics(
    template_type: str = "",
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    del current_user
    return {"code": 0, "data": _prompt_template_usage_metrics(db, template_type)}


@router.post("/prompt-templates", summary="创建口播提示词模板")
async def create_prompt_template(
    data: PromptTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    _ensure_prompt_templates_seeded(db)
    _assert_prompt_template_safe(data)
    category = db.query(PromptTemplateCategory).filter(
        PromptTemplateCategory.key == data.category_key,
        PromptTemplateCategory.is_active == True,
    ).first()
    if not category:
        raise HTTPException(status_code=400, detail="提示词分类不存在或已停用")
    exists = db.query(PromptTemplate).filter(PromptTemplate.key == data.key).first()
    if exists:
        raise HTTPException(status_code=409, detail="提示词模板 Key 已存在")
    if data.is_default:
        db.query(PromptTemplate).filter(PromptTemplate.category_key == data.category_key).update(
            {PromptTemplate.is_default: False}, synchronize_session=False
        )
    payload = data.model_dump(exclude={"writing_rules", "change_note"})
    payload["writing_rules_json"] = json.dumps(data.writing_rules, ensure_ascii=False)
    template = PromptTemplate(**payload)
    db.add(template)
    db.flush()
    version = _snapshot_prompt_template_version(db, template, data.change_note or "创建模板")
    _record_admin_operation(
        db,
        request,
        current_user,
        action="prompt_template.create",
        resource_type="prompt_template",
        resource_id=template.id,
        resource_key=template.key,
        after={**template.to_dict(include_prompt_body=True), "versionSnapshot": version.to_dict(include_prompt_body=True)},
    )
    db.commit()
    db.refresh(template)
    return {"code": 0, "data": {**template.to_dict(include_prompt_body=True), "versionId": version.id}, "message": "创建成功"}


@router.get("/prompt-templates/{template_id}", summary="获取口播提示词模板详情")
async def get_prompt_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    _ensure_prompt_templates_seeded(db)
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    return {"code": 0, "data": template.to_dict(include_prompt_body=True)}


@router.put("/prompt-templates/{template_id}", summary="更新口播提示词模板")
async def update_prompt_template(
    template_id: int,
    data: PromptTemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    _ensure_prompt_templates_seeded(db)
    _assert_prompt_template_safe(data)
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    before = template.to_dict(include_prompt_body=True)
    category = db.query(PromptTemplateCategory).filter(
        PromptTemplateCategory.key == data.category_key,
        PromptTemplateCategory.is_active == True,
    ).first()
    if not category:
        raise HTTPException(status_code=400, detail="提示词分类不存在或已停用")
    if data.key != template.key:
        key_exists = db.query(PromptTemplate).filter(PromptTemplate.key == data.key).first()
        if key_exists:
            raise HTTPException(status_code=409, detail="提示词模板 Key 已存在")
    if data.is_default:
        db.query(PromptTemplate).filter(
            PromptTemplate.category_key == data.category_key,
            PromptTemplate.id != template_id,
        ).update({PromptTemplate.is_default: False}, synchronize_session=False)
    payload = data.model_dump(exclude={"writing_rules", "change_note"})
    for key, value in payload.items():
        setattr(template, key, value)
    template.writing_rules_json = json.dumps(data.writing_rules, ensure_ascii=False)
    db.flush()
    version = _snapshot_prompt_template_version(db, template, data.change_note or "更新模板")
    _record_admin_operation(
        db,
        request,
        current_user,
        action="prompt_template.update",
        resource_type="prompt_template",
        resource_id=template.id,
        resource_key=template.key,
        before=before,
        after={**template.to_dict(include_prompt_body=True), "versionSnapshot": version.to_dict(include_prompt_body=True)},
    )
    db.commit()
    db.refresh(template)
    return {"code": 0, "data": {**template.to_dict(include_prompt_body=True), "versionId": version.id}, "message": "更新成功"}


@router.get("/prompt-templates/{template_id}/versions", summary="获取提示词模板版本历史")
async def list_prompt_template_versions(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    del current_user
    _ensure_prompt_templates_seeded(db)
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    items = db.query(PromptTemplateVersion).filter(PromptTemplateVersion.template_id == template_id).order_by(PromptTemplateVersion.id.desc()).all()
    return {"code": 0, "data": {"items": [item.to_dict(include_prompt_body=True) for item in items], "total": len(items)}}


@router.delete("/prompt-templates/{template_id}", summary="停用口播提示词模板")
async def delete_prompt_template(
    template_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    _ensure_prompt_templates_seeded(db)
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    before = template.to_dict(include_prompt_body=True)
    template.is_active = False
    template.is_default = False
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="prompt_template.disable",
        resource_type="prompt_template",
        resource_id=template.id,
        resource_key=template.key,
        before=before,
        after=template.to_dict(include_prompt_body=True),
    )
    db.commit()
    return {"code": 0, "message": "停用成功"}


@router.get("/model-configs", summary="获取后台大模型配置")
async def list_model_configs(
    model_type: str = "",
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    return {"code": 0, "data": _active_model_configs(db, current_user, model_type)}


@router.post("/model-configs", summary="创建后台大模型配置")
async def create_model_config(
    data: AIModelConfigCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    if data.is_default:
        db.query(AIModelConfig).filter(AIModelConfig.model_type == data.model_type).update(
            {AIModelConfig.is_default: False}, synchronize_session=False
        )
    payload = data.model_dump()
    payload["api_key"] = encrypt_secret(payload.get("api_key") or "")
    config = AIModelConfig(**payload)
    db.add(config)
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="model_config.create",
        resource_type="ai_model_config",
        resource_id=config.id,
        resource_key=config.name,
        after=config.to_dict(),
    )
    db.commit()
    db.refresh(config)
    return {"code": 0, "data": config.to_dict(), "message": "创建成功"}


@router.get("/model-configs/{config_id}", summary="获取后台大模型配置详情")
async def get_model_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    config = db.query(AIModelConfig).filter(AIModelConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return {"code": 0, "data": config.to_dict(include_secret=True)}


@router.put("/model-configs/{config_id}", summary="更新后台大模型配置")
async def update_model_config(
    config_id: int,
    data: AIModelConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    config = db.query(AIModelConfig).filter(AIModelConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    before = config.to_dict()
    if data.is_default:
        db.query(AIModelConfig).filter(
            AIModelConfig.model_type == data.model_type,
            AIModelConfig.id != config_id,
        ).update({AIModelConfig.is_default: False}, synchronize_session=False)
    payload = data.model_dump()
    payload["api_key"] = encrypt_secret(payload.get("api_key") or "")
    for key, value in payload.items():
        setattr(config, key, value)
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="model_config.update",
        resource_type="ai_model_config",
        resource_id=config.id,
        resource_key=config.name,
        before=before,
        after=config.to_dict(),
    )
    db.commit()
    db.refresh(config)
    return {"code": 0, "data": config.to_dict(), "message": "更新成功"}


@router.delete("/model-configs/{config_id}", summary="停用后台大模型配置")
async def delete_model_config(
    config_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    config = db.query(AIModelConfig).filter(AIModelConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    before = config.to_dict()
    config.is_active = False
    config.is_default = False
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="model_config.disable",
        resource_type="ai_model_config",
        resource_id=config.id,
        resource_key=config.name,
        before=before,
        after=config.to_dict(),
    )
    db.commit()
    return {"code": 0, "message": "停用成功"}


def _build_video_aip_plan_for_user(db: Session, data: VideoAipPlanRequest, current_user: UserAccount) -> dict:
    video_template = _prompt_template_by_id_or_key(db, data.video_prompt_template_id, template_type="video_clip")
    video_model_config = _model_config_by_id(db, data.video_model_config_id, user=current_user)
    if data.workflow_type == "drama":
        plan = _build_drama_aip_plan(data, video_template, video_model_config)
    elif data.workflow_type == "product_tvc":
        plan = _build_product_tvc_aip_plan(data, video_template, video_model_config)
    else:
        plan = _build_product_tvc_aip_plan(data, video_template, video_model_config)
        plan["workflow_type"] = "standard"
        plan["title"] = "标准视频提示词链路"
        plan["summary"] = "按脚本、分镜和最终视频提示词组织标准短视频生成链路。"
    return plan


@router.post("/video-aip/plan", summary="生成视频 AIP 链路计划")
async def generate_video_aip_plan(
    data: VideoAipPlanRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    plan = _build_video_aip_plan_for_user(db, data, current_user)
    return {"code": 0, "data": plan}


@router.post("/video-aip/projects", summary="创建视频 AIP 项目")
async def create_video_aip_project(
    data: VideoAipProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    _ensure_video_aip_source_allowed(db, data, current_user)
    plan = _build_video_aip_plan_for_user(db, data, current_user)
    project = _persist_video_aip_project(db, data, plan, current_user.id)
    return {"code": 0, "data": _video_aip_project_with_steps(db, project), "message": "创建成功"}


@router.post("/video-aip/projects/from-short-video/{short_video_project_id}", summary="从短视频工作流项目创建视频 AIP 项目")
async def create_video_aip_project_from_short_video(
    short_video_project_id: int,
    data: VideoAipBridgeCreateRequest = VideoAipBridgeCreateRequest(),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    source_project = db.query(ShortVideoProject).filter(
        ShortVideoProject.id == short_video_project_id,
        ShortVideoProject.user_id == current_user.id,
        ShortVideoProject.is_active == True,
    ).first()
    if not source_project:
        raise HTTPException(status_code=404, detail="短视频项目不存在或无权访问")

    workflow = _load_json(source_project.workflow_json, {})
    workflow_key = source_project.intent_key or (workflow.get("workflow") or {}).get("key") or ""
    workflow_type = _aip_workflow_type_from_short_video(workflow_key, data.workflow_type)
    source_text = _short_video_workflow_text(source_project, workflow)
    create_data = VideoAipProjectCreate(
        title=data.title.strip() or f"{source_project.title} · AIP执行链路",
        source_type="short_video_project",
        source_ref_id=source_project.id,
        workflow_type=workflow_type,
        source_content=source_project.user_input or source_project.core_message,
        script_content=source_text,
        product_name=source_project.subject_name if workflow_type == "product_tvc" else "",
        character_notes=source_project.subject_name if workflow_type == "drama" else "",
        media_notes=[source_project.notes] if source_project.notes else [],
        aspect_ratio=source_project.aspect_ratio or "9:16",
        duration=source_project.duration or "15秒",
        style=source_project.style or "高级、真实、有记忆点",
        user_requirements="从短视频工作流项目转入 Video AIP，请复用已生成的工作流步骤、脚本和分镜提示词。",
    )
    plan = _build_video_aip_plan_for_user(db, create_data, current_user)
    project = _persist_video_aip_project(db, create_data, plan, current_user.id)
    return {"code": 0, "data": _video_aip_project_with_steps(db, project), "message": "已从短视频工作流创建 AIP 项目"}


@router.post("/video-aip/projects/from-storyboard/{storyboard_id}", summary="从平台分镜记录创建视频 AIP 项目")
async def create_video_aip_project_from_storyboard(
    storyboard_id: int,
    data: VideoAipBridgeCreateRequest = VideoAipBridgeCreateRequest(),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    storyboard = db.query(StoryboardRecord).filter(
        StoryboardRecord.id == storyboard_id,
        StoryboardRecord.user_id == current_user.id,
        StoryboardRecord.is_active == True,
    ).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="分镜记录不存在或无权访问")

    frames = _load_json(storyboard.frames_json, [])
    assets = _load_json(storyboard.assets_json, [])
    workflow_type = _aip_workflow_type_from_storyboard(storyboard.storyboard_type, data.workflow_type)
    storyboard_text = _storyboard_record_text(storyboard, frames)
    create_data = VideoAipProjectCreate(
        title=data.title.strip() or f"{storyboard.title} · AIP执行链路",
        source_type="storyboard_record",
        source_ref_id=storyboard.id,
        workflow_type=workflow_type,
        source_content=storyboard_text,
        script_content=storyboard_text,
        product_name=storyboard.title if workflow_type == "product_tvc" else "",
        character_notes=storyboard.title if workflow_type == "drama" else "",
        media_notes=[f"分镜记录：{storyboard.title}"],
        source_assets=assets if isinstance(assets, list) else [],
        aspect_ratio="9:16",
        duration="15秒",
        style="高级、真实、有记忆点",
        user_requirements="从平台分镜记录转入 Video AIP，请优先复用既有分镜表和素材引用。",
    )
    plan = _build_video_aip_plan_for_user(db, create_data, current_user)
    project = _persist_video_aip_project(db, create_data, plan, current_user.id)
    return {"code": 0, "data": _video_aip_project_with_steps(db, project), "message": "已从分镜记录创建 AIP 项目"}


@router.get("/video-aip/projects", summary="获取视频 AIP 项目列表")
async def list_video_aip_projects(
    limit: int = 20,
    workflow_type: str = "",
    source_type: str = "",
    source_ref_id: int = 0,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    query = db.query(VideoAipProject).filter(VideoAipProject.user_id == current_user.id)
    if workflow_type:
        query = query.filter(VideoAipProject.workflow_type == workflow_type)
    if source_type:
        query = query.filter(VideoAipProject.source_type == source_type)
    if source_ref_id:
        query = query.filter(VideoAipProject.source_ref_id == source_ref_id)
    projects = query.order_by(VideoAipProject.created_at.desc()).limit(limit).all()
    items = []
    for project in projects:
        item = project.to_dict(include_plan=False)
        item["source"] = _video_aip_source_summary(db, project)
        items.append(item)
    return {"code": 0, "data": items}


@router.get("/video-aip/projects/{project_id}", summary="获取视频 AIP 项目详情")
async def get_video_aip_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    project = db.query(VideoAipProject).filter(
        VideoAipProject.id == project_id,
        VideoAipProject.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="视频 AIP 项目不存在")
    return {"code": 0, "data": _video_aip_project_with_steps(db, project)}


@router.post("/video-aip/projects/{project_id}/steps/{step_id}/run", summary="执行视频 AIP 步骤真实媒体任务")
async def run_video_aip_step(
    project_id: int,
    step_id: int,
    data: VideoAipStepRunRequest = VideoAipStepRunRequest(),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    _require_video_runtime_ready()
    project = db.query(VideoAipProject).filter(
        VideoAipProject.id == project_id,
        VideoAipProject.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="视频 AIP 项目不存在")
    step = db.query(VideoAipStepTask).filter(
        VideoAipStepTask.id == step_id,
        VideoAipStepTask.project_id == project_id,
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="视频 AIP 步骤不存在")
    record = _submit_video_aip_media_step(db, project, step, data)
    db.commit()
    db.refresh(project)
    return {
        "code": 0,
        "data": {
            "task": record.to_dict(),
            "project": _video_aip_project_with_steps(db, project),
        },
        "message": "真实媒体任务已提交",
    }


@router.post("/video-aip/projects/{project_id}/run-next", summary="执行视频 AIP 下一步")
async def run_next_video_aip_step(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    _require_video_runtime_ready()
    project = db.query(VideoAipProject).filter(
        VideoAipProject.id == project_id,
        VideoAipProject.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="视频 AIP 项目不存在")

    while True:
        step = _next_pending_or_failed_step(db, project_id)
        if not step:
            _refresh_video_aip_project_status(db, project_id)
            db.commit()
            db.refresh(project)
            return {"code": 0, "data": _video_aip_project_with_steps(db, project), "message": "没有待执行步骤"}
        try:
            record = _submit_video_aip_media_step(db, project, step, VideoAipStepRunRequest())
            db.commit()
            db.refresh(project)
            return {
                "code": 0,
                "data": {"task": record.to_dict(), "project": _video_aip_project_with_steps(db, project)},
                "message": "下一步真实媒体任务已提交",
            }
        except HTTPException as exc:
            if "文本编排步骤" not in str(exc.detail):
                raise
            await _generate_video_aip_text_step(db, project, step)
            db.commit()


@router.post("/video-aip/projects/{project_id}/run-all", summary="从当前进度执行视频 AIP 全部步骤")
async def run_all_video_aip_steps(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    _require_video_runtime_ready()
    project = db.query(VideoAipProject).filter(
        VideoAipProject.id == project_id,
        VideoAipProject.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="视频 AIP 项目不存在")
    next_step = _next_pending_or_failed_step(db, project_id)
    if next_step:
        try:
            defaults = _step_execution_defaults(project, next_step, VideoAipStepRunRequest())
            _require_media_workflow_credentials(defaults["workflow"])
        except HTTPException as exc:
            if "文本编排步骤" not in str(exc.detail):
                raise
    project.status = "running"
    db.commit()
    asyncio.create_task(_run_video_aip_project_sequence(project_id), name=f"video-aip-run-all-{project_id}")
    db.refresh(project)
    return {"code": 0, "data": _video_aip_project_with_steps(db, project), "message": "已开始后台顺序执行全部 AIP 步骤"}


@router.post("/video-aip/projects/{project_id}/steps/{step_id}/retry", summary="重试视频 AIP 步骤")
async def retry_video_aip_step(
    project_id: int,
    step_id: int,
    data: VideoAipStepRunRequest = VideoAipStepRunRequest(),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    _require_video_runtime_ready()
    project = db.query(VideoAipProject).filter(
        VideoAipProject.id == project_id,
        VideoAipProject.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="视频 AIP 项目不存在")
    step = db.query(VideoAipStepTask).filter(
        VideoAipStepTask.id == step_id,
        VideoAipStepTask.project_id == project_id,
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="视频 AIP 步骤不存在")
    old_output = _load_json(step.output_json, {})
    retry_history = old_output.get("retry_history") or []
    if old_output.get("task_id"):
        retry_history.append({
            "task_id": old_output.get("task_id"),
            "status": step.status,
            "error_message": step.error_message,
            "media_url": old_output.get("media_url"),
            "retried_at": datetime.utcnow().isoformat(),
        })
    preserved = {
        key: value for key, value in old_output.items()
        if key in {"task_type", "artifact_type", "default_media_type", "default_width", "default_height"}
    }
    step.output_json = json.dumps({**preserved, "retry_history": retry_history}, ensure_ascii=False)
    step.status = "pending"
    step.error_message = ""
    record = _submit_video_aip_media_step(db, project, step, data)
    db.commit()
    db.refresh(project)
    return {
        "code": 0,
        "data": {"task": record.to_dict(), "project": _video_aip_project_with_steps(db, project)},
        "message": "已重试并提交真实媒体任务",
    }


@router.put("/video-aip/projects/{project_id}/steps/{step_id}", summary="更新视频 AIP 步骤状态")
async def update_video_aip_step_status(
    project_id: int,
    step_id: int,
    data: VideoAipStepStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    project = db.query(VideoAipProject).filter(
        VideoAipProject.id == project_id,
        VideoAipProject.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="视频 AIP 项目不存在")
    step = db.query(VideoAipStepTask).filter(
        VideoAipStepTask.id == step_id,
        VideoAipStepTask.project_id == project_id,
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="视频 AIP 步骤不存在")
    if data.status not in {"pending", "running", "succeeded", "failed"}:
        raise HTTPException(status_code=400, detail="步骤状态不合法")
    step.status = data.status
    step.output_json = json.dumps(data.output, ensure_ascii=False)
    step.error_message = data.error_message
    project.current_step_key = step.step_key
    if data.status == "running":
        project.status = "running"
    elif data.status == "failed":
        project.status = "failed"
    else:
        all_steps = db.query(VideoAipStepTask).filter(VideoAipStepTask.project_id == project_id).all()
        if all(item.id == step.id or item.status == "succeeded" for item in all_steps) and data.status == "succeeded":
            project.status = "succeeded"
    db.commit()
    db.refresh(project)
    return {"code": 0, "data": _video_aip_project_with_steps(db, project), "message": "更新成功"}


@router.post("/generate", summary="一键生成口播文案 + 视频提示词 + 封面提示词")
async def generate_full_case(
    data: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """核心生成接口：依次生成口播文案、视频分镜提示词、封面提示词"""

    # 获取 IP 人设与栏目策略
    persona_profile = _persona_profile(db, data.persona_id)
    column_profile = _column_profile(db, data.column_id)
    prompt_template = _prompt_template_by_id_or_key(db, data.prompt_template_id, data.prompt_template_key, "text_script")
    cover_template = _prompt_template_by_id_or_key(db, data.cover_prompt_template_id, template_type="image_cover")
    video_template = _prompt_template_by_id_or_key(db, data.video_prompt_template_id, template_type="video_clip")
    text_model_config = _model_config_by_id(db, data.text_model_config_id, user=current_user) or _default_model_config(db, "text")
    cover_model_config = _model_config_by_id(db, data.cover_model_config_id, user=current_user) or _default_model_config(db, "image")
    video_model_config = _model_config_by_id(db, data.video_model_config_id, user=current_user) or _default_model_config(db, "video")
    prompt_template_profile = _prompt_template_profile(db, prompt_template, data.prompt_template_category)
    prompt_template_category = prompt_template["category_key"] if prompt_template else data.prompt_template_category
    cover_template_profile = _prompt_template_profile(db, cover_template)
    video_template_profile = _prompt_template_profile(db, video_template)
    model_snapshot = {
        "text_model": text_model_config.to_dict() if text_model_config else None,
        "cover_model": cover_model_config.to_dict() if cover_model_config else None,
        "video_model": video_model_config.to_dict() if video_model_config else None,
    }
    template_snapshot = {
        "text_script": _prompt_template_snapshot(prompt_template),
        "image_cover": _prompt_template_snapshot(cover_template),
        "video_clip": _prompt_template_snapshot(video_template),
    }
    strategy_requirements = "\n".join([
        data.extra_requirements or "无",
        "",
        "## 口播提示词模板",
        prompt_template_profile,
        "",
        "## 文案模型",
        text_model_config.name if text_model_config else "未选择，使用系统默认文本模型",
        "",
        "## 栏目策略",
        column_profile,
    ])

    ai = AIService(module_code="ip_system", db_session=db)

    # ── 步骤1：生成口播文案 ──
    script_messages = [
        {"role": "system", "content": GENERATE_SCRIPT_SYSTEM},
        {"role": "user", "content": GENERATE_SCRIPT_USER.format(
             extracted_content=data.extracted_content,
             persona_profile=persona_profile,
             extra_requirements=strategy_requirements,
        )},
    ]
    try:
        script_response = await _chat_with_optional_model_config(
            ai,
            text_model_config,
            script_messages,
            prompt_name="generate_script",
        )
        script_content = script_response.content

        # ── 步骤2：生成视频分镜提示词 ──
        video_messages = [
            {"role": "system", "content": GENERATE_VIDEO_PROMPTS_SYSTEM},
            {"role": "user", "content": GENERATE_VIDEO_PROMPTS_USER.format(
                script_content=script_content,
                target_platform=data.target_platform,
                style_preferences="\n".join([
                    data.extra_requirements or "电影级质感，专业配色",
                    f"视频比例：{data.video_aspect_ratio}",
                    f"视频时长：{data.video_duration}",
                    f"视频链路：{data.video_workflow_type}",
                    "视频提示词模板：",
                    video_template_profile,
                    "视频模型：" + (video_model_config.name if video_model_config else "未选择，使用系统默认文本模型生成视频提示词"),
                ]),
            )},
        ]
        video_response = await _chat_with_optional_model_config(
            ai,
            video_model_config if video_model_config and video_model_config.model_type in ["text", "multimodal"] else None,
            video_messages,
            prompt_name="generate_video_prompts",
        )
        video_prompts = video_response.content

        # ── 步骤3：生成封面提示词 ──
        cover_messages = [
            {"role": "system", "content": GENERATE_COVER_SYSTEM},
            {"role": "user", "content": GENERATE_COVER_USER.format(
                script_content=script_content,
                target_platform=data.target_platform,
                cover_style="\n".join([
                    data.cover_style or "竖版9:16，科技感",
                    f"封面比例：{data.cover_aspect_ratio}",
                    f"封面标题：{data.cover_title or '由脚本自动提炼'}",
                    "封面提示词模板：",
                    cover_template_profile,
                    "封面模型：" + (cover_model_config.name if cover_model_config else "未选择，使用系统默认文本模型生成封面提示词"),
                ]),
            )},
        ]
        cover_response = await _chat_with_optional_model_config(
            ai,
            cover_model_config if cover_model_config and cover_model_config.model_type in ["text", "multimodal"] else None,
            cover_messages,
            prompt_name="generate_cover_prompt",
        )
        cover_prompt = cover_response.content
    except Exception as e:
        raise _ai_unavailable_error(e, "一键生成全案")

    # ── 保存生成记录 ──
    history = GenerationHistory(
        title=data.extracted_content[:50] + "...",
        source_type="text",
        source_content=data.extracted_content[:500],
        extracted_content=data.extracted_content,
        persona_id=data.persona_id,
        script_content=script_content,
        video_prompts=video_prompts,
        cover_prompt=cover_prompt,
        target_platform=data.target_platform,
        prompt_template_id=prompt_template["id"] if prompt_template else data.prompt_template_id,
        prompt_template_key=prompt_template["key"] if prompt_template else data.prompt_template_key,
        prompt_template_version=prompt_template["version"] if prompt_template else "",
        prompt_template_category=prompt_template_category or "",
        text_model_config_id=text_model_config.id if text_model_config else data.text_model_config_id,
        cover_prompt_template_id=cover_template["id"] if cover_template else data.cover_prompt_template_id,
        cover_model_config_id=cover_model_config.id if cover_model_config else data.cover_model_config_id,
        video_prompt_template_id=video_template["id"] if video_template else data.video_prompt_template_id,
        video_model_config_id=video_model_config.id if video_model_config else data.video_model_config_id,
        generation_params_json=json.dumps({
            "cover_aspect_ratio": data.cover_aspect_ratio,
            "cover_title": data.cover_title,
            "video_aspect_ratio": data.video_aspect_ratio,
            "video_duration": data.video_duration,
            "video_workflow_type": data.video_workflow_type,
            "models": model_snapshot,
            "templates": template_snapshot,
        }, ensure_ascii=False),
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "code": 0,
        "data": {
            "history_id": history.id,
            "script_content": script_content,
            "video_prompts": video_prompts,
            "cover_prompt": cover_prompt,
            "prompt_template": template_snapshot["text_script"],
            "cover_prompt_template": template_snapshot["image_cover"],
            "video_prompt_template": template_snapshot["video_clip"],
            "model_snapshot": model_snapshot,
            "template_snapshot": template_snapshot,
            "prompt_template_id": history.prompt_template_id,
            "prompt_template_key": history.prompt_template_key,
            "prompt_template_version": history.prompt_template_version,
            "prompt_template_category": history.prompt_template_category,
        }
    }


@router.post("/generation-events", summary="记录生成后行为事件")
async def create_generation_action_event(
    data: GenerationActionEventCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    if data.event_type not in {"edited", "saved", "teleprompter_opened"}:
        raise HTTPException(status_code=400, detail="事件类型不支持")
    history = db.query(GenerationHistory).filter(GenerationHistory.id == data.history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="生成历史不存在")
    event = GenerationActionEvent(
        user_id=current_user.id,
        history_id=data.history_id,
        event_type=data.event_type,
        content_type=data.content_type,
        metadata_json=json.dumps(data.metadata or {}, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"code": 0, "data": event.to_dict(), "message": "事件已记录"}


# ─── 2.5 栏目库与策略能力 ─────────────────────────────────────

@router.get("/columns", summary="获取栏目库")
async def list_columns(persona_id: int = 0, db: Session = Depends(get_db)):
    query = db.query(ContentColumn).filter(ContentColumn.is_active == True)
    if persona_id:
        query = query.filter(ContentColumn.persona_id.in_([0, persona_id]))
    columns = query.order_by(ContentColumn.sort_order, ContentColumn.id).all()
    return {"code": 0, "data": [c.to_dict() for c in columns]}


@router.post("/columns", summary="创建栏目")
async def create_column(data: ColumnCreate, db: Session = Depends(get_db)):
    column = ContentColumn(**data.model_dump())
    db.add(column)
    db.commit()
    db.refresh(column)
    return {"code": 0, "data": column.to_dict(), "message": "创建成功"}


@router.put("/columns/{column_id}", summary="更新栏目")
async def update_column(column_id: int, data: ColumnUpdate, db: Session = Depends(get_db)):
    column = db.query(ContentColumn).filter(ContentColumn.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="栏目不存在")
    for key, value in data.model_dump().items():
        setattr(column, key, value)
    db.commit()
    db.refresh(column)
    return {"code": 0, "data": column.to_dict(), "message": "更新成功"}


@router.delete("/columns/{column_id}", summary="删除栏目")
async def delete_column(column_id: int, db: Session = Depends(get_db)):
    column = db.query(ContentColumn).filter(ContentColumn.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="栏目不存在")
    column.is_active = False
    db.commit()
    return {"code": 0, "message": "删除成功"}


@router.post("/strategy/topics", summary="生成选题策划")
async def generate_topic_plan(data: TopicPlanRequest, db: Session = Depends(get_db)):
    try:
        result = await _json_ai_response(
            [
                {"role": "system", "content": GENERATE_TOPICS_SYSTEM},
                {"role": "user", "content": GENERATE_TOPICS_USER.format(
                    count=data.count,
                    persona_profile=_persona_profile(db, data.persona_id),
                    column_profile=_column_profile(db, data.column_id),
                    extracted_content=data.extracted_content,
                    extra_requirements=data.extra_requirements or "无",
                )},
            ],
            prompt_name="generate_topics",
            db=db,
            temperature=0.85,
            default={"topics": []},
        )
    except AIProviderError as e:
        raise _ai_unavailable_error(e, "生成选题策划")
    return {"code": 0, "data": result}


@router.post("/strategy/hooks", summary="优化黄金3秒开头")
async def optimize_hooks(data: HookOptimizeRequest, db: Session = Depends(get_db)):
    try:
        result = await _json_ai_response(
            [
                {"role": "system", "content": OPTIMIZE_HOOKS_SYSTEM},
                {"role": "user", "content": OPTIMIZE_HOOKS_USER.format(
                    count=data.count,
                    persona_profile=_persona_profile(db, data.persona_id),
                    column_profile=_column_profile(db, data.column_id),
                    script_content=data.script_content,
                )},
            ],
            prompt_name="optimize_hooks",
            db=db,
            temperature=0.85,
            default={"hooks": []},
        )
    except AIProviderError as e:
        raise _ai_unavailable_error(e, "优化黄金3秒开头")
    return {"code": 0, "data": result}


@router.post("/strategy/publish-package", summary="生成发布全案")
async def generate_publish_package(data: PublishPackageRequest, db: Session = Depends(get_db)):
    try:
        result = await _json_ai_response(
            [
                {"role": "system", "content": GENERATE_PUBLISH_PACKAGE_SYSTEM},
                {"role": "user", "content": GENERATE_PUBLISH_PACKAGE_USER.format(
                    persona_profile=_persona_profile(db, data.persona_id),
                    column_profile=_column_profile(db, data.column_id),
                    script_content=data.script_content,
                    cover_prompt=data.cover_prompt or "无",
                    target_platform=data.target_platform,
                )},
            ],
            prompt_name="generate_publish_package",
            db=db,
            temperature=0.75,
            default={},
        )
    except AIProviderError as e:
        raise _ai_unavailable_error(e, "生成发布全案")
    return {"code": 0, "data": result}


@router.post("/strategy/quality-check", summary="发布前质检")
async def quality_check(data: QualityCheckRequest, db: Session = Depends(get_db)):
    try:
        result = await _json_ai_response(
            [
                {"role": "system", "content": QUALITY_CHECK_SYSTEM},
                {"role": "user", "content": QUALITY_CHECK_USER.format(
                    persona_profile=_persona_profile(db, data.persona_id),
                    column_profile=_column_profile(db, data.column_id),
                    script_content=data.script_content,
                    cover_prompt=data.cover_prompt or "无",
                    publish_copy=data.publish_copy or "无",
                )},
            ],
            prompt_name="quality_check",
            db=db,
            temperature=0.45,
            default={},
        )
    except AIProviderError as e:
        raise _ai_unavailable_error(e, "发布前质检")
    return {"code": 0, "data": result}


# ─── 3. Copilot 流式对话修改 ─────────────────────────────────

@router.post("/modify", summary="Copilot 对话修改（流式输出）")
async def copilot_modify(data: ModifyRequest, db: Session = Depends(get_db)):
    """用户在右侧对话框输入自然语言指令，AI 流式返回修改后的完整内容"""

    # 获取 IP 人设
    persona_profile = "无特定人设"
    if data.persona_id:
        persona = db.query(Persona).filter(Persona.id == data.persona_id).first()
        if persona:
            persona_profile = persona.to_profile_text()

    content_type_map = {
        "script": "口播文案",
        "video_prompts": "视频分镜提示词",
        "cover_prompt": "视频封面提示词",
        "reversal_drama": "短剧分镜脚本",
    }
    content_type_label = content_type_map.get(data.content_type, data.content_type)

    extra_context = ""
    if data.content_type == "reversal_drama":
        bits = []
        if data.template_key:
            bits.append(f"剧本类型：{data.template_key}")
        if data.cast_summary:
            bits.append(f"角色组：{data.cast_summary}")
        if bits:
            extra_context = "\n\n## 当前剧本上下文\n" + "\n".join(bits)

    user_instruction = data.user_instruction + extra_context

    messages = [
        {"role": "system", "content": COPILOT_MODIFY_SYSTEM},
        {"role": "user", "content": COPILOT_MODIFY_USER.format(
            content_type=content_type_label,
            current_content=data.current_content,
            persona_profile=persona_profile,
            user_instruction=user_instruction,
        )},
    ]

    ai = AIService(module_code="ip_system", db_session=db)

    async def stream_generator():
        async for chunk in ai.chat_stream(messages, prompt_name="copilot_modify"):
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── 4. 历史记录 ────────────────────────────────────────────

@router.get("/history", summary="获取生成历史")
async def list_history(limit: int = 20, db: Session = Depends(get_db)):
    records = (
        db.query(GenerationHistory)
        .order_by(GenerationHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"code": 0, "data": [r.to_dict() for r in records]}


@router.get("/history/{history_id}", summary="获取单条历史详情")
async def get_history(history_id: int, db: Session = Depends(get_db)):
    record = db.query(GenerationHistory).filter(GenerationHistory.id == history_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"code": 0, "data": record.to_dict()}


# ─── 5. 职场反转剧编剧 ─────────────────────────────────────────


def _parse_reversal_drama_markdown(md: str) -> dict:
    """将 AI 输出的 Markdown 切成结构化字段。

    解析失败的部分会以空值填充，前端仍可渲染 raw_markdown 兜底。
    """
    # —— 1. 剧本概览 —— 抓取「一、剧本概览」到下一节之间的 - **xx**：yy 行
    overview: dict = {}
    overview_match = re.search(
        r"##\s*一[、.\s]*剧本概览\s*(.+?)(?=##\s*二[、.\s])",
        md, re.DOTALL,
    )
    if overview_match:
        for line in overview_match.group(1).splitlines():
            kv = re.match(r"\s*[-*]\s*\*\*(.+?)\*\*[：:]\s*(.+?)\s*$", line)
            if kv:
                key = kv.group(1).strip()
                val = kv.group(2).strip()
                key_map = {
                    "标题": "title",
                    "时长预估": "duration",
                    "痛点": "pain_point",
                    "推销产品": "product",
                    "反转套路": "reversal_type",
                    "出场人物": "characters",
                }
                if key in key_map:
                    overview[key_map[key]] = val

    # —— 2. 分镜表 —— 抓取 markdown table 数据行（含 | 且不全是 :--: / --- ）
    scenes: list[dict] = []
    scenes_match = re.search(
        r"##\s*二[、.\s]*分镜表\s*(.+?)(?=##\s*三[、.\s])",
        md, re.DOTALL,
    )
    if scenes_match:
        for line in scenes_match.group(1).splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 5:
                continue
            # 跳过表头与分隔行
            if cells[0] in ("镜号", "Shot", "#"):
                continue
            if re.fullmatch(r":?-+:?", cells[0]):
                continue
            # 镜号必须是数字
            shot_match = re.search(r"\d+", cells[0])
            if not shot_match:
                continue
            scenes.append({
                "shot": int(shot_match.group(0)),
                "duration": cells[1],
                "visual": cells[2],
                "dialogue": cells[3],
                "bgm": cells[4],
            })

    # —— 3. 结尾字幕 —— 抓加粗那一行
    ending = ""
    ending_match = re.search(
        r"##\s*三[、.\s]*结尾字幕\s*(.+?)(?=##\s*四[、.\s])",
        md, re.DOTALL,
    )
    if ending_match:
        body = ending_match.group(1).strip()
        bold = re.search(r"\*\*(.+?)\*\*", body)
        ending = bold.group(1).strip() if bold else body.splitlines()[0].strip() if body else ""

    # —— 4. 自检清单 —— 抓 - [x] / - [ ] 行
    checklist: list[dict] = []
    checklist_match = re.search(
        r"##\s*四[、.\s]*自检清单\s*(.+?)$",
        md, re.DOTALL,
    )
    if checklist_match:
        for line in checklist_match.group(1).splitlines():
            m = re.match(r"\s*[-*]\s*\[([ xX])\]\s*(.+?)\s*$", line)
            if m:
                checklist.append({
                    "item": m.group(2).strip(),
                    "passed": m.group(1).lower() == "x",
                })

    return {
        "overview": overview,
        "scenes": scenes,
        "ending_subtitle": ending,
        "checklist": checklist,
    }


def _resolve_reversal_characters(
    db: Session,
    data: ReversalDramaRequest,
    current_user: UserAccount,
) -> tuple[list[dict], list[dict], str]:
    """解析最终角色列表、快照与关系说明。"""
    template = get_drama_template(db, data.template_key or "workplace_reversal")
    relationship_hint = template.get("relationship_hint", "")
    cast_snapshot: list[dict] = []

    if data.characters and any((c.name or "").strip() for c in data.characters):
        cast_snapshot = [c.model_dump() for c in data.characters if (c.name or "").strip()]
        return cast_snapshot, cast_snapshot, relationship_hint

    if data.cast_preset_id:
        preset = (
            db.query(DramaCastPreset)
            .filter(
                DramaCastPreset.id == data.cast_preset_id,
                DramaCastPreset.user_id == current_user.id,
                DramaCastPreset.is_active.is_(True),
            )
            .first()
        )
        if preset:
            try:
                cast_snapshot = json.loads(preset.characters_json or "[]")
            except Exception:
                cast_snapshot = []
            if cast_snapshot:
                relationship_hint = preset.relationship_hint or relationship_hint
                return cast_snapshot, cast_snapshot, relationship_hint

    return [], [], relationship_hint


@router.get("/drama-templates", summary="获取短剧剧本类型模板列表")
async def list_drama_script_templates(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    _ = current_user
    return {"code": 0, "data": list_drama_templates(db)}


@router.get("/drama-casts", summary="获取当前用户角色组预设")
async def list_drama_cast_presets(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    records = (
        db.query(DramaCastPreset)
        .filter(DramaCastPreset.user_id == current_user.id, DramaCastPreset.is_active.is_(True))
        .order_by(DramaCastPreset.is_default.desc(), DramaCastPreset.updated_at.desc())
        .all()
    )
    return {"code": 0, "data": [record.to_dict() for record in records]}


@router.post("/drama-casts", summary="创建角色组预设")
async def create_drama_cast_preset(
    data: DramaCastPresetPayload,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    characters = [c.model_dump() for c in data.characters if (c.name or "").strip()]
    if not characters:
        raise HTTPException(status_code=400, detail="请至少填写一个有效角色")
    if len(characters) > 6:
        raise HTTPException(status_code=400, detail="角色组最多 6 人")

    if data.is_default:
        db.query(DramaCastPreset).filter(
            DramaCastPreset.user_id == current_user.id,
            DramaCastPreset.is_default.is_(True),
        ).update({"is_default": False})

    record = DramaCastPreset(
        user_id=current_user.id,
        name=data.name.strip(),
        project_id=data.project_id,
        characters_json=json.dumps(characters, ensure_ascii=False),
        relationship_hint=data.relationship_hint.strip(),
        is_default=data.is_default,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"code": 0, "data": record.to_dict(), "message": "角色组已保存"}


@router.put("/drama-casts/{cast_id}", summary="更新角色组预设")
async def update_drama_cast_preset(
    cast_id: int,
    data: DramaCastPresetPayload,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    record = db.query(DramaCastPreset).filter(
        DramaCastPreset.id == cast_id,
        DramaCastPreset.user_id == current_user.id,
        DramaCastPreset.is_active.is_(True),
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="角色组不存在")

    characters = [c.model_dump() for c in data.characters if (c.name or "").strip()]
    if not characters:
        raise HTTPException(status_code=400, detail="请至少填写一个有效角色")
    if len(characters) > 6:
        raise HTTPException(status_code=400, detail="角色组最多 6 人")

    if data.is_default:
        db.query(DramaCastPreset).filter(
            DramaCastPreset.user_id == current_user.id,
            DramaCastPreset.is_default.is_(True),
            DramaCastPreset.id != cast_id,
        ).update({"is_default": False})

    record.name = data.name.strip()
    record.project_id = data.project_id
    record.characters_json = json.dumps(characters, ensure_ascii=False)
    record.relationship_hint = data.relationship_hint.strip()
    record.is_default = data.is_default
    db.commit()
    db.refresh(record)
    return {"code": 0, "data": record.to_dict(), "message": "角色组已更新"}


@router.delete("/drama-casts/{cast_id}", summary="删除角色组预设")
async def delete_drama_cast_preset(
    cast_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    record = db.query(DramaCastPreset).filter(
        DramaCastPreset.id == cast_id,
        DramaCastPreset.user_id == current_user.id,
        DramaCastPreset.is_active.is_(True),
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="角色组不存在")
    record.is_active = False
    db.commit()
    return {"code": 0, "message": "角色组已删除"}


@router.post("/reversal-drama/generate", summary="生成短剧分镜脚本")
async def generate_reversal_drama(
    data: ReversalDramaRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """短剧脚本工坊 - 同步生成。

    输入：剧本类型 + 产品 + 痛点 + (可选)角色组
    输出：raw_markdown + 结构化的 overview / scenes / ending_subtitle / checklist
    """
    template_key = data.template_key or "workplace_reversal"
    template = get_drama_template(db, template_key)
    pattern = (data.reversal_pattern or "auto").upper()
    if pattern not in {"AUTO", "A", "B", "C"}:
        pattern = "AUTO"
    pattern_key = "auto" if pattern == "AUTO" else pattern

    characters, cast_snapshot, relationship_hint = _resolve_reversal_characters(db, data, current_user)
    characters_block = build_cast_block(
        characters or None,
        default_cast_prompt=template.get("default_cast_prompt", ""),
        relationship_hint=relationship_hint,
        template_key=template_key,
    )
    reversal_instruction = build_reversal_pattern_instruction(
        template.get("reversal_patterns", []),
        pattern_key,
    )
    system_prompt = build_drama_system_prompt(
        template,
        characters_block=characters_block,
        reversal_pattern_instruction=reversal_instruction,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": REVERSAL_DRAMA_USER.format(
            product_name=data.product_name,
            product_function=data.product_function,
            pain_point=data.pain_point,
            characters_block=characters_block,
            platform=data.platform or "视频号+抖音",
            duration=data.duration or "30-60秒",
            reversal_pattern_instruction=reversal_instruction,
            extra_requirements=data.extra_requirements or "无",
        )},
    ]

    ai = AIService(module_code="ip_system", db_session=db)
    try:
        response = await ai.chat(
            messages,
            prompt_name="generate_reversal_drama",
            temperature=0.85,
            max_tokens=4096,
        )
    except AIProviderError as e:
        raise _ai_unavailable_error(e, "反转剧生成")

    raw_markdown = response.content or ""
    structured = _parse_reversal_drama_markdown(raw_markdown)

    # —— 保存生成记录 ——
    title = (structured.get("overview", {}).get("title")
             or f"{data.product_name} · 反转剧")
    result = {
        "history_id": 0,
        "template_key": template_key,
        "template_name": template.get("name", ""),
        "reversal_pattern": pattern_key,
        "cast_snapshot": cast_snapshot,
        "raw_markdown": raw_markdown,
        **structured,
    }

    reversal_history = ReversalDramaHistory(
        user_id=current_user.id,
        title=title[:200],
        product_name=data.product_name[:200],
        pain_point=data.pain_point,
        params_json=json.dumps(data.model_dump(), ensure_ascii=False),
        result_json=json.dumps(result, ensure_ascii=False),
        raw_markdown=raw_markdown,
    )
    db.add(reversal_history)
    db.flush()

    history = GenerationHistory(
        title=title[:200],
        source_type="reversal_drama",
        source_content=json.dumps(data.model_dump(), ensure_ascii=False)[:2000],
        extracted_content=data.pain_point[:500],
        persona_id=0,
        script_content=raw_markdown,
        video_prompts="",
        cover_prompt="",
        target_platform=data.platform,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    db.refresh(reversal_history)
    result["history_id"] = reversal_history.id
    reversal_history.result_json = json.dumps(result, ensure_ascii=False)
    db.commit()

    return {
        "code": 0,
        "data": result,
    }


@router.get("/reversal-drama/history", summary="获取当前用户反转剧历史")
async def list_reversal_drama_history(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    limit = max(1, min(limit, 100))
    records = (
        db.query(ReversalDramaHistory)
        .filter(ReversalDramaHistory.user_id == current_user.id)
        .order_by(ReversalDramaHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"code": 0, "data": [record.to_dict() for record in records]}


@router.delete("/reversal-drama/history/{history_id}", summary="删除当前用户反转剧历史")
async def delete_reversal_drama_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    record = db.query(ReversalDramaHistory).filter(
        ReversalDramaHistory.id == history_id,
        ReversalDramaHistory.user_id == current_user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    db.delete(record)
    db.commit()
    return {"code": 0, "message": "删除成功"}


@router.delete("/reversal-drama/history", summary="清空当前用户反转剧历史")
async def clear_reversal_drama_history(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    db.query(ReversalDramaHistory).filter(ReversalDramaHistory.user_id == current_user.id).delete()
    db.commit()
    return {"code": 0, "message": "清空成功"}
