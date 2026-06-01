#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def add_text(archive: tarfile.TarFile, name: str, text: str) -> None:
    data = text.encode("utf-8")
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = 0
    info.mode = 0o644
    archive.addfile(info, io.BytesIO(data))


def write_archive(path: Path, files: dict[str, str], manifest_files: list[str] | None = None) -> None:
    included = manifest_files if manifest_files is not None else [name.split("/", 1)[1] for name in files if not name.endswith("/DELIVERY-MANIFEST.json")]
    manifest = {
        "schema_version": "m21-delivery-package-archive-v1",
        "included_count": len(included),
        "excluded_count": 0,
        "included_files": included,
    }
    with tarfile.open(path, "w:gz") as archive:
        add_text(archive, "harness-engineering/DELIVERY-MANIFEST.json", json.dumps(manifest))
        for name, text in files.items():
            add_text(archive, name, text)


def required_extract_files(verifier_text: str = "print('fake verifier ok')\n") -> dict[str, str]:
    return {
        "harness-engineering/README.md": "ok\n",
        "harness-engineering/deploy/README.md": "ok\n",
        "harness-engineering/deploy/docker-compose.agent.yml": "services: {}\n",
        "harness-engineering/deploy/docker-compose.platform.yml": "services: {}\n",
        "harness-engineering/scripts/verify-mvp.sh": "#!/usr/bin/env bash\n",
        "harness-engineering/scripts/export-delivery-package.py": "print('fake exporter')\n",
        "harness-engineering/scripts/verify-delivery-package.py": verifier_text,
    }


class M21DeliveryPackageVerifyTest(unittest.TestCase):
    def run_verifier(self, archive: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "scripts/verify-delivery-package.py", "--archive", str(archive)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_exported_default_archive_passes_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            export = subprocess.run(
                ["python3", "scripts/export-delivery-package.py", "--output", str(archive)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(export.returncode, 0, export.stderr or export.stdout)
            completed = self.run_verifier(archive)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertIn("delivery package verification passed", completed.stdout)

    def test_exported_default_archive_passes_required_checksum_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            export = subprocess.run(
                ["python3", "scripts/export-delivery-package.py", "--output", str(archive)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(export.returncode, 0, export.stderr or export.stdout)
            completed = subprocess.run(
                ["python3", "scripts/verify-delivery-package.py", "--archive", str(archive), "--require-checksum"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_exported_default_archive_passes_extract_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            export = subprocess.run(
                ["python3", "scripts/export-delivery-package.py", "--output", str(archive)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(export.returncode, 0, export.stderr or export.stdout)
            completed = subprocess.run(
                ["python3", "scripts/verify-delivery-package.py", "--archive", str(archive), "--require-checksum", "--extract-smoke"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_extract_smoke_rejects_missing_required_entry_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            write_archive(archive, {"harness-engineering/README.md": "ok\n"})
            completed = subprocess.run(
                ["python3", "scripts/verify-delivery-package.py", "--archive", str(archive), "--extract-smoke"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("extracted package missing required file", completed.stderr)

    def test_extract_smoke_rejects_failed_post_extract_reverify_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            write_archive(
                archive,
                required_extract_files("import sys\nprint('fake verifier failed', file=sys.stderr)\nsys.exit(1)\n"),
            )
            completed = subprocess.run(
                ["python3", "scripts/verify-delivery-package.py", "--archive", str(archive), "--extract-smoke"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("post-extract reverify command failed", completed.stderr)
            self.assertIn("fake verifier failed", completed.stderr)

    def test_verifier_rejects_missing_required_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            write_archive(archive, {"harness-engineering/README.md": "ok\n"})
            completed = subprocess.run(
                ["python3", "scripts/verify-delivery-package.py", "--archive", str(archive), "--require-checksum"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("checksum file does not exist", completed.stderr)

    def test_verifier_rejects_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            export = subprocess.run(
                ["python3", "scripts/export-delivery-package.py", "--output", str(archive)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(export.returncode, 0, export.stderr or export.stdout)
            with archive.open("ab") as handle:
                handle.write(b"tampered")
            completed = subprocess.run(
                ["python3", "scripts/verify-delivery-package.py", "--archive", str(archive), "--require-checksum"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("checksum mismatch", completed.stderr)

    def test_verifier_rejects_manifest_archive_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            write_archive(archive, {"harness-engineering/README.md": "ok\n"}, manifest_files=["README.md", "missing.txt"])
            completed = self.run_verifier(archive)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("manifest/archive mismatch", completed.stderr)

    def test_verifier_rejects_runtime_database_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            write_archive(archive, {"harness-engineering/services/agent-api/data/agent.db": "db\n"})
            completed = self.run_verifier(archive)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("forbidden directory included", completed.stderr)

    def test_verifier_rejects_path_traversal_member(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "delivery.tar.gz"
            write_archive(archive, {"harness-engineering/../README.md": "bad\n"}, manifest_files=["../README.md"])
            completed = self.run_verifier(archive)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("archive path traversal", completed.stderr)

    def test_verify_mvp_invokes_delivery_package_verifier(self) -> None:
        script = (ROOT / "scripts" / "verify-mvp.sh").read_text("utf-8")
        self.assertIn("scripts/verify-delivery-package.py", script)
        self.assertIn("--extract-smoke", script)


if __name__ == "__main__":
    unittest.main()
