"""Local file routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response

import server as agent_server
from app.dependencies import body, request_store, require_user, required
from app.responses import ok


router = APIRouter()


@router.get("/api/agent/files")
def list_files(case_id: str | None = None, knowledge_base_id: str | None = None, folder_id: str | None = None, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    if knowledge_base_id:
        store.require_knowledge_base_access(knowledge_base_id, user["id"], "view")
        files = [
            item
            for item in store.list_files(knowledge_base_id=knowledge_base_id, folder_id=folder_id)
            if store.has_resource_access("file", item["id"], user["id"], "view")
        ]
        return ok(files)
    if case_id:
        store.require_case_access(case_id, user["id"])
        return ok(store.list_files(case_id))
    return ok(store.list_files_for_user(user["id"]))


@router.post("/api/agent/files/upload")
def upload_file(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    case_id = str(data["case_id"]) if data.get("case_id") else None
    if case_id:
        store.require_case_access(case_id, user["id"])
    return ok(
        store.save_uploaded_file(
            case_id,
            str(required(data, "file_name")),
            str(required(data, "content_base64")),
            data.get("knowledge_base_id"),
            data.get("folder_id"),
            user["id"],
        )
    )


@router.post("/api/agent/files/parse")
def parse_file(payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    data = body(payload)
    file_id = str(required(data, "file_id"))
    store.require_file_access(file_id, user["id"], "edit")
    return ok(store.parse_file(file_id))


@router.get("/api/agent/files/{file_id}/preview")
def preview_file(file_id: str, chunk_limit: int = 8, text_limit: int = 6000, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.preview_file(file_id, user["id"], chunk_limit, text_limit))


@router.get("/api/agent/files/{file_id}/native-preview")
def native_preview(file_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.native_preview_status(file_id, user["id"]))


@router.post("/api/agent/files/{file_id}/native-preview/run")
def run_native_preview(file_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.run_native_preview(file_id, user["id"]))


@router.get("/api/agent/files/{file_id}/content")
def file_content(file_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> Response:
    try:
        watermark, content, content_type = store.file_content_for_preview(file_id, user["id"])
    except agent_server.PreviewContentBlockedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except agent_server.PreviewContentNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{watermark["file_name"]}"',
            "X-Agent-Watermark": watermark["watermark_text"],
            "X-Agent-Watermark-Id": watermark["id"],
            "X-Agent-Watermark-File-Id": watermark["file_id"],
            "X-Agent-Watermark-Action": watermark["action"],
        },
    )


@router.patch("/api/agent/files/{file_id}")
def update_file(file_id: str, payload: dict[str, Any] | None = Body(default=None), user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.update_file(file_id, body(payload), user["id"]))


@router.delete("/api/agent/files/{file_id}")
def delete_file(file_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.soft_delete_file(file_id, user["id"]))


@router.post("/api/agent/files/{file_id}/restore")
def restore_file(file_id: str, user: dict[str, Any] = Depends(require_user), store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.restore_file(file_id, user["id"]))
