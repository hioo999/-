#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


platform_forbidden = load_module(
    "platform_forbidden",
    ROOT / "services" / "platform-api" / "app" / "security" / "forbidden_fields.py",
)
health_schema = load_module(
    "health_schema",
    ROOT / "services" / "platform-api" / "app" / "schemas" / "health.py",
)
agent_health = load_module(
    "agent_health",
    ROOT / "services" / "agent-api" / "app" / "services" / "health_reporter.py",
)
permission_checker = load_module(
    "permission_checker",
    ROOT / "services" / "agent-api" / "app" / "security" / "permission_checker.py",
)
credential_crypto = load_module(
    "credential_crypto",
    ROOT / "services" / "agent-api" / "app" / "security" / "credential_crypto.py",
)


class M2SecurityScaffoldTest(unittest.TestCase):
    def test_platform_forbidden_scanner_rejects_nested_business_fields(self) -> None:
        payload = {"tenant_id": "t_1", "nested": {"file_name": "secret.pdf"}}
        self.assertEqual(platform_forbidden.find_forbidden_fields(payload), {"file_name"})

    def test_platform_health_whitelist_rejects_extra_and_business_fields(self) -> None:
        with self.assertRaises(ValueError):
            platform_forbidden.ensure_allowed_fields(
                {"tenant_id": "t_1", "agent_id": "ag_1", "file_name": "secret.pdf"},
                health_schema.HEALTH_ALLOWED_FIELDS,
            )
        with self.assertRaises(ValueError):
            platform_forbidden.ensure_allowed_fields(
                {"tenant_id": "t_1", "agent_id": "ag_1", "extra": "not allowed"},
                health_schema.HEALTH_ALLOWED_FIELDS,
            )

    def test_agent_health_reporter_strips_to_allowed_fields(self) -> None:
        payload = agent_health.to_platform_health_payload(
            {
                "tenant_id": "t_1",
                "agent_id": "ag_1",
                "agent_version": "4.1.0",
                "status": "online",
                "local_only_detail": "not sent",
            }
        )
        self.assertEqual(set(payload), {"tenant_id", "agent_id", "agent_version", "status"})

    def test_agent_health_reporter_rejects_business_keys(self) -> None:
        with self.assertRaises(ValueError):
            agent_health.to_platform_health_payload({"tenant_id": "t_1", "file_name": "secret.pdf"})

    def test_case_scope_permission_guard(self) -> None:
        permission_checker.ensure_case_scope("case_a", "case_a")
        with self.assertRaises(PermissionError):
            permission_checker.ensure_case_scope("case_a", "case_b")

    def test_secret_mask_and_plaintext_guard(self) -> None:
        self.assertEqual(credential_crypto.mask_secret("sk-1234567890"), "sk-1****7890")
        with self.assertRaises(ValueError):
            credential_crypto.assert_no_plaintext_secret({"api_key": "sk-secret"})

    def test_platform_migration_has_no_business_tables(self) -> None:
        sql = (ROOT / "migrations" / "platform" / "001_control_plane.sql").read_text("utf-8")
        for forbidden in ("case_spaces", "local_files", "document_chunks", "chat_messages", "citations"):
            self.assertNotIn(forbidden, sql)


if __name__ == "__main__":
    unittest.main()
