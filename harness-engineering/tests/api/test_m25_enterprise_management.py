#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import base64
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


agent_server = load_module("agent_server_m25_enterprise", ROOT / "services" / "agent-api" / "server.py")

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - optional target runtime dependency
    TestClient = None


class M25EnterpriseStoreTest(unittest.TestCase):
    def test_enterprise_org_integrations_and_assistant_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            admin_id = "u_admin"
            profile = store.save_enterprise_profile({"name": "海鸥律师事务所", "source_type": "mixed"}, admin_id)
            self.assertEqual(profile["name"], "海鸥律师事务所")

            department = store.create_organization_unit({"name": "争议解决部", "unit_type": "department"}, admin_id)
            lawyer = store.create_user({"account": "lawyer", "name": "律师", "role": "lead_lawyer", "password": "secret1"}, admin_id)
            member = store.assign_organization_member({"user_id": lawyer["id"], "unit_id": department["id"], "position": "主办律师"}, admin_id)
            self.assertEqual(member["unit_name"], "争议解决部")

            integration = store.save_external_org_integration({"provider": "wecom", "corp_id": "corp", "secret": "sec", "sync_enabled": True}, admin_id)
            self.assertTrue(integration["secret_configured"])
            sync = store.simulate_external_org_sync("wecom", admin_id)
            self.assertEqual(sync["sync_status"], "synced")

            setting = store.save_ai_assistant_setting({"name": "律所助手", "system_prompt": "基于知识库回答", "enabled": True}, admin_id)
            self.assertEqual(setting["name"], "律所助手")
            feedback = store.create_ai_assistant_feedback({"rating": "down", "comment": "引用不足", "issue_label": "citation"}, lawyer["id"])
            self.assertEqual(feedback["rating"], "down")
            self.assertEqual(feedback["status"], "open")
            handled_feedback = store.handle_ai_assistant_feedback(feedback["id"], {"status": "resolved", "resolution_comment": "已补充引用策略"}, admin_id)
            self.assertEqual(handled_feedback["status"], "resolved")
            self.assertEqual(handled_feedback["handler_id"], admin_id)
            self.assertEqual(handled_feedback["resolution_comment"], "已补充引用策略")

            baseline_search_only_count = store.enterprise_overview()["knowledge_search_only_count"]
            kb = store.create_knowledge_base({"type": "team", "name": "管理看板库", "knowledge_type": "template", "review_status": "pending_review", "ai_usage_policy": "search_only"}, admin_id)
            expired_kb = store.update_knowledge_base(kb["id"], {"expires_at": agent_server.now() - 10}, admin_id)
            self.assertLess(expired_kb["expires_at"], agent_server.now())
            content = base64.b64encode("看板测试文件包含付款期限和违约责任。".encode("utf-8")).decode("ascii")
            file = store.save_uploaded_file(None, "dashboard.txt", content, kb["id"], None, admin_id)
            store.update_file(file["id"], {"review_status": "needs_update", "ai_usage_policy": "disabled"}, admin_id)
            store.preview_file(file["id"], admin_id)
            self.assertEqual(store.search_file(file["id"], "付款期限", user_id=admin_id), [])
            sensitive_content = base64.b64encode("客户身份证号 11010519491231002X，手机号 13800138000。".encode("utf-8")).decode("ascii")
            sensitive_file = store.save_uploaded_file(None, "sensitive-dashboard.txt", sensitive_content, kb["id"], None, admin_id)
            store.parse_file(sensitive_file["id"])
            store.audit("CHAT_ASKED", "knowledge_base", kb["id"], admin_id)
            store.audit("CHAT_ASKED_NO_CITATION", "knowledge_base", kb["id"], admin_id)

            overview = store.enterprise_overview()
            self.assertEqual(overview["enterprise"]["name"], "海鸥律师事务所")
            self.assertEqual(overview["department_count"], 1)
            self.assertGreaterEqual(overview["member_count"], 2)
            self.assertEqual(overview["knowledge_review_status_counts"]["pending_review"], 1)
            self.assertEqual(overview["knowledge_type_counts"]["template"], 1)
            self.assertEqual(overview["knowledge_search_only_count"], baseline_search_only_count + 1)
            self.assertEqual(overview["knowledge_expired_count"], 1)
            self.assertEqual(overview["file_review_status_counts"]["needs_update"], 1)
            self.assertEqual(overview["file_ai_disabled_count"], 2)
            self.assertEqual(overview["high_sensitive_file_count"], 1)
            self.assertEqual(overview["high_risk_access_count"], 2)
            self.assertEqual(overview["high_risk_access_action_counts"]["preview"], 1)
            self.assertEqual(overview["high_risk_access_action_counts"]["ai_query"], 1)
            self.assertEqual(overview["ai_feedback_negative_count"], 1)
            self.assertEqual(overview["ai_feedback_open_count"], 0)
            self.assertEqual(overview["ai_feedback_resolved_count"], 1)
            self.assertEqual(overview["ai_feedback_issue_counts"]["citation_missing"], 1)
            self.assertEqual(overview["ai_question_count"], 2)
            self.assertEqual(overview["ai_insufficient_evidence_count"], 1)
            self.assertEqual(overview["ai_insufficient_evidence_rate"], 0.5)
            quality = next(item for item in overview["knowledge_quality_top"] if item["id"] == kb["id"])
            self.assertEqual(quality["file_count"], 2)
            self.assertEqual(quality["ai_question_count"], 2)
            self.assertEqual(quality["insufficient_evidence_count"], 1)
            self.assertEqual(quality["insufficient_evidence_rate"], 0.5)
            self.assertEqual(quality["ai_disabled_file_count"], 2)
            admin_contribution = next(item for item in overview["knowledge_contributor_top"] if item["maintainer_id"] == admin_id)
            self.assertGreaterEqual(admin_contribution["knowledge_base_count"], 1)
            self.assertGreaterEqual(admin_contribution["file_count"], 2)

    def test_enterprise_overview_reports_permission_anomalies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                admin_id = "u_admin"
                stale_user = store.create_user({"account": "stale", "name": "离职成员", "role": "assistant", "password": "secret1"}, admin_id)
                case = store.create_case({"title": "残留权限案件", "owner_id": admin_id})
                store.grant_case_member({"case_id": case["id"], "user_id": stale_user["id"], "role_code": "readonly"}, admin_id)
                kb = store.create_knowledge_base({"type": "team", "name": "残留共享库"}, admin_id)
                store.grant_knowledge_base_member(kb["id"], {"principal_id": stale_user["id"], "role_code": "viewer"}, admin_id)
                content = base64.b64encode("权限异常检测文件。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "anomaly.txt", content, kb["id"], None, admin_id)
                store.set_acl_entry({"resource_type": "file", "resource_id": file["id"], "principal_id": stale_user["id"], "action": "preview"}, admin_id)
                unit = store.create_organization_unit({"name": "异常项目组", "unit_type": "team"}, admin_id)
                store.assign_organization_member({"user_id": stale_user["id"], "unit_id": unit["id"], "position": "外部顾问"}, admin_id)
                store.conn.execute("UPDATE local_users SET status = 'disabled' WHERE id = ?", (stale_user["id"],))

                expired_kb = store.create_knowledge_base({"type": "private", "name": "过期仍生成库", "expires_at": agent_server.now() - 10}, admin_id)
                expired_file = store.save_uploaded_file(None, "expired-ai.txt", content, expired_kb["id"], None, admin_id)
                sensitive_file = store.save_uploaded_file(None, "legacy-sensitive.txt", content, kb["id"], None, admin_id)
                store.conn.execute(
                    "UPDATE local_files SET is_high_sensitive = 1, ai_enabled = 1, ai_usage_policy = 'allow_generation' WHERE id = ?",
                    (sensitive_file["id"],),
                )
                store.conn.commit()

                anomalies = store.detect_permission_anomalies()
                counts: dict[str, int] = {}
                for item in anomalies:
                    counts[item["type"]] = counts.get(item["type"], 0) + 1

                self.assertEqual(counts["disabled_user_case_member"], 1)
                self.assertEqual(counts["disabled_user_knowledge_base_member"], 2)
                self.assertEqual(counts["disabled_user_acl_entry"], 1)
                self.assertEqual(counts["disabled_user_organization_member"], 1)
                self.assertEqual(counts["expired_knowledge_base_ai_generation_enabled"], 1)
                self.assertEqual(counts["expired_file_ai_generation_enabled"], 1)
                self.assertEqual(counts["high_sensitive_file_ai_not_disabled"], 1)

                overview = store.enterprise_overview()
                self.assertEqual(overview["permission_anomaly_count"], len(anomalies))
                self.assertEqual(overview["permission_anomaly_type_counts"], counts)
                self.assertLessEqual(len(overview["permission_anomaly_samples"]), 10)
                self.assertEqual(expired_file["expires_at"], expired_kb["expires_at"])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_knowledge_base_chat_feedback_binds_real_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                admin_id = "u_admin"
                kb = store.create_knowledge_base({"type": "private", "name": "问答反馈库"}, admin_id)
                content = base64.b64encode("问答反馈测试材料包含付款期限和违约责任。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "feedback.txt", content, kb["id"], None, admin_id)
                store.parse_file(file["id"])

                answer = store.ask_knowledge_base(kb["id"], "付款期限和违约责任是什么？", admin_id)
                self.assertFalse(answer["insufficient_evidence"])
                self.assertTrue(answer["session_id"].startswith("chat_"))
                self.assertTrue(answer["message_id"].startswith("msg_"))

                feedback = store.create_ai_assistant_feedback(
                    {"rating": "down", "session_id": answer["session_id"], "message_id": answer["message_id"], "issue_label": "citation", "comment": "引用不足"},
                    admin_id,
                )
                self.assertEqual(feedback["session_id"], answer["session_id"])
                self.assertEqual(feedback["message_id"], answer["message_id"])
                overview = store.enterprise_overview()
                self.assertEqual(overview["ai_feedback_negative_count"], 1)
                self.assertEqual(overview["ai_feedback_open_count"], 1)
                self.assertEqual(overview["ai_feedback_issue_counts"]["citation_missing"], 1)

                with self.assertRaises(KeyError):
                    store.create_ai_assistant_feedback({"rating": "down", "session_id": answer["session_id"], "message_id": "msg_missing"}, admin_id)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir


@unittest.skipIf(TestClient is None, "FastAPI is not installed")
class M25EnterpriseFastApiTest(unittest.TestCase):
    def test_fastapi_enterprise_admin_routes(self) -> None:
        agent_fastapi = load_module("agent_fastapi_m25_enterprise", ROOT / "services" / "agent-api" / "app" / "main.py")
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_fastapi.agent_server.Store(Path(tmp) / "agent.db")
            try:
                app = agent_fastapi.create_app(store)
                client = TestClient(app, raise_server_exceptions=False)
                token = client.post("/api/agent/auth/login", json={"account": "admin", "password": "admin"}).json()["data"]["token"]
                headers = {"Authorization": f"Bearer {token}"}

                profile = client.post("/api/agent/enterprise/profile", json={"name": "海鸥律师事务所", "source_type": "manual"}, headers=headers)
                self.assertEqual(profile.status_code, 200)

                unit = client.post("/api/agent/organization/units", json={"name": "合同业务部", "unit_type": "department"}, headers=headers)
                self.assertEqual(unit.status_code, 200)

                integration = client.post("/api/agent/external-org/integrations", json={"provider": "feishu", "app_id": "app", "secret": "secret", "sync_enabled": True}, headers=headers)
                self.assertEqual(integration.status_code, 200)
                self.assertTrue(integration.json()["data"]["secret_configured"])

                sync = client.post("/api/agent/external-org/integrations/feishu/sync", headers=headers)
                self.assertEqual(sync.status_code, 200)
                self.assertEqual(sync.json()["data"]["sync_status"], "synced")

                assistant = client.post("/api/agent/ai-assistant/settings", json={"name": "企业助手", "enabled": True}, headers=headers)
                self.assertEqual(assistant.status_code, 200)
                self.assertEqual(assistant.json()["data"]["name"], "企业助手")

                feedback = client.post("/api/agent/ai-assistant/feedback", json={"rating": "down", "issue_label": "citation", "comment": "引用不足"}, headers=headers)
                self.assertEqual(feedback.status_code, 200)
                self.assertEqual(feedback.json()["data"]["status"], "open")

                handled = client.post(f"/api/agent/ai-assistant/feedback/{feedback.json()['data']['id']}/handle", json={"status": "ignored", "resolution_comment": "重复反馈"}, headers=headers)
                self.assertEqual(handled.status_code, 200)
                self.assertEqual(handled.json()["data"]["status"], "ignored")
                self.assertEqual(handled.json()["data"]["resolution_comment"], "重复反馈")

                overview = client.get("/api/agent/enterprise/overview", headers=headers)
                self.assertEqual(overview.status_code, 200)
                self.assertEqual(overview.json()["data"]["department_count"], 1)
                self.assertIn("knowledge_review_status_counts", overview.json()["data"])
                self.assertIn("ai_insufficient_evidence_rate", overview.json()["data"])
                self.assertIn("knowledge_quality_top", overview.json()["data"])
                self.assertIn("knowledge_contributor_top", overview.json()["data"])
                self.assertEqual(overview.json()["data"]["ai_feedback_ignored_count"], 1)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
