"""Model gateway secret handling."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


_PREFIX = "enc:"


def _fernet() -> Fernet:
    raw = (
        os.getenv("MODEL_GATEWAY_SECRET")
        or os.getenv("SECRET_KEY")
        or os.getenv("ADMIN_PASSWORD")
        or "ip-system-local-model-gateway-secret"
    )
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    value = (value or "").strip()
    if not value or value.startswith(_PREFIX):
        return value
    return _PREFIX + _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    value = value or ""
    if not value.startswith(_PREFIX):
        return value
    try:
        return _fernet().decrypt(value.removeprefix(_PREFIX).encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""
