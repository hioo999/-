#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENT_CONSOLE = ROOT / "apps" / "agent-console"


def free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class M21DeliveryRedlineAndExtractSmokeTest(unittest.TestCase):
    def test_acceptance_report_redline_scan_passes_valid_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            report = Path(tmp) / "report.json"
            export = subprocess.run(["python3", "scripts/export-delivery-package.py", "--output", str(archive)], cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(export.returncode, 0, export.stderr or export.stdout)
            report_export = subprocess.run(
                ["python3", "scripts/export-delivery-acceptance-report.py", "--archive", str(archive), "--output", str(report)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(report_export.returncode, 0, report_export.stderr or report_export.stdout)
            scan = subprocess.run(["python3", "scripts/scan-delivery-acceptance-report.py", "--report", str(report)], cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(scan.returncode, 0, scan.stderr or scan.stdout)

    def test_acceptance_report_redline_scan_rejects_business_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            report.write_text(json.dumps({"schema_version": "x", "file_name": "secret.pdf"}), "utf-8")
            scan = subprocess.run(["python3", "scripts/scan-delivery-acceptance-report.py", "--report", str(report)], cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(scan.returncode, 1)
            self.assertIn("forbidden report key", scan.stderr)

    def test_acceptance_report_redline_scan_rejects_nested_v5_p0_business_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "m21-delivery-acceptance-report-v2",
                        "v5_p0_evidence": {
                            "evidence_items": [
                                {
                                    "name": "platform_invisibility_special_checks",
                                    "coverage": ["platform remains control-plane only"],
                                    "tests": ["tests/security/test_m19_platform_invisibility_report.py"],
                                    "acceptance_refs": ["P0-09"],
                                    "test_output": {"question": "must not export user prompt text"},
                                }
                            ]
                        },
                    }
                ),
                "utf-8",
            )
            scan = subprocess.run(["python3", "scripts/scan-delivery-acceptance-report.py", "--report", str(report)], cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(scan.returncode, 1)
            self.assertIn("forbidden report key", scan.stderr)
            self.assertIn("v5_p0_evidence", scan.stderr)

    def test_extracted_bundle_smoke_passes_exported_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = Path(tmp) / "bundle"
            export = subprocess.run(["python3", "scripts/export-delivery-bundle.py", "--output-dir", str(bundle_dir)], cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(export.returncode, 0, export.stderr or export.stdout)
            smoke = subprocess.run(["python3", "scripts/smoke-delivery-bundle-extract.py", "--bundle-dir", str(bundle_dir)], cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(smoke.returncode, 0, smoke.stderr or smoke.stdout)

    def test_platform_console_invisibility_ui_smoke_passes(self) -> None:
        completed = subprocess.run(["node", "apps/platform-console/scripts/check-invisibility-ui.mjs"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_agent_console_browser_smoke_skips_without_browser(self) -> None:
        env = os.environ.copy()
        env["AGENT_CONSOLE_SMOKE_PORT"] = str(free_local_port())
        completed = subprocess.run(["npm", "run", "check:browser-smoke"], cwd=AGENT_CONSOLE, capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertTrue("browser smoke" in completed.stdout)


if __name__ == "__main__":
    unittest.main()
