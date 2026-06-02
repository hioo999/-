"""Sprint 全案底座 API。

当前实现使用数据库持久化和登录用户归属隔离，生成内容仍保持规则 Mock，保证 Sprint2 可以在稳定底座上继续接入真实 AI 和平台发布能力。
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_routes import get_current_user
from database import get_db
from models.persona import (
    SprintContentColumn,
    SprintContentDraft,
    SprintContentStrategy,
    SprintGenerationTask,
    SprintIpAsset,
    SprintMaterial,
    SprintTopic,
    UserAccount,
)


router = APIRouter(tags=["Sprint全案底座"])

MAX_MATERIAL_SIZE = 5 * 1024 * 1024
ALLOWED_MATERIAL_EXTENSIONS = {".txt", ".md", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_MATERIAL_TYPES = {
    "text/plain",
    "text/markdown",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}
COMPLIANCE_FORBIDDEN_SUMMARY = "避免绝对化表达、结果承诺、收益承诺、过度焦虑和未经证实的案例。"


class IpAssetCreate(BaseModel):
    name: str = ""
    type: str = "expert"
    industry: str = ""
    targetAudience: str = ""
    businessGoal: str = ""
    mainPlatforms: list[str] = Field(default_factory=list)
    secondaryPlatforms: list[str] = Field(default_factory=list)
    tone: str = ""
    visualStyle: str = ""
    conversionPath: str = ""
    forbiddenExpressions: str = ""


class StrategyGenerateRequest(BaseModel):
    ipId: str


class StrategyUpdateRequest(BaseModel):
    positioning: str = ""
    targetUserProfile: str = ""
    corePainPoints: list[str] = Field(default_factory=list)
    platformRoles: dict[str, str] = Field(default_factory=dict)
    conversionPath: str = ""
    forbiddenDirections: list[str] = Field(default_factory=list)


class ColumnsGenerateRequest(BaseModel):
    ipId: str
    strategyId: str = ""


class ColumnUpdateRequest(BaseModel):
    name: str = ""
    positioning: str = ""
    platforms: list[str] = Field(default_factory=list)
    contentFormat: str = ""
    frequency: str = ""
    conversionAction: str = ""


class TopicsGenerateRequest(BaseModel):
    ipId: str
    columnId: str = ""
    count: int = Field(20, ge=1, le=60)


class DraftGenerateRequest(BaseModel):
    ipId: str
    topicId: str


class DraftUpdateRequest(BaseModel):
    painPoint: str = ""
    coreViewpoint: str = ""
    logic: str = ""
    cases: str = ""
    goldenSentences: list[str] = Field(default_factory=list)
    conversionAction: str = ""
    forbiddenExpressions: str = ""
    status: str = "generated"


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def fail(status_code: int, code: str, message: str, suggestion: str = "") -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "suggestion": suggestion},
    )


def parse_prefixed_id(value: str, prefix: str, code: str) -> int:
    raw = str(value or "").strip()
    pattern = rf"^{re.escape(prefix)}_(\d+)$"
    match = re.match(pattern, raw)
    if match:
        return int(match.group(1))
    if raw.isdigit():
        return int(raw)
    fail(400, "VALIDATION_ERROR", f"{prefix} ID 格式无效。", "请使用接口返回的 ID。")
    return 0


def require_fields(data: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if not str(data.get(field, "")).strip()]
    if missing:
        fail(400, "VALIDATION_ERROR", f"缺少必填字段：{', '.join(missing)}", "请补齐必填字段后重试。")


def profile_status(payload: dict[str, Any]) -> str:
    required = ["name", "type", "industry", "targetAudience", "businessGoal"]
    return "complete" if all(str(payload.get(field, "")).strip() for field in required) else "incomplete"


def get_user_ip(db: Session, ip_id: str, user: UserAccount) -> SprintIpAsset:
    numeric_id = parse_prefixed_id(ip_id, "ip", "IP_ASSET_NOT_FOUND")
    asset = db.query(SprintIpAsset).filter(
        SprintIpAsset.id == numeric_id,
        SprintIpAsset.user_id == user.id,
        SprintIpAsset.is_active.is_(True),
    ).first()
    if not asset:
        fail(404, "IP_ASSET_NOT_FOUND", "IP资产不存在或无权访问。")
    return asset


def get_user_topic(db: Session, topic_id: str, user: UserAccount) -> SprintTopic:
    numeric_id = parse_prefixed_id(topic_id, "topic", "TOPIC_NOT_FOUND")
    topic = db.query(SprintTopic).filter(
        SprintTopic.id == numeric_id,
        SprintTopic.user_id == user.id,
        SprintTopic.is_active.is_(True),
    ).first()
    if not topic:
        fail(404, "TOPIC_NOT_FOUND", "选题不存在或无权访问。")
    return topic


def get_user_strategy(db: Session, strategy_id: str, user: UserAccount) -> SprintContentStrategy:
    numeric_id = parse_prefixed_id(strategy_id, "strategy", "STRATEGY_NOT_FOUND")
    strategy = db.query(SprintContentStrategy).filter(
        SprintContentStrategy.id == numeric_id,
        SprintContentStrategy.user_id == user.id,
    ).first()
    if not strategy:
        fail(404, "STRATEGY_NOT_FOUND", "内容策略不存在或无权访问。")
    return strategy


def get_user_column(db: Session, column_id: str, user: UserAccount) -> SprintContentColumn:
    numeric_id = parse_prefixed_id(column_id, "column", "COLUMN_NOT_FOUND")
    column = db.query(SprintContentColumn).filter(
        SprintContentColumn.id == numeric_id,
        SprintContentColumn.user_id == user.id,
        SprintContentColumn.is_active.is_(True),
    ).first()
    if not column:
        fail(404, "COLUMN_NOT_FOUND", "栏目不存在或无权访问。")
    return column


def create_task(
    db: Session,
    user: UserAccount,
    task_type: str,
    input_snapshot: dict[str, Any],
    output_snapshot: Any,
    status: str = "succeeded",
) -> SprintGenerationTask:
    task = SprintGenerationTask(
        user_id=user.id,
        type=task_type,
        status=status,
        progress=100 if status == "succeeded" else 0,
        input_snapshot_json=dumps(input_snapshot),
        output_snapshot_json=dumps(output_snapshot),
        error_code="",
        error_message="",
    )
    db.add(task)
    db.flush()
    return task


@router.post("/api/ip-assets", summary="创建IP资产")
async def create_ip_asset(
    data: IpAssetCreate,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    payload = data.model_dump()
    require_fields(payload, ["name", "type", "industry", "targetAudience", "businessGoal"])

    asset = SprintIpAsset(
        user_id=user.id,
        name=payload["name"].strip(),
        type=payload["type"].strip(),
        industry=payload["industry"].strip(),
        target_audience=payload["targetAudience"].strip(),
        business_goal=payload["businessGoal"].strip(),
        main_platforms_json=dumps(payload["mainPlatforms"]),
        secondary_platforms_json=dumps(payload["secondaryPlatforms"]),
        tone=payload["tone"].strip(),
        visual_style=payload["visualStyle"].strip(),
        conversion_path=payload["conversionPath"].strip(),
        forbidden_expressions=payload["forbiddenExpressions"].strip(),
        profile_status=profile_status(payload),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"code": 0, "data": {"ipId": asset.to_dict()["id"], "asset": asset.to_dict()}, "message": "创建成功"}


@router.get("/api/ip-assets", summary="查询IP资产列表")
async def list_ip_assets(
    page: int = 1,
    pageSize: int = 20,
    type: str = "",
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    safe_page = max(page, 1)
    safe_page_size = min(max(pageSize, 1), 100)
    query = db.query(SprintIpAsset).filter(
        SprintIpAsset.user_id == user.id,
        SprintIpAsset.is_active.is_(True),
    )
    if type:
        query = query.filter(SprintIpAsset.type == type)
    total = query.count()
    items = (
        query.order_by(SprintIpAsset.updated_at.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {
        "code": 0,
        "data": {
            "items": [item.to_dict() for item in items],
            "total": total,
            "page": safe_page,
            "pageSize": safe_page_size,
        },
    }


@router.get("/api/ip-assets/{ip_id}", summary="查询IP资产详情")
async def get_ip_asset(
    ip_id: str,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    return {"code": 0, "data": get_user_ip(db, ip_id, user).to_dict()}


@router.put("/api/ip-assets/{ip_id}", summary="更新IP资产")
async def update_ip_asset(
    ip_id: str,
    data: IpAssetCreate,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    asset = get_user_ip(db, ip_id, user)
    payload = data.model_dump()
    require_fields(payload, ["name", "type", "industry", "targetAudience", "businessGoal"])
    asset.name = payload["name"].strip()
    asset.type = payload["type"].strip()
    asset.industry = payload["industry"].strip()
    asset.target_audience = payload["targetAudience"].strip()
    asset.business_goal = payload["businessGoal"].strip()
    asset.main_platforms_json = dumps(payload["mainPlatforms"])
    asset.secondary_platforms_json = dumps(payload["secondaryPlatforms"])
    asset.tone = payload["tone"].strip()
    asset.visual_style = payload["visualStyle"].strip()
    asset.conversion_path = payload["conversionPath"].strip()
    asset.forbidden_expressions = payload["forbiddenExpressions"].strip()
    asset.profile_status = profile_status(payload)
    db.commit()
    db.refresh(asset)
    return {"code": 0, "data": asset.to_dict(), "message": "更新成功"}


@router.post("/api/strategies/generate", summary="生成内容策略")
async def generate_strategy(
    data: StrategyGenerateRequest,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    asset = get_user_ip(db, data.ipId, user)
    asset_dict = asset.to_dict()
    strategy = SprintContentStrategy(
        user_id=user.id,
        ip_asset_id=asset.id,
        positioning=f"围绕{asset.industry}，以{asset.name}的专业视角帮助{asset.target_audience}做出可落地决策。",
        target_user_profile=f"核心用户是{asset.target_audience}，需要清晰判断标准、真实案例和可执行动作。",
        core_pain_points_json=dumps(["缺少判断框架", "信息过载难筛选", "需要可信案例", "不知道下一步怎么行动"]),
        platform_roles_json=dumps({
            "wechat": "沉淀深度方法论和案例文章",
            "xiaohongshu": "承接搜索和经验分享",
            "shipinhao": "建立信任和私域承接",
            "moments": "持续触达和咨询转化",
        }),
        conversion_path=asset.conversion_path or "内容建立认知 -> 私信咨询 -> 预约诊断 -> 服务转化",
        forbidden_directions_json=dumps([COMPLIANCE_FORBIDDEN_SUMMARY, "不制造过度焦虑"]),
        input_snapshot_json=dumps(asset_dict),
    )
    db.add(strategy)
    db.flush()
    task = create_task(db, user, "strategy_generate", {"ipId": data.ipId}, strategy.to_dict())
    strategy.task_id = task.id
    db.commit()
    db.refresh(strategy)
    return {"code": 0, "data": strategy.to_dict()}


@router.get("/api/strategies", summary="查询内容策略列表")
async def list_strategies(
    ipId: str = "",
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    query = db.query(SprintContentStrategy).filter(SprintContentStrategy.user_id == user.id)
    if ipId:
        query = query.filter(SprintContentStrategy.ip_asset_id == parse_prefixed_id(ipId, "ip", "VALIDATION_ERROR"))
    items = query.order_by(SprintContentStrategy.updated_at.desc()).all()
    return {"code": 0, "data": {"items": [item.to_dict() for item in items], "total": len(items)}}


@router.put("/api/strategies/{strategy_id}", summary="更新内容策略")
async def update_strategy(
    strategy_id: str,
    data: StrategyUpdateRequest,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    strategy = get_user_strategy(db, strategy_id, user)
    strategy.positioning = data.positioning
    strategy.target_user_profile = data.targetUserProfile
    strategy.core_pain_points_json = dumps(data.corePainPoints)
    strategy.platform_roles_json = dumps(data.platformRoles)
    strategy.conversion_path = data.conversionPath
    strategy.forbidden_directions_json = dumps(data.forbiddenDirections)
    db.commit()
    db.refresh(strategy)
    return {"code": 0, "data": strategy.to_dict(), "message": "保存成功"}


@router.post("/api/columns/generate", summary="生成栏目矩阵")
async def generate_columns(
    data: ColumnsGenerateRequest,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    asset = get_user_ip(db, data.ipId, user)
    strategy_id = parse_prefixed_id(data.strategyId, "strategy", "VALIDATION_ERROR") if data.strategyId else 0
    presets = [
        ("观点破局", "用强观点打破用户旧认知", ["shipinhao"], "观点口播", "每周2条", "引导评论区提问"),
        ("真实案例拆解", "用案例建立专业信任", ["wechat", "xiaohongshu"], "长文/图文", "每周1条", "引导预约诊断"),
        ("避坑清单", "降低用户决策风险", ["xiaohongshu", "moments"], "清单图文", "每周2条", "引导收藏和私信"),
        ("方法模板", "交付可复制方法", ["wechat", "xiaohongshu"], "模板教程", "每周1条", "引导领取资料"),
        ("问答快剪", "回应高频疑问", ["shipinhao"], "短视频口播", "每周3条", "引导关注"),
        ("私域转化", "持续触达潜在客户", ["moments"], "朋友圈短文", "每周5条", "引导私聊咨询"),
    ]
    generated = []
    for name, positioning, platforms, content_format, frequency, action in presets:
        column = SprintContentColumn(
            user_id=user.id,
            ip_asset_id=asset.id,
            strategy_id=strategy_id,
            name=name,
            positioning=f"{positioning}，服务于{asset.business_goal}。",
            platforms_json=dumps(platforms),
            content_format=content_format,
            frequency=frequency,
            conversion_action=action,
        )
        db.add(column)
        db.flush()
        generated.append(column.to_dict())
    task = create_task(db, user, "columns_generate", data.model_dump(), generated)
    db.commit()
    return {"code": 0, "data": {"taskId": task.to_dict()["taskId"], "items": generated}}


@router.get("/api/columns", summary="查询栏目矩阵列表")
async def list_columns(
    ipId: str = "",
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    query = db.query(SprintContentColumn).filter(
        SprintContentColumn.user_id == user.id,
        SprintContentColumn.is_active.is_(True),
    )
    if ipId:
        query = query.filter(SprintContentColumn.ip_asset_id == parse_prefixed_id(ipId, "ip", "VALIDATION_ERROR"))
    items = query.order_by(SprintContentColumn.created_at.asc(), SprintContentColumn.id.asc()).all()
    return {"code": 0, "data": {"items": [item.to_dict() for item in items], "total": len(items)}}


@router.put("/api/columns/{column_id}", summary="更新栏目")
async def update_column(
    column_id: str,
    data: ColumnUpdateRequest,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    column = get_user_column(db, column_id, user)
    if not data.name.strip():
        fail(400, "VALIDATION_ERROR", "栏目名称不能为空。")
    column.name = data.name.strip()
    column.positioning = data.positioning
    column.platforms_json = dumps(data.platforms)
    column.content_format = data.contentFormat
    column.frequency = data.frequency
    column.conversion_action = data.conversionAction
    db.commit()
    db.refresh(column)
    return {"code": 0, "data": column.to_dict(), "message": "保存成功"}


@router.delete("/api/columns/{column_id}", summary="删除栏目")
async def delete_column(
    column_id: str,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    column = get_user_column(db, column_id, user)
    column.is_active = False
    db.query(SprintTopic).filter(
        SprintTopic.user_id == user.id,
        SprintTopic.column_id == column.id,
        SprintTopic.is_active.is_(True),
    ).update({"is_active": False}, synchronize_session=False)
    db.commit()
    return {"code": 0, "data": {"columnId": column_id, "deleted": True}, "message": "删除成功"}


@router.post("/api/topics/generate", summary="批量生成选题")
async def generate_topics(
    data: TopicsGenerateRequest,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    asset = get_user_ip(db, data.ipId, user)
    query = db.query(SprintContentColumn).filter(
        SprintContentColumn.user_id == user.id,
        SprintContentColumn.ip_asset_id == asset.id,
        SprintContentColumn.is_active.is_(True),
    )
    if data.columnId:
        query = query.filter(SprintContentColumn.id == parse_prefixed_id(data.columnId, "column", "VALIDATION_ERROR"))
    available_columns = query.order_by(SprintContentColumn.id).all()
    if not available_columns:
        fail(400, "VALIDATION_ERROR", "请先生成栏目矩阵。", "生成栏目后再批量生成选题。")

    generated = []
    for index in range(data.count):
        column = available_columns[index % len(available_columns)]
        topic = SprintTopic(
            user_id=user.id,
            ip_asset_id=asset.id,
            column_id=column.id,
            title=f"{column.name}：{asset.target_audience}必须知道的第{index + 1}个关键判断",
            platforms_json=column.platforms_json,
            content_goal="trust_building" if index % 3 else "conversion",
            user_pain_point="知道问题存在，但缺少具体判断标准和行动步骤。",
            core_viewpoint="真正有效的内容不是讲道理，而是给用户一个马上能用的判断框架。",
            status="todo",
            priority="high" if index < 6 else "medium",
        )
        db.add(topic)
        db.flush()
        generated.append(topic.to_dict())
    task = create_task(db, user, "topics_generate", data.model_dump(), generated)
    db.commit()
    return {"code": 0, "data": {"taskId": task.to_dict()["taskId"], "items": generated}}


@router.get("/api/topics", summary="查询选题列表")
async def list_topics(
    ipId: str = "",
    platform: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    query = db.query(SprintTopic).filter(
        SprintTopic.user_id == user.id,
        SprintTopic.is_active.is_(True),
    )
    if ipId:
        query = query.filter(SprintTopic.ip_asset_id == parse_prefixed_id(ipId, "ip", "VALIDATION_ERROR"))
    if status:
        query = query.filter(SprintTopic.status == status)
    items = query.order_by(SprintTopic.created_at.desc()).all()
    data = [item.to_dict() for item in items]
    if platform:
        data = [item for item in data if platform in item.get("platforms", [])]
    return {"code": 0, "data": {"items": data, "total": len(data)}}


@router.get("/api/content-drafts", summary="查询内容母稿列表")
async def list_content_drafts(
    ipId: str = "",
    topicId: str = "",
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    query = db.query(SprintContentDraft).filter(SprintContentDraft.user_id == user.id)
    if ipId:
        query = query.filter(SprintContentDraft.ip_asset_id == parse_prefixed_id(ipId, "ip", "VALIDATION_ERROR"))
    if topicId:
        query = query.filter(SprintContentDraft.topic_id == parse_prefixed_id(topicId, "topic", "VALIDATION_ERROR"))
    items = query.order_by(SprintContentDraft.updated_at.desc()).all()
    return {"code": 0, "data": {"items": [item.to_dict() for item in items], "total": len(items)}}


@router.post("/api/content-drafts/generate", summary="生成内容母稿")
async def generate_content_draft(
    data: DraftGenerateRequest,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    asset = get_user_ip(db, data.ipId, user)
    topic = get_user_topic(db, data.topicId, user)
    if topic.ip_asset_id != asset.id:
        fail(404, "TOPIC_NOT_FOUND", "选题不属于当前IP。")
    draft = SprintContentDraft(
        user_id=user.id,
        ip_asset_id=asset.id,
        topic_id=topic.id,
        pain_point=topic.user_pain_point,
        core_viewpoint=topic.core_viewpoint,
        logic="先指出常见误区，再给出判断框架，最后用案例和行动建议完成转化。",
        cases="一个用户原本只看热门方向，后来按门槛、资源、周期重新评估，选择更匹配自己的路径。",
        golden_sentences_json=dumps(["方向不是被推荐出来的，而是用自己的筹码算出来的。", "好内容要让用户下一步能行动。"]),
        conversion_action="引导用户私信发送当前问题，领取一页诊断清单。",
        forbidden_expressions=COMPLIANCE_FORBIDDEN_SUMMARY,
        status="generated",
        version=1,
    )
    db.add(draft)
    db.flush()
    task = create_task(db, user, "draft_generate", data.model_dump(), draft.to_dict())
    draft.task_id = task.id
    topic.status = "drafted"
    db.commit()
    db.refresh(draft)
    return {"code": 0, "data": draft.to_dict()}


@router.put("/api/content-drafts/{draft_id}", summary="更新内容母稿")
async def update_content_draft(
    draft_id: str,
    data: DraftUpdateRequest,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    numeric_id = parse_prefixed_id(draft_id, "draft", "DRAFT_NOT_FOUND")
    draft = db.query(SprintContentDraft).filter(
        SprintContentDraft.id == numeric_id,
        SprintContentDraft.user_id == user.id,
    ).first()
    if not draft:
        fail(404, "DRAFT_NOT_FOUND", "内容母稿不存在或无权访问。")
    draft.pain_point = data.painPoint
    draft.core_viewpoint = data.coreViewpoint
    draft.logic = data.logic
    draft.cases = data.cases
    draft.golden_sentences_json = dumps(data.goldenSentences)
    draft.conversion_action = data.conversionAction
    draft.forbidden_expressions = data.forbiddenExpressions
    draft.status = data.status
    draft.version = int(draft.version or 1) + 1
    db.commit()
    db.refresh(draft)
    return {"code": 0, "data": draft.to_dict(), "message": "保存成功"}


@router.post("/api/materials/upload", summary="上传素材")
async def upload_material(
    ipId: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    ip_numeric_id = 0
    if ipId:
        ip_numeric_id = get_user_ip(db, ipId, user).id
    if not file.filename:
        fail(400, "MATERIAL_UPLOAD_FAILED", "素材文件无效。")

    filename = file.filename.strip()
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content_type = file.content_type or "application/octet-stream"
    if extension not in ALLOWED_MATERIAL_EXTENSIONS or content_type not in ALLOWED_MATERIAL_TYPES:
        fail(400, "MATERIAL_UPLOAD_FAILED", "仅支持 txt、md 和常见图片素材。", "请上传 .txt、.md、.png、.jpg、.webp 或 .gif 文件。")

    content = await file.read()
    file_size = len(content)
    if file_size > MAX_MATERIAL_SIZE:
        fail(400, "MATERIAL_UPLOAD_FAILED", "素材文件不能超过 5MB。", "请压缩素材或改为上传文本摘要。")

    material = SprintMaterial(
        user_id=user.id,
        ip_asset_id=ip_numeric_id,
        filename=filename,
        content_type=content_type,
        file_size=file_size,
        status="uploaded",
    )
    db.add(material)
    db.flush()
    material.url = f"/api/materials/{material.id}/mock-file"
    db.commit()
    db.refresh(material)
    return {"code": 0, "data": material.to_dict(), "message": "上传成功"}


@router.get("/api/generation-tasks/{task_id}", summary="查询生成任务状态")
async def get_generation_task(
    task_id: str,
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    numeric_id = parse_prefixed_id(task_id, "task", "TASK_NOT_FOUND")
    task = db.query(SprintGenerationTask).filter(
        SprintGenerationTask.id == numeric_id,
        SprintGenerationTask.user_id == user.id,
    ).first()
    if not task:
        fail(404, "TASK_NOT_FOUND", "生成任务不存在或无权访问。")
    return {"code": 0, "data": task.to_dict()}
