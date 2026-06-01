#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class M18DeliveryScriptsTest(unittest.TestCase):
    def test_verify_mvp_script_has_valid_shell_syntax(self) -> None:
        completed = subprocess.run(
            ["bash", "-n", "scripts/verify-mvp.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_deploy_config_validator_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/validate-deploy-config.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_artifact_scanner_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/scan-delivery-artifacts.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_package_checker_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/check-delivery-package.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_package_exporter_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/export-delivery-package.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_package_verifier_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/verify-delivery-package.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_acceptance_reporter_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/export-delivery-acceptance-report.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_acceptance_report_verifier_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/verify-delivery-acceptance-report.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_bundle_exporter_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/export-delivery-bundle.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_bundle_verifier_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/verify-delivery-bundle.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_acceptance_report_scanner_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/scan-delivery-acceptance-report.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_extracted_bundle_smoke_has_valid_python_syntax(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", "scripts/smoke-delivery-bundle-extract.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_delivery_docs_reference_final_verification_entrypoint(self) -> None:
        readme = (ROOT / "README.md").read_text("utf-8")
        deploy_readme = (ROOT / "deploy" / "README.md").read_text("utf-8")
        self.assertIn("bash scripts/verify-mvp.sh", readme)
        self.assertIn("bash scripts/verify-mvp.sh", deploy_readme)
        self.assertIn("scripts/validate-deploy-config.py", readme)
        self.assertIn("scripts/validate-deploy-config.py", deploy_readme)
        self.assertIn("scripts/scan-delivery-artifacts.py", readme)
        self.assertIn("scripts/scan-delivery-artifacts.py", deploy_readme)
        self.assertIn("scripts/check-delivery-package.py", readme)
        self.assertIn("scripts/check-delivery-package.py", deploy_readme)
        self.assertIn("scripts/export-delivery-package.py", readme)
        self.assertIn("scripts/export-delivery-package.py", deploy_readme)
        self.assertIn("scripts/verify-delivery-package.py", readme)
        self.assertIn("scripts/verify-delivery-package.py", deploy_readme)
        self.assertIn("scripts/export-delivery-acceptance-report.py", readme)
        self.assertIn("scripts/export-delivery-acceptance-report.py", deploy_readme)
        self.assertIn("scripts/verify-delivery-acceptance-report.py", readme)
        self.assertIn("scripts/verify-delivery-acceptance-report.py", deploy_readme)
        self.assertIn("scripts/export-delivery-bundle.py", readme)
        self.assertIn("scripts/export-delivery-bundle.py", deploy_readme)
        self.assertIn("scripts/verify-delivery-bundle.py", readme)
        self.assertIn("scripts/verify-delivery-bundle.py", deploy_readme)
        self.assertIn("scripts/scan-delivery-acceptance-report.py", (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8"))

    def test_run_agent_supports_runtime_dry_run_modes(self) -> None:
        stdlib = subprocess.run(
            ["bash", "scripts/run-agent.sh"],
            cwd=ROOT,
            env={"AGENT_RUNTIME": "stdlib", "AGENT_DRY_RUN": "1", "AGENT_PYTHON": "python-test"},
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(stdlib.returncode, 0, stdlib.stderr or stdlib.stdout)
        self.assertIn("python-test", stdlib.stdout)
        self.assertIn("services/agent-api/server.py", stdlib.stdout)

        fastapi = subprocess.run(
            ["bash", "scripts/run-agent.sh"],
            cwd=ROOT,
            env={"AGENT_RUNTIME": "fastapi", "AGENT_DRY_RUN": "1", "AGENT_PYTHON": "python-test"},
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(fastapi.returncode, 0, fastapi.stderr or fastapi.stdout)
        self.assertIn("run-agent-fastapi.sh", fastapi.stdout)

    def test_run_agent_rejects_unknown_runtime(self) -> None:
        completed = subprocess.run(
            ["bash", "scripts/run-agent.sh"],
            cwd=ROOT,
            env={"AGENT_RUNTIME": "unknown", "AGENT_DRY_RUN": "1"},
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("Unsupported AGENT_RUNTIME", completed.stderr)


if __name__ == "__main__":
    unittest.main()
