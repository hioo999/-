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
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_routes import get_current_user
from database import get_db
from models.persona import UserAccount, VideoAipProject, VideoAipStepTask
from video_engine import ENGINE_ROOT, runtime

router = APIRouter(prefix="/api/video", tags=["视频引擎"])
MAX_ASSET_UPLOAD_FILES = 8
MAX_ASSET_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_ASSET_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_ASSET_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
}


def _media_storage_roots() -> list[Path]:
    engine_root = Path(os.getenv("PIXELLE_VIDEO_ROOT", ENGINE_ROOT))
    return [
        (engine_root / "data").resolve(),
        (engine_root / "output").resolve(),
    ]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_media_path(value: str | None) -> Path | None:
    if not value:
        return None
    try:
        path = Path(value).resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not path.is_file():
        return None
    if not any(_is_relative_to(path, root) for root in _media_storage_roots()):
        raise HTTPException(status_code=403, detail="媒体文件不在允许访问的存储目录中")
    return path


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


class GenerateMediaRequest(BaseModel):
    prompt: str = Field(..., description="图片/视频生成提示词")
    media_type: str = Field("image", description="image / video")
    workflow: Optional[str] = Field(None, description="Pixelle media 工作流 key，如 runninghub/image_flux.json")
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    negative_prompt: Optional[str] = None
    steps: Optional[int] = None
    seed: Optional[int] = None
    cfg: Optional[float] = None
    sampler: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict, description="透传给 media workflow 的其它参数")


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
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    media_path: Optional[str] = None
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


def _load_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _ensure_record_owner(record, user: UserAccount) -> None:
    if not getattr(record, "user_id", 0) or record.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"task not found: {record.task_id}")


def _video_aip_step_output_by_task_id(db: Session, task_id: str, user: UserAccount) -> tuple[VideoAipStepTask, dict] | None:
    if not task_id:
        return None
    step = (
        db.query(VideoAipStepTask)
        .join(VideoAipProject, VideoAipProject.id == VideoAipStepTask.project_id)
        .filter(
            VideoAipProject.user_id == user.id,
            VideoAipStepTask.output_json.contains(task_id),
        )
        .order_by(VideoAipStepTask.updated_at.desc(), VideoAipStepTask.id.desc())
        .first()
    )
    if not step:
        return None
    output = _load_json(step.output_json, {})
    if output.get("task_id") != task_id:
        return None
    return step, output


def _video_aip_task_status_fallback(db: Session, task_id: str, user: UserAccount) -> TaskStatusResponse | None:
    match = _video_aip_step_output_by_task_id(db, task_id, user)
    if not match:
        return None
    step, output = match
    media_type = output.get("media_type") or output.get("task_type")
    progress = output.get("progress")
    if progress is None:
        progress = 1.0 if step.status in {"succeeded", "failed"} else 0.0
    return TaskStatusResponse(
        task_id=task_id,
        pipeline=f"media:{media_type or 'unknown'}",
        status=output.get("task_status") or step.status,
        progress=float(progress or 0.0),
        current_event=output.get("current_event"),
        error=step.error_message or output.get("error"),
        video_path=output.get("video_path"),
        media_type=media_type,
        media_url=output.get("media_url"),
        media_path=output.get("media_path"),
        duration=output.get("duration"),
        file_size=output.get("file_size"),
    )


def _video_aip_media_path_fallback(db: Session, task_id: str, user: UserAccount) -> tuple[str, str] | None:
    match = _video_aip_step_output_by_task_id(db, task_id, user)
    if not match:
        return None
    step, output = match
    if step.status != "succeeded" and output.get("task_status") != "succeeded":
        raise HTTPException(status_code=409, detail=f"task not ready (status={step.status})")
    path = _safe_media_path(output.get("media_path") or output.get("video_path"))
    if not path:
        return None
    return str(path), output.get("media_type") or output.get("task_type") or "image"


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


def _require_runninghub_key_for_media(workflow: Optional[str]) -> None:
    engine = runtime._engine()
    if _has_runninghub_api_key(engine):
        return
    if (workflow and workflow.startswith("runninghub/")) or _workflow_source(engine.media, workflow, "media") == "runninghub":
        _raise_runninghub_key_missing("RunningHub API key is required for media workflow")


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


def _asset_magic_matches(ext: str, data: bytes) -> bool:
    if ext in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == ".gif":
        return data.startswith((b"GIF87a", b"GIF89a"))
    if ext == ".webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if ext in {".mp4", ".mov"}:
        return len(data) >= 12 and data[4:8] == b"ftyp"
    if ext == ".avi":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"AVI "
    if ext in {".mkv", ".webm"}:
        return data.startswith(b"\x1a\x45\xdf\xa3")
    return False


async def _save_asset_uploads(files: list[UploadFile]) -> list[Path]:
    from pixelle_video.utils.os_util import get_data_path

    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个素材文件")
    if len(files) > MAX_ASSET_UPLOAD_FILES:
        raise HTTPException(status_code=400, detail=f"一次最多上传 {MAX_ASSET_UPLOAD_FILES} 个素材文件")

    batch_dir = Path(get_data_path("assets", uuid.uuid4().hex))
    batch_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    try:
        for upload in files:
            filename = Path(upload.filename or "asset").name
            ext = Path(filename).suffix.lower()
            content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
            if ext not in ALLOWED_ASSET_EXTS or content_type not in ALLOWED_ASSET_CONTENT_TYPES:
                raise HTTPException(status_code=400, detail="只支持常见图片或视频素材文件")
            path = batch_dir / f"{uuid.uuid4().hex}_{filename}"
            size = 0
            with path.open("wb") as f:
                checked_magic = False
                while chunk := await upload.read(1024 * 1024):
                    if not checked_magic:
                        checked_magic = True
                        if not _asset_magic_matches(ext, chunk):
                            raise HTTPException(status_code=400, detail="素材文件内容与格式不匹配")
                    size += len(chunk)
                    if size > MAX_ASSET_UPLOAD_BYTES:
                        raise HTTPException(status_code=400, detail="单个素材文件不能超过 50MB")
                    f.write(chunk)
                if not checked_magic:
                    raise HTTPException(status_code=400, detail="素材文件不能为空")
            saved.append(path)
    except Exception:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise
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
async def generate(req: GenerateRequest, current_user: UserAccount = Depends(get_current_user)) -> GenerateResponse:
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

    record = runtime.submit_task(text=req.text, pipeline=req.pipeline, user_id=current_user.id, **kwargs)
    return GenerateResponse(task_id=record.task_id, status=record.status, pipeline=record.pipeline)


@router.post("/generate-media", response_model=GenerateResponse)
async def generate_media(req: GenerateMediaRequest, current_user: UserAccount = Depends(get_current_user)) -> GenerateResponse:
    """Submit a real Pixelle image/video media generation task."""
    _require_engine()
    if req.media_type not in {"image", "video"}:
        raise HTTPException(status_code=400, detail="media_type must be image or video")
    _require_runninghub_key_for_media(req.workflow)

    kwargs: Dict[str, Any] = {}
    for key in ("width", "height", "duration", "negative_prompt", "steps", "seed", "cfg", "sampler"):
        value = getattr(req, key)
        if value is not None:
            kwargs[key] = value
    kwargs.update(req.extra)
    record = runtime.submit_media_task(
        prompt=req.prompt,
        media_type=req.media_type,
        workflow=req.workflow,
        user_id=current_user.id,
        **kwargs,
    )
    return GenerateResponse(task_id=record.task_id, status=record.status, pipeline=record.pipeline)


@router.post("/analyze-assets", response_model=AssetAnalysisResponse)
async def analyze_assets(
    files: list[UploadFile] = File(...),
    source: str = Form("runninghub"),
    current_user: UserAccount = Depends(get_current_user),
) -> AssetAnalysisResponse:
    """Analyze uploaded image/video assets into text usable by the full-case generator."""
    del current_user
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
    current_user: UserAccount = Depends(get_current_user),
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
        user_id=current_user.id,
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
async def task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
) -> TaskStatusResponse:
    record = runtime.get_task(task_id)
    if record is None:
        fallback = _video_aip_task_status_fallback(db, task_id, current_user)
        if fallback:
            return fallback
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    _ensure_record_owner(record, current_user)
    return TaskStatusResponse(**{k: v for k, v in record.to_dict().items() if k != "params"})


@router.get("/tasks/{task_id}/file")
async def task_file(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
) -> FileResponse:
    record = runtime.get_task(task_id)
    if record is None:
        fallback = _video_aip_media_path_fallback(db, task_id, current_user)
        if fallback:
            path, _media_type = fallback
            return FileResponse(path=path, media_type="video/mp4", filename=os.path.basename(path))
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    _ensure_record_owner(record, current_user)
    if record.status != "succeeded":
        raise HTTPException(
            status_code=409,
            detail=f"task not ready (status={record.status})",
        )
    path = _safe_media_path(record.video_path)
    if not path:
        raise HTTPException(status_code=410, detail="video file missing on disk")
    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=path.name,
    )


@router.get("/tasks/{task_id}/media-file")
async def task_media_file(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
) -> FileResponse:
    record = runtime.get_task(task_id)
    if record is None:
        fallback = _video_aip_media_path_fallback(db, task_id, current_user)
        if fallback:
            path, media_type_name = fallback
            suffix = Path(path).suffix.lower()
            media_type = "video/mp4" if media_type_name == "video" else "image/png"
            if suffix in {".jpg", ".jpeg"}:
                media_type = "image/jpeg"
            elif suffix == ".webp":
                media_type = "image/webp"
            elif suffix in {".mov", ".mp4", ".webm"}:
                media_type = "video/mp4"
            return FileResponse(path=path, media_type=media_type, filename=os.path.basename(path))
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    _ensure_record_owner(record, current_user)
    if record.status != "succeeded":
        raise HTTPException(status_code=409, detail=f"task not ready (status={record.status})")
    path = _safe_media_path(record.media_path or record.video_path)
    if not path:
        raise HTTPException(status_code=410, detail="media file missing on disk")
    suffix = Path(path).suffix.lower()
    media_type = "video/mp4" if record.media_type == "video" else "image/png"
    if suffix in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"
    elif suffix == ".webp":
        media_type = "image/webp"
    elif suffix in {".mov", ".mp4", ".webm"}:
        media_type = "video/mp4"
    return FileResponse(path=path, media_type=media_type, filename=path.name)
