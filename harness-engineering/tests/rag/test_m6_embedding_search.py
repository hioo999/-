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


agent_server = load_module("agent_server_m6_embedding_search", ROOT / "services" / "agent-api" / "server.py")


class EmbeddingModelHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        payload = json.loads(body)
        EmbeddingModelHandler.requests.append({"path": self.path, "auth": self.headers.get("Authorization", ""), "payload": payload})
        if self.path.endswith("/embeddings"):
            text = str(payload.get("input", ""))
            if "劳动" in text:
                vector = [0.0, 1.0]
            elif "付款" in text or "逾期" in text or "乙方" in text:
                vector = [1.0, 0.0]
            else:
                vector = [0.5, 0.5]
            response = {"data": [{"embedding": vector}]}
        else:
            response = {"choices": [{"message": {"content": "基于来源材料的模型回答。"}}]}
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


class M6EmbeddingSearchTest(unittest.TestCase):
    def test_parse_stores_embeddings_and_search_uses_vector_similarity_first(self) -> None:
        EmbeddingModelHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), EmbeddingModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                original_storage_dir = agent_server.STORAGE_DIR
                agent_server.STORAGE_DIR = Path(tmp) / "storage"
                try:
                    store = agent_server.Store(Path(tmp) / "agent.db")
                    case = store.create_case({"title": "买卖合同纠纷"})
                    store.save_model_config(
                        {
                            "provider": "openai-compatible",
                            "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                            "chat_model": "local-chat",
                            "embedding_model": "local-embedding",
                            "api_key": "sk-embedding-secret",
                        }
                    )
                    upload_and_index(store, case["id"], "payment.txt", "乙方应在2026年5月1日前付款。乙方逾期付款，应承担违约责任。")
                    upload_and_index(store, case["id"], "labor.txt", "劳动者主张未签劳动合同二倍工资，并要求确认劳动关系。")

                    self.assertEqual(store.embedding_vector_count(), 2)
                    hits = store.search(case["id"], "乙方付款风险", limit=2)
                    self.assertGreaterEqual(len(hits), 1)
                    self.assertEqual(hits[0]["file_name"], "payment.txt")
                    self.assertEqual(hits[0]["retrieval_mode"], "embedding")

                    answer = store.ask(case["id"], "乙方付款风险")
                    self.assertEqual(answer["citations"][0]["retrieval_mode"], "embedding")
                    self.assertNotIn("sk-embedding-secret", json.dumps(answer, ensure_ascii=False))
                    embedding_paths = [item["path"] for item in EmbeddingModelHandler.requests if item["path"].endswith("/embeddings")]
                    self.assertGreaterEqual(len(embedding_paths), 3)
                    self.assertTrue(all(item["auth"] == "Bearer sk-embedding-secret" for item in EmbeddingModelHandler.requests))
                    status = store.status_payload()
                    self.assertEqual(status["vector_store"], "local_sqlite_embedding_vectors")
                    self.assertEqual(status["embedding_vector_count"], 2)
                finally:
                    agent_server.STORAGE_DIR = original_storage_dir
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
