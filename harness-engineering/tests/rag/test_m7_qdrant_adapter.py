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


agent_server = load_module("agent_server_m7_qdrant", ROOT / "services" / "agent-api" / "server.py")


class EmbeddingHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        text = str(payload.get("input", ""))
        vector = [1.0, 0.0] if "付款" in text or "乙方" in text else [0.0, 1.0]
        response = {"data": [{"embedding": vector}]}
        data = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:
        return None


class QdrantHandler(BaseHTTPRequestHandler):
    collection_created = False
    points: list[dict] = []
    requests: list[dict] = []

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
        QdrantHandler.requests.append({"method": "GET", "path": self.path})
        if self.path == "/collections/case_chunks" and QdrantHandler.collection_created:
            self._send_json(200, {"result": {"status": "green"}})
        else:
            self._send_json(404, {"status": "not_found"})

    def do_PUT(self) -> None:  # noqa: N802
        payload = self._json()
        QdrantHandler.requests.append({"method": "PUT", "path": self.path, "payload": payload})
        if self.path == "/collections/case_chunks":
            QdrantHandler.collection_created = True
            self._send_json(200, {"result": True})
            return
        if self.path.startswith("/collections/case_chunks/points"):
            QdrantHandler.points.extend(payload.get("points", []))
            self._send_json(200, {"result": {"operation_id": 1, "status": "completed"}})
            return
        self._send_json(404, {"status": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        payload = self._json()
        QdrantHandler.requests.append({"method": "POST", "path": self.path, "payload": payload})
        if self.path == "/collections/case_chunks/points/search":
            results = []
            for point in QdrantHandler.points:
                results.append({"id": point["id"], "score": 0.99, "payload": point["payload"]})
            self._send_json(200, {"result": results[: payload.get("limit", 5)]})
            return
        self._send_json(404, {"status": "not_found"})

    def log_message(self, fmt: str, *args: object) -> None:
        return None


def upload_and_index(store, case_id: str, filename: str, text: str) -> dict:
    content = base64.b64encode(text.encode("utf-8")).decode("ascii")
    file = store.save_uploaded_file(case_id, filename, content)
    store.run_pending_tasks()
    return file


class M7QdrantAdapterTest(unittest.TestCase):
    def test_qdrant_upsert_and_search_are_used_when_configured(self) -> None:
        QdrantHandler.collection_created = False
        QdrantHandler.points = []
        QdrantHandler.requests = []
        model_server = ThreadingHTTPServer(("127.0.0.1", 0), EmbeddingHandler)
        qdrant_server = ThreadingHTTPServer(("127.0.0.1", 0), QdrantHandler)
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
                case = store.create_case({"title": "买卖合同纠纷"})
                store.save_model_config(
                    {
                        "provider": "openai-compatible",
                        "base_url": f"http://127.0.0.1:{model_server.server_port}/v1",
                        "chat_model": "local-chat",
                        "embedding_model": "local-embedding",
                        "api_key": "sk-qdrant-secret",
                    }
                )
                upload_and_index(store, case["id"], "payment.txt", "乙方应在2026年5月1日前付款。乙方逾期付款。")

                self.assertEqual(len(QdrantHandler.points), 1)
                refs = store.conn.execute("SELECT * FROM vector_index_refs").fetchall()
                self.assertEqual(refs[0]["vector_collection"], "qdrant:case_chunks")

                hits = store.search(case["id"], "乙方付款风险")
                self.assertGreaterEqual(len(hits), 1)
                self.assertEqual(hits[0]["retrieval_mode"], "qdrant")
                status = store.status_payload()
                self.assertTrue(status["qdrant_configured"])
                self.assertEqual(status["vector_store"], "qdrant:case_chunks")
                search_requests = [item for item in QdrantHandler.requests if item["method"] == "POST" and item["path"] == "/collections/case_chunks/points/search"]
                self.assertEqual(len(search_requests), 1)
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
