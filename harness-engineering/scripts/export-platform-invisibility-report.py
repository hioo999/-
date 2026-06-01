#!/usr/bin/env python3
"""Export a platform-invisibility acceptance report.

The report is intentionally metadata-only: it inspects table names, column names,
row counts, and whitelist/forbidden-field rules without exporting stored values.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORM_DB = ROOT / "services" / "platform-api" / "data" / "platform.db"
DEFAULT_OUTPUT = ROOT / "docs" / "platform-invisibility-report.json"
BUSINESS_TABLE_NAMES = {
    "case_spaces",
    "case_members",
    "local_files",
    "document_chunks",
    "vector_index_refs",
    "local_embedding_vectors",
    "chat_sessions",
    "chat_messages",
    "citations",
    "evidences",
    "model_configs",
}
REQUIRED_FORBIDDEN_FIELDS = {
    "case_name",
    "case_title",
    "case_no",
    "file_name",
    "file_path",
    "document_text",
    "chunk_text",
    "embedding",
    "vector",
    "question",
    "answer",
    "prompt",
    "api_key",
    "password",
    "db_password",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pass_check(name: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"name": name, "passed": True, "details": details or {}}


def fail_check(name: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"name": name, "passed": False, "message": message, "details": details or {}}
    return payload


def table_metadata(db_path: Path) -> tuple[dict[str, list[str]], dict[str, int]]:
    if not db_path.exists():
        return {}, {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        tables = [str(row["name"]) for row in rows]
        columns = {table: [str(col["name"]) for col in conn.execute(f"PRAGMA table_info({table})").fetchall()] for table in tables}  # noqa: S608 - SQLite table names come from sqlite_master
        counts = {table: int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]) for table in tables}  # noqa: S608 - SQLite table names come from sqlite_master
        return columns, counts
    finally:
        conn.close()


def evaluate_report(db_path: Path) -> dict[str, Any]:
    forbidden = load_module("platform_forbidden_report", ROOT / "services" / "platform-api" / "app" / "security" / "forbidden_fields.py")
    health = load_module("platform_health_report", ROOT / "services" / "platform-api" / "app" / "schemas" / "health.py")

    checks: list[dict[str, Any]] = []
    table_columns, row_counts = table_metadata(db_path)
    table_names = set(table_columns)

    business_tables = sorted(table_names & BUSINESS_TABLE_NAMES)
    if business_tables:
        checks.append(fail_check("platform_has_no_business_tables", "platform database contains business tables", {"business_tables": business_tables}))
    else:
        checks.append(pass_check("platform_has_no_business_tables", {"tables_checked": sorted(table_names)}))

    forbidden_columns = sorted(
        f"{table}.{column}"
        for table, columns in table_columns.items()
        for column in columns
        if column in forbidden.FORBIDDEN_FIELDS
    )
    if forbidden_columns:
        checks.append(fail_check("platform_has_no_forbidden_columns", "platform database contains forbidden business columns", {"forbidden_columns": forbidden_columns}))
    else:
        checks.append(pass_check("platform_has_no_forbidden_columns", {"tables_checked": sorted(table_names)}))

    missing_forbidden = sorted(REQUIRED_FORBIDDEN_FIELDS - set(forbidden.FORBIDDEN_FIELDS))
    if missing_forbidden:
        checks.append(fail_check("forbidden_field_catalog_covers_p0_business_fields", "required forbidden fields are missing", {"missing": missing_forbidden}))
    else:
        checks.append(pass_check("forbidden_field_catalog_covers_p0_business_fields", {"required_count": len(REQUIRED_FORBIDDEN_FIELDS)}))

    allowed_field_sets = {
        "health": set(health.HEALTH_ALLOWED_FIELDS),
        "register": set(health.REGISTER_ALLOWED_FIELDS),
        "heartbeat": set(health.HEARTBEAT_ALLOWED_FIELDS),
    }
    allowed_forbidden_overlap = {name: sorted(fields & set(forbidden.FORBIDDEN_FIELDS)) for name, fields in allowed_field_sets.items() if fields & set(forbidden.FORBIDDEN_FIELDS)}
    if allowed_forbidden_overlap:
        checks.append(fail_check("platform_whitelists_exclude_forbidden_fields", "allowed fields overlap forbidden business fields", allowed_forbidden_overlap))
    else:
        checks.append(pass_check("platform_whitelists_exclude_forbidden_fields", {name: sorted(fields) for name, fields in allowed_field_sets.items()}))

    injected_payload = {"tenant_id": "t_probe", "agent_id": "ag_probe", "status": "online", "file_name": "secret.pdf"}
    try:
        forbidden.ensure_allowed_fields(injected_payload, health.HEALTH_ALLOWED_FIELDS)
    except ValueError:
        checks.append(pass_check("platform_rejects_forbidden_business_field_probe", {"probe_field": "file_name"}))
    else:
        checks.append(fail_check("platform_rejects_forbidden_business_field_probe", "forbidden field probe was accepted"))

    return {
        "schema_version": "m19-platform-invisibility-v1",
        "generated_at": int(time.time()),
        "platform_db_exists": db_path.exists(),
        "row_counts": row_counts,
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "redaction": {
            "mode": "metadata_only",
            "database_values_exported": False,
            "business_data_exported": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export platform-invisibility acceptance report")
    parser.add_argument("--platform-db", type=Path, default=Path(os.environ.get("PLATFORM_DB", DEFAULT_PLATFORM_DB)), help="Platform SQLite database path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Report JSON output path")
    args = parser.parse_args()

    report = evaluate_report(args.platform_db)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(args.output))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
