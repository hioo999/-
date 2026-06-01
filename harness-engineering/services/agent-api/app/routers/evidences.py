"""Evidence routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Query

from app.dependencies import body, request_store, require_user
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/evidences")
def list_evidences(case_id: str = Query(...), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_evidences_for_user(case_id, user["id"]))


@router.post("/api/agent/evidences")
def create_evidence(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    store.require_case_access(str(data["case_id"]), user["id"])
    return ok(store.create_evidence(data))
