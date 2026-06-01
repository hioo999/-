#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
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


agent_server = load_module("agent_server_case_isolation", ROOT / "services" / "agent-api" / "server.py")


def upload_and_index(store, case_id: str, filename: str, text: str) -> dict:
    content = base64.b64encode(text.encode("utf-8")).decode("ascii")
    file = store.save_uploaded_file(case_id, filename, content)
    store.parse_file(file["id"])
    return file


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


class CaseIsolationCitationStoreTest(unittest.TestCase):
    def test_rag_does_not_cross_cases_and_citations_are_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                case_a = store.create_case({"title": "买卖合同纠纷"})
                case_b = store.create_case({"title": "劳动争议"})
                upload_and_index(store, case_a["id"], "contract.txt", "乙方应在2026年5月1日前付款。乙方逾期付款，应承担违约责任。")
                upload_and_index(store, case_b["id"], "labor.txt", "劳动者主张未签劳动合同二倍工资，并要求确认劳动关系。")

                answer_a = store.ask(case_a["id"], "乙方是否逾期付款？")
                self.assertFalse(answer_a["insufficient_evidence"])
                self.assertGreaterEqual(len(answer_a["citations"]), 1)
                for citation in answer_a["citations"]:
                    self.assertEqual(citation["case_id"], case_a["id"])
                    self.assertEqual(citation["file_name"], "contract.txt")
                    self.assertIn("chunk_id", citation)
                    self.assertIn("chunk_index", citation)
                    self.assertIn("paragraph_ref", citation)
                    self.assertIn("quote_text", citation)
                    self.assertNotIn("劳动关系", citation["quote_text"])

                no_cross = store.ask(case_a["id"], "是否存在未签劳动合同二倍工资？")
                self.assertTrue(no_cross["insufficient_evidence"])
                self.assertEqual(no_cross["citations"], [])
                self.assertIn("未检索到充分依据", no_cross["answer"])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_chat_history_can_be_filtered_by_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                case_a = store.create_case({"title": "A案"})
                case_b = store.create_case({"title": "B案"})
                upload_and_index(store, case_a["id"], "a.txt", "甲方支付货款，乙方交付货物。")
                upload_and_index(store, case_b["id"], "b.txt", "劳动者要求加班费。")
                session_a = store.ask(case_a["id"], "甲方是否支付货款？")["session_id"]
                store.ask(case_b["id"], "劳动者是否要求加班费？")
                chats_a = store.list_chats(case_a["id"])
                self.assertEqual(len(chats_a), 1)
                self.assertEqual(chats_a[0]["id"], session_a)
                messages = store.get_chat_messages(session_a)
                self.assertEqual([msg["role"] for msg in messages], ["user", "assistant"])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir


class CaseIsolationCitationApiTest(unittest.TestCase):
    def test_chat_history_api_filters_by_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_store = agent_server.STORE
            original_data_dir = agent_server.DATA_DIR
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.DATA_DIR = Path(tmp)
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            store = agent_server.Store(Path(tmp) / "agent.db")
            case = store.create_case({"title": "API案"})
            upload_and_index(store, case["id"], "api.txt", "乙方逾期付款。")
            session_id = store.ask(case["id"], "乙方是否逾期付款？")["session_id"]
            agent_server.STORE = store
            server = ThreadingHTTPServer(("127.0.0.1", 0), agent_server.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            try:
                status, login = request_json(base_url, "POST", "/api/agent/auth/login", {"account": "admin", "password": "admin"})
                self.assertEqual(status, 200)
                token = login["data"]["token"]
                query = urllib.parse.urlencode({"case_id": case["id"]})
                status, chats = request_json(base_url, "GET", f"/api/agent/chats?{query}", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(chats["data"][0]["id"], session_id)
                status, messages = request_json(base_url, "GET", f"/api/agent/chats/{session_id}", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(len(messages["data"]), 2)
            finally:
                server.shutdown()
                server.server_close()
                agent_server.STORE.close()
                agent_server.STORE = original_store
                agent_server.DATA_DIR = original_data_dir
                agent_server.STORAGE_DIR = original_storage_dir


if __name__ == "__main__":
    unittest.main()
