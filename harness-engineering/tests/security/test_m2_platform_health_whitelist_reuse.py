#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


platform_server = load_module("platform_server_reuse", ROOT / "services" / "platform-api" / "server.py")
platform_forbidden = load_module(
    "platform_forbidden_reuse",
    ROOT / "services" / "platform-api" / "app" / "security" / "forbidden_fields.py",
)
platform_health = load_module(
    "platform_health_reuse",
    ROOT / "services" / "platform-api" / "app" / "schemas" / "health.py",
)
agent_server = load_module("agent_server_health_reuse", ROOT / "services" / "agent-api" / "server.py")


def request_json(base_url: str, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base_url + path, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 - local test server
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class PlatformWhitelistReuseTest(unittest.TestCase):
    def test_platform_server_reuses_app_forbidden_fields_and_health_schema(self) -> None:
        self.assertEqual(platform_server.FORBIDDEN_FIELDS, set(platform_forbidden.FORBIDDEN_FIELDS))
        self.assertEqual(platform_server.HEALTH_ALLOWED_FIELDS, set(platform_health.HEALTH_ALLOWED_FIELDS))
        with self.assertRaises(ValueError):
            platform_server.ensure_allowed_fields(
                {"tenant_id": "t_1", "agent_id": "ag_1", "question": "案件问题"},
                platform_server.HEALTH_ALLOWED_FIELDS,
            )

    def test_platform_health_api_rejects_forbidden_business_field_injection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_store = platform_server.STORE
            platform_server.STORE = platform_server.Store(str(Path(tmp) / "platform.db"))
            server = ThreadingHTTPServer(("127.0.0.1", 0), platform_server.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            try:
                status, org = request_json(base_url, "POST", "/api/platform/organizations", {"name": "测试律所"})
                self.assertEqual(status, 200)
                status, license_body = request_json(base_url, "POST", "/api/platform/licenses", {"organization_id": org["data"]["id"]})
                self.assertEqual(status, 200)
                status, registered = request_json(
                    base_url,
                    "POST",
                    "/api/platform/agents/register",
                    {
                        "tenant_id": org["data"]["id"],
                        "agent_id": "ag_1",
                        "agent_version": "4.1.0",
                        "install_fingerprint": "fp",
                        "license_key_hash": license_body["data"]["license_key_hash"],
                    },
                )
                self.assertEqual(status, 200)
                self.assertEqual(registered["data"]["agent_id"], "ag_1")

                status, rejected = request_json(
                    base_url,
                    "POST",
                    "/api/platform/agents/health",
                    {
                        "tenant_id": org["data"]["id"],
                        "agent_id": "ag_1",
                        "agent_version": "4.1.0",
                        "status": "online",
                        "file_name": "secret.pdf",
                    },
                )
                self.assertEqual(status, 400)
                self.assertIn("forbidden business fields", rejected["message"])
            finally:
                server.shutdown()
                server.server_close()
                platform_server.STORE.close()
                platform_server.STORE = original_store


class AgentHealthReporterReuseTest(unittest.TestCase):
    def test_agent_health_payload_uses_reporter_and_excludes_business_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            payload = store.health_payload()
            self.assertTrue(set(payload).issubset(agent_server.HEALTH_ALLOWED_FIELDS))
            payload_json = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("file_name", payload_json)
            self.assertNotIn("question", payload_json)
            self.assertNotIn("api_key", payload_json)

    def test_agent_health_reporter_rejects_injected_business_fields(self) -> None:
        with self.assertRaises(ValueError):
            agent_server.to_platform_health_payload(
                {
                    "tenant_id": "t_1",
                    "agent_id": "ag_1",
                    "status": "online",
                    "api_key": "sk-secret",
                }
            )


if __name__ == "__main__":
    unittest.main()
