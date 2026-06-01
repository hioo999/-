#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class M21DeployConfigValidationTest(unittest.TestCase):
    def run_validator(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/validate-deploy-config.py", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_example_deploy_config_passes_security_validation(self) -> None:
        completed = self.run_validator("--mode", "example")
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("deploy config validation passed", completed.stdout)

    def test_production_mode_rejects_placeholder_secrets(self) -> None:
        completed = self.run_validator("--mode", "production")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("still uses placeholder value", completed.stderr)

    def test_agent_compose_rejects_weak_plaintext_database_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            unsafe_compose = tmp_path / "docker-compose.agent.yml"
            source = (ROOT / "deploy" / "docker-compose.agent.yml").read_text("utf-8")
            unsafe_compose.write_text(source.replace("${AGENT_POSTGRES_PASSWORD:-replace-with-agent-postgres-password}", "agent_password"), "utf-8")

            completed = self.run_validator(
                "--mode",
                "example",
                "--agent-compose",
                str(unsafe_compose),
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("weak plaintext secret value 'agent_password'", completed.stderr)

    def test_platform_compose_rejects_data_plane_services(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            unsafe_compose = tmp_path / "docker-compose.platform.yml"
            source = (ROOT / "deploy" / "docker-compose.platform.yml").read_text("utf-8")
            unsafe_compose.write_text(source + "\n  qdrant:\n    image: qdrant/qdrant:v1.9.5\n", "utf-8")

            completed = self.run_validator(
                "--mode",
                "example",
                "--platform-compose",
                str(unsafe_compose),
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("platform compose must not include Agent/data-plane token 'qdrant'", completed.stderr)

    def test_missing_key_security_variable_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            unsafe_env = tmp_path / "env.platform.example"
            source = (ROOT / "deploy" / "env.platform.example").read_text("utf-8")
            unsafe_env.write_text(
                "\n".join(line for line in source.splitlines() if not line.startswith("PLATFORM_JWT_SECRET=")),
                "utf-8",
            )

            completed = self.run_validator(
                "--mode",
                "example",
                "--platform-env",
                str(unsafe_env),
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("missing required key PLATFORM_JWT_SECRET", completed.stderr)


if __name__ == "__main__":
    unittest.main()
