"""Shared FastAPI exception envelope handlers for the Agent API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.responses import error


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return error(exc.status_code, str(exc.detail))

    @app.exception_handler(StarletteHTTPException)
    def starlette_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = "not found" if exc.status_code == 404 else str(exc.detail)
        return error(exc.status_code, message)

    @app.exception_handler(RequestValidationError)
    def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(400, str(exc))

    @app.exception_handler(PermissionError)
    def permission_exception_handler(_request: Request, exc: PermissionError) -> JSONResponse:
        status_code = 403 if exc.__class__.__name__ == "CaseAccessError" else 401
        return error(status_code, str(exc))

    @app.exception_handler(KeyError)
    def key_exception_handler(_request: Request, exc: KeyError) -> JSONResponse:
        return error(400, str(exc).strip("'"))

    @app.exception_handler(Exception)
    def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        return error(400, str(exc))
