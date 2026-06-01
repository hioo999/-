#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class M21DeliveryArtifactScanTest(unittest.TestCase):
    def run_scanner(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/scan-delivery-artifacts.py", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_default_delivery_artifacts_pass_scan(self) -> None:
        completed = self.run_scanner()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("delivery artifact scan passed", completed.stdout)

    def test_scanner_rejects_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            path.write_text("MODEL_API_KEY=sk-thisIsAConcreteSecretValue12345\n", "utf-8")
            completed = self.run_scanner("--path", str(path))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("OpenAI-style API key", completed.stderr)

    def test_scanner_rejects_personal_workstation_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "delivery.md"
            path.write_text("Sample source: /Users/alice/cases/secret-contract.pdf\n", "utf-8")
            completed = self.run_scanner("--path", str(path))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("personal macOS path", completed.stderr)

    def test_scanner_rejects_seeded_case_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diagnostics.txt"
            path.write_text("Secret Case Name should never be shipped\n", "utf-8")
            completed = self.run_scanner("--path", str(path))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("seeded sensitive case text", completed.stderr)

    def test_scanner_rejects_database_url_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deploy.yml"
            path.write_text("DATABASE_URL=postgresql://agent:realPassword123@localhost:5432/agent\n", "utf-8")
            completed = self.run_scanner("--path", str(path))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("database URL contains concrete password", completed.stderr)

    def test_verify_mvp_invokes_delivery_artifact_scan(self) -> None:
        script = (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8")
        self.assertIn("scripts/scan-delivery-artifacts.py", script)


if __name__ == "__main__":
    unittest.main()
