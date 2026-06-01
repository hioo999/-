#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_server = load_module("agent_server_m11_worker", ROOT / "services" / "agent-api" / "server.py")


class M11WorkerTest(unittest.TestCase):
    def test_worker_once_processes_pending_and_retries_failed_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            try:
                agent_server.STORAGE_DIR = Path(tmp) / "storage"
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "worker案件"})

                valid_content = base64.b64encode("甲方已经付款。".encode("utf-8")).decode("ascii")
                valid_file = store.save_uploaded_file(case["id"], "valid.txt", valid_content)
                empty_content = base64.b64encode(b"").decode("ascii")
                empty_file = store.save_uploaded_file(case["id"], "empty.txt", empty_content)

                first = store.run_worker_once(batch_size=10, max_retries=3, sync_qdrant=False)
                self.assertEqual(first["pending"]["picked_count"], 2)
                self.assertEqual(first["pending"]["success_count"], 1)
                self.assertEqual(first["pending"]["failed_count"], 1)
                self.assertEqual(store.get_file(valid_file["id"])["process_status"], "indexed")
                self.assertEqual(store.get_file(empty_file["id"])["process_status"], "failed")

                Path(store.get_file(empty_file["id"])["file_path"]).write_text("乙方已经收货。", "utf-8")
                second = store.run_worker_once(batch_size=10, max_retries=3, sync_qdrant=False)
                self.assertEqual(second["retries"]["picked_count"], 1)
                self.assertEqual(second["retries"]["success_count"], 1)
                self.assertEqual(store.get_file(empty_file["id"])["process_status"], "indexed")
                failed = store.list_tasks(case_id=case["id"], status="failed")
                self.assertEqual(failed, [])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_worker_retry_respects_max_retries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            try:
                agent_server.STORAGE_DIR = Path(tmp) / "storage"
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "worker案件"})
                empty_content = base64.b64encode(b"").decode("ascii")
                file = store.save_uploaded_file(case["id"], "empty.txt", empty_content)
                with self.assertRaises(ValueError):
                    store.parse_file(file["id"])
                task = store.list_tasks(file_id=file["id"], status="failed")[0]
                store.conn.execute("UPDATE processing_tasks SET retry_count = ? WHERE id = ?", (3, task["id"]))
                store.conn.commit()
                result = store.run_worker_once(batch_size=10, max_retries=3, sync_qdrant=False)
                self.assertEqual(result["retries"]["picked_count"], 0)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir


if __name__ == "__main__":
    unittest.main()
