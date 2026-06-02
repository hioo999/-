#!/usr/bin/env python3
from __future__ import annotations

import base64
import io
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def office_zip_base64(entries: dict[str, str]) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


agent_server = load_module("agent_server_m24_knowledge_base", ROOT / "services" / "agent-api" / "server.py")

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - optional target runtime dependency
    TestClient = None


class M24KnowledgeBaseStoreTest(unittest.TestCase):
    def test_case_members_sync_to_case_knowledge_base_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            owner = store.create_user({"account": "owner", "name": "Owner", "role": "lead_lawyer", "password": "secret1"})
            viewer = store.create_user({"account": "viewer", "name": "Viewer", "role": "readonly", "password": "secret2"})
            case = store.create_case({"title": "同步案件", "owner_id": owner["id"]})

            kb_id = store.get_case_knowledge_base_id(case["id"])
            self.assertEqual(store.knowledge_base_role(kb_id, owner["id"]), "admin")
            effective = store.effective_permissions("knowledge_base", kb_id, owner["id"], owner["id"])
            self.assertTrue(effective["boundary"]["allowed_by_boundary"])
            self.assertEqual(effective["boundary"]["matter_id"], case["id"])
            self.assertIn("matter_boundary_case_scope", effective["boundary"]["reasons"])

            granted = store.grant_case_member({"case_id": case["id"], "user_id": viewer["id"], "role_code": "readonly"}, owner["id"])
            self.assertEqual(store.knowledge_base_role(kb_id, viewer["id"]), "viewer")

            store.revoke_case_member(granted["id"], owner["id"])
            self.assertIsNone(store.knowledge_base_role(kb_id, viewer["id"]))

    def test_folder_file_management_and_kb_member_revoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                admin_id = "u_admin"
                viewer = store.create_user({"account": "viewer", "name": "Viewer", "role": "readonly", "password": "secret2"})
                kb = store.create_knowledge_base({"type": "private", "name": "管理测试库"}, admin_id)
                member = store.grant_knowledge_base_member(kb["id"], {"principal_id": viewer["id"], "role_code": "viewer"}, admin_id)
                self.assertEqual(store.knowledge_base_role(kb["id"], viewer["id"]), "viewer")

                root = store.create_folder({"knowledge_base_id": kb["id"], "name": "根材料"}, admin_id)
                child = store.create_folder({"knowledge_base_id": kb["id"], "parent_id": root["id"], "name": "子材料"}, admin_id)
                renamed = store.update_folder(child["id"], {"name": "已整理", "parent_id": None, "sort_order": 3}, admin_id)
                self.assertEqual(renamed["name"], "已整理")
                self.assertIsNone(renamed["parent_id"])
                self.assertEqual(renamed["sort_order"], 3)

                content = base64.b64encode("文件移动与恢复测试。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "move.txt", content, kb["id"], root["id"], admin_id)
                moved = store.update_file(file["id"], {"folder_id": child["id"]}, admin_id)
                self.assertEqual(moved["folder_id"], child["id"])

                deleted_file = store.soft_delete_file(file["id"], admin_id)
                self.assertTrue(deleted_file["deleted"])
                self.assertNotIn(file["id"], [item["id"] for item in store.get_knowledge_base_tree(kb["id"], admin_id)["files"]])
                self.assertIn(file["id"], [item["id"] for item in store.get_knowledge_base_tree(kb["id"], admin_id, include_deleted=True)["files"]])
                restored_file = store.restore_file(file["id"], admin_id)
                self.assertIsNone(restored_file["deleted_at"])

                deleted_folder = store.soft_delete_folder(child["id"], admin_id)
                self.assertTrue(deleted_folder["deleted"])
                self.assertIn(child["id"], [item["id"] for item in store.get_knowledge_base_tree(kb["id"], admin_id, include_deleted=True)["folders"]])
                self.assertEqual(store.list_files(knowledge_base_id=kb["id"], folder_id=child["id"]), [])
                with self.assertRaises(ValueError):
                    store.restore_file(file["id"], admin_id)
                restored_folder = store.restore_folder(child["id"], admin_id)
                self.assertEqual(restored_folder["id"], child["id"])
                self.assertEqual(len(store.list_files(knowledge_base_id=kb["id"], folder_id=child["id"])), 1)

                revoked = store.revoke_knowledge_base_member(kb["id"], member["id"], admin_id)
                self.assertTrue(revoked["revoked"])
                self.assertIsNone(store.knowledge_base_role(kb["id"], viewer["id"]))
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_knowledge_base_rag_uses_kb_scope_and_indexes_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base({"type": "private", "name": "RAG 知识库"}, "u_admin")
                content = base64.b64encode("合同审查要点包括付款期限、违约责任和解除条件。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "contract-review.txt", content, kb["id"], None, "u_admin")
                store.parse_file(file["id"])

                hits = store.search(kb["id"], "付款期限 违约责任", user_id="u_admin")
                self.assertGreaterEqual(len(hits), 1)
                self.assertEqual(hits[0]["case_id"], kb["id"])
                self.assertEqual(hits[0]["file_id"], file["id"])

                answer = store.ask_knowledge_base(kb["id"], "付款期限和违约责任有哪些要点？", "u_admin")
                self.assertFalse(answer["insufficient_evidence"])
                self.assertTrue(answer["message_id"].startswith("msg_"))
                self.assertEqual(answer["citations"][0]["knowledge_base_id"], kb["id"])
                history_messages = store.get_chat_messages(answer["session_id"], "u_admin")
                history_answer = [item for item in history_messages if item["role"] == "assistant"][-1]
                self.assertGreaterEqual(len(history_answer["citations"]), 1)
                self.assertEqual(history_answer["citations"][0]["file_id"], file["id"])
                self.assertEqual(history_answer["citations"][0]["file_name"], "contract-review.txt")
                self.assertEqual(history_answer["citations"][0]["retrieval_mode"], "history")
                for section in ("结论：", "依据：", "引用来源：", "适用前提：", "风险提示：", "不确定事项：", "建议下一步："):
                    self.assertIn(section, answer["answer"])
                for marker in ("文件中明确记载", "根据文件内容推理", "根据通用法律知识补充", "证据不足，不能下结论"):
                    self.assertIn(marker, answer["answer"])
                feedback = store.create_ai_assistant_feedback(
                    {"rating": "down", "session_id": answer["session_id"], "message_id": answer["message_id"], "issue_label": "citation", "comment": "引用需要复核"},
                    "u_admin",
                )
                self.assertEqual(feedback["session_id"], answer["session_id"])
                self.assertEqual(feedback["message_id"], answer["message_id"])
                self.assertEqual(feedback["issue_label"], "citation_missing")
                with self.assertRaises(ValueError):
                    store.create_ai_assistant_feedback(
                        {"rating": "down", "session_id": answer["session_id"], "message_id": answer["message_id"], "issue_label": "free_text_reason"},
                        "u_admin",
                    )

                indexes = {row["name"] for row in store.conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()}
                self.assertIn("ux_kb_members_principal", indexes)
                self.assertIn("ux_acl_resource_principal_action", indexes)
                self.assertIn("idx_local_files_kb_folder_deleted", indexes)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_no_evidence_answer_history_preserves_missing_evidence_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            kb = store.create_knowledge_base({"type": "private", "name": "空知识库"}, "u_admin")

            answer = store.ask_knowledge_base(kb["id"], "库里是否有付款期限依据？", "u_admin")

            self.assertTrue(answer["insufficient_evidence"])
            self.assertEqual(answer["citations"], [])
            self.assertIn("证据不足，不能下确定性法律结论", answer["answer"])
            self.assertIn("无可用引用来源", answer["answer"])

            history_messages = store.get_chat_messages(answer["session_id"], "u_admin")
            history_answer = [item for item in history_messages if item["role"] == "assistant"][-1]
            self.assertTrue(history_answer["insufficient_evidence"])
            self.assertEqual(history_answer["citations"], [])
            self.assertEqual(history_answer["has_citations"], 0)
            self.assertIn("证据不足，不能下确定性法律结论", history_answer["content"])
            self.assertIn("无可用引用来源", history_answer["content"])
            self.assertIn("CHAT_ASKED_NO_CITATION", [row["action"] for row in store.audit_logs()])

    def test_knowledge_base_governance_metadata_controls_ai_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base(
                    {
                        "type": "team",
                        "name": "模板治理库",
                        "knowledge_type": "template",
                        "review_status": "published",
                        "confidentiality_level": "confidential",
                        "ai_usage_policy": "search_only",
                        "citation_priority": 5,
                    },
                    "u_admin",
                )
                self.assertEqual(kb["knowledge_type"], "template")
                self.assertEqual(kb["review_status"], "published")
                self.assertEqual(kb["confidentiality_level"], "confidential")
                self.assertEqual(kb["ai_usage_policy"], "search_only")
                self.assertEqual(kb["citation_priority"], 5)

                content = base64.b64encode("合同模板应重点审查付款、违约和解除条款。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "template.txt", content, kb["id"], None, "u_admin")
                store.parse_file(file["id"])
                self.assertGreaterEqual(len(store.search(kb["id"], "付款 条款", user_id="u_admin")), 1)
                with self.assertRaises(PermissionError):
                    store.ask_knowledge_base(kb["id"], "付款条款怎么写？", "u_admin")
                self.assertIn("AI_REJECTED_SEARCH_ONLY", [row["action"] for row in store.audit_logs()])

                updated = store.update_knowledge_base(kb["id"], {"ai_usage_policy": "allow_generation", "ai_enabled": True}, "u_admin")
                self.assertEqual(updated["ai_usage_policy"], "allow_generation")
                governance_audit = store.list_knowledge_base_governance_audit(kb["id"], "u_admin")
                governance_fields = [row["field_name"] for row in governance_audit]
                self.assertIn("ai_usage_policy", governance_fields)
                policy_change = next(row for row in governance_audit if row["field_name"] == "ai_usage_policy")
                self.assertEqual(policy_change["old_value"], "search_only")
                self.assertEqual(policy_change["new_value"], "allow_generation")
                store.update_file(file["id"], {"ai_usage_policy": "allow_generation", "ai_enabled": True}, "u_admin")
                answer = store.ask_knowledge_base(kb["id"], "付款条款怎么写？", "u_admin")
                self.assertFalse(answer["insufficient_evidence"])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_knowledge_base_review_transitions_are_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base({"type": "team", "name": "审核流程库"}, "u_admin")
                self.assertEqual(kb["review_status"], "draft")
                self.assertEqual(kb["ai_usage_policy"], "search_only")
                content = base64.b64encode("审核发布后才可生成的模板条款。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "review-flow.txt", content, kb["id"], None, "u_admin")
                store.parse_file(file["id"])
                self.assertEqual(file["review_status"], "draft")
                self.assertEqual(file["ai_usage_policy"], "search_only")
                self.assertGreaterEqual(len(store.search(kb["id"], "模板条款", user_id="u_admin")), 1)
                with self.assertRaises(PermissionError):
                    store.ask_knowledge_base(kb["id"], "模板条款是什么？", "u_admin")
                self.assertIn("AI_REJECTED_SEARCH_ONLY", [row["action"] for row in store.audit_logs()])

                pending = store.transition_knowledge_base_review(kb["id"], {"action": "submit_review"}, "u_admin")
                self.assertEqual(pending["review_status"], "pending_review")

                with self.assertRaises(ValueError):
                    store.transition_knowledge_base_review(kb["id"], {"action": "reject"}, "u_admin")
                rejected = store.transition_knowledge_base_review(kb["id"], {"action": "reject", "comment": "缺少维护人和引用优先级"}, "u_admin")
                self.assertEqual(rejected["review_status"], "rejected")

                pending_again = store.transition_knowledge_base_review(kb["id"], {"action": "submit_review"}, "u_admin")
                self.assertEqual(pending_again["review_status"], "pending_review")

                published = store.transition_knowledge_base_review(kb["id"], {"action": "publish"}, "u_admin")
                self.assertEqual(published["review_status"], "published")
                self.assertEqual(published["ai_usage_policy"], "allow_generation")
                published_file = store.get_file(file["id"])
                self.assertEqual(published_file["review_status"], "published")
                self.assertEqual(published_file["ai_usage_policy"], "allow_generation")
                answer = store.ask_knowledge_base(kb["id"], "模板条款是什么？", "u_admin")
                self.assertFalse(answer["insufficient_evidence"])

                disabled = store.transition_knowledge_base_review(kb["id"], {"action": "disable_ai"}, "u_admin")
                self.assertEqual(disabled["review_status"], "ai_disabled")
                self.assertFalse(disabled["ai_enabled"])
                self.assertEqual(disabled["ai_usage_policy"], "disabled")
                self.assertEqual(store.search(kb["id"], "模板条款", user_id="u_admin"), [])
                self.assertEqual(store.search(kb["id"], "模板条款", user_id="u_admin", generate=True), [])
                with self.assertRaises(PermissionError):
                    store.ask_knowledge_base(kb["id"], "模板条款是什么？", "u_admin")

                review_logs = store.list_knowledge_base_review_logs(kb["id"], "u_admin")
                self.assertEqual([item["action"] for item in review_logs], ["submit_review", "reject", "submit_review", "publish", "disable_ai"])
                self.assertEqual(review_logs[1]["from_status"], "pending_review")
                self.assertEqual(review_logs[1]["to_status"], "rejected")
                self.assertEqual(review_logs[1]["comment"], "缺少维护人和引用优先级")

                actions = [row["action"] for row in store.audit_logs()]
                self.assertIn("KNOWLEDGE_BASE_REVIEW_SUBMITTED", actions)
                self.assertIn("KNOWLEDGE_BASE_REVIEW_REJECTED", actions)
                self.assertIn("KNOWLEDGE_BASE_REVIEW_PUBLISHED", actions)
                self.assertIn("KNOWLEDGE_BASE_REVIEW_AI_DISABLED", actions)
                governance_audit = store.list_knowledge_base_governance_audit(kb["id"], "u_admin")
                self.assertIn("review_status", [row["field_name"] for row in governance_audit])
                self.assertIn("ai_usage_policy", [row["field_name"] for row in governance_audit])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_knowledge_base_review_requires_qualified_separate_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            admin_id = "u_admin"
            submitter = store.create_user({"account": "submitter", "name": "提交人", "role": "assistant", "password": "secret1"}, admin_id)
            reviewer = store.create_user({"account": "reviewer", "name": "合伙人", "role": "lead_lawyer", "password": "secret2"}, admin_id)
            kb = store.create_knowledge_base({"type": "team", "name": "高影响模板库", "knowledge_type": "template"}, admin_id)
            store.grant_knowledge_base_member(kb["id"], {"principal_id": submitter["id"], "role_code": "admin"}, admin_id)
            store.grant_knowledge_base_member(kb["id"], {"principal_id": reviewer["id"], "role_code": "admin"}, admin_id)

            submitted = store.transition_knowledge_base_review(kb["id"], {"action": "submit_review"}, submitter["id"])
            self.assertEqual(submitted["review_status"], "pending_review")
            with self.assertRaises(PermissionError):
                store.transition_knowledge_base_review(kb["id"], {"action": "publish"}, submitter["id"])
            with self.assertRaises(ValueError):
                store.transition_knowledge_base_review(kb["id"], {"action": "publish"}, reviewer["id"])

            store.update_knowledge_base(
                kb["id"],
                {"maintainer_id": reviewer["id"], "citation_priority": 5, "expires_at": agent_server.now() + 30 * 86400},
                admin_id,
            )
            published = store.transition_knowledge_base_review(kb["id"], {"action": "publish"}, reviewer["id"])
            self.assertEqual(published["review_status"], "published")
            review_logs = store.list_knowledge_base_review_logs(kb["id"], admin_id)
            self.assertEqual(review_logs[-1]["operator_id"], reviewer["id"])

    def test_bound_department_manager_can_review_department_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            admin_id = "u_admin"
            department = store.create_organization_unit({"name": "资本市场部", "unit_type": "department"}, admin_id)
            submitter = store.create_user({"account": "dept_submitter", "name": "部门提交人", "role": "assistant", "password": "secret1"}, admin_id)
            manager = store.create_user({"account": "dept_manager", "name": "部门管理员", "role": "assistant", "password": "secret2"}, admin_id)
            store.assign_organization_member({"user_id": manager["id"], "unit_id": department["id"], "position": "部门管理员"}, admin_id)
            kb = store.create_knowledge_base({"type": "team", "name": "部门实践库", "department_id": department["id"]}, admin_id)
            store.grant_knowledge_base_member(kb["id"], {"principal_id": submitter["id"], "role_code": "admin"}, admin_id)
            store.grant_knowledge_base_member(kb["id"], {"principal_id": manager["id"], "role_code": "admin"}, admin_id)

            store.transition_knowledge_base_review(kb["id"], {"action": "submit_review"}, submitter["id"])
            published = store.transition_knowledge_base_review(kb["id"], {"action": "publish"}, manager["id"])
            self.assertEqual(published["review_status"], "published")

    def test_expired_knowledge_base_can_retrieve_but_cannot_generate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base({"type": "private", "name": "过期知识库", "expires_at": agent_server.now() - 10}, "u_admin")
                content = base64.b64encode("过期知识库仍可检索付款期限，但不能生成正式 AI 回答。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "expired-kb.txt", content, kb["id"], None, "u_admin")
                store.parse_file(file["id"])

                hits = store.search(kb["id"], "付款期限", user_id="u_admin")
                self.assertGreaterEqual(len(hits), 1)
                self.assertIn("expired", hits[0]["governance_flags"])
                self.assertTrue(hits[0]["file_is_expired"])
                self.assertTrue(hits[0]["file_requires_maintenance"])
                self.assertEqual(store.search(kb["id"], "付款期限", user_id="u_admin", generate=True), [])
                with self.assertRaises(PermissionError):
                    store.ask_knowledge_base(kb["id"], "付款期限是什么？", "u_admin")
                self.assertIn("AI_REJECTED_EXPIRED", [row["action"] for row in store.audit_logs()])

                restored = store.update_knowledge_base(kb["id"], {"expires_at": agent_server.now() + 3600}, "u_admin")
                self.assertGreater(restored["expires_at"], agent_server.now())
                store.update_file(file["id"], {"expires_at": agent_server.now() + 3600}, "u_admin")
                answer = store.ask_knowledge_base(kb["id"], "付款期限是什么？", "u_admin")
                self.assertFalse(answer["insufficient_evidence"])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_file_governance_controls_rag_retrieval_and_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base({"type": "private", "name": "文件治理库"}, "u_admin")
                content = base64.b64encode("股权转让协议应重点审查付款安排和违约责任。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "equity-transfer.txt", content, kb["id"], None, "u_admin")
                store.parse_file(file["id"])

                self.assertEqual(file["review_status"], "published")
                self.assertEqual(file["ai_usage_policy"], "allow_generation")
                self.assertGreaterEqual(len(store.search(kb["id"], "付款安排 违约责任", user_id="u_admin", generate=True)), 1)

                needs_update = store.update_file(file["id"], {"review_status": "needs_update"}, "u_admin")
                self.assertEqual(needs_update["review_status"], "needs_update")
                needs_update_hits = store.search(kb["id"], "付款安排 违约责任", user_id="u_admin")
                self.assertIn("needs_update", needs_update_hits[0]["governance_flags"])
                self.assertTrue(needs_update_hits[0]["file_requires_maintenance"])
                self.assertEqual(needs_update_hits[0]["knowledge_trust_level"], "general")
                self.assertGreaterEqual(len(store.search(kb["id"], "付款安排 违约责任", user_id="u_admin", generate=True)), 1)

                search_only = store.update_file(file["id"], {"ai_usage_policy": "search_only"}, "u_admin")
                self.assertEqual(search_only["ai_usage_policy"], "search_only")
                self.assertGreaterEqual(len(store.search(kb["id"], "付款安排 违约责任", user_id="u_admin")), 1)
                self.assertEqual(store.search(kb["id"], "付款安排 违约责任", user_id="u_admin", generate=True), [])
                answer = store.ask_knowledge_base(kb["id"], "付款安排和违约责任是什么？", "u_admin")
                self.assertTrue(answer["insufficient_evidence"])
                self.assertIn("证据不足，不能下确定性法律结论", answer["answer"])
                self.assertIn("证据不足，不能下结论：是", answer["answer"])
                self.assertIn("建议下一步：", answer["answer"])

                disabled = store.update_file(file["id"], {"ai_enabled": False}, "u_admin")
                self.assertFalse(disabled["ai_enabled"])
                self.assertEqual(store.search(kb["id"], "付款安排 违约责任", user_id="u_admin"), [])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_scenario_query_uses_structured_task_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base({"type": "private", "name": "场景入口库", "knowledge_type": "template", "citation_priority": 7}, "u_admin")
                content = base64.b64encode("股权转让协议约定付款期限、违约责任和陈述保证条款。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "scenario.txt", content, kb["id"], None, "u_admin")
                store.parse_file(file["id"])

                result = store.scenario_query({"scenario": "contract_review", "context_scope": "current_knowledge_base", "knowledge_base_id": kb["id"]}, "u_admin")
                self.assertEqual(result["scenario"], "contract_review")
                self.assertFalse(result["insufficient_evidence"])
                self.assertEqual(result["citations"][0]["knowledge_trust_level"], "reviewed_template")
                self.assertEqual(result["citations"][0]["citation_priority"], 7)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_file_preview_returns_traceable_watermark_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base({"type": "private", "name": "水印测试库"}, "u_admin")
                content = base64.b64encode("带水印的文件预览测试。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "watermark.txt", content, kb["id"], None, "u_admin")

                preview = store.preview_file(file["id"], "u_admin")
                watermark = preview["watermark"]

                self.assertEqual(preview["source"], "raw_file")
                self.assertIn("带水印的文件预览测试", preview["text"])
                self.assertEqual(watermark["user_id"], "u_admin")
                self.assertEqual(watermark["user_account"], "admin")
                self.assertEqual(watermark["file_id"], file["id"])
                self.assertEqual(watermark["file_name"], "watermark.txt")
                self.assertEqual(watermark["action"], "preview")
                self.assertIn(watermark["id"], watermark["watermark_text"])
                self.assertIn("admin", watermark["watermark_text"])

                row = store.conn.execute("SELECT * FROM access_watermarks WHERE id = ?", (watermark["id"],)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["file_id"], file["id"])
                actions = [item["action"] for item in store.audit_logs()]
                self.assertIn("FILE_PREVIEWED", actions)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_parse_file_marks_high_sensitive_content_ai_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base({"type": "private", "name": "高敏识别库"}, "u_admin")
                text = "客户张三，身份证号 11010519491231002X，手机号 13800138000，银行卡号 6228480402564890018。"
                content = base64.b64encode(text.encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "sensitive-client.txt", content, kb["id"], None, "u_admin")

                parsed = store.parse_file(file["id"])
                updated_file = store.get_file(file["id"])

                self.assertEqual(parsed["status"], agent_server.HIGH_SENSITIVE_PROCESS_STATUS)
                self.assertTrue(parsed["high_sensitive"])
                self.assertEqual(parsed["sensitive_signals"], {"mainland_id_card": 1, "mainland_mobile": 1, "bank_card": 1})
                self.assertEqual(parsed["chunks"], 0)
                self.assertEqual(store.chunk_count(file["id"]), 0)
                self.assertEqual(updated_file["process_status"], agent_server.HIGH_SENSITIVE_PROCESS_STATUS)
                self.assertEqual(updated_file["confidentiality_level"], "restricted")
                self.assertEqual(updated_file["ai_usage_policy"], "disabled")
                self.assertFalse(updated_file["ai_enabled"])
                self.assertTrue(updated_file["is_high_sensitive"])
                self.assertEqual(updated_file["sensitive_signal_types"], ["bank_card", "mainland_id_card", "mainland_mobile"])
                self.assertEqual(store.search(kb["id"], "客户 张三 身份证", user_id="u_admin"), [])
                self.assertEqual(store.search(kb["id"], "客户 张三 身份证", user_id="u_admin", generate=True), [])
                answer = store.ask_knowledge_base(kb["id"], "客户张三的信息是什么？", "u_admin")
                self.assertTrue(answer["insufficient_evidence"])
                native_status = store.native_preview_status(file["id"], "u_admin")
                self.assertEqual(native_status["status"], "blocked")
                self.assertIn("high-sensitive", native_status["error"])
                with self.assertRaises(agent_server.PreviewContentBlockedError):
                    store.file_content_for_preview(file["id"], "u_admin")

                actions = [row["action"] for row in store.audit_logs()]
                self.assertIn("FILE_HIGH_SENSITIVE_AI_DISABLED", actions)
                self.assertIn("FILE_CONTENT_PREVIEW_BLOCKED", actions)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_acl_deny_inheritance_boundaries_hide_descendant_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                admin_id = "u_admin"
                kb_denied_viewer = store.create_user({"account": "kb_denied", "name": "KB Denied", "role": "readonly", "password": "secret1"})
                folder_denied_viewer = store.create_user({"account": "folder_denied", "name": "Folder Denied", "role": "readonly", "password": "secret2"})
                folder_denied_editor = store.create_user({"account": "folder_denied_editor", "name": "Folder Denied Editor", "role": "assistant", "password": "secret3"})
                kb = store.create_knowledge_base({"type": "private", "name": "ACL 继承测试库"}, admin_id)
                folder = store.create_folder({"knowledge_base_id": kb["id"], "name": "受控目录"}, admin_id)
                content = base64.b64encode("ACL 继承边界测试。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "acl-boundary.txt", content, kb["id"], folder["id"], admin_id)

                for viewer in (kb_denied_viewer, folder_denied_viewer):
                    store.grant_knowledge_base_member(kb["id"], {"principal_id": viewer["id"], "role_code": "viewer"}, admin_id)
                    self.assertTrue(store.has_resource_access("file", file["id"], viewer["id"], "view"))

                store.set_acl_entry(
                    {"resource_type": "knowledge_base", "resource_id": kb["id"], "principal_id": kb_denied_viewer["id"], "action": "view"},
                    admin_id,
                    "deny",
                )
                self.assertFalse(store.has_resource_access("knowledge_base", kb["id"], kb_denied_viewer["id"], "view"))
                self.assertFalse(store.has_resource_access("file", file["id"], kb_denied_viewer["id"], "view"))
                with self.assertRaises(PermissionError):
                    store.require_file_access(file["id"], kb_denied_viewer["id"], "view")

                store.set_acl_entry(
                    {"resource_type": "folder", "resource_id": folder["id"], "principal_id": folder_denied_viewer["id"], "action": "view"},
                    admin_id,
                    "deny",
                )
                self.assertFalse(store.has_resource_access("folder", folder["id"], folder_denied_viewer["id"], "view"))
                self.assertFalse(store.has_resource_access("file", file["id"], folder_denied_viewer["id"], "view"))
                with self.assertRaises(PermissionError):
                    store.require_file_access(file["id"], folder_denied_viewer["id"], "view")

                store.grant_knowledge_base_member(kb["id"], {"principal_id": folder_denied_editor["id"], "role_code": "editor"}, admin_id)
                deleted_folder = store.create_folder({"knowledge_base_id": kb["id"], "name": "回收站受控目录"}, admin_id)
                trash_content = base64.b64encode("回收站 ACL 继承边界测试。".encode("utf-8")).decode("ascii")
                deleted_file = store.save_uploaded_file(None, "trash-acl.txt", trash_content, kb["id"], deleted_folder["id"], admin_id)
                store.set_acl_entry(
                    {"resource_type": "folder", "resource_id": deleted_folder["id"], "principal_id": folder_denied_editor["id"], "action": "view"},
                    admin_id,
                    "deny",
                )
                store.soft_delete_folder(deleted_folder["id"], admin_id)
                trash_tree = store.get_knowledge_base_tree(kb["id"], folder_denied_editor["id"], include_deleted=True)
                self.assertNotIn(deleted_folder["id"], [item["id"] for item in trash_tree["folders"]])
                self.assertNotIn(deleted_file["id"], [item["id"] for item in trash_tree["files"]])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_ai_query_permission_denial_blocks_retrieval_and_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                admin_id = "u_admin"
                viewer = store.create_user({"account": "ai_denied", "name": "AI Denied", "role": "readonly", "password": "secret1"})
                kb = store.create_knowledge_base({"type": "team", "name": "AI 权限隔离库", "review_status": "published", "ai_usage_policy": "allow_generation"}, admin_id)
                store.grant_knowledge_base_member(kb["id"], {"principal_id": viewer["id"], "role_code": "viewer"}, admin_id)
                content = base64.b64encode("AI 查询权限隔离测试材料，包含付款期限和违约责任。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "ai-query-acl.txt", content, kb["id"], None, admin_id)
                store.parse_file(file["id"])

                self.assertTrue(store.has_resource_access("knowledge_base", kb["id"], viewer["id"], "view"))
                self.assertTrue(store.has_resource_access("file", file["id"], viewer["id"], "view"))
                self.assertGreaterEqual(len(store.search(kb["id"], "付款期限 违约责任", user_id=viewer["id"])), 1)

                store.set_acl_entry({"resource_type": "knowledge_base", "resource_id": kb["id"], "principal_id": viewer["id"], "action": "ai_query"}, admin_id, "deny")

                self.assertTrue(store.has_resource_access("knowledge_base", kb["id"], viewer["id"], "view"))
                self.assertFalse(store.has_resource_access("knowledge_base", kb["id"], viewer["id"], "ai_query"))
                self.assertFalse(store.has_resource_access("file", file["id"], viewer["id"], "ai_query"))
                effective = store.effective_permissions("knowledge_base", kb["id"], admin_id, viewer["id"])
                self.assertTrue(effective["permissions"]["view"])
                self.assertFalse(effective["permissions"]["ai_query"])
                self.assertEqual(store.search(kb["id"], "付款期限 违约责任", user_id=viewer["id"]), [])
                with self.assertRaises(PermissionError):
                    store.ask_knowledge_base(kb["id"], "付款期限和违约责任是什么？", viewer["id"])
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_acl_temporary_permission_expires_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                admin_id = "u_admin"
                viewer = store.create_user({"account": "temp", "name": "临时协作人", "role": "readonly", "password": "secret1"})
                kb = store.create_knowledge_base({"type": "team", "name": "临时授权库"}, admin_id)
                content = base64.b64encode("临时授权测试文件。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "temporary-acl.txt", content, kb["id"], None, admin_id)

                active_until = agent_server.now() + 3600
                allowed = store.set_acl_entry(
                    {"resource_type": "file", "resource_id": file["id"], "principal_id": viewer["id"], "action": "preview", "expires_at": active_until},
                    admin_id,
                    "allow",
                )
                self.assertEqual(allowed["expires_at"], active_until)
                self.assertFalse(allowed["is_expired"])
                self.assertTrue(store.has_resource_access("file", file["id"], viewer["id"], "preview"))
                overview = store.enterprise_overview()
                self.assertEqual(overview["temporary_acl_active_count"], 1)
                self.assertEqual(overview["temporary_acl_expired_count"], 0)

                expired_at = agent_server.now() - 10
                expired = store.set_acl_entry(
                    {"resource_type": "file", "resource_id": file["id"], "principal_id": viewer["id"], "action": "preview", "expires_at": expired_at},
                    admin_id,
                    "allow",
                )
                self.assertTrue(expired["is_expired"])
                self.assertFalse(store.has_resource_access("file", file["id"], viewer["id"], "preview"))
                entries = store.list_resource_permissions("file", file["id"], admin_id)
                self.assertEqual(entries[0]["id"], allowed["id"])
                self.assertTrue(entries[0]["is_expired"])
                overview = store.enterprise_overview()
                self.assertEqual(overview["temporary_acl_active_count"], 0)
                self.assertEqual(overview["temporary_acl_expired_count"], 1)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir

    def test_ethical_wall_blocks_members_outside_bound_department(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            admin_id = "u_admin"
            restricted_dept = store.create_organization_unit({"name": "重大客户项目组", "unit_type": "department"}, admin_id)
            inside = store.create_user({"account": "inside", "name": "Inside", "role": "assistant", "password": "secret1"})
            outside = store.create_user({"account": "outside", "name": "Outside", "role": "assistant", "password": "secret2"})
            store.assign_organization_member({"user_id": admin_id, "unit_id": restricted_dept["id"], "position": "管理员"}, admin_id)
            store.assign_organization_member({"user_id": inside["id"], "unit_id": restricted_dept["id"], "position": "项目律师"}, admin_id)

            kb = store.create_knowledge_base(
                {
                    "type": "team",
                    "name": "客户墙知识库",
                    "department_id": restricted_dept["id"],
                    "ethical_wall_enabled": True,
                },
                admin_id,
            )
            self.assertTrue(kb["ethical_wall_enabled"])

            store.grant_knowledge_base_member(kb["id"], {"principal_id": inside["id"], "role_code": "viewer"}, admin_id)
            store.grant_knowledge_base_member(kb["id"], {"principal_id": outside["id"], "role_code": "viewer"}, admin_id)

            self.assertTrue(store.has_resource_access("knowledge_base", kb["id"], inside["id"], "view"))
            self.assertFalse(store.has_resource_access("knowledge_base", kb["id"], outside["id"], "view"))
            inside_effective = store.effective_permissions("knowledge_base", kb["id"], admin_id, inside["id"])
            self.assertTrue(inside_effective["boundary"]["allowed_by_boundary"])
            self.assertIn("department_member_matched", inside_effective["boundary"]["reasons"])
            outside_effective = store.effective_permissions("knowledge_base", kb["id"], admin_id, outside["id"])
            self.assertFalse(outside_effective["boundary"]["allowed_by_boundary"])
            self.assertFalse(outside_effective["permissions"]["view"])
            self.assertIn("department_member_missing", outside_effective["boundary"]["reasons"])
            self.assertIn("ethical_wall_blocked", outside_effective["boundary"]["reasons"])
            with self.assertRaises(PermissionError):
                store.get_knowledge_base(kb["id"], outside["id"])
            self.assertNotIn(kb["id"], [item["id"] for item in store.list_knowledge_bases(outside["id"])])

            relaxed = store.update_knowledge_base(kb["id"], {"ethical_wall_enabled": False}, admin_id)
            self.assertFalse(relaxed["ethical_wall_enabled"])
            self.assertTrue(store.has_resource_access("knowledge_base", kb["id"], outside["id"], "view"))

    def test_client_and_matter_boundaries_block_members_without_matching_org_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            admin_id = "u_admin"
            client_unit = store.create_organization_unit({"name": "敏感客户A", "unit_type": "client"}, admin_id)
            matter_unit = store.create_organization_unit({"name": "客户A并购项目", "unit_type": "matter", "parent_id": client_unit["id"]}, admin_id)
            project_team_unit = store.create_organization_unit({"name": "客户A并购项目组", "unit_type": "project_team", "parent_id": matter_unit["id"]}, admin_id)
            department_unit = store.create_organization_unit({"name": "普通部门", "unit_type": "department"}, admin_id)
            with self.assertRaises(ValueError):
                store.create_organization_unit({"name": "孤立案件", "unit_type": "matter"}, admin_id)
            with self.assertRaises(ValueError):
                store.create_organization_unit({"name": "错误项目组", "unit_type": "project_team", "parent_id": client_unit["id"]}, admin_id)
            inside = store.create_user({"account": "client_inside", "name": "Client Inside", "role": "assistant", "password": "secret1"})
            matter_missing = store.create_user({"account": "matter_missing", "name": "Matter Missing", "role": "assistant", "password": "secret2"})
            store.assign_organization_member({"user_id": admin_id, "unit_id": client_unit["id"], "position": "客户墙管理员"}, admin_id)
            store.assign_organization_member({"user_id": admin_id, "unit_id": matter_unit["id"], "position": "项目管理员"}, admin_id)
            store.assign_organization_member({"user_id": admin_id, "unit_id": project_team_unit["id"], "position": "项目组管理员"}, admin_id)
            store.assign_organization_member({"user_id": inside["id"], "unit_id": client_unit["id"], "position": "客户组律师"}, admin_id)
            store.assign_organization_member({"user_id": inside["id"], "unit_id": matter_unit["id"], "position": "项目律师"}, admin_id)
            store.assign_organization_member({"user_id": inside["id"], "unit_id": project_team_unit["id"], "position": "项目组律师"}, admin_id)
            store.assign_organization_member({"user_id": matter_missing["id"], "unit_id": client_unit["id"], "position": "客户组律师"}, admin_id)

            kb = store.create_knowledge_base(
                {"type": "team", "name": "客户案件隔离库", "client_id": client_unit["id"], "matter_id": matter_unit["id"], "project_team_id": project_team_unit["id"], "ethical_wall_enabled": True},
                admin_id,
            )
            with self.assertRaises(KeyError):
                store.create_knowledge_base({"type": "team", "name": "无效客户边界库", "client_id": "missing_client_unit"}, admin_id)
            with self.assertRaises(ValueError):
                store.update_knowledge_base(kb["id"], {"matter_id": client_unit["id"]}, admin_id)
            with self.assertRaises(ValueError):
                store.update_knowledge_base(kb["id"], {"project_team_id": matter_unit["id"]}, admin_id)
            with self.assertRaises(ValueError):
                store.update_knowledge_base(kb["id"], {"client_id": department_unit["id"]}, admin_id)
            store.grant_knowledge_base_member(kb["id"], {"principal_id": inside["id"], "role_code": "viewer"}, admin_id)
            store.grant_knowledge_base_member(kb["id"], {"principal_id": matter_missing["id"], "role_code": "viewer"}, admin_id)

            self.assertTrue(store.has_resource_access("knowledge_base", kb["id"], inside["id"], "view"))
            self.assertFalse(store.has_resource_access("knowledge_base", kb["id"], matter_missing["id"], "view"))
            allowed_boundary = store.effective_permissions("knowledge_base", kb["id"], admin_id, inside["id"])["boundary"]
            blocked_boundary = store.effective_permissions("knowledge_base", kb["id"], admin_id, matter_missing["id"])["boundary"]
            self.assertIn("client_member_matched", allowed_boundary["reasons"])
            self.assertIn("matter_member_matched", allowed_boundary["reasons"])
            self.assertIn("project_team_member_matched", allowed_boundary["reasons"])
            self.assertIn("matter_member_missing", blocked_boundary["reasons"])
            self.assertFalse(blocked_boundary["allowed_by_boundary"])

    def test_feedback_quality_issue_counts_enter_management_overview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                kb = store.create_knowledge_base({"type": "private", "name": "反馈统计库"}, "u_admin")
                content = base64.b64encode("法律意见应核验引用来源和证据充分性。".encode("utf-8")).decode("ascii")
                file = store.save_uploaded_file(None, "quality.txt", content, kb["id"], None, "u_admin")
                store.parse_file(file["id"])
                answer = store.ask_knowledge_base(kb["id"], "法律意见需要注意什么？", "u_admin")

                store.create_ai_assistant_feedback({"rating": "down", "session_id": answer["session_id"], "message_id": answer["message_id"], "issue_label": "citation_missing"}, "u_admin")
                store.create_ai_assistant_feedback({"rating": "down", "session_id": answer["session_id"], "message_id": answer["message_id"], "issue_label": "insufficient_evidence"}, "u_admin")
                store.create_ai_assistant_feedback({"rating": "down", "session_id": answer["session_id"], "message_id": answer["message_id"], "issue_label": "citation_inaccurate"}, "u_admin")
                store.create_ai_assistant_feedback({"rating": "down", "session_id": answer["session_id"], "message_id": answer["message_id"], "issue_label": "permission_issue"}, "u_admin")
                overview = store.enterprise_overview()

                self.assertEqual(overview["ai_feedback_citation_missing_count"], 1)
                self.assertEqual(overview["ai_feedback_insufficient_evidence_count"], 1)
                self.assertEqual(overview["ai_feedback_answer_inaccurate_count"], 1)
                self.assertEqual(overview["ai_feedback_permission_anomaly_count"], 1)
                self.assertEqual(overview["ai_feedback_issue_counts"]["citation_missing"], 1)
                self.assertEqual(overview["ai_feedback_issue_counts"]["insufficient_evidence"], 1)
                self.assertEqual(overview["ai_feedback_issue_counts"]["answer_inaccurate"], 1)
                self.assertEqual(overview["ai_feedback_issue_counts"]["permission_anomaly"], 1)
            finally:
                agent_server.STORAGE_DIR = original_storage_dir


@unittest.skipIf(TestClient is None, "FastAPI is not installed")
class M24KnowledgeBaseFastApiTest(unittest.TestCase):
    def test_fastapi_supports_kb_only_upload_scan_members_and_acl(self) -> None:
        agent_fastapi = load_module("agent_fastapi_m24_knowledge_base", ROOT / "services" / "agent-api" / "app" / "main.py")
        server = agent_fastapi.agent_server
        with tempfile.TemporaryDirectory() as tmp:
            original_data_dir = server.DATA_DIR
            original_storage_dir = server.STORAGE_DIR
            original_office_preview_dir = server.OFFICE_PREVIEW_DIR
            original_ensure_office_preview_pdf = server.ensure_office_preview_pdf
            store = None
            try:
                server.DATA_DIR = Path(tmp)
                server.STORAGE_DIR = Path(tmp) / "storage"
                server.OFFICE_PREVIEW_DIR = Path(tmp) / "office-previews"
                store = server.Store(Path(tmp) / "agent.db")
                app = agent_fastapi.create_app(store)
                client = TestClient(app, raise_server_exceptions=False)

                admin_token = client.post("/api/agent/auth/login", json={"account": "admin", "password": "admin"}).json()["data"]["token"]
                admin_headers = {"Authorization": f"Bearer {admin_token}"}

                viewer = client.post(
                    "/api/agent/users",
                    json={"account": "viewer", "name": "Viewer", "role": "readonly", "password": "secret2"},
                    headers=admin_headers,
                ).json()["data"]
                viewer_token = client.post("/api/agent/auth/login", json={"account": "viewer", "password": "secret2"}).json()["data"]["token"]
                viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

                created = client.post(
                    "/api/agent/knowledge-bases",
                    json={"type": "private", "name": "V4.2 私人知识库", "description": "KB-only"},
                    headers=admin_headers,
                )
                self.assertEqual(created.status_code, 200)
                kb_id = created.json()["data"]["id"]
                self.assertEqual(created.json()["data"]["current_user_role"], "admin")

                updated = client.patch(f"/api/agent/knowledge-bases/{kb_id}", json={"ai_enabled": False}, headers=admin_headers)
                self.assertEqual(updated.status_code, 200)
                self.assertFalse(updated.json()["data"]["ai_enabled"])

                governance = client.patch(
                    f"/api/agent/knowledge-bases/{kb_id}",
                    json={
                        "ai_enabled": True,
                        "knowledge_type": "regulation",
                        "review_status": "published",
                        "confidentiality_level": "internal",
                        "ai_usage_policy": "allow_generation",
                        "citation_priority": 2,
                    },
                    headers=admin_headers,
                )
                self.assertEqual(governance.status_code, 200)
                self.assertTrue(governance.json()["data"]["ai_enabled"])
                self.assertEqual(governance.json()["data"]["knowledge_type"], "regulation")
                self.assertEqual(governance.json()["data"]["review_status"], "published")
                self.assertEqual(governance.json()["data"]["citation_priority"], 2)

                review_transition = client.post(f"/api/agent/knowledge-bases/{kb_id}/review", json={"action": "mark_needs_update"}, headers=admin_headers)
                self.assertEqual(review_transition.status_code, 200)
                self.assertEqual(review_transition.json()["data"]["review_status"], "needs_update")

                republished = client.post(f"/api/agent/knowledge-bases/{kb_id}/review", json={"action": "publish"}, headers=admin_headers)
                self.assertEqual(republished.status_code, 200)
                self.assertEqual(republished.json()["data"]["review_status"], "published")

                folder = client.post("/api/agent/folders", json={"knowledge_base_id": kb_id, "name": "材料"}, headers=admin_headers)
                self.assertEqual(folder.status_code, 200)
                folder_id = folder.json()["data"]["id"]

                content = base64.b64encode("私人知识库上传文件。".encode("utf-8")).decode("ascii")
                uploaded = client.post(
                    "/api/agent/files/upload",
                    json={"knowledge_base_id": kb_id, "folder_id": folder_id, "file_name": "kb-upload.txt", "content_base64": content},
                    headers=admin_headers,
                )
                self.assertEqual(uploaded.status_code, 200)
                file_id = uploaded.json()["data"]["id"]
                self.assertIsNone(uploaded.json()["data"]["case_id"])
                self.assertEqual(uploaded.json()["data"]["knowledge_base_id"], kb_id)
                self.assertEqual(uploaded.json()["data"]["folder_id"], folder_id)
                raw_preview = client.get(f"/api/agent/files/{file_id}/preview", headers=admin_headers)
                self.assertEqual(raw_preview.status_code, 200)
                self.assertEqual(raw_preview.json()["data"]["source"], "raw_file")
                self.assertIn("私人知识库上传文件", raw_preview.json()["data"]["text"])
                self.assertEqual(raw_preview.json()["data"]["watermark"]["file_id"], file_id)
                self.assertEqual(raw_preview.json()["data"]["watermark"]["action"], "preview")
                self.assertEqual(client.post("/api/agent/files/parse", json={"file_id": file_id}, headers=admin_headers).status_code, 200)
                indexed_preview = client.get(f"/api/agent/files/{file_id}/preview", headers=admin_headers)
                self.assertEqual(indexed_preview.status_code, 200)
                self.assertEqual(indexed_preview.json()["data"]["source"], "chunks")
                self.assertGreaterEqual(indexed_preview.json()["data"]["chunk_count"], 1)
                self.assertEqual(indexed_preview.json()["data"]["watermark"]["file_id"], file_id)

                kb_retrieve = client.post("/api/agent/rag/retrieve", json={"knowledge_base_id": kb_id, "question": "私人知识库上传文件"}, headers=admin_headers)
                self.assertEqual(kb_retrieve.status_code, 200)
                self.assertGreaterEqual(len(kb_retrieve.json()["data"]), 1)

                kb_rag = client.post("/api/agent/rag/query", json={"knowledge_base_id": kb_id, "question": "私人知识库上传文件说了什么？"}, headers=admin_headers)
                self.assertEqual(kb_rag.status_code, 200)
                self.assertIn("answer", kb_rag.json()["data"])
                self.assertIn("message_id", kb_rag.json()["data"])
                self.assertEqual(kb_rag.json()["data"]["citations"][0]["knowledge_base_id"], kb_id)

                scan_dir = Path(tmp) / "scan"
                scan_dir.mkdir()
                (scan_dir / "scan.md").write_text("私人知识库扫描文件。", "utf-8")
                source = client.post("/api/agent/data-sources", json={"path": str(scan_dir)}, headers=admin_headers)
                self.assertEqual(source.status_code, 200)
                scanned = client.post(
                    f"/api/agent/data-sources/{source.json()['data']['id']}/scan",
                    json={"knowledge_base_id": kb_id, "folder_id": folder_id},
                    headers=admin_headers,
                )
                self.assertEqual(scanned.status_code, 200)
                self.assertEqual(scanned.json()["data"]["case_id"], None)
                self.assertEqual(scanned.json()["data"]["added_count"], 1)

                tree = client.get(f"/api/agent/knowledge-bases/{kb_id}/tree", headers=admin_headers)
                self.assertEqual(tree.status_code, 200)
                self.assertEqual([item["id"] for item in tree.json()["data"]["folders"]], [folder_id])
                self.assertEqual(len(tree.json()["data"]["files"]), 2)

                stats = client.get(f"/api/agent/knowledge-bases/{kb_id}/stats", headers=admin_headers)
                self.assertEqual(stats.status_code, 200)
                self.assertEqual(stats.json()["data"]["folder_count"], 1)
                self.assertEqual(stats.json()["data"]["file_count"], 2)

                pptx_content = office_zip_base64({"ppt/slides/slide1.xml": "<a:t>路演材料第一页</a:t><a:t>交易亮点</a:t>"})
                pptx_file = client.post(
                    "/api/agent/files/upload",
                    json={"knowledge_base_id": kb_id, "folder_id": folder_id, "file_name": "deck.pptx", "content_base64": pptx_content},
                    headers=admin_headers,
                )
                self.assertEqual(pptx_file.status_code, 200)
                pptx_preview = client.get(f"/api/agent/files/{pptx_file.json()['data']['id']}/preview", headers=admin_headers)
                self.assertEqual(pptx_preview.status_code, 200)
                self.assertIn("路演材料第一页", pptx_preview.json()["data"]["text"])
                original_converter = server.OFFICE_CONVERTER_COMMAND
                try:
                    server.OFFICE_CONVERTER_COMMAND = ""
                    pptx_native_status = client.get(f"/api/agent/files/{pptx_file.json()['data']['id']}/native-preview", headers=admin_headers)
                    self.assertEqual(pptx_native_status.status_code, 200)
                    self.assertEqual(pptx_native_status.json()["data"]["status"], "converting")
                    self.assertEqual(pptx_native_status.json()["data"]["content_type"], None)
                    pptx_content_response = client.get(f"/api/agent/files/{pptx_file.json()['data']['id']}/content", headers=admin_headers)
                    self.assertEqual(pptx_content_response.status_code, 409)
                    self.assertIn("office preview is not ready", pptx_content_response.json()["message"])

                    def fake_office_preview_pdf(_source: Path, output: Path) -> None:
                        output.parent.mkdir(parents=True, exist_ok=True)
                        output.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF")

                    server.ensure_office_preview_pdf = fake_office_preview_pdf
                    drained = client.post("/api/agent/tasks/run-pending", json={"limit": 20}, headers=admin_headers)
                    self.assertEqual(drained.status_code, 200)
                    self.assertIn("office_preview", [item.get("task_type") for item in drained.json()["data"]["tasks"]])
                    pptx_native_ready = client.get(f"/api/agent/files/{pptx_file.json()['data']['id']}/native-preview", headers=admin_headers)
                    self.assertEqual(pptx_native_ready.status_code, 200)
                    self.assertEqual(pptx_native_ready.json()["data"]["status"], "native_ready")
                    pptx_pdf_content = client.get(f"/api/agent/files/{pptx_file.json()['data']['id']}/content", headers=admin_headers)
                    self.assertEqual(pptx_pdf_content.status_code, 200)
                    self.assertEqual(pptx_pdf_content.headers["content-type"], "application/pdf")
                    self.assertEqual(pptx_pdf_content.headers["x-agent-watermark-action"], "content_preview")
                finally:
                    server.OFFICE_CONVERTER_COMMAND = original_converter
                    server.ensure_office_preview_pdf = original_ensure_office_preview_pdf

                xlsx_content = office_zip_base64({"xl/sharedStrings.xml": "<t>付款节点</t><t>违约责任</t>"})
                xlsx_file = client.post(
                    "/api/agent/files/upload",
                    json={"knowledge_base_id": kb_id, "folder_id": folder_id, "file_name": "terms.xlsx", "content_base64": xlsx_content},
                    headers=admin_headers,
                )
                self.assertEqual(xlsx_file.status_code, 200)
                xlsx_preview = client.get(f"/api/agent/files/{xlsx_file.json()['data']['id']}/preview", headers=admin_headers)
                self.assertEqual(xlsx_preview.status_code, 200)
                self.assertIn("付款节点", xlsx_preview.json()["data"]["text"])
                try:
                    def fail_office_preview_pdf(_source: Path, _output: Path) -> None:
                        raise RuntimeError("converter boom")

                    server.ensure_office_preview_pdf = fail_office_preview_pdf
                    xlsx_failed = client.post(f"/api/agent/files/{xlsx_file.json()['data']['id']}/native-preview/run", headers=admin_headers)
                    self.assertEqual(xlsx_failed.status_code, 200)
                    self.assertEqual(xlsx_failed.json()["data"]["status"], "conversion_failed")
                    self.assertIn("converter boom", xlsx_failed.json()["data"]["error"])

                    def retry_office_preview_pdf(_source: Path, output: Path) -> None:
                        output.parent.mkdir(parents=True, exist_ok=True)
                        output.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF")

                    server.ensure_office_preview_pdf = retry_office_preview_pdf
                    xlsx_retry = client.post(f"/api/agent/files/{xlsx_file.json()['data']['id']}/native-preview/run", headers=admin_headers)
                    self.assertEqual(xlsx_retry.status_code, 200)
                    self.assertEqual(xlsx_retry.json()["data"]["status"], "native_ready")
                    xlsx_pdf_content = client.get(f"/api/agent/files/{xlsx_file.json()['data']['id']}/content", headers=admin_headers)
                    self.assertEqual(xlsx_pdf_content.status_code, 200)
                    self.assertEqual(xlsx_pdf_content.headers["content-type"], "application/pdf")
                finally:
                    server.ensure_office_preview_pdf = original_ensure_office_preview_pdf

                png_content = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/VZkAAAAASUVORK5CYII=")
                png_file = client.post(
                    "/api/agent/files/upload",
                    json={"knowledge_base_id": kb_id, "folder_id": folder_id, "file_name": "image.png", "content_base64": base64.b64encode(png_content).decode("ascii")},
                    headers=admin_headers,
                )
                self.assertEqual(png_file.status_code, 200)
                png_content_response = client.get(f"/api/agent/files/{png_file.json()['data']['id']}/content", headers=admin_headers)
                self.assertEqual(png_content_response.status_code, 200)
                self.assertEqual(png_content_response.headers["content-type"], "image/png")
                self.assertEqual(png_content_response.headers["x-agent-watermark-file-id"], png_file.json()["data"]["id"])
                self.assertTrue(png_content_response.content.startswith(b"\x89PNG"))

                pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
                pdf_file = client.post(
                    "/api/agent/files/upload",
                    json={"knowledge_base_id": kb_id, "folder_id": folder_id, "file_name": "paper.pdf", "content_base64": base64.b64encode(pdf_bytes).decode("ascii")},
                    headers=admin_headers,
                )
                self.assertEqual(pdf_file.status_code, 200)
                pdf_content_response = client.get(f"/api/agent/files/{pdf_file.json()['data']['id']}/content", headers=admin_headers)
                self.assertEqual(pdf_content_response.status_code, 200)
                self.assertEqual(pdf_content_response.headers["content-type"], "application/pdf")
                self.assertEqual(pdf_content_response.headers["x-agent-watermark-action"], "content_preview")

                high_sensitive_text = "客户李四，身份证号 11010519491231002X，手机号 13800138000。"
                high_sensitive_file = client.post(
                    "/api/agent/files/upload",
                    json={"knowledge_base_id": kb_id, "folder_id": folder_id, "file_name": "sensitive.txt", "content_base64": base64.b64encode(high_sensitive_text.encode("utf-8")).decode("ascii")},
                    headers=admin_headers,
                )
                self.assertEqual(high_sensitive_file.status_code, 200)
                high_sensitive_id = high_sensitive_file.json()["data"]["id"]
                self.assertEqual(client.post("/api/agent/files/parse", json={"file_id": high_sensitive_id}, headers=admin_headers).status_code, 200)
                high_sensitive_native = client.get(f"/api/agent/files/{high_sensitive_id}/native-preview", headers=admin_headers)
                self.assertEqual(high_sensitive_native.status_code, 200)
                self.assertEqual(high_sensitive_native.json()["data"]["status"], "blocked")
                high_sensitive_content = client.get(f"/api/agent/files/{high_sensitive_id}/content", headers=admin_headers)
                self.assertEqual(high_sensitive_content.status_code, 403)
                self.assertIn("high-sensitive", high_sensitive_content.json()["message"])

                granted = client.post(
                    f"/api/agent/knowledge-bases/{kb_id}/members",
                    json={"principal_id": viewer["id"], "role_code": "viewer"},
                    headers=admin_headers,
                )
                self.assertEqual(granted.status_code, 200)

                viewer_upload = client.post(
                    "/api/agent/files/upload",
                    json={"knowledge_base_id": kb_id, "file_name": "denied.txt", "content_base64": content},
                    headers=viewer_headers,
                )
                self.assertEqual(viewer_upload.status_code, 401)
                self.assertIn("knowledge base access denied", viewer_upload.json()["message"])

                viewer_files = client.get(f"/api/agent/files?knowledge_base_id={kb_id}", headers=viewer_headers)
                self.assertEqual(viewer_files.status_code, 200)
                self.assertIn(file_id, [item["id"] for item in viewer_files.json()["data"]])

                denied = client.post(
                    "/api/agent/permissions/deny",
                    json={"resource_type": "file", "resource_id": file_id, "principal_id": viewer["id"], "action": "view"},
                    headers=admin_headers,
                )
                self.assertEqual(denied.status_code, 200)
                acl_id = denied.json()["data"]["id"]

                checked = client.post(
                    "/api/agent/permissions/check",
                    json={"resource_type": "file", "resource_id": file_id, "user_id": viewer["id"], "action": "view"},
                    headers=admin_headers,
                )
                self.assertEqual(checked.status_code, 200)
                self.assertFalse(checked.json()["data"]["allowed"])
                effective = client.get(f"/api/agent/permissions/effective?resource_type=file&resource_id={file_id}&user_id={viewer['id']}", headers=admin_headers)
                self.assertEqual(effective.status_code, 200)
                self.assertIn("boundary", effective.json()["data"])
                self.assertEqual(effective.json()["data"]["boundary"]["knowledge_base_id"], kb_id)
                self.assertTrue(effective.json()["data"]["boundary"]["allowed_by_boundary"])
                self.assertIn("ethical_wall_not_enabled", effective.json()["data"]["boundary"]["reasons"])

                team_kb = client.post("/api/agent/knowledge-bases", json={"type": "team", "name": "待审核共享库"}, headers=admin_headers)
                self.assertEqual(team_kb.status_code, 200)
                team_kb_id = team_kb.json()["data"]["id"]
                self.assertEqual(team_kb.json()["data"]["review_status"], "draft")
                self.assertEqual(team_kb.json()["data"]["ai_usage_policy"], "search_only")
                submitted = client.post(f"/api/agent/knowledge-bases/{team_kb_id}/review", json={"action": "submit_review"}, headers=admin_headers)
                self.assertEqual(submitted.status_code, 200)
                reject_without_reason = client.post(f"/api/agent/knowledge-bases/{team_kb_id}/review", json={"action": "reject"}, headers=admin_headers)
                self.assertEqual(reject_without_reason.status_code, 400)
                rejected = client.post(f"/api/agent/knowledge-bases/{team_kb_id}/review", json={"action": "reject", "comment": "材料缺少维护说明"}, headers=admin_headers)
                self.assertEqual(rejected.status_code, 200)
                review_logs = client.get(f"/api/agent/knowledge-bases/{team_kb_id}/review-logs", headers=admin_headers)
                self.assertEqual(review_logs.status_code, 200)
                self.assertEqual(review_logs.json()["data"][-1]["action"], "reject")
                self.assertEqual(review_logs.json()["data"][-1]["comment"], "材料缺少维护说明")

                review_submitter = client.post(
                    "/api/agent/users",
                    json={"account": "api_submitter", "name": "API 提交人", "role": "assistant", "password": "secret1"},
                    headers=admin_headers,
                ).json()["data"]
                api_reviewer = client.post(
                    "/api/agent/users",
                    json={"account": "api_reviewer", "name": "API 合伙人", "role": "lead_lawyer", "password": "secret2"},
                    headers=admin_headers,
                ).json()["data"]
                submitter_token = client.post("/api/agent/auth/login", json={"account": "api_submitter", "password": "secret1"}).json()["data"]["token"]
                reviewer_token = client.post("/api/agent/auth/login", json={"account": "api_reviewer", "password": "secret2"}).json()["data"]["token"]
                submitter_headers = {"Authorization": f"Bearer {submitter_token}"}
                reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}
                template_kb = client.post(
                    "/api/agent/knowledge-bases",
                    json={"type": "team", "name": "API 模板审核库", "knowledge_type": "template"},
                    headers=admin_headers,
                )
                self.assertEqual(template_kb.status_code, 200)
                template_kb_id = template_kb.json()["data"]["id"]
                self.assertEqual(client.post(f"/api/agent/knowledge-bases/{template_kb_id}/members", json={"principal_id": review_submitter["id"], "role_code": "admin"}, headers=admin_headers).status_code, 200)
                self.assertEqual(client.post(f"/api/agent/knowledge-bases/{template_kb_id}/members", json={"principal_id": api_reviewer["id"], "role_code": "admin"}, headers=admin_headers).status_code, 200)
                api_submitted = client.post(f"/api/agent/knowledge-bases/{template_kb_id}/review", json={"action": "submit_review"}, headers=submitter_headers)
                self.assertEqual(api_submitted.status_code, 200)
                self_review = client.post(f"/api/agent/knowledge-bases/{template_kb_id}/review", json={"action": "publish"}, headers=submitter_headers)
                self.assertEqual(self_review.status_code, 401)
                missing_metadata = client.post(f"/api/agent/knowledge-bases/{template_kb_id}/review", json={"action": "publish"}, headers=reviewer_headers)
                self.assertEqual(missing_metadata.status_code, 400)
                self.assertIn("high-impact knowledge requires", missing_metadata.json()["message"])
                ready_template = client.patch(
                    f"/api/agent/knowledge-bases/{template_kb_id}",
                    json={"maintainer_id": api_reviewer["id"], "citation_priority": 6, "expires_at": agent_server.now() + 86400},
                    headers=admin_headers,
                )
                self.assertEqual(ready_template.status_code, 200)
                governance_audit = client.get(f"/api/agent/knowledge-bases/{template_kb_id}/governance-audit", headers=admin_headers)
                self.assertEqual(governance_audit.status_code, 200)
                self.assertIn("citation_priority", [item["field_name"] for item in governance_audit.json()["data"]])
                api_published = client.post(f"/api/agent/knowledge-bases/{template_kb_id}/review", json={"action": "publish"}, headers=reviewer_headers)
                self.assertEqual(api_published.status_code, 200)
                self.assertEqual(api_published.json()["data"]["review_status"], "published")

                viewer_files_after_deny = client.get(f"/api/agent/files?knowledge_base_id={kb_id}", headers=viewer_headers)
                self.assertEqual(viewer_files_after_deny.status_code, 200)
                self.assertNotIn(file_id, [item["id"] for item in viewer_files_after_deny.json()["data"]])

                acl_entries = client.get(f"/api/agent/permissions/resource?resource_type=file&resource_id={file_id}", headers=admin_headers)
                self.assertEqual(acl_entries.status_code, 200)
                self.assertEqual(acl_entries.json()["data"][0]["id"], acl_id)

                deleted_acl = client.delete(f"/api/agent/permissions/{acl_id}", headers=admin_headers)
                self.assertEqual(deleted_acl.status_code, 200)
                self.assertTrue(deleted_acl.json()["data"]["deleted"])
            finally:
                if store is not None:
                    store.close()
                server.DATA_DIR = original_data_dir
                server.STORAGE_DIR = original_storage_dir
                server.OFFICE_PREVIEW_DIR = original_office_preview_dir


if __name__ == "__main__":
    unittest.main()
