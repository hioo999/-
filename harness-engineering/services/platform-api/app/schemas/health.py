"""Whitelisted platform health payload fields."""

from __future__ import annotations


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

REGISTER_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {"tenant_id", "agent_id", "agent_version", "install_fingerprint", "license_key_hash"}
)

HEARTBEAT_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {"tenant_id", "agent_id", "agent_version", "status", "last_heartbeat"}
)
