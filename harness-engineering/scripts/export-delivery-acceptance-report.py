#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def redact_arg(arg: str) -> str:
    text = str(arg)
    if text.startswith(str(ROOT)):
        return str(Path("<project>") / Path(text).relative_to(ROOT))
    path = Path(text)
    if path.is_absolute():
        return str(Path("<path>") / path.name)
    return text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_check(name: str, args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "name": name,
        "command": " ".join(redact_arg(arg) for arg in args),
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout.strip().splitlines()[-3:],
        "stderr_tail": completed.stderr.strip().splitlines()[-3:],
    }


def run_command(name: str, args: list[str], timeout: int = 30) -> dict[str, Any]:
    executable = shutil.which(args[0])
    if executable is None:
        return {
            "name": name,
            "command": " ".join(args),
            "passed": True,
            "skipped": True,
            "reason": f"{args[0]} not found",
            "returncode": None,
            "stdout_tail": [],
            "stderr_tail": [],
        }
    completed = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "name": name,
        "command": " ".join(redact_arg(arg) for arg in args),
        "passed": completed.returncode == 0,
        "skipped": False,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout.strip().splitlines()[-3:],
        "stderr_tail": completed.stderr.strip().splitlines()[-3:],
    }


def environment_fingerprint() -> dict[str, Any]:
    docker = run_command("docker_version", ["docker", "--version"])
    compose = run_command("docker_compose_version", ["docker", "compose", "version"])
    return {
        "python_executable": Path(sys.executable).name,
        "python_executable_path_exported": False,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "docker": docker,
        "docker_compose": compose,
    }


def compose_checks() -> list[dict[str, Any]]:
    docker = shutil.which("docker")
    if docker is None:
        return [
            {
                "name": "compose_config_platform",
                "command": "docker compose -f deploy/docker-compose.platform.yml config",
                "passed": True,
                "skipped": True,
                "reason": "docker not found",
                "returncode": None,
                "stdout_tail": [],
                "stderr_tail": [],
            },
            {
                "name": "compose_config_agent",
                "command": "docker compose -f deploy/docker-compose.agent.yml config",
                "passed": True,
                "skipped": True,
                "reason": "docker not found",
                "returncode": None,
                "stdout_tail": [],
                "stderr_tail": [],
            },
        ]
    return [
        run_command("compose_config_platform", ["docker", "compose", "-f", "deploy/docker-compose.platform.yml", "config"], timeout=60),
        run_command("compose_config_agent", ["docker", "compose", "-f", "deploy/docker-compose.agent.yml", "config"], timeout=60),
    ]


def read_archive_manifest(archive_path: Path) -> dict[str, Any]:
    with tarfile.open(archive_path, "r:gz") as archive:
        manifest_members = [name for name in archive.getnames() if name.endswith("/DELIVERY-MANIFEST.json")]
        if len(manifest_members) != 1:
            raise ValueError("archive must contain exactly one DELIVERY-MANIFEST.json")
        manifest_file = archive.extractfile(manifest_members[0])
        if manifest_file is None:
            raise ValueError("cannot read DELIVERY-MANIFEST.json")
        manifest = json.loads(manifest_file.read().decode("utf-8"))
    included_files = manifest.get("included_files", [])
    return {
        "schema_version": manifest.get("schema_version"),
        "included_count": manifest.get("included_count"),
        "excluded_count": manifest.get("excluded_count"),
        "included_files_count": len(included_files) if isinstance(included_files, list) else None,
        "excluded_rules": manifest.get("excluded_rules", {}),
    }


def v5_p0_evidence() -> dict[str, Any]:
    return {
        "scope": "V5 P0 department pilot acceptance evidence",
        "metadata_only": True,
        "business_data_exported": False,
        "evidence_items": [
            {
                "name": "knowledge_governance_metadata_and_audit",
                "coverage": [
                    "governance metadata persistence",
                    "review status transitions",
                    "separate reviewer control",
                    "department manager review permission",
                    "governance audit logs",
                ],
                "tests": [
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_knowledge_base_governance_metadata_controls_ai_usage",
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_knowledge_base_review_transitions_are_audited",
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_knowledge_base_review_requires_qualified_separate_reviewer",
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_bound_department_manager_can_review_department_knowledge",
                ],
                "acceptance_refs": ["P0-01", "P0-02"],
            },
            {
                "name": "ai_risk_controls_and_policy_enforcement",
                "coverage": [
                    "search-only policy rejects generation",
                    "disabled and expired knowledge cannot generate",
                    "high-sensitive content disables AI use",
                    "insufficient evidence guardrail",
                    "structured legal-risk response template",
                ],
                "tests": [
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_expired_knowledge_base_can_retrieve_but_cannot_generate",
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_file_governance_controls_rag_retrieval_and_generation",
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_parse_file_marks_high_sensitive_content_ai_disabled",
                    "tests/api/test_m25_enterprise_management.py::test_enterprise_org_integrations_and_assistant_feedback",
                ],
                "acceptance_refs": ["P0-03", "P0-06"],
            },
            {
                "name": "quality_feedback_closed_loop",
                "coverage": [
                    "feedback binds to a real assistant message",
                    "issue labels are normalized",
                    "feedback status handling is audited through management metrics",
                    "feedback quality counts enter enterprise overview",
                ],
                "tests": [
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_knowledge_base_rag_uses_kb_scope_and_indexes_are_created",
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_feedback_quality_issue_counts_enter_management_overview",
                    "tests/api/test_m25_enterprise_management.py::test_knowledge_base_chat_feedback_binds_real_answer",
                    "tests/api/test_m25_enterprise_management.py::test_fastapi_enterprise_admin_routes",
                ],
                "acceptance_refs": ["P0-07", "P0-08"],
            },
            {
                "name": "historical_citation_and_source_traceability",
                "coverage": [
                    "knowledge-base RAG stays in scope",
                    "citations carry knowledge-base identity",
                    "history retrieval restores citations",
                    "case isolation keeps unauthorized citations empty",
                    "citation trust level and priority are exposed",
                ],
                "tests": [
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_knowledge_base_rag_uses_kb_scope_and_indexes_are_created",
                    "tests/api/test_m24_knowledge_base_data_plane.py::test_scenario_query_uses_structured_task_prompt",
                    "tests/rag/test_m2_case_isolation_citations.py::test_rag_does_not_cross_cases_and_citations_are_structured",
                    "tests/rag/test_m2_case_isolation_citations.py::test_chat_history_api_filters_by_case",
                ],
                "acceptance_refs": ["P0-04", "P0-06"],
            },
            {
                "name": "platform_invisibility_special_checks",
                "coverage": [
                    "platform schema excludes business tables",
                    "platform schema excludes forbidden business columns",
                    "allowed control-plane fields exclude forbidden fields",
                    "forbidden business field probe is rejected",
                    "platform console invisibility UI smoke passes",
                ],
                "tests": [
                    "tests/security/test_m19_platform_invisibility_report.py::test_report_passes_for_control_plane_only_schema",
                    "tests/security/test_m19_platform_invisibility_report.py::test_report_fails_for_platform_business_schema_and_redacts_values",
                    "tests/security/test_m21_delivery_redline_and_extract_smoke.py::test_platform_console_invisibility_ui_smoke_passes",
                ],
                "scripts": [
                    "scripts/export-platform-invisibility-report.py",
                    "apps/platform-console/scripts/check-invisibility-ui.mjs",
                ],
                "acceptance_refs": ["P0-09"],
            },
            {
                "name": "delivery_acceptance_package_redaction",
                "coverage": [
                    "delivery boundary excludes runtime and local-only artifacts",
                    "artifact scan rejects secrets and business payloads",
                    "archive verification requires checksum",
                    "archive verification requires extract smoke",
                    "acceptance report redline scan rejects business fields",
                ],
                "tests": [
                    "tests/security/test_m21_delivery_acceptance_report.py",
                    "tests/security/test_m21_delivery_acceptance_report_verify.py",
                    "tests/security/test_m21_delivery_redline_and_extract_smoke.py::test_acceptance_report_redline_scan_passes_valid_report",
                    "tests/security/test_m21_delivery_redline_and_extract_smoke.py::test_acceptance_report_redline_scan_rejects_business_fields",
                ],
                "scripts": [
                    "scripts/export-delivery-acceptance-report.py",
                    "scripts/verify-delivery-acceptance-report.py",
                    "scripts/scan-delivery-acceptance-report.py",
                    "scripts/smoke-delivery-bundle-extract.py",
                ],
                "acceptance_refs": ["P0-09"],
            },
        ],
        "redaction": {
            "mode": "metadata_only",
            "test_outputs_exported": False,
            "business_data_exported": False,
            "database_values_exported": False,
        },
    }


def build_report(archive_path: Path | None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    archive_owned_by_report = archive_path is None

    try:
        if archive_path is None:
            temp_dir = tempfile.TemporaryDirectory()
            archive_path = Path(temp_dir.name) / "harness-engineering-delivery.tar.gz"
            checks.append(
                run_check(
                    "delivery_archive_export",
                    ["scripts/export-delivery-package.py", "--output", str(archive_path)],
                )
            )

        checksum_path = archive_path.with_name(archive_path.name + ".sha256")
        checks.extend(
            [
                run_check("deploy_config_validation", ["scripts/validate-deploy-config.py", "--mode", "example"]),
                run_check("delivery_artifact_scan", ["scripts/scan-delivery-artifacts.py"]),
                run_check("delivery_package_boundary", ["scripts/check-delivery-package.py"]),
                run_check(
                    "delivery_archive_verification",
                    ["scripts/verify-delivery-package.py", "--archive", str(archive_path), "--require-checksum", "--extract-smoke"],
                ),
            ]
        )
        checks.extend(compose_checks())

        archive: dict[str, Any] = {
            "path": archive_path.name,
            "path_exported": False,
            "exists": archive_path.exists(),
            "owned_by_report": archive_owned_by_report,
            "checksum_path": checksum_path.name,
            "checksum_path_exported": False,
            "checksum_exists": checksum_path.exists(),
        }
        if archive_path.exists():
            archive["size_bytes"] = archive_path.stat().st_size
            archive["sha256"] = sha256_file(archive_path)
            try:
                archive["manifest"] = read_archive_manifest(archive_path)
            except Exception as exc:
                archive["manifest_error"] = str(exc)
        if checksum_path.exists():
            archive["checksum_text"] = checksum_path.read_text("utf-8").strip()

        return {
            "schema_version": "m21-delivery-acceptance-report-v2",
            "generated_at": int(time.time()),
            "passed": all(check["passed"] for check in checks),
            "checks": checks,
            "environment": environment_fingerprint(),
            "archive": archive,
            "v5_p0_evidence": v5_p0_evidence(),
            "redaction": {
                "mode": "metadata_only",
                "business_data_exported": False,
                "archive_file_contents_exported": False,
            },
        }
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a metadata-only delivery acceptance evidence report.")
    parser.add_argument("--archive", type=Path, help="Existing delivery archive. If omitted, a temporary archive is exported and verified.")
    parser.add_argument("--output", type=Path, required=True, help="JSON report output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(args.archive.resolve() if args.archive else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "utf-8")
    print(str(args.output))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
