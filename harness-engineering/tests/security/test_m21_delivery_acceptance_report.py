#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class M21DeliveryAcceptanceReportTest(unittest.TestCase):
    def run_reporter(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/export-delivery-acceptance-report.py", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_report_exports_with_temporary_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "delivery-acceptance-report.json"
            completed = self.run_reporter("--output", str(output))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            report = json.loads(output.read_text("utf-8"))

        self.assertEqual(report["schema_version"], "m21-delivery-acceptance-report-v2")
        self.assertTrue(report["passed"])
        self.assertFalse(report["redaction"]["business_data_exported"])
        self.assertFalse(report["redaction"]["archive_file_contents_exported"])
        self.assertIn("sha256", report["archive"])
        self.assertEqual(report["archive"]["manifest"]["included_count"], report["archive"]["manifest"]["included_files_count"])
        self.assertTrue(all(check["passed"] for check in report["checks"]))
        self.assertIn("environment", report)
        self.assertIn("python_version", report["environment"])
        self.assertIn("docker", report["environment"])
        self.assertIn("docker_compose", report["environment"])
        self.assertTrue(report["v5_p0_evidence"]["metadata_only"])
        self.assertFalse(report["v5_p0_evidence"]["business_data_exported"])
        evidence_names = {item["name"] for item in report["v5_p0_evidence"]["evidence_items"]}
        self.assertIn("knowledge_governance_metadata_and_audit", evidence_names)
        self.assertIn("ai_risk_controls_and_policy_enforcement", evidence_names)
        self.assertIn("quality_feedback_closed_loop", evidence_names)
        self.assertIn("historical_citation_and_source_traceability", evidence_names)
        self.assertIn("platform_invisibility_special_checks", evidence_names)
        self.assertIn("delivery_acceptance_package_redaction", evidence_names)
        check_names = {check["name"] for check in report["checks"]}
        self.assertIn("compose_config_platform", check_names)
        self.assertIn("compose_config_agent", check_names)
        archive_verification = [check for check in report["checks"] if check["name"] == "delivery_archive_verification"][0]
        self.assertIn("--extract-smoke", archive_verification["command"])

    def test_report_exports_for_existing_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
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
            completed = self.run_reporter("--archive", str(archive), "--output", str(report_path))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            report = json.loads(report_path.read_text("utf-8"))

        self.assertFalse(report["archive"]["owned_by_report"])
        self.assertTrue(report["archive"]["checksum_exists"])
        self.assertIn("checksum_text", report["archive"])
        compose_checks = [check for check in report["checks"] if check["name"].startswith("compose_config_")]
        self.assertEqual(len(compose_checks), 2)
        self.assertTrue(all("skipped" in check for check in compose_checks))

    def test_report_fails_for_missing_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "missing.tar.gz"
            report_path = Path(tmp) / "report.json"
            completed = self.run_reporter("--archive", str(archive), "--output", str(report_path))
            self.assertEqual(completed.returncode, 1)
            report = json.loads(report_path.read_text("utf-8"))

        self.assertFalse(report["passed"])
        verification = [check for check in report["checks"] if check["name"] == "delivery_archive_verification"][0]
        self.assertFalse(verification["passed"])
        self.assertIn("--extract-smoke", verification["command"])
        self.assertTrue(report["archive"]["exists"] is False)
        self.assertIn("environment", report)

    def test_verify_mvp_invokes_delivery_acceptance_report(self) -> None:
        script = (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8")
        self.assertIn("scripts/export-delivery-acceptance-report.py", script)


if __name__ == "__main__":
    unittest.main()
