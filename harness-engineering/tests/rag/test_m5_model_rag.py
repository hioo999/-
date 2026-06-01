#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_server = load_module("agent_server_m5_model_rag", ROOT / "services" / "agent-api" / "server.py")


class ModelHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        payload = json.loads(body)
        ModelHandler.requests.append({"path": self.path, "auth": self.headers.get("Authorization", ""), "payload": payload})
        response = {
            "choices": [
                {
                    "message": {
                        "content": "模型依据来源材料判断：乙方存在逾期付款风险。以上结论需律师结合完整案情核验。"
                    }
                }
            ]
        }
        data = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:
        return None


def upload_and_index(store, case_id: str, filename: str, text: str) -> dict:
    content = base64.b64encode(text.encode("utf-8")).decode("ascii")
    file = store.save_uploaded_file(case_id, filename, content)
    store.run_pending_tasks()
    return file


class M5ModelRagTest(unittest.TestCase):
    def test_rag_uses_configured_local_model_with_citations_and_without_secret_leak(self) -> None:
        ModelHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                original_storage_dir = agent_server.STORAGE_DIR
                agent_server.STORAGE_DIR = Path(tmp) / "storage"
                try:
                    store = agent_server.Store(Path(tmp) / "agent.db")
                    case = store.create_case({"title": "买卖合同纠纷"})
                    upload_and_index(store, case["id"], "contract.txt", "乙方应在2026年5月1日前付款。乙方逾期付款，应承担违约责任。")
                    store.save_model_config(
                        {
                            "provider": "openai-compatible",
                            "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                            "chat_model": "local-chat",
                            "embedding_model": "local-embedding",
                            "api_key": "sk-local-secret-abcdef",
                        }
                    )

                    result = store.ask(case["id"], "乙方是否逾期付款？")
                    serialized = json.dumps(result, ensure_ascii=False)

                    self.assertTrue(result["model_used"])
                    self.assertEqual(result["model_status"], "success")
                    self.assertIn("模型依据来源材料判断", result["answer"])
                    self.assertGreaterEqual(len(result["citations"]), 1)
                    self.assertNotIn("sk-local-secret-abcdef", serialized)
                    chat_requests = [item for item in ModelHandler.requests if item["path"] == "/v1/chat/completions"]
                    self.assertEqual(len(chat_requests), 1)
                    self.assertEqual(chat_requests[0]["auth"], "Bearer sk-local-secret-abcdef")
                    prompt = json.dumps(chat_requests[0]["payload"], ensure_ascii=False)
                    self.assertIn("乙方应在2026年5月1日前付款", prompt)
                    self.assertIn(case["id"], prompt)
                finally:
                    agent_server.STORAGE_DIR = original_storage_dir
        finally:
            server.shutdown()
            server.server_close()

    def test_rag_falls_back_to_source_summary_when_model_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "买卖合同纠纷"})
                upload_and_index(store, case["id"], "contract.txt", "乙方应在2026年5月1日前付款。乙方逾期付款，应承担违约责任。")
                store.save_model_config(
                    {
                        "provider": "openai-compatible",
                        "base_url": "http://127.0.0.1:1/v1",
                        "chat_model": "local-chat",
                        "embedding_model": "local-embedding",
                        "api_key": "sk-local-secret-abcdef",
                    }
                )
                result = store.ask(case["id"], "乙方是否逾期付款？")
                self.assertFalse(result["model_used"])
                self.assertEqual(result["model_status"], "failed")
                self.assertGreaterEqual(len(result["citations"]), 1)
                self.assertIn("根据当前案件材料", result["answer"])
                self.assertNotIn("sk-local-secret-abcdef", json.dumps(result, ensure_ascii=False))
            finally:
                agent_server.STORAGE_DIR = original_storage_dir


if __name__ == "__main__":
    unittest.main()
