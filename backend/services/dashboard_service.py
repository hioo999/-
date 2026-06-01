"""Dashboard aggregation service for the lightweight home page."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models.persona import AIModelConfig, ContentTopic, GenerationTask, IpProject, PlatformContent, UnifiedAsset, UserAccount


def _count_assets_by_type(db: Session, user: UserAccount, asset_type: str) -> int:
    return db.query(UnifiedAsset).filter(
        UnifiedAsset.user_id == user.id,
        UnifiedAsset.asset_type == asset_type,
        UnifiedAsset.is_deleted.is_(False),
    ).count()


def _model_ready(db: Session, user: UserAccount, model_type: str) -> bool:
    return db.query(AIModelConfig).filter(
        AIModelConfig.is_active.is_(True),
        AIModelConfig.model_type.in_([model_type, "multimodal"]),
        or_(AIModelConfig.user_id == 0, AIModelConfig.user_id == user.id),
    ).first() is not None


def _ip_completeness(db: Session, user: UserAccount) -> dict:
    project = db.query(IpProject).filter(
        IpProject.user_id == user.id,
        IpProject.is_active.is_(True),
    ).order_by(IpProject.updated_at.desc()).first()
    topics_count = db.query(ContentTopic).filter(
        ContentTopic.user_id == user.id,
        ContentTopic.is_active.is_(True),
    ).count()

    if not project:
        return {"value": 20, "missingItems": ["IP 项目", "人设定位", "内容选题", "平台策略"]}

    checks = [
        (bool(project.name), "IP 项目"),
        (bool((project.positioning or "").strip()), "人设定位"),
        (bool((project.target_audience or "").strip()), "目标受众"),
        (bool((project.default_platforms_json or "[]") != "[]"), "平台策略"),
        (topics_count > 0, "内容选题"),
    ]
    passed = sum(1 for ok, _ in checks if ok)
    missing = [label for ok, label in checks if not ok]
    return {"value": max(20, int(passed / len(checks) * 100)), "missingItems": missing}


def get_dashboard_overview(db: Session, user: UserAccount) -> dict:
    active_contents = db.query(PlatformContent).filter(
        PlatformContent.user_id == user.id,
        PlatformContent.is_active.is_(True),
    )
    active_assets = db.query(UnifiedAsset).filter(
        UnifiedAsset.user_id == user.id,
        UnifiedAsset.is_deleted.is_(False),
    )
    tasks = db.query(GenerationTask).filter(GenerationTask.user_id == user.id)

    running_tasks = tasks.filter(GenerationTask.status.in_(["pending", "running", "retrying"])).count()
    failed_tasks = tasks.filter(GenerationTask.status == "failed").count()
    pending_publish = active_contents.filter(PlatformContent.status.in_(["generated", "editing", "ready", "ready_to_publish"])).count()

    recent_contents = active_contents.order_by(PlatformContent.updated_at.desc()).limit(6).all()
    recent_tasks = tasks.order_by(GenerationTask.updated_at.desc()).limit(6).all()
    last_content_at = active_contents.with_entities(func.max(PlatformContent.updated_at)).scalar()
    last_task_at = tasks.with_entities(func.max(GenerationTask.updated_at)).scalar()
    last_activity_at = max([value for value in [last_content_at, last_task_at] if value], default=None)

    completeness = _ip_completeness(db, user)
    today_actions = []
    if completeness["missingItems"]:
        today_actions.append({
            "title": "补齐 IP 档案",
            "status": "下一步",
            "owner": "人设定位/平台配置",
            "action": "去完善",
            "actionKey": "sprint1",
        })
    today_actions.extend([
        {
            "title": "创建内容选题并输入素材",
            "status": "可开始",
            "owner": "IP 项目/选题/素材",
            "action": "去生产中心",
            "actionKey": "ip",
        },
        {
            "title": "查看任务和资产状态",
            "status": "可追踪",
            "owner": "统一任务/资产库",
            "action": "去工作台",
            "actionKey": "platform",
        },
    ])
    if failed_tasks:
        today_actions.insert(0, {
            "title": "处理失败任务",
            "status": "待处理",
            "owner": f"{failed_tasks} 个任务失败",
            "action": "去任务中心",
            "actionKey": "platform",
        })

    return {
        "ipCompleteness": completeness,
        "taskSummary": {
            "total": tasks.count(),
            "running": running_tasks,
            "failed": failed_tasks,
            "pendingPublish": pending_publish,
        },
        "assetSummary": {
            "total": active_assets.count(),
            "scripts": _count_assets_by_type(db, user, "text"),
            "images": _count_assets_by_type(db, user, "image"),
            "publishPackages": active_contents.count(),
        },
        "modelStatus": {
            "textReady": _model_ready(db, user, "text"),
            "imageReady": _model_ready(db, user, "image"),
            "videoReady": _model_ready(db, user, "video"),
        },
        "todayActions": today_actions[:5],
        "recentContents": [item.to_dict(include_content=False) for item in recent_contents],
        "recentTasks": [item.to_dict() for item in recent_tasks],
        "lastActivityAt": last_activity_at.isoformat() if last_activity_at else None,
    }
