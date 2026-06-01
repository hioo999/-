#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
import copy


ROOT = Path(__file__).resolve().parents[2]


class M21DeliveryBundleExportTest(unittest.TestCase):
    def run_bundle(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/export-delivery-bundle.py", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_bundle_export_outputs_all_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "delivery-bundle"
            completed = self.run_bundle("--output-dir", str(output_dir))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            archive = output_dir / "harness-engineering-delivery.tar.gz"
            checksum = output_dir / "harness-engineering-delivery.tar.gz.sha256"
            report = output_dir / "delivery-acceptance-report.json"
            manifest_path = output_dir / "delivery-bundle-manifest.json"
            self.assertTrue(archive.exists())
            self.assertTrue(checksum.exists())
            self.assertTrue(report.exists())
            self.assertTrue(manifest_path.exists())

            manifest = json.loads(manifest_path.read_text("utf-8"))
            self.assertEqual(manifest["schema_version"], "m21-delivery-bundle-v2")
            self.assertTrue(manifest["passed"])
            self.assertTrue(manifest["artifacts"]["archive_exists"])
            self.assertTrue(manifest["artifacts"]["checksum_exists"])
            self.assertTrue(manifest["artifacts"]["acceptance_report_exists"])
            self.assertEqual(manifest["acceptance_report_summary"]["schema_version"], "m21-delivery-acceptance-report-v2")
            self.assertTrue(manifest["acceptance_report_summary"]["metadata_only"])
            self.assertFalse(manifest["acceptance_report_summary"]["business_data_exported"])
            self.assertIn("platform_invisibility_special_checks", manifest["acceptance_report_summary"]["v5_p0_evidence_names"])
            self.assertEqual({step["name"] for step in manifest["steps"]}, {
                "export_delivery_package",
                "verify_delivery_package",
                "export_delivery_acceptance_report",
                "verify_delivery_acceptance_report",
            })
            self.assertTrue(all(step["passed"] for step in manifest["steps"]))

            verify = subprocess.run(
                ["python3", "scripts/verify-delivery-bundle.py", "--manifest", str(manifest_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr or verify.stdout)

    def test_exported_bundle_archive_runs_basic_verification_from_extracted_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "delivery-bundle"
            completed = self.run_bundle("--output-dir", str(output_dir))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            archive_path = output_dir / "harness-engineering-delivery.tar.gz"
            report_path = output_dir / "delivery-acceptance-report.json"
            extract_dir = Path(tmp) / "extracted"
            extract_dir.mkdir()

            with tarfile.open(archive_path, "r:gz") as archive:
                archive.extractall(extract_dir, filter="data")

            roots = [path for path in extract_dir.iterdir() if path.is_dir()]
            self.assertEqual(len(roots), 1)
            extracted_root = roots[0]

            commands = [
                (["python3", "scripts/check-delivery-package.py"], "delivery package boundary check passed"),
                (["python3", "scripts/scan-delivery-artifacts.py"], "delivery artifact scan passed"),
                (
                    ["python3", "scripts/verify-delivery-acceptance-report.py", "--report", str(report_path)],
                    "delivery acceptance report verification passed",
                ),
            ]
            for command, expected_stdout in commands:
                with self.subTest(command=" ".join(command)):
                    result = subprocess.run(
                        command,
                        cwd=extracted_root,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                    self.assertIn(expected_stdout, result.stdout)

    def test_bundle_export_rejects_output_under_project_root_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = ROOT / "delivery-bundle-test-output"
            completed = self.run_bundle("--output-dir", str(output_dir))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("output directory must be outside the project root", completed.stderr)

    def test_bundle_verifier_rejects_missing_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "delivery-bundle"
            completed = self.run_bundle("--output-dir", str(output_dir))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            (output_dir / "harness-engineering-delivery.tar.gz.sha256").unlink()
            verify = subprocess.run(
                ["python3", "scripts/verify-delivery-bundle.py", "--manifest", str(output_dir / "delivery-bundle-manifest.json")],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(verify.returncode, 1)
            self.assertIn("artifact file missing", verify.stderr)

    def test_bundle_verifier_rejects_failed_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "delivery-bundle"
            completed = self.run_bundle("--output-dir", str(output_dir))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            manifest_path = output_dir / "delivery-bundle-manifest.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            mutated = copy.deepcopy(manifest)
            mutated["passed"] = False
            mutated["steps"][0]["passed"] = False
            mutated_path = output_dir / "mutated-bundle-manifest.json"
            mutated["bundle_manifest"] = str(mutated_path)
            mutated_path.write_text(json.dumps(mutated), "utf-8")
            verify = subprocess.run(
                ["python3", "scripts/verify-delivery-bundle.py", "--manifest", str(mutated_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(verify.returncode, 1)
            self.assertIn("step export_delivery_package did not pass", verify.stderr)

    def test_bundle_verifier_rejects_acceptance_summary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "delivery-bundle"
            completed = self.run_bundle("--output-dir", str(output_dir))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            manifest_path = output_dir / "delivery-bundle-manifest.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            mutated = copy.deepcopy(manifest)
            mutated["acceptance_report_summary"]["v5_p0_evidence_names"] = [
                name for name in mutated["acceptance_report_summary"]["v5_p0_evidence_names"] if name != "platform_invisibility_special_checks"
            ]
            mutated["acceptance_report_summary"]["v5_p0_evidence_count"] = len(mutated["acceptance_report_summary"]["v5_p0_evidence_names"])
            mutated_path = output_dir / "mutated-bundle-manifest.json"
            mutated["bundle_manifest"] = str(mutated_path)
            mutated_path.write_text(json.dumps(mutated), "utf-8")
            verify = subprocess.run(
                ["python3", "scripts/verify-delivery-bundle.py", "--manifest", str(mutated_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(verify.returncode, 1)
            self.assertIn("acceptance_report_summary missing V5 P0 evidence", verify.stderr)

    def test_verify_mvp_invokes_delivery_bundle_export(self) -> None:
        script = (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8")
        self.assertIn("scripts/export-delivery-bundle.py", script)
        self.assertIn("scripts/verify-delivery-bundle.py", script)


if __name__ == "__main__":
    unittest.main()
