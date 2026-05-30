"""
video_routes — HTTP surface for the video_engine integration.

Endpoints (prefix ``/api/video``):

- ``GET  /pipelines``            list registered pipelines and engine status.
- ``POST /generate``             submit a generation task (returns task_id).
- ``GET  /tasks/{task_id}``      poll a task's status & progress.
- ``GET  /tasks/{task_id}/file`` stream the final mp4 once succeeded.

This is a Stage 2 surface: tasks live in memory and are not persisted across
restarts. The schemas are intentionally permissive so pipeline-specific kwargs
flow through to ``video_engine.generate_video`` without coupling this module
to any one pipeline's signature.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from video_engine import runtime

router = APIRouter(prefix="/api/video", tags=["视频引擎"])


# ───────────────────────── Schemas ─────────────────────────

class GenerateRequest(BaseModel):
    text: str = Field(..., description="主题（mode=generate）或固定脚本（mode=fixed）")
    pipeline: str = Field("standard", description="standard / custom / asset_based")
    # Common StandardPipeline kwargs surfaced explicitly for discoverability;
    # any additional keys land in ``extra`` and are forwarded as kwargs.
    mode: Optional[str] = Field(None, description="generate | fixed")
    n_scenes: Optional[int] = None
    min_narration_words: Optional[int] = None
    max_narration_words: Optional[int] = None
    template: Optional[str] = Field(None, description="模板相对路径，如 1080x1920/image_default.html")
    extra: Dict[str, Any] = Field(default_factory=dict, description="透传给 pipeline 的其它参数")


class GenerateResponse(BaseModel):
    task_id: str
    status: str
    pipeline: str


class TaskStatusResponse(BaseModel):
    task_id: str
    pipeline: str
    status: str
    progress: float
    current_event: Optional[str] = None
    error: Optional[str] = None
    video_path: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None


class AssetAnalysisItem(BaseModel):
    filename: str
    path: str
    type: str
    description: str


class AssetAnalysisResponse(BaseModel):
    assets: list[AssetAnalysisItem]
    extracted_content: str


# ───────────────────────── Helpers ─────────────────────────

def _require_engine() -> None:
    if not runtime.ENGINE_STATE.ready:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "video_engine_unavailable",
                "reason": runtime.ENGINE_STATE.error or "engine not initialized",
                "hint": "检查 backend/video_engine/config.yaml 是否已配置，依赖是否已安装",
            },
        )


def _has_runninghub_api_key(engine: Any) -> bool:
    if os.getenv("RUNNINGHUB_API_KEY"):
        return True
    for service_name in ("image_analysis", "video_analysis", "media", "tts"):
        service = getattr(engine, service_name, None)
        config = getattr(service, "global_config", {}) or {}
        if config.get("runninghub_api_key"):
            return True
    return False


def _raise_runninghub_key_missing(reason: str = "RunningHub API key is required") -> None:
    raise HTTPException(
        status_code=503,
        detail={
            "error": "runninghub_api_key_missing",
            "message": "RunningHub API Key 未配置，无法使用 runninghub 素材分析/出片工作流。",
            "reason": reason,
            "hint": "配置 backend/video_engine/config.yaml 中的 services.runninghub_api_key，或设置环境变量 RUNNINGHUB_API_KEY；本地 ComfyUI 可切换 source=selfhost。",
        },
    )


def _raise_video_service_error(exc: Exception) -> None:
    reason = str(exc)
    if "RunningHub API key is required" in reason:
        _raise_runninghub_key_missing(reason)
    raise HTTPException(
        status_code=503,
        detail={
            "error": "video_service_unavailable",
            "message": "视频素材服务暂不可用，请检查工作流、API Key 或本地 ComfyUI 配置。",
            "reason": f"{type(exc).__name__}: {exc}",
        },
    )


def _video_llm_config_status() -> Dict[str, Any]:
    from pixelle_video.config import config_manager

    cfg = config_manager.config.llm
    api_key_set = bool(os.getenv("VIDEO_LLM_API_KEY") or cfg.api_key)
    base_url = os.getenv("VIDEO_LLM_BASE_URL") or cfg.base_url
    model = os.getenv("VIDEO_LLM_MODEL") or cfg.model
    return {
        "configured": bool(api_key_set and base_url and model),
        "api_key_set": api_key_set,
        "base_url_set": bool(base_url),
        "model": model or "",
        "source": "VIDEO_LLM_* env" if os.getenv("VIDEO_LLM_API_KEY") else "video_engine/config.yaml",
    }


def _content_llm_config_status() -> Dict[str, Any]:
    return {
        "configured": bool(os.getenv("AI_PRIMARY_API_KEY") and os.getenv("AI_PRIMARY_BASE_URL")),
        "api_key_set": bool(os.getenv("AI_PRIMARY_API_KEY")),
        "base_url_set": bool(os.getenv("AI_PRIMARY_BASE_URL")),
        "models": os.getenv("AI_PRIMARY_MODELS") or os.getenv("AI_PRIMARY_MODEL") or "",
        "source": "AI_PRIMARY_* env",
    }


def _video_dependency_config_status(engine: Any) -> Dict[str, Any]:
    return {
        "content_llm": _content_llm_config_status(),
        "video_llm": _video_llm_config_status(),
        "runninghub": {
            "api_key_set": _has_runninghub_api_key(engine),
            "source": "RUNNINGHUB_API_KEY env or video_engine/config.yaml",
        },
        "comfyui": {
            "base_url": getattr(engine.media, "global_config", {}).get("comfyui_url") if getattr(engine, "media", None) else "",
            "api_key_set": bool(getattr(engine.media, "global_config", {}).get("comfyui_api_key")) if getattr(engine, "media", None) else False,
        },
    }


def _require_video_llm_config() -> None:
    status = _video_llm_config_status()
    if status["configured"]:
        return
    raise HTTPException(
        status_code=503,
        detail={
            "error": "video_llm_unconfigured",
            "message": "视频生成专用大模型未配置，不能使用普通内容生成模型 Key 代替。",
            "reason": "VIDEO_LLM_API_KEY / VIDEO_LLM_BASE_URL / VIDEO_LLM_MODEL 或 backend/video_engine/config.yaml: llm 未完整配置。",
            "hint": "请配置 VIDEO_LLM_* 环境变量，或填写 backend/video_engine/config.yaml 中的 llm.api_key、llm.base_url、llm.model。",
        },
    )


def _workflow_source(service: Any, workflow: Optional[str], capability: str) -> str:
    try:
        return service._resolve_workflow(workflow=workflow).get("source", "")
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": f"{capability}_workflow_unconfigured",
                "message": f"{capability} 工作流未配置，无法提交出片任务。",
                "reason": f"{type(exc).__name__}: {exc}",
                "hint": "配置 backend/video_engine/config.yaml 中对应 default_workflow，或在请求中显式传入可用的 workflow。",
            },
        )


def _template_requires_media(template: Optional[str]) -> bool:
    from pixelle_video.utils.template_util import get_template_type

    template_name = Path(template or "1080x1920/default.html").name
    return get_template_type(template_name) in {"image", "video"}


def _require_runninghub_key_for_generate(kwargs: Dict[str, Any]) -> None:
    engine = runtime._engine()
    if _has_runninghub_api_key(engine):
        return

    media_workflow = kwargs.get("media_workflow")
    if _template_requires_media(kwargs.get("frame_template")):
        if (media_workflow and media_workflow.startswith("runninghub/")) or _workflow_source(engine.media, media_workflow, "media") == "runninghub":
            _raise_runninghub_key_missing("RunningHub API key is required for media workflow")

    tts_mode = kwargs.get("tts_inference_mode")
    tts_workflow = kwargs.get("tts_workflow")
    if tts_mode == "comfyui":
        if (tts_workflow and tts_workflow.startswith("runninghub/")) or _workflow_source(engine.tts, tts_workflow, "tts") == "runninghub":
            _raise_runninghub_key_missing("RunningHub API key is required for TTS workflow")


def _workflow_groups() -> Dict[str, Any]:
    """Return workflow choices from initialized Pixelle services."""
    _require_engine()
    engine = runtime._engine()
    return {
        "media": engine.media.list_workflows() if engine.media else [],
        "tts": engine.tts.list_workflows() if engine.tts else [],
        "image_analysis": engine.image_analysis.list_workflows() if engine.image_analysis else [],
        "video_analysis": engine.video_analysis.list_workflows() if engine.video_analysis else [],
    }


def _template_options() -> list[Dict[str, Any]]:
    """List HTML templates with metadata needed by the UI."""
    from pixelle_video.services.frame_html import HTMLFrameGenerator
    from pixelle_video.utils.template_util import (
        get_all_templates_with_info,
        get_template_type,
        resolve_template_path,
    )

    templates = []
    for template in get_all_templates_with_info():
        display = template.display_info
        template_name = Path(template.template_path).name
        item: Dict[str, Any] = {
            "path": template.template_path,
            "name": display.name,
            "size": display.size,
            "width": display.width,
            "height": display.height,
            "orientation": display.orientation,
            "is_standard": display.is_standard,
            "type": get_template_type(template_name),
            "params": {},
            "media_width": None,
            "media_height": None,
        }
        try:
            generator = HTMLFrameGenerator(resolve_template_path(template.template_path))
            media_width, media_height = generator.get_media_size()
            item["params"] = generator.parse_template_parameters()
            item["media_width"] = media_width
            item["media_height"] = media_height
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        templates.append(item)
    return templates


def _tts_voices() -> list[Dict[str, Any]]:
    from pixelle_video.tts_voices import EDGE_TTS_VOICES

    return EDGE_TTS_VOICES


def _bgm_options() -> list[str]:
    from pixelle_video.utils.os_util import list_resource_files

    audio_extensions = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac")
    return [name for name in list_resource_files("bgm") if name.lower().endswith(audio_extensions)]


def _asset_type(path: Path) -> str:
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = path.suffix.lower()
    if ext in image_exts:
        return "image"
    if ext in video_exts:
        return "video"
    return "unknown"


async def _save_asset_uploads(files: list[UploadFile]) -> list[Path]:
    from pixelle_video.utils.os_util import get_data_path

    batch_dir = Path(get_data_path("assets", uuid.uuid4().hex))
    batch_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for upload in files:
        filename = Path(upload.filename or "asset").name
        path = batch_dir / f"{uuid.uuid4().hex}_{filename}"
        with path.open("wb") as f:
            while chunk := await upload.read(1024 * 1024):
                f.write(chunk)
        saved.append(path)
    return saved


# ───────────────────────── Endpoints ─────────────────────────

@router.get("/pipelines")
async def pipelines() -> Dict[str, Any]:
    """List available pipelines and current engine readiness."""
    return {
        "ready": runtime.ENGINE_STATE.ready,
        "error": runtime.ENGINE_STATE.error,
        "pipelines": runtime.list_pipelines(),
    }


@router.get("/options")
async def options() -> Dict[str, Any]:
    """Return Pixelle feature options surfaced by this integration."""
    workflows: Dict[str, Any] = {"media": [], "tts": [], "image_analysis": [], "video_analysis": []}
    workflow_error = None
    try:
        workflows = _workflow_groups()
    except HTTPException as exc:
        workflow_error = exc.detail
    except Exception as exc:  # pragma: no cover - depends on optional services
        workflow_error = f"{type(exc).__name__}: {exc}"

    return {
        "ready": runtime.ENGINE_STATE.ready,
        "error": runtime.ENGINE_STATE.error,
        "pipelines": runtime.list_pipelines(),
        "templates": _template_options(),
        "workflows": workflows,
        "workflow_error": workflow_error,
        "config_status": _video_dependency_config_status(runtime._engine()) if runtime.ENGINE_STATE.ready else None,
        "tts_voices": _tts_voices(),
        "bgm": _bgm_options(),
    }


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    _require_engine()
    _require_video_llm_config()

    # Collect non-None top-level fields plus the explicit extras bag.
    kwargs: Dict[str, Any] = {}
    for key in ("mode", "n_scenes", "min_narration_words", "max_narration_words"):
        value = getattr(req, key)
        if value is not None:
            kwargs[key] = value
    kwargs.update(req.extra)
    if req.template is not None:
        # Pixelle StandardPipeline expects frame_template; keep the public API name concise.
        kwargs["frame_template"] = req.template
    if "template" in kwargs and "frame_template" not in kwargs:
        kwargs["frame_template"] = kwargs.pop("template")

    if req.pipeline not in runtime.list_pipelines():
        raise HTTPException(
            status_code=400,
            detail=f"unknown pipeline: {req.pipeline!r}; available: {runtime.list_pipelines()}",
        )
    _require_runninghub_key_for_generate(kwargs)

    record = runtime.submit_task(text=req.text, pipeline=req.pipeline, **kwargs)
    return GenerateResponse(task_id=record.task_id, status=record.status, pipeline=record.pipeline)


@router.post("/analyze-assets", response_model=AssetAnalysisResponse)
async def analyze_assets(
    files: list[UploadFile] = File(...),
    source: str = Form("runninghub"),
) -> AssetAnalysisResponse:
    """Analyze uploaded image/video assets into text usable by the full-case generator."""
    _require_engine()
    engine = runtime._engine()
    if source == "runninghub" and not _has_runninghub_api_key(engine):
        _raise_runninghub_key_missing()
    saved_paths = await _save_asset_uploads(files)

    results: list[AssetAnalysisItem] = []
    for path in saved_paths:
        asset_type = _asset_type(path)
        try:
            if asset_type == "image":
                description = await engine.image_analysis(str(path), source=source)
            elif asset_type == "video":
                description = await engine.video_analysis(str(path), source=source)
            else:
                description = "Unsupported asset type; kept for reference only."
        except Exception as exc:
            _raise_video_service_error(exc)

        results.append(
            AssetAnalysisItem(
                filename=path.name,
                path=str(path),
                type=asset_type,
                description=description,
            )
        )

    extracted_lines = ["用户上传了以下可用于 IP 内容创作的媒体素材："]
    for idx, item in enumerate(results, 1):
        extracted_lines.append(
            f"{idx}. [{item.type}] {item.filename}\n路径：{item.path}\n素材理解：{item.description}"
        )

    return AssetAnalysisResponse(assets=results, extracted_content="\n\n".join(extracted_lines))


@router.post("/generate-from-assets", response_model=GenerateResponse)
async def generate_from_assets(
    files: list[UploadFile] = File(...),
    video_title: str = Form(""),
    intent: str = Form(""),
    duration: int = Form(30),
    source: str = Form("runninghub"),
    voice_id: str = Form("zh-CN-YunjianNeural"),
    tts_speed: float = Form(1.2),
    bgm_path: str = Form(""),
    bgm_volume: float = Form(0.2),
    bgm_mode: str = Form("loop"),
) -> GenerateResponse:
    """Generate a video directly from uploaded media assets via Pixelle asset_based pipeline."""
    _require_engine()
    if source == "runninghub" and not _has_runninghub_api_key(runtime._engine()):
        _raise_runninghub_key_missing()
    saved_paths = await _save_asset_uploads(files)
    assets = [str(path) for path in saved_paths]
    record = runtime.submit_asset_task(
        assets=assets,
        video_title=video_title,
        intent=intent or video_title or "基于上传素材生成一条适合短视频平台发布的 IP 内容视频",
        duration=duration,
        source=source,
        voice_id=voice_id,
        tts_speed=tts_speed,
        bgm_path=bgm_path or None,
        bgm_volume=bgm_volume,
        bgm_mode=bgm_mode,
    )
    return GenerateResponse(task_id=record.task_id, status=record.status, pipeline=record.pipeline)


@router.get("/history")
async def history(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    _require_engine()
    return await runtime._engine().history.get_task_list(page=page, page_size=page_size)


@router.get("/history/{task_id}")
async def history_detail(task_id: str) -> Dict[str, Any]:
    _require_engine()
    detail = await runtime._engine().history.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"history task not found: {task_id}")
    return detail


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def task_status(task_id: str) -> TaskStatusResponse:
    record = runtime.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    return TaskStatusResponse(**{k: v for k, v in record.to_dict().items() if k != "params"})


@router.get("/tasks/{task_id}/file")
async def task_file(task_id: str) -> FileResponse:
    record = runtime.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    if record.status != "succeeded":
        raise HTTPException(
            status_code=409,
            detail=f"task not ready (status={record.status})",
        )
    if not record.video_path or not os.path.exists(record.video_path):
        raise HTTPException(status_code=410, detail="video file missing on disk")
    return FileResponse(
        path=record.video_path,
        media_type="video/mp4",
        filename=os.path.basename(record.video_path),
    )
