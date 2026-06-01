#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def create_allowed_platform_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE organizations (id TEXT PRIMARY KEY, name TEXT, status TEXT, created_at INTEGER, updated_at INTEGER);
            CREATE TABLE licenses (id TEXT PRIMARY KEY, organization_id TEXT, license_key_hash TEXT, status TEXT, expired_at INTEGER, created_at INTEGER);
            CREATE TABLE agent_instances (id TEXT PRIMARY KEY, organization_id TEXT, license_id TEXT, version TEXT, status TEXT, last_heartbeat_at INTEGER, created_at INTEGER);
            CREATE TABLE agent_heartbeats (id TEXT PRIMARY KEY, agent_id TEXT, status TEXT, task_pending_count INTEGER, task_running_count INTEGER, task_failed_count INTEGER, error_code TEXT, cpu_usage REAL, memory_usage REAL, disk_usage REAL, reported_at INTEGER);
            CREATE TABLE platform_audit_logs (id TEXT PRIMARY KEY, operator_id TEXT, action TEXT, target_type TEXT, target_id TEXT, created_at INTEGER);
            """
        )
        conn.execute("INSERT INTO organizations VALUES ('t_1', '测试律所', 'active', 1, 1)")
        conn.execute("INSERT INTO agent_heartbeats VALUES ('hb_1', 'ag_1', 'online', 1, 0, 0, NULL, 0.1, 0.2, 0.3, 1)")
        conn.commit()
    finally:
        conn.close()


def create_forbidden_platform_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE organizations (id TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE case_spaces (id TEXT PRIMARY KEY, case_name TEXT);
            CREATE TABLE leaked_payloads (id TEXT PRIMARY KEY, file_name TEXT, question TEXT);
            """
        )
        conn.execute("INSERT INTO case_spaces VALUES ('case_1', 'Secret Case')")
        conn.execute("INSERT INTO leaked_payloads VALUES ('leak_1', 'secret.pdf', '案情是什么')")
        conn.commit()
    finally:
        conn.close()


class M19PlatformInvisibilityReportTest(unittest.TestCase):
    def test_report_passes_for_control_plane_only_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "platform.db"
            output = Path(tmp) / "report.json"
            create_allowed_platform_db(db_path)
            completed = subprocess.run(
                [sys.executable, "scripts/export-platform-invisibility-report.py", "--platform-db", str(db_path), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            report = json.loads(output.read_text("utf-8"))
            self.assertTrue(report["passed"])
            self.assertFalse(report["redaction"]["database_values_exported"])
            self.assertEqual(report["row_counts"]["organizations"], 1)
            self.assertIn("platform_rejects_forbidden_business_field_probe", {check["name"] for check in report["checks"]})

    def test_report_fails_for_platform_business_schema_and_redacts_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "platform.db"
            output = Path(tmp) / "report.json"
            create_forbidden_platform_db(db_path)
            completed = subprocess.run(
                [sys.executable, "scripts/export-platform-invisibility-report.py", "--platform-db", str(db_path), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 1)
            report_text = output.read_text("utf-8")
            report = json.loads(report_text)
            self.assertFalse(report["passed"])
            failed = {check["name"] for check in report["checks"] if not check["passed"]}
            self.assertIn("platform_has_no_business_tables", failed)
            self.assertIn("platform_has_no_forbidden_columns", failed)
            self.assertNotIn("Secret Case", report_text)
            self.assertNotIn("secret.pdf", report_text)
            self.assertNotIn("案情是什么", report_text)


if __name__ == "__main__":
    unittest.main()
