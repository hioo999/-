#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


platform_server = load_module("platform_server", ROOT / "services" / "platform-api" / "server.py")
agent_server = load_module("agent_server", ROOT / "services" / "agent-api" / "server.py")


class PlatformBoundaryTest(unittest.TestCase):
    def test_health_whitelist_rejects_business_fields(self) -> None:
        with self.assertRaises(ValueError):
            platform_server.ensure_allowed_fields(
                {
                    "tenant_id": "t_1",
                    "agent_id": "ag_1",
                    "agent_version": "4.1.0",
                    "status": "online",
                    "file_name": "张三合同.pdf",
                },
                platform_server.HEALTH_ALLOWED_FIELDS,
            )

    def test_platform_store_has_no_business_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = platform_server.Store(str(Path(tmp) / "platform.db"))
            tables = {row["name"] for row in store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            forbidden = {"case_spaces", "local_files", "document_chunks", "chat_messages", "evidences"}
            self.assertTrue(forbidden.isdisjoint(tables))

    def test_health_payload_accepts_only_whitelist(self) -> None:
        payload = {
            "tenant_id": "t_1",
            "agent_id": "ag_1",
            "agent_version": "4.1.0",
            "status": "online",
            "last_heartbeat": "123",
            "task_pending_count": 0,
            "task_running_count": 0,
            "task_failed_count": 0,
            "error_code": None,
            "cpu_usage": 0.1,
            "memory_usage": 0.2,
            "disk_usage": 0.3,
        }
        platform_server.ensure_allowed_fields(payload, platform_server.HEALTH_ALLOWED_FIELDS)


class AgentMvpFlowTest(unittest.TestCase):
    def test_local_case_file_parse_question_citation_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "agent.db"
            storage = Path(tmp) / "storage"
            original_data_dir = agent_server.DATA_DIR
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.DATA_DIR = Path(tmp)
            agent_server.STORAGE_DIR = storage
            try:
                store = agent_server.Store(db_path)
                case = store.create_case({"title": "张三诉李四买卖合同纠纷", "cause_of_action": "买卖合同纠纷"})
                fixture = ROOT / "tests" / "fixtures" / "sample_case.txt"
                content_b64 = base64.b64encode(fixture.read_bytes()).decode("ascii")
                file = store.save_uploaded_file(case["id"], "sample_case.txt", content_b64)
                parsed = store.parse_file(file["id"])
                self.assertEqual(parsed["status"], "indexed")
                answer = store.ask(case["id"], "乙方是否逾期付款？")
                self.assertIn("相关依据", answer["answer"])
                self.assertGreaterEqual(len(answer["citations"]), 1)
                self.assertEqual(answer["citations"][0]["file_name"], "sample_case.txt")
                no_basis = store.ask(case["id"], "本案是否涉及海事仲裁？")
                self.assertIn("未检索到充分依据", no_basis["answer"])
            finally:
                agent_server.DATA_DIR = original_data_dir
                agent_server.STORAGE_DIR = original_storage_dir

    def test_agent_health_payload_is_whitelisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            payload = store.health_payload()
            self.assertTrue(set(payload).issubset(agent_server.HEALTH_ALLOWED_FIELDS))
            serialized = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("file_name", serialized)
            self.assertNotIn("case_name", serialized)


if __name__ == "__main__":
    unittest.main()
