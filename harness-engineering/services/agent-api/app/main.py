"""FastAPI entrypoint for the Agent local data plane.

This module is a parallel runtime adapter over the existing stdlib prototype in
``server.py``. It intentionally reuses the current Store business methods so the
FastAPI migration can proceed without changing or deleting the legacy handler.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server as agent_server  # noqa: E402


class FastApiDependencyError(RuntimeError):
    """Raised when the target FastAPI runtime dependencies are unavailable."""


def create_app(store: Any | None = None):
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
    except ModuleNotFoundError as exc:  # pragma: no cover - target dependency
        raise FastApiDependencyError("FastAPI is required for the target agent-api runtime") from exc

    from app.exception_handlers import register_exception_handlers
    from app.routers import audit_logs, auth, cases, chats, console, data_sources, enterprise, evidences, files, folders, knowledge_bases, members, model_configs, permissions, rag, setup, status, tasks

    globals().update({"Request": Request, "JSONResponse": JSONResponse})

    app = FastAPI(title="V4.1 Agent Local Data Plane", version="4.1.0-mvp")
    app.state.store = store or agent_server.STORE

    register_exception_handlers(app)
    for router in (
        console.router,
        setup.router,
        auth.router,
        status.router,
        data_sources.router,
        tasks.router,
        cases.router,
        files.router,
        knowledge_bases.router,
        folders.router,
        permissions.router,
        members.router,
        enterprise.router,
        model_configs.router,
        rag.router,
        chats.router,
        evidences.router,
        audit_logs.router,
    ):
        app.include_router(router)

    return app


try:
    app = create_app()
except FastApiDependencyError:  # pragma: no cover - dependency is optional in stdlib prototype tests
    app = None
