"""First-run local administrator setup routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/setup/status")
def setup_status(store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.setup_status())


@router.post("/api/agent/setup/admin")
def setup_admin(payload: dict[str, Any] | None = Body(default=None), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.setup_admin(body(payload)))
