"""在线提词器云端草稿与来源脚本接口。"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from api.auth_routes import get_current_user
from database import get_db
from models.persona import GenerationHistory, ShortVideoProject, TeleprompterDraft, UserAccount


router = APIRouter(prefix="/api/teleprompter", tags=["在线提词器"])

MAX_SCRIPT_LENGTH = 30000


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


class AnalyticsEventPayload(BaseModel):
    eventName: str = Field(..., min_length=1, max_length=100)
    eventTime: str = Field("", max_length=80)
    sessionId: str = Field("", max_length=120)
    properties: dict[str, Any] = Field(default_factory=dict)


def _count_words(text: str) -> int:
    english_words = re.findall(r"[A-Za-z0-9]+", text)
    chinese_chars = re.findall(r"[\u4e00-\u9fa5]", text)
    return len(english_words) + len(chinese_chars)


def _count_paragraphs(text: str) -> int:
    return len([item for item in re.split(r"\n\s*\n+|\n+", text) if item.strip()])


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


@router.post("/analytics/events", summary="上报提词器埋点")
async def collect_analytics_event(data: AnalyticsEventPayload):
    # V0.1 先接收事件，后续再落库或转发数据平台。
    return {"code": 0, "data": {"accepted": True, "eventName": data.eventName}, "message": "ok"}
