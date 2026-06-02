"""微信公众号排版与草稿箱发布接口。"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth_routes import get_current_user
from database import get_db
from models.persona import AdminOperationLog, GenerationTask, PlatformContent, UnifiedAsset, UserAccount, WechatAccount, WechatDraftRecord, WechatMaterialCache
from services.wechat_publisher import (
    WechatAccountConfig,
    WechatPublishError,
    decrypt_secret,
    encrypt_secret,
    explain_wechat_error,
    get_access_token,
    list_remote_themes,
    preflight_wechat_article,
    probe_wechat_capabilities,
    publish_markdown_to_draft,
    render_markdown_for_wechat,
)


router = APIRouter(prefix="/api/wechat", tags=["微信公众号"])


class WechatAccountPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    appId: str = Field(..., min_length=1, max_length=120)
    appSecret: str = Field("", max_length=300)
    originalId: str = Field("", max_length=120)
    feishuAccount: str = Field("", max_length=200)
    themeId: str = Field("", max_length=120)
    apiBase: str = Field("https://feishu2weixin.maolai.cc", max_length=300)
    defaultCoverUrl: str = Field("", max_length=500)
    notes: str = Field("", max_length=1000)
    isDefault: bool = False
    isActive: bool = True

    @field_validator("name", "appId")
    @classmethod
    def strip_required(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("必填字段不能为空")
        return result


class WechatPreviewPayload(BaseModel):
    title: str = Field("未命名公众号文章", max_length=200)
    rawContent: str = Field(..., min_length=1, max_length=80000)
    style: str = Field("knowledge", max_length=80)
    accountId: int | None = None
    feishuAccount: str = Field("", max_length=200)
    themeId: str = Field("", max_length=120)
    apiBase: str = Field("https://feishu2weixin.maolai.cc", max_length=300)


class WechatDraftPayload(BaseModel):
    accountId: int = Field(..., ge=1)
    platformContentId: int = Field(0, ge=0)
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field("", max_length=100)
    digest: str = Field("", max_length=240)
    rawContent: str = Field(..., min_length=1, max_length=80000)
    coverUrl: str = Field("", max_length=500)
    contentSourceUrl: str = Field("", max_length=500)
    style: str = Field("knowledge", max_length=80)
    idempotencyKey: str = Field("", max_length=120)

    @field_validator("title", "rawContent")
    @classmethod
    def strip_required(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("标题和正文不能为空")
        return result


class ThemeListPayload(BaseModel):
    feishuAccount: str = Field(..., min_length=1, max_length=200)
    apiBase: str = Field("https://feishu2weixin.maolai.cc", max_length=300)


class WechatPreflightPayload(BaseModel):
    accountId: int | None = Field(None, ge=1)
    title: str = Field("", max_length=200)
    digest: str = Field("", max_length=240)
    rawContent: str = Field("", max_length=80000)
    coverUrl: str = Field("", max_length=500)


def _get_account(db: Session, account_id: int, user: UserAccount) -> WechatAccount:
    account = db.query(WechatAccount).filter(
        WechatAccount.id == account_id,
        WechatAccount.is_active.is_(True),
    ).first()
    if not account or not _account_visible_to_user(account, user):
        raise HTTPException(status_code=404, detail="公众号账号不存在")
    return account


def _get_account_for_admin(db: Session, account_id: int, user: UserAccount) -> WechatAccount:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    account = db.query(WechatAccount).filter(WechatAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号账号不存在")
    return account


def _authorized_user_ids(account: WechatAccount) -> list[int]:
    try:
        parsed = json.loads(account.authorized_user_ids_json or "[]")
        return [int(item) for item in parsed if str(item).isdigit()]
    except Exception:
        return []


def _account_visible_to_user(account: WechatAccount, user: UserAccount) -> bool:
    if user.is_admin:
        return True
    if account.user_id == user.id and account.scope == "user":
        return True
    if account.scope in ("system", "global", "admin"):
        authorized = _authorized_user_ids(account)
        return not authorized or user.id in authorized
    return False


def _account_query_for_user(db: Session, user: UserAccount):
    query = db.query(WechatAccount).filter(WechatAccount.is_active.is_(True))
    if user.is_admin:
        return query
    return query.filter(or_(WechatAccount.user_id == user.id, WechatAccount.scope.in_(["system", "global", "admin"])))


def _apply_default_account(db: Session, user: UserAccount, account: WechatAccount, is_default: bool):
    if not is_default:
        account.is_default = False
        return
    if user.is_admin:
        db.query(WechatAccount).filter(WechatAccount.scope.in_(["system", "global", "admin"])).update({"is_default": False})
    else:
        db.query(WechatAccount).filter(WechatAccount.user_id == user.id).update({"is_default": False})
    account.is_default = True


def _account_config(account: WechatAccount) -> WechatAccountConfig:
    return WechatAccountConfig(
        app_id=account.app_id,
        app_secret=decrypt_secret(account.app_secret_encrypted),
        feishu_account=account.feishu_account,
        theme_id=account.theme_id,
        api_base=account.api_base or "https://feishu2weixin.maolai.cc",
        default_cover_url=account.default_cover_url,
    )


def _resolve_local_asset_cover(db: Session, user: UserAccount, platform_content: PlatformContent | None, cover_url: str) -> str:
    if not platform_content or not cover_url.startswith("/api/assets/"):
        return cover_url
    try:
        asset_id = int(cover_url.strip("/").split("/")[2])
    except Exception:
        return cover_url
    asset = db.query(UnifiedAsset).filter(
        UnifiedAsset.id == asset_id,
        UnifiedAsset.user_id == user.id,
        UnifiedAsset.platform_content_id == platform_content.id,
        UnifiedAsset.is_deleted.is_(False),
    ).first()
    if not asset or not asset.storage_path:
        return cover_url
    return f"file://{asset.storage_path}"


def _audit_payload(value) -> str:
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False, default=str)


def _record_admin_operation(
    db: Session,
    request: Request,
    user: UserAccount,
    action: str,
    resource_type: str,
    resource_id: int = 0,
    resource_key: str = "",
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    db.add(AdminOperationLog(
        user_id=user.id,
        user_email=user.email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id or 0,
        resource_key=resource_key or "",
        before_json=_audit_payload(before),
        after_json=_audit_payload(after),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:500],
    ))


def _create_wechat_draft_task(db: Session, user: UserAccount, data: WechatDraftPayload, platform_content: PlatformContent | None) -> GenerationTask:
    task = GenerationTask(
        user_id=user.id,
        project_id=platform_content.project_id if platform_content else 0,
        topic_id=platform_content.topic_id if platform_content else 0,
        platform_content_id=platform_content.id if platform_content else 0,
        task_type="wechat_draft_send",
        status="running",
        progress=10,
        input_snapshot_json=json.dumps(data.model_dump(), ensure_ascii=False),
        started_at=datetime.utcnow(),
    )
    db.add(task)
    db.flush()
    return task


def _finish_wechat_draft_task(db: Session, task: GenerationTask, record: WechatDraftRecord, result: dict) -> None:
    task.status = "succeeded"
    task.progress = 100
    task.output_snapshot_json = json.dumps({"draftId": record.id, "wechatMediaId": record.wechat_media_id, "thumbMediaId": record.thumb_media_id, **result}, ensure_ascii=False)
    task.finished_at = datetime.utcnow()
    db.flush()


def _fail_wechat_draft_task(db: Session, task: GenerationTask, record: WechatDraftRecord, exc: WechatPublishError) -> None:
    task.status = "failed"
    task.progress = 100
    task.error_code = exc.code
    task.error_message = exc.message
    task.output_snapshot_json = json.dumps({"draftId": record.id, "errorCode": exc.code, "payload": exc.payload}, ensure_ascii=False)
    task.raw_response_excerpt = json.dumps(exc.payload, ensure_ascii=False)[:1000]
    task.finished_at = datetime.utcnow()
    db.flush()


def _find_recent_duplicate(db: Session, user: UserAccount, data: WechatDraftPayload) -> WechatDraftRecord | None:
    cutoff = datetime.utcnow() - timedelta(seconds=90)
    return db.query(WechatDraftRecord).filter(
        WechatDraftRecord.user_id == user.id,
        WechatDraftRecord.wechat_account_id == data.accountId,
        WechatDraftRecord.platform_content_id == data.platformContentId,
        WechatDraftRecord.title == data.title.strip(),
        WechatDraftRecord.raw_content == data.rawContent,
        WechatDraftRecord.status.in_(["sending", "sent"]),
        WechatDraftRecord.created_at >= cutoff,
        WechatDraftRecord.is_active.is_(True),
    ).order_by(WechatDraftRecord.created_at.desc()).first()


def _find_idempotent_record(db: Session, user: UserAccount, data: WechatDraftPayload) -> WechatDraftRecord | None:
    key = data.idempotencyKey.strip()
    if not key:
        return None
    return db.query(WechatDraftRecord).filter(
        WechatDraftRecord.user_id == user.id,
        WechatDraftRecord.wechat_account_id == data.accountId,
        WechatDraftRecord.platform_content_id == data.platformContentId,
        WechatDraftRecord.idempotency_key == key,
        WechatDraftRecord.is_active.is_(True),
    ).order_by(WechatDraftRecord.created_at.desc()).first()


def _check_publish_rate_limit(db: Session, user: UserAccount, account_id: int):
    user_cutoff = datetime.utcnow() - timedelta(seconds=60)
    account_cutoff = datetime.utcnow() - timedelta(seconds=60)
    active_statuses = ["sending", "sent"]
    user_count = db.query(WechatDraftRecord).filter(
        WechatDraftRecord.user_id == user.id,
        WechatDraftRecord.status.in_(active_statuses),
        WechatDraftRecord.created_at >= user_cutoff,
        WechatDraftRecord.is_active.is_(True),
    ).count()
    if user_count >= 3:
        raise WechatPublishError("rate_limited_user", "发送过于频繁：每个用户每分钟最多发送 3 次公众号草稿")
    account_count = db.query(WechatDraftRecord).filter(
        WechatDraftRecord.user_id == user.id,
        WechatDraftRecord.wechat_account_id == account_id,
        WechatDraftRecord.status.in_(active_statuses),
        WechatDraftRecord.created_at >= account_cutoff,
        WechatDraftRecord.is_active.is_(True),
    ).count()
    if account_count >= 2:
        raise WechatPublishError("rate_limited_account", "发送过于频繁：同一公众号每分钟最多发送 2 次草稿")


def _material_cache_key(account_id: int, material_type: str, source_url: str) -> str:
    raw = f"{account_id}:{material_type}:{source_url.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_material_lookup(db: Session, user: UserAccount, account: WechatAccount):
    def lookup(material_type: str, source_url: str) -> dict[str, str] | None:
        cache = db.query(WechatMaterialCache).filter(
            WechatMaterialCache.user_id == user.id,
            WechatMaterialCache.wechat_account_id == account.id,
            WechatMaterialCache.material_type == material_type,
            WechatMaterialCache.cache_key == _material_cache_key(account.id, material_type, source_url),
            WechatMaterialCache.is_active.is_(True),
        ).first()
        if not cache:
            return None
        return {"mediaId": cache.media_id, "wechatUrl": cache.wechat_url}

    return lookup


def _build_material_save(db: Session, user: UserAccount, account: WechatAccount):
    def save(material_type: str, source_url: str, result: dict):
        key = _material_cache_key(account.id, material_type, source_url)
        cache = db.query(WechatMaterialCache).filter(
            WechatMaterialCache.user_id == user.id,
            WechatMaterialCache.wechat_account_id == account.id,
            WechatMaterialCache.material_type == material_type,
            WechatMaterialCache.cache_key == key,
            WechatMaterialCache.is_active.is_(True),
        ).first()
        if not cache:
            cache = WechatMaterialCache(
                user_id=user.id,
                wechat_account_id=account.id,
                source_url=source_url,
                cache_key=key,
                material_type=material_type,
            )
            db.add(cache)
        cache.media_id = result.get("mediaId", cache.media_id)
        cache.wechat_url = result.get("wechatUrl", cache.wechat_url)
        cache.content_type = result.get("contentType", cache.content_type)
        cache.byte_size = int(result.get("byteSize", cache.byte_size) or 0)
        db.flush()

    return save


@router.get("/accounts", summary="获取公众号账号列表")
async def list_accounts(db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    if user.is_admin:
        accounts = db.query(WechatAccount).order_by(WechatAccount.is_active.desc(), WechatAccount.is_default.desc(), WechatAccount.updated_at.desc()).all()
    else:
        accounts = _account_query_for_user(db, user).order_by(WechatAccount.is_default.desc(), WechatAccount.updated_at.desc()).all()
        accounts = [account for account in accounts if _account_visible_to_user(account, user)]
    return {"code": 0, "data": {"items": [account.to_dict() for account in accounts]}}


@router.post("/accounts", summary="新增公众号账号配置")
async def create_account(data: WechatAccountPayload, request: Request, db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="第一版公众号账号由管理员统一配置")
    if not data.appSecret.strip():
        raise HTTPException(status_code=400, detail="首次保存公众号账号必须填写 AppSecret")
    account = WechatAccount(
        user_id=user.id,
        scope="system",
        name=data.name.strip(),
        app_id=data.appId.strip(),
        app_secret_encrypted=encrypt_secret(data.appSecret.strip()),
        original_id=data.originalId.strip(),
        feishu_account=data.feishuAccount.strip(),
        theme_id=data.themeId.strip(),
        api_base=data.apiBase.strip() or "https://feishu2weixin.maolai.cc",
        default_cover_url=data.defaultCoverUrl.strip(),
        notes=data.notes.strip(),
        is_active=data.isActive,
    )
    _apply_default_account(db, user, account, data.isDefault)
    db.add(account)
    db.flush()
    _record_admin_operation(db, request, user, "wechat_account.create", "wechat_account", account.id, account.name, None, account.to_dict())
    db.commit()
    db.refresh(account)
    return {"code": 0, "data": account.to_dict(), "message": "公众号账号已保存"}


@router.put("/accounts/{account_id}", summary="更新公众号账号配置")
async def update_account(account_id: int, data: WechatAccountPayload, request: Request, db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="第一版公众号账号由管理员统一配置")
    account = _get_account_for_admin(db, account_id, user)
    before = account.to_dict()
    account.name = data.name.strip()
    account.app_id = data.appId.strip()
    if data.appSecret.strip():
        account.app_secret_encrypted = encrypt_secret(data.appSecret.strip())
    account.original_id = data.originalId.strip()
    account.feishu_account = data.feishuAccount.strip()
    account.theme_id = data.themeId.strip()
    account.api_base = data.apiBase.strip() or "https://feishu2weixin.maolai.cc"
    account.default_cover_url = data.defaultCoverUrl.strip()
    account.notes = data.notes.strip()
    account.is_active = data.isActive
    _apply_default_account(db, user, account, data.isDefault)
    db.flush()
    _record_admin_operation(db, request, user, "wechat_account.update", "wechat_account", account.id, account.name, before, account.to_dict())
    db.commit()
    db.refresh(account)
    return {"code": 0, "data": account.to_dict(), "message": "公众号账号已更新"}


@router.delete("/accounts/{account_id}", summary="删除公众号账号配置")
async def delete_account(account_id: int, request: Request, db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="第一版公众号账号由管理员统一配置")
    account = _get_account_for_admin(db, account_id, user)
    before = account.to_dict()
    account.is_active = False
    db.flush()
    _record_admin_operation(db, request, user, "wechat_account.delete", "wechat_account", account.id, account.name, before, account.to_dict())
    db.commit()
    return {"code": 0, "data": {"accountId": account_id, "deleted": True}, "message": "公众号账号已删除"}


@router.post("/accounts/{account_id}/test", summary="测试公众号连接")
async def test_account(account_id: int, request: Request, db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="第一版公众号连接测试由管理员执行")
    account = _get_account_for_admin(db, account_id, user)
    before = account.to_dict()
    try:
        token = await get_access_token(account.app_id, decrypt_secret(account.app_secret_encrypted))
        checks = await probe_wechat_capabilities(token)
        failed_checks = [item for item in checks if not item.get("ok")]
        account.last_test_status = "success" if not failed_checks else "partial"
        account.last_test_message = "公众号核心接口检测通过" if not failed_checks else "公众号凭据可用，但部分发布能力未通过检测"
        account.last_test_at = datetime.utcnow()
        db.flush()
        _record_admin_operation(db, request, user, "wechat_account.test", "wechat_account", account.id, account.name, before, account.to_dict())
        db.commit()
        return {"code": 0 if not failed_checks else 1, "data": {"ok": not failed_checks, "checks": checks}, "message": account.last_test_message}
    except WechatPublishError as exc:
        account.last_test_status = "failed"
        account.last_test_message = exc.message
        account.last_test_at = datetime.utcnow()
        db.flush()
        _record_admin_operation(db, request, user, "wechat_account.test", "wechat_account", account.id, account.name, before, account.to_dict())
        db.commit()
        return {"code": 1, "data": {"ok": False, "errorCode": exc.code}, "message": exc.message}


@router.post("/themes/list", summary="查询 feishu2weixin 主题列表")
async def list_themes(data: ThemeListPayload, user: UserAccount = Depends(get_current_user)):
    del user
    try:
        result = await list_remote_themes(data.feishuAccount, data.apiBase)
        return {"code": 0, "data": result}
    except WechatPublishError as exc:
        return {"code": 1, "data": {"errorCode": exc.code}, "message": exc.message}


@router.post("/format/preview", summary="生成公众号排版 HTML 预览")
async def preview_format(data: WechatPreviewPayload, db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    feishu_account = data.feishuAccount.strip()
    theme_id = data.themeId.strip()
    api_base = data.apiBase.strip() or "https://feishu2weixin.maolai.cc"
    if data.accountId:
        account = _get_account(db, data.accountId, user)
        feishu_account = account.feishu_account
        theme_id = account.theme_id
        api_base = account.api_base
    try:
        formatted_html = await render_markdown_for_wechat(
            data.rawContent,
            style=data.style,
            feishu_account=feishu_account,
            theme_id=theme_id,
            api_base=api_base,
        )
        return {"code": 0, "data": {"title": data.title, "formattedHtml": formatted_html, "style": data.style}}
    except WechatPublishError as exc:
        return {"code": 1, "data": {"errorCode": exc.code}, "message": exc.message}


@router.post("/drafts/preflight", summary="公众号草稿发送前检查")
async def preflight_draft(data: WechatPreflightPayload, db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    default_cover_url = ""
    if data.accountId:
        account = _get_account(db, data.accountId, user)
        default_cover_url = account.default_cover_url
    result = preflight_wechat_article(
        title=data.title,
        markdown=data.rawContent,
        digest=data.digest,
        cover_url=data.coverUrl,
        default_cover_url=default_cover_url,
    )
    return {"code": 0, "data": result}


@router.get("/errors/{errcode}", summary="获取微信错误码解释")
async def explain_error(errcode: str, errmsg: str = "", user: UserAccount = Depends(get_current_user)):
    del user
    return {"code": 0, "data": {"errcode": errcode, "message": explain_wechat_error(errcode, errmsg)}}


@router.get("/drafts", summary="获取公众号草稿发送记录")
async def list_drafts(
    page: int = 1,
    pageSize: int = 20,
    status: str = "",
    db: Session = Depends(get_db),
    user: UserAccount = Depends(get_current_user),
):
    safe_page = max(1, page)
    safe_page_size = max(1, min(pageSize, 100))
    query = db.query(WechatDraftRecord).filter(WechatDraftRecord.user_id == user.id, WechatDraftRecord.is_active.is_(True))
    if status:
        query = query.filter(WechatDraftRecord.status == status)
    total = query.count()
    items = query.order_by(WechatDraftRecord.updated_at.desc()).offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
    return {"code": 0, "data": {"items": [item.to_dict(include_content=False) for item in items], "page": safe_page, "pageSize": safe_page_size, "total": total}}


@router.get("/drafts/{draft_id}", summary="获取公众号草稿发送详情")
async def get_draft(draft_id: int, db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    record = db.query(WechatDraftRecord).filter(
        WechatDraftRecord.id == draft_id,
        WechatDraftRecord.user_id == user.id,
        WechatDraftRecord.is_active.is_(True),
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="公众号草稿记录不存在")
    return {"code": 0, "data": record.to_dict(include_content=True)}


@router.post("/drafts", summary="发送文章到公众号草稿箱")
async def create_wechat_draft(data: WechatDraftPayload, db: Session = Depends(get_db), user: UserAccount = Depends(get_current_user)):
    account = _get_account(db, data.accountId, user)
    platform_content = None
    raw_content = data.rawContent
    title = data.title.strip()
    digest = data.digest.strip()
    author = data.author.strip()
    if data.platformContentId:
        platform_content = db.query(PlatformContent).filter(
            PlatformContent.id == data.platformContentId,
            PlatformContent.user_id == user.id,
            PlatformContent.is_active.is_(True),
        ).first()
        if not platform_content:
            raise HTTPException(status_code=404, detail="公众号文章不存在或无权访问")
        raw_content = data.rawContent or platform_content.markdown_snapshot or platform_content.content_html
        title = title or platform_content.title
        digest = digest or platform_content.summary[:240]
        author = author or platform_content.author
    publish_cover_url = _resolve_local_asset_cover(db, user, platform_content, data.coverUrl.strip())
    preflight = preflight_wechat_article(title, raw_content, digest, publish_cover_url, account.default_cover_url, allow_local_asset=True)
    if not preflight["canSend"]:
        return {"code": 1, "data": {"preflight": preflight}, "message": "发送前检查未通过，请先处理错误项。"}
    idempotent_record = _find_idempotent_record(db, user, data)
    if idempotent_record:
        return {
            "code": 0 if idempotent_record.status == "sent" else 1,
            "data": idempotent_record.to_dict(include_content=idempotent_record.status == "sent"),
            "message": "已命中幂等发送记录，未重复创建公众号草稿。",
        }
    duplicate = _find_recent_duplicate(db, user, data)
    if duplicate:
        return {
            "code": 1,
            "data": duplicate.to_dict(include_content=False),
            "message": "检测到 90 秒内已有相同文章发送任务，请勿重复提交。",
        }
    try:
        _check_publish_rate_limit(db, user, account.id)
    except WechatPublishError as exc:
        return {"code": 1, "data": {"errorCode": exc.code}, "message": exc.message}
    task = _create_wechat_draft_task(db, user, data, platform_content)
    record = WechatDraftRecord(
        user_id=user.id,
        wechat_account_id=account.id,
        project_id=platform_content.project_id if platform_content else 0,
        topic_id=platform_content.topic_id if platform_content else 0,
        platform_content_id=platform_content.id if platform_content else 0,
        task_id=task.id,
        theme_id=account.theme_id,
        preflight_result_json=json.dumps(preflight, ensure_ascii=False),
        title=title,
        author=author,
        digest=digest,
        raw_content=raw_content,
        cover_url=data.coverUrl.strip(),
        content_source_url=data.contentSourceUrl.strip(),
        style=data.style,
        idempotency_key=data.idempotencyKey.strip(),
        status="sending",
        request_payload_json=json.dumps(data.model_dump(), ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        result = await publish_markdown_to_draft(
            config=_account_config(account),
            title=title,
            markdown=raw_content,
            author=author,
            digest=digest,
            cover_url=publish_cover_url,
            content_source_url=data.contentSourceUrl.strip(),
            style=data.style,
            material_lookup=_build_material_lookup(db, user, account),
            material_save=_build_material_save(db, user, account),
        )
        record.status = "sent"
        record.wechat_media_id = result["mediaId"]
        record.thumb_media_id = result["thumbMediaId"]
        record.cover_url = result["coverUrl"]
        record.formatted_html = result["formattedHtml"]
        record.response_payload_json = json.dumps(result, ensure_ascii=False)
        if platform_content:
            platform_content.status = "sent_to_draft"
        _finish_wechat_draft_task(db, task, record, result)
        db.commit()
        db.refresh(record)
        return {"code": 0, "data": record.to_dict(include_content=True), "message": "已发送到微信公众号草稿箱"}
    except WechatPublishError as exc:
        record.status = "failed"
        record.error_code = exc.code
        record.error_message = exc.message
        record.response_payload_json = json.dumps(exc.payload, ensure_ascii=False)
        _fail_wechat_draft_task(db, task, record, exc)
        db.commit()
        db.refresh(record)
        return {"code": 1, "data": record.to_dict(include_content=True), "message": exc.message}
