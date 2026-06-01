"""Case workspace routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user, required
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/cases")
def list_cases(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_cases(user["id"]))


@router.post("/api/agent/cases")
def create_case(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    data.setdefault("owner_id", user["id"])
    return ok(store.create_case(data))


@router.get("/api/agent/cases/{case_id}")
def get_case(case_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    store.require_case_access(case_id, user["id"])
    return ok(store.get_case(case_id))


@router.post("/api/agent/cases/summary")
def summarize_case(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    case_id = str(required(data, "case_id"))
    store.require_case_access(case_id, user["id"])
    return ok(store.create_summary(case_id))
