"""Target FastAPI entrypoint for the platform control plane.

This module is intentionally dependency-light: importing it does not require
FastAPI. ``create_app`` imports FastAPI only when the target runtime is used.
The current executable MVP remains ``services/platform-api/server.py`` until the
M2 migration wires these routers to FastAPI.
"""

from __future__ import annotations


def create_app():
    try:
        from fastapi import FastAPI
    except ModuleNotFoundError as exc:  # pragma: no cover - target dependency
        raise RuntimeError("FastAPI is required for the target platform-api runtime") from exc

    app = FastAPI(title="V4.1 Platform Control Plane", version="4.1.0-mvp")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "platform-api"}

    return app


app = None
