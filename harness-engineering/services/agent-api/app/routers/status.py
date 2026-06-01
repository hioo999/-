"""Agent status, activation, and health report routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

import server as agent_server
from app.dependencies import body, request_store, require_user, required
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/status")
def status(_user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.status_payload())


@router.get("/api/agent/status/dependencies")
def dependencies(_user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    status_payload = store.status_payload()
    return ok(
        {
            "database": status_payload["database"],
            "storage": status_payload["storage"],
            "task_queue": status_payload["task_queue"],
            "vector_store": status_payload["vector_store"],
            "model_connectivity": status_payload["model_connectivity"],
            "qdrant_configured": status_payload["qdrant_configured"],
            "ocr_configured": status_payload["ocr_configured"],
        }
    )


@router.post("/api/agent/activate")
def activate(payload: dict[str, Any] | None = Body(default=None), _user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    tenant_id = str(required(data, "tenant_id"))
    agent_id = str(data.get("agent_id") or agent_server.new_id("ag"))
    store.set_config("tenant_id", tenant_id)
    store.set_config("agent_id", agent_id)
    result = agent_server.post_json(
        f"{agent_server.PLATFORM_BASE_URL}/api/platform/agents/register",
        {
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "agent_version": "4.1.0-mvp",
            "install_fingerprint": "local-mvp",
            "license_key_hash": str(required(data, "license_key_hash")),
        },
    )
    return ok({"agent_id": agent_id, "platform_result": result})


@router.post("/api/agent/report-health")
def report_health(_user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(agent_server.post_json(f"{agent_server.PLATFORM_BASE_URL}/api/platform/agents/health", store.health_payload()))
