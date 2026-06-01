"""Resource ACL routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user, required
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/permissions/resource")
def list_resource_permissions(resource_type: str, resource_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_resource_permissions(resource_type, resource_id, user["id"]))


@router.get("/api/agent/permissions/effective")
def effective_permissions(resource_type: str, resource_id: str, user_id: str | None = None, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.effective_permissions(resource_type, resource_id, user["id"], user_id))


@router.post("/api/agent/permissions/grant")
def grant_permission(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.set_acl_entry(body(payload), user["id"], "allow"))


@router.post("/api/agent/permissions/deny")
def deny_permission(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.set_acl_entry(body(payload), user["id"], "deny"))


@router.post("/api/agent/permissions/check")
def check_permission(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    target_user_id = str(data.get("user_id", user["id"]))
    action = str(data.get("action", "view"))
    allowed = store.has_resource_access(str(required(data, "resource_type")), str(required(data, "resource_id")), target_user_id, action)
    return ok({"allowed": allowed, "user_id": target_user_id, "action": action})


@router.delete("/api/agent/permissions/{entry_id}")
def delete_permission(entry_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.delete_acl_entry(entry_id, user["id"]))
