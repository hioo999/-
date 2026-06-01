#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import os
import subprocess
import sys
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


try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - optional target runtime dependency
    TestClient = None


def fastapi_routes() -> set[tuple[str, str]]:
    agent_fastapi = load_module("agent_fastapi_m14_routes", ROOT / "services" / "agent-api" / "app" / "main.py")
    if agent_fastapi.app is None:
        raise unittest.SkipTest("FastAPI is not installed")
    app = agent_fastapi.create_app(object())
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        for method in methods:
            if method in {"GET", "POST", "PATCH", "DELETE"}:
                routes.add((method, path))
    return routes


class M14FastApiContractTest(unittest.TestCase):
    def test_importing_fastapi_entrypoint_does_not_create_default_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            db_path = data_dir / "agent.db"
            script = f"""
import importlib.util
import os
from pathlib import Path

os.environ['AGENT_DATA_DIR'] = {str(data_dir)!r}
os.environ['AGENT_STORAGE_DIR'] = {str(data_dir / 'storage')!r}
os.environ['AGENT_DB'] = {str(db_path)!r}
spec = importlib.util.spec_from_file_location('agent_fastapi_import_probe', {str(ROOT / 'services' / 'agent-api' / 'app' / 'main.py')!r})
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
if Path({str(db_path)!r}).exists():
    raise SystemExit('database was created during import')
"""
            completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_fastapi_entrypoint_references_v42_knowledge_base_routers(self) -> None:
        main_source = (ROOT / "services" / "agent-api" / "app" / "main.py").read_text("utf-8")
        for router_name in ("knowledge_bases", "folders", "permissions"):
            self.assertIn(router_name, main_source)
            self.assertTrue((ROOT / "services" / "agent-api" / "app" / "routers" / f"{router_name}.py").exists())

    def test_fastapi_entrypoint_declares_parallel_core_agent_routes(self) -> None:
        expected = {
            ("GET", "/"),
            ("GET", "/health"),
            ("POST", "/api/agent/auth/login"),
            ("POST", "/api/agent/auth/logout"),
            ("GET", "/api/agent/auth/me"),
            ("GET", "/api/agent/status"),
            ("GET", "/api/agent/status/dependencies"),
            ("POST", "/api/agent/activate"),
            ("POST", "/api/agent/report-health"),
            ("POST", "/api/agent/data-sources/check-permission"),
            ("GET", "/api/agent/data-sources"),
            ("POST", "/api/agent/data-sources"),
            ("POST", "/api/agent/data-sources/{data_source_id}/scan"),
            ("GET", "/api/agent/knowledge-bases"),
            ("POST", "/api/agent/knowledge-bases"),
            ("GET", "/api/agent/knowledge-bases/{kb_id}"),
            ("PATCH", "/api/agent/knowledge-bases/{kb_id}"),
            ("POST", "/api/agent/knowledge-bases/{kb_id}/review"),
            ("POST", "/api/agent/knowledge-bases/{kb_id}/archive"),
            ("GET", "/api/agent/knowledge-bases/{kb_id}/tree"),
            ("GET", "/api/agent/knowledge-bases/{kb_id}/members"),
            ("POST", "/api/agent/knowledge-bases/{kb_id}/members"),
            ("POST", "/api/agent/knowledge-bases/{kb_id}/members/{member_id}/revoke"),
            ("GET", "/api/agent/knowledge-bases/{kb_id}/stats"),
            ("POST", "/api/agent/folders"),
            ("PATCH", "/api/agent/folders/{folder_id}"),
            ("DELETE", "/api/agent/folders/{folder_id}"),
            ("POST", "/api/agent/folders/{folder_id}/restore"),
            ("GET", "/api/agent/permissions/resource"),
            ("GET", "/api/agent/permissions/effective"),
            ("POST", "/api/agent/permissions/grant"),
            ("POST", "/api/agent/permissions/deny"),
            ("POST", "/api/agent/permissions/check"),
            ("DELETE", "/api/agent/permissions/{entry_id}"),
            ("GET", "/api/agent/tasks"),
            ("GET", "/api/agent/tasks/{task_id}"),
            ("POST", "/api/agent/tasks/run-pending"),
            ("POST", "/api/agent/tasks/{task_id}/retry"),
            ("POST", "/api/agent/worker/run-once"),
            ("GET", "/api/agent/cases"),
            ("POST", "/api/agent/cases"),
            ("GET", "/api/agent/cases/{case_id}"),
            ("POST", "/api/agent/cases/summary"),
            ("GET", "/api/agent/files"),
            ("POST", "/api/agent/files/upload"),
            ("POST", "/api/agent/files/parse"),
            ("PATCH", "/api/agent/files/{file_id}"),
            ("DELETE", "/api/agent/files/{file_id}"),
            ("POST", "/api/agent/files/{file_id}/restore"),
            ("GET", "/api/agent/model-configs"),
            ("POST", "/api/agent/model-configs"),
            ("GET", "/api/agent/model-configs/{config_id}"),
            ("POST", "/api/agent/model-configs/{config_id}/test-chat"),
            ("POST", "/api/agent/model-configs/{config_id}/test-embedding"),
            ("POST", "/api/agent/rag/query"),
            ("POST", "/api/agent/rag/retrieve"),
            ("POST", "/api/agent/vector-store/sync-qdrant"),
            ("GET", "/api/agent/chats"),
            ("GET", "/api/agent/chats/{session_id}"),
            ("GET", "/api/agent/evidences"),
            ("POST", "/api/agent/evidences"),
            ("GET", "/api/agent/audit-logs"),
        }
        missing = expected - fastapi_routes()
        self.assertEqual(missing, set())


@unittest.skipIf(TestClient is None, "FastAPI is not installed")
class M14FastApiEntrypointTest(unittest.TestCase):
    def test_fastapi_entrypoint_reuses_store_for_core_agent_apis(self) -> None:
        agent_fastapi = load_module("agent_fastapi_m14", ROOT / "services" / "agent-api" / "app" / "main.py")
        agent_server = agent_fastapi.agent_server
        with tempfile.TemporaryDirectory() as tmp:
            original_data_dir = agent_server.DATA_DIR
            original_storage_dir = agent_server.STORAGE_DIR
            store = None
            try:
                agent_server.DATA_DIR = Path(tmp)
                agent_server.STORAGE_DIR = Path(tmp) / "storage"
                store = agent_server.Store(Path(tmp) / "agent.db")
                app = agent_fastapi.create_app(store)
                client = TestClient(app, raise_server_exceptions=False)

                unauthorized = client.get("/api/agent/cases")
                self.assertEqual(unauthorized.status_code, 401)
                self.assertIn("missing bearer token", unauthorized.json()["message"])

                invalid_token = client.get("/api/agent/cases", headers={"Authorization": "Bearer invalid"})
                self.assertEqual(invalid_token.status_code, 401)
                self.assertIn("invalid or expired bearer token", invalid_token.json()["message"])

                missing = client.get("/api/agent/does-not-exist")
                self.assertEqual(missing.status_code, 404)
                self.assertEqual(missing.json(), {"code": 404, "message": "not found", "data": None})

                wrong_method = client.put("/api/agent/cases")
                self.assertEqual(wrong_method.status_code, 405)
                self.assertEqual(wrong_method.json()["code"], 405)

                bad_login = client.post("/api/agent/auth/login", json={"account": "admin"})
                self.assertEqual(bad_login.status_code, 400)
                self.assertIn("missing field", bad_login.json()["message"])

                invalid_login = client.post("/api/agent/auth/login", json={"account": "admin", "password": "wrong"})
                self.assertEqual(invalid_login.status_code, 401)
                self.assertIn("invalid local account or password", invalid_login.json()["message"])

                login = client.post("/api/agent/auth/login", json={"account": "admin", "password": "admin"})
                self.assertEqual(login.status_code, 200)
                token = login.json()["data"]["token"]
                headers = {"Authorization": f"Bearer {token}"}

                status = client.get("/api/agent/status", headers=headers)
                self.assertEqual(status.status_code, 200)
                self.assertEqual(status.json()["data"]["database"], "ok")

                dependencies = client.get("/api/agent/status/dependencies", headers=headers)
                self.assertEqual(dependencies.status_code, 200)
                self.assertEqual(dependencies.json()["data"]["storage"], "ok")

                created = client.post("/api/agent/cases", json={"title": "FastAPI迁移案件"}, headers=headers)
                self.assertEqual(created.status_code, 200)
                case_id = created.json()["data"]["id"]

                content = base64.b64encode("乙方已经付款。".encode("utf-8")).decode("ascii")
                uploaded = client.post(
                    "/api/agent/files/upload",
                    json={"case_id": case_id, "file_name": "contract.txt", "content_base64": content},
                    headers=headers,
                )
                self.assertEqual(uploaded.status_code, 200)
                file_id = uploaded.json()["data"]["id"]

                invalid_upload = client.post(
                    "/api/agent/files/upload",
                    json={"case_id": case_id, "file_name": "malware.exe", "content_base64": content},
                    headers=headers,
                )
                self.assertEqual(invalid_upload.status_code, 400)
                self.assertIn("file extension is not allowed", invalid_upload.json()["message"])

                missing_task = client.get("/api/agent/tasks/task_missing", headers=headers)
                self.assertEqual(missing_task.status_code, 400)
                self.assertIn("task not found", missing_task.json()["message"])

                parsed = client.post("/api/agent/files/parse", json={"file_id": file_id}, headers=headers)
                self.assertEqual(parsed.status_code, 200)

                tasks = client.get(f"/api/agent/tasks?case_id={case_id}", headers=headers)
                self.assertEqual(tasks.status_code, 200)
                self.assertEqual(tasks.json()["data"][0]["status"], "success")

                cases = client.get("/api/agent/cases", headers=headers)
                self.assertEqual(cases.status_code, 200)
                self.assertEqual(cases.json()["data"][0]["id"], case_id)

                models = client.get("/api/agent/model-configs", headers=headers)
                self.assertEqual(models.status_code, 200)
                self.assertEqual(models.json()["data"], [])

                invalid_model = client.post(
                    "/api/agent/model-configs",
                    json={
                        "provider": "openai-compatible",
                        "base_url": "https://api.example.com/v1",
                        "chat_model": "chat",
                        "embedding_model": "embedding",
                        "api_key": "sk-test",
                    },
                    headers=headers,
                )
                self.assertEqual(invalid_model.status_code, 400)
                self.assertIn("model base_url must be localhost", invalid_model.json()["message"])

                missing_source = client.post("/api/agent/data-sources", json={"path": str(Path(tmp) / "missing")}, headers=headers)
                self.assertEqual(missing_source.status_code, 400)
                self.assertIn("data source path does not exist", missing_source.json()["message"])

                retrieve = client.post("/api/agent/rag/retrieve", json={"case_id": case_id, "question": "乙方是否付款？"}, headers=headers)
                self.assertEqual(retrieve.status_code, 200)
                self.assertGreaterEqual(len(retrieve.json()["data"]), 1)

                rag = client.post("/api/agent/rag/query", json={"case_id": case_id, "question": "乙方是否付款？"}, headers=headers)
                self.assertEqual(rag.status_code, 200)
                self.assertIn("answer", rag.json()["data"])
            finally:
                if store is not None:
                    store.close()
                agent_server.DATA_DIR = original_data_dir
                agent_server.STORAGE_DIR = original_storage_dir

    def test_uvicorn_entrypoint_smoke(self) -> None:
        agent_fastapi = load_module("agent_fastapi_m14_smoke", ROOT / "services" / "agent-api" / "app" / "main.py")
        if agent_fastapi.app is None:
            self.skipTest("FastAPI is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env.update(
                {
                    "AGENT_DATA_DIR": str(Path(tmp) / "data"),
                    "AGENT_STORAGE_DIR": str(Path(tmp) / "data" / "storage"),
                    "AGENT_DB": str(Path(tmp) / "data" / "agent.db"),
                }
            )
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--app-dir",
                    str(ROOT / "services" / "agent-api"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "0",
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=5)
            self.assertIn(proc.returncode, {0, -15})


if __name__ == "__main__":
    unittest.main()
