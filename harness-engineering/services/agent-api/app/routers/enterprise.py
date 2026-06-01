"""Enterprise organization, external directory sync, and assistant admin routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user
from app.responses import ok


router = APIRouter()


def require_agent_admin(user: dict[str, Any]) -> None:
    if user.get("role") != "agent_admin":
        raise PermissionError("agent admin role is required")


@router.get("/api/agent/enterprise/overview")
def enterprise_overview(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.enterprise_overview())


@router.get("/api/agent/enterprise/profile")
def enterprise_profile(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.ensure_enterprise_profile())


@router.post("/api/agent/enterprise/profile")
def save_enterprise_profile(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.save_enterprise_profile(body(payload), user["id"]))


@router.get("/api/agent/organization/units")
def list_organization_units(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.list_organization_units())


@router.post("/api/agent/organization/units")
def create_organization_unit(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.create_organization_unit(body(payload), user["id"]))


@router.get("/api/agent/organization/members")
def list_organization_members(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.list_organization_members())


@router.post("/api/agent/organization/members")
def assign_organization_member(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.assign_organization_member(body(payload), user["id"]))


@router.get("/api/agent/external-org/integrations")
def list_external_org_integrations(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.list_external_org_integrations())


@router.post("/api/agent/external-org/integrations")
def save_external_org_integration(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.save_external_org_integration(body(payload), user["id"]))


@router.post("/api/agent/external-org/integrations/{provider}/sync")
def trigger_external_org_sync(provider: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.simulate_external_org_sync(provider, user["id"]))


@router.get("/api/agent/ai-assistant/settings")
def get_ai_assistant_setting(scope_type: str = "enterprise", scope_id: str | None = None, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.get_ai_assistant_setting(scope_type, scope_id))


@router.post("/api/agent/ai-assistant/settings")
def save_ai_assistant_setting(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.save_ai_assistant_setting(body(payload), user["id"]))


@router.get("/api/agent/ai-assistant/feedback")
def list_ai_assistant_feedback(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.list_ai_assistant_feedback())


@router.post("/api/agent/ai-assistant/feedback")
def create_ai_assistant_feedback(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.create_ai_assistant_feedback(body(payload), user["id"]))


@router.post("/api/agent/ai-assistant/feedback/{feedback_id}/handle")
def handle_ai_assistant_feedback(feedback_id: str, payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    require_agent_admin(user)
    return ok(store.handle_ai_assistant_feedback(feedback_id, body(payload), user["id"]))
