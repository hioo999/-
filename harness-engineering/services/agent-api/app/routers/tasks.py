"""Processing task and worker routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

import server as agent_server
from app.dependencies import body, request_store, require_user
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/tasks")
def list_tasks(
    file_id: str | None = None,
    case_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = Depends(require_user),
    store: Any = Depends(request_store),
) -> dict[str, Any]:
    return ok(store.list_tasks(file_id, case_id, status, user["id"]))


@router.post("/api/agent/tasks/run-pending")
def run_pending_tasks(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    if user.get("role") != "agent_admin":
        raise PermissionError("agent admin role is required")
    data = body(payload)
    return ok(store.run_pending_tasks(int(data.get("limit", 20))))


@router.get("/api/agent/tasks/{task_id}")
def get_task(task_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    store.require_task_access(task_id, user["id"])
    return ok(store.get_task(task_id))


@router.post("/api/agent/tasks/{task_id}/retry")
def retry_task(task_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    store.require_task_access(task_id, user["id"])
    return ok(store.retry_task(task_id))


@router.post("/api/agent/worker/run-once")
def run_worker_once(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    if user.get("role") != "agent_admin":
        raise PermissionError("agent admin role is required")
    data = body(payload)
    return ok(
        store.run_worker_once(
            int(data.get("batch_size", agent_server.WORKER_BATCH_SIZE)),
            int(data.get("max_retries", agent_server.WORKER_MAX_RETRIES)),
            bool(data.get("sync_qdrant", True)),
        )
    )
