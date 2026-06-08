"""在线提词器云端草稿与来源脚本接口。"""

from __future__ import annotations

import json
import re
import hashlib
from html import escape
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from api.auth_routes import get_admin_user, get_current_user
from database import get_db
from models.persona import AuthSession, GenerationHistory, LiveTeleprompterScript, LiveTeleprompterTemplateRecord, ShortVideoProject, TeleprompterDraft, TeleprompterQueue, UserAccount
from services.ai_service import AIProviderError, AIService, safe_parse_ai_json


router = APIRouter(prefix="/api/teleprompter", tags=["在线提词器"])

MAX_SCRIPT_LENGTH = 30000
MAX_LIVE_PRODUCTS = 20

LIVE_TELEPROMPTER_TEMPLATES: dict[str, dict[str, Any]] = {
    "medical_beauty_advanced": {
        "name": "医美高级专场模板",
        "description": "按成品直播台本结构生成：开场预热、福利、主推、首发、系列、选购指南、返场、必背和万能话术。",
        "defaultStyle": "专业可信+双播强转化",
        "openingFocus": "换季/皮肤痛点、观看福利、重磅主推和首发悬念",
        "productFocus": "痛点场景-项目科普-权益说明-价格揭晓-顾虑消除-倒计时追单",
        "sectionBlueprint": ["开场预热", "福利引导", "主推引流爆款", "重磅首发", "系列产品", "选购指南", "爆品返场", "主播必背清单"],
        "complianceTips": ["医美项目必须提示到店面诊评估，不承诺治疗效果。", "所有疗程、适用人群和禁忌以医生/专业咨询评估为准。"],
    },
    "general_sales": {
        "name": "通用强转化直播",
        "description": "适合多品排品、福利促销、强成交场景。",
        "defaultStyle": "专业强转化",
        "openingFocus": "福利、主推品和最大优惠",
        "productFocus": "痛点-卖点-价格-顾虑-倒计时",
        "complianceTips": ["所有价格、库存、赠品和有效期以直播间当前链接为准。"],
    },
    "medical_beauty": {
        "name": "医美/皮肤管理直播",
        "description": "适合卡项、疗程、院内项目和专家型讲解。",
        "defaultStyle": "专业可信+强转化",
        "openingFocus": "皮肤痛点、专业评估和到店权益",
        "productFocus": "症状场景-原理科普-适合人群-到店面诊-锁价",
        "complianceTips": ["医美项目必须提示到店面诊评估，不承诺治疗效果。", "避免使用治愈、永久解决、保证有效等绝对化表达。"],
    },
    "skincare": {
        "name": "美妆护肤直播",
        "description": "适合护肤品、套组、功效成分和种草转化。",
        "defaultStyle": "轻专业种草+限时转化",
        "openingFocus": "肤质痛点、成分卖点和套组权益",
        "productFocus": "肤质匹配-成分利益-使用场景-价格权益",
        "complianceTips": ["功效表达避免夸大，敏感肌建议先做局部测试。"],
    },
    "health": {
        "name": "大健康直播",
        "description": "适合营养品、健康服务、体检和生活方式改善。",
        "defaultStyle": "专业科普+稳健转化",
        "openingFocus": "健康困扰、日常场景和科学建议",
        "productFocus": "风险意识-科学解释-适用边界-咨询转化",
        "complianceTips": ["不替代医疗诊断和治疗，特殊人群需咨询专业人士。"],
    },
    "local_service": {
        "name": "本地生活直播",
        "description": "适合门店套餐、到店服务、预约核销。",
        "defaultStyle": "亲切本地化+到店转化",
        "openingFocus": "门店位置、到店权益和限时预约",
        "productFocus": "服务场景-到店流程-权益价格-预约提醒",
        "complianceTips": ["到店地址、预约规则、核销有效期和退款规则需直播前复核。"],
    },
    "course": {
        "name": "课程/知识直播",
        "description": "适合课程、咨询、训练营和专家 IP 转化。",
        "defaultStyle": "专家干货+咨询转化",
        "openingFocus": "学习痛点、成果路径和限时名额",
        "productFocus": "问题诊断-方法框架-课程权益-名额提醒",
        "complianceTips": ["避免承诺收益、升学、就业或结果保证。"],
    },
    "single_product": {
        "name": "单品强转化",
        "description": "适合一个核心产品反复讲透、持续逼单。",
        "defaultStyle": "单品深讲+循环追单",
        "openingFocus": "单品核心痛点和最大差异点",
        "productFocus": "多轮痛点循环-案例-价格锚点-追单",
        "complianceTips": ["单品循环讲解时要定期重复适用边界和权益规则。"],
    },
}

LIVE_TELEPROMPTER_THEMES: dict[str, dict[str, str]] = {
    "dark_live": {"name": "深色直播间", "accent": "#22d3ee", "bg1": "#08111f", "bg2": "#132238", "card": "rgba(15, 23, 42, .92)", "text": "#f8fafc"},
    "high_contrast": {"name": "高对比远距", "accent": "#facc15", "bg1": "#020617", "bg2": "#111827", "card": "#000000", "text": "#ffffff"},
    "medical_green": {"name": "医美绿色", "accent": "#2ecc71", "bg1": "#0a1628", "bg2": "#0d2117", "card": "#111d2b", "text": "#f8fafc"},
    "beauty_pink": {"name": "美妆粉色", "accent": "#f472b6", "bg1": "#24111f", "bg2": "#3f172e", "card": "rgba(63, 23, 46, .88)", "text": "#fff7fb"},
    "black_gold": {"name": "黑金高客单", "accent": "#facc15", "bg1": "#080604", "bg2": "#1f1608", "card": "rgba(31, 22, 8, .92)", "text": "#fff7d6"},
    "minimal_big": {"name": "极简大字", "accent": "#2563eb", "bg1": "#f8fafc", "bg2": "#e2e8f0", "card": "#ffffff", "text": "#0f172a"},
    "mobile_landscape": {"name": "手机横屏", "accent": "#38bdf8", "bg1": "#020617", "bg2": "#0f172a", "card": "#0f172a", "text": "#f8fafc"},
}


class TeleprompterSettings(BaseModel):
    fontSize: str = Field("large")
    lineHeight: str = Field("normal")
    scrollSpeed: int = Field(5, ge=1, le=100)
    theme: str = Field("dark")
    mirrorMode: bool = False
    countdownEnabled: bool = True
    countdownSeconds: int = Field(3, ge=1, le=10)


class TeleprompterDraftPayload(BaseModel):
    title: str = Field("未命名提词稿", max_length=100)
    content: str = Field(..., min_length=1, max_length=MAX_SCRIPT_LENGTH)
    settings: TeleprompterSettings = Field(default_factory=TeleprompterSettings)
    currentParagraphIndex: int = Field(0, ge=0)
    currentScrollPosition: int = Field(0, ge=0)
    source: str = Field("blank", max_length=50)
    sourceId: str = Field("", max_length=100)
    status: str = Field("editing", max_length=30)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        return title or "未命名提词稿"

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("提词正文不能为空")
        return content


class TeleprompterQueuePayload(BaseModel):
    activeScriptId: str = Field("", max_length=120)
    scripts: list[dict[str, Any]] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class AnalyticsEventPayload(BaseModel):
    eventName: str = Field(..., min_length=1, max_length=100)
    eventTime: str = Field("", max_length=80)
    sessionId: str = Field("", max_length=120)
    properties: dict[str, Any] = Field(default_factory=dict)


class LiveTeleprompterHost(BaseModel):
    name: str = Field("主播A", max_length=30)
    role: str = Field("主讲", max_length=30)

    @field_validator("name", "role")
    @classmethod
    def normalize_host_text(cls, value: str) -> str:
        return value.strip()


class LiveTeleprompterProduct(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    category: str = Field("", max_length=60)
    positioning: str = Field("normal", max_length=30)
    originalPrice: str = Field("", max_length=40)
    livePrice: str = Field("", max_length=40)
    offer: str = Field("", max_length=160)
    sellingPoints: list[str] = Field(default_factory=list)
    painPoints: list[str] = Field(default_factory=list)
    suitableUsers: str = Field("", max_length=240)
    faq: list[str] = Field(default_factory=list)
    notes: str = Field("", max_length=500)
    durationMinutes: int = Field(10, ge=1, le=120)

    @field_validator("sellingPoints", "painPoints", "faq")
    @classmethod
    def normalize_text_list(cls, value: list[str]) -> list[str]:
        return [item.strip()[:180] for item in value if item and item.strip()][:12]

    @field_validator("name", "category", "positioning", "originalPrice", "livePrice", "offer", "suitableUsers", "notes")
    @classmethod
    def normalize_product_text(cls, value: str) -> str:
        return value.strip()


class LiveTeleprompterRequest(BaseModel):
    title: str = Field("直播专场台本", max_length=100)
    platform: str = Field("视频号", max_length=40)
    liveStart: str = Field("20:00", max_length=20)
    liveDurationMinutes: int = Field(60, ge=10, le=480)
    gmvTarget: str = Field("", max_length=40)
    audience: str = Field("", max_length=240)
    style: str = Field("专业强转化", max_length=60)
    hostCount: int = Field(1, ge=1, le=2)
    hosts: list[LiveTeleprompterHost] = Field(default_factory=list)
    benefits: str = Field("", max_length=600)
    extraRequirements: str = Field("", max_length=800)
    complianceMode: bool = True
    templateKey: str = Field("general_sales", max_length=80)
    themeKey: str = Field("dark_live", max_length=80)
    aiEnhance: bool = False
    saveHistory: bool = False
    products: list[LiveTeleprompterProduct] = Field(..., min_length=1, max_length=MAX_LIVE_PRODUCTS)

    @field_validator("title", "platform", "liveStart", "gmvTarget", "audience", "style", "benefits", "extraRequirements")
    @classmethod
    def normalize_request_text(cls, value: str) -> str:
        return value.strip()


class LiveTeleprompterSection(BaseModel):
    sectionId: str
    title: str
    timeRange: str
    goal: str
    plainText: str


class LiveTeleprompterGenerateResponse(BaseModel):
    scriptId: int | None = None
    title: str
    templateKey: str = "general_sales"
    themeKey: str = "dark_live"
    plainText: str
    html: str
    sections: list[LiveTeleprompterSection]
    mustRemember: list[str]
    complianceTips: list[str]
    generatedBy: str = "rule_based_v1"


class LiveTeleprompterImportPayload(BaseModel):
    rawText: str = Field(..., min_length=1, max_length=60000)


class LiveTeleprompterPreflightPayload(BaseModel):
    request: LiveTeleprompterRequest


class LiveTeleprompterReviewPayload(BaseModel):
    scriptId: int | None = None
    title: str = Field("直播复盘", max_length=120)
    actualGmv: str = Field("", max_length=60)
    productResults: list[dict[str, Any]] = Field(default_factory=list)
    winningLines: str = Field("", max_length=2000)
    weakProducts: str = Field("", max_length=2000)
    audienceQuestions: str = Field("", max_length=3000)
    notes: str = Field("", max_length=3000)


class LiveTeleprompterTemplatePayload(BaseModel):
    key: str = Field(..., min_length=2, max_length=80)
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=1000)
    defaultStyle: str = Field("专业强转化", max_length=120)
    openingFocus: str = Field("福利和重点", max_length=300)
    productFocus: str = Field("痛点-卖点-价格-顾虑-倒计时", max_length=500)
    complianceTips: list[str] = Field(default_factory=list)
    sectionBlueprint: list[str] = Field(default_factory=list)


class LiveTeleprompterHistoryPayload(BaseModel):
    title: str = Field("直播专场台本", max_length=120)
    templateKey: str = Field("general_sales", max_length=80)
    request: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    plainText: str = Field(..., min_length=1, max_length=120000)
    html: str = Field(..., min_length=1, max_length=240000)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_optional_user(authorization: str | None, db: Session) -> UserAccount | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    session = db.query(AuthSession).filter(
        AuthSession.token_hash == _token_hash(token),
        AuthSession.revoked_at.is_(None),
    ).first()
    if not session:
        return None
    return db.query(UserAccount).filter(UserAccount.id == session.user_id, UserAccount.is_active.is_(True)).first()


def _count_words(text: str) -> int:
    english_words = re.findall(r"[A-Za-z0-9]+", text)
    chinese_chars = re.findall(r"[\u4e00-\u9fa5]", text)
    return len(english_words) + len(chinese_chars)


def _count_paragraphs(text: str) -> int:
    return len([item for item in re.split(r"\n\s*\n+|\n+", text) if item.strip()])


def _safe_text(value: str) -> str:
    return escape(value or "", quote=True)


def _split_multiline(value: str) -> list[str]:
    return [line.strip() for line in re.split(r"[\n；;]+", value or "") if line.strip()]


def _minutes_to_clock(start: str, offset: int) -> str:
    match = re.match(r"^(\d{1,2}):(\d{2})$", start.strip())
    if not match:
        return f"+{offset}min"
    hour = int(match.group(1))
    minute = int(match.group(2))
    total = hour * 60 + minute + offset
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _host_names(data: LiveTeleprompterRequest) -> tuple[str, str]:
    hosts = data.hosts or []
    first = hosts[0].name if len(hosts) >= 1 and hosts[0].name else "主播A"
    second = hosts[1].name if len(hosts) >= 2 and hosts[1].name else "主播B"
    if data.hostCount == 1:
        return first, ""
    return first, second


def _speaker_line(host: str, text: str) -> str:
    return f"{host}：{text}" if host else text


def _product_goal(product: LiveTeleprompterProduct) -> str:
    mapping = {
        "main": "主推冲单",
        "hero": "主推冲单",
        "premiere": "首发冲量",
        "launch": "首发冲量",
        "return": "返场追单",
        "traffic": "引流拉新",
        "profit": "利润转化",
    }
    return mapping.get(product.positioning, "产品转化")


def _product_tag(product: LiveTeleprompterProduct) -> str:
    mapping = {
        "main": "主推",
        "hero": "主推",
        "premiere": "首发",
        "launch": "首发",
        "return": "返场",
        "traffic": "引流",
        "profit": "利润款",
    }
    return mapping.get(product.positioning, product.category or "产品")


def _template_for(data: LiveTeleprompterRequest, db: Session | None = None) -> dict[str, Any]:
    if data.templateKey not in LIVE_TELEPROMPTER_TEMPLATES and db is not None:
        record = db.query(LiveTeleprompterTemplateRecord).filter(
            LiveTeleprompterTemplateRecord.key == data.templateKey,
            LiveTeleprompterTemplateRecord.is_active.is_(True),
        ).first()
        if record:
            return record.to_dict()
    return LIVE_TELEPROMPTER_TEMPLATES.get(data.templateKey) or LIVE_TELEPROMPTER_TEMPLATES["general_sales"]


def _build_product_plain(product: LiveTeleprompterProduct, data: LiveTeleprompterRequest, host_a: str, host_b: str) -> str:
    pain_points = product.painPoints or ["最近遇到同类问题的用户，可以先听这一段再决定。"]
    selling_points = product.sellingPoints or ["核心价值清晰、适合直播间当场讲透。"]
    price_line = ""
    if product.livePrice:
        price_line = f"直播价 {product.livePrice}"
        if product.originalPrice:
            price_line += f"，日常价 {product.originalPrice}"
        if product.offer:
            price_line += f"，{product.offer}"

    lines = [
        f"【{product.name}】",
        _speaker_line(host_a, f"接下来讲 {product.name}，这是本场的{_product_tag(product)}。"),
    ]
    if data.hostCount == 2:
        lines.append(_speaker_line(host_b, f"它主要适合哪些人？评论区如果有同样情况，可以先扣 1。"))
    lines.extend([
        _speaker_line(host_a, f"先说痛点：{'；'.join(pain_points[:3])}"),
        _speaker_line(host_a, f"再说卖点：{'；'.join(selling_points[:4])}"),
    ])
    if product.suitableUsers:
        lines.append(_speaker_line(host_b if data.hostCount == 2 else host_a, f"适合人群：{product.suitableUsers}"))
    if price_line:
        lines.append(_speaker_line(host_a, f"重点听价格，{price_line}。先拍下锁定权益，到店或客服再确认细节。"))
    lines.extend([
        "【动作提示】拿起产品/指向链接/停顿 2 秒，让场控确认库存和链接状态。",
        _speaker_line(host_b if data.hostCount == 2 else host_a, "还在犹豫的用户，先看自己是不是符合刚才说的痛点，符合就不要错过这轮价格。"),
        "【倒计时】5、4、3、2、1，上链接。",
    ])
    if product.faq:
        lines.append("【常见问题】")
        lines.extend([f"- {item}" for item in product.faq[:5]])
    if product.notes:
        lines.append(f"【备注】{product.notes}")
    return "\n".join(lines)


def _build_live_sections(data: LiveTeleprompterRequest, db: Session | None = None) -> tuple[list[LiveTeleprompterSection], list[str], list[str]]:
    template = _template_for(data, db)
    host_a, host_b = _host_names(data)
    sections: list[LiveTeleprompterSection] = []
    must_remember: list[str] = []
    compliance_tips = [
        "涉及效果、健康、医美或大健康内容时，避免使用保证有效、永久解决、治愈等绝对化表达。",
        "价格、赠品、有效期和退款规则以实际活动配置为准，直播前需要场控复核。",
        *template.get("complianceTips", []),
    ] if data.complianceMode else []

    opening_minutes = min(10, max(5, data.liveDurationMinutes // 8))
    opening_lines = [
        _speaker_line(host_a, f"欢迎来到{data.title}，今天这场在{data.platform}直播，先把{template.get('openingFocus', '福利和重点')}给大家讲清楚。"),
    ]
    if data.hostCount == 2:
        opening_lines.append(_speaker_line(host_b, "刚进来的朋友先点关注，评论区告诉我们你最关心的问题。"))
    if data.audience:
        opening_lines.append(_speaker_line(host_a, f"今天主要帮这类用户解决问题：{data.audience}"))
    if data.benefits:
        opening_lines.append(_speaker_line(host_a, f"先说本场福利：{data.benefits}"))
    opening_lines.extend([
        "【互动】让用户扣 1 / 留关键词 / 点关注，场控同步观察评论高频问题。",
        f"【节奏】开场不要讲太散，3 分钟内必须抛出{template.get('openingFocus', '本场主推和最大优惠')}。",
    ])
    sections.append(LiveTeleprompterSection(
        sectionId="section-opening",
        title="开场预热",
        timeRange=f"{_minutes_to_clock(data.liveStart, 0)}-{_minutes_to_clock(data.liveStart, opening_minutes)}",
        goal="拉人气",
        plainText="\n".join(opening_lines),
    ))

    offset = opening_minutes
    for index, product in enumerate(data.products, start=1):
        duration = product.durationMinutes
        section_id = f"section-product-{index}"
        sections.append(LiveTeleprompterSection(
            sectionId=section_id,
            title=f"{_product_tag(product)} · {product.name}",
            timeRange=f"{_minutes_to_clock(data.liveStart, offset)}-{_minutes_to_clock(data.liveStart, offset + duration)}",
            goal=_product_goal(product),
            plainText=_build_product_plain(product, data, host_a, host_b),
        ))
        price = f"{product.livePrice}" if product.livePrice else "价格待复核"
        point = product.sellingPoints[0] if product.sellingPoints else "核心卖点待补充"
        must_remember.append(f"{product.name}：{price}；一句话卖点：{point}")
        offset += duration

    final_lines = [
        _speaker_line(host_a, "最后几分钟做返场，还没下单的用户重点听这段。"),
        "【返场顺序】优先返场主推/首发/库存紧张产品，每个产品只讲一句痛点、一句卖点、一句价格。",
    ]
    for product in data.products[:6]:
        final_lines.append(f"- {product.name}：{product.livePrice or '直播价待确认'}，{(product.sellingPoints or ['适合本场目标用户'])[0]}")
    final_lines.extend([
        _speaker_line(host_b if data.hostCount == 2 else host_a, "下单后看弹窗或私信客服，确认预约、发货、售后和使用方式。"),
        _speaker_line(host_a, "感谢大家陪伴，本场价格以直播间当前链接为准，错过这轮就等下次活动。"),
    ])
    sections.append(LiveTeleprompterSection(
        sectionId="section-final",
        title="返场收尾",
        timeRange=f"{_minutes_to_clock(data.liveStart, offset)}-{_minutes_to_clock(data.liveStart, min(offset + 8, data.liveDurationMinutes))}",
        goal="最后冲刺",
        plainText="\n".join(final_lines),
    ))

    if data.extraRequirements:
        must_remember.append(f"补充要求：{data.extraRequirements}")
    return sections, must_remember, compliance_tips


def _paragraphs_to_html(text: str, host_a: str, host_b: str) -> str:
    blocks = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        safe = _safe_text(line)
        cls = "script-line"
        if line.startswith("【"):
            cls += " action-line"
        elif host_a and line.startswith(f"{host_a}："):
            cls += " host-a-line"
            safe = safe.replace(_safe_text(f"{host_a}："), f'<span class="host-tag host-a">{_safe_text(host_a)}</span>', 1)
        elif host_b and line.startswith(f"{host_b}："):
            cls += " host-b-line"
            safe = safe.replace(_safe_text(f"{host_b}："), f'<span class="host-tag host-b">{_safe_text(host_b)}</span>', 1)
        blocks.append(f'<p class="{cls}">{safe}</p>')
    return "\n".join(blocks)


def _build_live_html(data: LiveTeleprompterRequest, sections: list[LiveTeleprompterSection], must_remember: list[str], compliance_tips: list[str]) -> str:
    host_a, host_b = _host_names(data)
    theme = LIVE_TELEPROMPTER_THEMES.get(data.themeKey) or LIVE_TELEPROMPTER_THEMES["dark_live"]
    gmv_badge = f'<div class="gmv-display">目标 {_safe_text(data.gmvTarget)}</div>' if data.gmvTarget else ""
    nav = "\n".join([
        f'<button class="nav-btn" onclick="scrollToSection(\'{_safe_text(section.sectionId)}\')">{_safe_text(section.title[:8])}</button>'
        for section in sections
    ])
    section_html = []
    for section in sections:
        section_html.append(f'''
<section class="time-section" id="{_safe_text(section.sectionId)}">
  <div class="time-header">
    <h2><span>{_safe_text(section.title)}</span><span class="time-tag">{_safe_text(section.timeRange)}</span><span class="goal-tag">{_safe_text(section.goal)}</span></h2>
  </div>
  <div class="product-card">
    <div class="script-section">
      <div class="section-title">直播话术</div>
      <div class="script-content">{_paragraphs_to_html(section.plainText, host_a, host_b)}</div>
    </div>
  </div>
</section>''')
    remember_html = "\n".join([f'<li>{_safe_text(item)}</li>' for item in must_remember])
    compliance_html = "\n".join([f'<li>{_safe_text(item)}</li>' for item in compliance_tips])
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
  <title>{_safe_text(data.title)}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ min-height: 100vh; padding-bottom: 88px; background: linear-gradient(135deg, {_safe_text(theme['bg1'])} 0%, {_safe_text(theme['bg2'])} 70%); color: {_safe_text(theme['text'])}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; line-height: 1.8; }}
    .top-nav {{ position: fixed; inset: 0 0 auto; z-index: 20; padding: 12px 16px; border-bottom: 1px solid rgba(56, 189, 248, 0.22); background: rgba(8, 17, 31, 0.94); backdrop-filter: blur(14px); }}
    .top-nav h1 {{ color: {_safe_text(theme['accent'])}; font-size: 17px; text-align: center; }}
    .top-nav .subtitle {{ margin-top: 2px; color: #94a3b8; font-size: 12px; text-align: center; }}
    .gmv-display, .time-display {{ position: fixed; top: 56px; z-index: 21; padding: 5px 12px; border-radius: 999px; color: #fff; font-size: 13px; font-weight: 800; }}
    .gmv-display {{ left: 14px; background: #dc2626; }} .time-display {{ right: 14px; background: #0891b2; }}
    .controls {{ position: fixed; top: 92px; right: 14px; z-index: 21; display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; max-width: 280px; }}
    .control-btn {{ border: 1px solid rgba(255,255,255,.16); border-radius: 999px; background: rgba(15,23,42,.86); color: #e2e8f0; padding: 6px 10px; font: inherit; font-size: 12px; cursor: pointer; }}
    .container {{ max-width: 880px; margin: 0 auto; padding: 122px 15px 24px; }}
    .time-section {{ margin-bottom: 26px; scroll-margin-top: 118px; }}
    .time-header {{ position: sticky; top: 52px; z-index: 10; padding: 14px 18px; border-radius: 16px 16px 0 0; background: linear-gradient(135deg, {_safe_text(theme['accent'])}, #0f766e); }}
    .time-header h2 {{ display: flex; align-items: center; gap: 9px; flex-wrap: wrap; font-size: 18px; }}
    .time-tag {{ padding: 2px 10px; border-radius: 999px; background: rgba(255,255,255,.18); font-size: 12px; }}
    .goal-tag {{ margin-left: auto; padding: 2px 10px; border-radius: 999px; background: #facc15; color: #111827; font-size: 12px; font-weight: 900; }}
    .product-card {{ overflow: hidden; border: 1px solid rgba(148, 163, 184, .18); border-top: 0; border-radius: 0 0 16px 16px; background: {_safe_text(theme['card'])}; box-shadow: 0 18px 50px rgba(0,0,0,.18); }}
    .script-section {{ padding: 16px 18px; }}
    .section-title {{ display: flex; align-items: center; gap: 8px; margin-bottom: 10px; color: #94a3b8; font-size: 13px; font-weight: 800; }}
    .section-title::before {{ content: ''; width: 3px; height: 16px; border-radius: 999px; background: {_safe_text(theme['accent'])}; }}
    .script-content {{ font-size: var(--script-size, 18px); line-height: var(--script-line, 2); }}
    .script-line {{ margin: 8px 0; }}
    .action-line {{ display: inline-block; margin: 8px 0; padding: 5px 10px; border-radius: 8px; background: rgba(56,189,248,.12); color: #bae6fd; font-size: calc(var(--script-size, 18px) - 2px); }}
    .host-tag {{ display: inline-block; margin-right: 8px; padding: 1px 9px; border-radius: 6px; color: #fff; font-size: 12px; font-weight: 900; vertical-align: middle; }}
    .host-a {{ background: #2563eb; }} .host-b {{ background: #ea580c; }}
    .must-card {{ margin: 26px 0; padding: 18px; border: 1px solid rgba(250,204,21,.28); border-radius: 16px; background: rgba(113, 63, 18, .34); }}
    .must-card h3 {{ margin-bottom: 10px; color: #fde68a; }}
    .must-card li {{ margin-left: 20px; padding: 4px 0; }}
    .quick-nav {{ position: fixed; inset: auto 0 0; z-index: 20; display: flex; gap: 8px; overflow-x: auto; padding: 10px; border-top: 1px solid rgba(56,189,248,.22); background: rgba(8,17,31,.96); backdrop-filter: blur(14px); }}
    .nav-btn {{ flex: 0 0 auto; padding: 8px 13px; border: 1px solid rgba(148,163,184,.22); border-radius: 999px; background: #172033; color: #cbd5e1; font: inherit; font-size: 12px; cursor: pointer; }}
    .back-top {{ position: fixed; right: 14px; bottom: 76px; z-index: 21; width: 44px; height: 44px; border: 0; border-radius: 50%; background: #0891b2; color: #fff; font-size: 18px; cursor: pointer; }}
    @media (max-width: 640px) {{ .controls {{ position: static; margin-top: 8px; justify-content: center; max-width: none; }} .container {{ padding-top: 108px; }} .time-header h2 {{ font-size: 16px; }} .script-content {{ font-size: var(--script-size-mobile, 16px); }} }}
  </style>
</head>
<body>
  <div class="top-nav"><h1>{_safe_text(data.title)}</h1><div class="subtitle">{_safe_text(data.platform)} · {_safe_text(data.style)} · {data.hostCount}人直播</div><div class="controls"><button class="control-btn" onclick="toggleAutoScroll()">自动滚动</button><button class="control-btn" onclick="changeFont(2)">字号+</button><button class="control-btn" onclick="changeFont(-2)">字号-</button><button class="control-btn" onclick="document.documentElement.requestFullscreen && document.documentElement.requestFullscreen()">全屏</button></div></div>
  {gmv_badge}<div class="time-display" id="timeDisplay">{_safe_text(data.liveStart)}</div>
  <main class="container">
    {''.join(section_html)}
    <section class="must-card"><h3>主播必背清单</h3><ul>{remember_html}</ul></section>
    <section class="must-card"><h3>合规与场控提醒</h3><ul>{compliance_html}</ul></section>
  </main>
  <button class="back-top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>
  <nav class="quick-nav">{nav}<button class="nav-btn" onclick="window.scrollTo({{top:document.body.scrollHeight,behavior:'smooth'}})">必背</button></nav>
  <script>
    let autoScrollTimer = null; let fontSize = 18;
    function scrollToSection(id) {{ document.getElementById(id)?.scrollIntoView({{ behavior: 'smooth' }}); }}
    function updateTime() {{ const now = new Date(); document.getElementById('timeDisplay').textContent = String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0'); }}
    function changeFont(delta) {{ fontSize = Math.max(14, Math.min(34, fontSize + delta)); document.documentElement.style.setProperty('--script-size', fontSize + 'px'); document.documentElement.style.setProperty('--script-size-mobile', Math.max(14, fontSize - 2) + 'px'); }}
    function toggleAutoScroll() {{ if (autoScrollTimer) {{ clearInterval(autoScrollTimer); autoScrollTimer = null; return; }} autoScrollTimer = setInterval(() => window.scrollBy({{ top: 1, behavior: 'auto' }}), 60); }}
    setInterval(updateTime, 1000); updateTime();
  </script>
</body>
</html>'''


def _build_plain_text(title: str, sections: list[LiveTeleprompterSection], must_remember: list[str], compliance_tips: list[str]) -> str:
    lines = [title, ""]
    for section in sections:
        lines.extend([f"## {section.title}｜{section.timeRange}｜{section.goal}", section.plainText, ""])
    lines.extend(["## 主播必背清单", *[f"- {item}" for item in must_remember], ""])
    if compliance_tips:
        lines.extend(["## 合规与场控提醒", *[f"- {item}" for item in compliance_tips]])
    return "\n".join(lines).strip()


async def _try_ai_enhance_live_sections(
    data: LiveTeleprompterRequest,
    sections: list[LiveTeleprompterSection],
    must_remember: list[str],
    compliance_tips: list[str],
    db: Session | None = None,
) -> tuple[list[LiveTeleprompterSection], list[str], list[str], str]:
    if not data.aiEnhance:
        return sections, must_remember, compliance_tips, "rule_based_v1"

    template = _template_for(data, db)
    prompt_payload = {
        "request": data.model_dump(),
        "template": template,
        "sections": [section.model_dump() for section in sections],
        "mustRemember": must_remember,
        "complianceTips": compliance_tips,
    }
    messages = [
        {
            "role": "system",
            "content": "你是直播台本导演。只返回 JSON，不要输出解释。保留输入的 sectionId/timeRange/goal，优化 plainText，使话术更像真实直播，但必须避免绝对化承诺。",
        },
        {
            "role": "user",
            "content": (
                "请根据以下直播台本草稿进行专业润色，返回 JSON："
                "{\"sections\":[{\"sectionId\":string,\"title\":string,\"timeRange\":string,\"goal\":string,\"plainText\":string}],"
                "\"mustRemember\":[string],\"complianceTips\":[string]}。\n"
                f"输入：{json.dumps(prompt_payload, ensure_ascii=False)}"
            ),
        },
    ]
    try:
        response = await AIService(module_code="live_teleprompter", db_session=db).chat(
            messages,
            prompt_name="live_teleprompter_enhance",
            temperature=0.62,
            max_tokens=6000,
        )
        parsed, _ = safe_parse_ai_json(response.content, {})
        parsed_sections = parsed.get("sections") if isinstance(parsed, dict) else None
        if not isinstance(parsed_sections, list) or not parsed_sections:
            return sections, must_remember, compliance_tips, "rule_based_v1_ai_parse_fallback"
        enhanced_sections = []
        original_by_id = {section.sectionId: section for section in sections}
        for item in parsed_sections:
            if not isinstance(item, dict):
                continue
            section_id = str(item.get("sectionId") or "")
            original = original_by_id.get(section_id)
            resolved_section_id = section_id or (original.sectionId if original else f"section-{len(enhanced_sections) + 1}")
            enhanced_sections.append(LiveTeleprompterSection(
                sectionId=resolved_section_id,
                title=str(item.get("title") or (original.title if original else "直播阶段"))[:120],
                timeRange=str(item.get("timeRange") or (original.timeRange if original else ""))[:40],
                goal=str(item.get("goal") or (original.goal if original else "转化"))[:40],
                plainText=str(item.get("plainText") or (original.plainText if original else ""))[:12000],
            ))
        if not enhanced_sections:
            return sections, must_remember, compliance_tips, "rule_based_v1_ai_parse_fallback"
        enhanced_must = parsed.get("mustRemember") if isinstance(parsed.get("mustRemember"), list) else must_remember
        enhanced_tips = parsed.get("complianceTips") if isinstance(parsed.get("complianceTips"), list) else compliance_tips
        return enhanced_sections, [str(item)[:260] for item in enhanced_must[:30]], [str(item)[:260] for item in enhanced_tips[:20]], "ai_enhanced_v1"
    except AIProviderError:
        return sections, must_remember, compliance_tips, "rule_based_v1_ai_unavailable"
    except Exception:
        return sections, must_remember, compliance_tips, "rule_based_v1_ai_error"


def _save_live_history(
    db: Session,
    user: UserAccount,
    data: LiveTeleprompterRequest,
    response: LiveTeleprompterGenerateResponse,
) -> LiveTeleprompterScript:
    record = LiveTeleprompterScript(
        user_id=user.id,
        title=response.title[:120],
        template_key=response.templateKey,
        request_json=json.dumps(data.model_dump(), ensure_ascii=False),
        result_json=json.dumps(response.model_dump(), ensure_ascii=False),
        plain_text=response.plainText,
        html_content=response.html,
        word_count=_count_words(response.plainText),
        section_count=len(response.sections),
        status="generated",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _parse_product_rows(raw_text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return []
    rows = []
    delimiter = "\t" if any("\t" in line for line in lines[:3]) else ","
    header = [cell.strip() for cell in re.split(r"\t|,", lines[0])]
    has_header = any(cell in {"产品名称", "名称", "产品", "直播价", "卖点", "痛点"} for cell in header)
    data_lines = lines[1:] if has_header else lines
    for index, line in enumerate(data_lines, start=1):
        cells = [cell.strip() for cell in re.split(r"\t|,", line)]
        if not any(cells):
            continue
        if has_header:
            row = dict(zip(header, cells))
            name = row.get("产品名称") or row.get("名称") or row.get("产品") or cells[0]
            category = row.get("类别") or row.get("分类") or ""
            live_price = row.get("直播价") or row.get("价格") or ""
            original_price = row.get("原价") or ""
            offer = row.get("权益") or row.get("优惠") or ""
            selling = row.get("卖点") or ""
            pain = row.get("痛点") or ""
        else:
            name = cells[0] if len(cells) > 0 else f"产品 {index}"
            category = cells[1] if len(cells) > 1 else ""
            live_price = cells[2] if len(cells) > 2 else ""
            original_price = cells[3] if len(cells) > 3 else ""
            offer = cells[4] if len(cells) > 4 else ""
            selling = cells[5] if len(cells) > 5 else ""
            pain = cells[6] if len(cells) > 6 else ""
        rows.append({
            "name": name[:80] or f"产品 {index}",
            "category": category[:60],
            "positioning": "main" if index == 1 else "normal",
            "originalPrice": original_price[:40],
            "livePrice": live_price[:40],
            "offer": offer[:160],
            "sellingPoints": _split_multiline(selling),
            "painPoints": _split_multiline(pain),
            "suitableUsers": "",
            "faq": [],
            "notes": "",
            "durationMinutes": 15 if index == 1 else 10,
        })
    return rows[:MAX_LIVE_PRODUCTS]


def _preflight_findings(data: LiveTeleprompterRequest) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not data.title:
        findings.append({"severity": "error", "label": "缺少直播主题", "suggestion": "填写直播主题后再生成。"})
    if not data.benefits:
        findings.append({"severity": "warning", "label": "缺少开场福利", "suggestion": "建议补充观看礼、互动礼、限时权益或预约权益。"})
    return_products = [item for item in data.products if item.positioning == "return"]
    if len(data.products) >= 3 and not return_products:
        findings.append({"severity": "warning", "label": "没有返场产品", "suggestion": "多品直播建议至少标记一个返场追单产品。"})
    for index, product in enumerate(data.products, start=1):
        prefix = f"产品 {index}：{product.name}"
        if not product.livePrice:
            findings.append({"severity": "error", "label": f"{prefix} 缺少直播价", "suggestion": "补充直播价或明确价格待定话术。"})
        if len(product.sellingPoints) < 2:
            findings.append({"severity": "warning", "label": f"{prefix} 卖点不足", "suggestion": "至少补 2 个卖点，避免直播间讲不深。"})
        if product.positioning in {"main", "premiere"} and not product.offer:
            findings.append({"severity": "warning", "label": f"{prefix} 缺少权益", "suggestion": "主推/首发产品建议写清赠品、抵扣、限时或预约权益。"})
        risky_text = "\n".join([product.notes, *product.sellingPoints, *product.painPoints, *product.faq])
        if re.search(r"保证|永久|治愈|根治|100%|绝对", risky_text):
            findings.append({"severity": "error", "label": f"{prefix} 命中高风险表达", "suggestion": "删除保证、永久、治愈、根治、100%、绝对等表达。"})
    passed = not any(item["severity"] == "error" for item in findings)
    findings.insert(0, {"severity": "success" if passed else "error", "label": "生成前检查", "suggestion": "可生成。" if passed else "存在必须修复项。"})
    return findings


def _build_review_report(data: LiveTeleprompterReviewPayload) -> dict[str, Any]:
    product_lines = []
    for item in data.productResults[:30]:
        name = str(item.get("name") or "未命名产品")
        sales = str(item.get("sales") or "未填")
        conversion = str(item.get("conversion") or "待复盘")
        product_lines.append(f"{name}：成交 {sales}，表现 {conversion}")
    suggestions = []
    if data.weakProducts.strip():
        suggestions.append("弱转化产品下次提前补充案例、对比锚点和顾虑回答。")
    if data.audienceQuestions.strip():
        suggestions.append("把高频问题沉淀为 FAQ，并插入对应产品讲解段。")
    if not suggestions:
        suggestions.append("下次保留当前结构，重点优化主推品价格揭晓和返场节奏。")
    markdown = "\n".join([
        f"# {data.title}",
        f"实际 GMV：{data.actualGmv or '未填写'}",
        "",
        "## 产品表现",
        *(product_lines or ["- 暂无产品成交数据"]),
        "",
        "## 高转化话术",
        data.winningLines or "未填写",
        "",
        "## 弱项与问题",
        data.weakProducts or "未填写",
        "",
        "## 用户高频问题",
        data.audienceQuestions or "未填写",
        "",
        "## 下次优化建议",
        *[f"- {item}" for item in suggestions],
        "",
        "## 备注",
        data.notes or "无",
    ])
    return {"markdown": markdown, "suggestions": suggestions, "productLines": product_lines}


def _settings_json(settings: TeleprompterSettings) -> str:
    return json.dumps(settings.model_dump(), ensure_ascii=False)


def _get_user_draft(db: Session, draft_id: int, user: UserAccount) -> TeleprompterDraft:
    draft = db.query(TeleprompterDraft).filter(
        TeleprompterDraft.id == draft_id,
        TeleprompterDraft.user_id == user.id,
        TeleprompterDraft.is_active.is_(True),
    ).first()
    if not draft:
        raise HTTPException(status_code=404, detail="提词器草稿不存在")
    return draft


def _get_user_live_script(db: Session, script_id: int, user: UserAccount) -> LiveTeleprompterScript:
    record = db.query(LiveTeleprompterScript).filter(
        LiveTeleprompterScript.id == script_id,
        LiveTeleprompterScript.user_id == user.id,
        LiveTeleprompterScript.is_active.is_(True),
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="直播台本不存在")
    return record


@router.get("/live-script/templates", summary="获取直播台本行业模板")
async def list_live_script_templates(db: Session = Depends(get_db)):
    items = [
        {"key": key, **value, "isCustom": False}
        for key, value in LIVE_TELEPROMPTER_TEMPLATES.items()
    ]
    custom = db.query(LiveTeleprompterTemplateRecord).filter(LiveTeleprompterTemplateRecord.is_active.is_(True)).order_by(LiveTeleprompterTemplateRecord.updated_at.desc()).all()
    items.extend([record.to_dict() for record in custom])
    return {"code": 0, "data": {"items": items}}


@router.get("/live-script/themes", summary="获取直播 HTML 主题")
async def list_live_script_themes():
    return {"code": 0, "data": {"items": [{"key": key, **value} for key, value in LIVE_TELEPROMPTER_THEMES.items()]}}


@router.post("/live-script/import-products", summary="批量解析直播排品表")
async def import_live_script_products(data: LiveTeleprompterImportPayload):
    products = _parse_product_rows(data.rawText)
    return {"code": 0, "data": {"items": products, "count": len(products)}, "message": "排品表已解析"}


@router.post("/live-script/preflight", summary="直播台本生成前检查")
async def preflight_live_script(data: LiveTeleprompterPreflightPayload):
    findings = _preflight_findings(data.request)
    return {"code": 0, "data": {"items": findings, "passed": not any(item["severity"] == "error" for item in findings)}}


@router.post("/live-script/review", summary="生成直播复盘报告")
async def review_live_script(data: LiveTeleprompterReviewPayload):
    return {"code": 0, "data": _build_review_report(data), "message": "直播复盘已生成"}


@router.post("/live-script/templates", summary="创建直播台本模板")
async def create_live_template(data: LiveTeleprompterTemplatePayload, db: Session = Depends(get_db), user: UserAccount = Depends(get_admin_user)):
    if data.key in LIVE_TELEPROMPTER_TEMPLATES:
        raise HTTPException(status_code=409, detail="不能覆盖系统内置模板")
    existing = db.query(LiveTeleprompterTemplateRecord).filter(LiveTeleprompterTemplateRecord.key == data.key).first()
    if existing:
        raise HTTPException(status_code=409, detail="模板 Key 已存在")
    config = data.model_dump(exclude={"key", "name", "description"})
    record = LiveTeleprompterTemplateRecord(user_id=user.id, key=data.key, name=data.name, description=data.description, config_json=json.dumps(config, ensure_ascii=False))
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"code": 0, "data": record.to_dict(), "message": "直播台本模板已创建"}


@router.put("/live-script/templates/{template_id}", summary="更新直播台本模板")
async def update_live_template(template_id: int, data: LiveTeleprompterTemplatePayload, db: Session = Depends(get_db), user: UserAccount = Depends(get_admin_user)):
    record = db.query(LiveTeleprompterTemplateRecord).filter(LiveTeleprompterTemplateRecord.id == template_id, LiveTeleprompterTemplateRecord.is_active.is_(True)).first()
    if not record:
        raise HTTPException(status_code=404, detail="模板不存在")
    if data.key != record.key and (data.key in LIVE_TELEPROMPTER_TEMPLATES or db.query(LiveTeleprompterTemplateRecord).filter(LiveTeleprompterTemplateRecord.key == data.key).first()):
        raise HTTPException(status_code=409, detail="模板 Key 已存在")
    record.key = data.key
    record.name = data.name
    record.description = data.description
    record.config_json = json.dumps(data.model_dump(exclude={"key", "name", "description"}), ensure_ascii=False)
    db.commit()
    db.refresh(record)
    return {"code": 0, "data": record.to_dict(), "message": "直播台本模板已更新"}


@router.delete("/live-script/templates/{template_id}", summary="删除直播台本模板")
async def delete_live_template(template_id: int, db: Session = Depends(get_db), user: UserAccount = Depends(get_admin_user)):
    record = db.query(LiveTeleprompterTemplateRecord).filter(LiveTeleprompterTemplateRecord.id == template_id, LiveTeleprompterTemplateRecord.is_active.is_(True)).first()
    if not record:
        raise HTTPException(status_code=404, detail="模板不存在")
    record.is_active = False
    db.commit()
    return {"code": 0, "data": {"templateId": template_id, "deleted": True}, "message": "直播台本模板已删除"}


@router.get("/queue", summary="获取用户提词器多文案队列")
async def get_queue(
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    queue = db.query(TeleprompterQueue).filter(
        TeleprompterQueue.user_id == user.id,
        TeleprompterQueue.is_active.is_(True),
    ).first()
    return {"code": 0, "data": queue.to_dict() if queue else None}


@router.put("/queue", summary="保存用户提词器多文案队列")
async def save_queue(
    data: TeleprompterQueuePayload,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    queue = db.query(TeleprompterQueue).filter(TeleprompterQueue.user_id == user.id).first()
    if not queue:
        queue = TeleprompterQueue(user_id=user.id)
        db.add(queue)

    queue.active_script_id = data.activeScriptId
    queue.scripts_json = json.dumps(data.scripts[:100], ensure_ascii=False)
    queue.settings_json = json.dumps(data.settings, ensure_ascii=False)
    queue.is_active = True
    db.commit()
    db.refresh(queue)
    return {"code": 0, "data": queue.to_dict(), "message": "提词器队列已保存"}


@router.get("/drafts", summary="获取提词器草稿列表")
async def list_drafts(
    page: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    safe_page = max(1, page)
    safe_page_size = max(1, min(pageSize, 100))
    query = db.query(TeleprompterDraft).filter(
        TeleprompterDraft.user_id == user.id,
        TeleprompterDraft.is_active.is_(True),
    )
    total = query.count()
    items = (
        query.order_by(TeleprompterDraft.updated_at.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {
        "code": 0,
        "data": {
            "items": [draft.to_dict(include_content=False) for draft in items],
            "page": safe_page,
            "pageSize": safe_page_size,
            "total": total,
        },
    }


@router.get("/drafts/recent", summary="获取最近提词器草稿")
async def get_recent_draft(
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    draft = db.query(TeleprompterDraft).filter(
        TeleprompterDraft.user_id == user.id,
        TeleprompterDraft.is_active.is_(True),
    ).order_by(TeleprompterDraft.updated_at.desc()).first()
    return {"code": 0, "data": draft.to_dict(include_content=False) if draft else None}


@router.get("/drafts/{draft_id}", summary="获取提词器草稿详情")
async def get_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    draft = _get_user_draft(db, draft_id, user)
    return {"code": 0, "data": draft.to_dict(include_content=True)}


@router.post("/drafts", summary="创建提词器草稿")
async def create_draft(
    data: TeleprompterDraftPayload,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    draft = TeleprompterDraft(
        user_id=user.id,
        title=data.title,
        content=data.content,
        settings_json=_settings_json(data.settings),
        current_paragraph_index=data.currentParagraphIndex,
        current_scroll_position=data.currentScrollPosition,
        source=data.source,
        source_id=data.sourceId,
        word_count=_count_words(data.content),
        paragraph_count=_count_paragraphs(data.content),
        status=data.status,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {"code": 0, "data": draft.to_dict(include_content=False), "message": "提词器草稿保存成功"}


@router.put("/drafts/{draft_id}", summary="更新提词器草稿")
async def update_draft(
    draft_id: int,
    data: TeleprompterDraftPayload,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    draft = _get_user_draft(db, draft_id, user)
    draft.title = data.title
    draft.content = data.content
    draft.settings_json = _settings_json(data.settings)
    draft.current_paragraph_index = data.currentParagraphIndex
    draft.current_scroll_position = data.currentScrollPosition
    draft.source = data.source
    draft.source_id = data.sourceId
    draft.word_count = _count_words(data.content)
    draft.paragraph_count = _count_paragraphs(data.content)
    draft.status = data.status
    db.commit()
    db.refresh(draft)
    return {"code": 0, "data": draft.to_dict(include_content=False), "message": "提词器草稿更新成功"}


@router.delete("/drafts/{draft_id}", summary="删除提词器草稿")
async def delete_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    draft = _get_user_draft(db, draft_id, user)
    draft.is_active = False
    db.commit()
    return {"code": 0, "data": {"draftId": draft_id, "deleted": True}, "message": "提词器草稿已删除"}


@router.get("/scripts/{script_id}", summary="获取AI脚本提词内容")
async def get_script(script_id: int, db: Session = Depends(get_db)):
    record = db.query(GenerationHistory).filter(GenerationHistory.id == script_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="脚本不存在")
    return {
        "code": 0,
        "data": {
            "scriptId": record.id,
            "title": record.title or f"脚本 {record.id}",
            "content": record.script_content,
            "platform": record.target_platform,
            "source": "script",
            "estimatedDuration": max(1, round(_count_words(record.script_content) / 5)),
            "updatedAt": record.updated_at.isoformat() if record.updated_at else None,
        },
    }


@router.get("/video-packages/{package_id}/teleprompter-script", summary="获取短视频发布包提词脚本")
async def get_video_package_script(package_id: int, db: Session = Depends(get_db)):
    project = db.query(ShortVideoProject).filter(ShortVideoProject.id == package_id, ShortVideoProject.is_active.is_(True)).first()
    if not project:
        raise HTTPException(status_code=404, detail="短视频发布包不存在")

    content = _extract_project_script(project)
    return {
        "code": 0,
        "data": {
            "packageId": project.id,
            "scriptId": project.id,
            "title": project.title,
            "content": content,
            "platform": project.platform,
            "durationEstimate": max(1, round(_count_words(content) / 5)),
            "source": "video_package",
            "updatedAt": project.updated_at.isoformat() if project.updated_at else None,
        },
    }


def _extract_project_script(project: ShortVideoProject) -> str:
    for raw in [project.archive_markdown, project.workflow_json, project.user_input, project.core_message]:
        if raw and raw.strip():
            return raw.strip()
    return project.title


@router.post("/live-script/generate", summary="生成直播 HTML 台本")
async def generate_live_script(
    data: LiveTeleprompterRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    sections, must_remember, compliance_tips = _build_live_sections(data, db)
    sections, must_remember, compliance_tips, generated_by = await _try_ai_enhance_live_sections(
        data,
        sections,
        must_remember,
        compliance_tips,
        db,
    )
    plain_text = _build_plain_text(data.title, sections, must_remember, compliance_tips)
    html = _build_live_html(data, sections, must_remember, compliance_tips)
    response = LiveTeleprompterGenerateResponse(
        title=data.title,
        templateKey=data.templateKey if data.templateKey in LIVE_TELEPROMPTER_TEMPLATES else "general_sales",
        themeKey=data.themeKey if data.themeKey in LIVE_TELEPROMPTER_THEMES else "dark_live",
        plainText=plain_text,
        html=html,
        sections=sections,
        mustRemember=must_remember,
        complianceTips=compliance_tips,
        generatedBy=generated_by,
    )
    user = _get_optional_user(authorization, db)
    if data.saveHistory and user:
        saved = _save_live_history(db, user, data, response)
        response.scriptId = saved.id
    return {"code": 0, "data": response.model_dump(), "message": "直播台本已生成"}


@router.get("/live-script/history", summary="获取直播台本历史")
async def list_live_script_history(
    page: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    safe_page = max(1, page)
    safe_page_size = max(1, min(pageSize, 100))
    query = db.query(LiveTeleprompterScript).filter(
        LiveTeleprompterScript.user_id == user.id,
        LiveTeleprompterScript.is_active.is_(True),
    )
    total = query.count()
    items = (
        query.order_by(LiveTeleprompterScript.updated_at.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {"code": 0, "data": {"items": [item.to_dict(False) for item in items], "page": safe_page, "pageSize": safe_page_size, "total": total}}


@router.get("/live-script/history/{script_id}", summary="获取直播台本历史详情")
async def get_live_script_history(
    script_id: int,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    record = _get_user_live_script(db, script_id, user)
    return {"code": 0, "data": record.to_dict(True)}


@router.post("/live-script/history", summary="保存直播台本历史")
async def create_live_script_history(
    data: LiveTeleprompterHistoryPayload,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    record = LiveTeleprompterScript(
        user_id=user.id,
        title=data.title,
        template_key=data.templateKey,
        request_json=json.dumps(data.request, ensure_ascii=False),
        result_json=json.dumps(data.result, ensure_ascii=False),
        plain_text=data.plainText,
        html_content=data.html,
        word_count=_count_words(data.plainText),
        section_count=len(data.result.get("sections", [])) if isinstance(data.result, dict) else 0,
        status="generated",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"code": 0, "data": record.to_dict(False), "message": "直播台本历史已保存"}


@router.delete("/live-script/history/{script_id}", summary="删除直播台本历史")
async def delete_live_script_history(
    script_id: int,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    record = _get_user_live_script(db, script_id, user)
    record.is_active = False
    db.commit()
    return {"code": 0, "data": {"scriptId": script_id, "deleted": True}, "message": "直播台本历史已删除"}


@router.post("/analytics/events", summary="上报提词器埋点")
async def collect_analytics_event(data: AnalyticsEventPayload):
    # V0.1 先接收事件，后续再落库或转发数据平台。
    return {"code": 0, "data": {"accepted": True, "eventName": data.eventName}, "message": "ok"}
