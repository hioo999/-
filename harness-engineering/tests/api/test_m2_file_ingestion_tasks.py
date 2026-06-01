#!/usr/bin/env python3
from __future__ import annotations

import base64
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


agent_server = load_module("agent_server_file_ingestion", ROOT / "services" / "agent-api" / "server.py")


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


class FileIngestionTaskStoreTest(unittest.TestCase):
    def test_upload_rejects_path_traversal_extension_and_bad_base64(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "测试案件"})
                content = base64.b64encode(b"hello").decode("ascii")
                with self.assertRaises(ValueError):
                    store.save_uploaded_file(case["id"], "../secret.txt", content)
                with self.assertRaises(ValueError):
                    store.save_uploaded_file(case["id"], "malware.exe", content)
                with self.assertRaises(ValueError):
                    store.save_uploaded_file(case["id"], "sample.txt", "not-base64")
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_failed_parse_creates_failed_task_and_retry_can_succeed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "测试案件"})
                file = store.save_uploaded_file(case["id"], "empty.txt", base64.b64encode(b"").decode("ascii"))
                with self.assertRaises(ValueError):
                    store.parse_file(file["id"])
                failed_tasks = store.list_tasks(file_id=file["id"], status="failed")
                self.assertEqual(len(failed_tasks), 1)
                file_path = Path(store.get_file(file["id"])["file_path"])
                file_path.write_text("乙方应在2026年5月1日前付款。", "utf-8")
                retried = store.retry_task(failed_tasks[0]["id"])
                self.assertEqual(retried["status"], "indexed")
                task = store.get_task(failed_tasks[0]["id"])
                self.assertEqual(task["status"], "success")
                self.assertEqual(task["retry_count"], 1)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_directory_permission_check_does_not_create_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            missing = Path(tmp) / "missing"
            result = store.check_directory_permission(str(missing))
            self.assertFalse(result["exists"])
            self.assertEqual(result["permission_status"], "denied")
            self.assertFalse(missing.exists())
            with self.assertRaises(ValueError):
                store.add_data_source(str(missing))
            self.assertFalse(missing.exists())

    def test_upload_enqueues_pending_task_and_deduplicates_by_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "测试案件"})
                content = base64.b64encode("同一份合同内容".encode("utf-8")).decode("ascii")
                first = store.save_uploaded_file(case["id"], "contract-a.txt", content)
                second = store.save_uploaded_file(case["id"], "contract-b.txt", content)
                self.assertFalse(first["deduplicated"])
                self.assertTrue(second["deduplicated"])
                self.assertEqual(first["id"], second["id"])
                tasks = store.list_tasks(file_id=first["id"])
                self.assertEqual(len(tasks), 1)
                self.assertEqual(tasks[0]["status"], "pending")
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_scan_data_source_adds_supported_files_skips_duplicates_and_enqueues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            (root / "a.txt").write_text("甲方提交付款凭证。", "utf-8")
            (root / "b.md").write_text("乙方确认收到货物。", "utf-8")
            (root / "ignored.exe").write_text("unsupported", "utf-8")
            (root / "duplicate.txt").write_text("甲方提交付款凭证。", "utf-8")
            store = agent_server.Store(Path(tmp) / "agent.db")
            case = store.create_case({"title": "测试案件"})
            source = store.add_data_source(str(root))
            result = store.scan_data_source(source["id"], case["id"])
            self.assertEqual(result["discovered_count"], 4)
            self.assertEqual(result["added_count"], 2)
            self.assertEqual(result["duplicate_count"], 1)
            self.assertEqual(result["unsupported_count"], 1)
            self.assertEqual(result["enqueued_count"], 2)
            self.assertEqual(len(store.list_files(case["id"])), 2)
            self.assertEqual(len(store.list_tasks(case_id=case["id"], status="pending")), 2)

    def test_run_pending_tasks_processes_enqueued_uploads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "测试案件"})
                for idx in range(2):
                    content = base64.b64encode(f"第{idx}份材料，甲方已经付款。".encode("utf-8")).decode("ascii")
                    store.save_uploaded_file(case["id"], f"material-{idx}.txt", content)
                self.assertEqual(len(store.list_tasks(case_id=case["id"], status="pending")), 2)
                result = store.run_pending_tasks(limit=10)
                self.assertEqual(result["picked_count"], 2)
                self.assertEqual(result["success_count"], 2)
                self.assertEqual(len(store.list_tasks(case_id=case["id"], status="pending")), 0)
                self.assertEqual(len(store.list_tasks(case_id=case["id"], status="success")), 2)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir


class FileIngestionTaskApiTest(unittest.TestCase):
    def test_task_and_permission_endpoints_require_auth_and_return_data(self) -> None:
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
                status, _ = request_json(base_url, "GET", "/api/agent/tasks")
                self.assertEqual(status, 401)

                status, login = request_json(base_url, "POST", "/api/agent/auth/login", {"account": "admin", "password": "admin"})
                self.assertEqual(status, 200)
                token = login["data"]["token"]

                status, body = request_json(base_url, "POST", "/api/agent/data-sources/check-permission", {"path": tmp}, token=token)
                self.assertEqual(status, 200)
                self.assertTrue(body["data"]["exists"])

                status, case_body = request_json(base_url, "POST", "/api/agent/cases", {"title": "测试案件"}, token=token)
                self.assertEqual(status, 200)
                case_id = case_body["data"]["id"]

                content = base64.b64encode("乙方逾期付款。".encode("utf-8")).decode("ascii")
                status, file_body = request_json(base_url, "POST", "/api/agent/files/upload", {"case_id": case_id, "file_name": "sample.txt", "content_base64": content}, token=token)
                self.assertEqual(status, 200)
                file_id = file_body["data"]["id"]
                self.assertIn("task_id", file_body["data"])

                status, parse_body = request_json(base_url, "POST", "/api/agent/files/parse", {"file_id": file_id}, token=token)
                self.assertEqual(status, 200)
                task_id = parse_body["data"]["task_id"]

                status, tasks_body = request_json(base_url, "GET", f"/api/agent/tasks?file_id={file_id}", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(tasks_body["data"][0]["id"], task_id)

                status, task_body = request_json(base_url, "GET", f"/api/agent/tasks/{task_id}", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(task_body["data"]["status"], "success")

                scan_dir = Path(tmp) / "scan"
                scan_dir.mkdir()
                (scan_dir / "scan.txt").write_text("扫描目录文件。", "utf-8")
                status, source_body = request_json(base_url, "POST", "/api/agent/data-sources", {"path": str(scan_dir)}, token=token)
                self.assertEqual(status, 200)
                source_id = source_body["data"]["id"]
                status, scan_body = request_json(base_url, "POST", f"/api/agent/data-sources/{source_id}/scan", {"case_id": case_id}, token=token)
                self.assertEqual(status, 200)
                self.assertEqual(scan_body["data"]["added_count"], 1)
                self.assertEqual(scan_body["data"]["enqueued_count"], 1)

                status, run_body = request_json(base_url, "POST", "/api/agent/tasks/run-pending", {"limit": 10}, token=token)
                self.assertEqual(status, 200)
                self.assertGreaterEqual(run_body["data"]["success_count"], 1)
            finally:
                server.shutdown()
                server.server_close()
                agent_server.STORE.close()
                agent_server.STORE = original_store
                agent_server.DATA_DIR = original_data_dir
                agent_server.STORAGE_DIR = original_storage_dir


if __name__ == "__main__":
    unittest.main()
