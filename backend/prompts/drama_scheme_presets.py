"""短剧脚本工坊：成套快速方案（模板 + 角色 + 示例填空）。"""

from __future__ import annotations

from typing import Any

TEMPLATE_KEY_ALIASES = {
    "med_aesthetics_edu": "professional_edu",
}

BUILTIN_DRAMA_SCHEMES: list[dict[str, Any]] = [
    {
        "key": "workplace_efficiency_trio",
        "name": "职场效率三人组",
        "tagline": "老板施压 → 同事接应 → 技术翻盘",
        "category": "企业场景",
        "template_key": "workplace_reversal",
        "reversal_pattern": "auto",
        "cast_source": "default",
        "platform": "视频号+抖音",
        "duration": "30-60秒",
        "example_product_name": "AI 在线考试系统",
        "example_product_function": "自动组卷、AI 监考、自动判卷、成绩实时推送",
        "example_pain_point": "线下考试组织麻烦、卷子改不完、管理层拿不到即时数据",
        "example_hook": "本集突出老板突击检查，结果被实时数据轻轻打脸",
    },
    {
        "key": "product_seed_duo",
        "name": "种草闺蜜双人组",
        "tagline": "博主晒痛点 → 闺蜜质疑 → 细节真香",
        "category": "种草带货",
        "template_key": "product_seed",
        "reversal_pattern": "auto",
        "cast_source": "default",
        "platform": "抖音+小红书",
        "duration": "30-45秒",
        "example_product_name": "便携榨汁杯",
        "example_product_function": "10 秒出汁、易清洗、随身带",
        "example_pain_point": "想喝鲜榨果汁但嫌麻烦、清洗太费劲",
        "example_hook": "闺蜜以为鸡肋，结果被一个清洗细节说服",
    },
    {
        "key": "professional_myth_bust",
        "name": "科普避坑三人组",
        "tagline": "用户误区 → 顾问接住 → 专家拆穿",
        "category": "知识科普",
        "template_key": "professional_edu",
        "reversal_pattern": "A",
        "cast_source": "default",
        "platform": "视频号+抖音",
        "duration": "30-60秒",
        "example_product_name": "企业合规咨询服务",
        "example_product_function": "标准化流程评估 + 风险清单输出",
        "example_pain_point": "很多人以为「照着做就行」，其实忽略了关键步骤",
        "example_hook": "用一份检查清单反转「我以为没问题」",
    },
    {
        "key": "expert_opinion_duo",
        "name": "专家观点双人组",
        "tagline": "反常识钩子 → 质疑 → 证据翻盘",
        "category": "专家IP",
        "template_key": "expert_knowledge",
        "reversal_pattern": "A",
        "cast_source": "default",
        "platform": "视频号+抖音",
        "duration": "30-60秒",
        "example_product_name": "行业数据分析工具",
        "example_product_function": "把复杂报表变成一张可决策的看板",
        "example_pain_point": "大家都以为「数据越多越好」，其实关键在少数指标",
        "example_hook": "用一个反常识观点开场，最后用数据案例反转",
    },
    {
        "key": "customer_story_duo",
        "name": "客户故事双人组",
        "tagline": "真实困扰 → 尝试 → 小反转",
        "category": "案例故事",
        "template_key": "customer_story",
        "reversal_pattern": "A",
        "cast_source": "default",
        "platform": "视频号+抖音",
        "duration": "30-45秒",
        "example_product_name": "智能工单系统",
        "example_product_function": "报修、派单、回访全流程在线化",
        "example_pain_point": "客户投诉处理慢、信息总断层",
        "example_hook": "客户本来没抱希望，结果被响应速度细节打动",
    },
    {
        "key": "live_host_duo",
        "name": "直播切片双人组",
        "tagline": "弹幕质疑 → 场控转述 → 主播演示翻盘",
        "category": "直播切片",
        "template_key": "live_stream_clip",
        "reversal_pattern": "A",
        "cast_source": "default",
        "platform": "抖音",
        "duration": "30-45秒",
        "example_product_name": "多功能料理锅",
        "example_product_function": "一锅多用途、少油烟、易收纳",
        "example_pain_point": "直播间观众质疑「真的实用吗」",
        "example_hook": "用一条尖锐弹幕开场，现场演示反转",
    },
    {
        "key": "emotional_companion",
        "name": "情感共鸣陪伴组",
        "tagline": "共鸣困境 → 陪伴 → 小释然",
        "category": "品牌情感",
        "template_key": "emotional_resonance",
        "reversal_pattern": "C",
        "cast_source": "default",
        "platform": "视频号+抖音",
        "duration": "30-45秒",
        "example_product_name": "时间管理 App",
        "example_product_function": "帮你把碎片任务收进一个清单",
        "example_pain_point": "每天很忙却总觉得什么都没做完",
        "example_hook": "产品只做配角，核心是情绪共鸣与小行动",
    },
    {
        "key": "custom_freeform",
        "name": "自由创作",
        "tagline": "自选模板与角色，完全自定义",
        "category": "高级",
        "template_key": "custom",
        "reversal_pattern": "auto",
        "cast_source": "manual",
        "platform": "视频号+抖音",
        "duration": "30-60秒",
        "example_product_name": "你的产品/服务名",
        "example_product_function": "一句话说明核心价值",
        "example_pain_point": "目标用户最典型的困扰",
        "example_hook": "本集想突出的反转或钩子（可选）",
        "characters": [
            {"name": "主角", "role": "主人公", "personality": "有具体困境", "drama_role": "reversal_carrier"},
        ],
    },
]


def list_drama_schemes() -> list[dict[str, Any]]:
    return [dict(item) for item in BUILTIN_DRAMA_SCHEMES]


def get_drama_scheme(scheme_key: str) -> dict[str, Any] | None:
    for item in BUILTIN_DRAMA_SCHEMES:
        if item["key"] == scheme_key:
            return dict(item)
    return None


def resolve_template_key(template_key: str) -> str:
    return TEMPLATE_KEY_ALIASES.get(template_key, template_key)
