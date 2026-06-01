"""Agent health reporter whitelist mapper."""

from __future__ import annotations

from typing import Any


HEALTH_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
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
)

FORBIDDEN_BUSINESS_KEYS: frozenset[str] = frozenset(
    {"case_name", "file_name", "file_path", "question", "answer", "prompt", "api_key", "document_text", "chunk_text"}
)


def to_platform_health_payload(raw: dict[str, Any]) -> dict[str, Any]:
    forbidden = set(raw) & FORBIDDEN_BUSINESS_KEYS
    if forbidden:
        raise ValueError(f"health payload contains forbidden business keys: {sorted(forbidden)}")
    return {key: raw[key] for key in HEALTH_ALLOWED_FIELDS if key in raw}
