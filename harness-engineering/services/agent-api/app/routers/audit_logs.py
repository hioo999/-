"""Audit log routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import request_store, require_user
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/audit-logs")
def audit_logs(_user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.audit_logs())
