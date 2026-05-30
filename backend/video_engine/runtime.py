"""
video_engine.runtime — Lifecycle hooks and in-memory task registry.

This module is the thin integration layer between the FastAPI app and the
underlying Pixelle-Video engine. It deliberately keeps state in-process for
Stage 2 of the integration; persisting tasks to the SQLAlchemy database is
deferred to a later stage so we can first validate the end-to-end flow.

Public surface:

- ``startup()`` / ``shutdown()``: idempotent coroutines invoked from FastAPI's
  lifespan. ``startup()`` swallows initialization errors (e.g. missing
  ``config.yaml`` or unavailable upstream services) and records them on
  ``ENGINE_STATE`` so the HTTP layer can respond with a clean 503 instead of
  crashing the entire backend.
- ``ENGINE_STATE``: snapshot of whether the engine is ready and, if not, why.
- ``submit_task(...)`` / ``get_task(...)`` / ``list_pipelines()``:
  task-orchestration helpers used by ``api/video_routes.py``.

Each task runs as an ``asyncio.Task`` on the FastAPI event loop. The engine's
pipelines are already async and ``await``-friendly, so this is sufficient for a
single-worker dev setup. For production with multiple workers we will move
this onto an out-of-process queue in Stage 4/5.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import video_engine as _ve_pkg  # sets sys.path + PIXELLE_VIDEO_ROOT on import

logger = logging.getLogger(__name__)


def _engine():
    """Lazily resolve the underlying engine singleton.

    Wrapped so a missing third-party dep (e.g. ``comfykit``) only surfaces
    when the engine is actually exercised, not at backend import time.
    """
    return _ve_pkg.video_engine  # triggers PEP 562 lazy load


# ───────────────────────── Engine lifecycle ─────────────────────────

@dataclass
class _EngineState:
    """Tracks whether the underlying engine is usable at runtime."""

    ready: bool = False
    error: Optional[str] = None


ENGINE_STATE = _EngineState()


async def startup() -> None:
    """Initialize the engine. Safe to call from FastAPI lifespan.

    Failure is non-fatal: ``ENGINE_STATE.ready`` stays ``False`` and the HTTP
    layer surfaces a 503 for any endpoint that needs the engine.
    """
    if ENGINE_STATE.ready:
        return
    try:
        await _engine().initialize()
        ENGINE_STATE.ready = True
        ENGINE_STATE.error = None
        logger.info("video_engine initialized")
    except Exception as exc:  # pragma: no cover - depends on external services
        ENGINE_STATE.ready = False
        ENGINE_STATE.error = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "video_engine initialization failed (endpoints will return 503): %s",
            ENGINE_STATE.error,
        )


async def shutdown() -> None:
    """Release engine resources (ComfyKit session, etc.)."""
    if not ENGINE_STATE.ready:
        return
    try:
        await _engine().cleanup()
    except Exception as exc:  # pragma: no cover
        logger.warning("video_engine cleanup raised: %s", exc)
    finally:
        ENGINE_STATE.ready = False


# ───────────────────────── Task registry ─────────────────────────

# Pipeline kwargs forwarded to ``video_engine.generate_video`` that we expose
# over HTTP. We allow a permissive set since pipelines define their own
# parameters; unknown kwargs are passed straight through.
_KNOWN_PIPELINES = ("standard", "custom", "asset_based")


@dataclass
class TaskRecord:
    """In-memory record of a single video generation task."""

    task_id: str
    pipeline: str
    status: str = "pending"  # pending | running | succeeded | failed
    progress: float = 0.0
    current_event: Optional[str] = None
    error: Optional[str] = None
    video_path: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)
    asyncio_task: Optional[asyncio.Task] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "pipeline": self.pipeline,
            "status": self.status,
            "progress": self.progress,
            "current_event": self.current_event,
            "error": self.error,
            "video_path": self.video_path,
            "duration": self.duration,
            "file_size": self.file_size,
            "params": self.params,
        }


_TASKS: Dict[str, TaskRecord] = {}


def list_pipelines() -> list[str]:
    """Return pipelines registered on the engine (or the static fallback)."""
    if ENGINE_STATE.ready:
        try:
            pipelines = getattr(_engine(), "pipelines", None)
            if pipelines:
                return list(pipelines.keys())
        except Exception:
            pass
    return list(_KNOWN_PIPELINES)


def get_task(task_id: str) -> Optional[TaskRecord]:
    return _TASKS.get(task_id)


def submit_task(
    text: str,
    pipeline: str = "standard",
    **pipeline_kwargs: Any,
) -> TaskRecord:
    """Create a TaskRecord and dispatch the engine call as a background task.

    The caller is responsible for checking ``ENGINE_STATE.ready`` first; we
    intentionally do not guard here so callers can produce a clear 503.
    """
    record = TaskRecord(
        task_id=uuid.uuid4().hex,
        pipeline=pipeline,
        params={"text_preview": text[:120], **pipeline_kwargs},
    )
    _TASKS[record.task_id] = record

    def _on_progress(event) -> None:
        record.progress = float(event.progress)
        record.current_event = event.event_type

    async def _run() -> None:
        record.status = "running"
        try:
            result = await _engine().generate_video(
                text=text,
                pipeline=pipeline,
                progress_callback=_on_progress,
                **pipeline_kwargs,
            )
            record.status = "succeeded"
            record.progress = 1.0
            record.video_path = getattr(result, "video_path", None)
            record.duration = getattr(result, "duration", None)
            record.file_size = getattr(result, "file_size", None)
        except Exception as exc:  # pragma: no cover - engine errors
            record.status = "failed"
            record.error = f"{type(exc).__name__}: {exc}"
            logger.exception("Video task %s failed", record.task_id)

    record.asyncio_task = asyncio.create_task(_run(), name=f"video-task-{record.task_id}")
    return record


def submit_asset_task(
    assets: list[str],
    video_title: str = "",
    intent: str = "",
    duration: int = 30,
    **pipeline_kwargs: Any,
) -> TaskRecord:
    """Dispatch the Pixelle asset_based pipeline as a background task."""
    record = TaskRecord(
        task_id=uuid.uuid4().hex,
        pipeline="asset_based",
        params={
            "asset_count": len(assets),
            "video_title": video_title,
            "intent_preview": intent[:120],
            "duration": duration,
            **pipeline_kwargs,
        },
    )
    _TASKS[record.task_id] = record

    def _on_progress(event) -> None:
        record.progress = float(event.progress)
        record.current_event = event.event_type

    async def _run() -> None:
        record.status = "running"
        try:
            result = await _engine().pipelines["asset_based"](
                assets=assets,
                video_title=video_title,
                intent=intent,
                duration=duration,
                progress_callback=_on_progress,
                **pipeline_kwargs,
            )
            record.status = "succeeded"
            record.progress = 1.0
            record.video_path = getattr(result, "video_path", None) or getattr(result, "final_video_path", None)
            storyboard = getattr(result, "storyboard", None)
            record.duration = getattr(result, "duration", None) or getattr(storyboard, "total_duration", None)
            if record.video_path and os.path.exists(record.video_path):
                record.file_size = os.path.getsize(record.video_path)
        except Exception as exc:  # pragma: no cover - engine errors
            record.status = "failed"
            record.error = f"{type(exc).__name__}: {exc}"
            logger.exception("Asset video task %s failed", record.task_id)

    record.asyncio_task = asyncio.create_task(_run(), name=f"asset-video-task-{record.task_id}")
    return record
