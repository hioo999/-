"""Chat history routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import request_store, require_user
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/chats")
def list_chats(case_id: str | None = None, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    if case_id:
        store.require_case_access(case_id, user["id"])
        return ok(store.list_chats(case_id))
    return ok(store.list_chats_for_user(user["id"]))


@router.get("/api/agent/chats/{session_id}")
def get_chat_messages(session_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.get_chat_messages(session_id, user["id"]))
