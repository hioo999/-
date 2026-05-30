"""Copilot 工作台核心 API

提供：内容解析、一键生成全案、流式对话修改 三大核心接口。
"""

import json
import logging
import re
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from api.auth_routes import get_admin_user, get_current_user
from models.persona import (
    Persona,
    GenerationHistory,
    ContentColumn,
    PromptTemplateCategory,
    PromptTemplate,
    ReversalDramaHistory,
    UserAccount,
    AdminOperationLog,
    AIModelConfig,
)
from services.ai_service import AIProviderError, AIService, safe_parse_ai_json
from services.content_parser import extract_from_url, extract_from_text, extract_from_file
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
    REVERSAL_DRAMA_SYSTEM, REVERSAL_DRAMA_USER, build_characters_block,
)

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
    content_type: str = Field(..., description="内容类型：script/video_prompts/cover_prompt")
    current_content: str = Field(..., description="当前内容")
    user_instruction: str = Field(..., description="用户修改指令")
    persona_id: int = Field(0, description="IP 人设 ID")


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
    aspect_ratio: str = Field("9:16", description="视频比例")
    duration: str = Field("15秒", description="视频时长")
    style: str = Field("高级、真实、有记忆点", description="画面风格")
    user_requirements: str = Field("", description="用户补充要求")
    video_prompt_template_id: int = Field(0, description="视频模板 ID")
    video_model_config_id: int = Field(0, description="视频模型配置 ID")


class ReversalCharacter(BaseModel):
    name: str = Field("", description="人物名字")
    gender: str = Field("", description="性别")
    role: str = Field("", description="岗位/身份")
    personality: str = Field("", description="性格底色")
    catchphrase: str = Field("", description="口头禅")


class ReversalDramaRequest(BaseModel):
    product_name: str = Field(..., description="推销产品名")
    product_function: str = Field(..., description="产品一句话功能")
    pain_point: str = Field(..., description="要打的痛点")
    characters: Optional[list[ReversalCharacter]] = Field(
        None, description="自定义人物，留空走默认铁三角（农总+淇淇+海鸥）"
    )
    platform: str = Field("视频号+抖音", description="发布平台")
    duration: str = Field("30-60秒", description="时长偏好")
    extra_requirements: str = Field("", description="额外要求")


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
            continue
        data = {key: value for key, value in template_data.items() if key not in ["id", "writing_rules"]}
        data["writing_rules_json"] = json.dumps(template_data.get("writing_rules") or [], ensure_ascii=False)
        data.setdefault("prompt_body", "")
        db.add(PromptTemplate(**data))
    db.commit()


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


def _active_prompt_templates(db: Session, category_key: str = "", template_type: str = "") -> list[dict]:
    try:
        _ensure_prompt_templates_seeded(db)
        query = db.query(PromptTemplate).filter(PromptTemplate.is_active == True)
        if category_key:
            query = query.filter(PromptTemplate.category_key == category_key)
        if template_type:
            query = query.filter(PromptTemplate.template_type == template_type)
        templates = query.order_by(PromptTemplate.sort_order, PromptTemplate.id).all()
        return [template.to_dict() for template in templates]
    except Exception as exc:
        db.rollback()
        logger.warning("读取提示词模板失败，使用静态默认配置: %s", exc)
        templates = [template for template in PROMPT_TEMPLATES if template.get("is_active", True)]
        if category_key:
            templates = [template for template in templates if template["category_key"] == category_key]
        if template_type:
            templates = [template for template in templates if template.get("template_type", "text_script") == template_type]
        return sorted(templates, key=lambda item: item["sort_order"])


def _prompt_template_by_id_or_key(db: Session, template_id: int = 0, template_key: str = "", template_type: str = "") -> Optional[dict]:
    for template in _active_prompt_templates(db, template_type=template_type):
        if template_id and template["id"] == template_id:
            return template
        if template_key and template["key"] == template_key:
            return template
    return None


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


def _active_model_configs(db: Session, model_type: str = "") -> list[dict]:
    query = db.query(AIModelConfig).filter(AIModelConfig.is_active == True)
    if model_type:
        query = query.filter(AIModelConfig.model_type.in_([model_type, "multimodal"]))
    configs = query.order_by(AIModelConfig.sort_order, AIModelConfig.id).all()
    return [config.to_dict() for config in configs]


def _model_config_by_id(db: Session, config_id: int = 0) -> Optional[AIModelConfig]:
    if not config_id:
        return None
    return db.query(AIModelConfig).filter(
        AIModelConfig.id == config_id,
        AIModelConfig.is_active == True,
    ).first()


async def _chat_with_optional_model_config(
    ai: AIService,
    model_config: Optional[AIModelConfig],
    messages: list,
    prompt_name: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    if model_config and model_config.api_key and model_config.base_url and model_config.model_id:
        return await ai._call_provider(
            base_url=model_config.base_url.rstrip("/"),
            api_key=model_config.api_key,
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
            "prompt": f"""请基于用户上传的产品图，清理出完整产品主体图。
主体：{product_name}
要求：保留完整包装轮廓、Logo、标签文字、材质反光和颜色；背景干净；产品不能变形。
一致性约束：{consistency}
素材理解：{base_context}
输出：主体清理提示词、负面提示词、适合继续生成三视图/四视图的参考图说明。""",
        },
        {
            "key": "multi_view",
            "title": "第 2 步：三视图 / 四视图",
            "goal": "生成产品正面、侧面、背面和细节视图，锁定产品一致性。",
            "prompt": f"""根据已清理的产品主体图，为 {product_name} 生成产品四视图提示词。
视图：正面、45度侧面、背面、包装/材质细节特写。
比例：1:1 或 4:5，背景统一为高级棚拍浅色背景。
一致性约束：{consistency}
输出：每个视图的画面描述、镜头角度、光线、禁止事项。""",
        },
        {
            "key": "storyboard_grid",
            "title": "第 3 步：九宫格 / 三十六宫格分镜",
            "goal": "把产品卖点、情绪和转化路径拆成连续镜头。",
            "prompt": f"""请为 {product_name} 生成产品宣传大片分镜。
视频比例：{data.aspect_ratio}
视频时长：{data.duration}
画面风格：{data.style}
用户要求：{data.user_requirements or '突出产品质感、卖点和记忆点'}
模板：{template_name}
九宫格结构：1开场环境，2主体登场，3细节特写，4动作开始，5核心卖点，6视觉高潮，7体验反应，8结果呈现，9品牌收尾。
如果用户要求更细，请扩展为三十六宫格，每 4 格对应一个九宫格镜头的细分动作。
一致性约束：{consistency}
输出：镜头编号、画面、叙事功能、产品位置、运镜、字幕/声音建议。""",
        },
        {
            "key": "final_video_prompt",
            "title": "第 4 步：最终视频生成提示词",
            "goal": "整合主体图、四视图、分镜和用户要求，形成可提交给视频模型的提示词。",
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
【禁止事项】禁止改包装文字、错误 Logo、产品变形、凭空添加卖点、画面前后不一致。""",
        },
    ]
    return {
        "workflow_type": "product_tvc",
        "title": f"{product_name} 产品宣传大片 AIP 链路",
        "summary": "先锁产品主体一致性，再生成多视图和分镜，最后合成视频提示词。",
        "template": video_template,
        "model": model_config.to_dict() if model_config else None,
        "steps": steps,
        "handoff": "当前输出为可复制提示词链路；接入图片/视频模型后，每一步可升级为真实任务节点。",
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
            "prompt": f"""请根据上传的人物图片，为每个角色生成四视图设定提示词。
人物关系：{character_notes}
四视图：正面、侧面、背面、半身表情细节。
一致性约束：{consistency}
输出：每个角色的身份、视觉锚点、四视图描述、禁止事项。""",
        },
        {
            "key": "drama_script",
            "title": "第 2 步：剧情提示词 / 剧本结构",
            "goal": "把人物关系、冲突点和反转点组织成可拍摄短剧。",
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
            "prompt": f"""请根据剧本生成九宫格图片分镜提示词。
九宫格结构：1环境建立，2主角出场，3矛盾出现，4对话推进，5冲突升级，6反转揭示，7角色反应，8结果呈现，9结尾记忆点。
一致性约束：{consistency}
输出：镜头编号、出现角色、动作表情、台词/字幕、画面构图、参考角色图要求、禁止事项。""",
        },
        {
            "key": "final_video_prompt",
            "title": "第 4 步：最终短剧视频提示词",
            "goal": "整合剧本、角色四视图和图片分镜，生成视频模型提示词。",
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
【禁止事项】禁止串脸、换衣、错误人物关系、台词错位、镜头断裂、多余肢体。""",
        },
    ]
    return {
        "workflow_type": "drama",
        "title": "人物短剧 AIP 链路",
        "summary": "先分别锁定多角色一致性，再生成剧情、图片分镜和最终视频提示词。",
        "template": video_template,
        "model": model_config.to_dict() if model_config else None,
        "steps": steps,
        "handoff": "当前输出为可复制提示词链路；接入图片/视频模型后，每一步可升级为真实任务节点。",
    }


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


@router.post("/prompt-templates", summary="创建口播提示词模板")
async def create_prompt_template(
    data: PromptTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    _ensure_prompt_templates_seeded(db)
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
    payload = data.model_dump(exclude={"writing_rules"})
    payload["writing_rules_json"] = json.dumps(data.writing_rules, ensure_ascii=False)
    template = PromptTemplate(**payload)
    db.add(template)
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="prompt_template.create",
        resource_type="prompt_template",
        resource_id=template.id,
        resource_key=template.key,
        after=template.to_dict(include_prompt_body=True),
    )
    db.commit()
    db.refresh(template)
    return {"code": 0, "data": template.to_dict(include_prompt_body=True), "message": "创建成功"}


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
    payload = data.model_dump(exclude={"writing_rules"})
    for key, value in payload.items():
        setattr(template, key, value)
    template.writing_rules_json = json.dumps(data.writing_rules, ensure_ascii=False)
    db.flush()
    _record_admin_operation(
        db,
        request,
        current_user,
        action="prompt_template.update",
        resource_type="prompt_template",
        resource_id=template.id,
        resource_key=template.key,
        before=before,
        after=template.to_dict(include_prompt_body=True),
    )
    db.commit()
    db.refresh(template)
    return {"code": 0, "data": template.to_dict(include_prompt_body=True), "message": "更新成功"}


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
async def list_model_configs(model_type: str = "", db: Session = Depends(get_db)):
    return {"code": 0, "data": _active_model_configs(db, model_type)}


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
    config = AIModelConfig(**data.model_dump())
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
    for key, value in data.model_dump().items():
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


@router.post("/video-aip/plan", summary="生成视频 AIP 链路计划")
async def generate_video_aip_plan(data: VideoAipPlanRequest, db: Session = Depends(get_db)):
    video_template = _prompt_template_by_id_or_key(db, data.video_prompt_template_id, template_type="video_clip")
    video_model_config = _model_config_by_id(db, data.video_model_config_id)
    if data.workflow_type == "drama":
        plan = _build_drama_aip_plan(data, video_template, video_model_config)
    elif data.workflow_type == "product_tvc":
        plan = _build_product_tvc_aip_plan(data, video_template, video_model_config)
    else:
        plan = _build_product_tvc_aip_plan(data, video_template, video_model_config)
        plan["workflow_type"] = "standard"
        plan["title"] = "标准视频提示词链路"
        plan["summary"] = "按脚本、分镜和最终视频提示词组织标准短视频生成链路。"
    return {"code": 0, "data": plan}


@router.post("/generate", summary="一键生成口播文案 + 视频提示词 + 封面提示词")
async def generate_full_case(data: GenerateRequest, db: Session = Depends(get_db)):
    """核心生成接口：依次生成口播文案、视频分镜提示词、封面提示词"""

    # 获取 IP 人设与栏目策略
    persona_profile = _persona_profile(db, data.persona_id)
    column_profile = _column_profile(db, data.column_id)
    prompt_template = _prompt_template_by_id_or_key(db, data.prompt_template_id, data.prompt_template_key, "text_script")
    cover_template = _prompt_template_by_id_or_key(db, data.cover_prompt_template_id, template_type="image_cover")
    video_template = _prompt_template_by_id_or_key(db, data.video_prompt_template_id, template_type="video_clip")
    text_model_config = _model_config_by_id(db, data.text_model_config_id)
    cover_model_config = _model_config_by_id(db, data.cover_model_config_id)
    video_model_config = _model_config_by_id(db, data.video_model_config_id)
    prompt_template_profile = _prompt_template_profile(db, prompt_template, data.prompt_template_category)
    prompt_template_category = prompt_template["category_key"] if prompt_template else data.prompt_template_category
    cover_template_profile = _prompt_template_profile(db, cover_template)
    video_template_profile = _prompt_template_profile(db, video_template)
    model_snapshot = {
        "text_model": text_model_config.to_dict() if text_model_config else None,
        "cover_model": cover_model_config.to_dict() if cover_model_config else None,
        "video_model": video_model_config.to_dict() if video_model_config else None,
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
            "prompt_template": prompt_template,
            "cover_prompt_template": cover_template,
            "video_prompt_template": video_template,
            "model_snapshot": model_snapshot,
            "prompt_template_id": history.prompt_template_id,
            "prompt_template_key": history.prompt_template_key,
            "prompt_template_version": history.prompt_template_version,
            "prompt_template_category": history.prompt_template_category,
        }
    }


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
    }
    content_type_label = content_type_map.get(data.content_type, data.content_type)

    messages = [
        {"role": "system", "content": COPILOT_MODIFY_SYSTEM},
        {"role": "user", "content": COPILOT_MODIFY_USER.format(
            content_type=content_type_label,
            current_content=data.current_content,
            persona_profile=persona_profile,
            user_instruction=data.user_instruction,
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


@router.post("/reversal-drama/generate", summary="生成职场反转剧分镜脚本")
async def generate_reversal_drama(
    data: ReversalDramaRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """职场反转剧编剧智能体 - 同步生成。

    输入：产品 + 痛点 + (可选)自定义人物
    输出：raw_markdown + 结构化的 overview / scenes / ending_subtitle / checklist
    """
    characters_block = build_characters_block(
        [c.model_dump() for c in data.characters] if data.characters else None
    )

    messages = [
        {"role": "system", "content": REVERSAL_DRAMA_SYSTEM},
        {"role": "user", "content": REVERSAL_DRAMA_USER.format(
            product_name=data.product_name,
            product_function=data.product_function,
            pain_point=data.pain_point,
            characters_block=characters_block,
            platform=data.platform or "视频号+抖音",
            duration=data.duration or "30-60秒",
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
