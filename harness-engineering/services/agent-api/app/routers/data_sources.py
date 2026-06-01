"""Local data source routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user, required
from app.responses import ok


router = APIRouter()


@router.post("/api/agent/data-sources/check-permission")
def check_data_source_permission(payload: dict[str, Any] | None = Body(default=None), _user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    return ok(store.check_directory_permission(str(required(data, "path"))))


@router.get("/api/agent/data-sources")
def list_data_sources(_user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_data_sources())


@router.post("/api/agent/data-sources")
def add_data_source(payload: dict[str, Any] | None = Body(default=None), _user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    return ok(store.add_data_source(str(required(data, "path"))))


@router.post("/api/agent/data-sources/{data_source_id}/scan")
def scan_data_source(data_source_id: str, payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    case_id = str(data["case_id"]) if data.get("case_id") else None
    if case_id:
        store.require_case_access(case_id, user["id"])
    return ok(store.scan_data_source(data_source_id, case_id, data.get("knowledge_base_id"), data.get("folder_id"), user["id"]))
