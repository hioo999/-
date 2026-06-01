#!/usr/bin/env python3
"""Minimal V4.1 platform control-plane API.

This service intentionally stores only control-plane data. It rejects known
business-data fields at the API boundary so the platform remains blind to
lawyer business data.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


ROOT = os.path.dirname(__file__)
DB_PATH = os.environ.get("PLATFORM_DB", os.path.join(os.path.dirname(__file__), "data", "platform.db"))
HOST = os.environ.get("PLATFORM_HOST", "127.0.0.1")
PORT = int(os.environ.get("PLATFORM_PORT", "8100"))

def load_local_module(name: str, relative_path: str):
    path = os.path.join(ROOT, relative_path)
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


forbidden_fields_module = load_local_module("platform_forbidden_fields", "app/security/forbidden_fields.py")
health_schema_module = load_local_module("platform_health_schema", "app/schemas/health.py")

FORBIDDEN_FIELDS = set(forbidden_fields_module.FORBIDDEN_FIELDS)
HEALTH_ALLOWED_FIELDS = set(health_schema_module.HEALTH_ALLOWED_FIELDS)
REGISTER_ALLOWED_FIELDS = set(health_schema_module.REGISTER_ALLOWED_FIELDS)
HEARTBEAT_ALLOWED_FIELDS = set(health_schema_module.HEARTBEAT_ALLOWED_FIELDS)
find_forbidden_fields = forbidden_fields_module.find_forbidden_fields
ensure_allowed_fields = forbidden_fields_module.ensure_allowed_fields


def now() -> int:
    return int(time.time())


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path: str = DB_PATH) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._closed = False
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS licenses (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                license_key_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                expired_at INTEGER,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_instances (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                license_id TEXT,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                last_heartbeat_at INTEGER,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_heartbeats (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL,
                task_pending_count INTEGER DEFAULT 0,
                task_running_count INTEGER DEFAULT 0,
                task_failed_count INTEGER DEFAULT 0,
                error_code TEXT,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                reported_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS platform_audit_logs (
                id TEXT PRIMARY KEY,
                operator_id TEXT NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        if not self._closed:
            self.conn.close()
            self._closed = True

    def __del__(self) -> None:  # pragma: no cover - cleanup fallback
        try:
            self.close()
        except Exception:
            pass

    def audit(self, action: str, target_type: str, target_id: str, operator_id: str = "system") -> None:
        self.conn.execute(
            "INSERT INTO platform_audit_logs VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), operator_id, action, target_type, target_id, now()),
        )
        self.conn.commit()

    def create_org(self, name: str) -> dict[str, Any]:
        org_id = f"t_{uuid.uuid4().hex[:12]}"
        ts = now()
        self.conn.execute("INSERT INTO organizations VALUES (?, ?, ?, ?, ?)", (org_id, name, "active", ts, ts))
        self.conn.commit()
        self.audit("ORG_CREATED", "organization", org_id)
        return {"id": org_id, "name": name, "status": "active"}

    def create_license(self, organization_id: str, license_key: str | None = None, expired_at: int | None = None) -> dict[str, Any]:
        license_id = f"lic_{uuid.uuid4().hex[:12]}"
        raw_key = license_key or f"lk_{uuid.uuid4().hex}"
        key_hash = hash_value(raw_key)
        self.conn.execute(
            "INSERT INTO licenses VALUES (?, ?, ?, ?, ?, ?)",
            (license_id, organization_id, key_hash, "active", expired_at, now()),
        )
        self.conn.commit()
        self.audit("LICENSE_CREATED", "license", license_id)
        return {"id": license_id, "license_key": raw_key, "license_key_hash": key_hash, "status": "active"}

    def find_license(self, key_hash: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM licenses WHERE license_key_hash = ?", (key_hash,)).fetchone()

    def register_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_allowed_fields(payload, REGISTER_ALLOWED_FIELDS)
        license_row = self.find_license(str(payload.get("license_key_hash", "")))
        if not license_row or license_row["status"] != "active":
            raise PermissionError("license is not active")
        agent_id = str(payload["agent_id"])
        ts = now()
        self.conn.execute(
            """
            INSERT INTO agent_instances (id, organization_id, license_id, version, status, last_heartbeat_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET version=excluded.version, status='online', last_heartbeat_at=excluded.last_heartbeat_at
            """,
            (agent_id, license_row["organization_id"], license_row["id"], payload["agent_version"], "online", ts, ts),
        )
        self.conn.commit()
        self.audit("AGENT_REGISTERED", "agent", agent_id)
        return {"agent_id": agent_id, "license_status": "active", "heartbeat_interval_seconds": 60}

    def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_allowed_fields(payload, HEARTBEAT_ALLOWED_FIELDS)
        agent_id = str(payload["agent_id"])
        self.conn.execute(
            "UPDATE agent_instances SET status = ?, version = ?, last_heartbeat_at = ? WHERE id = ?",
            (payload.get("status", "online"), payload.get("agent_version", "unknown"), now(), agent_id),
        )
        self.conn.commit()
        return {"agent_id": agent_id, "status": payload.get("status", "online")}

    def health(self, payload: dict[str, Any]) -> dict[str, Any]:
        ensure_allowed_fields(payload, HEALTH_ALLOWED_FIELDS)
        agent_id = str(payload["agent_id"])
        self.conn.execute(
            "INSERT INTO agent_heartbeats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                agent_id,
                payload.get("status", "online"),
                int(payload.get("task_pending_count", 0)),
                int(payload.get("task_running_count", 0)),
                int(payload.get("task_failed_count", 0)),
                payload.get("error_code"),
                payload.get("cpu_usage"),
                payload.get("memory_usage"),
                payload.get("disk_usage"),
                now(),
            ),
        )
        self.conn.execute("UPDATE agent_instances SET status = ?, last_heartbeat_at = ? WHERE id = ?", (payload.get("status", "online"), now(), agent_id))
        self.conn.commit()
        return {"agent_id": agent_id, "accepted_fields": sorted(payload.keys())}

    def list_agents(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT id, organization_id, version, status, last_heartbeat_at, created_at FROM agent_instances ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def audit_logs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM platform_audit_logs ORDER BY created_at DESC LIMIT 100").fetchall()
        return [dict(row) for row in rows]


STORE = Store()


class Handler(BaseHTTPRequestHandler):
    server_version = "V41PlatformAPI/0.1"

    def _send(self, status: int, body: Any, content_type: str = "application/json") -> None:
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _ok(self, data: Any) -> None:
        self._send(200, {"code": 0, "message": "ok", "data": data})

    def _error(self, status: int, message: str) -> None:
        self._send(status, {"code": status, "message": message, "data": None})

    def do_GET(self) -> None:  # noqa: N802
        try:
            if self.path == "/health":
                self._ok({"status": "ok", "service": "platform-api"})
            elif self.path == "/api/platform/agents":
                self._ok(STORE.list_agents())
            elif self.path == "/api/platform/audit-logs":
                self._ok(STORE.audit_logs())
            elif self.path == "/":
                html = """<html><head><title>Platform Console</title></head><body><h1>平台控制台</h1><p>仅显示组织、授权、Agent 状态和脱敏健康数据。平台不可见律师业务数据。</p></body></html>"""
                self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._error(404, "not found")
        except Exception as exc:  # pragma: no cover
            self._error(500, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._json()
            forbidden = find_forbidden_fields(payload)
            if forbidden:
                self._error(400, f"forbidden business fields: {sorted(forbidden)}")
                return
            if self.path == "/api/platform/organizations":
                self._ok(STORE.create_org(str(payload.get("name", "未命名组织"))))
            elif self.path == "/api/platform/licenses":
                self._ok(STORE.create_license(str(payload["organization_id"]), payload.get("license_key"), payload.get("expired_at")))
            elif self.path == "/api/platform/agents/register":
                self._ok(STORE.register_agent(payload))
            elif self.path == "/api/platform/agents/heartbeat":
                self._ok(STORE.heartbeat(payload))
            elif self.path == "/api/platform/agents/health":
                self._ok(STORE.health(payload))
            else:
                self._error(404, "not found")
        except KeyError as exc:
            self._error(400, f"missing field: {exc}")
        except PermissionError as exc:
            self._error(403, str(exc))
        except ValueError as exc:
            self._error(400, str(exc))
        except Exception as exc:  # pragma: no cover
            self._error(500, str(exc))

    def log_message(self, fmt: str, *args: Any) -> None:
        safe = fmt % args
        if find_forbidden_fields({"message": safe}):
            safe = "[redacted forbidden platform log]"
        sys.stderr.write(f"{self.address_string()} - {safe}\n")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"platform-api listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
