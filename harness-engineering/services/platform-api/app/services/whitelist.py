"""Platform request whitelist validation service."""

from __future__ import annotations

from typing import Any

from app.schemas.health import HEALTH_ALLOWED_FIELDS, HEARTBEAT_ALLOWED_FIELDS, REGISTER_ALLOWED_FIELDS
from app.security.forbidden_fields import ensure_allowed_fields


def validate_register_payload(payload: dict[str, Any]) -> None:
    ensure_allowed_fields(payload, REGISTER_ALLOWED_FIELDS)


def validate_heartbeat_payload(payload: dict[str, Any]) -> None:
    ensure_allowed_fields(payload, HEARTBEAT_ALLOWED_FIELDS)


def validate_health_payload(payload: dict[str, Any]) -> None:
    ensure_allowed_fields(payload, HEALTH_ALLOWED_FIELDS)
