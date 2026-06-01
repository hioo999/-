#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE_NAME = "harness-engineering-delivery.tar.gz"
DEFAULT_REPORT_NAME = "delivery-acceptance-report.json"


def output_is_under_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return False
    return True


def run_step(name: str, args: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "name": name,
        "command": " ".join(args),
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout.strip().splitlines()[-5:],
        "stderr_tail": completed.stderr.strip().splitlines()[-5:],
    }


def read_acceptance_report_summary(report_path: Path) -> dict[str, object]:
    if not report_path.exists():
        return {"exists": False}
    report = json.loads(report_path.read_text("utf-8"))
    v5_evidence = report.get("v5_p0_evidence", {}) if isinstance(report, dict) else {}
    evidence_items = v5_evidence.get("evidence_items", []) if isinstance(v5_evidence, dict) else []
    evidence_names = [item.get("name") for item in evidence_items if isinstance(item, dict) and isinstance(item.get("name"), str)]
    return {
        "exists": True,
        "schema_version": report.get("schema_version"),
        "passed": report.get("passed"),
        "v5_p0_evidence_count": len(evidence_names),
        "v5_p0_evidence_names": sorted(evidence_names),
        "metadata_only": bool(v5_evidence.get("metadata_only")) if isinstance(v5_evidence, dict) else False,
        "business_data_exported": bool(v5_evidence.get("business_data_exported")) if isinstance(v5_evidence, dict) else True,
    }


def export_bundle(output_dir: Path, allow_output_under_root: bool) -> tuple[dict[str, object], list[dict[str, object]]]:
    output_dir = output_dir.resolve()
    if output_is_under_root(output_dir) and not allow_output_under_root:
        raise ValueError("output directory must be outside the project root; use --allow-output-under-root only for isolated tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_path = output_dir / DEFAULT_ARCHIVE_NAME
    checksum_path = archive_path.with_name(archive_path.name + ".sha256")
    report_path = output_dir / DEFAULT_REPORT_NAME
    steps = [
        run_step("export_delivery_package", ["scripts/export-delivery-package.py", "--output", str(archive_path)]),
        run_step(
            "verify_delivery_package",
            ["scripts/verify-delivery-package.py", "--archive", str(archive_path), "--require-checksum", "--extract-smoke"],
        ),
        run_step(
            "export_delivery_acceptance_report",
            ["scripts/export-delivery-acceptance-report.py", "--archive", str(archive_path), "--output", str(report_path)],
        ),
        run_step("verify_delivery_acceptance_report", ["scripts/verify-delivery-acceptance-report.py", "--report", str(report_path)]),
    ]
    acceptance_report_summary = read_acceptance_report_summary(report_path)
    manifest = {
        "schema_version": "m21-delivery-bundle-v2",
        "passed": all(bool(step["passed"]) for step in steps),
        "output_dir": str(output_dir),
        "archive": str(archive_path),
        "checksum": str(checksum_path),
        "acceptance_report": str(report_path),
        "acceptance_report_summary": acceptance_report_summary,
        "artifacts": {
            "archive_exists": archive_path.exists(),
            "checksum_exists": checksum_path.exists(),
            "acceptance_report_exists": report_path.exists(),
        },
        "steps": steps,
    }
    manifest_path = output_dir / "delivery-bundle-manifest.json"
    manifest["bundle_manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "utf-8")
    return manifest, steps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export delivery archive, checksum, acceptance report, and verification evidence in one command.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory outside the project root")
    parser.add_argument("--allow-output-under-root", action="store_true", help="Allow output directory under project root for isolated tests only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest, steps = export_bundle(args.output_dir, args.allow_output_under_root)
    except Exception as exc:
        print(f"delivery bundle export failed: {exc}", file=sys.stderr)
        return 1
    for step in steps:
        status = "passed" if step["passed"] else "failed"
        print(f"{step['name']}: {status}")
    print(str(manifest["bundle_manifest"]))
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
