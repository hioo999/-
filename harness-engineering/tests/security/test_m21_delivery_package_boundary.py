#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class M21DeliveryPackageBoundaryTest(unittest.TestCase):
    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/check-delivery-package.py", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_default_delivery_package_boundary_passes(self) -> None:
        completed = self.run_checker()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("delivery package boundary check passed", completed.stdout)

    def test_manifest_excludes_runtime_data_dependencies_and_private_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("delivery root\n", "utf-8")
            (root / "services" / "agent-api" / "data").mkdir(parents=True)
            (root / "services" / "agent-api" / "data" / "agent.db").write_bytes(b"sqlite data")
            (root / "apps" / "agent-console" / "node_modules").mkdir(parents=True)
            (root / "apps" / "agent-console" / "node_modules" / "bundle.js").write_text("dependency\n", "utf-8")
            (root / "deploy").mkdir()
            (root / "deploy" / "env.agent").write_text("AGENT_SECRET_KEY=real-secret\n", "utf-8")
            (root / "deploy" / "env.agent.example").write_text("AGENT_SECRET_KEY=replace-with-secret\n", "utf-8")
            output = root / "manifest.json"

            completed = self.run_checker(
                "--root",
                str(root),
                "--include",
                "README.md",
                "--include",
                "services",
                "--include",
                "apps",
                "--include",
                "deploy",
                "--output",
                str(output),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            payload = json.loads(output.read_text("utf-8"))
            included = set(payload["included_files"])
            self.assertIn("README.md", included)
            self.assertIn("deploy/env.agent.example", included)
            self.assertNotIn("services/agent-api/data/agent.db", included)
            self.assertNotIn("apps/agent-console/node_modules/bundle.js", included)
            self.assertNotIn("deploy/env.agent", included)
            self.assertGreaterEqual(payload["excluded_count"], 3)

    def test_dockerignore_excludes_runtime_artifacts(self) -> None:
        dockerignore = (ROOT / ".dockerignore").read_text("utf-8")
        required_patterns = [
            ".venv-agent-api",
            "node_modules/",
            "services/*/data/",
            "*.db",
            "*.gz",
            "*.sha256",
            ".env",
            "diagnostics/",
            "__pycache__",
        ]
        for pattern in required_patterns:
            self.assertIn(pattern, dockerignore)

    def test_verify_mvp_invokes_delivery_package_boundary_check(self) -> None:
        script = (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8")
        self.assertIn("scripts/check-delivery-package.py", script)


if __name__ == "__main__":
    unittest.main()
