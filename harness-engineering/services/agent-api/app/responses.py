"""Shared FastAPI response envelope helpers for the Agent API."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}


def error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": status_code, "message": message, "data": None})
