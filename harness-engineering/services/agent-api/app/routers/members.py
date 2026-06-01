"""Local member and case permission routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user
from app.responses import ok


router = APIRouter()


def require_agent_admin(user: dict[str, Any]) -> None:
    if user.get("role") != "agent_admin":
        raise PermissionError("agent admin role is required")


@router.get("/api/agent/users")
def list_users(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.list_users())


@router.post("/api/agent/users")
def create_user(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.create_user(body(payload), user["id"]))


@router.post("/api/agent/users/{user_id}/disable")
def disable_user(user_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.disable_user(user_id, user["id"]))


@router.post("/api/agent/users/{user_id}/reset-password")
def reset_user_password(user_id: str, payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.reset_user_password(user_id, str(body(payload).get("password", "")), user["id"]))


@router.get("/api/agent/case-members")
def list_case_members(case_id: str | None = None, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.list_case_members(case_id))


@router.post("/api/agent/case-members")
def grant_case_member(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.grant_case_member(body(payload), user["id"]))


@router.post("/api/agent/case-members/{member_id}/revoke")
def revoke_case_member(member_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.revoke_case_member(member_id, user["id"]))
