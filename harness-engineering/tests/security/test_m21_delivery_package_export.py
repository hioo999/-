#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class M21DeliveryPackageExportTest(unittest.TestCase):
    def run_exporter(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/export-delivery-package.py", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_default_delivery_package_export_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "harness-engineering-delivery.tar.gz"
            completed = self.run_exporter("--output", str(output))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertTrue(output.exists())
            self.assertTrue(output.with_name(output.name + ".sha256").exists())
            self.assertGreater(output.stat().st_size, 0)
            with tarfile.open(output, "r:gz") as archive:
                names = archive.getnames()
            self.assertIn("harness-engineering/DELIVERY-MANIFEST.json", names)
            self.assertIn("harness-engineering/README.md", names)

    def test_export_writes_matching_sha256_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "harness-engineering-delivery.tar.gz"
            completed = self.run_exporter("--output", str(output))
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            checksum_path = output.with_name(output.name + ".sha256")
            checksum_text = checksum_path.read_text("utf-8").strip()
            digest, filename = checksum_text.split()
            self.assertEqual(filename, output.name)
            self.assertEqual(digest, hashlib.sha256(output.read_bytes()).hexdigest())

    def test_export_reuses_boundary_manifest_and_excludes_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "root"
            root.mkdir()
            (root / "README.md").write_text("delivery root\n", "utf-8")
            (root / "services" / "agent-api" / "data").mkdir(parents=True)
            (root / "services" / "agent-api" / "data" / "agent.db").write_bytes(b"sqlite data")
            (root / "apps" / "agent-console" / "node_modules").mkdir(parents=True)
            (root / "apps" / "agent-console" / "node_modules" / "bundle.js").write_text("dependency\n", "utf-8")
            (root / "deploy").mkdir()
            (root / "deploy" / "env.agent").write_text("AGENT_SECRET_KEY=real-secret\n", "utf-8")
            (root / "deploy" / "env.agent.example").write_text("AGENT_SECRET_KEY=replace-with-secret\n", "utf-8")
            output = tmp_path / "delivery.tar.gz"

            completed = self.run_exporter(
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

            with tarfile.open(output, "r:gz") as archive:
                names = set(archive.getnames())
                manifest_file = archive.extractfile("harness-engineering/DELIVERY-MANIFEST.json")
                assert manifest_file is not None
                manifest = json.loads(manifest_file.read().decode("utf-8"))

            self.assertIn("harness-engineering/README.md", names)
            self.assertIn("harness-engineering/deploy/env.agent.example", names)
            self.assertNotIn("harness-engineering/services/agent-api/data/agent.db", names)
            self.assertNotIn("harness-engineering/apps/agent-console/node_modules/bundle.js", names)
            self.assertNotIn("harness-engineering/deploy/env.agent", names)
            self.assertIn("deploy/env.agent.example", manifest["included_files"])
            self.assertNotIn("deploy/env.agent", manifest["included_files"])

    def test_export_rejects_output_under_project_root_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            (root / "README.md").write_text("delivery root\n", "utf-8")
            output = root / "delivery.tar.gz"
            completed = self.run_exporter("--root", str(root), "--include", "README.md", "--output", str(output))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("output path must be outside the project root", completed.stderr)

    def test_export_is_reproducible_for_same_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "root"
            root.mkdir()
            (root / "README.md").write_text("delivery root\n", "utf-8")
            output_one = tmp_path / "one.tar.gz"
            output_two = tmp_path / "two.tar.gz"

            first = self.run_exporter("--root", str(root), "--include", "README.md", "--output", str(output_one))
            second = self.run_exporter("--root", str(root), "--include", "README.md", "--output", str(output_two))
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
            self.assertEqual(output_one.read_bytes(), output_two.read_bytes())

    def test_verify_mvp_invokes_delivery_package_export(self) -> None:
        script = (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8")
        self.assertIn("scripts/export-delivery-package.py", script)


if __name__ == "__main__":
    unittest.main()
