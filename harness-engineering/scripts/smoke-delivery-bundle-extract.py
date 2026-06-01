#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


REQUIRED_COMMANDS = [
    ["scripts/check-delivery-package.py"],
    ["scripts/scan-delivery-artifacts.py"],
]


def run_extracted(root: Path, args: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    return completed.returncode == 0, output


def smoke(bundle_dir: Path) -> list[str]:
    archive = bundle_dir / "harness-engineering-delivery.tar.gz"
    report = bundle_dir / "delivery-acceptance-report.json"
    errors: list[str] = []
    if not archive.exists():
        return [f"bundle archive missing: {archive}"]
    if not report.exists():
        return [f"bundle acceptance report missing: {report}"]

    with tempfile.TemporaryDirectory() as tmp:
        extract_dir = Path(tmp)
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(extract_dir, filter="data")
        roots = [path for path in extract_dir.iterdir() if path.is_dir()]
        if len(roots) != 1:
            return [f"expected one extracted root, got {len(roots)}"]
        root = roots[0]
        for command in REQUIRED_COMMANDS:
            passed, output = run_extracted(root, command)
            if not passed:
                errors.append(f"extracted command failed {' '.join(command)}: {output}")
        passed, output = run_extracted(root, ["scripts/verify-delivery-acceptance-report.py", "--report", str(report)])
        if not passed:
            errors.append(f"extracted report verification failed: {output}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract exported delivery bundle and rerun basic verification commands from the extracted tree.")
    parser.add_argument("--bundle-dir", type=Path, required=True, help="Directory created by export-delivery-bundle.py")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = smoke(args.bundle_dir.resolve())
    if errors:
        print("extracted delivery bundle smoke failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"extracted delivery bundle smoke passed: {args.bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
