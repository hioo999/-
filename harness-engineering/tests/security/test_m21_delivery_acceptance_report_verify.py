#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class M21DeliveryAcceptanceReportVerifyTest(unittest.TestCase):
    def run_verifier(self, report: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/verify-delivery-acceptance-report.py", "--report", str(report)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def make_report(self, tmp: str) -> tuple[Path, dict]:
        archive = Path(tmp) / "delivery.tar.gz"
        report_path = Path(tmp) / "report.json"
        export = subprocess.run(
            ["python3", "scripts/export-delivery-package.py", "--output", str(archive)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(export.returncode, 0, export.stderr or export.stdout)
        report = subprocess.run(
            ["python3", "scripts/export-delivery-acceptance-report.py", "--archive", str(archive), "--output", str(report_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(report.returncode, 0, report.stderr or report.stdout)
        return report_path, json.loads(report_path.read_text("utf-8"))

    def write_mutated(self, tmp: str, report: dict) -> Path:
        path = Path(tmp) / "mutated-report.json"
        path.write_text(json.dumps(report), "utf-8")
        return path

    def test_valid_report_passes_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path, _ = self.make_report(tmp)
            completed = self.run_verifier(report_path)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertIn("delivery acceptance report verification passed", completed.stdout)

    def test_verifier_rejects_missing_required_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, report = self.make_report(tmp)
            mutated = copy.deepcopy(report)
            mutated["checks"] = [check for check in mutated["checks"] if check["name"] != "delivery_package_boundary"]
            completed = self.run_verifier(self.write_mutated(tmp, mutated))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("missing required checks", completed.stderr)

    def test_verifier_rejects_missing_extract_smoke_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, report = self.make_report(tmp)
            mutated = copy.deepcopy(report)
            for check in mutated["checks"]:
                if check["name"] == "delivery_archive_verification":
                    check["command"] = check["command"].replace(" --extract-smoke", "")
            completed = self.run_verifier(self.write_mutated(tmp, mutated))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("archive verification missing --extract-smoke", completed.stderr)

    def test_verifier_rejects_redaction_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, report = self.make_report(tmp)
            mutated = copy.deepcopy(report)
            mutated["redaction"]["business_data_exported"] = True
            completed = self.run_verifier(self.write_mutated(tmp, mutated))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("business_data_exported must be false", completed.stderr)

    def test_verifier_rejects_missing_v5_p0_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, report = self.make_report(tmp)
            mutated = copy.deepcopy(report)
            mutated.pop("v5_p0_evidence")
            completed = self.run_verifier(self.write_mutated(tmp, mutated))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("v5_p0_evidence must be object", completed.stderr)

    def test_verifier_rejects_incomplete_v5_p0_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, report = self.make_report(tmp)
            mutated = copy.deepcopy(report)
            mutated["v5_p0_evidence"]["evidence_items"] = [
                item for item in mutated["v5_p0_evidence"]["evidence_items"] if item["name"] != "platform_invisibility_special_checks"
            ]
            completed = self.run_verifier(self.write_mutated(tmp, mutated))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("missing v5_p0_evidence items", completed.stderr)

    def test_verify_mvp_invokes_report_verifier(self) -> None:
        script = (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8")
        self.assertIn("scripts/verify-delivery-acceptance-report.py", script)


if __name__ == "__main__":
    unittest.main()
