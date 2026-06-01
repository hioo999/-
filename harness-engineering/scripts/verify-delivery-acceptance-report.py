#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "m21-delivery-acceptance-report-v2"
REQUIRED_CHECKS = {
    "deploy_config_validation",
    "delivery_artifact_scan",
    "delivery_package_boundary",
    "delivery_archive_verification",
    "compose_config_platform",
    "compose_config_agent",
}
REQUIRED_ENVIRONMENT_KEYS = {
    "python_executable",
    "python_version",
    "platform",
    "machine",
    "docker",
    "docker_compose",
}
REQUIRED_V5_P0_EVIDENCE = {
    "knowledge_governance_metadata_and_audit",
    "ai_risk_controls_and_policy_enforcement",
    "quality_feedback_closed_loop",
    "historical_citation_and_source_traceability",
    "platform_invisibility_special_checks",
    "delivery_acceptance_package_redaction",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_check(check: dict[str, Any], errors: list[str]) -> None:
    name = check.get("name", "<unknown>")
    require(isinstance(check.get("name"), str) and bool(check.get("name")), f"check {name} missing name", errors)
    require(isinstance(check.get("command"), str) and bool(check.get("command")), f"check {name} missing command", errors)
    require(isinstance(check.get("passed"), bool), f"check {name} missing boolean passed", errors)
    if not check.get("passed", False):
        require(not check.get("skipped", False), f"check {name} cannot be skipped and failed", errors)
    require("returncode" in check, f"check {name} missing returncode", errors)
    require(isinstance(check.get("stdout_tail"), list), f"check {name} missing stdout_tail list", errors)
    require(isinstance(check.get("stderr_tail"), list), f"check {name} missing stderr_tail list", errors)


def validate_v5_p0_evidence(evidence: Any, errors: list[str]) -> None:
    require(isinstance(evidence, dict), "v5_p0_evidence must be object", errors)
    if not isinstance(evidence, dict):
        return

    require(evidence.get("metadata_only") is True, "v5_p0_evidence.metadata_only must be true", errors)
    require(evidence.get("business_data_exported") is False, "v5_p0_evidence.business_data_exported must be false", errors)
    items = evidence.get("evidence_items")
    require(isinstance(items, list), "v5_p0_evidence.evidence_items must be list", errors)
    if not isinstance(items, list):
        return

    names: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append("each v5_p0_evidence item must be object")
            continue
        name = item.get("name")
        require(isinstance(name, str) and bool(name), "v5_p0_evidence item missing name", errors)
        if isinstance(name, str):
            names.add(name)
        require(isinstance(item.get("coverage"), list) and bool(item.get("coverage")), f"v5_p0_evidence item {name} missing coverage", errors)
        require(isinstance(item.get("tests"), list) and bool(item.get("tests")), f"v5_p0_evidence item {name} missing tests", errors)
        require(isinstance(item.get("acceptance_refs"), list) and bool(item.get("acceptance_refs")), f"v5_p0_evidence item {name} missing acceptance_refs", errors)

    missing = sorted(REQUIRED_V5_P0_EVIDENCE - names)
    require(not missing, f"missing v5_p0_evidence items: {missing}", errors)

    redaction = evidence.get("redaction")
    require(isinstance(redaction, dict), "v5_p0_evidence.redaction must be object", errors)
    if isinstance(redaction, dict):
        require(redaction.get("mode") == "metadata_only", "v5_p0_evidence.redaction.mode must be metadata_only", errors)
        require(redaction.get("test_outputs_exported") is False, "v5_p0_evidence test_outputs_exported must be false", errors)
        require(redaction.get("business_data_exported") is False, "v5_p0_evidence redaction business_data_exported must be false", errors)
        require(redaction.get("database_values_exported") is False, "v5_p0_evidence database_values_exported must be false", errors)


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(report.get("schema_version") == EXPECTED_SCHEMA, "unexpected schema_version", errors)
    require(isinstance(report.get("generated_at"), int), "generated_at must be int", errors)
    require(isinstance(report.get("passed"), bool), "passed must be bool", errors)

    checks = report.get("checks")
    require(isinstance(checks, list), "checks must be list", errors)
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, dict):
                validate_check(check, errors)
            else:
                errors.append("each check must be object")
        check_names = {check.get("name") for check in checks if isinstance(check, dict)}
        missing = sorted(REQUIRED_CHECKS - check_names)
        require(not missing, f"missing required checks: {missing}", errors)
        expected_passed = all(bool(check.get("passed")) for check in checks if isinstance(check, dict))
        require(report.get("passed") == expected_passed, "passed does not match check statuses", errors)
        archive_checks = [check for check in checks if isinstance(check, dict) and check.get("name") == "delivery_archive_verification"]
        if archive_checks:
            command = archive_checks[0].get("command", "")
            require("--require-checksum" in command, "archive verification missing --require-checksum", errors)
            require("--extract-smoke" in command, "archive verification missing --extract-smoke", errors)

    environment = report.get("environment")
    require(isinstance(environment, dict), "environment must be object", errors)
    if isinstance(environment, dict):
        missing_env = sorted(REQUIRED_ENVIRONMENT_KEYS - set(environment))
        require(not missing_env, f"environment missing keys: {missing_env}", errors)

    archive = report.get("archive")
    require(isinstance(archive, dict), "archive must be object", errors)
    if isinstance(archive, dict):
        require(isinstance(archive.get("exists"), bool), "archive.exists must be bool", errors)
        require(isinstance(archive.get("checksum_exists"), bool), "archive.checksum_exists must be bool", errors)
        if archive.get("exists"):
            require(isinstance(archive.get("size_bytes"), int) and archive.get("size_bytes", 0) > 0, "archive.size_bytes must be positive", errors)
            sha256 = archive.get("sha256")
            require(isinstance(sha256, str) and len(sha256) == 64, "archive.sha256 must be hex digest", errors)
            manifest = archive.get("manifest")
            require(isinstance(manifest, dict), "archive.manifest must be object when archive exists", errors)
            if isinstance(manifest, dict):
                require(manifest.get("included_count") == manifest.get("included_files_count"), "manifest included counts mismatch", errors)
                require(isinstance(manifest.get("excluded_count"), int), "manifest excluded_count must be int", errors)
        if archive.get("checksum_exists"):
            checksum_text = archive.get("checksum_text", "")
            require(isinstance(checksum_text, str) and archive.get("sha256", "") in checksum_text, "checksum_text must include archive sha256", errors)

    validate_v5_p0_evidence(report.get("v5_p0_evidence"), errors)

    redaction = report.get("redaction")
    require(isinstance(redaction, dict), "redaction must be object", errors)
    if isinstance(redaction, dict):
        require(redaction.get("mode") == "metadata_only", "redaction.mode must be metadata_only", errors)
        require(redaction.get("business_data_exported") is False, "business_data_exported must be false", errors)
        require(redaction.get("archive_file_contents_exported") is False, "archive_file_contents_exported must be false", errors)
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify delivery acceptance evidence report schema and required checks.")
    parser.add_argument("--report", type=Path, required=True, help="Delivery acceptance report JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = json.loads(args.report.read_text("utf-8"))
    except Exception as exc:
        print(f"delivery acceptance report verification failed: {exc}", file=sys.stderr)
        return 1
    errors = validate_report(report)
    if errors:
        print("delivery acceptance report verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"delivery acceptance report verification passed: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
