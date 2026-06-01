"""Forbidden business-data field detection for platform APIs.

Platform APIs use a whitelist-first approach and must reject any business data
fields before request bodies reach persistence or logs.
"""

from __future__ import annotations

from typing import Any


FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "case_name",
        "case_title",
        "case_no",
        "cause_of_action",
        "party_name",
        "client_name",
        "file_name",
        "file_path",
        "document_text",
        "raw_text",
        "extracted_text",
        "ocr_text",
        "chunk_text",
        "chunk_content",
        "paragraph_text",
        "embedding",
        "vector",
        "vector_payload",
        "question",
        "answer",
        "prompt",
        "completion",
        "chat_content",
        "citation_text",
        "source_excerpt",
        "original_snippet",
        "draft_content",
        "pleading_text",
        "legal_opinion",
        "note_content",
        "strategy_note",
        "work_memo",
        "database_value",
        "row_data",
        "field_value",
        "table_record",
        "api_key",
        "password",
        "ssh_key",
        "db_password",
        "token_secret",
        "model_request_body",
        "model_response_body",
        "error_message",
    }
)


def find_forbidden_fields(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_FIELDS:
                found.add(key)
            found.update(find_forbidden_fields(child))
    elif isinstance(value, list):
        for child in value:
            found.update(find_forbidden_fields(child))
    return found


def ensure_no_forbidden_fields(value: Any) -> None:
    forbidden = find_forbidden_fields(value)
    if forbidden:
        raise ValueError(f"forbidden business fields: {sorted(forbidden)}")


def ensure_allowed_fields(payload: dict[str, Any], allowed: set[str] | frozenset[str]) -> None:
    ensure_no_forbidden_fields(payload)
    extra = set(payload) - set(allowed)
    if extra:
        raise ValueError(f"fields not in whitelist: {sorted(extra)}")
