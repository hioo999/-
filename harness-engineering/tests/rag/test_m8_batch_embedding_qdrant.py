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


agent_server = load_module("agent_server_m8_batch", ROOT / "services" / "agent-api" / "server.py")


class BatchEmbeddingHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        BatchEmbeddingHandler.requests.append({"path": self.path, "payload": payload})
        inputs = payload.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        response = {"data": [{"embedding": [1.0, float(idx)]} for idx, _ in enumerate(inputs)]}
        data = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:
        return None


class BatchQdrantHandler(BaseHTTPRequestHandler):
    collection_created = False
    upserts: list[dict] = []

    def _json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/collections/case_chunks" and BatchQdrantHandler.collection_created:
            self._send_json(200, {"result": {"status": "green"}})
        else:
            self._send_json(404, {"status": "not_found"})

    def do_PUT(self) -> None:  # noqa: N802
        payload = self._json()
        if self.path == "/collections/case_chunks":
            BatchQdrantHandler.collection_created = True
            self._send_json(200, {"result": True})
            return
        if self.path.startswith("/collections/case_chunks/points"):
            BatchQdrantHandler.upserts.append(payload)
            self._send_json(200, {"result": {"status": "completed"}})
            return
        self._send_json(404, {"status": "not_found"})

    def log_message(self, fmt: str, *args: object) -> None:
        return None


def upload_and_index(store, case_id: str, filename: str, text: str) -> dict:
    content = base64.b64encode(text.encode("utf-8")).decode("ascii")
    file = store.save_uploaded_file(case_id, filename, content)
    store.run_pending_tasks()
    return file


class M8BatchEmbeddingQdrantTest(unittest.TestCase):
    def test_file_parse_batches_embedding_request_and_qdrant_upsert(self) -> None:
        BatchEmbeddingHandler.requests = []
        BatchQdrantHandler.collection_created = False
        BatchQdrantHandler.upserts = []
        model_server = ThreadingHTTPServer(("127.0.0.1", 0), BatchEmbeddingHandler)
        qdrant_server = ThreadingHTTPServer(("127.0.0.1", 0), BatchQdrantHandler)
        threading.Thread(target=model_server.serve_forever, daemon=True).start()
        threading.Thread(target=qdrant_server.serve_forever, daemon=True).start()
        original_qdrant_url = agent_server.QDRANT_URL
        original_qdrant_collection = agent_server.QDRANT_COLLECTION
        original_storage_dir = agent_server.STORAGE_DIR
        try:
            agent_server.QDRANT_URL = f"http://127.0.0.1:{qdrant_server.server_port}"
            agent_server.QDRANT_COLLECTION = "case_chunks"
            with tempfile.TemporaryDirectory() as tmp:
                agent_server.STORAGE_DIR = Path(tmp) / "storage"
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "长文材料"})
                store.save_model_config(
                    {
                        "provider": "openai-compatible",
                        "base_url": f"http://127.0.0.1:{model_server.server_port}/v1",
                        "chat_model": "local-chat",
                        "embedding_model": "local-embedding",
                        "api_key": "sk-batch-secret",
                    }
                )
                text = "乙方逾期付款，应承担违约责任。" * 120
                upload_and_index(store, case["id"], "long.txt", text)
                chunk_count = store.chunk_count(store.list_files(case["id"])[0]["id"])

                embedding_requests = [item for item in BatchEmbeddingHandler.requests if item["path"].endswith("/embeddings")]
                self.assertEqual(len(embedding_requests), 1)
                self.assertIsInstance(embedding_requests[0]["payload"]["input"], list)
                self.assertEqual(len(embedding_requests[0]["payload"]["input"]), chunk_count)
                self.assertEqual(len(BatchQdrantHandler.upserts), 1)
                self.assertEqual(len(BatchQdrantHandler.upserts[0]["points"]), chunk_count)
                refs = store.conn.execute("SELECT * FROM vector_index_refs").fetchall()
                self.assertTrue(all(row["vector_collection"] == "qdrant:case_chunks" for row in refs))
        finally:
            agent_server.QDRANT_URL = original_qdrant_url
            agent_server.QDRANT_COLLECTION = original_qdrant_collection
            agent_server.STORAGE_DIR = original_storage_dir
            model_server.shutdown()
            model_server.server_close()
            qdrant_server.shutdown()
            qdrant_server.server_close()


if __name__ == "__main__":
    unittest.main()
