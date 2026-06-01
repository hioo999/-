"""Knowledge base routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/knowledge-bases")
def list_knowledge_bases(user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_knowledge_bases(user["id"]))


@router.post("/api/agent/knowledge-bases")
def create_knowledge_base(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.create_knowledge_base(body(payload), user["id"]))


@router.get("/api/agent/knowledge-bases/{kb_id}")
def get_knowledge_base(kb_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.get_knowledge_base(kb_id, user["id"]))


@router.patch("/api/agent/knowledge-bases/{kb_id}")
def update_knowledge_base(kb_id: str, payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.update_knowledge_base(kb_id, body(payload), user["id"]))


@router.delete("/api/agent/knowledge-bases/{kb_id}")
def delete_knowledge_base(kb_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.soft_delete_knowledge_base(kb_id, user["id"]))


@router.post("/api/agent/knowledge-bases/{kb_id}/review")
def transition_knowledge_base_review(kb_id: str, payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.transition_knowledge_base_review(kb_id, body(payload), user["id"]))


@router.get("/api/agent/knowledge-bases/{kb_id}/review-logs")
def list_knowledge_base_review_logs(kb_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_knowledge_base_review_logs(kb_id, user["id"]))


@router.get("/api/agent/knowledge-bases/{kb_id}/governance-audit")
def list_knowledge_base_governance_audit(kb_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_knowledge_base_governance_audit(kb_id, user["id"]))


@router.post("/api/agent/knowledge-bases/{kb_id}/archive")
def archive_knowledge_base(kb_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.archive_knowledge_base(kb_id, user["id"]))


@router.get("/api/agent/knowledge-bases/{kb_id}/tree")
def get_knowledge_base_tree(kb_id: str, include_deleted: bool = False, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.get_knowledge_base_tree(kb_id, user["id"], include_deleted=include_deleted))


@router.get("/api/agent/knowledge-bases/{kb_id}/members")
def list_knowledge_base_members(kb_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_knowledge_base_members(kb_id, user["id"]))


@router.post("/api/agent/knowledge-bases/{kb_id}/members")
def grant_knowledge_base_member(kb_id: str, payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.grant_knowledge_base_member(kb_id, body(payload), user["id"]))


@router.post("/api/agent/knowledge-bases/{kb_id}/members/{member_id}/revoke")
def revoke_knowledge_base_member(kb_id: str, member_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.revoke_knowledge_base_member(kb_id, member_id, user["id"]))


@router.get("/api/agent/knowledge-bases/{kb_id}/stats")
def knowledge_base_stats(kb_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.knowledge_base_stats(kb_id, user["id"]))
