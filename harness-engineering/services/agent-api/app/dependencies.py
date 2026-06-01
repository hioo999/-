"""Shared FastAPI dependencies for the Agent API routers."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Header, HTTPException, Request


def request_store(request: Request) -> Any:
    return request.app.state.store


def bearer_token(authorization: str | None = Header(default=None, alias="Authorization")) -> str | None:
    prefix = "Bearer "
    if authorization and authorization.startswith(prefix):
        return authorization[len(prefix) :].strip()
    return None


def require_user(request: Request, token: str | None = Depends(bearer_token)) -> dict[str, Any]:
    return request.app.state.store.current_user(token)


def body(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload or {}


def required(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise HTTPException(status_code=400, detail=f"missing field: '{key}'")
    return payload[key]
