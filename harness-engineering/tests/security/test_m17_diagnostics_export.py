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


def seed_sensitive_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE case_spaces (id TEXT, title TEXT)")
        conn.execute("CREATE TABLE local_files (id TEXT, case_id TEXT, file_name TEXT, file_path TEXT, process_status TEXT)")
        conn.execute("CREATE TABLE document_chunks (id TEXT, chunk_text TEXT)")
        conn.execute("CREATE TABLE chat_messages (id TEXT, content TEXT)")
        conn.execute("CREATE TABLE processing_tasks (id TEXT, status TEXT, error_code TEXT)")
        conn.execute("CREATE TABLE model_configs (id TEXT, api_key_encrypted TEXT)")
        conn.execute("INSERT INTO case_spaces VALUES ('case_1', 'Secret Case Name')")
        conn.execute("INSERT INTO local_files VALUES ('file_1', 'case_1', 'secret-contract.txt', '/tmp/secret-contract.txt', 'indexed')")
        conn.execute("INSERT INTO document_chunks VALUES ('chunk_1', '乙方已经付款。')")
        conn.execute("INSERT INTO chat_messages VALUES ('msg_1', '乙方是否付款？')")
        conn.execute("INSERT INTO processing_tasks VALUES ('task_1', 'success', NULL)")
        conn.execute("INSERT INTO model_configs VALUES ('model_1', 'sk-secret-value')")
        conn.commit()
    finally:
        conn.close()


class M17DiagnosticsExportTest(unittest.TestCase):
    def test_diagnostics_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "agent.db"
            seed_sensitive_db(db_path)
            output_dir = Path(tmp) / "diagnostics"
            completed = subprocess.run(
                [sys.executable, "scripts/export-diagnostics.py", "--db", str(db_path), "--output-dir", str(output_dir)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 3)
            self.assertIn("whitelist_only", completed.stdout)
            self.assertIn("without --confirm", completed.stderr)
            self.assertFalse(output_dir.exists())

    def test_diagnostics_exports_only_whitelisted_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "agent.db"
            seed_sensitive_db(db_path)
            output_dir = Path(tmp) / "diagnostics"
            completed = subprocess.run(
                [sys.executable, "scripts/export-diagnostics.py", "--db", str(db_path), "--output-dir", str(output_dir), "--confirm"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            bundle_path = Path(completed.stdout.strip())
            bundle_text = bundle_path.read_text("utf-8")
            payload = json.loads(bundle_text)

            self.assertEqual(payload["schema_version"], "m17-diagnostics-v1")
            self.assertEqual(payload["database"]["table_counts"]["case_spaces"], 1)
            self.assertEqual(payload["database"]["task_status_counts"], {"success": 1})
            self.assertEqual(payload["database"]["file_status_counts"], {"indexed": 1})
            self.assertEqual(payload["database"]["model_secret_configured_count"], 1)

            forbidden_values = [
                "Secret Case Name",
                "secret-contract.txt",
                "/tmp/secret-contract.txt",
                "乙方已经付款",
                "乙方是否付款",
                "sk-secret-value",
            ]
            for value in forbidden_values:
                self.assertNotIn(value, bundle_text)


if __name__ == "__main__":
    unittest.main()
