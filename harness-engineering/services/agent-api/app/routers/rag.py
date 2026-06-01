"""RAG and vector-store routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user, required
from app.responses import ok


router = APIRouter()


@router.post("/api/agent/rag/query")
def rag_query(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    question = str(required(data, "question"))
    if data.get("knowledge_base_id"):
        return ok(store.ask_knowledge_base(str(data["knowledge_base_id"]), question, user["id"]))
    return ok(store.ask(str(required(data, "case_id")), question, user["id"]))


@router.post("/api/agent/ai/scenario-query")
def scenario_query(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.scenario_query(body(payload), user["id"]))


@router.post("/api/agent/rag/retrieve")
def rag_retrieve(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    limit = int(data.get("limit", 5))
    question = str(required(data, "question"))
    if data.get("knowledge_base_id"):
        knowledge_base_id = str(data["knowledge_base_id"])
        store.require_knowledge_base_ai_usage(knowledge_base_id, user["id"], generate=False)
        return ok(store.search(knowledge_base_id, question, limit, user["id"]))
    case_id = str(required(data, "case_id"))
    store.require_case_access(case_id, user["id"])
    return ok(store.search(case_id, question, limit, user["id"]))


@router.post("/api/agent/vector-store/sync-qdrant")
def sync_qdrant(payload: dict[str, Any] | None = Body(default=None), _user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    return ok(store.sync_qdrant_vectors(int(data.get("limit", 500)), data.get("case_id")))
