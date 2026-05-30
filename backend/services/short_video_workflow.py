"""Short-video prompt workflow router.

This module is intentionally deterministic and does not call an AI provider.
It gives the frontend a stable API for intent routing, workflow steps, and
copy-ready prompt templates. AI-based classification can be layered on top
later without changing the response contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IntentConfig:
    key: str
    label: str
    command: str
    template_doc: str
    keywords: tuple[str, ...]
    steps: tuple[str, ...]


STEP_LABELS = {
    "asset_profile": "IP资产建档",
    "consistency": "主体一致性锚点",
    "clean_subject": "主体清理",
    "four_views": "四视图/角色设定图",
    "storyboard": "九宫格分镜",
    "script": "15秒动态脚本",
    "final_prompt": "最终视频模型提示词",
    "hooks": "前3秒钩子",
    "publish": "标题封面发布文案",
    "quality": "质检与重生成",
}


INTENT_CONFIGS: dict[str, IntentConfig] = {
    "product_tvc": IntentConfig(
        key="product_tvc",
        label="产品TVC",
        command="/产品TVC",
        template_doc="文档/AI短视频生产系统/02-产品TVC提示词模板.md",
        keywords=("产品", "商品", "包装", "饮料", "酒", "香水", "护肤", "TVC", "广告", "卖点", "罐", "瓶"),
        steps=("asset_profile", "consistency", "clean_subject", "four_views", "storyboard", "script", "final_prompt", "publish", "quality"),
    ),
    "pet_vlog": IntentConfig(
        key="pet_vlog",
        label="宠物Vlog",
        command="/宠物Vlog",
        template_doc="文档/AI短视频生产系统/03-宠物Vlog提示词模板.md",
        keywords=("宠物", "猫", "狗", "萌宠", "布偶", "柴犬", "Vlog", "毛色", "品种", "爪子"),
        steps=("asset_profile", "consistency", "four_views", "storyboard", "script", "final_prompt", "publish", "quality"),
    ),
    "ip_character": IntentConfig(
        key="ip_character",
        label="人物IP短片",
        command="/IP人物短片",
        template_doc="文档/AI短视频生产系统/04-人物IP短片提示词模板.md",
        keywords=("人物", "个人IP", "IP", "虚拟人", "数字人", "创始人", "专家", "人设", "剧情", "口播"),
        steps=("asset_profile", "consistency", "four_views", "storyboard", "script", "final_prompt", "publish", "quality"),
    ),
    "knowledge_talk": IntentConfig(
        key="knowledge_talk",
        label="知识口播",
        command="/IP人物短片",
        template_doc="文档/AI短视频生产系统/05-知识口播提示词模板.md",
        keywords=("知识", "科普", "课程", "干货", "观点", "讲解", "教程", "认知", "方法", "经验"),
        steps=("asset_profile", "hooks", "script", "storyboard", "final_prompt", "publish", "quality"),
    ),
    "lifestyle": IntentConfig(
        key="lifestyle",
        label="生活方式种草",
        command="/短视频工作流",
        template_doc="文档/AI短视频生产系统/06-生活方式种草提示词模板.md",
        keywords=("种草", "好物", "生活方式", "家居", "穿搭", "咖啡", "香氛", "体验", "小红书", "松弛"),
        steps=("asset_profile", "consistency", "hooks", "storyboard", "script", "final_prompt", "publish", "quality"),
    ),
    "space_store": IntentConfig(
        key="space_store",
        label="空间探店",
        command="/短视频工作流",
        template_doc="文档/AI短视频生产系统/07-空间探店提示词模板.md",
        keywords=("门店", "探店", "餐厅", "民宿", "空间", "展厅", "茶馆", "办公室", "店", "装修"),
        steps=("asset_profile", "consistency", "hooks", "storyboard", "script", "final_prompt", "publish", "quality"),
    ),
}


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _score_intent(text: str, config: IntentConfig) -> int:
    lower_text = text.lower()
    score = 0
    for keyword in config.keywords:
        if keyword.lower() in lower_text:
            score += 1
    return score


def detect_short_video_intent(text: str, requested_intent: str = "auto") -> dict[str, Any]:
    """Detect workflow intent using transparent keyword scoring."""

    if requested_intent and requested_intent != "auto" and requested_intent in INTENT_CONFIGS:
        config = INTENT_CONFIGS[requested_intent]
        return {
            "intent": config.key,
            "label": config.label,
            "confidence": 1.0,
            "matched_keywords": [],
            "source": "manual",
        }

    scores = []
    for config in INTENT_CONFIGS.values():
        score = _score_intent(text, config)
        scores.append((score, config))
    scores.sort(key=lambda item: item[0], reverse=True)

    top_score, top_config = scores[0]
    total_score = sum(score for score, _ in scores)
    if top_score == 0:
        return {
            "intent": "unknown",
            "label": "未知场景",
            "confidence": 0.0,
            "matched_keywords": [],
            "source": "keyword",
        }

    matched = [keyword for keyword in top_config.keywords if keyword.lower() in text.lower()]
    confidence = min(0.95, max(0.55, top_score / max(total_score, 1)))
    return {
        "intent": top_config.key,
        "label": top_config.label,
        "confidence": round(confidence, 2),
        "matched_keywords": matched,
        "source": "keyword",
    }


def build_short_video_workflow(
    *,
    user_input: str,
    subject_name: str = "主体",
    requested_intent: str = "auto",
    platform: str = "抖音/小红书",
    aspect_ratio: str = "9:16",
    duration: str = "15秒",
    model: str = "即梦2.0",
    style: str = "高级、真实、有记忆点",
    target_audience: str = "目标用户",
    core_message: str = "核心卖点或核心观点",
) -> dict[str, Any]:
    """Build a structured workflow response for frontend auto routing."""

    user_input = _normalize_text(user_input)
    subject_name = _normalize_text(subject_name) or "主体"
    platform = _normalize_text(platform) or "抖音/小红书"
    aspect_ratio = _normalize_text(aspect_ratio) or "9:16"
    duration = _normalize_text(duration) or "15秒"
    model = _normalize_text(model) or "即梦2.0"
    style = _normalize_text(style) or "高级、真实、有记忆点"
    target_audience = _normalize_text(target_audience) or "目标用户"
    core_message = _normalize_text(core_message) or "核心卖点或核心观点"

    detection = detect_short_video_intent(user_input, requested_intent)
    if detection["intent"] == "unknown":
        return _unknown_workflow_response(user_input)

    config = INTENT_CONFIGS[detection["intent"]]
    variables = {
        "主体名称": subject_name,
        "视频主题": user_input or f"围绕{subject_name}生成短视频",
        "目标受众": target_audience,
        "核心表达": core_message,
        "平台": platform,
        "画面比例": aspect_ratio,
        "视频时长": duration,
        "模型": model,
        "情绪基调": style,
    }

    steps = [
        _build_step(step_key, config, variables)
        for step_key in config.steps
    ]

    return {
        "intent": detection,
        "workflow": {
            "key": config.key,
            "label": config.label,
            "recommended_command": config.command,
            "template_doc": config.template_doc,
        },
        "variables": variables,
        "steps": steps,
        "next_actions": [
            "前端展示识别结果并允许用户手动切换场景",
            "按步骤生成或复制提示词到图像/视频模型",
            "生成九宫格后回填画面描述，再生成最终视频提示词",
            "成片后调用质检与重生成步骤",
        ],
    }


def _unknown_workflow_response(user_input: str) -> dict[str, Any]:
    return {
        "intent": {
            "intent": "unknown",
            "label": "未知场景",
            "confidence": 0.0,
            "matched_keywords": [],
            "source": "keyword",
        },
        "workflow": None,
        "variables": {"视频主题": user_input},
        "steps": [],
        "questions": [
            "这是产品、宠物、人物IP、知识口播、生活方式还是空间探店？",
            "视频主要发布到哪个平台？",
            "希望横版、竖版还是方形？",
            "核心卖点、观点或情绪是什么？",
        ],
        "next_actions": ["补充关键信息后重新调用短视频工作流路由接口"],
    }


def _build_step(step_key: str, config: IntentConfig, variables: dict[str, str]) -> dict[str, str]:
    label = STEP_LABELS[step_key]
    prompt = STEP_PROMPT_BUILDERS.get(step_key, _generic_prompt)(config, variables)
    return {
        "key": step_key,
        "label": label,
        "description": _step_description(step_key),
        "prompt": prompt,
    }


def _step_description(step_key: str) -> str:
    descriptions = {
        "asset_profile": "沉淀主体资产档案，供长期复用。",
        "consistency": "锁定主体不能变化的关键特征。",
        "clean_subject": "生成清理背景和干扰元素的提示词。",
        "four_views": "生成四视图、角色设定图或参考图提示词。",
        "storyboard": "生成3×3九宫格关键帧分镜。",
        "script": "根据九宫格生成按时间轴展开的动态视频脚本。",
        "final_prompt": "整合参考图、脚本、运镜、声音和禁止事项。",
        "hooks": "生成适合前3秒打开率的钩子。",
        "publish": "生成标题、封面文案、正文和话题标签。",
        "quality": "检查一致性、连续性、文字和画面质量，并给出重生成提示词。",
    }
    return descriptions.get(step_key, "生成对应阶段提示词。")


def _asset_profile_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"""请为「{v['主体名称']}」建立短视频IP资产档案。

资产类型：{config.label}
视频主题：{v['视频主题']}
目标受众：{v['目标受众']}
核心表达：{v['核心表达']}
平台：{v['平台']}

请输出：主体核心识别特征、视觉风格、情绪基调、常用场景、主体一致性锚点、禁改项、适合栏目、适合短视频类型。"""


def _consistency_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    if config.key == "product_tvc":
        anchor = "产品外形、包装结构、标签文字、品牌标识、图案位置、颜色、材质、比例、反光和纹理"
        forbidden = "不得改字、加字、改品牌、改包装、变形或生成多余产品"
    elif config.key == "pet_vlog":
        anchor = "宠物品种、毛色、花纹、眼睛颜色、耳朵形状、鼻子、嘴巴、体型、尾巴长度、毛发质感和面部气质"
        forbidden = "不得变成其他品种、不得脸部变形、不得出现多余肢体、不得改变毛色分布"
    elif config.key in ("ip_character", "knowledge_talk"):
        anchor = "人物脸型、五官、发型、发色、肤色、体型、服装、配饰、年龄感、气质和人设表达方式"
        forbidden = "不得换脸、改年龄、改服装风格、破坏人设、面部扭曲或出现多余手指"
    elif config.key == "space_store":
        anchor = "空间结构、入口位置、主视觉区域、材质、灯光、品牌气质和动线逻辑"
        forbidden = "不得让空间前后矛盾、不得生成错误招牌、不得新增无关文字"
    else:
        anchor = "主体外形、颜色、结构、比例、材质和关键细节"
        forbidden = "不得改变主体外观、不得出现错字、不得新增水印"

    return f"""请为「{v['主体名称']}」提炼主体一致性锚点。

必须保持：{anchor}。
禁止事项：{forbidden}。

请输出一段可直接复制到后续四视图、九宫格分镜和视频生成提示词中的一致性约束。"""


def _clean_subject_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"""针对上传图片，请识别图片中的核心主体「{v['主体名称']}」。

请清除图片中除核心主体以外的干扰元素，包括背景杂物、无关文字、标注、水印、贴纸、噪点和多余装饰。

核心主体必须保持完全不变：外形、比例、颜色、材质、纹理、结构、关键细节全部与原图一致，不得重绘、不得改字、不得变形、不得新增任何文字或标识。

输出为干净背景、高清写实风格、适合作为后续短视频生成参考图的主体图片。"""


def _four_views_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    if config.key == "product_tvc":
        view_desc = "正面视图、侧面视图、背面视图、顶部视图"
    elif config.key == "pet_vlog":
        view_desc = "正面、侧面、背面、自然坐姿或站姿"
    elif config.key in ("ip_character", "knowledge_talk"):
        view_desc = "正面、侧面、背面、半身姿态"
    else:
        view_desc = "正面、侧面、背面、核心细节"

    return f"""请基于上传图片中的「{v['主体名称']}」生成一致性参考图。

画面包含：{view_desc}。

要求：主体特征、比例、颜色、材质、气质与参考图保持一致；统一光源、统一背景、统一风格；不得改变主体身份、品牌、外观或关键细节。

输出适合作为后续九宫格分镜和视频生成的参考图。"""


def _storyboard_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"""请围绕「{v['主体名称']}」生成一组 {v['画面比例']} 的九宫格短视频分镜图，以3×3网格呈现9个无边界满屏超清镜头。

视频类型：{config.label}
视频主题：{v['视频主题']}
目标受众：{v['目标受众']}
核心表达：{v['核心表达']}
情绪基调：{v['情绪基调']}
平台：{v['平台']}

分镜结构：
第1格：开场环境，建立场景和情绪。
第2格：主体登场，建立识别。
第3格：细节特写，强化记忆点。
第4格：动作开始，进入叙事。
第5格：核心卖点、核心观点或核心情绪。
第6格：视觉高潮或剧情高潮。
第7格：体验、反应或共鸣。
第8格：情绪释放或结果呈现。
第9格：品牌、IP或故事收尾。

要求：每一格都必须是可用于视频生成的关键帧；镜头之间有连续叙事；主体全程保持一致；不得变形、换主体或出现错误文字。"""


def _script_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"""你是专业AI短视频导演和AI视频提示词专家。请根据九宫格分镜图，为「{v['主体名称']}」写一个{v['视频时长']}的动态视频脚本。

要求：
1. 每个镜头必须对应九宫格中的一格。
2. 输出9个镜头，每个镜头包含时间、画面、动作、运镜、声音、转场。
3. 必须是动态描述，不要只写静态画面。
4. 主体必须全程保持一致。
5. 节奏适合{v['平台']}，并适配{v['模型']}视频生成模型。

输出格式：
【视频标题】
【视频类型】{config.label}
【主体一致性要求】
【镜头脚本】

镜头1：0-1.5s
画面：
动作：
运镜：
声音：
转场：

直到镜头9。

【整体风格】
【禁止事项】"""


def _final_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"""请基于上传的九宫格分镜图和动态脚本，生成一条{v['视频时长']}的{config.label}视频。

【主体一致性】
始终保持「{v['主体名称']}」的外形、颜色、结构、比例、材质、关键细节与参考图完全一致，不得变形、不得换主体、不得新增无关文字、不得出现水印。

【参考图片说明】
上传的九宫格图片为9个连续镜头关键帧，每一格对应一个视频镜头，请按照从左到右、从上到下的顺序执行。

【画面比例】
{v['画面比例']}

【视频时长】
{v['视频时长']}

【动态脚本】
{{粘贴15秒视频脚本}}

【运镜要求】
镜头运动自然流畅，包含推近、跟拍、微距、轻微环绕、景深变化和自然转场。不得出现突然跳变和不合理运动。

【声音氛围】
根据视频类型加入背景音乐、环境声、动作声和必要的人声或旁白，声音干净，与画面节奏匹配。

【禁止事项】
不得改变主体外观，不得出现错字，不得新增水印，不得出现畸变、多余肢体、主体漂移、镜头断裂和风格突变。"""


def _hooks_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"""请为以下短视频主题生成20个前3秒钩子。

视频主题：{v['视频主题']}
视频类型：{config.label}
目标受众：{v['目标受众']}
核心表达：{v['核心表达']}
平台：{v['平台']}
表达风格：{v['情绪基调']}

要求：每个钩子不超过25个字；分成痛点型、反常识型、结果型、悬念型、场景型5类；不要夸大承诺，不要虚假营销；每个钩子都要能自然接入后续内容。"""


def _publish_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"""请根据以下短视频内容，生成适合{v['平台']}发布的物料。

视频主题：{v['视频主题']}
视频类型：{config.label}
目标受众：{v['目标受众']}
核心表达：{v['核心表达']}
风格：{v['情绪基调']}

请输出：5个标题、3个封面文案、1版正式发布文案、1版更口语化的发布文案、10个话题标签、3条评论区引导、1条私域或转化引导。

要求：标题要有钩子但不要标题党；文案符合平台语气；不夸大承诺；保持IP人设和品牌调性一致。"""


def _quality_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"""请对「{v['主体名称']}」的{config.label}短视频分镜、脚本或成片进行质检。

质检维度：主体一致性、镜头连续性、品牌一致性、平台适配、商业表达、内容表达、画面质量、声音表现。

请输出：
1. 问题清单。
2. 优先修正顺序。
3. 可直接复制的局部重生成提示词。

局部重生成模板：请保持原九宫格分镜结构不变，仅修正第{{镜头编号}}镜头的问题：{{问题描述}}。必须保持主体一致，不得改变其他镜头，不得改变整体风格。"""


def _generic_prompt(config: IntentConfig, v: dict[str, str]) -> str:
    return f"请围绕「{v['主体名称']}」生成{config.label}的{v['视频时长']}短视频提示词。"


STEP_PROMPT_BUILDERS = {
    "asset_profile": _asset_profile_prompt,
    "consistency": _consistency_prompt,
    "clean_subject": _clean_subject_prompt,
    "four_views": _four_views_prompt,
    "storyboard": _storyboard_prompt,
    "script": _script_prompt,
    "final_prompt": _final_prompt,
    "hooks": _hooks_prompt,
    "publish": _publish_prompt,
    "quality": _quality_prompt,
}
