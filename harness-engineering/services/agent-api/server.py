#!/usr/bin/env python3
"""Minimal V4.1 lawyer-side Agent API.

The agent stores and processes business data locally. It can report a strict
health whitelist to the platform, but it never sends case/file/chat content to
the platform.
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import html
import ipaddress
import importlib.util
import json
import math
import os
import re
import shlex
import shutil
import sqlite3
import string
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("AGENT_DATA_DIR", ROOT / "data"))
STORAGE_DIR = Path(os.environ.get("AGENT_STORAGE_DIR", DATA_DIR / "storage"))
OFFICE_PREVIEW_DIR = Path(os.environ.get("AGENT_OFFICE_PREVIEW_DIR", DATA_DIR / "office-previews"))
DB_PATH = Path(os.environ.get("AGENT_DB", DATA_DIR / "agent.db"))
HOST = os.environ.get("AGENT_HOST", "127.0.0.1")
PORT = int(os.environ.get("AGENT_PORT", "8200"))
PLATFORM_BASE_URL = os.environ.get("AGENT_PLATFORM_BASE_URL", "http://127.0.0.1:8100")
ADMIN_PASSWORD = os.environ.get("AGENT_ADMIN_PASSWORD", "admin")
SECRET_KEY = os.environ.get("AGENT_SECRET_KEY", ADMIN_PASSWORD)
SESSION_TTL_SECONDS = int(os.environ.get("AGENT_SESSION_TTL_SECONDS", "86400"))
ALLOWED_FILE_EXTENSIONS = {
    item.strip().lower()
    for item in os.environ.get("AGENT_ALLOWED_FILE_EXTENSIONS", ".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg,.bmp,.tiff,.txt,.md,.csv").split(",")
    if item.strip()
}
MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("AGENT_MAX_UPLOAD_SIZE_MB", "100")) * 1024 * 1024
MODEL_REQUEST_TIMEOUT_SECONDS = float(os.environ.get("AGENT_MODEL_REQUEST_TIMEOUT_SECONDS", "15"))
MODEL_CONNECTIVITY_TIMEOUT_SECONDS = float(os.environ.get("AGENT_MODEL_CONNECTIVITY_TIMEOUT_SECONDS", "2"))
MODEL_CONNECTIVITY_PROBE_LOCAL_DNS = os.environ.get("AGENT_MODEL_CONNECTIVITY_PROBE_LOCAL_DNS", "0") == "1"
QDRANT_URL = os.environ.get("AGENT_QDRANT_URL", "").rstrip("/")
QDRANT_COLLECTION = os.environ.get("AGENT_QDRANT_COLLECTION", "case_chunks")
QDRANT_TIMEOUT_SECONDS = float(os.environ.get("AGENT_QDRANT_TIMEOUT_SECONDS", "5"))
OCR_COMMAND = os.environ.get("AGENT_OCR_COMMAND", "").strip()
OCR_TIMEOUT_SECONDS = float(os.environ.get("AGENT_OCR_TIMEOUT_SECONDS", "30"))
OFFICE_CONVERTER_COMMAND = os.environ.get("AGENT_OFFICE_CONVERTER_COMMAND", "").strip() or (shutil.which("soffice") or shutil.which("libreoffice") or "")
OFFICE_CONVERT_TIMEOUT_SECONDS = float(os.environ.get("AGENT_OFFICE_CONVERT_TIMEOUT_SECONDS", "45"))
OFFICE_FILE_EXTENSIONS = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}
DIRECT_PREVIEW_FILE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".txt", ".md", ".csv"}
DEFAULT_KNOWLEDGE_BASES = [
    {"type": "private", "name": "AI资料", "description": "个人沉淀的 AI 资料、模型说明、工具文档和研究素材", "knowledge_type": "ai_ready", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "allow_generation"},
    {"type": "private", "name": "AI知识库", "description": "个人可复用的 AI 知识、提示词、案例和操作方法", "knowledge_type": "ai_ready", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "allow_generation"},
    {"type": "private", "name": "战略思维", "description": "战略、商业、管理和长期判断相关资料", "knowledge_type": "general", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "allow_generation"},
    {"type": "private", "name": "读书学习", "description": "读书笔记、课程学习、摘录和复盘内容", "knowledge_type": "training", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "allow_generation"},
    {"type": "team", "name": "开发", "description": "团队开发资料、工程规范、代码实践和技术文档", "knowledge_type": "department_practice", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "allow_generation"},
    {"type": "team", "name": "工具演练", "description": "工具试用记录、操作步骤、评测结果和演练资料", "knowledge_type": "training", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "allow_generation"},
    {"type": "team", "name": "公众号资料", "description": "公众号选题、素材、文章资料和发布参考", "knowledge_type": "general", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "allow_generation"},
    {"type": "team", "name": "教学课程", "description": "课程大纲、教学材料、训练营和知识产品资料", "knowledge_type": "training", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "allow_generation"},
    {"type": "team", "name": "海鸥知识库-实用提示词", "description": "团队共享的实用提示词、问答范式和 AI 操作模板", "knowledge_type": "ai_ready", "review_status": "published", "confidentiality_level": "internal", "ai_usage_policy": "search_only"},
]
OCR_ALLOWED_COMMANDS = {
    item.strip()
    for item in os.environ.get("AGENT_OCR_ALLOWED_COMMANDS", "tesseract,paddleocr,python3").split(",")
    if item.strip()
}


class PreviewContentNotReadyError(RuntimeError):
    pass


class PreviewContentBlockedError(PermissionError):
    pass
WORKER_BATCH_SIZE = int(os.environ.get("AGENT_WORKER_BATCH_SIZE", "20"))
WORKER_SLEEP_SECONDS = float(os.environ.get("AGENT_WORKER_SLEEP_SECONDS", "5"))
WORKER_MAX_RETRIES = int(os.environ.get("AGENT_WORKER_MAX_RETRIES", "3"))
ALLOWED_DATA_ROOTS = [Path(item).expanduser().resolve() for item in os.environ.get("AGENT_ALLOWED_DATA_ROOTS", "").split(",") if item.strip()]
FORBIDDEN_DATA_ROOTS = [
    Path(item).expanduser().resolve()
    for item in os.environ.get("AGENT_FORBIDDEN_DATA_ROOTS", "/etc,/private/etc,/System,/bin,/sbin,/usr/bin,/usr/sbin,/var/root,/root").split(",")
    if item.strip()
]
FORBIDDEN_PATH_PARTS = {
    item.strip()
    for item in os.environ.get("AGENT_FORBIDDEN_PATH_PARTS", ".ssh,.gnupg,.aws,.kube").split(",")
    if item.strip()
}

HEALTH_ALLOWED_FIELDS = {
    "tenant_id",
    "agent_id",
    "agent_version",
    "status",
    "last_heartbeat",
    "task_pending_count",
    "task_running_count",
    "task_failed_count",
    "error_code",
    "cpu_usage",
    "memory_usage",
    "disk_usage",
}

ERROR_CODES = {
    "AGENT_OFFLINE",
    "AGENT_AUTH_FAILED",
    "DIR_PERMISSION_DENIED",
    "FILE_PARSE_FAILED",
    "OCR_FAILED",
    "VECTOR_INSERT_FAILED",
    "LLM_TIMEOUT",
    "LLM_AUTH_FAILED",
    "DB_CONN_FAILED",
    "DB_AUTH_FAILED",
    "DB_READONLY_REQUIRED",
    "UNKNOWN_ERROR",
}

KNOWLEDGE_TYPES = {
    "general",
    "regulation",
    "case_law",
    "template",
    "clause",
    "pleading",
    "training",
    "project_review",
    "client_industry",
    "department_practice",
    "matter_workspace",
    "partner_selected",
    "ai_ready",
    "search_only",
}
KNOWLEDGE_REVIEW_STATUSES = {
    "draft",
    "pending_review",
    "published",
    "rejected",
    "archived",
    "deprecated",
    "needs_update",
    "ai_disabled",
}
KNOWLEDGE_CONFIDENTIALITY_LEVELS = {"public", "internal", "confidential", "restricted"}
KNOWLEDGE_AI_USAGE_POLICIES = {"allow_generation", "search_only", "disabled"}
HIGH_IMPACT_REVIEW_KNOWLEDGE_TYPES = {"template", "clause", "pleading"}
KNOWLEDGE_REVIEWER_LOCAL_ROLES = {"agent_admin", "lead_lawyer", "co_lawyer"}
LEGAL_ANSWER_SECTIONS = ("结论：", "依据：", "引用来源：", "适用前提：", "风险提示：", "不确定事项：", "建议下一步：")
AI_FEEDBACK_ISSUE_LABELS = {
    "citation_missing",
    "citation_inaccurate",
    "insufficient_evidence",
    "answer_inaccurate",
    "answer_incomplete",
    "legal_reasoning_risk",
    "permission_anomaly",
    "missed_question",
    "other",
    "knowledge_base_chat",
}
AI_FEEDBACK_ISSUE_ALIASES = {
    "citation": "citation_missing",
    "no_citation": "citation_missing",
    "source_missing": "citation_missing",
    "evidence_insufficient": "insufficient_evidence",
    "citation_inaccurate": "answer_inaccurate",
    "legal_reasoning_risk": "answer_inaccurate",
    "context_reasoning_risk": "answer_inaccurate",
    "permission_exception": "permission_anomaly",
    "permission_issue": "permission_anomaly",
}
HIGH_SENSITIVE_PROCESS_STATUS = "ai_disabled"
KNOWLEDGE_TRUST_LEVELS = {
    "regulation": "authoritative",
    "case_law": "authoritative",
    "template": "reviewed_template",
    "clause": "reviewed_template",
    "pleading": "reviewed_template",
    "partner_selected": "expert_experience",
    "department_practice": "expert_experience",
    "matter_workspace": "matter_fact",
    "project_review": "experience",
    "client_industry": "background",
    "training": "training",
    "ai_ready": "reviewed_template",
    "search_only": "reference_only",
    "general": "general",
}
SCENARIO_PROMPTS = {
    "contract_review": "请从当前材料中识别合同审查要点，重点列出高风险条款、依据、风险等级和建议修改方向。",
    "case_law_research": "请从当前材料中检索类似案例、裁判观点和可引用依据，并说明适用前提与差异风险。",
    "regulation_search": "请从当前材料中检索相关法律法规、规则依据和适用条件，并区分明确依据与待核验内容。",
    "risk_summary": "请为合伙人汇总当前客户或项目的核心法律风险、证据依据、未决问题和下一步处理建议。",
    "dispute_focus": "请根据当前案件或材料提炼争议焦点、支持事实、相反风险和需要补充的证据。",
    "due_diligence_checklist": "请根据当前材料生成尽调问题清单，区分已发现风险、待补充材料和建议访谈问题。",
}

MAINLAND_ID_CARD_RE = re.compile(r"(?<![0-9A-Za-z])([1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx])(?![0-9A-Za-z])")
MAINLAND_MOBILE_RE = re.compile(r"(?<!\d)(1[3-9]\d[ -]?\d{4}[ -]?\d{4})(?!\d)")
BANK_CARD_RE = re.compile(r"(?<![0-9A-Za-z])((?:\d[ -]?){13,19})(?![0-9A-Za-z])")


class CaseAccessError(PermissionError):
    """Raised when a local user is not authorized for a case workspace."""


def load_local_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


health_reporter_module = load_local_module("agent_health_reporter", "app/services/health_reporter.py")
to_platform_health_payload = health_reporter_module.to_platform_health_payload


def now() -> int:
    return int(time.time())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def normalize_choice(value: Any, allowed: set[str], default: str, field_name: str) -> str:
    normalized = str(value if value is not None else default).strip() or default
    if normalized not in allowed:
        raise ValueError(f"invalid {field_name}")
    return normalized


def optional_int(value: Any, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field_name}") from exc


def optional_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    return default


def tokenize(text: str) -> list[str]:
    text = text.lower()
    text = text.translate(str.maketrans({ch: " " for ch in string.punctuation}))
    ascii_words = re.findall(r"[a-z0-9_]+", text)
    cjk_stop = set("的是了在和与及或本案是否涉及当前这个那个什么如何可以有关没有")
    cjk_chars = [ch for ch in re.findall(r"[\u4e00-\u9fff]", text) if ch not in cjk_stop]
    cjk_bigrams = ["".join(cjk_chars[i : i + 2]) for i in range(max(len(cjk_chars) - 1, 0))]
    return ascii_words + cjk_chars + cjk_bigrams


def split_chunks(text: str, size: int = 600, overlap: int = 80) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += max(size - overlap, 1)
    return chunks


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def valid_luhn(value: str) -> bool:
    digits = only_digits(value)
    if len(digits) < 13 or len(digits) > 19 or len(set(digits)) == 1:
        return False
    total = 0
    reverse_digits = digits[::-1]
    for idx, ch in enumerate(reverse_digits):
        digit = int(ch)
        if idx % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def valid_mainland_id_card(value: str) -> bool:
    normalized = value.upper()
    if not MAINLAND_ID_CARD_RE.fullmatch(normalized):
        return False
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    checks = "10X98765432"
    total = sum(int(normalized[idx]) * weights[idx] for idx in range(17))
    return normalized[-1] == checks[total % 11]


def detect_high_sensitive_signals(text: str) -> dict[str, int]:
    signals: dict[str, set[str]] = {
        "mainland_id_card": set(),
        "mainland_mobile": set(),
        "bank_card": set(),
    }
    for match in MAINLAND_ID_CARD_RE.finditer(text):
        candidate = match.group(1).upper()
        if valid_mainland_id_card(candidate):
            signals["mainland_id_card"].add(candidate)
    for match in MAINLAND_MOBILE_RE.finditer(text):
        candidate = only_digits(match.group(1))
        if len(candidate) == 11:
            signals["mainland_mobile"].add(candidate)
    for match in BANK_CARD_RE.finditer(text):
        candidate = only_digits(match.group(1))
        if candidate in signals["mainland_mobile"] or candidate in signals["mainland_id_card"]:
            continue
        if valid_luhn(candidate):
            signals["bank_card"].add(candidate)
    return {name: len(values) for name, values in signals.items() if values}


def parse_txt(path: Path) -> str:
    return path.read_text("utf-8", errors="ignore")


def xml_text_fragments(xml: str) -> list[str]:
    xml = re.sub(r"<[^>]+>", " ", xml)
    text = html.unescape(xml)
    return [fragment.strip() for fragment in re.split(r"\s+", text) if fragment.strip()]


def read_zip_member_texts(path: Path, name_pattern: re.Pattern[str]) -> list[str]:
    fragments: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            if name_pattern.match(name):
                xml = zf.read(name).decode("utf-8", errors="ignore")
                fragments.extend(xml_text_fragments(xml))
    return fragments


def parse_docx(path: Path) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            if re.match(r"word/(document|header\d*|footer\d*)\.xml$", name):
                xml = zf.read(name).decode("utf-8", errors="ignore")
                xml = re.sub(r"<w:tab\s*/>", "\t", xml)
                xml = re.sub(r"</w:p>", "\n", xml)
                text = re.sub(r"<[^>]+>", "", xml)
                paragraphs.extend(line.strip() for line in html.unescape(text).splitlines() if line.strip())
    return "\n".join(paragraphs)


def parse_pptx(path: Path) -> str:
    fragments = read_zip_member_texts(path, re.compile(r"ppt/(slides|notesSlides)/[^/]+\.xml$"))
    return "\n".join(fragments)


def parse_xlsx(path: Path) -> str:
    fragments = read_zip_member_texts(path, re.compile(r"xl/(sharedStrings|worksheets)/[^/]+\.xml$|xl/sharedStrings\.xml$"))
    return "\n".join(fragments)


def parse_legacy_office_best_effort(path: Path) -> str:
    data = path.read_bytes()[:2_000_000]
    candidates = []
    for encoding in ("utf-8", "gb18030", "latin-1"):
        decoded = data.decode(encoding, errors="ignore")
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", decoded)
        cleaned = re.sub(r"\s+", " ", cleaned)
        segments = re.findall(r"[\u4e00-\u9fffA-Za-z0-9，。；：、（）《》“”\"'!?.,;:()\-_/ ]{4,}", cleaned)
        text = "\n".join(segment.strip() for segment in segments if segment.strip())
        candidates.append(text)
    return max(candidates, key=len)[:8000]


def preview_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
    }.get(suffix, "application/octet-stream")


def office_preview_pdf_path(file_id: str, file_hash: str | None, modified_at: int | None) -> Path:
    key = hashlib.sha256(f"{file_id}:{file_hash or ''}:{modified_at or 0}".encode("utf-8")).hexdigest()[:24]
    return OFFICE_PREVIEW_DIR / f"{key}.pdf"


def ensure_office_preview_pdf(source: Path, output: Path) -> None:
    if not OFFICE_CONVERTER_COMMAND:
        raise RuntimeError("office converter is not configured")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.stat().st_size > 0:
        return
    tmp_dir = output.parent / f"tmp-{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    if "{input}" in OFFICE_CONVERTER_COMMAND:
        command = [part.replace("{input}", str(source)).replace("{output_dir}", str(tmp_dir)) for part in shlex.split(OFFICE_CONVERTER_COMMAND)]
    else:
        command = [
            OFFICE_CONVERTER_COMMAND,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_dir),
            str(source),
        ]
    try:
        completed = subprocess.run(command, capture_output=True, check=False, text=True, timeout=OFFICE_CONVERT_TIMEOUT_SECONDS)
        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout or "office converter returned non-zero exit").strip()
            raise RuntimeError(error[:300])
        converted = tmp_dir / f"{source.stem}.pdf"
        if not converted.exists() or converted.stat().st_size == 0:
            matches = list(tmp_dir.glob("*.pdf"))
            if not matches:
                raise RuntimeError("office converter did not produce a PDF")
            converted = matches[0]
        shutil.move(str(converted), output)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def parse_pdf_best_effort(path: Path) -> str:
    data = path.read_bytes()
    # Best-effort text extraction for MVP fixtures and simple text PDFs.
    decoded = data.decode("latin-1", errors="ignore")
    matches = re.findall(r"\(([^()]{2,})\)\s*Tj", decoded)
    matches += re.findall(r"\(([^()]{2,})\)", decoded)
    visible = "\n".join(matches)
    if visible.strip():
        return visible
    ascii_text = re.sub(r"[^\x20-\x7E\n\r\t]+", " ", decoded)
    ascii_text = re.sub(r"\s+", " ", ascii_text)
    return ascii_text[:5000]


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_local_data_path(path: Path) -> None:
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise PermissionError("symbolic link data paths are not allowed")
    resolved = expanded.resolve()
    if any(part in FORBIDDEN_PATH_PARTS for part in resolved.parts):
        raise PermissionError("data path contains a forbidden sensitive segment")
    if any(path_is_relative_to(resolved, root) for root in FORBIDDEN_DATA_ROOTS):
        raise PermissionError("data path is under a forbidden system directory")
    if ALLOWED_DATA_ROOTS and not any(path_is_relative_to(resolved, root) for root in ALLOWED_DATA_ROOTS):
        raise PermissionError("data path is outside configured allowed roots")


def validate_ocr_command(command: list[str]) -> None:
    if not command:
        raise PermissionError("OCR command is empty")
    executable = Path(command[0]).name
    if executable not in OCR_ALLOWED_COMMANDS:
        raise PermissionError("OCR command is not in the allowed command list")
    dangerous = {";", "&&", "||", "|", ">", "<", "`", "$()"}
    if any(part in dangerous for part in command):
        raise PermissionError("OCR command contains unsafe shell control tokens")


def run_ocr_command(path: Path) -> str:
    if not OCR_COMMAND:
        return f"[OCR_PENDING] image file {path.name} requires OCR engine configuration."
    command = [part.replace("{file}", str(path)) for part in shlex.split(OCR_COMMAND)]
    if not any(str(path) in part for part in command):
        command.append(str(path))
    try:
        validate_ocr_command(command)
    except PermissionError as exc:
        return f"[OCR_BLOCKED] image file {path.name}: {exc}"
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=OCR_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"[OCR_FAILED] image file {path.name} OCR timed out."
    except Exception as exc:
        return f"[OCR_FAILED] image file {path.name} OCR command failed: {exc}"
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "OCR command returned non-zero exit").strip()
        return f"[OCR_FAILED] image file {path.name}: {error[:300]}"
    text = completed.stdout.strip()
    if not text:
        return f"[OCR_EMPTY] image file {path.name} produced no text."
    return text


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".csv"}:
        return parse_txt(path)
    if suffix == ".docx":
        return parse_docx(path)
    if suffix == ".pptx":
        return parse_pptx(path)
    if suffix == ".xlsx":
        return parse_xlsx(path)
    if suffix in {".doc", ".ppt", ".xls"}:
        return parse_legacy_office_best_effort(path)
    if suffix == ".pdf":
        return parse_pdf_best_effort(path)
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        return run_ocr_command(path)
    return parse_txt(path)


def validate_upload_filename(filename: str) -> str:
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename or "/" in filename or "\\" in filename:
        raise ValueError("invalid file name")
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_FILE_EXTENSIONS:
        raise ValueError(f"file extension is not allowed: {suffix or '<none>'}")
    return safe_name


def decode_upload_content(content_b64: str) -> bytes:
    try:
        content = base64.b64decode(content_b64, validate=True)
    except Exception as exc:
        raise ValueError("invalid base64 file content") from exc
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("file exceeds configured upload size limit")
    return content


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for idx in range(1, 10_000):
        candidate = parent / f"{stem}-{idx}{suffix}"
        if not candidate.exists():
            return candidate
    raise ValueError("cannot allocate unique file path")


def stable_uuid(value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def derive_secret_key(salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", SECRET_KEY.encode("utf-8"), salt, 120_000, dklen=32)


def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(byte ^ key[idx % len(key)] for idx, byte in enumerate(data))


def encrypt_secret(value: str) -> str:
    salt = os.urandom(16)
    key = derive_secret_key(salt)
    plaintext = value.encode("utf-8")
    ciphertext = xor_bytes(plaintext, key)
    mac = hmac.new(key, plaintext, hashlib.sha256).digest()
    payload = base64.urlsafe_b64encode(salt + mac + ciphertext).decode("ascii")
    return f"v1${payload}"


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("v1$"):
        try:
            raw = base64.urlsafe_b64decode(value[3:].encode("ascii"))
            salt = raw[:16]
            mac = raw[16:48]
            ciphertext = raw[48:]
            key = derive_secret_key(salt)
            plaintext = xor_bytes(ciphertext, key)
            expected = hmac.new(key, plaintext, hashlib.sha256).digest()
            if not hmac.compare_digest(mac, expected):
                return None
            return plaintext.decode("utf-8")
        except Exception:
            return None
    # Backward compatibility for earlier local prototype data.
    try:
        return base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
    except Exception:
        return None


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 180_000)
    return "pbkdf2_sha256$180000$" + base64.urlsafe_b64encode(salt).decode("ascii") + "$" + base64.urlsafe_b64encode(digest).decode("ascii")


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    if not encoded.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password, encoded)
    try:
        _, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def is_allowed_local_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost", "host.docker.internal"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private or ip.is_link_local
    except ValueError:
        return False


def should_probe_model_connectivity_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.endswith(".local") and not MODEL_CONNECTIVITY_PROBE_LOCAL_DNS:
        return False
    return True


class Store:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._closed = False
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS local_users (
                id TEXT PRIMARY KEY,
                account TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                last_login_at INTEGER,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS local_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                account TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS local_data_sources (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                path TEXT NOT NULL,
                status TEXT NOT NULL,
                permission_status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS case_spaces (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                cause_of_action TEXT,
                court TEXT,
                stage TEXT,
                client_name TEXT,
                owner_id TEXT,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS case_members (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role_code TEXT NOT NULL,
                granted_by TEXT,
                granted_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS local_files (
                id TEXT PRIMARY KEY,
                data_source_id TEXT,
                case_id TEXT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_ext TEXT,
                file_size INTEGER,
                file_hash TEXT,
                modified_at INTEGER,
                process_status TEXT NOT NULL,
                review_status TEXT NOT NULL DEFAULT 'published',
                confidentiality_level TEXT NOT NULL DEFAULT 'internal',
                maintainer_id TEXT,
                expires_at INTEGER,
                ai_usage_policy TEXT NOT NULL DEFAULT 'allow_generation',
                ai_enabled INTEGER NOT NULL DEFAULT 1,
                is_high_sensitive INTEGER NOT NULL DEFAULT 0,
                sensitive_signal_types TEXT NOT NULL DEFAULT '[]',
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS processing_tasks (
                id TEXT PRIMARY KEY,
                file_id TEXT,
                case_id TEXT,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL,
                error_code TEXT,
                retry_count INTEGER DEFAULT 0,
                started_at INTEGER,
                finished_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                case_id TEXT,
                file_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                page_number INTEGER,
                paragraph_ref TEXT,
                token_count INTEGER,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vector_index_refs (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL,
                vector_collection TEXT NOT NULL,
                vector_id TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS local_embedding_vectors (
                chunk_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                user_id TEXT,
                title TEXT,
                save_mode TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                has_citations INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS citations (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                page_number INTEGER,
                quote_text TEXT NOT NULL,
                relevance_score REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidences (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                evidence_name TEXT NOT NULL,
                evidence_type TEXT,
                purpose TEXT,
                related_issue TEXT,
                sort_order INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS access_watermarks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_account TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                action TEXT NOT NULL,
                watermark_text TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS high_risk_access_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                action TEXT NOT NULL,
                risk_reasons TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS model_configs (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                base_url TEXT,
                chat_model TEXT,
                embedding_model TEXT,
                api_key_encrypted TEXT,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                owner_type TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                knowledge_type TEXT NOT NULL DEFAULT 'general',
                business_domain TEXT,
                legal_domain TEXT,
                jurisdiction TEXT,
                client_id TEXT,
                matter_id TEXT,
                department_id TEXT,
                project_team_id TEXT,
                ethical_wall_enabled INTEGER NOT NULL DEFAULT 0,
                review_status TEXT NOT NULL DEFAULT 'draft',
                confidentiality_level TEXT NOT NULL DEFAULT 'internal',
                maintainer_id TEXT,
                expires_at INTEGER,
                ai_usage_policy TEXT NOT NULL DEFAULT 'allow_generation',
                citation_priority INTEGER NOT NULL DEFAULT 0,
                ai_enabled INTEGER NOT NULL DEFAULT 1,
                default_permission_policy TEXT NOT NULL DEFAULT 'private',
                status TEXT NOT NULL DEFAULT 'active',
                created_by TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge_base_members (
                id TEXT PRIMARY KEY,
                knowledge_base_id TEXT NOT NULL,
                principal_type TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                role_code TEXT NOT NULL,
                granted_by TEXT,
                granted_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge_base_review_logs (
                id TEXT PRIMARY KEY,
                knowledge_base_id TEXT NOT NULL,
                action TEXT NOT NULL,
                from_status TEXT NOT NULL,
                to_status TEXT NOT NULL,
                operator_id TEXT NOT NULL,
                comment TEXT,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge_base_governance_audit (
                id TEXT PRIMARY KEY,
                knowledge_base_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                operator_id TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                knowledge_base_id TEXT NOT NULL,
                parent_id TEXT,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                permission_inherit INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active',
                created_by TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                deleted_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS acl_entries (
                id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                principal_type TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                action TEXT NOT NULL,
                effect TEXT NOT NULL,
                inherit INTEGER NOT NULL DEFAULT 1,
                created_by TEXT,
                created_at INTEGER NOT NULL,
                expires_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS agent_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enterprise_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS organization_units (
                id TEXT PRIMARY KEY,
                enterprise_id TEXT NOT NULL,
                parent_id TEXT,
                name TEXT NOT NULL,
                unit_type TEXT NOT NULL DEFAULT 'department',
                source_type TEXT NOT NULL DEFAULT 'manual',
                external_id TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS organization_members (
                id TEXT PRIMARY KEY,
                enterprise_id TEXT NOT NULL,
                unit_id TEXT,
                user_id TEXT NOT NULL,
                position TEXT,
                source_type TEXT NOT NULL DEFAULT 'manual',
                external_user_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                joined_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS external_org_integrations (
                id TEXT PRIMARY KEY,
                enterprise_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                corp_id TEXT,
                agent_id TEXT,
                app_key TEXT,
                app_id TEXT,
                secret_encrypted TEXT,
                callback_url TEXT,
                sync_enabled INTEGER NOT NULL DEFAULT 0,
                last_sync_at INTEGER,
                sync_status TEXT NOT NULL DEFAULT 'not_configured',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_assistant_settings (
                id TEXT PRIMARY KEY,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                name TEXT NOT NULL,
                system_prompt TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                allowed_knowledge_base_ids TEXT NOT NULL DEFAULT '[]',
                updated_by TEXT,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_assistant_feedback (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                message_id TEXT,
                user_id TEXT,
                rating TEXT NOT NULL,
                comment TEXT,
                issue_label TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                handler_id TEXT,
                handled_at INTEGER,
                resolution_comment TEXT,
                created_at INTEGER NOT NULL
            );
            """
        )
        self.conn.commit()
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(local_users)").fetchall()}
        if "password_hash" not in columns:
            self.conn.execute("ALTER TABLE local_users ADD COLUMN password_hash TEXT")
            self.conn.commit()
        if "status" not in columns:
            self.conn.execute("ALTER TABLE local_users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
            self.conn.commit()
        if "last_login_at" not in columns:
            self.conn.execute("ALTER TABLE local_users ADD COLUMN last_login_at INTEGER")
            self.conn.commit()
        file_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(local_files)").fetchall()}
        local_file_migrations = {
            "knowledge_base_id": "ALTER TABLE local_files ADD COLUMN knowledge_base_id TEXT",
            "folder_id": "ALTER TABLE local_files ADD COLUMN folder_id TEXT",
            "storage_mode": "ALTER TABLE local_files ADD COLUMN storage_mode TEXT NOT NULL DEFAULT 'uploaded'",
            "deleted_at": "ALTER TABLE local_files ADD COLUMN deleted_at INTEGER",
            "review_status": "ALTER TABLE local_files ADD COLUMN review_status TEXT NOT NULL DEFAULT 'published'",
            "confidentiality_level": "ALTER TABLE local_files ADD COLUMN confidentiality_level TEXT NOT NULL DEFAULT 'internal'",
            "maintainer_id": "ALTER TABLE local_files ADD COLUMN maintainer_id TEXT",
            "expires_at": "ALTER TABLE local_files ADD COLUMN expires_at INTEGER",
            "ai_usage_policy": "ALTER TABLE local_files ADD COLUMN ai_usage_policy TEXT NOT NULL DEFAULT 'allow_generation'",
            "ai_enabled": "ALTER TABLE local_files ADD COLUMN ai_enabled INTEGER NOT NULL DEFAULT 1",
            "is_high_sensitive": "ALTER TABLE local_files ADD COLUMN is_high_sensitive INTEGER NOT NULL DEFAULT 0",
            "sensitive_signal_types": "ALTER TABLE local_files ADD COLUMN sensitive_signal_types TEXT NOT NULL DEFAULT '[]'",
        }
        for column_name, statement in local_file_migrations.items():
            if column_name not in file_columns:
                self.conn.execute(statement)
                self.conn.commit()
        knowledge_base_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(knowledge_bases)").fetchall()}
        knowledge_base_migrations = {
            "knowledge_type": "ALTER TABLE knowledge_bases ADD COLUMN knowledge_type TEXT NOT NULL DEFAULT 'general'",
            "business_domain": "ALTER TABLE knowledge_bases ADD COLUMN business_domain TEXT",
            "legal_domain": "ALTER TABLE knowledge_bases ADD COLUMN legal_domain TEXT",
            "jurisdiction": "ALTER TABLE knowledge_bases ADD COLUMN jurisdiction TEXT",
            "client_id": "ALTER TABLE knowledge_bases ADD COLUMN client_id TEXT",
            "matter_id": "ALTER TABLE knowledge_bases ADD COLUMN matter_id TEXT",
            "department_id": "ALTER TABLE knowledge_bases ADD COLUMN department_id TEXT",
            "project_team_id": "ALTER TABLE knowledge_bases ADD COLUMN project_team_id TEXT",
            "ethical_wall_enabled": "ALTER TABLE knowledge_bases ADD COLUMN ethical_wall_enabled INTEGER NOT NULL DEFAULT 0",
            "review_status": "ALTER TABLE knowledge_bases ADD COLUMN review_status TEXT NOT NULL DEFAULT 'draft'",
            "confidentiality_level": "ALTER TABLE knowledge_bases ADD COLUMN confidentiality_level TEXT NOT NULL DEFAULT 'internal'",
            "maintainer_id": "ALTER TABLE knowledge_bases ADD COLUMN maintainer_id TEXT",
            "expires_at": "ALTER TABLE knowledge_bases ADD COLUMN expires_at INTEGER",
            "ai_usage_policy": "ALTER TABLE knowledge_bases ADD COLUMN ai_usage_policy TEXT NOT NULL DEFAULT 'allow_generation'",
            "citation_priority": "ALTER TABLE knowledge_bases ADD COLUMN citation_priority INTEGER NOT NULL DEFAULT 0",
        }
        for column_name, statement in knowledge_base_migrations.items():
            if column_name not in knowledge_base_columns:
                self.conn.execute(statement)
                self.conn.commit()
        feedback_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(ai_assistant_feedback)").fetchall()}
        feedback_migrations = {
            "status": "ALTER TABLE ai_assistant_feedback ADD COLUMN status TEXT NOT NULL DEFAULT 'open'",
            "handler_id": "ALTER TABLE ai_assistant_feedback ADD COLUMN handler_id TEXT",
            "handled_at": "ALTER TABLE ai_assistant_feedback ADD COLUMN handled_at INTEGER",
            "resolution_comment": "ALTER TABLE ai_assistant_feedback ADD COLUMN resolution_comment TEXT",
        }
        for column_name, statement in feedback_migrations.items():
            if column_name not in feedback_columns:
                self.conn.execute(statement)
                self.conn.commit()
        acl_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(acl_entries)").fetchall()}
        if "expires_at" not in acl_columns:
            self.conn.execute("ALTER TABLE acl_entries ADD COLUMN expires_at INTEGER")
            self.conn.commit()
        if not self.conn.execute("SELECT 1 FROM local_users WHERE account = 'admin'").fetchone():
            self.conn.execute(
                "INSERT INTO local_users (id, account, name, role, password_hash, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("u_admin", "admin", "Agent Admin", "agent_admin", hash_password(ADMIN_PASSWORD), "active", now()),
            )
            self.conn.commit()
        self.ensure_indexes()
        self.ensure_case_knowledge_bases()
        self.ensure_default_knowledge_bases()

    def ensure_indexes(self) -> None:
        self.conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_feedback_status
                ON ai_assistant_feedback (status, rating, issue_label, created_at);
            DELETE FROM knowledge_base_members
            WHERE rowid NOT IN (
                SELECT MAX(rowid)
                FROM knowledge_base_members
                GROUP BY knowledge_base_id, principal_type, principal_id
            );
            DELETE FROM acl_entries
            WHERE rowid NOT IN (
                SELECT MAX(rowid)
                FROM acl_entries
                GROUP BY resource_type, resource_id, principal_type, principal_id, action
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ux_kb_members_principal
                ON knowledge_base_members (knowledge_base_id, principal_type, principal_id);
            CREATE INDEX IF NOT EXISTS idx_kb_review_logs_kb_time
                ON knowledge_base_review_logs (knowledge_base_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_kb_governance_audit_kb_time
                ON knowledge_base_governance_audit (knowledge_base_id, created_at);
            CREATE UNIQUE INDEX IF NOT EXISTS ux_acl_resource_principal_action
                ON acl_entries (resource_type, resource_id, principal_type, principal_id, action);
            CREATE INDEX IF NOT EXISTS idx_folders_kb_parent_name
                ON folders (knowledge_base_id, parent_id, name);
            CREATE INDEX IF NOT EXISTS idx_local_files_kb_folder_deleted
                ON local_files (knowledge_base_id, folder_id, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_local_files_kb_hash_deleted
                ON local_files (knowledge_base_id, file_hash, deleted_at);
            CREATE INDEX IF NOT EXISTS idx_local_files_governance
                ON local_files (knowledge_base_id, review_status, ai_usage_policy, ai_enabled, expires_at);
            CREATE INDEX IF NOT EXISTS idx_knowledge_bases_governance
                ON knowledge_bases (knowledge_type, review_status, confidentiality_level, ai_usage_policy);
            CREATE INDEX IF NOT EXISTS idx_knowledge_bases_isolation
                ON knowledge_bases (client_id, matter_id, department_id, project_team_id, ethical_wall_enabled);
            CREATE INDEX IF NOT EXISTS idx_access_watermarks_file_user
                ON access_watermarks (file_id, user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_high_risk_access_file_user
                ON high_risk_access_events (file_id, user_id, action, created_at);
            CREATE INDEX IF NOT EXISTS idx_document_chunks_scope_file
                ON document_chunks (case_id, file_id);
            CREATE INDEX IF NOT EXISTS idx_embedding_vectors_scope_file
                ON local_embedding_vectors (case_id, file_id);
            CREATE INDEX IF NOT EXISTS idx_org_units_enterprise_parent
                ON organization_units (enterprise_id, parent_id, status);
            CREATE UNIQUE INDEX IF NOT EXISTS ux_org_members_user_unit
                ON organization_members (enterprise_id, user_id, unit_id);
            CREATE UNIQUE INDEX IF NOT EXISTS ux_external_org_provider
                ON external_org_integrations (enterprise_id, provider);
            CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_assistant_scope
                ON ai_assistant_settings (scope_type, scope_id);
            """
        )
        self.conn.commit()

    def close(self) -> None:
        if not self._closed:
            self.conn.close()
            self._closed = True

    def __del__(self) -> None:  # pragma: no cover - cleanup fallback
        try:
            self.close()
        except Exception:
            pass

    def login(self, account: str, password: str) -> dict[str, Any]:
        self.cleanup_expired_sessions()
        row = self.conn.execute("SELECT * FROM local_users WHERE account = ?", (account,)).fetchone()
        if not row:
            raise PermissionError("invalid local account or password")
        if row["status"] != "active":
            raise PermissionError("local account is disabled")
        if not row["password_hash"]:
            self.conn.execute("UPDATE local_users SET password_hash = ? WHERE id = ?", (hash_password(ADMIN_PASSWORD), row["id"]))
            self.conn.commit()
            row = self.conn.execute("SELECT * FROM local_users WHERE account = ?", (account,)).fetchone()
        if not verify_password(password, row["password_hash"]):
            raise PermissionError("invalid local account or password")
        token = new_id("sess") + uuid.uuid4().hex
        created_at = now()
        expires_at = created_at + SESSION_TTL_SECONDS
        self.conn.execute(
            "INSERT INTO local_sessions VALUES (?, ?, ?, ?, ?, ?)",
            (token, row["id"], row["account"], row["role"], created_at, expires_at),
        )
        self.conn.execute("UPDATE local_users SET last_login_at = ? WHERE id = ?", (created_at, row["id"]))
        self.conn.commit()
        self.audit("LOCAL_LOGIN", "user", row["id"], row["id"])
        return {
            "token": token,
            "token_type": "Bearer",
            "expires_at": expires_at,
            "user": {"id": row["id"], "account": row["account"], "name": row["name"], "role": row["role"]},
        }

    def setup_status(self) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM local_users WHERE id = ?", ("u_admin",)).fetchone()
        user_count = self.conn.execute("SELECT COUNT(*) AS count FROM local_users").fetchone()["count"]
        default_admin_password = bool(row and row["account"] == "admin" and verify_password(ADMIN_PASSWORD, row["password_hash"]))
        return {"setup_required": default_admin_password, "user_count": user_count, "default_admin_password": default_admin_password}

    def setup_admin(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.setup_status()["setup_required"]:
            raise PermissionError("admin setup is already completed")
        account = str(payload.get("account", "")).strip()
        name = str(payload.get("name", "")).strip()
        password = str(payload.get("password", ""))
        if not account or not name or not password:
            raise ValueError("account, name and password are required")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        ts = now()
        self.conn.execute(
            """
            UPDATE local_users
            SET account = ?, name = ?, role = ?, password_hash = ?, status = ?, last_login_at = NULL, created_at = ?
            WHERE id = ?
            """,
            (account, name, "agent_admin", hash_password(password), "active", ts, "u_admin"),
        )
        self.conn.execute("DELETE FROM local_sessions")
        self.conn.commit()
        self.audit("ADMIN_SETUP_COMPLETED", "user", "u_admin", "u_admin")
        return self.get_user("u_admin")

    def cleanup_expired_sessions(self) -> int:
        cursor = self.conn.execute("DELETE FROM local_sessions WHERE expires_at <= ?", (now(),))
        self.conn.commit()
        return cursor.rowcount

    def current_user(self, token: str | None) -> dict[str, Any]:
        if not token:
            raise PermissionError("missing bearer token")
        row = self.conn.execute(
            "SELECT * FROM local_sessions WHERE token = ? AND expires_at > ?",
            (token, now()),
        ).fetchone()
        if not row:
            raise PermissionError("invalid or expired bearer token")
        user = self.conn.execute("SELECT * FROM local_users WHERE id = ?", (row["user_id"],)).fetchone()
        if not user:
            raise PermissionError("session user no longer exists")
        if user["status"] != "active":
            raise PermissionError("session user is disabled")
        return {"id": user["id"], "account": user["account"], "name": user["name"], "role": user["role"]}

    def logout(self, token: str | None) -> dict[str, Any]:
        user = self.current_user(token)
        self.conn.execute("DELETE FROM local_sessions WHERE token = ?", (token,))
        self.conn.commit()
        self.audit("LOCAL_LOGOUT", "user", user["id"], user["id"])
        return {"logged_out": True}

    def list_users(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, account, name, role, status, created_at, last_login_at FROM local_users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def get_user(self, user_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT id, account, name, role, status, created_at, last_login_at FROM local_users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            raise KeyError("user not found")
        return dict(row)

    def create_user(self, payload: dict[str, Any], operator_id: str = "u_admin") -> dict[str, Any]:
        account = str(payload.get("account", "")).strip()
        name = str(payload.get("name", "")).strip()
        role = str(payload.get("role", "")).strip() or "assistant"
        password = str(payload.get("password", ""))
        if not account or not name or not password:
            raise ValueError("account, name and password are required")
        if len(password) < 6:
            raise ValueError("password must be at least 6 characters")
        if role not in {"agent_admin", "lead_lawyer", "co_lawyer", "assistant", "readonly"}:
            raise ValueError("invalid local user role")
        user_id = new_id("user")
        self.conn.execute(
            "INSERT INTO local_users (id, account, name, role, password_hash, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, account, name, role, hash_password(password), "active", now()),
        )
        self.conn.commit()
        self.audit("USER_CREATED", "user", user_id, operator_id)
        return self.get_user(user_id)

    def disable_user(self, user_id: str, operator_id: str = "u_admin") -> dict[str, Any]:
        if user_id == operator_id:
            raise ValueError("cannot disable current user")
        self.get_user(user_id)
        revoke_summary = self.revoke_user_resource_permissions(user_id)
        self.conn.execute("UPDATE local_users SET status = ? WHERE id = ?", ("disabled", user_id))
        self.conn.commit()
        self.audit("USER_PERMISSIONS_REVOKED", "user", user_id, operator_id)
        self.audit("USER_DISABLED", "user", user_id, operator_id)
        user = self.get_user(user_id)
        user["permission_revoke_summary"] = revoke_summary
        return user

    def revoke_user_resource_permissions(self, user_id: str) -> dict[str, int]:
        session_cursor = self.conn.execute("DELETE FROM local_sessions WHERE user_id = ?", (user_id,))
        case_cursor = self.conn.execute("DELETE FROM case_members WHERE user_id = ?", (user_id,))
        kb_cursor = self.conn.execute(
            "DELETE FROM knowledge_base_members WHERE principal_type = 'user' AND principal_id = ?",
            (user_id,),
        )
        acl_cursor = self.conn.execute(
            "DELETE FROM acl_entries WHERE principal_type = 'user' AND principal_id = ?",
            (user_id,),
        )
        org_cursor = self.conn.execute(
            "UPDATE organization_members SET status = 'inactive' WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        return {
            "sessions_revoked": session_cursor.rowcount,
            "case_memberships_revoked": case_cursor.rowcount,
            "knowledge_base_memberships_revoked": kb_cursor.rowcount,
            "acl_entries_revoked": acl_cursor.rowcount,
            "organization_memberships_inactivated": org_cursor.rowcount,
        }

    def reset_user_password(self, user_id: str, password: str, operator_id: str = "u_admin") -> dict[str, Any]:
        self.get_user(user_id)
        if len(password) < 6:
            raise ValueError("password must be at least 6 characters")
        self.conn.execute("UPDATE local_users SET password_hash = ?, status = ? WHERE id = ?", (hash_password(password), "active", user_id))
        self.conn.execute("DELETE FROM local_sessions WHERE user_id = ?", (user_id,))
        self.conn.commit()
        self.audit("USER_PASSWORD_RESET", "user", user_id, operator_id)
        return self.get_user(user_id)

    def audit(self, action: str, target_type: str, target_id: str | None = None, user_id: str = "u_admin") -> None:
        self.conn.execute(
            "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id("log"), user_id, action, target_type, target_id, None, None, now()),
        )
        self.conn.commit()

    def create_access_watermark(self, file: dict[str, Any], user_id: str, action: str) -> dict[str, Any]:
        user = self.get_user(user_id)
        created_at = now()
        watermark_id = new_id("wm")
        file_name = str(file.get("file_name") or "")
        watermark_text = f"{user['account']} / {user_id} / {action} / {file_name} / {created_at} / {watermark_id}"
        watermark = {
            "id": watermark_id,
            "user_id": user_id,
            "user_account": user["account"],
            "file_id": file["id"],
            "file_name": file_name,
            "action": action,
            "watermark_text": watermark_text,
            "created_at": created_at,
        }
        self.conn.execute(
            "INSERT INTO access_watermarks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                watermark["id"],
                watermark["user_id"],
                watermark["user_account"],
                watermark["file_id"],
                watermark["file_name"],
                watermark["action"],
                watermark["watermark_text"],
                watermark["created_at"],
            ),
        )
        self.conn.commit()
        return watermark

    def high_risk_file_reasons(self, file: dict[str, Any]) -> list[str]:
        reasons = []
        if file.get("is_high_sensitive"):
            reasons.append("high_sensitive")
        if file.get("confidentiality_level") == "restricted":
            reasons.append("restricted_confidentiality")
        if not file.get("ai_enabled", True) or file.get("ai_usage_policy") == "disabled" or file.get("review_status") == "ai_disabled":
            reasons.append("ai_disabled")
        return reasons

    def record_high_risk_file_access(self, file: dict[str, Any], user_id: str, action: str) -> dict[str, Any] | None:
        reasons = self.high_risk_file_reasons(file)
        if not reasons:
            return None
        event_id = new_id("risk")
        event = {
            "id": event_id,
            "user_id": user_id,
            "file_id": file["id"],
            "file_name": file.get("file_name") or "",
            "action": action,
            "risk_reasons": reasons,
            "created_at": now(),
        }
        self.conn.execute(
            "INSERT INTO high_risk_access_events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, user_id, event["file_id"], event["file_name"], action, json.dumps(reasons, ensure_ascii=False), event["created_at"]),
        )
        self.conn.commit()
        audit_action = "HIGH_RISK_FILE_PREVIEWED" if action == "preview" else "HIGH_RISK_FILE_AI_QUERIED"
        self.audit(audit_action, "file", event["file_id"], user_id)
        return event

    def set_config(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO agent_config VALUES (?, ?)", (key, value))
        self.conn.commit()

    def get_config(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM agent_config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def ensure_enterprise_profile(self) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM enterprise_profiles ORDER BY created_at ASC LIMIT 1").fetchone()
        if row:
            return dict(row)
        ts = now()
        enterprise_id = "ent_local"
        self.conn.execute(
            "INSERT INTO enterprise_profiles VALUES (?, ?, ?, ?, ?, ?)",
            (enterprise_id, "本地律所", "manual", "active", ts, ts),
        )
        self.conn.commit()
        return dict(self.conn.execute("SELECT * FROM enterprise_profiles WHERE id = ?", (enterprise_id,)).fetchone())

    def enterprise_overview(self) -> dict[str, Any]:
        enterprise = self.ensure_enterprise_profile()
        enterprise_id = enterprise["id"]
        user_count = self.conn.execute("SELECT COUNT(*) AS count FROM local_users WHERE status = 'active'").fetchone()["count"]
        admin_count = self.conn.execute("SELECT COUNT(*) AS count FROM local_users WHERE status = 'active' AND role = 'agent_admin'").fetchone()["count"]
        unit_count = self.conn.execute("SELECT COUNT(*) AS count FROM organization_units WHERE enterprise_id = ? AND status = 'active'", (enterprise_id,)).fetchone()["count"]
        knowledge_row = self.conn.execute("SELECT COUNT(*) AS count FROM knowledge_bases WHERE status = 'active'").fetchone()
        file_row = self.conn.execute("SELECT COUNT(*) AS count FROM local_files WHERE deleted_at IS NULL").fetchone()
        folder_row = self.conn.execute("SELECT COUNT(*) AS count FROM folders WHERE deleted_at IS NULL").fetchone()
        kb_review_rows = self.conn.execute("SELECT review_status, COUNT(*) AS count FROM knowledge_bases WHERE status = 'active' GROUP BY review_status").fetchall()
        kb_type_rows = self.conn.execute("SELECT knowledge_type, COUNT(*) AS count FROM knowledge_bases WHERE status = 'active' GROUP BY knowledge_type").fetchall()
        file_review_rows = self.conn.execute("SELECT review_status, COUNT(*) AS count FROM local_files WHERE deleted_at IS NULL GROUP BY review_status").fetchall()
        ai_feedback_total = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback").fetchone()["count"]
        ai_feedback_negative = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback WHERE rating = 'down'").fetchone()["count"]
        ai_feedback_open = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback WHERE status = 'open'").fetchone()["count"]
        ai_feedback_resolved = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback WHERE status = 'resolved'").fetchone()["count"]
        ai_feedback_ignored = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback WHERE status = 'ignored'").fetchone()["count"]
        ai_feedback_issue_rows = self.conn.execute("SELECT COALESCE(issue_label, 'unknown') AS issue_label, COUNT(*) AS count FROM ai_assistant_feedback GROUP BY COALESCE(issue_label, 'unknown')").fetchall()
        ai_feedback_citation_missing_count = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback WHERE issue_label = 'citation_missing'").fetchone()["count"]
        ai_feedback_insufficient_evidence_count = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback WHERE issue_label = 'insufficient_evidence'").fetchone()["count"]
        ai_feedback_answer_inaccurate_count = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback WHERE issue_label = 'answer_inaccurate'").fetchone()["count"]
        ai_feedback_permission_anomaly_count = self.conn.execute("SELECT COUNT(*) AS count FROM ai_assistant_feedback WHERE issue_label = 'permission_anomaly'").fetchone()["count"]
        ai_question_count = self.conn.execute("SELECT COUNT(*) AS count FROM audit_logs WHERE action IN ('CHAT_ASKED', 'CHAT_ASKED_NO_CITATION')").fetchone()["count"]
        ai_insufficient_count = self.conn.execute("SELECT COUNT(*) AS count FROM audit_logs WHERE action = 'CHAT_ASKED_NO_CITATION'").fetchone()["count"]
        timestamp = now()
        kb_expired_count = self.conn.execute("SELECT COUNT(*) AS count FROM knowledge_bases WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?", (timestamp,)).fetchone()["count"]
        file_expired_count = self.conn.execute("SELECT COUNT(*) AS count FROM local_files WHERE deleted_at IS NULL AND expires_at IS NOT NULL AND expires_at <= ?", (timestamp,)).fetchone()["count"]
        kb_ai_disabled_count = self.conn.execute("SELECT COUNT(*) AS count FROM knowledge_bases WHERE status = 'active' AND (ai_enabled = 0 OR ai_usage_policy = 'disabled' OR review_status = 'ai_disabled')").fetchone()["count"]
        file_ai_disabled_count = self.conn.execute("SELECT COUNT(*) AS count FROM local_files WHERE deleted_at IS NULL AND (ai_enabled = 0 OR ai_usage_policy = 'disabled' OR review_status = 'ai_disabled')").fetchone()["count"]
        high_sensitive_file_count = self.conn.execute("SELECT COUNT(*) AS count FROM local_files WHERE deleted_at IS NULL AND is_high_sensitive = 1").fetchone()["count"]
        high_risk_access_count = self.conn.execute("SELECT COUNT(*) AS count FROM high_risk_access_events").fetchone()["count"]
        high_risk_access_action_rows = self.conn.execute("SELECT action, COUNT(*) AS count FROM high_risk_access_events GROUP BY action").fetchall()
        temporary_acl_active_count = self.conn.execute("SELECT COUNT(*) AS count FROM acl_entries WHERE expires_at IS NOT NULL AND expires_at > ?", (timestamp,)).fetchone()["count"]
        temporary_acl_expired_count = self.conn.execute("SELECT COUNT(*) AS count FROM acl_entries WHERE expires_at IS NOT NULL AND expires_at <= ?", (timestamp,)).fetchone()["count"]
        kb_search_only_count = self.conn.execute("SELECT COUNT(*) AS count FROM knowledge_bases WHERE status = 'active' AND ai_usage_policy = 'search_only'").fetchone()["count"]
        file_search_only_count = self.conn.execute("SELECT COUNT(*) AS count FROM local_files WHERE deleted_at IS NULL AND ai_usage_policy = 'search_only'").fetchone()["count"]
        low_usage_threshold = timestamp - 30 * 86400
        low_usage_rows = self.conn.execute(
            """
            SELECT kb.id, kb.name, kb.knowledge_type, kb.maintainer_id, COUNT(al.id) AS ai_question_count
            FROM knowledge_bases kb
            LEFT JOIN audit_logs al ON al.target_type = 'knowledge_base' AND al.target_id = kb.id AND al.action IN ('CHAT_ASKED', 'CHAT_ASKED_NO_CITATION') AND al.created_at >= ?
            WHERE kb.status = 'active'
            GROUP BY kb.id
            HAVING ai_question_count = 0
            ORDER BY kb.updated_at ASC
            LIMIT 10
            """,
            (low_usage_threshold,),
        ).fetchall()
        high_risk_rows = self.conn.execute(
            """
            SELECT file_id, file_name, COUNT(*) AS access_count, MAX(created_at) AS last_access_at
            FROM high_risk_access_events
            GROUP BY file_id, file_name
            ORDER BY access_count DESC, last_access_at DESC
            LIMIT 10
            """
        ).fetchall()
        ai_user_rows = self.conn.execute(
            """
            SELECT COALESCE(u.id, al.user_id, 'unknown') AS user_id, COALESCE(u.name, al.user_id, 'unknown') AS user_name, COUNT(*) AS ai_question_count
            FROM audit_logs al
            LEFT JOIN local_users u ON u.id = al.user_id
            WHERE al.action IN ('CHAT_ASKED', 'CHAT_ASKED_NO_CITATION')
            GROUP BY COALESCE(u.id, al.user_id, 'unknown')
            ORDER BY ai_question_count DESC
            LIMIT 10
            """
        ).fetchall()
        trust_counts = Counter(KNOWLEDGE_TRUST_LEVELS.get(row["knowledge_type"], "general") for row in kb_type_rows for _ in range(int(row["count"] or 0)))
        sync_row = self.conn.execute(
            "SELECT MAX(last_sync_at) AS last_sync_at FROM external_org_integrations WHERE enterprise_id = ?",
            (enterprise_id,),
        ).fetchone()
        permission_anomalies = self.detect_permission_anomalies()
        permission_anomaly_type_counts = Counter(item["type"] for item in permission_anomalies)
        knowledge_quality_rows = self.conn.execute(
            """
            WITH file_stats AS (
                SELECT
                    knowledge_base_id,
                    COUNT(*) AS file_count,
                    SUM(CASE WHEN expires_at IS NOT NULL AND expires_at <= ? THEN 1 ELSE 0 END) AS expired_file_count,
                    SUM(CASE WHEN is_high_sensitive = 1 THEN 1 ELSE 0 END) AS high_sensitive_file_count,
                    SUM(CASE WHEN ai_enabled = 0 OR ai_usage_policy = 'disabled' OR review_status = 'ai_disabled' THEN 1 ELSE 0 END) AS ai_disabled_file_count
                FROM local_files
                WHERE deleted_at IS NULL
                GROUP BY knowledge_base_id
            ), audit_stats AS (
                SELECT
                    target_id AS knowledge_base_id,
                    COUNT(*) AS ai_question_count,
                    SUM(CASE WHEN action = 'CHAT_ASKED_NO_CITATION' THEN 1 ELSE 0 END) AS insufficient_evidence_count
                FROM audit_logs
                WHERE target_type = 'knowledge_base' AND action IN ('CHAT_ASKED', 'CHAT_ASKED_NO_CITATION')
                GROUP BY target_id
            ), feedback_stats AS (
                SELECT
                    cs.case_id AS knowledge_base_id,
                    SUM(CASE WHEN fb.rating = 'down' THEN 1 ELSE 0 END) AS negative_feedback_count
                FROM chat_sessions cs
                JOIN ai_assistant_feedback fb ON fb.session_id = cs.id
                GROUP BY cs.case_id
            )
            SELECT
                kb.id,
                kb.name,
                kb.knowledge_type,
                kb.review_status,
                kb.maintainer_id,
                COALESCE(fs.file_count, 0) AS file_count,
                COALESCE(fs.expired_file_count, 0) AS expired_file_count,
                COALESCE(fs.high_sensitive_file_count, 0) AS high_sensitive_file_count,
                COALESCE(fs.ai_disabled_file_count, 0) AS ai_disabled_file_count,
                COALESCE(aus.ai_question_count, 0) AS ai_question_count,
                COALESCE(aus.insufficient_evidence_count, 0) AS insufficient_evidence_count,
                COALESCE(fbs.negative_feedback_count, 0) AS negative_feedback_count
            FROM knowledge_bases kb
            LEFT JOIN file_stats fs ON fs.knowledge_base_id = kb.id
            LEFT JOIN audit_stats aus ON aus.knowledge_base_id = kb.id
            LEFT JOIN feedback_stats fbs ON fbs.knowledge_base_id = kb.id
            WHERE kb.status = 'active'
            ORDER BY insufficient_evidence_count DESC, negative_feedback_count DESC, expired_file_count DESC, file_count DESC, kb.updated_at DESC
            LIMIT 10
            """,
            (timestamp,),
        ).fetchall()
        contributor_rows = self.conn.execute(
            """
            SELECT
                COALESCE(kb.maintainer_id, kb.created_by, 'unknown') AS maintainer_id,
                COALESCE(u.name, COALESCE(kb.maintainer_id, kb.created_by, 'unknown')) AS maintainer_name,
                COUNT(DISTINCT kb.id) AS knowledge_base_count,
                COUNT(DISTINCT f.id) AS file_count,
                SUM(CASE WHEN kb.review_status IN ('published', 'needs_update') THEN 1 ELSE 0 END) AS publish_ready_count,
                SUM(CASE WHEN kb.expires_at IS NOT NULL AND kb.expires_at <= ? THEN 1 ELSE 0 END) AS expired_knowledge_base_count
            FROM knowledge_bases kb
            LEFT JOIN local_users u ON u.id = COALESCE(kb.maintainer_id, kb.created_by)
            LEFT JOIN local_files f ON f.knowledge_base_id = kb.id AND f.deleted_at IS NULL
            WHERE kb.status = 'active'
            GROUP BY COALESCE(kb.maintainer_id, kb.created_by, 'unknown')
            ORDER BY knowledge_base_count DESC, file_count DESC
            LIMIT 10
            """,
            (timestamp,),
        ).fetchall()
        knowledge_quality_top = []
        for row in knowledge_quality_rows:
            questions = int(row["ai_question_count"] or 0)
            insufficient = int(row["insufficient_evidence_count"] or 0)
            knowledge_quality_top.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "knowledge_type": row["knowledge_type"],
                    "review_status": row["review_status"],
                    "maintainer_id": row["maintainer_id"],
                    "file_count": int(row["file_count"] or 0),
                    "expired_file_count": int(row["expired_file_count"] or 0),
                    "high_sensitive_file_count": int(row["high_sensitive_file_count"] or 0),
                    "ai_disabled_file_count": int(row["ai_disabled_file_count"] or 0),
                    "ai_question_count": questions,
                    "insufficient_evidence_count": insufficient,
                    "insufficient_evidence_rate": round(insufficient / questions, 4) if questions else 0,
                    "negative_feedback_count": int(row["negative_feedback_count"] or 0),
                }
            )
        return {
            "enterprise": enterprise,
            "member_count": user_count,
            "admin_count": admin_count,
            "department_count": unit_count,
            "external_collaborator_count": 0,
            "active_knowledge_base_count": knowledge_row["count"],
            "file_count": file_row["count"],
            "folder_count": folder_row["count"],
            "last_sync_at": sync_row["last_sync_at"] if sync_row else None,
            "stats_until": timestamp,
            "knowledge_review_status_counts": {row["review_status"]: row["count"] for row in kb_review_rows},
            "knowledge_type_counts": {row["knowledge_type"]: row["count"] for row in kb_type_rows},
            "knowledge_ai_disabled_count": kb_ai_disabled_count,
            "knowledge_search_only_count": kb_search_only_count,
            "knowledge_expired_count": kb_expired_count,
            "file_review_status_counts": {row["review_status"]: row["count"] for row in file_review_rows},
            "file_ai_disabled_count": file_ai_disabled_count,
            "high_sensitive_file_count": high_sensitive_file_count,
            "high_risk_access_count": high_risk_access_count,
            "high_risk_access_action_counts": {row["action"]: row["count"] for row in high_risk_access_action_rows},
            "permission_anomaly_count": len(permission_anomalies),
            "permission_anomaly_type_counts": dict(permission_anomaly_type_counts),
            "permission_anomaly_samples": permission_anomalies[:10],
            "temporary_acl_active_count": temporary_acl_active_count,
            "temporary_acl_expired_count": temporary_acl_expired_count,
            "file_search_only_count": file_search_only_count,
            "file_expired_count": file_expired_count,
            "knowledge_trust_level_counts": dict(trust_counts),
            "low_usage_knowledge_top": [dict(row) for row in low_usage_rows],
            "high_risk_file_access_top": [dict(row) for row in high_risk_rows],
            "ai_user_top": [dict(row) for row in ai_user_rows],
            "estimated_time_saved_minutes": ai_question_count * 12,
            "ai_feedback_total_count": ai_feedback_total,
            "ai_feedback_negative_count": ai_feedback_negative,
            "ai_feedback_open_count": ai_feedback_open,
            "ai_feedback_resolved_count": ai_feedback_resolved,
            "ai_feedback_ignored_count": ai_feedback_ignored,
            "ai_feedback_issue_counts": {row["issue_label"]: row["count"] for row in ai_feedback_issue_rows},
            "ai_feedback_citation_missing_count": ai_feedback_citation_missing_count,
            "ai_feedback_insufficient_evidence_count": ai_feedback_insufficient_evidence_count,
            "ai_feedback_answer_inaccurate_count": ai_feedback_answer_inaccurate_count,
            "ai_feedback_permission_anomaly_count": ai_feedback_permission_anomaly_count,
            "ai_question_count": ai_question_count,
            "ai_insufficient_evidence_count": ai_insufficient_count,
            "ai_insufficient_evidence_rate": round(ai_insufficient_count / ai_question_count, 4) if ai_question_count else 0,
            "knowledge_quality_top": knowledge_quality_top,
            "knowledge_contributor_top": [dict(row) for row in contributor_rows],
        }

    def detect_permission_anomalies(self) -> list[dict[str, Any]]:
        timestamp = now()
        anomalies: list[dict[str, Any]] = []
        disabled_case_members = self.conn.execute(
            """
            SELECT cm.id AS resource_id, cm.user_id, u.account, cm.case_id AS scope_id
            FROM case_members cm
            JOIN local_users u ON u.id = cm.user_id
            WHERE u.status != 'active'
            """
        ).fetchall()
        for row in disabled_case_members:
            anomalies.append({"type": "disabled_user_case_member", "resource_type": "case_member", **dict(row)})

        disabled_kb_members = self.conn.execute(
            """
            SELECT kbm.id AS resource_id, kbm.principal_id AS user_id, u.account, kbm.knowledge_base_id AS scope_id
            FROM knowledge_base_members kbm
            JOIN local_users u ON u.id = kbm.principal_id
            WHERE kbm.principal_type = 'user' AND u.status != 'active'
            """
        ).fetchall()
        for row in disabled_kb_members:
            anomalies.append({"type": "disabled_user_knowledge_base_member", "resource_type": "knowledge_base_member", **dict(row)})

        disabled_acl_entries = self.conn.execute(
            """
            SELECT acl.id AS resource_id, acl.principal_id AS user_id, u.account, acl.resource_type AS scope_type, acl.resource_id AS scope_id
            FROM acl_entries acl
            JOIN local_users u ON u.id = acl.principal_id
            WHERE acl.principal_type = 'user' AND u.status != 'active'
            """
        ).fetchall()
        for row in disabled_acl_entries:
            anomalies.append({"type": "disabled_user_acl_entry", **dict(row)})

        disabled_org_members = self.conn.execute(
            """
            SELECT om.id AS resource_id, om.user_id, u.account, om.unit_id AS scope_id
            FROM organization_members om
            JOIN local_users u ON u.id = om.user_id
            WHERE om.status = 'active' AND u.status != 'active'
            """
        ).fetchall()
        for row in disabled_org_members:
            anomalies.append({"type": "disabled_user_organization_member", "resource_type": "organization_member", **dict(row)})

        expired_ai_kbs = self.conn.execute(
            """
            SELECT id AS resource_id, name, expires_at
            FROM knowledge_bases
            WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?
              AND ai_enabled = 1 AND ai_usage_policy = 'allow_generation' AND review_status != 'ai_disabled'
            """,
            (timestamp,),
        ).fetchall()
        for row in expired_ai_kbs:
            anomalies.append({"type": "expired_knowledge_base_ai_generation_enabled", "resource_type": "knowledge_base", **dict(row)})

        expired_ai_files = self.conn.execute(
            """
            SELECT id AS resource_id, file_name, expires_at
            FROM local_files
            WHERE deleted_at IS NULL AND expires_at IS NOT NULL AND expires_at <= ?
              AND ai_enabled = 1 AND ai_usage_policy = 'allow_generation' AND review_status != 'ai_disabled'
            """,
            (timestamp,),
        ).fetchall()
        for row in expired_ai_files:
            anomalies.append({"type": "expired_file_ai_generation_enabled", "resource_type": "file", **dict(row)})

        high_sensitive_ai_files = self.conn.execute(
            """
            SELECT id AS resource_id, file_name
            FROM local_files
            WHERE deleted_at IS NULL AND is_high_sensitive = 1
              AND (ai_enabled = 1 OR ai_usage_policy != 'disabled')
            """
        ).fetchall()
        for row in high_sensitive_ai_files:
            anomalies.append({"type": "high_sensitive_file_ai_not_disabled", "resource_type": "file", **dict(row)})
        return anomalies

    def save_enterprise_profile(self, payload: dict[str, Any], operator_id: str) -> dict[str, Any]:
        current = self.ensure_enterprise_profile()
        name = str(payload.get("name", current["name"])).strip()
        if not name:
            raise ValueError("enterprise name is required")
        source_type = str(payload.get("source_type", current["source_type"]))
        if source_type not in {"manual", "wecom", "dingtalk", "feishu", "mixed"}:
            raise ValueError("invalid enterprise source_type")
        ts = now()
        self.conn.execute(
            "UPDATE enterprise_profiles SET name = ?, source_type = ?, updated_at = ? WHERE id = ?",
            (name, source_type, ts, current["id"]),
        )
        self.conn.commit()
        self.audit("ENTERPRISE_PROFILE_SAVED", "enterprise", current["id"], operator_id)
        return dict(self.conn.execute("SELECT * FROM enterprise_profiles WHERE id = ?", (current["id"],)).fetchone())

    def list_organization_units(self) -> list[dict[str, Any]]:
        enterprise = self.ensure_enterprise_profile()
        rows = self.conn.execute(
            "SELECT * FROM organization_units WHERE enterprise_id = ? AND status = 'active' ORDER BY sort_order, created_at",
            (enterprise["id"],),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_organization_unit(self, payload: dict[str, Any], operator_id: str) -> dict[str, Any]:
        enterprise = self.ensure_enterprise_profile()
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("organization unit name is required")
        unit_type = str(payload.get("unit_type", "department"))
        if unit_type not in {"enterprise", "department", "team", "practice_group", "client", "matter", "project_team"}:
            raise ValueError("invalid organization unit type")
        parent_id = payload.get("parent_id")
        if parent_id:
            parent = self.conn.execute("SELECT * FROM organization_units WHERE id = ? AND enterprise_id = ?", (parent_id, enterprise["id"])).fetchone()
            if not parent:
                raise KeyError("parent organization unit not found")
            parent = dict(parent)
            if unit_type == "matter" and parent.get("unit_type") != "client":
                raise ValueError("matter organization unit must belong to a client unit")
            if unit_type == "project_team" and parent.get("unit_type") != "matter":
                raise ValueError("project_team organization unit must belong to a matter unit")
        if unit_type in {"matter", "project_team"} and not parent_id:
            raise ValueError(f"{unit_type} organization unit requires parent_id")
        unit_id = new_id("org")
        ts = now()
        self.conn.execute(
            """
            INSERT INTO organization_units
            (id, enterprise_id, parent_id, name, unit_type, source_type, external_id, sort_order, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (unit_id, enterprise["id"], parent_id, name, unit_type, str(payload.get("source_type", "manual")), payload.get("external_id"), int(payload.get("sort_order", 0)), "active", ts, ts),
        )
        self.conn.commit()
        self.audit("ORGANIZATION_UNIT_CREATED", "organization_unit", unit_id, operator_id)
        return dict(self.conn.execute("SELECT * FROM organization_units WHERE id = ?", (unit_id,)).fetchone())

    def require_organization_unit(self, unit_id: str, allowed_types: set[str] | None = None) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM organization_units WHERE id = ? AND status = 'active'", (unit_id,)).fetchone()
        if not row:
            raise KeyError("organization unit not found")
        unit = dict(row)
        if allowed_types and unit.get("unit_type") not in allowed_types:
            raise ValueError("organization unit type does not match boundary field")
        return unit

    def user_in_organization_unit(self, user_id: str, unit_id: str | None) -> bool:
        if not unit_id:
            return False
        row = self.conn.execute(
            "SELECT 1 FROM organization_members WHERE user_id = ? AND unit_id = ? AND status = 'active' LIMIT 1",
            (user_id, unit_id),
        ).fetchone()
        return bool(row)

    def organization_unit_exists(self, unit_id: str | None) -> bool:
        if not unit_id:
            return False
        row = self.conn.execute("SELECT 1 FROM organization_units WHERE id = ? AND status = 'active' LIMIT 1", (unit_id,)).fetchone()
        return bool(row)

    def list_organization_members(self) -> list[dict[str, Any]]:
        enterprise = self.ensure_enterprise_profile()
        rows = self.conn.execute(
            """
            SELECT om.*, u.account, u.name, u.role, u.status AS user_status, ou.name AS unit_name
            FROM organization_members om
            JOIN local_users u ON u.id = om.user_id
            LEFT JOIN organization_units ou ON ou.id = om.unit_id
            WHERE om.enterprise_id = ? AND om.status = 'active'
            ORDER BY om.joined_at DESC
            """,
            (enterprise["id"],),
        ).fetchall()
        return [dict(row) for row in rows]

    def assign_organization_member(self, payload: dict[str, Any], operator_id: str) -> dict[str, Any]:
        enterprise = self.ensure_enterprise_profile()
        user_id = str(payload.get("user_id", ""))
        self.get_user(user_id)
        unit_id = payload.get("unit_id")
        if unit_id:
            unit = self.conn.execute("SELECT id FROM organization_units WHERE id = ? AND enterprise_id = ?", (unit_id, enterprise["id"])).fetchone()
            if not unit:
                raise KeyError("organization unit not found")
        existing = self.conn.execute(
            "SELECT id FROM organization_members WHERE enterprise_id = ? AND user_id = ? AND IFNULL(unit_id, '') = IFNULL(?, '')",
            (enterprise["id"], user_id, unit_id),
        ).fetchone()
        member_id = existing["id"] if existing else new_id("orgm")
        if existing:
            self.conn.execute(
                "UPDATE organization_members SET position = ?, source_type = ?, external_user_id = ?, status = ? WHERE id = ?",
                (payload.get("position"), str(payload.get("source_type", "manual")), payload.get("external_user_id"), "active", member_id),
            )
        else:
            self.conn.execute(
                "INSERT INTO organization_members VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (member_id, enterprise["id"], unit_id, user_id, payload.get("position"), str(payload.get("source_type", "manual")), payload.get("external_user_id"), "active", now()),
            )
        self.conn.commit()
        self.audit("ORGANIZATION_MEMBER_ASSIGNED", "organization_member", member_id, operator_id)
        return next(row for row in self.list_organization_members() if row["id"] == member_id)

    def list_external_org_integrations(self) -> list[dict[str, Any]]:
        enterprise = self.ensure_enterprise_profile()
        rows = self.conn.execute("SELECT * FROM external_org_integrations WHERE enterprise_id = ? ORDER BY updated_at DESC", (enterprise["id"],)).fetchall()
        results = []
        for row in rows:
            data = dict(row)
            data.pop("secret_encrypted", None)
            data["secret_configured"] = bool(row["secret_encrypted"])
            data["sync_enabled"] = bool(data["sync_enabled"])
            results.append(data)
        return results

    def save_external_org_integration(self, payload: dict[str, Any], operator_id: str) -> dict[str, Any]:
        enterprise = self.ensure_enterprise_profile()
        provider = str(payload.get("provider", ""))
        if provider not in {"wecom", "dingtalk", "feishu"}:
            raise ValueError("provider must be wecom, dingtalk or feishu")
        existing = self.conn.execute("SELECT * FROM external_org_integrations WHERE enterprise_id = ? AND provider = ?", (enterprise["id"], provider)).fetchone()
        ts = now()
        integration_id = existing["id"] if existing else new_id("orgint")
        secret_encrypted = existing["secret_encrypted"] if existing else None
        if payload.get("secret"):
            secret_encrypted = encrypt_secret(str(payload["secret"]))
        fields = (
            integration_id,
            enterprise["id"],
            provider,
            payload.get("corp_id"),
            payload.get("agent_id"),
            payload.get("app_key"),
            payload.get("app_id"),
            secret_encrypted,
            payload.get("callback_url"),
            1 if payload.get("sync_enabled") else 0,
            existing["last_sync_at"] if existing else None,
            "configured" if payload.get("sync_enabled") else "disabled",
            existing["created_at"] if existing else ts,
            ts,
        )
        self.conn.execute("INSERT OR REPLACE INTO external_org_integrations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", fields)
        self.conn.commit()
        self.audit("EXTERNAL_ORG_INTEGRATION_SAVED", "external_org_integration", integration_id, operator_id)
        return next(item for item in self.list_external_org_integrations() if item["id"] == integration_id)

    def simulate_external_org_sync(self, provider: str, operator_id: str) -> dict[str, Any]:
        enterprise = self.ensure_enterprise_profile()
        row = self.conn.execute("SELECT * FROM external_org_integrations WHERE enterprise_id = ? AND provider = ?", (enterprise["id"], provider)).fetchone()
        if not row:
            raise KeyError("external organization integration not found")
        ts = now()
        status = "pending_credentials" if not row["secret_encrypted"] else "synced"
        self.conn.execute("UPDATE external_org_integrations SET last_sync_at = ?, sync_status = ?, updated_at = ? WHERE id = ?", (ts, status, ts, row["id"]))
        self.conn.commit()
        self.audit("EXTERNAL_ORG_SYNC_TRIGGERED", "external_org_integration", row["id"], operator_id)
        return {"provider": provider, "sync_status": status, "last_sync_at": ts}

    def get_ai_assistant_setting(self, scope_type: str = "enterprise", scope_id: str | None = None) -> dict[str, Any]:
        enterprise = self.ensure_enterprise_profile()
        actual_scope_id = scope_id or enterprise["id"]
        row = self.conn.execute("SELECT * FROM ai_assistant_settings WHERE scope_type = ? AND scope_id = ?", (scope_type, actual_scope_id)).fetchone()
        if not row:
            return {
                "id": None,
                "scope_type": scope_type,
                "scope_id": actual_scope_id,
                "name": "律所知识库助手",
                "system_prompt": "你是律师知识库助手，回答必须基于授权知识库材料，并提示证据不足。",
                "enabled": True,
                "allowed_knowledge_base_ids": [],
                "updated_by": None,
                "updated_at": None,
            }
        data = dict(row)
        data["enabled"] = bool(data["enabled"])
        data["allowed_knowledge_base_ids"] = json.loads(data.get("allowed_knowledge_base_ids") or "[]")
        return data

    def save_ai_assistant_setting(self, payload: dict[str, Any], operator_id: str) -> dict[str, Any]:
        enterprise = self.ensure_enterprise_profile()
        scope_type = str(payload.get("scope_type", "enterprise"))
        scope_id = str(payload.get("scope_id", enterprise["id"]))
        if scope_type not in {"enterprise", "department", "knowledge_base", "user"}:
            raise ValueError("invalid assistant scope_type")
        name = str(payload.get("name", "律所知识库助手")).strip()
        if not name:
            raise ValueError("assistant name is required")
        setting_id = str(payload.get("id") or new_id("asst"))
        allowed_ids = json.dumps(payload.get("allowed_knowledge_base_ids", []), ensure_ascii=False)
        ts = now()
        self.conn.execute(
            "INSERT OR REPLACE INTO ai_assistant_settings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (setting_id, scope_type, scope_id, name, payload.get("system_prompt"), 1 if payload.get("enabled", True) else 0, allowed_ids, operator_id, ts),
        )
        self.conn.commit()
        self.audit("AI_ASSISTANT_SETTING_SAVED", "ai_assistant_setting", setting_id, operator_id)
        return self.get_ai_assistant_setting(scope_type, scope_id)

    def create_ai_assistant_feedback(self, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        rating = str(payload.get("rating", ""))
        if rating not in {"up", "down", "neutral"}:
            raise ValueError("feedback rating must be up, down or neutral")
        issue_label = self.normalize_ai_feedback_issue_label(payload.get("issue_label"), rating)
        session_id = payload.get("session_id")
        message_id = payload.get("message_id")
        if session_id:
            session = self.conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            if not session:
                raise KeyError("feedback chat session not found")
            self.require_chat_scope_access(str(session["case_id"]), user_id)
        if message_id:
            message = self.conn.execute("SELECT * FROM chat_messages WHERE id = ?", (message_id,)).fetchone()
            if not message:
                raise KeyError("feedback chat message not found")
            if session_id and message["session_id"] != session_id:
                raise ValueError("feedback message does not belong to session")
            if message["role"] != "assistant":
                raise ValueError("feedback message must be an assistant answer")
            if not session_id:
                message_session = self.conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (message["session_id"],)).fetchone()
                if not message_session:
                    raise KeyError("feedback chat session not found")
                self.require_chat_scope_access(str(message_session["case_id"]), user_id)
                session_id = message["session_id"]
        feedback_id = new_id("fb")
        self.conn.execute(
            """
            INSERT INTO ai_assistant_feedback
            (id, session_id, message_id, user_id, rating, comment, issue_label, status, handler_id, handled_at, resolution_comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (feedback_id, session_id, message_id, user_id, rating, payload.get("comment"), issue_label, "open", None, None, None, now()),
        )
        self.conn.commit()
        self.audit("AI_ASSISTANT_FEEDBACK_CREATED", "ai_assistant_feedback", feedback_id, user_id)
        return dict(self.conn.execute("SELECT * FROM ai_assistant_feedback WHERE id = ?", (feedback_id,)).fetchone())

    def handle_ai_assistant_feedback(self, feedback_id: str, payload: dict[str, Any], operator_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM ai_assistant_feedback WHERE id = ?", (feedback_id,)).fetchone()
        if not row:
            raise KeyError("AI assistant feedback not found")
        status = str(payload.get("status", "resolved"))
        if status not in {"open", "resolved", "ignored"}:
            raise ValueError("feedback status must be open, resolved or ignored")
        handled_at = None if status == "open" else now()
        handler_id = None if status == "open" else operator_id
        self.conn.execute(
            "UPDATE ai_assistant_feedback SET status = ?, handler_id = ?, handled_at = ?, resolution_comment = ? WHERE id = ?",
            (status, handler_id, handled_at, payload.get("resolution_comment"), feedback_id),
        )
        self.conn.commit()
        self.audit("AI_ASSISTANT_FEEDBACK_HANDLED", "ai_assistant_feedback", feedback_id, operator_id)
        return dict(self.conn.execute("SELECT * FROM ai_assistant_feedback WHERE id = ?", (feedback_id,)).fetchone())

    def list_ai_assistant_feedback(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM ai_assistant_feedback ORDER BY created_at DESC LIMIT 200").fetchall()
        return [dict(row) for row in rows]

    def normalize_ai_feedback_issue_label(self, value: Any, rating: str) -> str | None:
        if rating != "down" and value in (None, ""):
            return None
        label = str(value or "other").strip()
        label = AI_FEEDBACK_ISSUE_ALIASES.get(label, label)
        if label not in AI_FEEDBACK_ISSUE_LABELS:
            raise ValueError("invalid feedback issue_label")
        return label

    def add_data_source(self, path: str) -> dict[str, Any]:
        p = Path(path).expanduser().resolve()
        validate_local_data_path(p)
        check = self.check_directory_permission(str(p))
        if not check["exists"]:
            raise ValueError("data source path does not exist")
        if not check["is_dir"]:
            raise ValueError("data source path is not a directory")
        if not check["readable"]:
            raise PermissionError("data source directory is not readable")
        permission = check["permission_status"]
        ds_id = new_id("ds")
        self.conn.execute("INSERT INTO local_data_sources VALUES (?, ?, ?, ?, ?, ?)", (ds_id, "local_directory", str(p), "active", permission, now()))
        self.conn.commit()
        self.audit("DATA_SOURCE_CREATED", "data_source", ds_id)
        return {"id": ds_id, "type": "local_directory", "path": str(p), "status": "active", "permission_status": permission, "created_at": now()}

    def check_directory_permission(self, path: str) -> dict[str, Any]:
        p = Path(path).expanduser().resolve()
        exists = p.exists()
        is_dir = p.is_dir()
        readable = exists and is_dir and os.access(p, os.R_OK)
        writable = exists and is_dir and os.access(p, os.W_OK)
        if readable and writable:
            permission = "readable_writable"
        elif readable:
            permission = "readable"
        else:
            permission = "denied"
        return {"path": str(p), "exists": exists, "is_dir": is_dir, "readable": readable, "writable": writable, "permission_status": permission}

    def list_data_sources(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM local_data_sources ORDER BY created_at DESC").fetchall()]

    def get_data_source(self, data_source_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM local_data_sources WHERE id = ?", (data_source_id,)).fetchone()
        if not row:
            raise KeyError("data source not found")
        return dict(row)

    def ensure_case_knowledge_bases(self) -> None:
        cases = self.conn.execute("SELECT * FROM case_spaces").fetchall()
        for row in cases:
            self.ensure_case_knowledge_base(dict(row))

    def ensure_default_knowledge_bases(self) -> None:
        admin = self.conn.execute("SELECT * FROM local_users WHERE id = ?", ("u_admin",)).fetchone()
        if not admin:
            return
        user_id = admin["id"]
        ts = now()
        for item in DEFAULT_KNOWLEDGE_BASES:
            existing = self.conn.execute(
                "SELECT id FROM knowledge_bases WHERE type = ? AND name = ? AND status = 'active' LIMIT 1",
                (item["type"], item["name"]),
            ).fetchone()
            if existing:
                self.upsert_knowledge_base_member(existing["id"], "user", user_id, "admin", "system")
                continue
            kb_id = new_id("kb")
            self.conn.execute(
                """
                INSERT INTO knowledge_bases
                (id, type, name, description, owner_type, owner_id, knowledge_type, review_status, confidentiality_level, maintainer_id, ai_usage_policy, citation_priority, ai_enabled, default_permission_policy, status, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kb_id,
                    item["type"],
                    item["name"],
                    item["description"],
                    "user" if item["type"] == "private" else "team",
                    user_id,
                    item["knowledge_type"],
                    item["review_status"],
                    item["confidentiality_level"],
                    user_id,
                    item["ai_usage_policy"],
                    0,
                    1,
                    "private",
                    "active",
                    user_id,
                    ts,
                    ts,
                ),
            )
            self.upsert_knowledge_base_member(kb_id, "user", user_id, "admin", "system")
        self.conn.commit()

    def ensure_case_knowledge_base(self, case: dict[str, Any]) -> str:
        row = self.conn.execute(
            "SELECT id FROM knowledge_bases WHERE type = 'case' AND owner_type = 'case' AND owner_id = ? LIMIT 1",
            (case["id"],),
        ).fetchone()
        kb_id = row["id"] if row else f"kb_{case['id']}"
        ts = now()
        if not row:
            self.conn.execute(
                """
                INSERT INTO knowledge_bases
                (id, type, name, description, owner_type, owner_id, knowledge_type, matter_id, review_status, confidentiality_level, maintainer_id, ai_usage_policy, ai_enabled, default_permission_policy, status, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (kb_id, "case", case["title"], "案件自动知识库", "case", case["id"], "matter_workspace", case["id"], "published", "confidential", case.get("owner_id"), "allow_generation", 1, "case_members", "active", case.get("owner_id"), ts, ts),
            )
        members = self.conn.execute("SELECT * FROM case_members WHERE case_id = ?", (case["id"],)).fetchall()
        for member in members:
            self.upsert_knowledge_base_member(kb_id, "user", member["user_id"], self.case_role_to_kb_role(member["role_code"]), member["granted_by"] or "system")
        self.conn.execute("UPDATE local_files SET knowledge_base_id = ? WHERE case_id = ? AND knowledge_base_id IS NULL", (kb_id, case["id"]))
        self.conn.commit()
        return kb_id

    def case_role_to_kb_role(self, role_code: str) -> str:
        if role_code == "readonly":
            return "viewer"
        if role_code in {"owner", "lead_lawyer"}:
            return "admin"
        return "editor"

    def normalize_knowledge_base(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        data = dict(row)
        data["ai_enabled"] = bool(data.get("ai_enabled"))
        data["ethical_wall_enabled"] = bool(data.get("ethical_wall_enabled"))
        data["expires_at"] = optional_int(data.get("expires_at"), "expires_at")
        data["citation_priority"] = int(data.get("citation_priority") or 0)
        return data

    def normalize_file(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        data = dict(row)
        data["ai_enabled"] = bool(data.get("ai_enabled", True))
        data["is_high_sensitive"] = bool(data.get("is_high_sensitive", False))
        signal_types = data.get("sensitive_signal_types") or "[]"
        if isinstance(signal_types, str):
            try:
                parsed_signal_types = json.loads(signal_types)
            except json.JSONDecodeError:
                parsed_signal_types = []
        else:
            parsed_signal_types = signal_types
        data["sensitive_signal_types"] = [str(item) for item in parsed_signal_types] if isinstance(parsed_signal_types, list) else []
        data["expires_at"] = optional_int(data.get("expires_at"), "expires_at")
        return data

    def normalize_knowledge_base_payload(self, payload: dict[str, Any], kb_type: str, user_id: str) -> dict[str, Any]:
        default_review_status = "published" if kb_type == "private" else "draft"
        default_ai_usage_policy = "allow_generation" if kb_type == "private" else "search_only"
        ai_usage_policy = normalize_choice(payload.get("ai_usage_policy"), KNOWLEDGE_AI_USAGE_POLICIES, default_ai_usage_policy, "AI usage policy")
        ai_enabled = optional_bool(payload.get("ai_enabled"), True) and ai_usage_policy != "disabled"
        maintainer_id = str(payload.get("maintainer_id") or user_id).strip() or user_id
        if maintainer_id != user_id:
            self.get_user(maintainer_id)
        department_id = str(payload.get("department_id") or "").strip() or None
        project_team_id = str(payload.get("project_team_id") or "").strip() or None
        client_id = str(payload.get("client_id") or "").strip() or None
        matter_id = str(payload.get("matter_id") or "").strip() or None
        ethical_wall_enabled = optional_bool(payload.get("ethical_wall_enabled"), False)
        if department_id:
            self.require_organization_unit(department_id, {"department", "practice_group"})
        if project_team_id:
            self.require_organization_unit(project_team_id, {"project_team"})
        if client_id:
            self.require_organization_unit(client_id, {"client"})
        if matter_id:
            self.require_organization_unit(matter_id, {"matter"})
        if ethical_wall_enabled and not (department_id or project_team_id):
            raise ValueError("ethical wall requires department_id or project_team_id")
        return {
            "knowledge_type": normalize_choice(payload.get("knowledge_type"), KNOWLEDGE_TYPES, "general", "knowledge type"),
            "business_domain": payload.get("business_domain") or None,
            "legal_domain": payload.get("legal_domain") or None,
            "jurisdiction": payload.get("jurisdiction") or None,
            "client_id": client_id,
            "matter_id": matter_id,
            "department_id": department_id,
            "project_team_id": project_team_id,
            "ethical_wall_enabled": ethical_wall_enabled,
            "review_status": normalize_choice(payload.get("review_status"), KNOWLEDGE_REVIEW_STATUSES, default_review_status, "review status"),
            "confidentiality_level": normalize_choice(payload.get("confidentiality_level"), KNOWLEDGE_CONFIDENTIALITY_LEVELS, "internal", "confidentiality level"),
            "maintainer_id": maintainer_id,
            "expires_at": optional_int(payload.get("expires_at"), "expires_at"),
            "ai_usage_policy": ai_usage_policy,
            "citation_priority": optional_int(payload.get("citation_priority", 0), "citation_priority") or 0,
            "ai_enabled": ai_enabled,
        }

    def file_governance_defaults(self, knowledge_base_id: str, user_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (knowledge_base_id,)).fetchone()
        if not row:
            raise KeyError("knowledge base not found")
        kb = self.normalize_knowledge_base(row)
        return {
            "review_status": kb.get("review_status") or "published",
            "confidentiality_level": kb.get("confidentiality_level") or "internal",
            "maintainer_id": kb.get("maintainer_id") or user_id,
            "expires_at": kb.get("expires_at"),
            "ai_usage_policy": kb.get("ai_usage_policy") or "allow_generation",
            "ai_enabled": bool(kb.get("ai_enabled", True)),
        }

    def normalize_file_governance_payload(self, payload: dict[str, Any], defaults: dict[str, Any], user_id: str) -> dict[str, Any]:
        ai_usage_policy = normalize_choice(payload.get("ai_usage_policy", defaults.get("ai_usage_policy")), KNOWLEDGE_AI_USAGE_POLICIES, "allow_generation", "AI usage policy")
        maintainer_id = str(payload.get("maintainer_id") or defaults.get("maintainer_id") or user_id).strip() or user_id
        if maintainer_id != user_id:
            self.get_user(maintainer_id)
        return {
            "review_status": normalize_choice(payload.get("review_status", defaults.get("review_status")), KNOWLEDGE_REVIEW_STATUSES, "published", "review status"),
            "confidentiality_level": normalize_choice(payload.get("confidentiality_level", defaults.get("confidentiality_level")), KNOWLEDGE_CONFIDENTIALITY_LEVELS, "internal", "confidentiality level"),
            "maintainer_id": maintainer_id,
            "expires_at": optional_int(payload.get("expires_at", defaults.get("expires_at")), "expires_at"),
            "ai_usage_policy": ai_usage_policy,
            "ai_enabled": optional_bool(payload.get("ai_enabled"), optional_bool(defaults.get("ai_enabled"), True)) and ai_usage_policy != "disabled",
        }

    def create_knowledge_base(self, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        kb_type = str(payload.get("type", "private")).strip()
        if kb_type not in {"private", "team"}:
            raise ValueError("knowledge base type must be private or team")
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("knowledge base name is required")
        kb_id = new_id("kb")
        ts = now()
        owner_type = "user" if kb_type == "private" else str(payload.get("owner_type", "team") or "team")
        owner_id = user_id if kb_type == "private" else str(payload.get("owner_id", user_id) or user_id)
        governance = self.normalize_knowledge_base_payload(payload, kb_type, user_id)
        self.conn.execute(
            """
            INSERT INTO knowledge_bases
            (id, type, name, description, owner_type, owner_id, knowledge_type, business_domain, legal_domain, jurisdiction, client_id, matter_id, department_id, project_team_id, ethical_wall_enabled, review_status, confidentiality_level, maintainer_id, expires_at, ai_usage_policy, citation_priority, ai_enabled, default_permission_policy, status, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kb_id,
                kb_type,
                name,
                payload.get("description"),
                owner_type,
                owner_id,
                governance["knowledge_type"],
                governance["business_domain"],
                governance["legal_domain"],
                governance["jurisdiction"],
                governance["client_id"],
                governance["matter_id"],
                governance["department_id"],
                governance["project_team_id"],
                1 if governance["ethical_wall_enabled"] else 0,
                governance["review_status"],
                governance["confidentiality_level"],
                governance["maintainer_id"],
                governance["expires_at"],
                governance["ai_usage_policy"],
                governance["citation_priority"],
                1 if governance["ai_enabled"] else 0,
                str(payload.get("default_permission_policy", "private")),
                "active",
                user_id,
                ts,
                ts,
            ),
        )
        self.upsert_knowledge_base_member(kb_id, "user", user_id, "admin", user_id)
        self.conn.commit()
        self.audit("KNOWLEDGE_BASE_CREATED", "knowledge_base", kb_id, user_id)
        return self.get_knowledge_base(kb_id, user_id)

    def upsert_knowledge_base_member(self, kb_id: str, principal_type: str, principal_id: str, role_code: str, granted_by: str = "system") -> str:
        if role_code not in {"admin", "editor", "viewer"}:
            raise ValueError("invalid knowledge base role")
        existing = self.conn.execute(
            """
            SELECT id FROM knowledge_base_members
            WHERE knowledge_base_id = ? AND principal_type = ? AND principal_id = ?
            """,
            (kb_id, principal_type, principal_id),
        ).fetchone()
        ts = now()
        if existing:
            member_id = existing["id"]
            self.conn.execute(
                "UPDATE knowledge_base_members SET role_code = ?, granted_by = ?, granted_at = ? WHERE id = ?",
                (role_code, granted_by, ts, member_id),
            )
        else:
            member_id = new_id("kbm")
            self.conn.execute(
                "INSERT INTO knowledge_base_members VALUES (?, ?, ?, ?, ?, ?, ?)",
                (member_id, kb_id, principal_type, principal_id, role_code, granted_by, ts),
            )
        return member_id

    def knowledge_base_role(self, kb_id: str, user_id: str) -> str | None:
        row = self.conn.execute(
            """
            SELECT role_code FROM knowledge_base_members
            WHERE knowledge_base_id = ? AND principal_type = 'user' AND principal_id = ?
            LIMIT 1
            """,
            (kb_id, user_id),
        ).fetchone()
        if row:
            return row["role_code"]
        kb = self.conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)).fetchone()
        if kb and kb["type"] == "private" and kb["owner_type"] == "user" and kb["owner_id"] == user_id:
            return "admin"
        return None

    def role_allows_action(self, role_code: str | None, action: str) -> bool:
        permissions = {
            "admin": {"view", "preview", "upload", "edit", "delete", "download", "ai_query", "grant", "audit_view"},
            "editor": {"view", "preview", "upload", "edit", "download", "ai_query"},
            "viewer": {"view", "preview", "download", "ai_query"},
        }
        return action in permissions.get(role_code or "", set())

    def user_is_bound_unit_reviewer(self, kb: dict[str, Any], user_id: str) -> bool:
        unit_ids = [kb.get("department_id"), kb.get("project_team_id"), kb.get("matter_id")]
        unit_ids = [str(item) for item in unit_ids if item]
        if not unit_ids:
            return False
        placeholders = ",".join("?" for _ in unit_ids)
        rows = self.conn.execute(
            f"SELECT position FROM organization_members WHERE user_id = ? AND unit_id IN ({placeholders}) AND status = 'active'",
            (user_id, *unit_ids),
        ).fetchall()
        reviewer_markers = ("管理员", "负责人", "合伙人", "主管", "reviewer", "approver", "manager", "partner")
        return any(any(marker in str(row["position"] or "").lower() for marker in reviewer_markers) for row in rows)

    def can_review_knowledge_base(self, kb: dict[str, Any], user_id: str) -> bool:
        user = self.get_user(user_id)
        local_role = user.get("role")
        if local_role == "agent_admin":
            return True
        if self.knowledge_base_role(str(kb["id"]), user_id) != "admin":
            return False
        if kb.get("knowledge_type") in HIGH_IMPACT_REVIEW_KNOWLEDGE_TYPES:
            return local_role == "lead_lawyer" or self.user_is_bound_unit_reviewer(kb, user_id)
        return local_role in KNOWLEDGE_REVIEWER_LOCAL_ROLES or self.user_is_bound_unit_reviewer(kb, user_id)

    def latest_knowledge_base_review_submitter(self, kb_id: str) -> str | None:
        row = self.conn.execute(
            """
            SELECT operator_id FROM knowledge_base_review_logs
            WHERE knowledge_base_id = ? AND action = 'submit_review'
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (kb_id,),
        ).fetchone()
        return row["operator_id"] if row else None

    def validate_publish_readiness(self, kb: dict[str, Any]) -> None:
        if kb.get("knowledge_type") not in HIGH_IMPACT_REVIEW_KNOWLEDGE_TYPES:
            return
        missing = []
        if not kb.get("maintainer_id"):
            missing.append("maintainer_id")
        if int(kb.get("citation_priority") or 0) <= 0:
            missing.append("citation_priority")
        if not kb.get("expires_at"):
            missing.append("expires_at")
        if missing:
            raise ValueError(f"high-impact knowledge requires {', '.join(missing)} before publish")

    def require_knowledge_base_review_permission(self, kb: dict[str, Any], action: str, user_id: str) -> None:
        if action == "submit_review":
            return
        if not self.can_review_knowledge_base(kb, user_id):
            raise PermissionError("knowledge base review permission denied")
        user = self.get_user(user_id)
        latest_submitter = self.latest_knowledge_base_review_submitter(str(kb["id"]))
        if action in {"publish", "reject"} and latest_submitter == user_id and user.get("role") != "agent_admin":
            raise PermissionError("knowledge base reviewer must differ from submitter")
        if action == "publish":
            self.validate_publish_readiness(kb)

    def validate_permission_action(self, action: str) -> None:
        if action not in {"view", "preview", "upload", "edit", "delete", "download", "ai_query", "grant", "audit_view"}:
            raise ValueError("invalid permission action")

    def validate_resource(self, resource_type: str, resource_id: str, include_deleted: bool = False) -> dict[str, Any]:
        if resource_type == "knowledge_base":
            row = self.conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (resource_id,)).fetchone()
        elif resource_type == "folder":
            deleted_clause = "" if include_deleted else "AND deleted_at IS NULL"
            row = self.conn.execute(f"SELECT * FROM folders WHERE id = ? {deleted_clause}", (resource_id,)).fetchone()
        elif resource_type == "file":
            deleted_clause = "" if include_deleted else "AND deleted_at IS NULL"
            row = self.conn.execute(f"SELECT * FROM local_files WHERE id = ? {deleted_clause}", (resource_id,)).fetchone()
        else:
            raise ValueError("invalid resource type")
        if not row:
            raise KeyError("resource not found")
        return dict(row)

    def resource_acl_chain(self, resource_type: str, resource_id: str, include_deleted: bool = False) -> list[tuple[str, str]]:
        resource = self.validate_resource(resource_type, resource_id, include_deleted=include_deleted)
        if resource_type == "knowledge_base":
            return [("knowledge_base", resource_id)]
        if resource_type == "folder":
            chain: list[tuple[str, str]] = [("folder", resource_id)]
            current = resource
            while current.get("parent_id"):
                parent = self.get_folder_any_status(str(current["parent_id"])) if include_deleted else self.get_folder(str(current["parent_id"]))
                chain.append(("folder", parent["id"]))
                current = parent
            chain.append(("knowledge_base", resource["knowledge_base_id"]))
            return chain
        if resource_type == "file":
            chain = [("file", resource_id)]
            if resource.get("folder_id"):
                chain.extend(self.resource_acl_chain("folder", str(resource["folder_id"]), include_deleted=include_deleted))
            elif resource.get("knowledge_base_id"):
                chain.append(("knowledge_base", resource["knowledge_base_id"]))
            return chain
        raise ValueError("invalid resource type")

    def resource_knowledge_base_id(self, resource_type: str, resource_id: str, include_deleted: bool = False) -> str:
        resource = self.validate_resource(resource_type, resource_id, include_deleted=include_deleted)
        if resource_type == "knowledge_base":
            return resource_id
        kb_id = resource.get("knowledge_base_id")
        if not kb_id:
            raise PermissionError("resource has no knowledge base")
        return str(kb_id)

    def acl_entries_for_user(self, resource_type: str, resource_id: str, user_id: str, action: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM acl_entries
            WHERE resource_type = ? AND resource_id = ?
              AND principal_type = 'user' AND principal_id = ?
              AND action = ?
            ORDER BY created_at DESC
            """,
            (resource_type, resource_id, user_id, action),
        ).fetchall()
        entries = [self.normalize_acl_entry(row) for row in rows]
        return [entry for entry in entries if not entry["is_expired"]]

    def normalize_acl_entry(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        entry = dict(row)
        entry["expires_at"] = optional_int(entry.get("expires_at"), "expires_at")
        entry["is_expired"] = bool(entry["expires_at"] and entry["expires_at"] <= now())
        return entry

    def has_resource_access(self, resource_type: str, resource_id: str, user_id: str, action: str = "view", include_deleted: bool = False) -> bool:
        self.validate_permission_action(action)
        chain = self.resource_acl_chain(resource_type, resource_id, include_deleted=include_deleted)
        for item_type, item_id in chain:
            if any(entry["effect"] == "deny" for entry in self.acl_entries_for_user(item_type, item_id, user_id, action)):
                return False
        kb_id = self.resource_knowledge_base_id(resource_type, resource_id, include_deleted=include_deleted)
        if not self.passes_ethical_wall(kb_id, user_id):
            return False
        for item_type, item_id in chain:
            if any(entry["effect"] == "allow" for entry in self.acl_entries_for_user(item_type, item_id, user_id, action)):
                return True
        return self.role_allows_action(self.knowledge_base_role(kb_id, user_id), action)

    def passes_ethical_wall(self, kb_id: str, user_id: str) -> bool:
        row = self.conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)).fetchone()
        if not row:
            raise KeyError("knowledge base not found")
        kb = self.normalize_knowledge_base(row)
        return bool(self.knowledge_boundary_evaluation(kb_id, user_id)["allowed_by_boundary"])

    def knowledge_boundary_evaluation(self, kb_id: str, user_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)).fetchone()
        if not row:
            raise KeyError("knowledge base not found")
        kb = self.normalize_knowledge_base(row)
        case_scope_managed = kb.get("type") == "case" and kb.get("owner_type") == "case"
        client_member = self.user_in_organization_unit(user_id, kb.get("client_id")) if kb.get("client_id") and not case_scope_managed else None
        matter_member = self.user_in_organization_unit(user_id, kb.get("matter_id")) if kb.get("matter_id") and not case_scope_managed else None
        department_member = self.user_in_organization_unit(user_id, kb.get("department_id")) if kb.get("department_id") else None
        project_team_member = self.user_in_organization_unit(user_id, kb.get("project_team_id")) if kb.get("project_team_id") else None
        ethical_wall_required = bool(kb.get("ethical_wall_enabled"))
        client_boundary_required = bool(kb.get("client_id") and not case_scope_managed)
        matter_boundary_required = bool(kb.get("matter_id") and not case_scope_managed)
        client_boundary_passed = True if not client_boundary_required else bool(client_member)
        matter_boundary_passed = True if not matter_boundary_required else bool(matter_member)
        ethical_wall_passed = True if not ethical_wall_required else bool(department_member or project_team_member)
        allowed_by_boundary = client_boundary_passed and matter_boundary_passed and ethical_wall_passed
        enabled_dimensions = [
            name
            for name, value in (
                ("client", kb.get("client_id")),
                ("matter", kb.get("matter_id")),
                ("department", kb.get("department_id")),
                ("project_team", kb.get("project_team_id")),
            )
            if value
        ]
        reasons: list[str] = []
        if kb.get("client_id"):
            reasons.append("client_boundary_tagged")
            if client_boundary_required:
                reasons.append("client_member_matched" if client_member else "client_member_missing")
            else:
                reasons.append("client_boundary_case_scope")
        if kb.get("matter_id"):
            reasons.append("matter_boundary_tagged")
            if matter_boundary_required:
                reasons.append("matter_member_matched" if matter_member else "matter_member_missing")
            else:
                reasons.append("matter_boundary_case_scope")
        if kb.get("department_id"):
            reasons.append("department_boundary_tagged")
            reasons.append("department_member_matched" if department_member else "department_member_missing")
        if kb.get("project_team_id"):
            reasons.append("project_team_boundary_tagged")
            reasons.append("project_team_member_matched" if project_team_member else "project_team_member_missing")
        if ethical_wall_required:
            reasons.append("ethical_wall_passed" if ethical_wall_passed else "ethical_wall_blocked")
        else:
            reasons.append("ethical_wall_not_enabled")
        return {
            "knowledge_base_id": kb_id,
            "user_id": user_id,
            "client_id": kb.get("client_id"),
            "matter_id": kb.get("matter_id"),
            "department_id": kb.get("department_id"),
            "project_team_id": kb.get("project_team_id"),
            "enabled_dimensions": enabled_dimensions,
            "ethical_wall_enabled": ethical_wall_required,
            "client_member": client_member,
            "matter_member": matter_member,
            "department_member": department_member,
            "project_team_member": project_team_member,
            "allowed_by_boundary": allowed_by_boundary,
            "reasons": reasons,
        }

    def require_resource_access(self, resource_type: str, resource_id: str, user_id: str, action: str = "view") -> dict[str, Any]:
        resource = self.validate_resource(resource_type, resource_id)
        if not self.has_resource_access(resource_type, resource_id, user_id, action):
            raise PermissionError("resource access denied")
        return resource

    def list_resource_permissions(self, resource_type: str, resource_id: str, user_id: str) -> list[dict[str, Any]]:
        self.require_resource_access(resource_type, resource_id, user_id, "grant")
        rows = self.conn.execute(
            "SELECT * FROM acl_entries WHERE resource_type = ? AND resource_id = ? ORDER BY created_at DESC",
            (resource_type, resource_id),
        ).fetchall()
        return [self.normalize_acl_entry(row) for row in rows]

    def effective_permissions(self, resource_type: str, resource_id: str, user_id: str, target_user_id: str | None = None) -> dict[str, Any]:
        target = target_user_id or user_id
        self.require_resource_access(resource_type, resource_id, user_id, "view")
        actions = ["view", "preview", "upload", "edit", "delete", "download", "ai_query", "grant", "audit_view"]
        return {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": target,
            "permissions": {action: self.has_resource_access(resource_type, resource_id, target, action) for action in actions},
            "boundary": self.knowledge_boundary_evaluation(self.resource_knowledge_base_id(resource_type, resource_id), target),
        }

    def set_acl_entry(self, payload: dict[str, Any], operator_id: str, effect: str | None = None) -> dict[str, Any]:
        resource_type = str(payload.get("resource_type", ""))
        resource_id = str(payload.get("resource_id", ""))
        principal_type = str(payload.get("principal_type", "user"))
        principal_id = str(payload.get("principal_id", payload.get("user_id", "")))
        action = str(payload.get("action", "view"))
        entry_effect = effect or str(payload.get("effect", "allow"))
        expires_at = optional_int(payload.get("expires_at"), "expires_at")
        if principal_type != "user":
            raise ValueError("MVP only supports user ACL principals")
        if entry_effect not in {"allow", "deny"}:
            raise ValueError("invalid ACL effect")
        self.validate_permission_action(action)
        self.get_user(principal_id)
        self.require_resource_access(resource_type, resource_id, operator_id, "grant")
        existing = self.conn.execute(
            """
            SELECT id FROM acl_entries
            WHERE resource_type = ? AND resource_id = ? AND principal_type = ? AND principal_id = ? AND action = ?
            """,
            (resource_type, resource_id, principal_type, principal_id, action),
        ).fetchone()
        ts = now()
        if existing:
            entry_id = existing["id"]
            self.conn.execute(
                "UPDATE acl_entries SET effect = ?, inherit = ?, created_by = ?, created_at = ?, expires_at = ? WHERE id = ?",
                (entry_effect, 1 if payload.get("inherit", True) else 0, operator_id, ts, expires_at, entry_id),
            )
        else:
            entry_id = new_id("acl")
            self.conn.execute(
                "INSERT INTO acl_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (entry_id, resource_type, resource_id, principal_type, principal_id, action, entry_effect, 1 if payload.get("inherit", True) else 0, operator_id, ts, expires_at),
            )
        self.conn.commit()
        self.audit("ACL_ENTRY_SET", resource_type, resource_id, operator_id)
        return self.normalize_acl_entry(self.conn.execute("SELECT * FROM acl_entries WHERE id = ?", (entry_id,)).fetchone())

    def delete_acl_entry(self, entry_id: str, operator_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM acl_entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            raise KeyError("ACL entry not found")
        entry = dict(row)
        self.require_resource_access(entry["resource_type"], entry["resource_id"], operator_id, "grant")
        self.conn.execute("DELETE FROM acl_entries WHERE id = ?", (entry_id,))
        self.conn.commit()
        self.audit("ACL_ENTRY_DELETED", entry["resource_type"], entry["resource_id"], operator_id)
        return {"id": entry_id, "deleted": True}

    def require_knowledge_base_access(self, kb_id: str, user_id: str, action: str = "view") -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)).fetchone()
        if not row:
            raise KeyError("knowledge base not found")
        role_code = self.knowledge_base_role(kb_id, user_id)
        if not self.has_resource_access("knowledge_base", kb_id, user_id, action):
            raise PermissionError("knowledge base access denied")
        data = self.normalize_knowledge_base(row)
        data["current_user_role"] = role_code
        return data

    def get_case_knowledge_base_id(self, case_id: str) -> str:
        case = self.get_case(case_id)
        return self.ensure_case_knowledge_base(case)

    def get_knowledge_base(self, kb_id: str, user_id: str) -> dict[str, Any]:
        return self.require_knowledge_base_access(kb_id, user_id, "view")

    def list_knowledge_bases(self, user_id: str) -> list[dict[str, Any]]:
        self.ensure_case_knowledge_bases()
        rows = self.conn.execute(
            """
            SELECT DISTINCT kb.*
            FROM knowledge_bases kb
            LEFT JOIN knowledge_base_members kbm ON kbm.knowledge_base_id = kb.id
            WHERE kb.status = 'active'
              AND (
                (kb.owner_type = 'user' AND kb.owner_id = ?)
                OR (kbm.principal_type = 'user' AND kbm.principal_id = ?)
              )
            ORDER BY kb.updated_at DESC
            """,
            (user_id, user_id),
        ).fetchall()
        results = []
        for row in rows:
            data = self.normalize_knowledge_base(row)
            if not self.has_resource_access("knowledge_base", data["id"], user_id, "view"):
                continue
            data["current_user_role"] = self.knowledge_base_role(data["id"], user_id)
            results.append(data)
        return results

    def serialize_governance_audit_value(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def record_knowledge_base_governance_changes(self, kb_id: str, changes: dict[str, tuple[Any, Any]], operator_id: str) -> None:
        ts = now()
        for field_name, (old_value, new_value) in changes.items():
            if self.serialize_governance_audit_value(old_value) == self.serialize_governance_audit_value(new_value):
                continue
            self.conn.execute(
                """
                INSERT INTO knowledge_base_governance_audit
                (id, knowledge_base_id, field_name, old_value, new_value, operator_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("kbga"),
                    kb_id,
                    field_name,
                    self.serialize_governance_audit_value(old_value),
                    self.serialize_governance_audit_value(new_value),
                    operator_id,
                    ts,
                ),
            )

    def list_knowledge_base_governance_audit(self, kb_id: str, user_id: str) -> list[dict[str, Any]]:
        self.require_knowledge_base_access(kb_id, user_id, "audit_view")
        rows = self.conn.execute(
            "SELECT * FROM knowledge_base_governance_audit WHERE knowledge_base_id = ? ORDER BY created_at DESC LIMIT 200",
            (kb_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def update_knowledge_base(self, kb_id: str, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        current = self.require_knowledge_base_access(kb_id, user_id, "grant")
        updates = []
        params: list[Any] = []
        governance_audit_changes: dict[str, tuple[Any, Any]] = {}
        for field in ("name", "description", "default_permission_policy"):
            if field in payload:
                value = str(payload[field]).strip() if field == "name" else payload[field]
                if field == "name" and not value:
                    raise ValueError("knowledge base name is required")
                updates.append(f"{field} = ?")
                params.append(value)
                if field == "default_permission_policy" and current.get(field) != value:
                    governance_audit_changes[field] = (current.get(field), value)
        governance_fields = {
            "knowledge_type",
            "business_domain",
            "legal_domain",
            "jurisdiction",
            "client_id",
            "matter_id",
            "department_id",
            "project_team_id",
            "ethical_wall_enabled",
            "review_status",
            "confidentiality_level",
            "maintainer_id",
            "expires_at",
            "ai_usage_policy",
            "citation_priority",
        }
        governance_touched = any(field in payload for field in governance_fields)
        if governance_touched:
            merged = {**current, **payload}
            governance = self.normalize_knowledge_base_payload(merged, str(current["type"]), user_id)
            for field in governance_fields:
                updates.append(f"{field} = ?")
                value = 1 if field == "ethical_wall_enabled" and governance[field] else 0 if field == "ethical_wall_enabled" else governance[field]
                params.append(value)
                if field in payload and current.get(field) != governance[field]:
                    governance_audit_changes[field] = (current.get(field), governance[field])
            if "ai_enabled" not in payload:
                updates.append("ai_enabled = ?")
                params.append(1 if governance["ai_enabled"] else 0)
                if current.get("ai_enabled") != governance["ai_enabled"] and ("ai_usage_policy" in payload or "review_status" in payload):
                    governance_audit_changes["ai_enabled"] = (current.get("ai_enabled"), governance["ai_enabled"])
        if "ai_enabled" in payload:
            ai_usage_policy = str(payload.get("ai_usage_policy", current.get("ai_usage_policy", "allow_generation")))
            next_ai_enabled = bool(payload.get("ai_enabled")) and ai_usage_policy != "disabled"
            updates.append("ai_enabled = ?")
            params.append(1 if next_ai_enabled else 0)
            if current.get("ai_enabled") != next_ai_enabled:
                governance_audit_changes["ai_enabled"] = (current.get("ai_enabled"), next_ai_enabled)
        if not updates:
            return self.get_knowledge_base(kb_id, user_id)
        updates.append("updated_at = ?")
        params.append(now())
        params.append(kb_id)
        self.conn.execute(f"UPDATE knowledge_bases SET {', '.join(updates)} WHERE id = ?", params)
        self.record_knowledge_base_governance_changes(kb_id, governance_audit_changes, user_id)
        self.conn.commit()
        self.audit("KNOWLEDGE_BASE_UPDATED", "knowledge_base", kb_id, user_id)
        return self.get_knowledge_base(kb_id, user_id)

    def transition_knowledge_base_review(self, kb_id: str, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        current = self.require_knowledge_base_access(kb_id, user_id, "grant")
        action = str(payload.get("action", "")).strip()
        status = str(current.get("review_status", "draft"))
        comment = str(payload.get("comment") or payload.get("reason") or "").strip() or None
        transitions = {
            "submit_review": {"from": {"draft", "rejected", "needs_update"}, "to": "pending_review", "audit": "KNOWLEDGE_BASE_REVIEW_SUBMITTED"},
            "publish": {"from": {"draft", "pending_review", "needs_update"}, "to": "published", "audit": "KNOWLEDGE_BASE_REVIEW_PUBLISHED"},
            "reject": {"from": {"pending_review"}, "to": "rejected", "audit": "KNOWLEDGE_BASE_REVIEW_REJECTED"},
            "mark_needs_update": {"from": {"published"}, "to": "needs_update", "audit": "KNOWLEDGE_BASE_REVIEW_NEEDS_UPDATE"},
            "deprecate": {"from": KNOWLEDGE_REVIEW_STATUSES - {"deprecated"}, "to": "deprecated", "audit": "KNOWLEDGE_BASE_REVIEW_DEPRECATED"},
            "disable_ai": {"from": KNOWLEDGE_REVIEW_STATUSES - {"ai_disabled"}, "to": "ai_disabled", "audit": "KNOWLEDGE_BASE_REVIEW_AI_DISABLED"},
            "enable_ai": {"from": {"ai_disabled"}, "to": "published", "audit": "KNOWLEDGE_BASE_REVIEW_AI_ENABLED"},
        }
        transition = transitions.get(action)
        if not transition:
            raise ValueError("invalid knowledge base review action")
        self.require_knowledge_base_review_permission(current, action, user_id)
        if status not in transition["from"]:
            raise ValueError(f"cannot {action} from {status}")
        review_status = str(payload.get("review_status") or transition["to"])
        if review_status != transition["to"]:
            raise ValueError("review_status does not match review action")
        if action == "reject" and not comment:
            raise ValueError("reject reason is required")
        updates = ["review_status = ?", "updated_at = ?"]
        ts = now()
        params: list[Any] = [review_status, ts]
        governance_audit_changes: dict[str, tuple[Any, Any]] = {}
        if current.get("review_status") != review_status:
            governance_audit_changes["review_status"] = (current.get("review_status"), review_status)
        if action == "disable_ai":
            updates.extend(["ai_enabled = ?", "ai_usage_policy = ?"])
            params.extend([0, "disabled"])
            governance_audit_changes["ai_enabled"] = (current.get("ai_enabled"), False)
            governance_audit_changes["ai_usage_policy"] = (current.get("ai_usage_policy"), "disabled")
        elif action == "enable_ai":
            ai_usage_policy = normalize_choice(payload.get("ai_usage_policy"), KNOWLEDGE_AI_USAGE_POLICIES - {"disabled"}, "allow_generation", "AI usage policy")
            updates.extend(["ai_enabled = ?", "ai_usage_policy = ?"])
            params.extend([1, ai_usage_policy])
            governance_audit_changes["ai_enabled"] = (current.get("ai_enabled"), True)
            governance_audit_changes["ai_usage_policy"] = (current.get("ai_usage_policy"), ai_usage_policy)
        elif action == "publish" and current.get("type") == "team" and current.get("ai_usage_policy") == "search_only":
            ai_usage_policy = normalize_choice(payload.get("ai_usage_policy"), KNOWLEDGE_AI_USAGE_POLICIES - {"disabled"}, "allow_generation", "AI usage policy")
            updates.extend(["ai_enabled = ?", "ai_usage_policy = ?"])
            params.extend([1, ai_usage_policy])
            governance_audit_changes["ai_enabled"] = (current.get("ai_enabled"), True)
            governance_audit_changes["ai_usage_policy"] = (current.get("ai_usage_policy"), ai_usage_policy)
        params.append(kb_id)
        self.conn.execute(f"UPDATE knowledge_bases SET {', '.join(updates)} WHERE id = ?", params)
        if action == "publish" and optional_bool(payload.get("publish_files"), True):
            file_ai_usage_policy = normalize_choice(payload.get("ai_usage_policy"), KNOWLEDGE_AI_USAGE_POLICIES - {"disabled"}, "allow_generation", "AI usage policy")
            self.conn.execute(
                """
                UPDATE local_files
                SET review_status = 'published', ai_usage_policy = ?, ai_enabled = 1
                WHERE knowledge_base_id = ?
                  AND deleted_at IS NULL
                  AND is_high_sensitive = 0
                  AND review_status IN ('draft', 'pending_review', 'rejected')
                  AND ai_usage_policy = 'search_only'
                """,
                (file_ai_usage_policy, kb_id),
            )
        self.conn.execute(
            """
            INSERT INTO knowledge_base_review_logs
            (id, knowledge_base_id, action, from_status, to_status, operator_id, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id("kbr"), kb_id, action, status, review_status, user_id, comment, ts),
        )
        self.record_knowledge_base_governance_changes(kb_id, governance_audit_changes, user_id)
        self.conn.commit()
        self.audit(str(transition["audit"]), "knowledge_base", kb_id, user_id)
        return self.get_knowledge_base(kb_id, user_id)

    def list_knowledge_base_review_logs(self, kb_id: str, user_id: str) -> list[dict[str, Any]]:
        self.require_knowledge_base_access(kb_id, user_id, "audit_view")
        rows = self.conn.execute(
            "SELECT * FROM knowledge_base_review_logs WHERE knowledge_base_id = ? ORDER BY created_at ASC",
            (kb_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def archive_knowledge_base(self, kb_id: str, user_id: str) -> dict[str, Any]:
        self.require_knowledge_base_access(kb_id, user_id, "grant")
        self.conn.execute("UPDATE knowledge_bases SET status = ?, updated_at = ? WHERE id = ?", ("archived", now(), kb_id))
        self.conn.commit()
        self.audit("KNOWLEDGE_BASE_ARCHIVED", "knowledge_base", kb_id, user_id)
        return {"id": kb_id, "status": "archived"}

    def soft_delete_knowledge_base(self, kb_id: str, user_id: str) -> dict[str, Any]:
        self.require_knowledge_base_access(kb_id, user_id, "delete")
        ts = now()
        self.conn.execute("UPDATE knowledge_bases SET status = ?, updated_at = ? WHERE id = ?", ("deleted", ts, kb_id))
        self.conn.execute("UPDATE folders SET deleted_at = ?, updated_at = ? WHERE knowledge_base_id = ? AND deleted_at IS NULL", (ts, ts, kb_id))
        self.conn.execute("UPDATE local_files SET deleted_at = ? WHERE knowledge_base_id = ? AND deleted_at IS NULL", (ts, kb_id))
        self.conn.commit()
        self.audit("KNOWLEDGE_BASE_DELETED", "knowledge_base", kb_id, user_id)
        return {"id": kb_id, "deleted": True, "status": "deleted"}

    def list_knowledge_base_members(self, kb_id: str, user_id: str) -> list[dict[str, Any]]:
        self.require_knowledge_base_access(kb_id, user_id, "grant")
        rows = self.conn.execute(
            "SELECT * FROM knowledge_base_members WHERE knowledge_base_id = ? ORDER BY granted_at DESC",
            (kb_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def knowledge_base_stats(self, kb_id: str, user_id: str) -> dict[str, Any]:
        self.require_knowledge_base_access(kb_id, user_id, "view")
        file_row = self.conn.execute(
            "SELECT COUNT(*) AS file_count, COALESCE(SUM(file_size), 0) AS total_size FROM local_files WHERE knowledge_base_id = ? AND deleted_at IS NULL",
            (kb_id,),
        ).fetchone()
        member_count = self.conn.execute("SELECT COUNT(*) AS count FROM knowledge_base_members WHERE knowledge_base_id = ?", (kb_id,)).fetchone()["count"]
        folder_count = self.conn.execute("SELECT COUNT(*) AS count FROM folders WHERE knowledge_base_id = ? AND deleted_at IS NULL", (kb_id,)).fetchone()["count"]
        return {
            "knowledge_base_id": kb_id,
            "file_count": file_row["file_count"],
            "folder_count": folder_count,
            "member_count": member_count,
            "total_size": file_row["total_size"],
        }

    def grant_knowledge_base_member(self, kb_id: str, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        self.require_knowledge_base_access(kb_id, user_id, "grant")
        principal_type = str(payload.get("principal_type", "user"))
        principal_id = str(payload.get("principal_id", payload.get("user_id", "")))
        role_code = str(payload.get("role_code", "viewer"))
        if principal_type != "user":
            raise ValueError("MVP only supports user principals")
        self.get_user(principal_id)
        member_id = self.upsert_knowledge_base_member(kb_id, principal_type, principal_id, role_code, user_id)
        self.conn.commit()
        self.audit("KNOWLEDGE_BASE_MEMBER_GRANTED", "knowledge_base_member", member_id, user_id)
        rows = self.list_knowledge_base_members(kb_id, user_id)
        return next(row for row in rows if row["id"] == member_id)

    def revoke_knowledge_base_member(self, kb_id: str, member_id: str, user_id: str) -> dict[str, Any]:
        self.require_knowledge_base_access(kb_id, user_id, "grant")
        row = self.conn.execute("SELECT * FROM knowledge_base_members WHERE id = ? AND knowledge_base_id = ?", (member_id, kb_id)).fetchone()
        if not row:
            raise KeyError("knowledge base member not found")
        member = dict(row)
        if member["role_code"] == "admin":
            admin_count = self.conn.execute(
                "SELECT COUNT(*) AS count FROM knowledge_base_members WHERE knowledge_base_id = ? AND role_code = 'admin'",
                (kb_id,),
            ).fetchone()["count"]
            if admin_count <= 1:
                raise ValueError("cannot revoke the last knowledge base admin")
        self.conn.execute("DELETE FROM knowledge_base_members WHERE id = ?", (member_id,))
        self.conn.commit()
        self.audit("KNOWLEDGE_BASE_MEMBER_REVOKED", "knowledge_base_member", member_id, user_id)
        return {"revoked": True, "id": member_id}

    def create_folder(self, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        kb_id = str(payload.get("knowledge_base_id", ""))
        self.require_knowledge_base_access(kb_id, user_id, "upload")
        parent_id = payload.get("parent_id")
        if parent_id:
            parent = self.get_folder(str(parent_id))
            if parent["knowledge_base_id"] != kb_id:
                raise ValueError("parent folder is outside the knowledge base")
            self.require_resource_access("folder", str(parent_id), user_id, "upload")
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("folder name is required")
        folder_id = new_id("folder")
        ts = now()
        self.conn.execute(
            """
            INSERT INTO folders
            (id, knowledge_base_id, parent_id, name, sort_order, permission_inherit, status, created_by, created_at, updated_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (folder_id, kb_id, parent_id, name, int(payload.get("sort_order", 0)), 1, "active", user_id, ts, ts, None),
        )
        self.conn.commit()
        self.audit("FOLDER_CREATED", "folder", folder_id, user_id)
        return self.get_folder(folder_id)

    def get_folder(self, folder_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM folders WHERE id = ? AND deleted_at IS NULL", (folder_id,)).fetchone()
        if not row:
            raise KeyError("folder not found")
        return dict(row)

    def get_folder_any_status(self, folder_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone()
        if not row:
            raise KeyError("folder not found")
        return dict(row)

    def descendant_folder_ids(self, folder_id: str) -> list[str]:
        ids: list[str] = []
        children = self.conn.execute("SELECT id FROM folders WHERE parent_id = ?", (folder_id,)).fetchall()
        for child in children:
            child_id = child["id"]
            ids.append(child_id)
            ids.extend(self.descendant_folder_ids(child_id))
        return ids

    def validate_folder_parent(self, folder_id: str, kb_id: str, parent_id: str | None, user_id: str) -> None:
        if not parent_id:
            return
        if parent_id == folder_id:
            raise ValueError("folder cannot be its own parent")
        parent = self.get_folder(parent_id)
        if parent["knowledge_base_id"] != kb_id:
            raise ValueError("parent folder is outside the knowledge base")
        current: dict[str, Any] | None = parent
        while current and current.get("parent_id"):
            if current["parent_id"] == folder_id:
                raise ValueError("folder cannot move under its descendant")
            current = self.get_folder(str(current["parent_id"]))
        self.require_resource_access("folder", parent_id, user_id, "upload")

    def update_folder(self, folder_id: str, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        folder = self.require_resource_access("folder", folder_id, user_id, "edit")
        updates = []
        params: list[Any] = []
        if "name" in payload:
            name = str(payload.get("name", "")).strip()
            if not name:
                raise ValueError("folder name is required")
            updates.append("name = ?")
            params.append(name)
        if "parent_id" in payload:
            parent_id = payload.get("parent_id")
            parent_id = str(parent_id) if parent_id else None
            self.validate_folder_parent(folder_id, folder["knowledge_base_id"], parent_id, user_id)
            updates.append("parent_id = ?")
            params.append(parent_id)
        if "sort_order" in payload:
            updates.append("sort_order = ?")
            params.append(int(payload.get("sort_order", 0)))
        if not updates:
            return self.get_folder(folder_id)
        updates.append("updated_at = ?")
        params.append(now())
        params.append(folder_id)
        self.conn.execute(f"UPDATE folders SET {', '.join(updates)} WHERE id = ?", params)
        self.conn.commit()
        self.audit("FOLDER_UPDATED", "folder", folder_id, user_id)
        return self.get_folder(folder_id)

    def soft_delete_folder(self, folder_id: str, user_id: str) -> dict[str, Any]:
        folder = self.require_resource_access("folder", folder_id, user_id, "delete")
        folder_ids = [folder_id, *self.descendant_folder_ids(folder_id)]
        ts = now()
        placeholders = ",".join("?" for _ in folder_ids)
        self.conn.execute(f"UPDATE folders SET deleted_at = ?, updated_at = ? WHERE id IN ({placeholders})", [ts, ts, *folder_ids])
        self.conn.execute(f"UPDATE local_files SET deleted_at = ? WHERE folder_id IN ({placeholders})", [ts, *folder_ids])
        self.conn.commit()
        self.audit("FOLDER_DELETED", "folder", folder_id, user_id)
        return {"id": folder_id, "deleted": True, "folder_count": len(folder_ids), "knowledge_base_id": folder["knowledge_base_id"]}

    def restore_folder(self, folder_id: str, user_id: str) -> dict[str, Any]:
        folder = self.get_folder_any_status(folder_id)
        self.require_knowledge_base_access(folder["knowledge_base_id"], user_id, "edit")
        if folder.get("parent_id"):
            parent = self.get_folder_any_status(str(folder["parent_id"]))
            if parent.get("deleted_at"):
                raise ValueError("cannot restore folder while parent folder is deleted")
        folder_ids = [folder_id, *self.descendant_folder_ids(folder_id)]
        placeholders = ",".join("?" for _ in folder_ids)
        self.conn.execute(f"UPDATE folders SET deleted_at = NULL, updated_at = ? WHERE id IN ({placeholders})", [now(), *folder_ids])
        self.conn.execute(f"UPDATE local_files SET deleted_at = NULL WHERE folder_id IN ({placeholders})", folder_ids)
        self.conn.commit()
        self.audit("FOLDER_RESTORED", "folder", folder_id, user_id)
        return self.get_folder(folder_id)

    def get_knowledge_base_tree(self, kb_id: str, user_id: str, include_deleted: bool = False) -> dict[str, Any]:
        tree_action = "edit" if include_deleted else "view"
        kb = self.require_knowledge_base_access(kb_id, user_id, tree_action)
        folder_deleted_clause = "" if include_deleted else "AND deleted_at IS NULL"
        file_deleted_clause = "" if include_deleted else "AND deleted_at IS NULL"

        folders = [
            dict(row)
            for row in self.conn.execute(f"SELECT * FROM folders WHERE knowledge_base_id = ? {folder_deleted_clause} ORDER BY parent_id, sort_order, name", (kb_id,)).fetchall()
            if self.has_resource_access("folder", row["id"], user_id, "view", include_deleted=include_deleted)
        ]
        files = [
            dict(row)
            for row in self.conn.execute(f"SELECT * FROM local_files WHERE knowledge_base_id = ? {file_deleted_clause} ORDER BY created_at DESC", (kb_id,)).fetchall()
            if self.has_resource_access("file", row["id"], user_id, "view", include_deleted=include_deleted)
        ]
        return {"knowledge_base": kb, "folders": folders, "files": files}

    def create_case(self, payload: dict[str, Any]) -> dict[str, Any]:
        case_id = new_id("case")
        ts = now()
        owner_id = payload.get("owner_id", "u_admin")
        self.conn.execute(
            "INSERT INTO case_spaces VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                case_id,
                payload.get("title", "未命名案件"),
                payload.get("cause_of_action"),
                payload.get("court"),
                payload.get("stage"),
                payload.get("client_name"),
                owner_id,
                "active",
                ts,
                ts,
            ),
        )
        self.conn.execute("INSERT INTO case_members VALUES (?, ?, ?, ?, ?, ?)", (new_id("cm"), case_id, owner_id, "owner", "system", ts))
        self.ensure_case_knowledge_base({"id": case_id, "title": payload.get("title", "未命名案件"), "owner_id": owner_id})
        self.conn.commit()
        self.audit("CASE_CREATED", "case", case_id)
        return self.get_case(case_id)

    def get_case(self, case_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM case_spaces WHERE id = ?", (case_id,)).fetchone()
        if not row:
            raise KeyError("case not found")
        return dict(row)

    def list_cases(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id:
            rows = self.conn.execute(
                """
                SELECT DISTINCT cs.*
                FROM case_spaces cs
                JOIN case_members cm ON cm.case_id = cs.id
                JOIN local_users u ON u.id = cm.user_id
                WHERE cm.user_id = ? AND u.status = 'active'
                ORDER BY cs.updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM case_spaces ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def is_case_member(self, case_id: str, user_id: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1
            FROM case_members cm
            JOIN local_users u ON u.id = cm.user_id
            WHERE cm.case_id = ? AND cm.user_id = ? AND u.status = 'active'
            LIMIT 1
            """,
            (case_id, user_id),
        ).fetchone()
        return bool(row)

    def require_case_access(self, case_id: str, user_id: str) -> None:
        self.get_case(case_id)
        if not self.is_case_member(case_id, user_id):
            raise CaseAccessError("case access denied")

    def list_case_members(self, case_id: str | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT cm.id, cm.case_id, cs.title AS case_title, cm.user_id, u.account, u.name, u.status AS user_status,
                   cm.role_code, cm.granted_by, cm.granted_at
            FROM case_members cm
            JOIN case_spaces cs ON cs.id = cm.case_id
            JOIN local_users u ON u.id = cm.user_id
        """
        params: list[Any] = []
        if case_id:
            sql += " WHERE cm.case_id = ?"
            params.append(case_id)
        sql += " ORDER BY cm.granted_at DESC"
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def grant_case_member(self, payload: dict[str, Any], operator_id: str = "u_admin") -> dict[str, Any]:
        case_id = str(payload.get("case_id", ""))
        user_id = str(payload.get("user_id", ""))
        role_code = str(payload.get("role_code", ""))
        if role_code not in {"owner", "co_lawyer", "assistant", "readonly"}:
            raise ValueError("invalid case role")
        self.get_case(case_id)
        user = self.get_user(user_id)
        if user["status"] != "active":
            raise ValueError("cannot grant disabled user")
        existing = self.conn.execute("SELECT id FROM case_members WHERE case_id = ? AND user_id = ?", (case_id, user_id)).fetchone()
        ts = now()
        if existing:
            member_id = existing["id"]
            self.conn.execute(
                "UPDATE case_members SET role_code = ?, granted_by = ?, granted_at = ? WHERE id = ?",
                (role_code, operator_id, ts, member_id),
            )
        else:
            member_id = new_id("cm")
            self.conn.execute("INSERT INTO case_members VALUES (?, ?, ?, ?, ?, ?)", (member_id, case_id, user_id, role_code, operator_id, ts))
        kb_id = self.get_case_knowledge_base_id(case_id)
        self.upsert_knowledge_base_member(kb_id, "user", user_id, self.case_role_to_kb_role(role_code), operator_id)
        self.conn.commit()
        self.audit("CASE_MEMBER_GRANTED", "case_member", member_id, operator_id)
        rows = self.list_case_members(case_id)
        return next(row for row in rows if row["id"] == member_id)

    def revoke_case_member(self, member_id: str, operator_id: str = "u_admin") -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM case_members WHERE id = ?", (member_id,)).fetchone()
        if not row:
            raise KeyError("case member not found")
        kb_id = self.get_case_knowledge_base_id(row["case_id"])
        self.conn.execute(
            "DELETE FROM knowledge_base_members WHERE knowledge_base_id = ? AND principal_type = 'user' AND principal_id = ?",
            (kb_id, row["user_id"]),
        )
        self.conn.execute("DELETE FROM case_members WHERE id = ?", (member_id,))
        self.conn.commit()
        self.audit("CASE_MEMBER_REVOKED", "case_member", member_id, operator_id)
        return {"revoked": True, "id": member_id}

    def save_uploaded_file(self, case_id: str | None, filename: str, content_b64: str, knowledge_base_id: str | None = None, folder_id: str | None = None, user_id: str = "u_admin") -> dict[str, Any]:
        if case_id:
            self.get_case(case_id)
            knowledge_base_id = knowledge_base_id or self.get_case_knowledge_base_id(case_id)
        if not knowledge_base_id:
            raise ValueError("knowledge_base_id is required")
        self.require_knowledge_base_access(knowledge_base_id, user_id, "upload")
        if folder_id:
            folder = self.get_folder(folder_id)
            if folder["knowledge_base_id"] != knowledge_base_id:
                raise ValueError("folder is outside the knowledge base")
        storage_dir = STORAGE_DIR / knowledge_base_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        safe_name = validate_upload_filename(filename)
        content = decode_upload_content(content_b64)
        content_hash = sha256_bytes(content)
        duplicate = self.find_duplicate_file(case_id, content_hash, knowledge_base_id)
        if duplicate:
            data = self.normalize_file(duplicate)
            data["deduplicated"] = True
            data["task_id"] = self.ensure_parse_task(data["id"])["id"]
            return data
        path = unique_path(storage_dir / safe_name)
        path.write_bytes(content)
        data = self.add_file(case_id, path, data_source_id=None, file_hash=content_hash, knowledge_base_id=knowledge_base_id, folder_id=folder_id, storage_mode="uploaded", user_id=user_id)
        data["task_id"] = self.ensure_parse_task(data["id"])["id"]
        data["deduplicated"] = False
        return data

    def find_duplicate_file(self, case_id: str | None, file_hash: str, knowledge_base_id: str | None = None) -> dict[str, Any] | None:
        if knowledge_base_id:
            row = self.conn.execute(
                "SELECT * FROM local_files WHERE knowledge_base_id = ? AND file_hash = ? AND deleted_at IS NULL ORDER BY created_at ASC LIMIT 1",
                (knowledge_base_id, file_hash),
            ).fetchone()
            return dict(row) if row else None
        row = self.conn.execute(
            "SELECT * FROM local_files WHERE case_id = ? AND file_hash = ? AND deleted_at IS NULL ORDER BY created_at ASC LIMIT 1",
            (case_id, file_hash),
        ).fetchone()
        return dict(row) if row else None

    def add_file(self, case_id: str | None, path: Path, data_source_id: str | None = None, file_hash: str | None = None, knowledge_base_id: str | None = None, folder_id: str | None = None, storage_mode: str = "scanned", user_id: str = "u_admin") -> dict[str, Any]:
        if case_id:
            self.get_case(case_id)
            knowledge_base_id = knowledge_base_id or self.get_case_knowledge_base_id(case_id)
        if not knowledge_base_id:
            raise ValueError("knowledge_base_id is required")
        suffix = path.suffix.lower()
        if suffix not in ALLOWED_FILE_EXTENSIONS:
            raise ValueError(f"file extension is not allowed: {suffix or '<none>'}")
        stat = path.stat()
        if stat.st_size > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError("file exceeds configured upload size limit")
        file_hash = file_hash or sha256_file(path)
        duplicate = self.find_duplicate_file(case_id, file_hash, knowledge_base_id)
        if duplicate:
            data = self.normalize_file(duplicate)
            data["deduplicated"] = True
            data["task_id"] = self.ensure_parse_task(data["id"])["id"]
            return data
        file_id = new_id("file")
        governance = self.file_governance_defaults(knowledge_base_id, user_id)
        self.conn.execute(
            """
            INSERT INTO local_files
            (id, data_source_id, case_id, file_name, file_path, file_ext, file_size, file_hash, modified_at, process_status, review_status, confidentiality_level, maintainer_id, expires_at, ai_usage_policy, ai_enabled, is_high_sensitive, sensitive_signal_types, created_at, knowledge_base_id, folder_id, storage_mode, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                data_source_id,
                case_id,
                path.name,
                str(path),
                path.suffix.lower(),
                stat.st_size,
                file_hash,
                int(stat.st_mtime),
                "pending",
                governance["review_status"],
                governance["confidentiality_level"],
                governance["maintainer_id"],
                governance["expires_at"],
                governance["ai_usage_policy"],
                1 if governance["ai_enabled"] else 0,
                0,
                "[]",
                now(),
                knowledge_base_id,
                folder_id,
                storage_mode,
                None,
            ),
        )
        self.conn.commit()
        self.audit("FILE_ADDED", "file", file_id)
        data = self.get_file(file_id)
        data["deduplicated"] = False
        return data

    def scan_data_source(self, data_source_id: str, case_id: str | None = None, knowledge_base_id: str | None = None, folder_id: str | None = None, user_id: str = "u_admin") -> dict[str, Any]:
        if case_id:
            self.get_case(case_id)
            knowledge_base_id = knowledge_base_id or self.get_case_knowledge_base_id(case_id)
        if not knowledge_base_id:
            raise ValueError("knowledge_base_id is required")
        self.require_knowledge_base_access(knowledge_base_id, user_id, "upload")
        if folder_id:
            folder = self.get_folder(folder_id)
            if folder["knowledge_base_id"] != knowledge_base_id:
                raise ValueError("folder is outside the knowledge base")
        source = self.get_data_source(data_source_id)
        check = self.check_directory_permission(source["path"])
        if not check["readable"]:
            raise PermissionError("data source directory is not readable")
        root = Path(source["path"])
        result: dict[str, Any] = {
            "data_source_id": data_source_id,
            "case_id": case_id,
            "knowledge_base_id": knowledge_base_id,
            "folder_id": folder_id,
            "discovered_count": 0,
            "added_count": 0,
            "duplicate_count": 0,
            "unsupported_count": 0,
            "enqueued_count": 0,
            "error_count": 0,
            "files": [],
            "errors": [],
        }
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.is_symlink():
                result["error_count"] += 1
                result["errors"].append({"path": str(path), "message": "symbolic link files are not allowed"})
                continue
            result["discovered_count"] += 1
            if path.suffix.lower() not in ALLOWED_FILE_EXTENSIONS:
                result["unsupported_count"] += 1
                continue
            try:
                validate_local_data_path(path)
                file_data = self.add_file(case_id, path, data_source_id=data_source_id, knowledge_base_id=knowledge_base_id, folder_id=folder_id, storage_mode="scanned", user_id=user_id)
                task = self.ensure_parse_task(file_data["id"])
                file_data["task_id"] = task["id"]
                result["files"].append(file_data)
                if file_data.get("deduplicated"):
                    result["duplicate_count"] += 1
                else:
                    result["added_count"] += 1
                    if task["status"] == "pending":
                        result["enqueued_count"] += 1
            except Exception as exc:
                result["error_count"] += 1
                result["errors"].append({"path": str(path), "message": str(exc)})
        self.audit("DATA_SOURCE_SCANNED", "data_source", data_source_id)
        return result

    def list_files(self, case_id: str | None = None, knowledge_base_id: str | None = None, folder_id: str | None = None) -> list[dict[str, Any]]:
        clauses = ["deleted_at IS NULL"]
        params: list[Any] = []
        if case_id:
            clauses.append("case_id = ?")
            params.append(case_id)
        if knowledge_base_id:
            clauses.append("knowledge_base_id = ?")
            params.append(knowledge_base_id)
        if folder_id:
            clauses.append("folder_id = ?")
            params.append(folder_id)
        rows = self.conn.execute("SELECT * FROM local_files WHERE " + " AND ".join(clauses) + " ORDER BY created_at DESC", params).fetchall()
        return [self.normalize_file(row) for row in rows]

    def list_files_for_user(self, user_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT DISTINCT f.*
            FROM local_files f
            LEFT JOIN knowledge_base_members kbm ON kbm.knowledge_base_id = f.knowledge_base_id
            LEFT JOIN knowledge_bases kb ON kb.id = f.knowledge_base_id
            LEFT JOIN case_members cm ON cm.case_id = f.case_id
            LEFT JOIN local_users u ON u.id = cm.user_id
            WHERE f.deleted_at IS NULL
              AND (
                (kb.owner_type = 'user' AND kb.owner_id = ?)
                OR (kbm.principal_type = 'user' AND kbm.principal_id = ?)
                OR (cm.user_id = ? AND u.status = 'active')
              )
            ORDER BY f.created_at DESC
            """,
            (user_id, user_id, user_id),
        ).fetchall()
        return [self.normalize_file(row) for row in rows]

    def get_file(self, file_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM local_files WHERE id = ?", (file_id,)).fetchone()
        if not row:
            raise KeyError("file not found")
        return self.normalize_file(row)

    def preview_file(self, file_id: str, user_id: str, chunk_limit: int = 8, text_limit: int = 6000) -> dict[str, Any]:
        file = self.require_file_access(file_id, user_id, "preview")
        watermark = self.create_access_watermark(file, user_id, "preview")
        self.audit("FILE_PREVIEWED", "file", file_id, user_id)
        risk_event = self.record_high_risk_file_access(file, user_id, "preview")
        chunk_limit = max(1, min(int(chunk_limit), 20))
        text_limit = max(500, min(int(text_limit), 20000))
        rows = self.conn.execute(
            """
            SELECT id, chunk_index, chunk_text, page_number, paragraph_ref
            FROM document_chunks
            WHERE file_id = ?
            ORDER BY chunk_index ASC
            LIMIT ?
            """,
            (file_id, chunk_limit),
        ).fetchall()
        if rows:
            chunks = [
                {
                    "chunk_id": row["id"],
                    "chunk_index": row["chunk_index"],
                    "text": row["chunk_text"],
                    "page_number": row["page_number"],
                    "paragraph_ref": row["paragraph_ref"],
                }
                for row in rows
            ]
            text = "\n\n".join(chunk["text"] for chunk in chunks)
            total_chunks = self.chunk_count(file_id)
            truncated = total_chunks > len(chunks) or len(text) > text_limit
            return {
                "file": file,
                "source": "chunks",
                "status": file["process_status"],
                "text": text[:text_limit],
                "chunks": chunks,
                "chunk_count": total_chunks,
                "truncated": truncated,
                "error": None,
                "watermark": watermark,
                "high_risk_event": risk_event,
            }

        path = Path(str(file["file_path"]))
        if not path.exists() or not path.is_file():
            return {
                "file": file,
                "source": "unavailable",
                "status": file["process_status"],
                "text": "",
                "chunks": [],
                "chunk_count": 0,
                "truncated": False,
                "error": "file content is not available on disk",
                "watermark": watermark,
                "high_risk_event": risk_event,
            }
        text = extract_text(path)
        return {
            "file": file,
            "source": "raw_file",
            "status": file["process_status"],
            "text": text[:text_limit],
            "chunks": [],
            "chunk_count": 0,
            "truncated": len(text) > text_limit,
            "error": None,
            "watermark": watermark,
            "high_risk_event": risk_event,
        }

    def file_content_for_preview(self, file_id: str, user_id: str) -> tuple[dict[str, Any], bytes, str]:
        file = self.require_file_access(file_id, user_id, "preview")
        if file.get("is_high_sensitive"):
            self.record_high_risk_file_access(file, user_id, "content_preview_blocked")
            self.audit("FILE_CONTENT_PREVIEW_BLOCKED", "file", file_id, user_id)
            raise PreviewContentBlockedError("native content preview is blocked for high-sensitive files; use text preview instead")
        path = Path(str(file["file_path"]))
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("file content is not available on disk")
        suffix = path.suffix.lower()
        watermark = self.create_access_watermark(file, user_id, "content_preview")
        self.audit("FILE_CONTENT_PREVIEWED", "file", file_id, user_id)
        self.record_high_risk_file_access(file, user_id, "content_preview")
        if suffix in OFFICE_FILE_EXTENSIONS:
            preview_pdf = office_preview_pdf_path(file_id, file.get("file_hash"), file.get("modified_at"))
            if not preview_pdf.exists() or preview_pdf.stat().st_size <= 0:
                self.ensure_office_preview_task(file_id)
                raise PreviewContentNotReadyError("office preview is not ready; conversion task has been queued")
            return watermark, preview_pdf.read_bytes(), "application/pdf"
        if suffix not in DIRECT_PREVIEW_FILE_EXTENSIONS:
            raise ValueError("file type is not supported for direct content preview")
        return watermark, path.read_bytes(), preview_content_type(path)

    def native_preview_status(self, file_id: str, user_id: str) -> dict[str, Any]:
        file = self.require_file_access(file_id, user_id, "preview")
        if file.get("is_high_sensitive"):
            return {"file_id": file_id, "status": "blocked", "content_type": None, "task_id": None, "error": "native content preview is blocked for high-sensitive files; use text preview instead"}
        path = Path(str(file["file_path"]))
        suffix = path.suffix.lower()
        if not path.exists() or not path.is_file():
            return {"file_id": file_id, "status": "unavailable", "content_type": None, "task_id": None, "error": "file content is not available on disk"}
        if suffix in DIRECT_PREVIEW_FILE_EXTENSIONS:
            return {"file_id": file_id, "status": "native_ready", "content_type": preview_content_type(path), "task_id": None, "error": None}
        if suffix not in OFFICE_FILE_EXTENSIONS:
            return {"file_id": file_id, "status": "unsupported", "content_type": None, "task_id": None, "error": "file type is not supported for direct content preview"}
        preview_pdf = office_preview_pdf_path(file_id, file.get("file_hash"), file.get("modified_at"))
        if preview_pdf.exists() and preview_pdf.stat().st_size > 0:
            return {"file_id": file_id, "status": "native_ready", "content_type": "application/pdf", "task_id": None, "error": None}
        task = self.ensure_office_preview_task(file_id)
        status_map = {"pending": "converting", "running": "converting", "failed": "conversion_failed", "success": "native_ready"}
        status = status_map.get(str(task.get("status")), "converting")
        if task.get("status") == "success" and (not preview_pdf.exists() or preview_pdf.stat().st_size <= 0):
            status = "conversion_failed"
        error = None
        if status == "conversion_failed":
            error = task.get("error_code") or "office preview conversion failed"
        return {"file_id": file_id, "status": status, "content_type": "application/pdf" if status == "native_ready" else None, "task_id": task.get("id"), "error": error}

    def run_native_preview(self, file_id: str, user_id: str) -> dict[str, Any]:
        status = self.native_preview_status(file_id, user_id)
        if status["status"] != "converting" and status["status"] != "conversion_failed":
            return status
        try:
            if status["status"] == "conversion_failed" and status.get("task_id"):
                self.retry_task(str(status["task_id"]))
            else:
                self.run_office_preview(file_id)
        except Exception:
            return self.native_preview_status(file_id, user_id)
        return self.native_preview_status(file_id, user_id)

    def require_file_access(self, file_id: str, user_id: str, action: str = "view") -> dict[str, Any]:
        file = self.get_file(file_id)
        if file.get("knowledge_base_id"):
            self.require_resource_access("file", file_id, user_id, "ai_query" if action == "ai_query" else action)
            return file
        if file.get("case_id"):
            self.require_case_access(file["case_id"], user_id)
            return file
        raise PermissionError("file access denied")

    def soft_delete_file(self, file_id: str, user_id: str) -> dict[str, Any]:
        self.require_file_access(file_id, user_id, "delete")
        self.conn.execute("UPDATE local_files SET deleted_at = ? WHERE id = ?", (now(), file_id))
        self.conn.commit()
        self.audit("FILE_DELETED", "file", file_id, user_id)
        return {"id": file_id, "deleted": True}

    def restore_file(self, file_id: str, user_id: str) -> dict[str, Any]:
        file = self.get_file(file_id)
        if file.get("knowledge_base_id"):
            self.require_knowledge_base_access(file["knowledge_base_id"], user_id, "edit")
            current_folder_id = file.get("folder_id")
            while current_folder_id:
                folder = self.get_folder_any_status(str(current_folder_id))
                if folder.get("deleted_at"):
                    raise ValueError("cannot restore file while parent folder is deleted")
                current_folder_id = folder.get("parent_id")
        elif file.get("case_id"):
            self.require_case_access(file["case_id"], user_id)
        else:
            raise PermissionError("file access denied")
        self.conn.execute("UPDATE local_files SET deleted_at = NULL WHERE id = ?", (file_id,))
        self.conn.commit()
        self.audit("FILE_RESTORED", "file", file_id, user_id)
        return self.get_file(file_id)

    def update_file(self, file_id: str, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        file = self.require_file_access(file_id, user_id, "edit")
        governance_fields = {"review_status", "confidentiality_level", "maintainer_id", "expires_at", "ai_usage_policy", "ai_enabled"}
        content_updated = False
        if "folder_id" not in payload and "file_name" not in payload and "content_base64" not in payload and not any(field in payload for field in governance_fields):
            return file
        updates = []
        params: list[Any] = []
        current_path = Path(str(file["file_path"]))
        next_path = current_path
        if "file_name" in payload:
            safe_name = validate_upload_filename(str(payload.get("file_name") or ""))
            if safe_name != file.get("file_name"):
                candidate_path = current_path.with_name(safe_name)
                if current_path.exists() and current_path.is_file():
                    next_path = unique_path(candidate_path) if candidate_path.exists() and candidate_path != current_path else candidate_path
                    current_path.rename(next_path)
                else:
                    next_path = candidate_path
                updates.extend(["file_name = ?", "file_path = ?", "file_ext = ?"])
                params.extend([next_path.name, str(next_path), next_path.suffix.lower()])
        if "content_base64" in payload:
            content = decode_upload_content(str(payload.get("content_base64") or ""))
            if not next_path.parent.exists():
                next_path.parent.mkdir(parents=True, exist_ok=True)
            next_path.write_bytes(content)
            stat = next_path.stat()
            updates.extend(["file_size = ?", "file_hash = ?", "modified_at = ?", "process_status = ?", "is_high_sensitive = ?", "sensitive_signal_types = ?"])
            params.extend([stat.st_size, sha256_bytes(content), int(stat.st_mtime), "pending", 0, "[]"])
            content_updated = True
        if "folder_id" in payload:
            folder_id = payload.get("folder_id")
            folder_id = str(folder_id) if folder_id else None
            if folder_id:
                folder = self.get_folder(folder_id)
                if folder["knowledge_base_id"] != file.get("knowledge_base_id"):
                    raise ValueError("folder is outside the knowledge base")
                self.require_resource_access("folder", folder_id, user_id, "upload")
            updates.append("folder_id = ?")
            params.append(folder_id)
        if any(field in payload for field in governance_fields):
            governance = self.normalize_file_governance_payload(payload, file, user_id)
            for field in ("review_status", "confidentiality_level", "maintainer_id", "expires_at", "ai_usage_policy", "ai_enabled"):
                updates.append(f"{field} = ?")
                params.append(1 if field == "ai_enabled" and governance[field] else 0 if field == "ai_enabled" else governance[field])
        params.append(file_id)
        self.conn.execute(f"UPDATE local_files SET {', '.join(updates)} WHERE id = ?", params)
        if content_updated:
            chunk_ids = [row["id"] for row in self.conn.execute("SELECT id FROM document_chunks WHERE file_id = ?", (file_id,)).fetchall()]
            if chunk_ids:
                placeholders = ",".join("?" for _ in chunk_ids)
                self.conn.execute(f"DELETE FROM vector_index_refs WHERE chunk_id IN ({placeholders})", chunk_ids)
            self.conn.execute("DELETE FROM local_embedding_vectors WHERE file_id = ?", (file_id,))
            self.conn.execute("DELETE FROM document_chunks WHERE file_id = ?", (file_id,))
        self.conn.commit()
        self.audit("FILE_UPDATED", "file", file_id, user_id)
        if content_updated:
            self.ensure_parse_task(file_id)
        return self.get_file(file_id)

    def ensure_parse_task(self, file_id: str) -> dict[str, Any]:
        file = self.get_file(file_id)
        row = self.conn.execute(
            """
            SELECT * FROM processing_tasks
            WHERE file_id = ? AND task_type = 'parse_index' AND status IN ('pending', 'running', 'failed')
            ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'running' THEN 1 ELSE 2 END, COALESCE(started_at, 0) DESC, id DESC
            LIMIT 1
            """,
            (file_id,),
        ).fetchone()
        if row:
            return dict(row)
        task_id = new_id("task")
        self.conn.execute(
            "INSERT INTO processing_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, file_id, file["case_id"], "parse_index", "pending", None, 0, None, None),
        )
        self.conn.execute("UPDATE local_files SET process_status = ? WHERE id = ?", ("pending", file_id))
        self.conn.commit()
        self.audit("TASK_ENQUEUED", "task", task_id)
        return self.get_task(task_id)

    def ensure_office_preview_task(self, file_id: str) -> dict[str, Any]:
        file = self.get_file(file_id)
        path = Path(str(file["file_path"]))
        if path.suffix.lower() not in OFFICE_FILE_EXTENSIONS:
            raise ValueError("file type is not supported for office preview conversion")
        row = self.conn.execute(
            """
            SELECT * FROM processing_tasks
            WHERE file_id = ? AND task_type = 'office_preview' AND status IN ('pending', 'running', 'failed')
            ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'running' THEN 1 WHEN 'failed' THEN 2 ELSE 3 END, COALESCE(started_at, 0) DESC, id DESC
            LIMIT 1
            """,
            (file_id,),
        ).fetchone()
        if row:
            return dict(row)
        task_id = new_id("task")
        self.conn.execute(
            "INSERT INTO processing_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, file_id, file["case_id"], "office_preview", "pending", None, 0, None, None),
        )
        self.conn.commit()
        self.audit("TASK_ENQUEUED", "task", task_id)
        return self.get_task(task_id)

    def list_tasks(self, file_id: str | None = None, case_id: str | None = None, status: str | None = None, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id:
            if case_id:
                self.require_case_access(case_id, user_id)
            if file_id:
                self.require_file_access(file_id, user_id)
            if not case_id and not file_id:
                rows = self.conn.execute(
                    """
                    SELECT DISTINCT t.*
                    FROM processing_tasks t
                    LEFT JOIN local_files f ON f.id = t.file_id
                    LEFT JOIN knowledge_base_members kbm ON kbm.knowledge_base_id = f.knowledge_base_id
                    LEFT JOIN knowledge_bases kb ON kb.id = f.knowledge_base_id
                    LEFT JOIN case_members cm ON cm.case_id = t.case_id
                    LEFT JOIN local_users u ON u.id = cm.user_id
                    WHERE (cm.user_id = ? AND u.status = 'active')
                       OR (kb.owner_type = 'user' AND kb.owner_id = ?)
                       OR (kbm.principal_type = 'user' AND kbm.principal_id = ?)
                    """,
                    (user_id, user_id, user_id),
                ).fetchall()
                if status:
                    rows = [row for row in rows if row["status"] == status]
                return [dict(row) for row in rows]
        sql = "SELECT * FROM processing_tasks"
        clauses = []
        params: list[Any] = []
        if file_id:
            clauses.append("file_id = ?")
            params.append(file_id)
        if case_id:
            clauses.append("case_id = ?")
            params.append(case_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY COALESCE(started_at, 0) DESC, id DESC"
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def get_task(self, task_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM processing_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise KeyError("task not found")
        return dict(row)

    def require_task_access(self, task_id: str, user_id: str) -> dict[str, Any]:
        task = self.get_task(task_id)
        case_id = task.get("case_id")
        if case_id:
            self.require_case_access(str(case_id), user_id)
        elif task.get("file_id"):
            self.require_file_access(str(task["file_id"]), user_id)
        return task

    def parse_file(self, file_id: str) -> dict[str, Any]:
        file = self.get_file(file_id)
        existing_success = self.conn.execute(
            "SELECT * FROM processing_tasks WHERE file_id = ? AND task_type = 'parse_index' AND status = 'success' ORDER BY finished_at DESC LIMIT 1",
            (file_id,),
        ).fetchone()
        if existing_success and file["process_status"] == "indexed":
            return {"file_id": file_id, "task_id": existing_success["id"], "chunks": self.chunk_count(file_id), "status": "indexed"}
        if existing_success and file["process_status"] == HIGH_SENSITIVE_PROCESS_STATUS and not self.file_allows_ai_usage(file_id, generate=False):
            return {
                "file_id": file_id,
                "task_id": existing_success["id"],
                "chunks": 0,
                "status": HIGH_SENSITIVE_PROCESS_STATUS,
                "high_sensitive": True,
                "sensitive_signal_types": file.get("sensitive_signal_types", []),
            }
        task = self.ensure_parse_task(file_id)
        task_id = task["id"]
        self.conn.execute("UPDATE processing_tasks SET status = ?, error_code = ?, started_at = ?, finished_at = ? WHERE id = ?", ("running", None, now(), None, task_id))
        self.conn.execute("UPDATE local_files SET process_status = ? WHERE id = ?", ("parsing", file_id))
        self.conn.commit()
        return self._run_parse_task(file_id, task_id)

    def run_pending_tasks(self, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        rows = self.conn.execute(
            """
            SELECT * FROM processing_tasks
            WHERE status = 'pending' AND task_type IN ('parse_index', 'office_preview')
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        result: dict[str, Any] = {"requested_limit": limit, "picked_count": len(rows), "success_count": 0, "failed_count": 0, "tasks": []}
        for row in rows:
            task = dict(row)
            file_id = task.get("file_id")
            if not file_id:
                continue
            try:
                if task.get("task_type") == "office_preview":
                    converted = self.run_office_preview(file_id)
                    result["success_count"] += 1
                    result["tasks"].append({"task_id": task["id"], "file_id": file_id, "task_type": task.get("task_type"), "status": "success", "content_type": converted["content_type"]})
                    continue
                parsed = self.parse_file(file_id)
                result["success_count"] += 1
                result["tasks"].append({"task_id": task["id"], "file_id": file_id, "task_type": task.get("task_type"), "status": "success", "chunks": parsed["chunks"]})
            except Exception as exc:
                result["failed_count"] += 1
                result["tasks"].append({"task_id": task["id"], "file_id": file_id, "task_type": task.get("task_type"), "status": "failed", "error": str(exc)})
        self.audit("TASK_QUEUE_DRAINED", "task_queue", None)
        return result

    def retry_failed_tasks(self, limit: int = 20, max_retries: int = WORKER_MAX_RETRIES) -> dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        rows = self.conn.execute(
            """
            SELECT * FROM processing_tasks
            WHERE status = 'failed' AND task_type IN ('parse_index', 'office_preview') AND retry_count < ?
            ORDER BY COALESCE(finished_at, 0) ASC, id ASC
            LIMIT ?
            """,
            (max_retries, limit),
        ).fetchall()
        result: dict[str, Any] = {"requested_limit": limit, "max_retries": max_retries, "picked_count": len(rows), "success_count": 0, "failed_count": 0, "tasks": []}
        for row in rows:
            task = dict(row)
            try:
                retried = self.retry_task(task["id"])
                result["success_count"] += 1
                item = {"task_id": task["id"], "file_id": task.get("file_id"), "task_type": task.get("task_type"), "status": "success"}
                if "chunks" in retried:
                    item["chunks"] = retried["chunks"]
                if "content_type" in retried:
                    item["content_type"] = retried["content_type"]
                result["tasks"].append(item)
            except Exception as exc:
                result["failed_count"] += 1
                result["tasks"].append({"task_id": task["id"], "file_id": task.get("file_id"), "status": "failed", "error": str(exc)})
        self.audit("TASK_QUEUE_RETRIED", "task_queue", None)
        return result

    def run_worker_once(self, batch_size: int = WORKER_BATCH_SIZE, max_retries: int = WORKER_MAX_RETRIES, sync_qdrant: bool = True) -> dict[str, Any]:
        pending = self.run_pending_tasks(batch_size)
        retries = self.retry_failed_tasks(batch_size, max_retries)
        qdrant_sync = self.sync_qdrant_vectors(batch_size) if sync_qdrant and self.qdrant_enabled() else {"status": "skipped", "qdrant_configured": self.qdrant_enabled(), "picked_count": 0, "synced_count": 0, "updated_ref_count": 0}
        return {
            "status": "ok",
            "pending": pending,
            "retries": retries,
            "qdrant_sync": qdrant_sync,
            "processed_count": pending["success_count"] + pending["failed_count"] + retries["success_count"] + retries["failed_count"],
        }

    def chunk_count(self, file_id: str) -> int:
        return self.conn.execute("SELECT COUNT(*) AS c FROM document_chunks WHERE file_id = ?", (file_id,)).fetchone()["c"]

    def clear_file_ai_index(self, file_id: str) -> None:
        self.conn.execute(
            "DELETE FROM vector_index_refs WHERE chunk_id IN (SELECT id FROM document_chunks WHERE file_id = ?)",
            (file_id,),
        )
        self.conn.execute("DELETE FROM document_chunks WHERE file_id = ?", (file_id,))
        self.conn.execute("DELETE FROM local_embedding_vectors WHERE file_id = ?", (file_id,))

    def mark_file_high_sensitive(self, file_id: str, task_id: str, signals: dict[str, int]) -> dict[str, Any]:
        self.clear_file_ai_index(file_id)
        self.conn.execute(
            """
            UPDATE local_files
            SET process_status = ?, confidentiality_level = ?, ai_usage_policy = ?, ai_enabled = ?, is_high_sensitive = ?, sensitive_signal_types = ?
            WHERE id = ?
            """,
            (
                HIGH_SENSITIVE_PROCESS_STATUS,
                "restricted",
                "disabled",
                0,
                1,
                json.dumps(sorted(signals), ensure_ascii=False),
                file_id,
            ),
        )
        self.conn.execute("UPDATE processing_tasks SET status = ?, error_code = ?, finished_at = ? WHERE id = ?", ("success", None, now(), task_id))
        self.conn.commit()
        self.audit("FILE_HIGH_SENSITIVE_AI_DISABLED", "file", file_id)
        return {
            "file_id": file_id,
            "task_id": task_id,
            "chunks": 0,
            "status": HIGH_SENSITIVE_PROCESS_STATUS,
            "high_sensitive": True,
            "sensitive_signals": signals,
        }

    def embedding_vector_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS c FROM local_embedding_vectors").fetchone()["c"]

    def request_embedding(self, text: str) -> dict[str, Any]:
        result = self.request_embeddings([text])
        if result["status"] != "success" or not result.get("vectors"):
            return {"status": result["status"], "vector": None, "model": result["model"], "error_code": result["error_code"]}
        return {"status": "success", "vector": result["vectors"][0], "model": result["model"], "error_code": None}

    def request_embeddings(self, texts: list[str]) -> dict[str, Any]:
        row = self.latest_model_config_row()
        if not row:
            return {"status": "not_configured", "vectors": None, "model": "mvp-keyword", "error_code": "MODEL_NOT_CONFIGURED"}
        if not texts:
            return {"status": "success", "vectors": [], "model": row["embedding_model"], "error_code": None}
        api_key = decrypt_secret(row["api_key_encrypted"])
        if not api_key:
            return {"status": "failed", "vectors": None, "model": row["embedding_model"], "error_code": "MODEL_API_KEY_MISSING"}
        payload = {"model": row["embedding_model"], "input": [text[:8000] for text in texts]}
        url = str(row["base_url"]).rstrip("/") + "/embeddings"
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=MODEL_REQUEST_TIMEOUT_SECONDS) as resp:  # noqa: S310 - configured lawyer-side model URL
                body = json.loads(resp.read().decode("utf-8"))
            vectors = self.extract_embedding_vectors(body)
            if vectors is None or len(vectors) != len(texts):
                return {"status": "failed", "vectors": None, "model": row["embedding_model"], "error_code": "EMBEDDING_EMPTY"}
            return {"status": "success", "vectors": vectors, "model": row["embedding_model"], "error_code": None}
        except urllib.error.HTTPError as exc:
            return {"status": "failed", "vectors": None, "model": row["embedding_model"], "error_code": f"HTTP_{exc.code}"}
        except urllib.error.URLError:
            return {"status": "failed", "vectors": None, "model": row["embedding_model"], "error_code": "CONNECTION_FAILED"}
        except TimeoutError:
            return {"status": "failed", "vectors": None, "model": row["embedding_model"], "error_code": "TIMEOUT"}
        except Exception:
            return {"status": "failed", "vectors": None, "model": row["embedding_model"], "error_code": "EMBEDDING_RESPONSE_INVALID"}

    def extract_embedding_vector(self, body: dict[str, Any]) -> list[float] | None:
        vectors = self.extract_embedding_vectors(body)
        return vectors[0] if vectors else None

    def extract_embedding_vectors(self, body: dict[str, Any]) -> list[list[float]] | None:
        data = body.get("data")
        if not isinstance(data, list) or not data:
            return None
        vectors: list[list[float]] = []
        for entry in data:
            embedding = entry.get("embedding") if isinstance(entry, dict) else None
            if not isinstance(embedding, list) or not embedding:
                return None
            vector: list[float] = []
            for item in embedding:
                if not isinstance(item, int | float):
                    return None
                vector.append(float(item))
            vectors.append(vector)
        return vectors

    def save_embedding_vector(self, chunk_id: str, case_id: str, file_id: str, model: str, vector: list[float]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO local_embedding_vectors VALUES (?, ?, ?, ?, ?, ?)",
            (chunk_id, case_id, file_id, model, json.dumps(vector), now()),
        )

    def qdrant_enabled(self) -> bool:
        return bool(QDRANT_URL) and is_allowed_local_url(QDRANT_URL)

    def qdrant_point_id(self, chunk_id: str) -> str:
        return stable_uuid(f"{QDRANT_COLLECTION}:{chunk_id}")

    def qdrant_request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.qdrant_enabled():
            raise RuntimeError("qdrant is not configured")
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{QDRANT_URL}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=QDRANT_TIMEOUT_SECONDS) as resp:  # noqa: S310 - configured local vector store URL
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}

    def ensure_qdrant_collection(self, vector_size: int) -> bool:
        if not self.qdrant_enabled():
            return False
        try:
            self.qdrant_request("GET", f"/collections/{QDRANT_COLLECTION}")
            return True
        except Exception:
            payload = {"vectors": {"size": vector_size, "distance": "Cosine"}}
            try:
                self.qdrant_request("PUT", f"/collections/{QDRANT_COLLECTION}", payload)
                return True
            except Exception:
                return False

    def upsert_qdrant_vector(self, chunk_id: str, case_id: str, file_id: str, model: str, vector: list[float]) -> bool:
        return self.upsert_qdrant_vectors([{"chunk_id": chunk_id, "case_id": case_id, "file_id": file_id, "model": model, "vector": vector}])

    def upsert_qdrant_vectors(self, items: list[dict[str, Any]]) -> bool:
        valid_items = [item for item in items if item.get("vector")]
        if not valid_items:
            return False
        first_vector = valid_items[0]["vector"]
        if not self.ensure_qdrant_collection(len(first_vector)):
            return False
        points = []
        for item in valid_items:
            chunk_id = item["chunk_id"]
            points.append(
                {
                    "id": self.qdrant_point_id(chunk_id),
                    "vector": item["vector"],
                    "payload": {"chunk_id": chunk_id, "case_id": item["case_id"], "file_id": item["file_id"], "embedding_model": item["model"]},
                }
            )
        payload = {
            "points": points
        }
        try:
            self.qdrant_request("PUT", f"/collections/{QDRANT_COLLECTION}/points?wait=true", payload)
            return True
        except Exception:
            return False

    def sync_qdrant_vectors(self, limit: int = 500, case_id: str | None = None) -> dict[str, Any]:
        limit = max(1, min(int(limit), 5000))
        if not self.qdrant_enabled():
            return {"qdrant_configured": False, "picked_count": 0, "synced_count": 0, "updated_ref_count": 0, "status": "not_configured"}
        sql = "SELECT * FROM local_embedding_vectors"
        params: list[Any] = []
        if case_id:
            self.get_case(case_id)
            sql += " WHERE case_id = ?"
            params.append(case_id)
        sql += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        items = []
        for row in rows:
            try:
                vector = [float(item) for item in json.loads(row["vector_json"])]
            except Exception:
                continue
            items.append({"chunk_id": row["chunk_id"], "case_id": row["case_id"], "file_id": row["file_id"], "model": row["embedding_model"], "vector": vector})
        if not items:
            return {"qdrant_configured": True, "picked_count": len(rows), "synced_count": 0, "updated_ref_count": 0, "status": "empty"}
        if not self.upsert_qdrant_vectors(items):
            return {"qdrant_configured": True, "picked_count": len(rows), "synced_count": 0, "updated_ref_count": 0, "status": "failed"}
        updated_ref_count = 0
        for item in items:
            cursor = self.conn.execute(
                "UPDATE vector_index_refs SET vector_collection = ?, vector_id = ? WHERE chunk_id = ?",
                (f"qdrant:{QDRANT_COLLECTION}", self.qdrant_point_id(item["chunk_id"]), item["chunk_id"]),
            )
            updated_ref_count += cursor.rowcount
        self.conn.commit()
        self.audit("QDRANT_VECTOR_SYNCED", "vector_store", QDRANT_COLLECTION)
        return {
            "qdrant_configured": True,
            "collection": QDRANT_COLLECTION,
            "picked_count": len(rows),
            "synced_count": len(items),
            "updated_ref_count": updated_ref_count,
            "status": "success",
        }

    def search_qdrant(self, scope_id: str, query_vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
        if not self.qdrant_enabled() or not query_vector:
            return []
        payload = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True,
            "filter": {"must": [{"key": "case_id", "match": {"value": scope_id}}]},
        }
        try:
            response = self.qdrant_request("POST", f"/collections/{QDRANT_COLLECTION}/points/search", payload)
        except Exception:
            return []
        points = response.get("result")
        if not isinstance(points, list):
            return []
        chunk_ids: list[str] = []
        scores: dict[str, float] = {}
        for point in points:
            if not isinstance(point, dict):
                continue
            payload_data = point.get("payload") if isinstance(point.get("payload"), dict) else {}
            chunk_id = payload_data.get("chunk_id")
            if isinstance(chunk_id, str):
                chunk_ids.append(chunk_id)
                scores[chunk_id] = float(point.get("score", 0.0))
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        rows = self.conn.execute(
            f"""
            SELECT c.*, f.file_name
            FROM document_chunks c
            JOIN local_files f ON f.id = c.file_id
            WHERE c.id IN ({placeholders}) AND c.case_id = ? AND (f.case_id = ? OR f.knowledge_base_id = ?) AND f.deleted_at IS NULL
            """,
            [*chunk_ids, scope_id, scope_id, scope_id],
        ).fetchall()
        by_id = {row["id"]: dict(row) for row in rows}
        results = []
        for chunk_id in chunk_ids:
            item = by_id.get(chunk_id)
            if not item:
                continue
            item["score"] = scores.get(chunk_id, 0.0)
            item["retrieval_mode"] = "qdrant"
            results.append(item)
        return results

    def cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)

    def _run_parse_task(self, file_id: str, task_id: str) -> dict[str, Any]:
        file = self.get_file(file_id)
        try:
            text = extract_text(Path(file["file_path"]))
            sensitive_signals = detect_high_sensitive_signals(text)
            if sensitive_signals:
                return self.mark_file_high_sensitive(file_id, task_id, sensitive_signals)
            chunks = split_chunks(text)
            if not chunks:
                raise ValueError("empty document text")
            self.clear_file_ai_index(file_id)
            embedding_batch = self.request_embeddings(chunks)
            vectors = embedding_batch.get("vectors") if embedding_batch["status"] == "success" else None
            qdrant_items: list[dict[str, Any]] = []
            chunk_records: list[dict[str, Any]] = []
            scope_id = file["case_id"] or file.get("knowledge_base_id")
            for idx, chunk in enumerate(chunks):
                chunk_id = new_id("chunk")
                self.conn.execute(
                    "INSERT INTO document_chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (chunk_id, scope_id, file_id, idx, chunk, None, f"chunk-{idx}", len(tokenize(chunk)), now()),
                )
                vector_collection = "local_keyword_index"
                vector_id = chunk_id
                embedding_model = "mvp-keyword"
                vector = vectors[idx] if isinstance(vectors, list) and idx < len(vectors) else None
                if vector:
                    vector_collection = "local_sqlite_embedding_vectors"
                    vector_id = f"emb_{chunk_id}"
                    embedding_model = embedding_batch["model"]
                    self.save_embedding_vector(chunk_id, scope_id, file_id, embedding_model, vector)
                    qdrant_items.append({"chunk_id": chunk_id, "case_id": scope_id, "file_id": file_id, "model": embedding_model, "vector": vector})
                chunk_records.append({"chunk_id": chunk_id, "vector_collection": vector_collection, "vector_id": vector_id, "embedding_model": embedding_model})
            qdrant_success = self.upsert_qdrant_vectors(qdrant_items)
            for record in chunk_records:
                vector_collection = record["vector_collection"]
                vector_id = record["vector_id"]
                if qdrant_success and vector_collection == "local_sqlite_embedding_vectors":
                    vector_collection = f"qdrant:{QDRANT_COLLECTION}"
                    vector_id = self.qdrant_point_id(record["chunk_id"])
                self.conn.execute(
                    "INSERT INTO vector_index_refs VALUES (?, ?, ?, ?, ?, ?)",
                    (new_id("vec"), record["chunk_id"], vector_collection, vector_id, record["embedding_model"], now()),
                )
            self.conn.execute("UPDATE local_files SET process_status = ? WHERE id = ?", ("indexed", file_id))
            self.conn.execute("UPDATE processing_tasks SET status = ?, finished_at = ? WHERE id = ?", ("success", now(), task_id))
            self.conn.commit()
            self.audit("FILE_INDEXED", "file", file_id)
            return {"file_id": file_id, "task_id": task_id, "chunks": len(chunks), "status": "indexed"}
        except Exception:
            self.conn.execute("UPDATE local_files SET process_status = ? WHERE id = ?", ("failed", file_id))
            self.conn.execute("UPDATE processing_tasks SET status = ?, error_code = ?, finished_at = ? WHERE id = ?", ("failed", "FILE_PARSE_FAILED", now(), task_id))
            self.conn.commit()
            raise

    def run_office_preview(self, file_id: str) -> dict[str, Any]:
        file = self.get_file(file_id)
        path = Path(str(file["file_path"]))
        if path.suffix.lower() not in OFFICE_FILE_EXTENSIONS:
            raise ValueError("file type is not supported for office preview conversion")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("file content is not available on disk")
        task = self.ensure_office_preview_task(file_id)
        task_id = task["id"]
        preview_pdf = office_preview_pdf_path(file_id, file.get("file_hash"), file.get("modified_at"))
        if preview_pdf.exists() and preview_pdf.stat().st_size > 0:
            self.conn.execute("UPDATE processing_tasks SET status = ?, error_code = ?, finished_at = ? WHERE id = ?", ("success", None, now(), task_id))
            self.conn.commit()
            self.audit("FILE_OFFICE_PREVIEW_READY", "file", file_id)
            return {"file_id": file_id, "task_id": task_id, "status": "native_ready", "content_type": "application/pdf", "preview_path": str(preview_pdf)}
        self.conn.execute("UPDATE processing_tasks SET status = ?, error_code = ?, started_at = ?, finished_at = ? WHERE id = ?", ("running", None, now(), None, task_id))
        self.conn.commit()
        try:
            ensure_office_preview_pdf(path, preview_pdf)
            self.conn.execute("UPDATE processing_tasks SET status = ?, error_code = ?, finished_at = ? WHERE id = ?", ("success", None, now(), task_id))
            self.conn.commit()
            self.audit("FILE_OFFICE_PREVIEW_READY", "file", file_id)
            return {"file_id": file_id, "task_id": task_id, "status": "native_ready", "content_type": "application/pdf", "preview_path": str(preview_pdf)}
        except Exception as exc:
            message = str(exc)[:300] or "office preview conversion failed"
            self.conn.execute("UPDATE processing_tasks SET status = ?, error_code = ?, finished_at = ? WHERE id = ?", ("failed", message, now(), task_id))
            self.conn.commit()
            raise

    def retry_task(self, task_id: str) -> dict[str, Any]:
        task = self.get_task(task_id)
        if task["status"] != "failed":
            raise ValueError("only failed tasks can be retried")
        file_id = task.get("file_id")
        if not file_id:
            raise ValueError("task has no file to retry")
        self.conn.execute(
            "UPDATE processing_tasks SET status = ?, error_code = ?, retry_count = retry_count + 1, started_at = ?, finished_at = ? WHERE id = ?",
            ("running", None, now(), None, task_id),
        )
        if task.get("task_type") == "parse_index":
            self.conn.execute("UPDATE local_files SET process_status = ? WHERE id = ?", ("parsing", file_id))
        self.conn.commit()
        if task.get("task_type") == "office_preview":
            return self.run_office_preview(file_id)
        return self._run_parse_task(file_id, task_id)

    def file_allows_ai_usage(self, file_id: str, generate: bool) -> bool:
        file = self.get_file(file_id)
        if file.get("deleted_at"):
            return False
        if file.get("is_high_sensitive"):
            return False
        if not file.get("ai_enabled") or file.get("ai_usage_policy") == "disabled" or file.get("review_status") == "ai_disabled":
            return False
        if file.get("review_status") == "deprecated":
            return False
        if generate and file.get("ai_usage_policy") == "search_only":
            return False
        if generate and file.get("review_status") not in {"published", "needs_update"}:
            return False
        if generate and file.get("expires_at") and int(file["expires_at"]) <= now():
            return False
        return True

    def scope_allows_ai_usage(self, scope_id: str, generate: bool) -> bool:
        row = self.conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (scope_id,)).fetchone()
        if not row:
            return True
        kb = self.normalize_knowledge_base(row)
        if kb.get("status") != "active":
            return False
        if not kb.get("ai_enabled") or kb.get("ai_usage_policy") == "disabled" or kb.get("review_status") == "ai_disabled":
            return False
        if generate and kb.get("ai_usage_policy") == "search_only":
            return False
        if generate and kb.get("review_status") not in {"published", "needs_update"}:
            return False
        if generate and kb.get("expires_at") and int(kb["expires_at"]) <= now():
            return False
        return True

    def governance_flags_for_file(self, file: dict[str, Any]) -> list[str]:
        flags = []
        if file.get("expires_at") and int(file["expires_at"]) <= now():
            flags.append("expired")
        if file.get("review_status") == "needs_update":
            flags.append("needs_update")
        if file.get("review_status") == "deprecated":
            flags.append("deprecated")
        if file.get("ai_usage_policy") == "search_only":
            flags.append("search_only")
        if not file.get("ai_enabled", True) or file.get("ai_usage_policy") == "disabled" or file.get("review_status") == "ai_disabled":
            flags.append("ai_disabled")
        if file.get("is_high_sensitive"):
            flags.append("high_sensitive")
        return flags

    def annotate_search_hit_governance(self, hit: dict[str, Any]) -> dict[str, Any]:
        file = self.get_file(str(hit["file_id"]))
        kb_row = self.conn.execute("SELECT knowledge_type, review_status, citation_priority FROM knowledge_bases WHERE id = ?", (file.get("knowledge_base_id"),)).fetchone() if file.get("knowledge_base_id") else None
        flags = self.governance_flags_for_file(file)
        hit["file_review_status"] = file.get("review_status")
        hit["file_ai_usage_policy"] = file.get("ai_usage_policy")
        hit["file_ai_enabled"] = file.get("ai_enabled")
        hit["file_expires_at"] = file.get("expires_at")
        hit["file_confidentiality_level"] = file.get("confidentiality_level")
        hit["file_is_high_sensitive"] = file.get("is_high_sensitive")
        if kb_row:
            hit["knowledge_type"] = kb_row["knowledge_type"]
            hit["knowledge_review_status"] = kb_row["review_status"]
            hit["knowledge_trust_level"] = KNOWLEDGE_TRUST_LEVELS.get(kb_row["knowledge_type"], "general")
            hit["citation_priority"] = int(kb_row["citation_priority"] or 0)
        else:
            hit["knowledge_trust_level"] = "matter_fact" if file.get("case_id") else "general"
            hit["citation_priority"] = 0
        hit["governance_flags"] = flags
        hit["file_is_expired"] = "expired" in flags
        hit["file_requires_maintenance"] = bool({"expired", "needs_update", "deprecated"}.intersection(flags))
        return hit

    def search(self, scope_id: str, question: str, limit: int = 5, user_id: str | None = None, generate: bool = False) -> list[dict[str, Any]]:
        if not self.scope_allows_ai_usage(scope_id, generate=generate):
            return []
        vector_hits = self.vector_search(scope_id, question, limit)
        if vector_hits:
            hits = vector_hits
        else:
            hits = self.keyword_search(scope_id, question, limit)
        if user_id:
            hits = [hit for hit in hits if self.has_resource_access("file", hit["file_id"], user_id, "ai_query")]
        hits = [hit for hit in hits if self.file_allows_ai_usage(hit["file_id"], generate=generate)]
        annotated_hits = [self.annotate_search_hit_governance(hit) for hit in hits]
        if generate:
            annotated_hits.sort(key=lambda item: (int(item.get("citation_priority") or 0), float(item.get("score") or 0)), reverse=True)
        scoped_hits = annotated_hits[:limit]
        if user_id:
            seen_file_ids = set()
            for hit in scoped_hits:
                hit_file_id = hit["file_id"]
                if hit_file_id in seen_file_ids:
                    continue
                seen_file_ids.add(hit_file_id)
                self.record_high_risk_file_access(self.get_file(hit_file_id), user_id, "ai_query")
        return scoped_hits

    def vector_search(self, scope_id: str, question: str, limit: int = 5) -> list[dict[str, Any]]:
        embedding = self.request_embedding(question)
        query_vector = embedding.get("vector")
        if embedding["status"] != "success" or not query_vector:
            return []
        qdrant_hits = self.search_qdrant(scope_id, query_vector, limit)
        if qdrant_hits:
            return qdrant_hits
        rows = self.conn.execute(
            """
            SELECT c.*, f.file_name, v.vector_json, v.embedding_model
            FROM local_embedding_vectors v
            JOIN document_chunks c ON c.id = v.chunk_id
            JOIN local_files f ON f.id = c.file_id
            WHERE v.case_id = ? AND c.case_id = ? AND (f.case_id = ? OR f.knowledge_base_id = ?) AND f.deleted_at IS NULL
            """,
            (scope_id, scope_id, scope_id, scope_id),
        ).fetchall()
        results = []
        for row in rows:
            try:
                vector = json.loads(row["vector_json"])
                score = self.cosine_similarity(query_vector, [float(item) for item in vector])
            except Exception:
                continue
            if score > 0.01:
                item = dict(row)
                item.pop("vector_json", None)
                item["score"] = float(score)
                item["retrieval_mode"] = "embedding"
                results.append(item)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def keyword_search(self, scope_id: str, question: str, limit: int = 5) -> list[dict[str, Any]]:
        q_tokens = Counter(tokenize(question))
        rows = self.conn.execute(
            """
            SELECT c.*, f.file_name
            FROM document_chunks c
            JOIN local_files f ON f.id = c.file_id
            WHERE c.case_id = ? AND (f.case_id = ? OR f.knowledge_base_id = ?) AND f.deleted_at IS NULL
            """,
            (scope_id, scope_id, scope_id),
        ).fetchall()
        results = []
        for row in rows:
            text = row["chunk_text"]
            tokens = Counter(tokenize(text))
            score = sum(min(q_tokens[t], tokens[t]) for t in q_tokens)
            if score == 0:
                # Fallback substring scoring for Chinese phrases and exact terms.
                score = sum(1 for t in q_tokens if t and t in text.lower())
            if score >= 2:
                item = dict(row)
                item["score"] = float(score)
                item["retrieval_mode"] = "keyword"
                results.append(item)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def search_file(self, file_id: str, question: str, limit: int = 5, user_id: str | None = None, generate: bool = False) -> list[dict[str, Any]]:
        if user_id:
            file = self.require_file_access(file_id, user_id, "ai_query")
            self.record_high_risk_file_access(file, user_id, "ai_query")
        if not self.file_allows_ai_usage(file_id, generate=generate):
            return []
        hits = self.vector_search_file(file_id, question, limit)
        if not hits:
            hits = self.keyword_search_file(file_id, question, limit)
        annotated_hits = [self.annotate_search_hit_governance(hit) for hit in hits]
        if generate:
            annotated_hits.sort(key=lambda item: (int(item.get("citation_priority") or 0), float(item.get("score") or 0)), reverse=True)
        return annotated_hits[:limit]

    def vector_search_file(self, file_id: str, question: str, limit: int = 5) -> list[dict[str, Any]]:
        embedding = self.request_embedding(question)
        query_vector = embedding.get("vector")
        if embedding["status"] != "success" or not query_vector:
            return []
        rows = self.conn.execute(
            """
            SELECT c.*, f.file_name, v.vector_json, v.embedding_model
            FROM local_embedding_vectors v
            JOIN document_chunks c ON c.id = v.chunk_id
            JOIN local_files f ON f.id = c.file_id
            WHERE v.file_id = ? AND c.file_id = ? AND f.id = ? AND f.deleted_at IS NULL
            """,
            (file_id, file_id, file_id),
        ).fetchall()
        results = []
        for row in rows:
            try:
                vector = json.loads(row["vector_json"])
                score = self.cosine_similarity(query_vector, [float(item) for item in vector])
            except Exception:
                continue
            if score > 0.01:
                item = dict(row)
                item.pop("vector_json", None)
                item["score"] = float(score)
                item["retrieval_mode"] = "embedding"
                results.append(item)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def keyword_search_file(self, file_id: str, question: str, limit: int = 5) -> list[dict[str, Any]]:
        q_tokens = Counter(tokenize(question))
        rows = self.conn.execute(
            """
            SELECT c.*, f.file_name
            FROM document_chunks c
            JOIN local_files f ON f.id = c.file_id
            WHERE c.file_id = ? AND f.id = ? AND f.deleted_at IS NULL
            """,
            (file_id, file_id),
        ).fetchall()
        results = []
        for row in rows:
            text = row["chunk_text"]
            tokens = Counter(tokenize(text))
            score = sum(min(q_tokens[t], tokens[t]) for t in q_tokens)
            if score == 0:
                score = sum(1 for t in q_tokens if t and t in text.lower())
            if score >= 1:
                item = dict(row)
                item["score"] = float(score)
                item["retrieval_mode"] = "keyword"
                results.append(item)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def ask(self, case_id: str, question: str, user_id: str = "u_admin") -> dict[str, Any]:
        self.require_case_access(case_id, user_id)
        return self.ask_scope(case_id, question, user_id, "case")

    def ask_knowledge_base(self, kb_id: str, question: str, user_id: str = "u_admin") -> dict[str, Any]:
        self.require_knowledge_base_ai_usage(kb_id, user_id, generate=True)
        return self.ask_scope(kb_id, question, user_id, "knowledge_base")

    def ask_file(self, file_id: str, question: str, user_id: str = "u_admin") -> dict[str, Any]:
        file = self.require_file_access(file_id, user_id, "ai_query")
        hits = self.search_file(file_id, question, user_id=user_id, generate=True)
        session_id = new_id("chat")
        session_scope = file.get("case_id") or file.get("knowledge_base_id") or file_id
        self.conn.execute("INSERT INTO chat_sessions VALUES (?, ?, ?, ?, ?, ?)", (session_id, session_scope, user_id, question[:50], "current_file", now()))
        qid = new_id("msg")
        self.conn.execute("INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?, ?)", (qid, session_id, "user", question, 0, now()))
        if not hits:
            answer = self.build_structured_legal_answer("", "", [], "file", insufficient_evidence=True)
            aid = new_id("msg")
            self.conn.execute("INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?, ?)", (aid, session_id, "assistant", answer, 0, now()))
            self.conn.commit()
            self.audit("CHAT_ASKED_NO_CITATION", "file", file_id, user_id)
            return {"answer": answer, "citations": [], "session_id": session_id, "message_id": aid, "insufficient_evidence": True, "context_scope": "current_file"}
        summary = "\n".join(f"- {hit['chunk_text'][:220]}" for hit in hits[:3])
        model_result = self.generate_model_answer(file_id, question, hits)
        if model_result["status"] == "success":
            answer = model_result["answer"]
        else:
            answer = self.build_structured_legal_answer(
                "根据当前文件检索到的材料，可以形成初步辅助分析，但需律师复核后才能用于正式判断。",
                f"根据当前文件材料，检索到以下相关依据：\n{summary}",
                [],
                "file",
            )
        aid = new_id("msg")
        citations = []
        for hit in hits:
            if hit["file_id"] != file_id:
                raise PermissionError("citation is outside the current file scope")
            citation = {
                "case_id": hit["case_id"],
                "knowledge_base_id": file.get("knowledge_base_id"),
                "file_id": hit["file_id"],
                "file_name": hit["file_name"],
                "chunk_id": hit["id"],
                "chunk_index": hit["chunk_index"],
                "page_number": hit["page_number"],
                "paragraph_ref": hit["paragraph_ref"],
                "quote_text": hit["chunk_text"][:500],
                "relevance_score": hit["score"],
                "retrieval_mode": hit.get("retrieval_mode", "keyword"),
                "governance_flags": hit.get("governance_flags", []),
                "file_review_status": hit.get("file_review_status"),
                "file_ai_usage_policy": hit.get("file_ai_usage_policy"),
                "file_expires_at": hit.get("file_expires_at"),
                "file_is_expired": bool(hit.get("file_is_expired")),
                "file_requires_maintenance": bool(hit.get("file_requires_maintenance")),
                "knowledge_type": hit.get("knowledge_type"),
                "knowledge_trust_level": hit.get("knowledge_trust_level"),
                "citation_priority": hit.get("citation_priority"),
            }
            self.conn.execute(
                "INSERT INTO citations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id("cit"), aid, citation["file_id"], citation["chunk_id"], citation["page_number"], citation["quote_text"], citation["relevance_score"]),
            )
            citations.append(citation)
        answer = self.ensure_structured_legal_answer(answer, citations, "file")
        self.conn.execute("INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?, ?)", (aid, session_id, "assistant", answer, 1, now()))
        self.conn.commit()
        self.audit("CHAT_ASKED", "file", file_id, user_id)
        return {
            "answer": answer,
            "citations": citations,
            "session_id": session_id,
            "message_id": aid,
            "insufficient_evidence": False,
            "model_used": model_result["status"] == "success",
            "model_status": model_result["status"],
            "model_error_code": model_result.get("error_code"),
            "context_scope": "current_file",
        }

    def ai_query(self, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        question = str(payload.get("question", "")).strip()
        if not question:
            raise ValueError("question is required")
        context_scope = str(payload.get("context_scope", "")).strip()
        if context_scope == "current_file":
            return self.ask_file(str(payload["file_id"]), question, user_id)
        if context_scope in {"current_knowledge_base", "current_kb"}:
            result = self.ask_knowledge_base(str(payload["knowledge_base_id"]), question, user_id)
            result["context_scope"] = "current_knowledge_base"
            return result
        if context_scope == "current_case":
            result = self.ask(str(payload["case_id"]), question, user_id)
            result["context_scope"] = "current_case"
            return result
        raise ValueError("unsupported context_scope")

    def scenario_query(self, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        scenario = str(payload.get("scenario", "")).strip()
        if scenario not in SCENARIO_PROMPTS:
            raise ValueError("unsupported scenario")
        user_prompt = str(payload.get("question", "")).strip()
        question = SCENARIO_PROMPTS[scenario] if not user_prompt else f"{SCENARIO_PROMPTS[scenario]}\n\n用户补充：{user_prompt}"
        result = self.ai_query({**payload, "question": question}, user_id)
        result["scenario"] = scenario
        return result

    def require_knowledge_base_ai_usage(self, kb_id: str, user_id: str, generate: bool) -> dict[str, Any]:
        kb = self.require_knowledge_base_access(kb_id, user_id, "ai_query")
        if not kb.get("ai_enabled") or kb.get("ai_usage_policy") == "disabled" or kb.get("review_status") == "ai_disabled":
            self.audit("AI_REJECTED_DISABLED", "knowledge_base", kb_id, user_id)
            raise PermissionError("knowledge base AI usage is disabled")
        if generate and kb.get("ai_usage_policy") == "search_only":
            self.audit("AI_REJECTED_SEARCH_ONLY", "knowledge_base", kb_id, user_id)
            raise PermissionError("knowledge base is search-only and cannot generate AI answers")
        if generate and kb.get("review_status") not in {"published", "needs_update"}:
            self.audit("AI_REJECTED_NOT_PUBLISHED", "knowledge_base", kb_id, user_id)
            raise PermissionError("knowledge base is not published for AI generation")
        if generate and kb.get("expires_at") and int(kb["expires_at"]) <= now():
            self.audit("AI_REJECTED_EXPIRED", "knowledge_base", kb_id, user_id)
            raise PermissionError("knowledge base is expired and cannot generate AI answers")
        return kb

    def build_structured_legal_answer(self, conclusion: str, basis: str, citations: list[dict[str, Any]], scope_type: str, insufficient_evidence: bool = False) -> str:
        source_lines = [
            f"{index}. {citation['file_name']}，段落 {citation.get('paragraph_ref') or citation.get('chunk_index')}，摘录：{citation['quote_text'][:120]}"
            for index, citation in enumerate(citations[:5], start=1)
        ]
        scope_label = {"knowledge_base": "当前知识库材料", "file": "当前文件材料"}.get(scope_type, "当前案件材料")
        if insufficient_evidence:
            conclusion = "证据不足，不能下确定性法律结论。"
            basis = f"{scope_label}中未检索到充分依据，无法支撑确定性法律结论。"
            source_text = "无可用引用来源。"
            evidence_classification = "文件中明确记载：未检索到可核验记载。\n根据文件内容推理：因缺少引用材料，不进行推理。\n根据通用法律知识补充：不补充确定性结论，避免脱离材料泛化。\n证据不足，不能下结论：是。"
            uncertainty = "缺少可核验事实、法律依据或关键文件片段。"
            next_step = "请补充材料、缩小问题范围，或由律师人工检索后重新提问。"
        else:
            source_text = "\n".join(source_lines) if source_lines else "本次回答无可展示引用，不应作为正式依据。"
            explicit_record = source_lines[0] if source_lines else "未形成可展示引用。"
            evidence_classification = "\n".join(
                [
                    f"文件中明确记载：{explicit_record}",
                    "根据文件内容推理：只能在上述引用片段与问题之间做有限关联分析，不能扩展到未入库事实。",
                    "根据通用法律知识补充：仅可作为辅助背景，正式意见仍需律师核验现行法规、判例和完整事实。",
                    "证据不足，不能下结论：否；但结论范围受限于当前引用材料。",
                ]
            )
            uncertainty = "仅基于已入库且当前用户有权访问的材料，未覆盖库外事实、最新法规变化或未上传文件。"
            next_step = "请点击引用来源复核原文；如用于正式法律意见，应由律师结合完整事实和现行法律人工确认。"
        return "\n".join(
            [
                f"结论：\n{conclusion}",
                f"依据：\n{basis}\n\n{evidence_classification}",
                f"引用来源：\n{source_text}",
                f"适用前提：\n上述分析仅适用于当前问题、当前权限范围和已入库材料。",
                "风险提示：\nAI 回答仅作辅助分析，不构成正式法律意见；涉及客户出具、诉讼策略或重大交易时必须人工复核。",
                f"不确定事项：\n{uncertainty}",
                f"建议下一步：\n{next_step}",
            ]
        )

    def ensure_structured_legal_answer(self, answer: str, citations: list[dict[str, Any]], scope_type: str) -> str:
        evidence_markers = ("文件中明确记载", "根据文件内容推理", "根据通用法律知识补充", "证据不足，不能下结论")
        if all(section in answer for section in LEGAL_ANSWER_SECTIONS) and all(marker in answer for marker in evidence_markers):
            return answer
        basis = "模型已基于引用材料生成回答，但原始输出未完全符合结构化模板，系统已按法律工作台格式包装。"
        return self.build_structured_legal_answer(answer, basis, citations, scope_type)

    def ask_scope(self, scope_id: str, question: str, user_id: str, scope_type: str) -> dict[str, Any]:
        hits = self.search(scope_id, question, user_id=user_id, generate=True)
        session_id = new_id("chat")
        self.conn.execute("INSERT INTO chat_sessions VALUES (?, ?, ?, ?, ?, ?)", (session_id, scope_id, user_id, question[:50], "full", now()))
        qid = new_id("msg")
        self.conn.execute("INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?, ?)", (qid, session_id, "user", question, 0, now()))
        if not hits:
            answer = self.build_structured_legal_answer("", "", [], scope_type, insufficient_evidence=True)
            aid = new_id("msg")
            self.conn.execute("INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?, ?)", (aid, session_id, "assistant", answer, 0, now()))
            self.conn.commit()
            self.audit("CHAT_ASKED_NO_CITATION", scope_type, scope_id, user_id)
            return {"answer": answer, "citations": [], "session_id": session_id, "message_id": aid, "insufficient_evidence": True}
        summary = "\n".join(f"- {hit['chunk_text'][:220]}" for hit in hits[:3])
        model_result = self.generate_model_answer(scope_id, question, hits)
        if model_result["status"] == "success":
            answer = model_result["answer"]
        else:
            scope_label = "当前知识库材料" if scope_type == "knowledge_base" else "当前案件材料"
            answer = f"根据{scope_label}，检索到以下相关依据：\n{summary}\n\n以上为基于已入库材料的辅助分析，需律师结合完整案情确认。"
        aid = new_id("msg")
        citations = []
        for hit in hits:
            if hit["case_id"] != scope_id:
                raise PermissionError("citation is outside the current knowledge scope")
            citation = {
                "case_id": hit["case_id"],
                "knowledge_base_id": hit["case_id"] if scope_type == "knowledge_base" else None,
                "file_id": hit["file_id"],
                "file_name": hit["file_name"],
                "chunk_id": hit["id"],
                "chunk_index": hit["chunk_index"],
                "page_number": hit["page_number"],
                "paragraph_ref": hit["paragraph_ref"],
                "quote_text": hit["chunk_text"][:500],
                "relevance_score": hit["score"],
                "retrieval_mode": hit.get("retrieval_mode", "keyword"),
                "governance_flags": hit.get("governance_flags", []),
                "file_review_status": hit.get("file_review_status"),
                "file_ai_usage_policy": hit.get("file_ai_usage_policy"),
                "file_expires_at": hit.get("file_expires_at"),
                "file_is_expired": bool(hit.get("file_is_expired")),
                "file_requires_maintenance": bool(hit.get("file_requires_maintenance")),
                "knowledge_type": hit.get("knowledge_type"),
                "knowledge_trust_level": hit.get("knowledge_trust_level"),
                "citation_priority": hit.get("citation_priority"),
            }
            self.conn.execute(
                "INSERT INTO citations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id("cit"), aid, citation["file_id"], citation["chunk_id"], citation["page_number"], citation["quote_text"], citation["relevance_score"]),
            )
            citations.append(citation)
        answer = self.ensure_structured_legal_answer(answer, citations, scope_type)
        self.conn.execute("INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?, ?)", (aid, session_id, "assistant", answer, 1, now()))
        self.conn.commit()
        self.audit("CHAT_ASKED", scope_type, scope_id, user_id)
        return {
            "answer": answer,
            "citations": citations,
            "session_id": session_id,
            "message_id": aid,
            "insufficient_evidence": False,
            "model_used": model_result["status"] == "success",
            "model_status": model_result["status"],
            "model_error_code": model_result.get("error_code"),
        }

    def latest_model_config_row(self) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM model_configs ORDER BY created_at DESC LIMIT 1").fetchone()

    def generate_model_answer(self, case_id: str, question: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
        row = self.latest_model_config_row()
        if not row:
            return {"status": "not_configured", "answer": None, "error_code": "MODEL_NOT_CONFIGURED"}
        api_key = decrypt_secret(row["api_key_encrypted"])
        if not api_key:
            return {"status": "failed", "answer": None, "error_code": "MODEL_API_KEY_MISSING"}
        contexts = []
        for idx, hit in enumerate(hits[:5], start=1):
            contexts.append(f"[来源{idx}] 文件：{hit['file_name']}，段落：{hit['paragraph_ref']}\n{hit['chunk_text'][:1200]}")
        payload = {
            "model": row["chat_model"],
            "messages": [
                {
                    "role": "system",
                    "content": "你是律师本地知识库助手。只能依据用户提供的来源材料回答；不得编造事实；没有可靠引用时不得输出确定性法律结论。必须按以下栏目输出：结论、依据、引用来源、适用前提、风险提示、不确定事项、建议下一步。依据栏目必须明确区分：文件中明确记载、根据文件内容推理、根据通用法律知识补充、证据不足，不能下结论。回答末尾必须提示律师核验。",
                },
                {
                    "role": "user",
                    "content": f"问题：{question}\n\n当前知识范围ID：{case_id}\n\n来源材料：\n" + "\n\n".join(contexts),
                },
            ],
            "temperature": 0.2,
        }
        url = str(row["base_url"]).rstrip("/") + "/chat/completions"
        started = time.time()
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=MODEL_REQUEST_TIMEOUT_SECONDS) as resp:  # noqa: S310 - configured lawyer-side model URL
                body = json.loads(resp.read().decode("utf-8"))
            answer = self.extract_chat_answer(body)
            if not answer:
                return {"status": "failed", "answer": None, "error_code": "MODEL_EMPTY_ANSWER", "latency_ms": int((time.time() - started) * 1000)}
            return {"status": "success", "answer": answer, "error_code": None, "latency_ms": int((time.time() - started) * 1000)}
        except urllib.error.HTTPError as exc:
            return {"status": "failed", "answer": None, "error_code": f"HTTP_{exc.code}", "latency_ms": int((time.time() - started) * 1000)}
        except urllib.error.URLError:
            return {"status": "failed", "answer": None, "error_code": "CONNECTION_FAILED", "latency_ms": int((time.time() - started) * 1000)}
        except TimeoutError:
            return {"status": "failed", "answer": None, "error_code": "TIMEOUT", "latency_ms": int((time.time() - started) * 1000)}
        except Exception:
            return {"status": "failed", "answer": None, "error_code": "MODEL_RESPONSE_INVALID", "latency_ms": int((time.time() - started) * 1000)}

    def extract_chat_answer(self, body: dict[str, Any]) -> str | None:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first = choices[0]
        if not isinstance(first, dict):
            return None
        message = first.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"].strip()
        if isinstance(first.get("text"), str):
            return first["text"].strip()
        return None

    def list_chats(self, case_id: str | None = None) -> list[dict[str, Any]]:
        if case_id:
            self.get_case(case_id)
            rows = self.conn.execute("SELECT * FROM chat_sessions WHERE case_id = ? ORDER BY created_at DESC", (case_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM chat_sessions ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def list_chats_for_user(self, user_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT DISTINCT s.*
            FROM chat_sessions s
            LEFT JOIN case_members cm ON cm.case_id = s.case_id
            LEFT JOIN local_users u ON u.id = cm.user_id
            LEFT JOIN knowledge_base_members kbm ON kbm.knowledge_base_id = s.case_id
            LEFT JOIN knowledge_bases kb ON kb.id = s.case_id
            WHERE (cm.user_id = ? AND u.status = 'active')
               OR (kb.owner_type = 'user' AND kb.owner_id = ?)
               OR (kbm.principal_type = 'user' AND kbm.principal_id = ?)
            ORDER BY s.created_at DESC
            """,
            (user_id, user_id, user_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def require_chat_scope_access(self, scope_id: str, user_id: str) -> None:
        if self.conn.execute("SELECT 1 FROM case_spaces WHERE id = ?", (scope_id,)).fetchone():
            self.require_case_access(scope_id, user_id)
            return
        self.require_knowledge_base_access(scope_id, user_id, "ai_query")

    def get_chat_messages(self, session_id: str, user_id: str | None = None) -> list[dict[str, Any]]:
        session_scope_id: str | None = None
        if user_id:
            row = self.conn.execute("SELECT case_id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                raise KeyError("chat session not found")
            session_scope_id = str(row["case_id"])
            self.require_chat_scope_access(str(row["case_id"]), user_id)
        else:
            row = self.conn.execute("SELECT case_id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            session_scope_id = str(row["case_id"]) if row else None
        rows = self.conn.execute("SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,)).fetchall()
        messages = []
        for row in rows:
            message = dict(row)
            message["insufficient_evidence"] = bool(message.get("role") == "assistant" and not int(message.get("has_citations") or 0))
            if message.get("role") == "assistant" and int(message.get("has_citations") or 0):
                citation_rows = self.conn.execute(
                    """
                    SELECT
                        c.file_id,
                        c.chunk_id,
                        c.page_number,
                        c.quote_text,
                        c.relevance_score,
                        f.case_id,
                        f.knowledge_base_id,
                        f.file_name,
                        f.review_status AS file_review_status,
                        f.ai_usage_policy AS file_ai_usage_policy,
                        f.expires_at AS file_expires_at,
                        dc.chunk_index,
                        dc.paragraph_ref
                    FROM citations c
                    LEFT JOIN local_files f ON f.id = c.file_id
                    LEFT JOIN document_chunks dc ON dc.id = c.chunk_id
                    WHERE c.message_id = ?
                    ORDER BY c.relevance_score DESC
                    """,
                    (message["id"],),
                ).fetchall()
                citations = []
                for citation_row in citation_rows:
                    file_expires_at = citation_row["file_expires_at"]
                    citations.append(
                        {
                            "case_id": citation_row["case_id"] or session_scope_id,
                            "knowledge_base_id": citation_row["knowledge_base_id"],
                            "file_id": citation_row["file_id"],
                            "file_name": citation_row["file_name"] or citation_row["file_id"],
                            "chunk_id": citation_row["chunk_id"],
                            "chunk_index": citation_row["chunk_index"] if citation_row["chunk_index"] is not None else 0,
                            "page_number": citation_row["page_number"],
                            "paragraph_ref": citation_row["paragraph_ref"],
                            "quote_text": citation_row["quote_text"],
                            "relevance_score": citation_row["relevance_score"],
                            "retrieval_mode": "history",
                            "governance_flags": [],
                            "file_review_status": citation_row["file_review_status"],
                            "file_ai_usage_policy": citation_row["file_ai_usage_policy"],
                            "file_expires_at": file_expires_at,
                            "file_is_expired": bool(file_expires_at and int(file_expires_at) <= now()),
                            "file_requires_maintenance": bool(file_expires_at and int(file_expires_at) <= now()),
                        }
                    )
                message["citations"] = citations
            else:
                message["citations"] = []
            messages.append(message)
        return messages

    def create_summary(self, case_id: str) -> dict[str, Any]:
        rows = self.conn.execute("SELECT chunk_text FROM document_chunks WHERE case_id = ? ORDER BY chunk_index LIMIT 5", (case_id,)).fetchall()
        if not rows:
            return {"summary": "当前案件暂无已索引材料，无法生成摘要。", "status": "needs_material"}
        text = " ".join(row["chunk_text"] for row in rows)
        summary = text[:600] + ("..." if len(text) > 600 else "")
        return {"summary": summary, "status": "pending_lawyer_confirmation"}

    def create_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        ev_id = new_id("ev")
        file = self.get_file(payload["file_id"])
        if str(payload.get("case_id", "")) != str(file["case_id"]):
            raise PermissionError("evidence case does not match file case")
        self.conn.execute(
            "INSERT INTO evidences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ev_id, payload["case_id"], payload["file_id"], payload.get("evidence_name", file["file_name"]), payload.get("evidence_type"), payload.get("purpose"), payload.get("related_issue"), payload.get("sort_order", 0)),
        )
        self.conn.commit()
        self.audit("EVIDENCE_CREATED", "evidence", ev_id)
        return dict(self.conn.execute("SELECT * FROM evidences WHERE id = ?", (ev_id,)).fetchone())

    def list_evidences(self, case_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM evidences WHERE case_id = ? ORDER BY sort_order, evidence_name", (case_id,)).fetchall()]

    def list_evidences_for_user(self, case_id: str, user_id: str) -> list[dict[str, Any]]:
        self.require_case_access(case_id, user_id)
        return self.list_evidences(case_id)

    def audit_logs(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 200").fetchall()]

    def _sanitize_model_config(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        data = dict(row)
        encrypted = data.pop("api_key_encrypted", None)
        api_key = decrypt_secret(encrypted)
        data["api_key_configured"] = bool(api_key)
        data["api_key_masked"] = mask_secret(api_key)
        return data

    def save_model_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = str(payload.get("provider", "openai-compatible"))
        base_url = str(payload["base_url"])
        if not is_allowed_local_url(base_url):
            raise ValueError("model base_url must be localhost, private network, link-local, or .local")
        chat_model = str(payload["chat_model"])
        embedding_model = str(payload["embedding_model"])
        api_key = str(payload["api_key"])
        if not api_key.strip():
            raise ValueError("api_key is required")
        config_id = str(payload.get("id") or new_id("model"))
        ts = now()
        encrypted = encrypt_secret(api_key)
        self.conn.execute(
            "INSERT OR REPLACE INTO model_configs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (config_id, provider, base_url, chat_model, embedding_model, encrypted, "configured", ts),
        )
        self.conn.commit()
        self.audit("MODEL_CONFIG_SAVED", "model_config", config_id)
        return self.get_model_config(config_id)

    def list_model_configs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM model_configs ORDER BY created_at DESC").fetchall()
        return [self._sanitize_model_config(row) for row in rows]

    def get_model_config(self, config_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM model_configs WHERE id = ?", (config_id,)).fetchone()
        if not row:
            raise KeyError("model config not found")
        return self._sanitize_model_config(row)

    def latest_model_config(self) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM model_configs ORDER BY created_at DESC LIMIT 1").fetchone()
        return self._sanitize_model_config(row) if row else None

    def test_model_config(self, config_id: str, mode: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM model_configs WHERE id = ?", (config_id,)).fetchone()
        if not row:
            raise KeyError("model config not found")
        config = self._sanitize_model_config(row)
        if mode not in {"chat", "embedding"}:
            raise ValueError("mode must be chat or embedding")
        model_name = config["chat_model"] if mode == "chat" else config["embedding_model"]
        api_key = decrypt_secret(row["api_key_encrypted"])
        if not api_key:
            raise ValueError("api_key is not configured")
        base_url = str(config["base_url"]).rstrip("/")
        path = "/chat/completions" if mode == "chat" else "/embeddings"
        url = base_url + path
        payload = {"model": model_name}
        if mode == "chat":
            payload["messages"] = [{"role": "user", "content": "ping"}]
            payload["max_tokens"] = 1
        else:
            payload["input"] = "ping"
        started = time.time()
        status = "failed"
        error_code = None
        message = "connectivity check failed"
        if not should_probe_model_connectivity_url(base_url):
            return {
                "config_id": config_id,
                "mode": mode,
                "provider": config["provider"],
                "model": model_name,
                "base_url": config["base_url"],
                "status": status,
                "message": "model .local DNS probe is disabled by default",
                "error_code": "LOCAL_DNS_PROBE_DISABLED",
                "latency_ms": int((time.time() - started) * 1000),
                "api_key_configured": bool(api_key),
            }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=MODEL_CONNECTIVITY_TIMEOUT_SECONDS) as resp:  # noqa: S310 - configured lawyer-side model URL
                if 200 <= resp.status < 300:
                    status = "success"
                    message = "connectivity check succeeded"
                else:
                    error_code = f"HTTP_{resp.status}"
        except urllib.error.HTTPError as exc:
            error_code = f"HTTP_{exc.code}"
            message = "model endpoint returned an error"
        except urllib.error.URLError as exc:
            error_code = "CONNECTION_FAILED"
            message = str(exc.reason)[:160]
        except TimeoutError:
            error_code = "TIMEOUT"
            message = "model endpoint timed out"
        latency_ms = int((time.time() - started) * 1000)
        return {
            "config_id": config_id,
            "mode": mode,
            "status": status,
            "provider": config["provider"],
            "base_url": config["base_url"],
            "model": model_name,
            "api_key_configured": config["api_key_configured"],
            "latency_ms": latency_ms,
            "error_code": error_code,
            "message": message,
        }

    def status_payload(self) -> dict[str, Any]:
        self.conn.execute("SELECT 1").fetchone()
        storage_ready = STORAGE_DIR.exists() and os.access(STORAGE_DIR, os.W_OK)
        model_config = self.latest_model_config()
        embedding_count = self.embedding_vector_count()
        vector_store = "prototype_local_keyword_index"
        if embedding_count:
            vector_store = f"qdrant:{QDRANT_COLLECTION}" if self.qdrant_enabled() else "local_sqlite_embedding_vectors"
        return {
            "service": "agent-api",
            "status": "ok",
            "api": "ok",
            "database": "ok",
            "storage": "ok" if storage_ready else "error",
            "task_queue": "local_pending_queue_with_batch_runner",
            "vector_store": vector_store,
            "embedding_vector_count": embedding_count,
            "qdrant_configured": self.qdrant_enabled(),
            "ocr_configured": bool(OCR_COMMAND),
            "model_connectivity": "configured" if model_config else "not_configured",
            "model_provider": model_config["provider"] if model_config else None,
            "chat_model": model_config["chat_model"] if model_config else None,
            "embedding_model": model_config["embedding_model"] if model_config else None,
            "platform_base_url_configured": bool(PLATFORM_BASE_URL),
        }

    def health_payload(self) -> dict[str, Any]:
        pending = self.conn.execute("SELECT COUNT(*) AS c FROM processing_tasks WHERE status='pending'").fetchone()["c"]
        running = self.conn.execute("SELECT COUNT(*) AS c FROM processing_tasks WHERE status='running'").fetchone()["c"]
        failed = self.conn.execute("SELECT COUNT(*) AS c FROM processing_tasks WHERE status='failed'").fetchone()["c"]
        usage = shutil.disk_usage(DATA_DIR)
        payload = {
            "tenant_id": self.get_config("tenant_id", "local_tenant"),
            "agent_id": self.get_config("agent_id", "local_agent"),
            "agent_version": "4.1.0-mvp",
            "status": "online",
            "last_heartbeat": str(now()),
            "task_pending_count": pending,
            "task_running_count": running,
            "task_failed_count": failed,
            "error_code": "UNKNOWN_ERROR" if failed else None,
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": round(usage.used / usage.total, 4) if usage.total else 0.0,
        }
        return to_platform_health_payload(payload)


class LazyStore:
    def __init__(self) -> None:
        self._store: Store | None = None
        self._lock = threading.Lock()

    def _get(self) -> Store:
        if self._store is None:
            with self._lock:
                if self._store is None:
                    self._store = Store()
        return self._store

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


STORE: Store | LazyStore = LazyStore()


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 - configured local platform URL for MVP
        return json.loads(resp.read().decode("utf-8"))


class Handler(BaseHTTPRequestHandler):
    server_version = "V41AgentAPI/0.1"

    def _send(self, status: int, body: Any, content_type: str = "application/json") -> None:
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _ok(self, data: Any) -> None:
        self._send(200, {"code": 0, "message": "ok", "data": data})

    def _error(self, status: int, message: str) -> None:
        self._send(status, {"code": status, "message": message, "data": None})

    def _bearer_token(self) -> str | None:
        auth = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if auth.startswith(prefix):
            return auth[len(prefix) :].strip()
        return None

    def _require_user(self) -> dict[str, Any]:
        return STORE.current_user(self._bearer_token())

    def _require_agent_admin(self) -> dict[str, Any]:
        user = self._require_user()
        if user.get("role") != "agent_admin":
            raise PermissionError("agent admin role is required")
        return user

    def do_GET(self) -> None:  # noqa: N802
        try:
            path, _, query = self.path.partition("?")
            params = dict(part.split("=", 1) for part in query.split("&") if "=" in part)
            if path == "/health":
                self._ok(STORE.health_payload())
            elif path == "/api/agent/setup/status":
                self._ok(STORE.setup_status())
            elif path == "/api/agent/auth/me":
                self._ok(self._require_user())
            elif path == "/api/agent/status":
                self._require_user()
                self._ok(STORE.status_payload())
            elif path == "/api/agent/model-configs":
                self._require_user()
                self._ok(STORE.list_model_configs())
            elif path == "/api/agent/data-sources":
                self._require_user()
                self._ok(STORE.list_data_sources())
            elif path == "/api/agent/knowledge-bases":
                user = self._require_user()
                self._ok(STORE.list_knowledge_bases(user["id"]))
            elif path.startswith("/api/agent/knowledge-bases/") and path.endswith("/tree"):
                user = self._require_user()
                kb_id = path.split("/")[-2]
                self._ok(STORE.get_knowledge_base_tree(kb_id, user["id"]))
            elif path.startswith("/api/agent/knowledge-bases/") and path.endswith("/members"):
                user = self._require_user()
                kb_id = path.split("/")[-2]
                self._ok(STORE.list_knowledge_base_members(kb_id, user["id"]))
            elif path.startswith("/api/agent/knowledge-bases/") and path.endswith("/review-logs"):
                user = self._require_user()
                kb_id = path.split("/")[-2]
                self._ok(STORE.list_knowledge_base_review_logs(kb_id, user["id"]))
            elif path.startswith("/api/agent/knowledge-bases/") and path.endswith("/governance-audit"):
                user = self._require_user()
                kb_id = path.split("/")[-2]
                self._ok(STORE.list_knowledge_base_governance_audit(kb_id, user["id"]))
            elif path.startswith("/api/agent/knowledge-bases/") and path.endswith("/stats"):
                user = self._require_user()
                kb_id = path.split("/")[-2]
                self._ok(STORE.knowledge_base_stats(kb_id, user["id"]))
            elif path.startswith("/api/agent/knowledge-bases/"):
                user = self._require_user()
                kb_id = path.rsplit("/", 1)[-1]
                self._ok(STORE.get_knowledge_base(kb_id, user["id"]))
            elif path == "/api/agent/users":
                self._require_agent_admin()
                self._ok(STORE.list_users())
            elif path == "/api/agent/case-members":
                self._require_agent_admin()
                self._ok(STORE.list_case_members(params.get("case_id")))
            elif path == "/api/agent/enterprise/overview":
                self._require_agent_admin()
                self._ok(STORE.enterprise_overview())
            elif path == "/api/agent/enterprise/profile":
                self._require_agent_admin()
                self._ok(STORE.ensure_enterprise_profile())
            elif path == "/api/agent/organization/units":
                self._require_agent_admin()
                self._ok(STORE.list_organization_units())
            elif path == "/api/agent/organization/members":
                self._require_agent_admin()
                self._ok(STORE.list_organization_members())
            elif path == "/api/agent/external-org/integrations":
                self._require_agent_admin()
                self._ok(STORE.list_external_org_integrations())
            elif path == "/api/agent/ai-assistant/settings":
                self._require_agent_admin()
                self._ok(STORE.get_ai_assistant_setting(params.get("scope_type", "enterprise"), params.get("scope_id")))
            elif path == "/api/agent/ai-assistant/feedback":
                self._require_agent_admin()
                self._ok(STORE.list_ai_assistant_feedback())
            elif path == "/api/agent/tasks":
                user = self._require_user()
                self._ok(STORE.list_tasks(params.get("file_id"), params.get("case_id"), params.get("status"), user["id"]))
            elif path.startswith("/api/agent/tasks/"):
                user = self._require_user()
                task_id = path.rsplit("/", 1)[-1]
                STORE.require_task_access(task_id, user["id"])
                self._ok(STORE.get_task(task_id))
            elif path == "/api/agent/cases":
                user = self._require_user()
                self._ok(STORE.list_cases(user["id"]))
            elif path == "/api/agent/files":
                user = self._require_user()
                if params.get("knowledge_base_id"):
                    STORE.require_knowledge_base_access(params["knowledge_base_id"], user["id"], "view")
                    files = [
                        item
                        for item in STORE.list_files(knowledge_base_id=params.get("knowledge_base_id"), folder_id=params.get("folder_id"))
                        if STORE.has_resource_access("file", item["id"], user["id"], "view")
                    ]
                    self._ok(files)
                elif params.get("case_id"):
                    STORE.require_case_access(params["case_id"], user["id"])
                    self._ok(STORE.list_files(params.get("case_id")))
                else:
                    self._ok(STORE.list_files_for_user(user["id"]))
            elif path.startswith("/api/agent/files/") and path.endswith("/native-preview"):
                user = self._require_user()
                file_id = path.split("/")[-2]
                self._ok(STORE.native_preview_status(file_id, user["id"]))
            elif path.startswith("/api/agent/files/") and path.endswith("/preview"):
                user = self._require_user()
                file_id = path.split("/")[-2]
                self._ok(STORE.preview_file(file_id, user["id"], int(params.get("chunk_limit", 8)), int(params.get("text_limit", 6000))))
            elif path.startswith("/api/agent/files/") and path.endswith("/content"):
                user = self._require_user()
                file_id = path.split("/")[-2]
                watermark, content, content_type = STORE.file_content_for_preview(file_id, user["id"])
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Content-Disposition", f'inline; filename="{watermark["file_name"]}"')
                self.send_header("X-Agent-Watermark", watermark["watermark_text"])
                self.send_header("X-Agent-Watermark-Id", watermark["id"])
                self.send_header("X-Agent-Watermark-File-Id", watermark["file_id"])
                self.send_header("X-Agent-Watermark-Action", watermark["action"])
                self.end_headers()
                self.wfile.write(content)
            elif path == "/api/agent/audit-logs":
                self._require_user()
                self._ok(STORE.audit_logs())
            elif path == "/api/agent/permissions/resource":
                user = self._require_user()
                self._ok(STORE.list_resource_permissions(params["resource_type"], params["resource_id"], user["id"]))
            elif path == "/api/agent/permissions/effective":
                user = self._require_user()
                self._ok(STORE.effective_permissions(params["resource_type"], params["resource_id"], user["id"], params.get("user_id")))
            elif path == "/api/agent/chats":
                user = self._require_user()
                if params.get("case_id"):
                    STORE.require_case_access(params["case_id"], user["id"])
                    self._ok(STORE.list_chats(params.get("case_id")))
                else:
                    self._ok(STORE.list_chats_for_user(user["id"]))
            elif path.startswith("/api/agent/chats/"):
                user = self._require_user()
                session_id = path.rsplit("/", 1)[-1]
                self._ok(STORE.get_chat_messages(session_id, user["id"]))
            elif path == "/api/agent/evidences":
                user = self._require_user()
                self._ok(STORE.list_evidences_for_user(params["case_id"], user["id"]))
            elif path == "/":
                html_doc = """<html><head><title>Agent Console</title></head><body><h1>Agent 本地管理台</h1><p>当前页面运行在律师本地 Agent，业务数据仅保存在本地，平台不可见。</p><ul><li>/api/agent/cases</li><li>/api/agent/files?case_id=...</li><li>/api/agent/rag/query</li></ul></body></html>"""
                self._send(200, html_doc.encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._error(404, "not found")
        except CaseAccessError as exc:
            self._error(403, str(exc))
        except PreviewContentBlockedError as exc:
            self._error(403, str(exc))
        except PermissionError as exc:
            self._error(401, str(exc))
        except PreviewContentNotReadyError as exc:
            self._error(409, str(exc))
        except Exception as exc:
            self._error(400, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._json()
            if self.path == "/api/agent/setup/admin":
                self._ok(STORE.setup_admin(payload))
            elif self.path == "/api/agent/auth/login":
                self._ok(STORE.login(str(payload["account"]), str(payload["password"])))
            elif self.path == "/api/agent/auth/logout":
                self._ok(STORE.logout(self._bearer_token()))
            elif self.path == "/api/agent/activate":
                self._require_user()
                tenant_id = payload["tenant_id"]
                agent_id = payload.get("agent_id", new_id("ag"))
                STORE.set_config("tenant_id", tenant_id)
                STORE.set_config("agent_id", agent_id)
                license_key_hash = payload["license_key_hash"]
                result = post_json(
                    f"{PLATFORM_BASE_URL}/api/platform/agents/register",
                    {
                        "tenant_id": tenant_id,
                        "agent_id": agent_id,
                        "agent_version": "4.1.0-mvp",
                        "install_fingerprint": "local-mvp",
                        "license_key_hash": license_key_hash,
                    },
                )
                self._ok({"agent_id": agent_id, "platform_result": result})
            elif self.path == "/api/agent/report-health":
                self._require_user()
                result = post_json(f"{PLATFORM_BASE_URL}/api/platform/agents/health", STORE.health_payload())
                self._ok(result)
            elif self.path == "/api/agent/data-sources/check-permission":
                self._require_user()
                self._ok(STORE.check_directory_permission(payload["path"]))
            elif self.path == "/api/agent/data-sources":
                self._require_user()
                self._ok(STORE.add_data_source(payload["path"]))
            elif self.path == "/api/agent/knowledge-bases":
                user = self._require_user()
                self._ok(STORE.create_knowledge_base(payload, user["id"]))
            elif self.path.startswith("/api/agent/knowledge-bases/") and self.path.endswith("/archive"):
                user = self._require_user()
                kb_id = self.path.split("/")[-2]
                self._ok(STORE.archive_knowledge_base(kb_id, user["id"]))
            elif self.path.startswith("/api/agent/knowledge-bases/") and self.path.endswith("/revoke"):
                user = self._require_user()
                parts = self.path.split("/")
                self._ok(STORE.revoke_knowledge_base_member(parts[4], parts[6], user["id"]))
            elif self.path.startswith("/api/agent/knowledge-bases/") and self.path.endswith("/members"):
                user = self._require_user()
                kb_id = self.path.split("/")[-2]
                self._ok(STORE.grant_knowledge_base_member(kb_id, payload, user["id"]))
            elif self.path == "/api/agent/folders":
                user = self._require_user()
                self._ok(STORE.create_folder(payload, user["id"]))
            elif self.path.startswith("/api/agent/folders/") and self.path.endswith("/restore"):
                user = self._require_user()
                folder_id = self.path.split("/")[-2]
                self._ok(STORE.restore_folder(folder_id, user["id"]))
            elif self.path == "/api/agent/permissions/grant":
                user = self._require_user()
                self._ok(STORE.set_acl_entry(payload, user["id"], "allow"))
            elif self.path == "/api/agent/permissions/deny":
                user = self._require_user()
                self._ok(STORE.set_acl_entry(payload, user["id"], "deny"))
            elif self.path == "/api/agent/permissions/check":
                user = self._require_user()
                target_user_id = str(payload.get("user_id", user["id"]))
                action = str(payload.get("action", "view"))
                allowed = STORE.has_resource_access(str(payload["resource_type"]), str(payload["resource_id"]), target_user_id, action)
                self._ok({"allowed": allowed, "user_id": target_user_id, "action": action})
            elif self.path == "/api/agent/users":
                user = self._require_agent_admin()
                self._ok(STORE.create_user(payload, user["id"]))
            elif self.path.startswith("/api/agent/users/") and self.path.endswith("/disable"):
                user = self._require_agent_admin()
                user_id = self.path.split("/")[-2]
                self._ok(STORE.disable_user(user_id, user["id"]))
            elif self.path.startswith("/api/agent/users/") and self.path.endswith("/reset-password"):
                user = self._require_agent_admin()
                user_id = self.path.split("/")[-2]
                self._ok(STORE.reset_user_password(user_id, str(payload.get("password", "")), user["id"]))
            elif self.path == "/api/agent/case-members":
                user = self._require_agent_admin()
                self._ok(STORE.grant_case_member(payload, user["id"]))
            elif self.path.startswith("/api/agent/case-members/") and self.path.endswith("/revoke"):
                user = self._require_agent_admin()
                member_id = self.path.split("/")[-2]
                self._ok(STORE.revoke_case_member(member_id, user["id"]))
            elif self.path == "/api/agent/enterprise/profile":
                user = self._require_agent_admin()
                self._ok(STORE.save_enterprise_profile(payload, user["id"]))
            elif self.path == "/api/agent/organization/units":
                user = self._require_agent_admin()
                self._ok(STORE.create_organization_unit(payload, user["id"]))
            elif self.path == "/api/agent/organization/members":
                user = self._require_agent_admin()
                self._ok(STORE.assign_organization_member(payload, user["id"]))
            elif self.path == "/api/agent/external-org/integrations":
                user = self._require_agent_admin()
                self._ok(STORE.save_external_org_integration(payload, user["id"]))
            elif self.path.startswith("/api/agent/external-org/integrations/") and self.path.endswith("/sync"):
                user = self._require_agent_admin()
                provider = self.path.split("/")[-2]
                self._ok(STORE.simulate_external_org_sync(provider, user["id"]))
            elif self.path == "/api/agent/ai-assistant/settings":
                user = self._require_agent_admin()
                self._ok(STORE.save_ai_assistant_setting(payload, user["id"]))
            elif self.path == "/api/agent/ai-assistant/feedback":
                user = self._require_user()
                self._ok(STORE.create_ai_assistant_feedback(payload, user["id"]))
            elif self.path.startswith("/api/agent/data-sources/") and self.path.endswith("/scan"):
                user = self._require_user()
                if payload.get("case_id"):
                    STORE.require_case_access(payload["case_id"], user["id"])
                data_source_id = self.path.split("/")[-2]
                self._ok(STORE.scan_data_source(data_source_id, payload.get("case_id"), payload.get("knowledge_base_id"), payload.get("folder_id"), user["id"]))
            elif self.path == "/api/agent/model-configs":
                self._require_user()
                self._ok(STORE.save_model_config(payload))
            elif self.path.startswith("/api/agent/model-configs/") and self.path.endswith("/test-chat"):
                self._require_user()
                config_id = self.path.split("/")[-2]
                self._ok(STORE.test_model_config(config_id, "chat"))
            elif self.path.startswith("/api/agent/model-configs/") and self.path.endswith("/test-embedding"):
                self._require_user()
                config_id = self.path.split("/")[-2]
                self._ok(STORE.test_model_config(config_id, "embedding"))
            elif self.path == "/api/agent/tasks/run-pending":
                self._require_agent_admin()
                self._ok(STORE.run_pending_tasks(int(payload.get("limit", 20))))
            elif self.path == "/api/agent/worker/run-once":
                self._require_agent_admin()
                self._ok(
                    STORE.run_worker_once(
                        int(payload.get("batch_size", WORKER_BATCH_SIZE)),
                        int(payload.get("max_retries", WORKER_MAX_RETRIES)),
                        bool(payload.get("sync_qdrant", True)),
                    )
                )
            elif self.path == "/api/agent/vector-store/sync-qdrant":
                self._require_user()
                self._ok(STORE.sync_qdrant_vectors(int(payload.get("limit", 500)), payload.get("case_id")))
            elif self.path.startswith("/api/agent/tasks/") and self.path.endswith("/retry"):
                user = self._require_user()
                task_id = self.path.split("/")[-2]
                STORE.require_task_access(task_id, user["id"])
                self._ok(STORE.retry_task(task_id))
            elif self.path == "/api/agent/cases":
                user = self._require_user()
                payload.setdefault("owner_id", user["id"])
                self._ok(STORE.create_case(payload))
            elif self.path == "/api/agent/files/upload":
                user = self._require_user()
                if payload.get("case_id"):
                    STORE.require_case_access(payload["case_id"], user["id"])
                self._ok(STORE.save_uploaded_file(payload.get("case_id"), payload["file_name"], payload["content_base64"], payload.get("knowledge_base_id"), payload.get("folder_id"), user["id"]))
            elif self.path == "/api/agent/files/parse":
                user = self._require_user()
                STORE.require_file_access(payload["file_id"], user["id"], "edit")
                self._ok(STORE.parse_file(payload["file_id"]))
            elif self.path.startswith("/api/agent/files/") and self.path.endswith("/native-preview/run"):
                user = self._require_user()
                file_id = self.path.split("/")[-3]
                self._ok(STORE.run_native_preview(file_id, user["id"]))
            elif self.path.startswith("/api/agent/files/") and self.path.endswith("/restore"):
                user = self._require_user()
                file_id = self.path.split("/")[-2]
                self._ok(STORE.restore_file(file_id, user["id"]))
            elif self.path == "/api/agent/ai/query":
                user = self._require_user()
                self._ok(STORE.ai_query(payload, user["id"]))
            elif self.path == "/api/agent/ai/scenario-query":
                user = self._require_user()
                self._ok(STORE.scenario_query(payload, user["id"]))
            elif self.path == "/api/agent/rag/query":
                user = self._require_user()
                if payload.get("knowledge_base_id"):
                    self._ok(STORE.ask_knowledge_base(payload["knowledge_base_id"], payload["question"], user["id"]))
                else:
                    self._ok(STORE.ask(payload["case_id"], payload["question"], user["id"]))
            elif self.path == "/api/agent/cases/summary":
                user = self._require_user()
                STORE.require_case_access(payload["case_id"], user["id"])
                self._ok(STORE.create_summary(payload["case_id"]))
            elif self.path == "/api/agent/evidences":
                user = self._require_user()
                STORE.require_case_access(payload["case_id"], user["id"])
                self._ok(STORE.create_evidence(payload))
            else:
                self._error(404, "not found")
        except KeyError as exc:
            self._error(400, f"missing field: {exc}")
        except CaseAccessError as exc:
            self._error(403, str(exc))
        except PermissionError as exc:
            self._error(401, str(exc))
        except Exception as exc:
            self._error(400, str(exc))

    def do_PATCH(self) -> None:  # noqa: N802
        try:
            payload = self._json()
            if self.path.startswith("/api/agent/knowledge-bases/"):
                user = self._require_user()
                kb_id = self.path.rsplit("/", 1)[-1]
                self._ok(STORE.update_knowledge_base(kb_id, payload, user["id"]))
            elif self.path.startswith("/api/agent/folders/"):
                user = self._require_user()
                folder_id = self.path.rsplit("/", 1)[-1]
                self._ok(STORE.update_folder(folder_id, payload, user["id"]))
            elif self.path.startswith("/api/agent/files/"):
                user = self._require_user()
                file_id = self.path.rsplit("/", 1)[-1]
                self._ok(STORE.update_file(file_id, payload, user["id"]))
            else:
                self._error(404, "not found")
        except KeyError as exc:
            self._error(400, f"missing field: {exc}")
        except CaseAccessError as exc:
            self._error(403, str(exc))
        except PermissionError as exc:
            self._error(401, str(exc))
        except Exception as exc:
            self._error(400, str(exc))

    def do_DELETE(self) -> None:  # noqa: N802
        try:
            if self.path.startswith("/api/agent/permissions/"):
                user = self._require_user()
                entry_id = self.path.rsplit("/", 1)[-1]
                self._ok(STORE.delete_acl_entry(entry_id, user["id"]))
            elif self.path.startswith("/api/agent/folders/"):
                user = self._require_user()
                folder_id = self.path.rsplit("/", 1)[-1]
                self._ok(STORE.soft_delete_folder(folder_id, user["id"]))
            elif self.path.startswith("/api/agent/knowledge-bases/"):
                user = self._require_user()
                kb_id = self.path.rsplit("/", 1)[-1]
                self._ok(STORE.soft_delete_knowledge_base(kb_id, user["id"]))
            elif self.path.startswith("/api/agent/files/"):
                user = self._require_user()
                file_id = self.path.rsplit("/", 1)[-1]
                self._ok(STORE.soft_delete_file(file_id, user["id"]))
            else:
                self._error(404, "not found")
        except KeyError as exc:
            self._error(400, f"missing field: {exc}")
        except CaseAccessError as exc:
            self._error(403, str(exc))
        except PermissionError as exc:
            self._error(401, str(exc))
        except Exception as exc:
            self._error(400, str(exc))

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")


def main() -> None:
    if "--worker" in sys.argv:
        print(f"agent-worker running batch_size={WORKER_BATCH_SIZE} sleep={WORKER_SLEEP_SECONDS}s max_retries={WORKER_MAX_RETRIES}")
        while True:
            result = STORE.run_worker_once(WORKER_BATCH_SIZE, WORKER_MAX_RETRIES, sync_qdrant=True)
            print(json.dumps(result, ensure_ascii=False))
            time.sleep(WORKER_SLEEP_SECONDS)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"agent-api listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
