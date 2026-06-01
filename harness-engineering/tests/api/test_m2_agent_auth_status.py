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


agent_server = load_module("agent_server_auth", ROOT / "services" / "agent-api" / "server.py")


def request_json(base_url: str, method: str, path: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 - local test server
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class AgentAuthStatusApiTest(unittest.TestCase):
    def test_protected_agent_routes_require_login_and_accept_bearer_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_store = agent_server.STORE
            original_data_dir = agent_server.DATA_DIR
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.DATA_DIR = Path(tmp)
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            agent_server.STORE = agent_server.Store(Path(tmp) / "agent.db")
            server = ThreadingHTTPServer(("127.0.0.1", 0), agent_server.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            try:
                status, body = request_json(base_url, "GET", "/api/agent/cases")
                self.assertEqual(status, 401)
                self.assertIn("missing bearer token", body["message"])

                status, body = request_json(base_url, "POST", "/api/agent/auth/login", {"account": "admin", "password": "admin"})
                self.assertEqual(status, 200)
                token = body["data"]["token"]
                self.assertTrue(token.startswith("sess_"))

                status, body = request_json(base_url, "GET", "/api/agent/auth/me", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(body["data"]["account"], "admin")

                status, body = request_json(base_url, "GET", "/api/agent/status", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(body["data"]["database"], "ok")

                status, body = request_json(base_url, "GET", "/api/agent/cases", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(body["data"], [])
            finally:
                server.shutdown()
                server.server_close()
                agent_server.STORE.close()
                agent_server.STORE = original_store
                agent_server.DATA_DIR = original_data_dir
                agent_server.STORAGE_DIR = original_storage_dir


if __name__ == "__main__":
    unittest.main()
