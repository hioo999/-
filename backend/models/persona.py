"""IP 人设库数据模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Persona(Base):
    """IP 人设表

    存储预配置的 IP 人设档案，包含语气风格、话术结构、禁用词等。
    在生成口播/脚本前，将作为上下文注入到 AI 会话中。
    """
    __tablename__ = "ip_personas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="人设名称，如：犀利测评官")
    avatar_url = Column(String(500), default="", comment="人设头像 URL")
    description = Column(Text, default="", comment="人设简介")

    # 核心人设参数
    tone = Column(String(50), default="专业", comment="语气风格：如 专业/幽默/犀利/知性/亲切")
    speaking_style = Column(Text, default="", comment="说话风格详述（如：喜欢用反问句，常用数据举例）")
    catchphrase = Column(Text, default="", comment="口头禅/标志性话术（多个用换行分隔）")
    target_audience = Column(String(200), default="", comment="目标受众画像")
    professional_field = Column(String(200), default="", comment="专业领域")
    reference_account = Column(String(200), default="", comment="对标账号/大V参考")
    forbidden_words = Column(Text, default="", comment="禁用词汇（多个用换行分隔）")

    # 完整 Prompt 模板（用于直接注入 AI 系统提示）
    full_prompt = Column(Text, default="", comment="完整的人设系统提示词（高级用户直接编辑）")

    # 管理字段
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序权重")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_profile_text(self) -> str:
        """将人设数据组装为可直接注入 AI 的上下文文本"""
        # 如果用户已经填写了完整的 full_prompt，则直接使用
        if self.full_prompt and self.full_prompt.strip():
            return self.full_prompt.strip()

        # 否则根据结构化字段自动组装
        parts = [f"# IP 人设：{self.name}"]
        if self.description:
            parts.append(f"人设简介：{self.description}")
        if self.tone:
            parts.append(f"语气风格：{self.tone}")
        if self.speaking_style:
            parts.append(f"说话风格：{self.speaking_style}")
        if self.catchphrase:
            parts.append(f"口头禅：{self.catchphrase}")
        if self.target_audience:
            parts.append(f"目标受众：{self.target_audience}")
        if self.professional_field:
            parts.append(f"专业领域：{self.professional_field}")
        if self.reference_account:
            parts.append(f"对标账号：{self.reference_account}")
        if self.forbidden_words:
            parts.append(f"禁用词汇（绝对不能出现）：{self.forbidden_words}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "description": self.description,
            "tone": self.tone,
            "speaking_style": self.speaking_style,
            "catchphrase": self.catchphrase,
            "target_audience": self.target_audience,
            "professional_field": self.professional_field,
            "reference_account": self.reference_account,
            "forbidden_words": self.forbidden_words,
            "full_prompt": self.full_prompt,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserAccount(Base):
    """系统用户表

    正式账号用于隔离生成历史、限制游客权限和后续团队协作。
    """
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="用户姓名/昵称")
    email = Column(String(200), nullable=False, unique=True, index=True, comment="登录邮箱")
    password_hash = Column(String(300), nullable=False, comment="PBKDF2 密码哈希")
    is_admin = Column(Boolean, default=False, comment="是否管理员")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuthSession(Base):
    """登录会话表

    存储 token 摘要，不保存明文 token。
    """
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    revoked_at = Column(DateTime, nullable=True, comment="注销时间")


class ReversalDramaHistory(Base):
    """反转剧专属历史表

    绑定正式用户，保存输入参数和结构化生成结果。
    """
    __tablename__ = "reversal_drama_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    title = Column(String(200), default="", comment="剧本标题")
    product_name = Column(String(200), default="", comment="产品名")
    pain_point = Column(Text, default="", comment="痛点")
    params_json = Column(Text, default="{}", comment="生成输入参数 JSON")
    result_json = Column(Text, default="{}", comment="结构化生成结果 JSON")
    raw_markdown = Column(Text, default="", comment="原始 Markdown")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self) -> dict:
        import json

        try:
            params = json.loads(self.params_json or "{}")
        except Exception:
            params = {}
        try:
            result = json.loads(self.result_json or "{}")
        except Exception:
            result = {"raw_markdown": self.raw_markdown}

        return {
            "id": self.id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "title": self.title,
            "productName": self.product_name,
            "painPoint": self.pain_point,
            "params": params,
            "result": result,
        }


class GenerationHistory(Base):
    """生成历史记录表

    保存每一次生成的完整结果，方便用户回看和复用。
    """
    __tablename__ = "generation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), default="", comment="任务标题（自动生成或用户指定）")
    source_type = Column(String(20), default="text", comment="来源类型：text/url/file")
    source_content = Column(Text, default="", comment="原始输入内容或链接")
    extracted_content = Column(Text, default="", comment="提取后的核心内容")
    persona_id = Column(Integer, default=0, comment="使用的人设 ID")
    script_content = Column(Text, default="", comment="生成的口播文案")
    video_prompts = Column(Text, default="", comment="视频分镜提示词（JSON）")
    cover_prompt = Column(Text, default="", comment="封面提示词（JSON）")
    target_platform = Column(String(50), default="veo", comment="目标视频平台")
    prompt_template_id = Column(Integer, default=0, comment="使用的口播提示词模板 ID")
    prompt_template_key = Column(String(100), default="", comment="使用的口播提示词模板 Key")
    prompt_template_version = Column(String(30), default="", comment="使用的口播提示词模板版本")
    prompt_template_category = Column(String(80), default="", comment="使用的口播提示词模板分类")
    text_model_config_id = Column(Integer, default=0, comment="文本生成模型配置 ID")
    cover_prompt_template_id = Column(Integer, default=0, comment="封面提示词模板 ID")
    cover_model_config_id = Column(Integer, default=0, comment="封面模型配置 ID")
    video_prompt_template_id = Column(Integer, default=0, comment="视频提示词模板 ID")
    video_model_config_id = Column(Integer, default=0, comment="视频模型配置 ID")
    generation_params_json = Column(Text, default="{}", comment="生成配置侧栏参数快照 JSON")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source_type": self.source_type,
            "source_content": self.source_content,
            "extracted_content": self.extracted_content,
            "persona_id": self.persona_id,
            "script_content": self.script_content,
            "video_prompts": self.video_prompts,
            "cover_prompt": self.cover_prompt,
            "target_platform": self.target_platform,
            "prompt_template_id": self.prompt_template_id,
            "prompt_template_key": self.prompt_template_key,
            "prompt_template_version": self.prompt_template_version,
            "prompt_template_category": self.prompt_template_category,
            "text_model_config_id": self.text_model_config_id,
            "cover_prompt_template_id": self.cover_prompt_template_id,
            "cover_model_config_id": self.cover_model_config_id,
            "video_prompt_template_id": self.video_prompt_template_id,
            "video_model_config_id": self.video_model_config_id,
            "generation_params_json": self.generation_params_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContentColumn(Base):
    """栏目库

    栏目是持续生产的最小策略单元，用于固定内容结构、平台、模板和转化目标。
    """
    __tablename__ = "content_columns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="栏目名称，如：老板60秒")
    persona_id = Column(Integer, default=0, comment="绑定 IP 人设 ID，0 表示通用")
    goal = Column(String(100), default="涨粉", comment="栏目目标：涨粉/建信任/转化/教育用户")
    target_platform = Column(String(50), default="视频号+抖音", comment="推荐平台")
    duration = Column(String(50), default="30-60秒", comment="推荐时长")
    structure = Column(Text, default="", comment="固定内容结构")
    opening_style = Column(String(100), default="痛点直击型", comment="默认开头类型")
    cta = Column(Text, default="", comment="默认结尾 CTA")
    default_template = Column(String(200), default="1080x1920/image_default.html", comment="默认视频模板")
    default_voice = Column(String(100), default="zh-CN-YunjianNeural", comment="默认 TTS 音色")
    default_bgm = Column(String(200), default="", comment="默认 BGM")
    notes = Column(Text, default="", comment="栏目备注")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序权重")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_context_text(self) -> str:
        return "\n".join([
            f"# 栏目：{self.name}",
            f"栏目目标：{self.goal}",
            f"推荐平台：{self.target_platform}",
            f"推荐时长：{self.duration}",
            f"固定结构：{self.structure or '未设置'}",
            f"默认开头类型：{self.opening_style}",
            f"默认 CTA：{self.cta or '未设置'}",
            f"备注：{self.notes or '无'}",
        ])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "persona_id": self.persona_id,
            "goal": self.goal,
            "target_platform": self.target_platform,
            "duration": self.duration,
            "structure": self.structure,
            "opening_style": self.opening_style,
            "cta": self.cta,
            "default_template": self.default_template,
            "default_voice": self.default_voice,
            "default_bgm": self.default_bgm,
            "notes": self.notes,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PromptTemplateCategory(Base):
    """口播提示词模板分类

    用于后台统一管理口播模板的场景分类，前端只展示已启用分类。
    """
    __tablename__ = "prompt_template_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(80), nullable=False, unique=True, index=True, comment="分类唯一 Key")
    template_type = Column(String(50), default="text_script", index=True, comment="模板类型：text_script/image_cover/image_character/video_clip")
    name = Column(String(100), nullable=False, comment="分类名称")
    description = Column(Text, default="", comment="分类说明")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序权重")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "template_type": self.template_type,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PromptTemplate(Base):
    """口播提示词模板

    后台控制具体模板结构和写作规则，生成时只把选中模板注入 AI 上下文。
    """
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, index=True, comment="模板唯一 Key")
    template_type = Column(String(50), default="text_script", index=True, comment="模板类型：text_script/image_cover/image_character/video_clip")
    category_key = Column(String(80), nullable=False, index=True, comment="所属分类 Key")
    platform = Column(String(80), default="", index=True, comment="适用平台：wechat/xiaohongshu/douyin/shipinhao 等")
    scene = Column(String(120), default="", index=True, comment="业务场景：二创、原创、口播、封面、分镜等")
    step = Column(String(120), default="", index=True, comment="生成步骤：正文生成、标题生成、图片提示词、视频提示词等")
    name = Column(String(100), nullable=False, comment="模板名称")
    description = Column(Text, default="", comment="模板说明")
    scenario = Column(String(100), default="", comment="适用场景")
    output_structure = Column(Text, default="", comment="输出结构")
    writing_rules_json = Column(Text, default="[]", comment="写作规则 JSON 数组")
    prompt_body = Column(Text, default="", comment="后台控制的完整提示词正文")
    user_prompt_hint = Column(Text, default="", comment="前端可展示的用户补充提示建议")
    default_params_json = Column(Text, default="{}", comment="默认生成参数 JSON")
    default_model_config_id = Column(Integer, default=0, comment="默认模型配置 ID")
    version = Column(String(30), default="1.0.0", comment="模板版本")
    is_default = Column(Boolean, default=False, comment="是否分类默认模板")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序权重")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    @property
    def writing_rules(self) -> list[str]:
        import json

        try:
            rules = json.loads(self.writing_rules_json or "[]")
        except Exception:
            rules = []
        return rules if isinstance(rules, list) else []

    def to_dict(self, include_prompt_body: bool = False) -> dict:
        data = {
            "id": self.id,
            "key": self.key,
            "template_type": self.template_type,
            "category_key": self.category_key,
            "platform": self.platform,
            "scene": self.scene,
            "step": self.step,
            "name": self.name,
            "description": self.description,
            "scenario": self.scenario,
            "output_structure": self.output_structure,
            "writing_rules": self.writing_rules,
            "user_prompt_hint": self.user_prompt_hint,
            "default_params_json": self.default_params_json,
            "default_model_config_id": self.default_model_config_id,
            "version": self.version,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_prompt_body:
            data["prompt_body"] = self.prompt_body
        return data


class PromptTemplateVersion(Base):
    """提示词模板版本历史。"""
    __tablename__ = "prompt_template_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("prompt_templates.id"), nullable=False, index=True)
    template_key = Column(String(100), default="", index=True)
    version = Column(String(30), default="1.0.0", index=True)
    platform = Column(String(80), default="", index=True)
    scene = Column(String(120), default="", index=True)
    step = Column(String(120), default="", index=True)
    prompt_body = Column(Text, default="")
    output_structure = Column(Text, default="")
    writing_rules_json = Column(Text, default="[]")
    default_params_json = Column(Text, default="{}")
    change_note = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def writing_rules(self) -> list[str]:
        import json

        try:
            rules = json.loads(self.writing_rules_json or "[]")
        except Exception:
            rules = []
        return rules if isinstance(rules, list) else []

    def to_dict(self, include_prompt_body: bool = False) -> dict:
        data = {
            "versionId": self.id,
            "templateId": self.template_id,
            "templateKey": self.template_key,
            "version": self.version,
            "platform": self.platform,
            "scene": self.scene,
            "step": self.step,
            "outputStructure": self.output_structure,
            "writingRules": self.writing_rules,
            "defaultParamsJson": self.default_params_json,
            "changeNote": self.change_note,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if include_prompt_body:
            data["promptBody"] = self.prompt_body
        return data


class AIModelConfig(Base):
    """后台大模型配置，前端只读取脱敏后的元数据。"""
    __tablename__ = "ai_model_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), default=0, index=True, comment="归属用户，0 表示全局配置")
    gateway_id = Column(Integer, ForeignKey("model_gateways.id"), default=0, index=True, comment="来源中转配置 ID")
    name = Column(String(120), nullable=False, comment="前端展示名称")
    model_type = Column(String(50), default="text", index=True, comment="text/image/video/multimodal")
    provider = Column(String(80), default="custom", comment="供应商")
    api_key = Column(Text, default="", comment="API Key，前端永不返回明文")
    base_url = Column(String(500), default="https://api.openai.com/v1", comment="OpenAI-compatible Base URL")
    model_id = Column(String(160), default="", comment="服务商模型 ID")
    is_openai_compatible = Column(Boolean, default=True, comment="是否 OpenAI 兼容")
    is_default = Column(Boolean, default=False, comment="是否类型默认模型")
    is_active = Column(Boolean, default=True, comment="是否启用")
    recommendation_label = Column(String(120), default="", comment="推荐标签")
    recommendation_reason = Column(Text, default="", comment="推荐原因")
    risk_note = Column(Text, default="", comment="风险提示")
    last_seen_at = Column(DateTime, nullable=True, comment="最近一次从中转模型列表发现时间")
    timeout_seconds = Column(Integer, default=180, comment="超时时间")
    max_retries = Column(Integer, default=2, comment="最大重试次数")
    sort_order = Column(Integer, default=0, comment="排序权重")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    @staticmethod
    def mask_key(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "****"
        return f"{value[:4]}****{value[-4:]}"

    def to_dict(self, include_secret: bool = False) -> dict:
        from services.model_security import decrypt_secret

        decrypted_key = decrypt_secret(self.api_key)
        data = {
            "id": self.id,
            "user_id": self.user_id or 0,
            "gateway_id": self.gateway_id or 0,
            "name": self.name,
            "model_type": self.model_type,
            "provider": self.provider,
            "api_key_masked": self.mask_key(decrypted_key),
            "base_url": self.base_url,
            "model_id": self.model_id,
            "is_openai_compatible": self.is_openai_compatible,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "recommendation_label": self.recommendation_label,
            "recommendation_reason": self.recommendation_reason,
            "risk_note": self.risk_note,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "sort_order": self.sort_order,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_secret:
            data["api_key"] = decrypted_key
        return data


class ModelGateway(Base):
    """用户或系统级 OpenAI-compatible 模型中转配置。"""
    __tablename__ = "model_gateways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), default=0, index=True, comment="归属用户，0 表示系统级")
    scope = Column(String(30), default="user", index=True, comment="user/global")
    name = Column(String(120), nullable=False, comment="中转配置名称")
    provider_type = Column(String(80), default="openai_compatible", comment="中转协议类型")
    base_url = Column(String(500), default="https://api.openai.com/v1", comment="OpenAI-compatible Base URL")
    api_key_encrypted = Column(Text, default="", comment="加密后的 API Key")
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_test_status = Column(String(40), default="untested", comment="untested/succeeded/failed")
    last_test_message = Column(Text, default="", comment="最近测试结果")
    last_model_count = Column(Integer, default=0, comment="最近发现模型数量")
    last_synced_at = Column(DateTime, nullable=True, comment="最近同步模型时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self) -> dict:
        from services.model_security import decrypt_secret

        return {
            "id": self.id,
            "user_id": self.user_id or 0,
            "scope": self.scope,
            "name": self.name,
            "provider_type": self.provider_type,
            "base_url": self.base_url,
            "api_key_masked": AIModelConfig.mask_key(decrypt_secret(self.api_key_encrypted)),
            "is_active": self.is_active,
            "last_test_status": self.last_test_status,
            "last_test_message": self.last_test_message,
            "last_model_count": self.last_model_count,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserModelDefault(Base):
    """用户个人默认模型。"""
    __tablename__ = "user_model_defaults"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    model_type = Column(String(50), default="text", index=True, comment="text/image/video/multimodal")
    model_config_id = Column(Integer, ForeignKey("ai_model_configs.id"), default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "model_type": self.model_type,
            "model_config_id": self.model_config_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IpProject(Base):
    """平台化重构后的 IP 项目空间。"""
    __tablename__ = "ip_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    ip_type = Column(String(80), default="personal_ip", index=True)
    positioning = Column(Text, default="")
    target_audience = Column(String(300), default="")
    default_platforms_json = Column(Text, default="[]")
    voice_style_json = Column(Text, default="{}")
    status = Column(String(40), default="active", index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        return {
            "projectId": self.id,
            "name": self.name,
            "ipType": self.ip_type,
            "positioning": self.positioning,
            "targetAudience": self.target_audience,
            "defaultPlatforms": load(self.default_platforms_json, []),
            "voiceStyle": load(self.voice_style_json, {}),
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContentTopic(Base):
    """IP 项目下的内容选题。"""
    __tablename__ = "content_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("ip_projects.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    input_source_type = Column(String(40), default="topic")
    target_platforms_json = Column(Text, default='["wechat"]')
    status = Column(String(40), default="draft", index=True)
    priority = Column(String(40), default="medium")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json
        try:
            platforms = json.loads(self.target_platforms_json or "[]")
        except Exception:
            platforms = []
        return {
            "topicId": self.id,
            "projectId": self.project_id,
            "title": self.title,
            "inputSourceType": self.input_source_type,
            "targetPlatforms": platforms,
            "status": self.status,
            "priority": self.priority,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class SourceMaterial(Base):
    """统一素材中心，第一阶段承接链接、粘贴原文和主题。"""
    __tablename__ = "source_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("ip_projects.id"), default=0, index=True)
    topic_id = Column(Integer, ForeignKey("content_topics.id"), default=0, index=True)
    source_type = Column(String(40), default="topic", index=True)
    source_url = Column(String(700), default="")
    raw_text = Column(Text, default="")
    extracted_text = Column(Text, default="")
    parse_status = Column(String(40), default="succeeded", index=True)
    parse_error = Column(Text, default="")
    metadata_json = Column(Text, default="{}")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json
        try:
            metadata = json.loads(self.metadata_json or "{}")
        except Exception:
            metadata = {}
        return {
            "materialId": self.id,
            "projectId": self.project_id,
            "topicId": self.topic_id,
            "sourceType": self.source_type,
            "sourceUrl": self.source_url,
            "rawText": self.raw_text,
            "extractedText": self.extracted_text,
            "parseStatus": self.parse_status,
            "parseError": self.parse_error,
            "metadata": metadata,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class PlatformContent(Base):
    """平台内容主表，公众号文章、小红书笔记、口播稿等统一保存。"""
    __tablename__ = "platform_contents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("ip_projects.id"), default=0, index=True)
    topic_id = Column(Integer, ForeignKey("content_topics.id"), default=0, index=True)
    material_id = Column(Integer, ForeignKey("source_materials.id"), default=0, index=True)
    platform = Column(String(40), default="wechat", index=True)
    content_type = Column(String(80), default="wechat_article", index=True)
    title = Column(String(240), default="")
    subtitle = Column(String(240), default="")
    author = Column(String(100), default="")
    summary = Column(Text, default="")
    content_json = Column(Text, default="{}")
    content_html = Column(Text, default="")
    markdown_snapshot = Column(Text, default="")
    cover_prompt = Column(Text, default="")
    cover_asset_id = Column(Integer, default=0)
    image_slots_json = Column(Text, default="[]")
    tags_json = Column(Text, default="[]")
    compliance_risks_json = Column(Text, default="[]")
    status = Column(String(40), default="generated", index=True)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_content: bool = True) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        data = {
            "contentId": self.id,
            "projectId": self.project_id,
            "topicId": self.topic_id,
            "materialId": self.material_id,
            "platform": self.platform,
            "contentType": self.content_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "summary": self.summary,
            "coverPrompt": self.cover_prompt,
            "coverAssetId": self.cover_asset_id,
            "imageSlots": load(self.image_slots_json, []),
            "tags": load(self.tags_json, []),
            "complianceRisks": load(self.compliance_risks_json, []),
            "status": self.status,
            "version": self.version,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            data.update({
                "content": load(self.content_json, {}),
                "contentHtml": self.content_html,
                "markdownSnapshot": self.markdown_snapshot,
            })
        return data


class UnifiedAsset(Base):
    """统一资产库。"""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, default=0, index=True)
    topic_id = Column(Integer, default=0, index=True)
    platform_content_id = Column(Integer, default=0, index=True)
    asset_type = Column(String(80), default="text", index=True)
    source_type = Column(String(80), default="generated", index=True)
    url = Column(String(700), default="")
    storage_path = Column(String(700), default="")
    title = Column(String(240), default="")
    metadata_json = Column(Text, default="{}")
    tags_json = Column(Text, default="[]")
    status = Column(String(40), default="active", index=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        return {
            "assetId": self.id,
            "projectId": self.project_id,
            "topicId": self.topic_id,
            "platformContentId": self.platform_content_id,
            "assetType": self.asset_type,
            "sourceType": self.source_type,
            "url": self.url,
            "storagePath": self.storage_path,
            "title": self.title,
            "metadata": load(self.metadata_json, {}),
            "tags": load(self.tags_json, []),
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class GenerationTask(Base):
    """统一任务中心。"""
    __tablename__ = "generation_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, default=0, index=True)
    topic_id = Column(Integer, default=0, index=True)
    platform_content_id = Column(Integer, default=0, index=True)
    task_type = Column(String(80), default="", index=True)
    status = Column(String(40), default="pending", index=True)
    progress = Column(Integer, default=0)
    input_snapshot_json = Column(Text, default="{}")
    output_snapshot_json = Column(Text, default="{}")
    error_code = Column(String(80), default="")
    error_message = Column(Text, default="")
    raw_response_excerpt = Column(Text, default="")
    retry_count = Column(Integer, default=0)
    parent_task_id = Column(Integer, default=0, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        return {
            "taskId": self.id,
            "projectId": self.project_id,
            "topicId": self.topic_id,
            "platformContentId": self.platform_content_id,
            "taskType": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "inputSnapshot": load(self.input_snapshot_json, {}),
            "outputSnapshot": load(self.output_snapshot_json, {}),
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "retryCount": self.retry_count,
            "parentTaskId": self.parent_task_id,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "finishedAt": self.finished_at.isoformat() if self.finished_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class GenerationRecord(Base):
    """AI 调用记录，保存提示词、模型、原始返回和解析结果。"""
    __tablename__ = "generation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("generation_tasks.id"), default=0, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, default=0, index=True)
    topic_id = Column(Integer, default=0, index=True)
    platform_content_id = Column(Integer, default=0, index=True)
    prompt_template_id = Column(Integer, default=0)
    prompt_template_version_id = Column(Integer, default=0)
    prompt_snapshot_json = Column(Text, default="{}")
    model_config_id = Column(Integer, default=0)
    model_snapshot_json = Column(Text, default="{}")
    params_json = Column(Text, default="{}")
    raw_request_json = Column(Text, default="{}")
    raw_response_text = Column(Text, default="")
    parsed_output_json = Column(Text, default="{}")
    parse_status = Column(String(40), default="parsed", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        return {
            "recordId": self.id,
            "taskId": self.task_id,
            "projectId": self.project_id,
            "topicId": self.topic_id,
            "platformContentId": self.platform_content_id,
            "promptTemplateId": self.prompt_template_id,
            "promptTemplateVersionId": self.prompt_template_version_id,
            "promptSnapshot": load(self.prompt_snapshot_json, {}),
            "modelConfigId": self.model_config_id,
            "modelSnapshot": load(self.model_snapshot_json, {}),
            "params": load(self.params_json, {}),
            "parsedOutput": load(self.parsed_output_json, {}),
            "parseStatus": self.parse_status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class VideoAipProject(Base):
    """视频 AIP 项目。

    将一次产品大片/人物短剧 AIP 链路固化为可恢复、可逐步执行的项目。
    """
    __tablename__ = "video_aip_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), default=0, index=True, comment="所属用户")
    title = Column(String(200), nullable=False, comment="项目标题")
    workflow_type = Column(String(50), default="product_tvc", index=True, comment="product_tvc/drama/standard")
    status = Column(String(40), default="planned", index=True, comment="planned/running/succeeded/failed")
    source_content = Column(Text, default="", comment="素材解析或原始需求")
    script_content = Column(Text, default="", comment="口播或剧情脚本")
    product_name = Column(String(200), default="", comment="产品名")
    character_notes = Column(Text, default="", comment="人物关系说明")
    source_type = Column(String(80), default="manual", index=True, comment="来源类型：manual/short_video_project/storyboard_record")
    source_ref_id = Column(Integer, default=0, index=True, comment="来源记录 ID")
    source_assets_json = Column(Text, default="[]", comment="原始上传素材引用 JSON")
    params_json = Column(Text, default="{}", comment="输入参数快照")
    plan_json = Column(Text, default="{}", comment="完整 AIP 计划 JSON")
    current_step_key = Column(String(80), default="", comment="当前步骤 Key")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self, include_plan: bool = True) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "workflow_type": self.workflow_type,
            "status": self.status,
            "source_content": self.source_content,
            "script_content": self.script_content,
            "product_name": self.product_name,
            "character_notes": self.character_notes,
            "source_type": self.source_type,
            "source_ref_id": self.source_ref_id,
            "source_assets": load(self.source_assets_json, []),
            "params": load(self.params_json, {}),
            "current_step_key": self.current_step_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_plan:
            data["plan"] = load(self.plan_json, {})
        return data


class VideoAipStepTask(Base):
    """视频 AIP 步骤任务。"""
    __tablename__ = "video_aip_step_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("video_aip_projects.id"), nullable=False, index=True)
    step_key = Column(String(80), nullable=False, index=True)
    title = Column(String(200), default="")
    goal = Column(Text, default="")
    prompt = Column(Text, default="")
    status = Column(String(40), default="pending", index=True, comment="pending/running/succeeded/failed")
    output_json = Column(Text, default="{}", comment="步骤输出或模型任务结果")
    error_message = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self) -> dict:
        import json

        try:
            output = json.loads(self.output_json or "{}")
        except Exception:
            output = {}
        return {
            "id": self.id,
            "project_id": self.project_id,
            "step_key": self.step_key,
            "title": self.title,
            "goal": self.goal,
            "prompt": self.prompt,
            "status": self.status,
            "output": output,
            "error_message": self.error_message,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AdminOperationLog(Base):
    """后台管理操作日志。"""

    __tablename__ = "admin_operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    user_email = Column(String(200), default="", index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(80), nullable=False, index=True)
    resource_id = Column(Integer, default=0, index=True)
    resource_key = Column(String(120), default="", index=True)
    before_json = Column(Text, default="")
    after_json = Column(Text, default="")
    ip_address = Column(String(80), default="")
    user_agent = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    def to_dict(self) -> dict:
        import json

        def load(value: str):
            try:
                return json.loads(value or "null")
            except Exception:
                return None

        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_key": self.resource_key,
            "before": load(self.before_json),
            "after": load(self.after_json),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ShortVideoProject(Base):
    """AI短视频项目归档表

    保存短视频工作流识别结果、变量、步骤提示词和导出的 Markdown，
    用于后续复用、二次编辑和发布复盘。
    """
    __tablename__ = "short_video_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), default=0, index=True)
    title = Column(String(200), nullable=False, comment="项目标题")
    subject_name = Column(String(200), default="", comment="主体名称")
    intent_key = Column(String(50), default="", comment="识别场景 key")
    intent_label = Column(String(100), default="", comment="识别场景名称")
    confidence = Column(String(20), default="0", comment="识别置信度")
    platform = Column(String(100), default="", comment="目标平台")
    aspect_ratio = Column(String(20), default="", comment="画面比例")
    duration = Column(String(50), default="", comment="视频时长")
    model = Column(String(100), default="", comment="目标视频模型")
    style = Column(String(200), default="", comment="风格")
    target_audience = Column(String(300), default="", comment="目标受众")
    core_message = Column(Text, default="", comment="核心表达")
    user_input = Column(Text, default="", comment="原始用户需求")
    workflow_json = Column(Text, default="", comment="完整工作流 JSON")
    archive_markdown = Column(Text, default="", comment="导出归档 Markdown")
    notes = Column(Text, default="", comment="备注")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self, include_content: bool = True) -> dict:
        data = {
            "id": self.id,
            "user_id": self.user_id or 0,
            "title": self.title,
            "subject_name": self.subject_name,
            "intent_key": self.intent_key,
            "intent_label": self.intent_label,
            "confidence": self.confidence,
            "platform": self.platform,
            "aspect_ratio": self.aspect_ratio,
            "duration": self.duration,
            "model": self.model,
            "style": self.style,
            "target_audience": self.target_audience,
            "core_message": self.core_message,
            "user_input": self.user_input,
            "notes": self.notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            data["workflow_json"] = self.workflow_json
            data["archive_markdown"] = self.archive_markdown
        return data


class TeleprompterDraft(Base):
    """在线提词器草稿表

    保存登录用户的提词脚本、显示设置和播放位置，用于跨设备恢复。
    游客模式仍走前端本地草稿，不写入该表。
    """
    __tablename__ = "teleprompter_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    title = Column(String(100), default="未命名提词稿", comment="草稿标题")
    content = Column(Text, nullable=False, comment="提词正文")
    settings_json = Column(Text, default="{}", comment="字号、行距、速度、主题等设置 JSON")
    current_paragraph_index = Column(Integer, default=0, comment="当前段落索引")
    current_scroll_position = Column(Integer, default=0, comment="当前滚动位置")
    source = Column(String(50), default="blank", comment="来源类型")
    source_id = Column(String(100), default="", comment="来源 ID")
    word_count = Column(Integer, default=0, comment="字数/词数")
    paragraph_count = Column(Integer, default=0, comment="段落数")
    status = Column(String(30), default="editing", comment="草稿状态")
    is_active = Column(Boolean, default=True, comment="是否有效")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self, include_content: bool = True) -> dict:
        import json

        try:
            settings = json.loads(self.settings_json or "{}")
        except Exception:
            settings = {}

        data = {
            "draftId": self.id,
            "title": self.title,
            "source": self.source,
            "sourceId": self.source_id,
            "wordCount": self.word_count,
            "paragraphCount": self.paragraph_count,
            "status": self.status,
            "currentParagraphIndex": self.current_paragraph_index,
            "currentScrollPosition": self.current_scroll_position,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if include_content:
            data["content"] = self.content
            data["settings"] = settings
        return data


class WechatAccount(Base):
    """微信公众号账号配置表。

    AppSecret 只保存加密值，前端列表不返回明文密钥。
    """
    __tablename__ = "wechat_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    scope = Column(String(30), default="system", index=True, comment="system/user，第一版以管理员系统账号为主")
    authorized_user_ids_json = Column(Text, default="[]", comment="预留授权用户 ID，空数组表示所有登录用户可用")
    name = Column(String(120), nullable=False, comment="公众号名称")
    app_id = Column(String(120), nullable=False, comment="微信公众号 AppID")
    app_secret_encrypted = Column(Text, nullable=False, comment="加密后的 AppSecret")
    original_id = Column(String(120), default="", comment="公众号原始 ID")
    feishu_account = Column(String(200), default="", comment="feishu2weixin 渲染服务账号")
    theme_id = Column(String(120), default="", comment="feishu2weixin 主题 ID")
    api_base = Column(String(300), default="https://feishu2weixin.maolai.cc", comment="排版服务 API 地址")
    default_cover_url = Column(String(500), default="", comment="默认封面图 URL")
    notes = Column(Text, default="", comment="账号备注")
    is_default = Column(Boolean, default=False, comment="是否默认账号")
    last_test_status = Column(String(30), default="untested", comment="最近测试状态")
    last_test_message = Column(Text, default="", comment="最近测试信息")
    last_test_at = Column(DateTime, nullable=True, comment="最近测试时间")
    is_active = Column(Boolean, default=True, comment="是否有效")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def to_dict(self) -> dict:
        return {
            "accountId": self.id,
            "scope": self.scope,
            "name": self.name,
            "appId": self.app_id,
            "appSecretMasked": "********" if self.app_secret_encrypted else "",
            "originalId": self.original_id,
            "feishuAccount": self.feishu_account,
            "themeId": self.theme_id,
            "apiBase": self.api_base,
            "defaultCoverUrl": self.default_cover_url,
            "notes": self.notes,
            "isActive": self.is_active,
            "isDefault": self.is_default,
            "authorizedUserIds": self._authorized_user_ids(),
            "lastTestStatus": self.last_test_status,
            "lastTestMessage": self.last_test_message,
            "lastTestAt": self.last_test_at.isoformat() if self.last_test_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

    def _authorized_user_ids(self) -> list[int]:
        import json
        try:
            parsed = json.loads(self.authorized_user_ids_json or "[]")
            return [int(item) for item in parsed if str(item).isdigit()]
        except Exception:
            return []


class WechatDraftRecord(Base):
    """公众号草稿发送记录表。"""
    __tablename__ = "wechat_draft_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    wechat_account_id = Column(Integer, ForeignKey("wechat_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, default=0, index=True)
    topic_id = Column(Integer, default=0, index=True)
    platform_content_id = Column(Integer, default=0, index=True)
    task_id = Column(Integer, default=0, index=True)
    theme_id = Column(String(120), default="")
    cover_asset_id = Column(Integer, default=0)
    contains_ai_images = Column(Boolean, default=False)
    preflight_result_json = Column(Text, default="{}")
    title = Column(String(200), nullable=False)
    author = Column(String(100), default="")
    digest = Column(Text, default="")
    raw_content = Column(Text, default="")
    formatted_html = Column(Text, default="")
    cover_url = Column(String(500), default="")
    content_source_url = Column(String(500), default="")
    style = Column(String(80), default="knowledge")
    idempotency_key = Column(String(120), default="", index=True)
    wechat_media_id = Column(String(200), default="")
    thumb_media_id = Column(String(200), default="")
    status = Column(String(40), default="pending", index=True)
    error_code = Column(String(80), default="")
    error_message = Column(Text, default="")
    request_payload_json = Column(Text, default="{}")
    response_payload_json = Column(Text, default="{}")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_content: bool = True) -> dict:
        data = {
            "draftId": self.id,
            "accountId": self.wechat_account_id,
            "projectId": self.project_id,
            "topicId": self.topic_id,
            "platformContentId": self.platform_content_id,
            "taskId": self.task_id,
            "themeId": self.theme_id,
            "coverAssetId": self.cover_asset_id,
            "containsAiImages": self.contains_ai_images,
            "title": self.title,
            "author": self.author,
            "digest": self.digest,
            "coverUrl": self.cover_url,
            "contentSourceUrl": self.content_source_url,
            "style": self.style,
            "idempotencyKey": self.idempotency_key,
            "wechatMediaId": self.wechat_media_id,
            "thumbMediaId": self.thumb_media_id,
            "status": self.status,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            data["rawContent"] = self.raw_content
            data["formattedHtml"] = self.formatted_html
        return data


class WechatMaterialCache(Base):
    """公众号素材上传缓存表。

    缓存封面永久素材 media_id 和正文 uploadimg URL，避免重复上传相同图片。
    """
    __tablename__ = "wechat_material_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    wechat_account_id = Column(Integer, ForeignKey("wechat_accounts.id"), nullable=False, index=True)
    source_url = Column(String(700), nullable=False)
    cache_key = Column(String(128), nullable=False, index=True)
    material_type = Column(String(40), nullable=False, index=True)
    media_id = Column(String(200), default="")
    wechat_url = Column(String(700), default="")
    content_type = Column(String(80), default="")
    byte_size = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "cacheId": self.id,
            "accountId": self.wechat_account_id,
            "sourceUrl": self.source_url,
            "materialType": self.material_type,
            "mediaId": self.media_id,
            "wechatUrl": self.wechat_url,
            "contentType": self.content_type,
            "byteSize": self.byte_size,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class PlatformPublishConfig(Base):
    """预留平台发布配置。

    第一版不自动发布小红书、抖音、视频号，但后台需要先保存平台、账号、接口状态和备注，
    便于后续接入授权发布时沿用统一配置表。
    """
    __tablename__ = "platform_publish_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    platform = Column(String(80), default="xiaohongshu", index=True)
    name = Column(String(160), nullable=False)
    account_label = Column(String(160), default="")
    api_base = Column(String(500), default="")
    auth_type = Column(String(80), default="manual")
    credentials_encrypted = Column(Text, default="")
    status = Column(String(40), default="reserved", index=True)
    notes = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "configId": self.id,
            "platform": self.platform,
            "name": self.name,
            "accountLabel": self.account_label,
            "apiBase": self.api_base,
            "authType": self.auth_type,
            "credentialsMasked": "********" if self.credentials_encrypted else "",
            "status": self.status,
            "notes": self.notes,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class CharacterProfile(Base):
    """IP 项目内人物角色资产。"""
    __tablename__ = "character_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, default=0, index=True)
    name = Column(String(120), nullable=False)
    role = Column(String(120), default="")
    identity = Column(String(200), default="")
    personality = Column(Text, default="")
    speaking_style = Column(Text, default="")
    catchphrase = Column(Text, default="")
    reference_images_json = Column(Text, default="[]")
    profile_json = Column(Text, default="{}")
    status = Column(String(40), default="active", index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        return {
            "characterId": self.id,
            "projectId": self.project_id,
            "name": self.name,
            "role": self.role,
            "identity": self.identity,
            "personality": self.personality,
            "speakingStyle": self.speaking_style,
            "catchphrase": self.catchphrase,
            "referenceImages": load(self.reference_images_json, []),
            "profile": load(self.profile_json, {}),
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class StoryboardRecord(Base):
    """统一分镜记录，保存剧本短视频和短大片的分镜表/分镜图。"""
    __tablename__ = "storyboard_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    project_id = Column(Integer, default=0, index=True)
    topic_id = Column(Integer, default=0, index=True)
    platform_content_id = Column(Integer, default=0, index=True)
    title = Column(String(240), nullable=False)
    storyboard_type = Column(String(80), default="drama", index=True)
    frames_json = Column(Text, default="[]")
    assets_json = Column(Text, default="[]")
    status = Column(String(40), default="draft", index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        return {
            "storyboardId": self.id,
            "projectId": self.project_id,
            "topicId": self.topic_id,
            "platformContentId": self.platform_content_id,
            "title": self.title,
            "storyboardType": self.storyboard_type,
            "frames": load(self.frames_json, []),
            "assets": load(self.assets_json, []),
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class SprintIpAsset(Base):
    """Sprint 全案底座 IP 资产表。"""

    __tablename__ = "sprint_ip_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    type = Column(String(60), default="expert")
    industry = Column(String(120), default="")
    target_audience = Column(String(300), default="")
    business_goal = Column(String(120), default="")
    main_platforms_json = Column(Text, default="[]")
    secondary_platforms_json = Column(Text, default="[]")
    tone = Column(String(200), default="")
    visual_style = Column(String(200), default="")
    conversion_path = Column(Text, default="")
    forbidden_expressions = Column(Text, default="")
    profile_status = Column(String(30), default="incomplete")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load_list(value: str) -> list[str]:
            try:
                parsed = json.loads(value or "[]")
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []

        return {
            "id": f"ip_{self.id:03d}",
            "name": self.name,
            "type": self.type,
            "industry": self.industry,
            "targetAudience": self.target_audience,
            "businessGoal": self.business_goal,
            "mainPlatforms": load_list(self.main_platforms_json),
            "secondaryPlatforms": load_list(self.secondary_platforms_json),
            "tone": self.tone,
            "visualStyle": self.visual_style,
            "conversionPath": self.conversion_path,
            "forbiddenExpressions": self.forbidden_expressions,
            "profileStatus": self.profile_status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class SprintContentStrategy(Base):
    """Sprint 全案底座内容策略表。"""

    __tablename__ = "sprint_content_strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    ip_asset_id = Column(Integer, ForeignKey("sprint_ip_assets.id"), nullable=False, index=True)
    positioning = Column(Text, default="")
    target_user_profile = Column(Text, default="")
    core_pain_points_json = Column(Text, default="[]")
    platform_roles_json = Column(Text, default="{}")
    conversion_path = Column(Text, default="")
    forbidden_directions_json = Column(Text, default="[]")
    input_snapshot_json = Column(Text, default="{}")
    task_id = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        return {
            "strategyId": f"strategy_{self.id:03d}",
            "ipId": f"ip_{self.ip_asset_id:03d}",
            "positioning": self.positioning,
            "targetUserProfile": self.target_user_profile,
            "corePainPoints": load(self.core_pain_points_json, []),
            "platformRoles": load(self.platform_roles_json, {}),
            "conversionPath": self.conversion_path,
            "forbiddenDirections": load(self.forbidden_directions_json, []),
            "inputSnapshot": load(self.input_snapshot_json, {}),
            "taskId": f"task_{self.task_id:03d}" if self.task_id else "",
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class SprintContentColumn(Base):
    """Sprint 全案底座栏目矩阵表。"""

    __tablename__ = "sprint_content_columns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    ip_asset_id = Column(Integer, ForeignKey("sprint_ip_assets.id"), nullable=False, index=True)
    strategy_id = Column(Integer, default=0)
    name = Column(String(120), nullable=False)
    positioning = Column(Text, default="")
    platforms_json = Column(Text, default="[]")
    content_format = Column(String(120), default="")
    frequency = Column(String(80), default="")
    conversion_action = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        try:
            platforms = json.loads(self.platforms_json or "[]")
        except Exception:
            platforms = []
        return {
            "id": f"column_{self.id:03d}",
            "ipId": f"ip_{self.ip_asset_id:03d}",
            "strategyId": f"strategy_{self.strategy_id:03d}" if self.strategy_id else "",
            "name": self.name,
            "positioning": self.positioning,
            "platforms": platforms,
            "contentFormat": self.content_format,
            "frequency": self.frequency,
            "conversionAction": self.conversion_action,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class SprintTopic(Base):
    """Sprint 全案底座选题表。"""

    __tablename__ = "sprint_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    ip_asset_id = Column(Integer, ForeignKey("sprint_ip_assets.id"), nullable=False, index=True)
    column_id = Column(Integer, ForeignKey("sprint_content_columns.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    platforms_json = Column(Text, default="[]")
    content_goal = Column(String(80), default="trust_building")
    user_pain_point = Column(Text, default="")
    core_viewpoint = Column(Text, default="")
    status = Column(String(40), default="todo")
    priority = Column(String(40), default="medium")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        try:
            platforms = json.loads(self.platforms_json or "[]")
        except Exception:
            platforms = []
        return {
            "id": f"topic_{self.id:03d}",
            "ipId": f"ip_{self.ip_asset_id:03d}",
            "columnId": f"column_{self.column_id:03d}",
            "title": self.title,
            "platforms": platforms,
            "contentGoal": self.content_goal,
            "userPainPoint": self.user_pain_point,
            "coreViewpoint": self.core_viewpoint,
            "status": self.status,
            "priority": self.priority,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class SprintContentDraft(Base):
    """Sprint 全案底座内容母稿表。"""

    __tablename__ = "sprint_content_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    ip_asset_id = Column(Integer, ForeignKey("sprint_ip_assets.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("sprint_topics.id"), nullable=False, index=True)
    pain_point = Column(Text, default="")
    core_viewpoint = Column(Text, default="")
    logic = Column(Text, default="")
    cases = Column(Text, default="")
    golden_sentences_json = Column(Text, default="[]")
    conversion_action = Column(Text, default="")
    forbidden_expressions = Column(Text, default="")
    status = Column(String(40), default="generated")
    version = Column(Integer, default=1)
    task_id = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        try:
            golden_sentences = json.loads(self.golden_sentences_json or "[]")
        except Exception:
            golden_sentences = []
        return {
            "draftId": f"draft_{self.id:03d}",
            "topicId": f"topic_{self.topic_id:03d}",
            "ipId": f"ip_{self.ip_asset_id:03d}",
            "painPoint": self.pain_point,
            "coreViewpoint": self.core_viewpoint,
            "logic": self.logic,
            "cases": self.cases,
            "goldenSentences": golden_sentences,
            "conversionAction": self.conversion_action,
            "forbiddenExpressions": self.forbidden_expressions,
            "status": self.status,
            "version": self.version,
            "taskId": f"task_{self.task_id:03d}" if self.task_id else "",
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class SprintMaterial(Base):
    """Sprint 全案底座素材表。"""

    __tablename__ = "sprint_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    ip_asset_id = Column(Integer, default=0, index=True)
    filename = Column(String(300), nullable=False)
    content_type = Column(String(120), default="application/octet-stream")
    file_size = Column(Integer, default=0)
    url = Column(String(500), default="")
    status = Column(String(40), default="uploaded")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "materialId": f"material_{self.id:03d}",
            "ipId": f"ip_{self.ip_asset_id:03d}" if self.ip_asset_id else "",
            "filename": self.filename,
            "contentType": self.content_type,
            "fileSize": self.file_size,
            "url": self.url,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class SprintGenerationTask(Base):
    """Sprint 全案底座生成任务表。"""

    __tablename__ = "sprint_generation_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    type = Column(String(80), default="")
    status = Column(String(40), default="succeeded")
    progress = Column(Integer, default=100)
    input_snapshot_json = Column(Text, default="{}")
    output_snapshot_json = Column(Text, default="{}")
    error_code = Column(String(80), default="")
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        import json

        def load(value: str, fallback):
            try:
                return json.loads(value or "")
            except Exception:
                return fallback

        return {
            "taskId": f"task_{self.id:03d}",
            "type": self.type,
            "status": self.status,
            "progress": self.progress,
            "inputSnapshot": load(self.input_snapshot_json, {}),
            "outputSnapshot": load(self.output_snapshot_json, {}),
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
