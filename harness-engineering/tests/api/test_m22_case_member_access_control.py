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


agent_server = load_module("agent_server_m22_case_access", ROOT / "services" / "agent-api" / "server.py")

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - optional target runtime dependency
    TestClient = None


class M22CaseMemberStoreAccessTest(unittest.TestCase):
    def test_case_list_and_rag_are_filtered_by_case_membership(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            alice = store.create_user({"account": "alice", "name": "Alice", "role": "lead_lawyer", "password": "secret1"})
            bob = store.create_user({"account": "bob", "name": "Bob", "role": "assistant", "password": "secret2"})
            case = store.create_case({"title": "Alice 案件", "owner_id": alice["id"]})

            self.assertEqual([item["id"] for item in store.list_cases(alice["id"])], [case["id"]])
            self.assertEqual(store.list_cases(bob["id"]), [])
            with self.assertRaises(agent_server.CaseAccessError):
                store.ask(case["id"], "能否看到该案件？", bob["id"])

            granted = store.grant_case_member({"case_id": case["id"], "user_id": bob["id"], "role_code": "readonly"})
            self.assertEqual([item["id"] for item in store.list_cases(bob["id"])], [case["id"]])

            store.revoke_case_member(granted["id"])
            self.assertEqual(store.list_cases(bob["id"]), [])
            with self.assertRaises(agent_server.CaseAccessError):
                store.require_case_access(case["id"], bob["id"])

    def test_disable_user_revokes_resource_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                admin_id = "u_admin"
                bob = store.create_user({"account": "bob", "name": "Bob", "role": "assistant", "password": "secret2"})
                case = store.create_case({"title": "权限回收案件", "owner_id": admin_id})
                granted_case_member = store.grant_case_member({"case_id": case["id"], "user_id": bob["id"], "role_code": "readonly"}, admin_id)
                case_kb_id = store.get_case_knowledge_base_id(case["id"])

                kb = store.create_knowledge_base({"type": "team", "name": "权限回收共享库"}, admin_id)
                store.grant_knowledge_base_member(kb["id"], {"principal_id": bob["id"], "role_code": "viewer"}, admin_id)
                content = base64.b64encode("权限回收测试文件。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "revoke.txt", content, kb["id"], None, admin_id)
                acl = store.set_acl_entry({"resource_type": "file", "resource_id": file["id"], "principal_id": bob["id"], "action": "preview"}, admin_id)
                unit = store.create_organization_unit({"name": "临时项目组", "unit_type": "team"}, admin_id)
                store.assign_organization_member({"user_id": bob["id"], "unit_id": unit["id"], "position": "临时成员"}, admin_id)
                store.login("bob", "secret2")

                self.assertEqual([item["id"] for item in store.list_cases(bob["id"])], [case["id"]])
                self.assertEqual(store.knowledge_base_role(case_kb_id, bob["id"]), "viewer")
                self.assertEqual(store.knowledge_base_role(kb["id"], bob["id"]), "viewer")
                self.assertTrue(store.has_resource_access("file", file["id"], bob["id"], "preview"))

                disabled = store.disable_user(bob["id"], admin_id)
                summary = disabled["permission_revoke_summary"]

                self.assertEqual(disabled["status"], "disabled")
                self.assertEqual(summary["sessions_revoked"], 1)
                self.assertEqual(summary["case_memberships_revoked"], 1)
                self.assertEqual(summary["knowledge_base_memberships_revoked"], 2)
                self.assertEqual(summary["acl_entries_revoked"], 1)
                self.assertEqual(summary["organization_memberships_inactivated"], 1)
                self.assertEqual(store.list_cases(bob["id"]), [])
                self.assertIsNone(store.knowledge_base_role(case_kb_id, bob["id"]))
                self.assertIsNone(store.knowledge_base_role(kb["id"], bob["id"]))
                self.assertFalse(store.conn.execute("SELECT 1 FROM acl_entries WHERE id = ?", (acl["id"],)).fetchone())
                self.assertFalse(store.conn.execute("SELECT 1 FROM case_members WHERE id = ?", (granted_case_member["id"],)).fetchone())
                actions = [row["action"] for row in store.audit_logs()]
                self.assertIn("USER_PERMISSIONS_REVOKED", actions)
                self.assertIn("USER_DISABLED", actions)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir


@unittest.skipIf(TestClient is None, "FastAPI is not installed")
class M22CaseMemberFastApiAccessTest(unittest.TestCase):
    def test_fastapi_rejects_non_member_and_allows_granted_member(self) -> None:
        agent_fastapi = load_module("agent_fastapi_m22_case_access", ROOT / "services" / "agent-api" / "app" / "main.py")
        server = agent_fastapi.agent_server
        with tempfile.TemporaryDirectory() as tmp:
            original_data_dir = server.DATA_DIR
            original_storage_dir = server.STORAGE_DIR
            store = None
            try:
                server.DATA_DIR = Path(tmp)
                server.STORAGE_DIR = Path(tmp) / "storage"
                store = server.Store(Path(tmp) / "agent.db")
                app = agent_fastapi.create_app(store)
                client = TestClient(app, raise_server_exceptions=False)

                admin_token = client.post("/api/agent/auth/login", json={"account": "admin", "password": "admin"}).json()["data"]["token"]
                admin_headers = {"Authorization": f"Bearer {admin_token}"}

                alice = client.post(
                    "/api/agent/users",
                    json={"account": "alice", "name": "Alice", "role": "lead_lawyer", "password": "secret1"},
                    headers=admin_headers,
                ).json()["data"]
                bob = client.post(
                    "/api/agent/users",
                    json={"account": "bob", "name": "Bob", "role": "assistant", "password": "secret2"},
                    headers=admin_headers,
                ).json()["data"]

                alice_token = client.post("/api/agent/auth/login", json={"account": "alice", "password": "secret1"}).json()["data"]["token"]
                bob_token = client.post("/api/agent/auth/login", json={"account": "bob", "password": "secret2"}).json()["data"]["token"]
                alice_headers = {"Authorization": f"Bearer {alice_token}"}
                bob_headers = {"Authorization": f"Bearer {bob_token}"}

                created = client.post("/api/agent/cases", json={"title": "Alice 案件"}, headers=alice_headers)
                self.assertEqual(created.status_code, 200)
                case_id = created.json()["data"]["id"]
                self.assertEqual(created.json()["data"]["owner_id"], alice["id"])

                content = base64.b64encode("乙方逾期付款，应承担违约责任。".encode("utf-8")).decode("ascii")
                uploaded = client.post(
                    "/api/agent/files/upload",
                    json={"case_id": case_id, "file_name": "contract.txt", "content_base64": content},
                    headers=alice_headers,
                )
                self.assertEqual(uploaded.status_code, 200)
                file_id = uploaded.json()["data"]["id"]
                task_id = uploaded.json()["data"]["task_id"]
                self.assertEqual(client.post("/api/agent/files/parse", json={"file_id": file_id}, headers=alice_headers).status_code, 200)
                session_id = client.post("/api/agent/rag/query", json={"case_id": case_id, "question": "乙方是否逾期付款？"}, headers=alice_headers).json()["data"]["session_id"]

                self.assertEqual(client.get("/api/agent/cases", headers=bob_headers).json()["data"], [])
                for method, path, payload in (
                    ("get", f"/api/agent/cases/{case_id}", None),
                    ("get", f"/api/agent/files?case_id={case_id}", None),
                    ("get", f"/api/agent/tasks?case_id={case_id}", None),
                    ("get", f"/api/agent/tasks/{task_id}", None),
                    ("get", f"/api/agent/chats?case_id={case_id}", None),
                    ("get", f"/api/agent/chats/{session_id}", None),
                    ("post", "/api/agent/rag/retrieve", {"case_id": case_id, "question": "逾期付款"}),
                    ("post", "/api/agent/rag/query", {"case_id": case_id, "question": "逾期付款"}),
                ):
                    response = getattr(client, method)(path, json=payload, headers=bob_headers) if payload is not None else getattr(client, method)(path, headers=bob_headers)
                    self.assertEqual(response.status_code, 403, path)
                    self.assertEqual(response.json()["message"], "case access denied")

                granted = client.post(
                    "/api/agent/case-members",
                    json={"case_id": case_id, "user_id": bob["id"], "role_code": "readonly"},
                    headers=admin_headers,
                )
                self.assertEqual(granted.status_code, 200)
                member_id = granted.json()["data"]["id"]

                self.assertEqual(client.get("/api/agent/cases", headers=bob_headers).json()["data"][0]["id"], case_id)
                self.assertEqual(client.get(f"/api/agent/cases/{case_id}", headers=bob_headers).status_code, 200)
                self.assertEqual(client.get(f"/api/agent/files?case_id={case_id}", headers=bob_headers).json()["data"][0]["id"], file_id)
                self.assertEqual(client.get(f"/api/agent/tasks?case_id={case_id}", headers=bob_headers).json()["data"][0]["id"], task_id)
                self.assertEqual(client.get(f"/api/agent/chats/{session_id}", headers=bob_headers).status_code, 200)

                revoked = client.post(f"/api/agent/case-members/{member_id}/revoke", headers=admin_headers)
                self.assertEqual(revoked.status_code, 200)
                self.assertEqual(client.get("/api/agent/cases", headers=bob_headers).json()["data"], [])
                self.assertEqual(client.get(f"/api/agent/cases/{case_id}", headers=bob_headers).status_code, 403)
            finally:
                if store is not None:
                    store.close()
                server.DATA_DIR = original_data_dir
                server.STORAGE_DIR = original_storage_dir


if __name__ == "__main__":
    unittest.main()
