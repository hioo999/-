#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PlatformInvisibilityRedlineScanTest(unittest.TestCase):
    def run_scanner(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/scan-platform-invisibility-redlines.py", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_scanner_allows_metadata_only_platform_report_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "platform-invisibility-report.json"
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "m19-platform-invisibility-v1",
                        "passed": True,
                        "checks": [
                            {
                                "name": "platform_rejects_forbidden_business_field_probe",
                                "passed": True,
                                "details": {"probe_field": "file_name"},
                            }
                        ],
                        "redaction": {"mode": "metadata_only", "business_data_exported": False},
                    }
                ),
                "utf-8",
            )
            completed = self.run_scanner("--path", str(report))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertIn("platform invisibility redline scan passed", completed.stdout)

    def test_scanner_rejects_forbidden_json_business_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "bad-report.json"
            report.write_text(json.dumps({"schema_version": "x", "file_name": "secret.pdf"}), "utf-8")
            completed = self.run_scanner("--path", str(report))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("forbidden business-data key", completed.stderr)
            self.assertIn("file_name", completed.stderr)

    def test_scanner_rejects_nested_question_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "bad-report.json"
            report.write_text(json.dumps({"v5_p0_evidence": {"test_output": {"question": "business prompt"}}}), "utf-8")
            completed = self.run_scanner("--path", str(report))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("$.v5_p0_evidence.test_output.question", completed.stderr)

    def test_scanner_rejects_secret_value_in_text_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "diagnostics.txt"
            report.write_text("MODEL_API_KEY=sk-thisIsAConcreteSecretValue12345\n", "utf-8")
            completed = self.run_scanner("--path", str(report))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("OpenAI-style API key", completed.stderr)

    def test_strict_text_key_mode_rejects_business_field_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "artifact.txt"
            report.write_text("file_name: secret.pdf\n", "utf-8")
            completed = self.run_scanner("--strict-text-keys", "--path", str(report))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("forbidden business-data text key", completed.stderr)

    def test_verify_mvp_invokes_platform_invisibility_redline_scan(self) -> None:
        script = (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8")
        self.assertIn("scripts/scan-platform-invisibility-redlines.py", script)


if __name__ == "__main__":
    unittest.main()
