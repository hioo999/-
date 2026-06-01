"""Model configuration routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import body, request_store, require_user
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/model-configs")
def list_model_configs(_user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.list_model_configs())


@router.post("/api/agent/model-configs")
def save_model_config(payload: dict[str, Any] | None = Body(default=None), _user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.save_model_config(body(payload)))


@router.get("/api/agent/model-configs/{config_id}")
def get_model_config(config_id: str, _user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.get_model_config(config_id))


@router.post("/api/agent/model-configs/{config_id}/test-chat")
def test_chat_model(config_id: str, _user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.test_model_config(config_id, "chat"))


@router.post("/api/agent/model-configs/{config_id}/test-embedding")
def test_embedding_model(config_id: str, _user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.test_model_config(config_id, "embedding"))
