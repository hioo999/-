"""Knowledge base folder routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user
from app.responses import ok


router = APIRouter()


@router.post("/api/agent/folders")
def create_folder(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.create_folder(body(payload), user["id"]))


@router.patch("/api/agent/folders/{folder_id}")
def update_folder(folder_id: str, payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.update_folder(folder_id, body(payload), user["id"]))


@router.delete("/api/agent/folders/{folder_id}")
def delete_folder(folder_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.soft_delete_folder(folder_id, user["id"]))


@router.post("/api/agent/folders/{folder_id}/restore")
def restore_folder(folder_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.restore_folder(folder_id, user["id"]))
