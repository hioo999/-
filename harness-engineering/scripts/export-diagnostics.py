#!/usr/bin/env python3
"""Export a local diagnostics bundle with strict business-data redaction."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "services" / "agent-api" / "data" / "agent.db"
DEFAULT_OUTPUT_DIR = ROOT / "diagnostics"

KNOWN_TABLES = [
    "local_users",
    "local_sessions",
    "local_data_sources",
    "case_spaces",
    "case_members",
    "local_files",
    "processing_tasks",
    "document_chunks",
    "vector_index_refs",
    "local_embedding_vectors",
    "chat_sessions",
    "chat_messages",
    "citations",
    "evidences",
    "audit_logs",
    "model_configs",
    "agent_config",
]


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()  # noqa: S608 - known static table names only
    return int(row["c"])


def grouped_counts(conn: sqlite3.Connection, table: str, column: str) -> dict[str, int]:
    rows = conn.execute(f"SELECT {column} AS k, COUNT(*) AS c FROM {table} GROUP BY {column}").fetchall()  # noqa: S608 - known static names only
    return {str(row["k"]): int(row["c"]) for row in rows}


def existing_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {str(row["name"]) for row in rows}


def build_payload(db_path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "m17-diagnostics-v1",
        "generated_at": int(time.time()),
        "agent": {
            "version": "4.1.0-mvp",
            "db_exists": db_path.exists(),
        },
        "database": {
            "path_configured": bool(db_path),
            "table_counts": {},
            "task_status_counts": {},
            "file_status_counts": {},
            "model_secret_configured_count": 0,
        },
        "redaction": {
            "mode": "whitelist_only",
            "excluded": [
                "case names",
                "file names",
                "file paths",
                "document text",
                "chunks",
                "vectors",
                "questions",
                "answers",
                "prompts",
                "model secrets",
                "database credentials",
            ],
        },
    }
    if not db_path.exists():
        return payload

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = existing_tables(conn)
        payload["database"]["table_counts"] = {table: count_rows(conn, table) for table in KNOWN_TABLES if table in tables}
        if "processing_tasks" in tables:
            payload["database"]["task_status_counts"] = grouped_counts(conn, "processing_tasks", "status")
        if "local_files" in tables:
            payload["database"]["file_status_counts"] = grouped_counts(conn, "local_files", "process_status")
        if "model_configs" in tables:
            row = conn.execute("SELECT COUNT(*) AS c FROM model_configs WHERE api_key_encrypted IS NOT NULL AND api_key_encrypted != ''").fetchone()
            payload["database"]["model_secret_configured_count"] = int(row["c"])
    finally:
        conn.close()
    return payload


def render_preview(payload: dict[str, Any]) -> str:
    table_counts = payload["database"]["table_counts"]
    return json.dumps(
        {
            "schema_version": payload["schema_version"],
            "db_exists": payload["agent"]["db_exists"],
            "tables_included": sorted(table_counts.keys()),
            "redaction_mode": payload["redaction"]["mode"],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export redacted Agent diagnostics")
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("AGENT_DB", DEFAULT_DB)), help="Agent SQLite database path")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for diagnostics bundle")
    parser.add_argument("--confirm", action="store_true", help="Confirm export after previewing redaction scope")
    args = parser.parse_args()

    payload = build_payload(args.db)
    if not args.confirm:
        print(render_preview(payload))
        print("Refusing to export diagnostics without --confirm.", file=sys.stderr)
        return 3

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"agent-diagnostics-{payload['generated_at']}.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
