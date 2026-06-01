"""Console and health routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.dependencies import request_store
from app.responses import ok


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def console() -> str:
    return """<html><head><title>Agent Console</title></head><body><h1>Agent local console</h1><p>FastAPI migration entrypoint. Business data remains local to the lawyer-side Agent.</p></body></html>"""


@router.get("/health")
def health(store: Any = Depends(request_store)) -> dict[str, Any]:
    return ok(store.health_payload())
