"""Credential handling helpers for M2 scaffold.

This file intentionally avoids fake reversible encryption. The current helper
only supports display masking and explicit runtime failure for encryption until
AES-GCM/Fernet is wired with a deployment-provided master key.
"""

from __future__ import annotations


SECRET_KEYS = ("api_key", "password", "db_password", "ssh_key", "token_secret")


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def assert_no_plaintext_secret(payload: dict[str, object]) -> None:
    leaked = [key for key, value in payload.items() if key in SECRET_KEYS and value]
    if leaked:
        raise ValueError(f"plaintext secret fields are not allowed in this payload: {sorted(leaked)}")


def encrypt_secret(_: str) -> str:
    raise NotImplementedError("Wire AES-GCM or Fernet with AGENT_MASTER_KEY before storing secrets")
