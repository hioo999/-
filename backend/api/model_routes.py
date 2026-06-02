"""Model gateway, discovery, and default model APIs."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth_routes import get_admin_user, get_current_user
from database import get_db
from models.persona import AIModelConfig, ModelGateway, UserAccount, UserModelDefault
from services.model_security import decrypt_secret, encrypt_secret
from video_engine.pixelle_video.utils.llm_util import fetch_available_models, test_llm_connection


router = APIRouter(prefix="/api", tags=["模型中转"])

MODEL_TYPES = {"text", "image", "video", "multimodal"}
ALLOW_PRIVATE_GATEWAY_URLS = os.getenv("MODEL_GATEWAY_ALLOW_PRIVATE_URLS", "").lower() in {"1", "true", "yes"}
_SECRET_RE = re.compile(r"(authorization|api[-_]?key|token|secret|password)(\s*[=:]\s*)(bearer\s+)?[^\s,;]+", re.I)
_BEARER_RE = re.compile(r"\bbearer\s+[^\s,;]+", re.I)


class ModelGatewayCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    base_url: str = Field("https://api.openai.com/v1", min_length=1, max_length=500)
    api_key: str = Field("", description="API Key")
    provider_type: str = Field("openai_compatible", max_length=80)
    is_active: bool = True
    scope: str = Field("user", description="user/global，global 仅管理员可用")


class ModelGatewayUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    base_url: str = Field("https://api.openai.com/v1", min_length=1, max_length=500)
    api_key: str = Field("", description="留空表示不更新 API Key")
    provider_type: str = Field("openai_compatible", max_length=80)
    is_active: bool = True
    scope: str = Field("user", description="user/global，global 仅管理员可用")


class ModelCapabilityUpdate(BaseModel):
    model_type: str = Field(..., description="text/image/video/multimodal/unknown")
    recommendation_label: str = Field("", max_length=120)
    recommendation_reason: str = ""
    risk_note: str = ""
    sort_order: int = 0
    is_active: bool = True


class ModelDefaultUpdate(BaseModel):
    model_type: str = Field(..., description="text/image/video/multimodal")
    model_config_id: int = Field(0, description="0 表示清空个人默认")


def _guess_model_type(model_id: str) -> str:
    value = model_id.lower()
    image_markers = ["flux", "sd", "stable-diffusion", "dall-e", "midjourney", "imagen", "image"]
    video_markers = ["kling", "runway", "hailuo", "veo", "sora", "video", "wan", "jimeng"]
    multimodal_markers = ["vision", "vl", "omni", "qwen-vl", "gpt-4o", "gemini"]
    text_markers = ["gpt", "claude", "kimi", "qwen", "deepseek", "llama", "mistral", "minimax"]
    if any(marker in value for marker in video_markers):
        return "video"
    if any(marker in value for marker in image_markers):
        return "image"
    if any(marker in value for marker in multimodal_markers):
        return "multimodal"
    if any(marker in value for marker in text_markers):
        return "text"
    return "unknown"


def _sanitize_gateway_message(message: str) -> str:
    value = _SECRET_RE.sub(r"\1\2[redacted]", str(message or ""))
    value = _BEARER_RE.sub("Bearer [redacted]", value)
    return value[:300]


def _validate_gateway_base_url(value: str) -> str:
    base_url = (value or "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="模型中转地址必须是有效的 http/https URL")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="模型中转地址不能包含用户名或密码")
    if parsed.scheme != "https" and not ALLOW_PRIVATE_GATEWAY_URLS:
        raise HTTPException(status_code=400, detail="模型中转地址必须使用 HTTPS")

    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="模型中转地址域名无法解析") from None

    addresses = {info[4][0] for info in infos}
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            raise HTTPException(status_code=400, detail="模型中转地址解析结果无效") from None
        if not ALLOW_PRIVATE_GATEWAY_URLS and not ip.is_global:
            raise HTTPException(status_code=400, detail="模型中转地址不能指向本机、内网或保留地址")
    return base_url


def _recommendation_for(model_type: str) -> tuple[str, str, str]:
    if model_type == "text":
        return "推荐用于口播文案", "适合脚本、标题、提示词和分镜文案生成。", ""
    if model_type == "image":
        return "推荐用于图片生成", "适合封面、主体清理、四视图和分镜图任务。", "请确认中转服务支持图片生成协议。"
    if model_type == "video":
        return "推荐用于视频生成", "适合最终视频、图生视频或文生视频任务。", "视频模型通常耗时和成本更高。"
    if model_type == "multimodal":
        return "推荐用于图文理解", "适合素材解析、参考图理解和图文混合任务。", ""
    return "待标注能力", "系统无法可靠识别该模型能力，请手动标注后再用于生成。", "未标注前不建议直接用于生成。"


def _gateway_query(db: Session, user: UserAccount):
    return db.query(ModelGateway).filter(
        ModelGateway.is_active.is_(True),
        or_(ModelGateway.user_id == user.id, ModelGateway.scope == "global"),
    )


def _get_gateway(db: Session, gateway_id: int, user: UserAccount) -> ModelGateway:
    gateway = _gateway_query(db, user).filter(ModelGateway.id == gateway_id).first()
    if not gateway:
        raise HTTPException(status_code=404, detail="模型中转配置不存在")
    return gateway


def _model_visible_to_user(model: AIModelConfig, user: UserAccount) -> bool:
    return bool((model.user_id or 0) in (0, user.id))


def _active_catalog_query(db: Session, user: UserAccount, model_type: str = ""):
    query = db.query(AIModelConfig).filter(
        AIModelConfig.is_active.is_(True),
        or_(AIModelConfig.user_id == 0, AIModelConfig.user_id == user.id),
    )
    if model_type:
        query = query.filter(AIModelConfig.model_type.in_([model_type, "multimodal"]))
    return query.order_by(AIModelConfig.is_default.desc(), AIModelConfig.sort_order, AIModelConfig.id)


def _resolve_model(db: Session, user: UserAccount, model_type: str) -> tuple[AIModelConfig | None, str]:
    personal = db.query(UserModelDefault).filter(
        UserModelDefault.user_id == user.id,
        UserModelDefault.model_type == model_type,
    ).first()
    if personal and personal.model_config_id:
        model = db.query(AIModelConfig).filter(
            AIModelConfig.id == personal.model_config_id,
            AIModelConfig.is_active.is_(True),
        ).first()
        if model and _model_visible_to_user(model, user):
            return model, "user_default"

    global_default = db.query(AIModelConfig).filter(
        AIModelConfig.model_type == model_type,
        AIModelConfig.is_default.is_(True),
        AIModelConfig.is_active.is_(True),
        AIModelConfig.user_id == 0,
    ).order_by(AIModelConfig.sort_order, AIModelConfig.id).first()
    if global_default:
        return global_default, "global_default"

    fallback = _active_catalog_query(db, user, model_type).first()
    if fallback:
        return fallback, "recommendation_fallback"
    return None, "none"


def _model_with_resolution(model: AIModelConfig | None, resolved_by: str) -> dict | None:
    if not model:
        return None
    data = model.to_dict()
    data["resolved_by"] = resolved_by
    return data


@router.get("/model-gateways", summary="获取当前用户可用模型中转配置")
async def list_model_gateways(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    gateways = _gateway_query(db, current_user).order_by(ModelGateway.scope, ModelGateway.id.desc()).all()
    return {"code": 0, "data": [gateway.to_dict() for gateway in gateways]}


@router.post("/model-gateways", summary="创建模型中转配置")
async def create_model_gateway(
    data: ModelGatewayCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    scope = "global" if data.scope == "global" and current_user.is_admin else "user"
    base_url = _validate_gateway_base_url(data.base_url)
    gateway = ModelGateway(
        user_id=0 if scope == "global" else current_user.id,
        scope=scope,
        name=data.name.strip(),
        provider_type=data.provider_type or "openai_compatible",
        base_url=base_url,
        api_key_encrypted=encrypt_secret(data.api_key),
        is_active=data.is_active,
    )
    db.add(gateway)
    db.commit()
    db.refresh(gateway)
    return {"code": 0, "data": gateway.to_dict(), "message": "模型中转配置已创建"}


@router.put("/model-gateways/{gateway_id}", summary="更新模型中转配置")
async def update_model_gateway(
    gateway_id: int,
    data: ModelGatewayUpdate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    gateway = _get_gateway(db, gateway_id, current_user)
    if gateway.scope == "global" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    scope = "global" if data.scope == "global" and current_user.is_admin else "user"
    base_url = _validate_gateway_base_url(data.base_url)
    gateway.scope = scope
    gateway.user_id = 0 if scope == "global" else current_user.id
    gateway.name = data.name.strip()
    gateway.provider_type = data.provider_type or "openai_compatible"
    gateway.base_url = base_url
    gateway.is_active = data.is_active
    if data.api_key.strip():
        gateway.api_key_encrypted = encrypt_secret(data.api_key)
    db.commit()
    db.refresh(gateway)
    return {"code": 0, "data": gateway.to_dict(), "message": "模型中转配置已更新"}


@router.delete("/model-gateways/{gateway_id}", summary="停用模型中转配置")
async def delete_model_gateway(
    gateway_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    gateway = _get_gateway(db, gateway_id, current_user)
    if gateway.scope == "global" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    gateway.is_active = False
    db.query(AIModelConfig).filter(AIModelConfig.gateway_id == gateway.id).update(
        {AIModelConfig.is_active: False, AIModelConfig.is_default: False}, synchronize_session=False
    )
    db.commit()
    return {"code": 0, "message": "模型中转配置已停用"}


@router.post("/model-gateways/{gateway_id}/test", summary="测试模型中转连接")
async def test_model_gateway(
    gateway_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    gateway = _get_gateway(db, gateway_id, current_user)
    if gateway.scope == "global" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="全局中转测试需要管理员权限")
    base_url = _validate_gateway_base_url(gateway.base_url)
    api_key = decrypt_secret(gateway.api_key_encrypted)
    ok, message, model_count = test_llm_connection(api_key, base_url, timeout=15.0)
    message = _sanitize_gateway_message(message)
    gateway.last_test_status = "succeeded" if ok else "failed"
    gateway.last_test_message = message
    gateway.last_model_count = model_count
    db.commit()
    return {"code": 0, "data": {"ok": ok, "message": message, "model_count": model_count}}


@router.post("/model-gateways/{gateway_id}/sync-models", summary="从中转配置同步模型列表")
async def sync_model_gateway_models(
    gateway_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    gateway = _get_gateway(db, gateway_id, current_user)
    if gateway.scope == "global" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="全局中转同步需要管理员权限")
    base_url = _validate_gateway_base_url(gateway.base_url)
    api_key = decrypt_secret(gateway.api_key_encrypted)
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 无效或无法解密")
    try:
        model_ids = fetch_available_models(api_key, base_url, timeout=20.0)
    except Exception as exc:
        message = _sanitize_gateway_message(str(exc)) or "中转服务不可用或返回异常"
        gateway.last_test_status = "failed"
        gateway.last_test_message = message
        db.commit()
        raise HTTPException(status_code=400, detail=f"拉取模型失败：{message}") from exc

    now = datetime.utcnow()
    synced: list[AIModelConfig] = []
    for model_id in model_ids:
        model = db.query(AIModelConfig).filter(
            AIModelConfig.gateway_id == gateway.id,
            AIModelConfig.model_id == model_id,
        ).first()
        guessed_type = _guess_model_type(model_id)
        label, reason, risk = _recommendation_for(guessed_type)
        if not model:
            model = AIModelConfig(
                user_id=gateway.user_id or 0,
                gateway_id=gateway.id,
                name=model_id,
                model_type=guessed_type,
                provider=gateway.name,
                api_key=gateway.api_key_encrypted,
                base_url=gateway.base_url,
                model_id=model_id,
                is_openai_compatible=True,
                is_default=False,
                is_active=guessed_type != "unknown",
                recommendation_label=label,
                recommendation_reason=reason,
                risk_note=risk,
                last_seen_at=now,
            )
            db.add(model)
        else:
            model.user_id = gateway.user_id or 0
            model.api_key = gateway.api_key_encrypted
            model.base_url = gateway.base_url
            model.provider = gateway.name
            model.last_seen_at = now
            if model.model_type == "unknown" and guessed_type != "unknown":
                model.model_type = guessed_type
                model.is_active = True
                model.recommendation_label = label
                model.recommendation_reason = reason
                model.risk_note = risk
        synced.append(model)

    gateway.last_test_status = "succeeded"
    gateway.last_test_message = f"已同步 {len(model_ids)} 个模型"
    gateway.last_model_count = len(model_ids)
    gateway.last_synced_at = now
    db.commit()
    for model in synced:
        db.refresh(model)
    return {"code": 0, "data": [model.to_dict() for model in synced], "message": gateway.last_test_message}


@router.get("/models/catalog", summary="获取当前用户可用模型目录")
async def list_model_catalog(
    model_type: str = "",
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    if model_type:
        models = _active_catalog_query(db, current_user, model_type).all()
    else:
        models = db.query(AIModelConfig).filter(
            or_(AIModelConfig.user_id == 0, AIModelConfig.user_id == current_user.id),
        ).order_by(AIModelConfig.is_active.desc(), AIModelConfig.sort_order, AIModelConfig.id).all()
    return {"code": 0, "data": [model.to_dict() for model in models]}


@router.patch("/models/catalog/{model_id}", summary="更新模型能力和推荐信息")
async def update_model_catalog_item(
    model_id: int,
    data: ModelCapabilityUpdate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    model = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
    if not model or not _model_visible_to_user(model, current_user):
        raise HTTPException(status_code=404, detail="模型不存在")
    if (model.user_id or 0) == 0 and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="全局模型需要管理员权限")
    model.model_type = data.model_type
    model.recommendation_label = data.recommendation_label
    model.recommendation_reason = data.recommendation_reason
    model.risk_note = data.risk_note
    model.sort_order = data.sort_order
    model.is_active = data.is_active and data.model_type != "unknown"
    db.commit()
    db.refresh(model)
    return {"code": 0, "data": model.to_dict(), "message": "模型信息已更新"}


@router.get("/model-defaults", summary="获取个人默认、全局默认和解析结果")
async def get_model_defaults(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    payload: dict[str, dict] = {}
    for model_type in sorted(MODEL_TYPES):
        personal = db.query(UserModelDefault).filter(
            UserModelDefault.user_id == current_user.id,
            UserModelDefault.model_type == model_type,
        ).first()
        personal_model = None
        if personal and personal.model_config_id:
            personal_model = db.query(AIModelConfig).filter(AIModelConfig.id == personal.model_config_id).first()
            if personal_model and not _model_visible_to_user(personal_model, current_user):
                personal_model = None
        global_model = db.query(AIModelConfig).filter(
            AIModelConfig.model_type == model_type,
            AIModelConfig.is_default.is_(True),
            AIModelConfig.is_active.is_(True),
            AIModelConfig.user_id == 0,
        ).first()
        resolved, resolved_by = _resolve_model(db, current_user, model_type)
        payload[model_type] = {
            "personal": personal_model.to_dict() if personal_model else None,
            "global": global_model.to_dict() if global_model else None,
            "resolved": _model_with_resolution(resolved, resolved_by),
        }
    return {"code": 0, "data": payload}


@router.put("/model-defaults", summary="设置个人默认模型")
async def set_model_default(
    data: ModelDefaultUpdate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    if data.model_type not in MODEL_TYPES:
        raise HTTPException(status_code=400, detail="模型类型不支持")
    if data.model_config_id:
        model = db.query(AIModelConfig).filter(
            AIModelConfig.id == data.model_config_id,
            AIModelConfig.is_active.is_(True),
        ).first()
        if not model or not _model_visible_to_user(model, current_user):
            raise HTTPException(status_code=404, detail="模型不存在或不可用")
        if model.model_type not in [data.model_type, "multimodal"]:
            raise HTTPException(status_code=400, detail="模型能力与默认类型不匹配")

    item = db.query(UserModelDefault).filter(
        UserModelDefault.user_id == current_user.id,
        UserModelDefault.model_type == data.model_type,
    ).first()
    if not item:
        item = UserModelDefault(user_id=current_user.id, model_type=data.model_type)
        db.add(item)
    item.model_config_id = data.model_config_id
    db.commit()
    db.refresh(item)
    return {"code": 0, "data": item.to_dict(), "message": "个人默认模型已更新"}


@router.put("/admin/model-defaults", summary="设置全局默认模型")
async def set_global_model_default(
    data: ModelDefaultUpdate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_admin_user),
):
    if data.model_type not in MODEL_TYPES:
        raise HTTPException(status_code=400, detail="模型类型不支持")
    db.query(AIModelConfig).filter(
        AIModelConfig.model_type == data.model_type,
        AIModelConfig.user_id == 0,
    ).update(
        {AIModelConfig.is_default: False}, synchronize_session=False
    )
    model = None
    if data.model_config_id:
        model = db.query(AIModelConfig).filter(
            AIModelConfig.id == data.model_config_id,
            AIModelConfig.is_active.is_(True),
            AIModelConfig.user_id == 0,
        ).first()
        if not model:
            raise HTTPException(status_code=404, detail="全局模型不存在或不可用")
        if model.model_type not in [data.model_type, "multimodal"]:
            raise HTTPException(status_code=400, detail="模型能力与默认类型不匹配")
        model.is_default = True
    db.commit()
    if model:
        db.refresh(model)
    return {"code": 0, "data": model.to_dict() if model else None, "message": "全局默认模型已更新"}


@router.get("/models/resolve-default", summary="解析当前任务默认模型")
async def resolve_default_model(
    model_type: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    if model_type not in MODEL_TYPES:
        raise HTTPException(status_code=400, detail="模型类型不支持")
    model, resolved_by = _resolve_model(db, current_user, model_type)
    return {"code": 0, "data": _model_with_resolution(model, resolved_by)}
