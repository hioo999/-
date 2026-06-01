#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SCHEMA = "m21-delivery-bundle-v2"
REQUIRED_STEPS = {
    "export_delivery_package",
    "verify_delivery_package",
    "export_delivery_acceptance_report",
    "verify_delivery_acceptance_report",
}
REQUIRED_V5_P0_EVIDENCE = {
    "knowledge_governance_metadata_and_audit",
    "ai_risk_controls_and_policy_enforcement",
    "quality_feedback_closed_loop",
    "historical_citation_and_source_traceability",
    "platform_invisibility_special_checks",
    "delivery_acceptance_package_redaction",
}


def run_verifier(args: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    return completed.returncode == 0, output


def validate_step(step: dict[str, Any], errors: list[str]) -> None:
    name = step.get("name", "<unknown>")
    if not isinstance(step.get("name"), str) or not step.get("name"):
        errors.append(f"step {name} missing name")
    if not isinstance(step.get("command"), str) or not step.get("command"):
        errors.append(f"step {name} missing command")
    if step.get("passed") is not True:
        errors.append(f"step {name} did not pass")
    if "returncode" not in step:
        errors.append(f"step {name} missing returncode")
    if not isinstance(step.get("stdout_tail"), list):
        errors.append(f"step {name} missing stdout_tail list")
    if not isinstance(step.get("stderr_tail"), list):
        errors.append(f"step {name} missing stderr_tail list")


def validate_acceptance_report_summary(manifest: dict[str, Any], report_path: Path, errors: list[str]) -> None:
    summary = manifest.get("acceptance_report_summary")
    if not isinstance(summary, dict):
        errors.append("acceptance_report_summary must be object")
        return
    if summary.get("exists") is not True:
        errors.append("acceptance_report_summary.exists must be true")
    if summary.get("schema_version") != "m21-delivery-acceptance-report-v2":
        errors.append("acceptance_report_summary schema_version must be m21-delivery-acceptance-report-v2")
    if summary.get("passed") is not True:
        errors.append("acceptance_report_summary passed must be true")
    if summary.get("metadata_only") is not True:
        errors.append("acceptance_report_summary metadata_only must be true")
    if summary.get("business_data_exported") is not False:
        errors.append("acceptance_report_summary business_data_exported must be false")
    names = summary.get("v5_p0_evidence_names")
    if not isinstance(names, list):
        errors.append("acceptance_report_summary v5_p0_evidence_names must be list")
        names = []
    missing = sorted(REQUIRED_V5_P0_EVIDENCE - {name for name in names if isinstance(name, str)})
    if missing:
        errors.append(f"acceptance_report_summary missing V5 P0 evidence: {missing}")
    if summary.get("v5_p0_evidence_count") != len(names):
        errors.append("acceptance_report_summary evidence count mismatch")

    if not report_path.exists():
        return
    try:
        report = json.loads(report_path.read_text("utf-8"))
    except Exception as exc:
        errors.append(f"cannot read acceptance report for summary check: {exc}")
        return
    v5_evidence = report.get("v5_p0_evidence", {}) if isinstance(report, dict) else {}
    evidence_items = v5_evidence.get("evidence_items", []) if isinstance(v5_evidence, dict) else []
    report_names = sorted(item.get("name") for item in evidence_items if isinstance(item, dict) and isinstance(item.get("name"), str))
    if sorted(name for name in names if isinstance(name, str)) != report_names:
        errors.append("acceptance_report_summary does not match acceptance report V5 P0 evidence")


def validate_bundle(manifest_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text("utf-8"))
    except Exception as exc:
        return [f"cannot read bundle manifest: {exc}"]

    if manifest.get("schema_version") != EXPECTED_SCHEMA:
        errors.append("unexpected schema_version")
    if manifest.get("passed") is not True:
        errors.append("bundle manifest passed must be true")

    archive = Path(str(manifest.get("archive", "")))
    checksum = Path(str(manifest.get("checksum", "")))
    report = Path(str(manifest.get("acceptance_report", "")))
    bundle_manifest = Path(str(manifest.get("bundle_manifest", "")))
    expected_bundle_manifest = manifest_path.resolve()
    if bundle_manifest.resolve() != expected_bundle_manifest:
        errors.append("bundle_manifest path does not match verified manifest path")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be object")
        artifacts = {}
    for key, path in (
        ("archive_exists", archive),
        ("checksum_exists", checksum),
        ("acceptance_report_exists", report),
    ):
        if artifacts.get(key) is not True:
            errors.append(f"artifacts.{key} must be true")
        if not path.exists() or not path.is_file():
            errors.append(f"artifact file missing: {path}")

    steps = manifest.get("steps")
    if not isinstance(steps, list):
        errors.append("steps must be list")
        steps = []
    for step in steps:
        if isinstance(step, dict):
            validate_step(step, errors)
        else:
            errors.append("each step must be object")
    step_names = {step.get("name") for step in steps if isinstance(step, dict)}
    missing = sorted(REQUIRED_STEPS - step_names)
    if missing:
        errors.append(f"missing required steps: {missing}")

    if archive.exists():
        passed, output = run_verifier(["scripts/verify-delivery-package.py", "--archive", str(archive), "--require-checksum", "--extract-smoke"])
        if not passed:
            errors.append(f"archive verifier failed: {output}")
    if report.exists():
        passed, output = run_verifier(["scripts/verify-delivery-acceptance-report.py", "--report", str(report)])
        if not passed:
            errors.append(f"acceptance report verifier failed: {output}")
    validate_acceptance_report_summary(manifest, report, errors)
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify delivery bundle manifest, artifacts, archive, and acceptance report.")
    parser.add_argument("--manifest", type=Path, required=True, help="delivery-bundle-manifest.json path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_bundle(args.manifest.resolve())
    if errors:
        print("delivery bundle verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"delivery bundle verification passed: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
