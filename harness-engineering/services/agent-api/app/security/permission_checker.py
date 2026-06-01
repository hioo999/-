"""Minimal case-scope permission checks for RAG isolation."""

from __future__ import annotations


def ensure_case_scope(request_case_id: str, resource_case_id: str) -> None:
    if not request_case_id or not resource_case_id or request_case_id != resource_case_id:
        raise PermissionError("resource is outside the current case scope")
