#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import posixpath
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "scripts" / "check-delivery-package.py"
MANIFEST_NAME = "DELIVERY-MANIFEST.json"
EXPECTED_SCHEMA = "m21-delivery-package-archive-v1"
REQUIRED_EXTRACTED_PATHS = [
    "README.md",
    "deploy/README.md",
    "deploy/docker-compose.agent.yml",
    "deploy/docker-compose.platform.yml",
    "scripts/verify-mvp.sh",
    "scripts/export-delivery-package.py",
    "scripts/verify-delivery-package.py",
]


def load_delivery_checker():
    spec = importlib.util.spec_from_file_location("delivery_package_checker_verify", CHECK_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load delivery checker: {CHECK_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def unsafe_member_reason(name: str) -> str | None:
    path = PurePosixPath(name)
    if path.is_absolute():
        return "absolute archive path"
    if ".." in path.parts:
        return "archive path traversal"
    if not path.parts or path.parts[0] in {"", "."}:
        return "empty archive path"
    return None


def archive_relative_name(name: str) -> str:
    parts = PurePosixPath(name).parts
    if len(parts) < 2:
        return ""
    return posixpath.join(*parts[1:])


def default_checksum_path(archive_path: Path) -> Path:
    return archive_path.with_name(archive_path.name + ".sha256")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_checksum(archive_path: Path, checksum_path: Path, require: bool) -> list[str]:
    if not checksum_path.exists():
        return [f"checksum file does not exist: {checksum_path}"] if require else []
    checksum_text = checksum_path.read_text("utf-8").strip()
    line = checksum_text.splitlines()[0] if checksum_text else ""
    parts = line.split()
    if not parts:
        return [f"checksum file is empty: {checksum_path}"]
    expected = parts[0].lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        return [f"checksum file does not start with a SHA-256 digest: {checksum_path}"]
    actual = sha256_file(archive_path)
    if expected != actual:
        return [f"checksum mismatch: expected {expected}, got {actual}"]
    if len(parts) >= 2 and Path(parts[-1]).name != archive_path.name:
        return [f"checksum filename mismatch: expected {archive_path.name}, got {parts[-1]}"]
    return []


def validate_archive(archive_path: Path) -> list[str]:
    checker = load_delivery_checker()
    errors: list[str] = []
    if not archive_path.exists():
        return [f"archive does not exist: {archive_path}"]
    if not tarfile.is_tarfile(archive_path):
        return [f"archive is not a tar file: {archive_path}"]

    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        member_names = [member.name for member in members]
        for member in members:
            reason = unsafe_member_reason(member.name)
            if reason:
                errors.append(f"{reason}: {member.name}")
            if member.isdir():
                continue
            relative_name = archive_relative_name(member.name)
            if not relative_name:
                errors.append(f"file is not under archive prefix: {member.name}")
                continue
            relative_path = Path(relative_name)
            if any(checker.is_excluded_dir(Path(part)) for part in relative_path.parts[:-1]):
                errors.append(f"forbidden directory included: {member.name}")
            if checker.is_excluded_file(relative_path):
                errors.append(f"forbidden file included: {member.name}")
            if checker.is_sensitive_included_file(relative_path):
                errors.append(f"sensitive file included: {member.name}")

        manifest_members = [name for name in member_names if name.endswith(f"/{MANIFEST_NAME}")]
        if len(manifest_members) != 1:
            errors.append(f"archive must contain exactly one {MANIFEST_NAME}")
            return errors

        manifest_file = archive.extractfile(manifest_members[0])
        if manifest_file is None:
            errors.append(f"cannot read {manifest_members[0]}")
            return errors
        try:
            manifest = json.loads(manifest_file.read().decode("utf-8"))
        except Exception as exc:
            errors.append(f"invalid manifest json: {exc}")
            return errors

    if manifest.get("schema_version") != EXPECTED_SCHEMA:
        errors.append(f"unexpected manifest schema: {manifest.get('schema_version')!r}")

    included_files = manifest.get("included_files")
    if not isinstance(included_files, list) or not all(isinstance(item, str) for item in included_files):
        errors.append("manifest included_files must be a string list")
        included_files = []
    included_set = set(included_files)
    archive_files = {
        archive_relative_name(name)
        for name in member_names
        if not name.endswith("/") and not name.endswith(f"/{MANIFEST_NAME}")
    }
    if included_set != archive_files:
        missing = sorted(included_set - archive_files)[:10]
        extra = sorted(archive_files - included_set)[:10]
        errors.append(f"manifest/archive mismatch: missing={missing} extra={extra}")
    if manifest.get("included_count") != len(included_set):
        errors.append("manifest included_count does not match included_files")
    return errors


def validate_extract_smoke(archive_path: Path) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(output_dir, filter="data")

        roots = [path for path in output_dir.iterdir() if path.is_dir()]
        if len(roots) != 1:
            return [f"archive must extract to exactly one top-level directory, got {len(roots)}"]
        root = roots[0]
        for relative in REQUIRED_EXTRACTED_PATHS:
            extracted = root / relative
            if not extracted.is_file():
                errors.append(f"extracted package missing required file: {relative}")
        forbidden_after_extract = [
            "services/agent-api/data/agent.db",
            "services/platform-api/data/platform.db",
            ".venv-agent-api",
            "apps/agent-console/node_modules",
            "diagnostics",
        ]
        for relative in forbidden_after_extract:
            if (root / relative).exists():
                errors.append(f"extracted package contains forbidden runtime path: {relative}")
        if not errors:
            errors.extend(validate_post_extract_reverify(root, archive_path))
    return errors


def validate_post_extract_reverify(root: Path, archive_path: Path) -> list[str]:
    verifier = root / "scripts" / "verify-delivery-package.py"
    completed = subprocess.run(
        [sys.executable, str(verifier), "--archive", str(archive_path.resolve())],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode == 0:
        return []
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    return [f"post-extract reverify command failed: {output}"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify exported delivery tar.gz archive against its manifest and exclusion rules.")
    parser.add_argument("--archive", type=Path, required=True, help="Delivery .tar.gz archive to verify")
    parser.add_argument("--checksum", type=Path, help="SHA-256 sidecar path. Defaults to <archive>.sha256 when present or required.")
    parser.add_argument("--require-checksum", action="store_true", help="Fail when checksum sidecar is missing")
    parser.add_argument("--extract-smoke", action="store_true", help="Safely extract archive to a temporary directory and verify required entry files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        errors = validate_archive(args.archive)
        checksum_path = args.checksum or default_checksum_path(args.archive)
        errors.extend(validate_checksum(args.archive, checksum_path, args.require_checksum or bool(args.checksum)))
        if args.extract_smoke:
            errors.extend(validate_extract_smoke(args.archive))
    except Exception as exc:
        print(f"delivery package verification failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("delivery package verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"delivery package verification passed: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
