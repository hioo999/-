"""IP 档案分步生成：模板 + 规则兜底，可选 AI 增强。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from services.ai_service import AIService, AIProviderError

logger = logging.getLogger(__name__)

SECTION_FIELDS: dict[str, list[str]] = {
    "ip": ["name", "type", "businessGoal"],
    "strategy": ["industry", "targetAudience"],
    "columns": ["mainPlatforms", "secondaryPlatforms"],
    "topics": ["tone", "visualStyle", "conversionPath", "forbiddenExpressions"],
}

SECTION_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "ip": [
        {
            "key": "workplace_career",
            "label": "典型职场 IP",
            "fields": {
                "name": "职场成长说",
                "type": "职场IP",
                "businessGoal": "帮助职场人突破瓶颈，建立专业影响力并承接咨询或课程",
            },
        },
        {
            "key": "solo_entrepreneur",
            "label": "个人创业 IP",
            "fields": {
                "name": "一人公司实验室",
                "type": "创业者IP",
                "businessGoal": "分享创业实战经验，吸引同频伙伴与高意向合作或客户",
            },
        },
        {
            "key": "knowledge_creator",
            "label": "知识博主",
            "fields": {
                "name": "行业经验分享官",
                "type": "知识IP",
                "businessGoal": "沉淀可复制的方法论，获取高意向私域线索",
            },
        },
    ],
    "strategy": [
        {
            "key": "workplace_career",
            "fields": {
                "industry": "职场成长 / 企业管理",
                "targetAudience": "25-38 岁一二线城市白领，面临晋升、跳槽、向上管理或团队管理转型焦虑",
            },
        },
        {
            "key": "solo_entrepreneur",
            "fields": {
                "industry": "个人创业 / 超级个体",
                "targetAudience": "28-45 岁想副业转型或已有小团队的创业者，缺方法、缺资源、缺稳定变现路径",
            },
        },
        {
            "key": "knowledge_creator",
            "fields": {
                "industry": "职业成长 / 行业洞察",
                "targetAudience": "22-35 岁职场人，信息过载，需要可执行的判断标准和真实案例",
            },
        },
    ],
    "columns": [
        {
            "key": "workplace_channels",
            "fields": {
                "mainPlatforms": ["wechat", "shipinhao"],
                "secondaryPlatforms": ["xiaohongshu", "moments"],
            },
        },
        {
            "key": "founder_channels",
            "fields": {
                "mainPlatforms": ["douyin", "shipinhao"],
                "secondaryPlatforms": ["wechat", "xiaohongshu"],
            },
        },
        {
            "key": "omni_channel",
            "fields": {
                "mainPlatforms": ["wechat", "shipinhao", "xiaohongshu"],
                "secondaryPlatforms": ["douyin", "moments"],
            },
        },
    ],
    "topics": [
        {
            "key": "workplace_career",
            "fields": {
                "tone": "理性、实战、有洞见，不说空话，不贩卖焦虑",
                "visualStyle": "简洁专业、图文清晰、少量信息图",
                "conversionPath": "干货内容 → 收藏关注 → 私信领资料 → 咨询或课程转化",
                "forbiddenExpressions": "绝对化成功承诺、贬低同行、未经证实的职场捷径、保证晋升",
            },
        },
        {
            "key": "solo_entrepreneur",
            "fields": {
                "tone": "真实、直接、有颗粒度，敢讲失败也讲方法",
                "visualStyle": "实拍、白板、工作场景、轻纪录片感",
                "conversionPath": "案例复盘 → 评论区交流 → 私信诊断 → 陪跑或合作转化",
                "forbiddenExpressions": "稳赚不赔、一夜暴富、夸大收入截图、保证回本",
            },
        },
        {
            "key": "professional_warm",
            "fields": {
                "tone": "专业、亲和、有温度，避免说教和堆术语",
                "visualStyle": "清爽、干净、真实感",
                "conversionPath": "内容建立认知 → 评论区互动 → 私信咨询 → 深度服务",
                "forbiddenExpressions": "绝对化承诺、未经证实的案例、收益保证、过度焦虑话术",
            },
        },
    ],
}


def _normalize_platforms(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _serialize_platforms(value: Any) -> str:
    return ",".join(_normalize_platforms(value))


def _find_template(section: str, template_key: str) -> dict[str, Any] | None:
    for item in SECTION_TEMPLATES.get(section, []):
        if item.get("key") == template_key:
            return item
    return None


def _personalize_fields(section: str, fields: dict[str, Any], context: dict[str, Any]) -> dict[str, str]:
    name = str(context.get("name") or "").strip()
    industry = str(context.get("industry") or "").strip()
    business_goal = str(context.get("businessGoal") or "").strip()
    result: dict[str, str] = {}

    for key, value in fields.items():
        if key in {"mainPlatforms", "secondaryPlatforms"}:
            result[key] = _serialize_platforms(value)
            continue
        text = str(value or "").strip()
        if section == "strategy" and key == "industry" and industry:
            text = industry
        if section == "strategy" and key == "targetAudience" and name and industry:
            text = f"关注{industry}的用户，因{ name }的内容而来，需要清晰判断标准与可执行建议。"
        if section == "ip" and key == "name" and name:
            text = name
        if section == "ip" and key == "businessGoal" and business_goal:
            text = business_goal
        result[key] = text
    return result


def _rule_generate_section(section: str, context: dict[str, Any], template_key: str = "") -> dict[str, str]:
    template = _find_template(section, template_key) if template_key else None
    if not template and SECTION_TEMPLATES.get(section):
        template = SECTION_TEMPLATES[section][0]
    base_fields = dict(template.get("fields", {})) if template else {}

    if section == "ip":
        seed_name = str(context.get("name") or base_fields.get("name") or "品牌主理人").strip()
        seed_industry = str(context.get("industry") or "所在行业").strip()
        if not base_fields:
            base_fields = {
                "name": seed_name,
                "type": "专家IP",
                "businessGoal": f"围绕{seed_industry}建立专业信任，并承接私信咨询与业务转化",
            }
    elif section == "strategy":
        seed_name = str(context.get("name") or "该 IP").strip()
        seed_industry = str(context.get("industry") or "目标行业").strip()
        if not base_fields:
            base_fields = {
                "industry": seed_industry,
                "targetAudience": f"关注{seed_industry}决策的用户，希望从{seed_name}获得真实案例和可执行建议",
            }
    elif section == "columns":
        platforms = _normalize_platforms(context.get("mainPlatforms"))
        if platforms:
            secondary = [item for item in ["xiaohongshu", "douyin", "moments", "wechat", "shipinhao"] if item not in platforms][:2]
            return {
                "mainPlatforms": _serialize_platforms(platforms),
                "secondaryPlatforms": _serialize_platforms(secondary),
            }
        if not base_fields:
            base_fields = {
                "mainPlatforms": ["wechat", "shipinhao"],
                "secondaryPlatforms": ["xiaohongshu", "moments"],
            }
    elif section == "topics":
        goal = str(context.get("businessGoal") or "业务转化").strip()
        if not base_fields:
            base_fields = {
                "tone": "专业、亲和、有温度",
                "visualStyle": "清爽、干净、真实感",
                "conversionPath": f"内容种草 → 互动答疑 → 私信咨询 → {goal}",
                "forbiddenExpressions": "绝对化承诺、夸大疗效、收益保证、未经证实的案例",
            }

    return _personalize_fields(section, base_fields, context)


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}


async def _ai_generate_section(section: str, context: dict[str, Any]) -> dict[str, str] | None:
    fields = SECTION_FIELDS.get(section, [])
    if not fields:
        return None

    prompt = (
        "你是 IP 档案顾问。请根据已有上下文，为指定步骤生成可直接填入表单的 JSON。"
        "只返回 JSON 对象，不要解释。"
        f"\n步骤: {section}"
        f"\n需要字段: {', '.join(fields)}"
        f"\n已有上下文: {json.dumps(context, ensure_ascii=False)}"
        "\n要求: 中文、具体、可执行；平台字段用英文逗号分隔字符串；禁用表达要符合合规。"
    )
    ai = AIService(module_code="ip_system")
    try:
        response = await ai.chat(
            messages=[{"role": "user", "content": prompt}],
            prompt_name="generate_script",
            temperature=0.5,
        )
    except AIProviderError as exc:
        logger.info("IP section AI fallback: %s", exc)
        return None

    payload = _extract_json_object(response.content or "")
    if not payload:
        return None

    result: dict[str, str] = {}
    for key in fields:
        value = payload.get(key)
        if value is None:
            continue
        if key in {"mainPlatforms", "secondaryPlatforms"}:
            result[key] = _serialize_platforms(value)
        else:
            result[key] = str(value).strip()
    return result or None


async def generate_ip_asset_section(
    section: str,
    context: dict[str, Any] | None = None,
    template_key: str = "",
    mode: str = "smart",
) -> dict[str, Any]:
    safe_section = str(section or "").strip()
    if safe_section not in SECTION_FIELDS:
        raise ValueError("section 无效")

    safe_context = context or {}
    if mode == "template":
        fields = _rule_generate_section(safe_section, safe_context, template_key)
        return {"section": safe_section, "fields": fields, "source": "template"}

    ai_fields = await _ai_generate_section(safe_section, safe_context)
    if ai_fields:
        return {"section": safe_section, "fields": ai_fields, "source": "ai"}

    fields = _rule_generate_section(safe_section, safe_context, template_key)
    return {"section": safe_section, "fields": fields, "source": "rule"}
