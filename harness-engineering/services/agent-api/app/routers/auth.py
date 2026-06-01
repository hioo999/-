"""Local authentication routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import bearer_token, body, request_store, require_user, required
from app.responses import ok


router = APIRouter()


@router.post("/api/agent/auth/login")
def login(payload: dict[str, Any] | None = Body(default=None), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    return ok(store.login(str(required(data, "account")), str(required(data, "password"))))


@router.post("/api/agent/auth/logout")
def logout(token: str | None = Depends(bearer_token), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.logout(token))


@router.get("/api/agent/auth/me")
def me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return ok(user)
