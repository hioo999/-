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
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_server = load_module("agent_server_model_config", ROOT / "services" / "agent-api" / "server.py")


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


MODEL_PAYLOAD = {
    "provider": "openai-compatible",
    "base_url": "https://llm.local/v1",
    "chat_model": "case-chat",
    "embedding_model": "case-embedding",
    "api_key": "sk-test-secret-1234567890",
}


class ModelConfigStoreSecurityTest(unittest.TestCase):
    def test_model_config_masks_secret_and_health_excludes_model_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            saved = store.save_model_config(MODEL_PAYLOAD)
            serialized = json.dumps(saved, ensure_ascii=False)
            self.assertNotIn(MODEL_PAYLOAD["api_key"], serialized)
            self.assertNotIn("api_key_encrypted", saved)
            self.assertEqual(saved["api_key_masked"], "sk-t****7890")
            self.assertTrue(saved["api_key_configured"])

            listed = store.list_model_configs()
            self.assertEqual(len(listed), 1)
            self.assertNotIn(MODEL_PAYLOAD["api_key"], json.dumps(listed, ensure_ascii=False))

            status = store.status_payload()
            self.assertEqual(status["model_connectivity"], "configured")
            self.assertEqual(status["chat_model"], "case-chat")
            self.assertEqual(status["embedding_model"], "case-embedding")
            self.assertNotIn(MODEL_PAYLOAD["api_key"], json.dumps(status, ensure_ascii=False))

            health = store.health_payload()
            health_json = json.dumps(health, ensure_ascii=False)
            self.assertNotIn("chat_model", health)
            self.assertNotIn("embedding_model", health)
            self.assertNotIn(MODEL_PAYLOAD["api_key"], health_json)

    def test_model_connectivity_failure_does_not_expose_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            saved = store.save_model_config(MODEL_PAYLOAD)
            result = store.test_model_config(saved["id"], "chat")
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["api_key_configured"])
            self.assertNotIn(MODEL_PAYLOAD["api_key"], json.dumps(result, ensure_ascii=False))

    def test_model_connectivity_success_uses_openai_compatible_endpoint(self) -> None:
        class ModelHandler(BaseHTTPRequestHandler):
            seen_paths: list[str] = []
            seen_auth: list[str] = []

            def do_POST(self) -> None:  # noqa: N802
                ModelHandler.seen_paths.append(self.path)
                ModelHandler.seen_auth.append(self.headers.get("Authorization", ""))
                length = int(self.headers.get("Content-Length", "0"))
                if length:
                    self.rfile.read(length)
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt: str, *args: object) -> None:
                return None

        server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                store = agent_server.Store(Path(tmp) / "agent.db")
                payload = dict(MODEL_PAYLOAD)
                payload["base_url"] = f"http://127.0.0.1:{server.server_port}/v1"
                saved = store.save_model_config(payload)
                chat = store.test_model_config(saved["id"], "chat")
                embedding = store.test_model_config(saved["id"], "embedding")
                self.assertEqual(chat["status"], "success")
                self.assertEqual(embedding["status"], "success")
                self.assertEqual(ModelHandler.seen_paths, ["/v1/chat/completions", "/v1/embeddings"])
                self.assertTrue(all(value == "Bearer sk-test-secret-1234567890" for value in ModelHandler.seen_auth))
                self.assertNotIn(MODEL_PAYLOAD["api_key"], json.dumps(chat, ensure_ascii=False))
        finally:
            server.shutdown()
            server.server_close()


class ModelConfigApiSecurityTest(unittest.TestCase):
    def test_model_config_api_requires_auth_and_never_returns_plaintext_secret(self) -> None:
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
                status, _ = request_json(base_url, "GET", "/api/agent/model-configs")
                self.assertEqual(status, 401)

                status, login = request_json(base_url, "POST", "/api/agent/auth/login", {"account": "admin", "password": "admin"})
                self.assertEqual(status, 200)
                token = login["data"]["token"]

                status, saved = request_json(base_url, "POST", "/api/agent/model-configs", MODEL_PAYLOAD, token=token)
                self.assertEqual(status, 200)
                config = saved["data"]
                self.assertEqual(config["api_key_masked"], "sk-t****7890")
                response_json = json.dumps(saved, ensure_ascii=False)
                self.assertNotIn(MODEL_PAYLOAD["api_key"], response_json)
                self.assertNotIn("api_key_encrypted", response_json)

                status, configs = request_json(base_url, "GET", "/api/agent/model-configs", token=token)
                self.assertEqual(status, 200)
                self.assertNotIn(MODEL_PAYLOAD["api_key"], json.dumps(configs, ensure_ascii=False))

                status, chat_test = request_json(base_url, "POST", f"/api/agent/model-configs/{config['id']}/test-chat", {}, token=token)
                self.assertEqual(status, 200)
                self.assertEqual(chat_test["data"]["status"], "failed")
                self.assertNotIn(MODEL_PAYLOAD["api_key"], json.dumps(chat_test, ensure_ascii=False))

                status, embedding_test = request_json(base_url, "POST", f"/api/agent/model-configs/{config['id']}/test-embedding", {}, token=token)
                self.assertEqual(status, 200)
                self.assertEqual(embedding_test["data"]["mode"], "embedding")

                status, agent_status = request_json(base_url, "GET", "/api/agent/status", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(agent_status["data"]["model_connectivity"], "configured")
                self.assertNotIn(MODEL_PAYLOAD["api_key"], json.dumps(agent_status, ensure_ascii=False))
            finally:
                server.shutdown()
                server.server_close()
                agent_server.STORE.close()
                agent_server.STORE = original_store
                agent_server.DATA_DIR = original_data_dir
                agent_server.STORAGE_DIR = original_storage_dir


if __name__ == "__main__":
    unittest.main()
