"""Sprint 全案底座接口、安全与异常回归测试。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import json
from unittest.mock import patch

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"ip_system_sprint_test_{os.getpid()}.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
os.environ.setdefault("ADMIN_PASSWORD", "secret123")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from database import SessionLocal  # noqa: E402
from main import app  # noqa: E402
from models.persona import AdminOperationLog, GenerationHistory  # noqa: E402
from services.ai_service import AIResponse  # noqa: E402


class SprintFoundationApiTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.owner_headers = self._auth("owner@example.com")
        self.other_headers = self._auth("other@example.com")
        self.admin_headers = self._auth("admin@163.com")
        self.ip_payload = {
            "name": "QA测试IP",
            "type": "expert",
            "industry": "职业教育",
            "targetAudience": "大学生",
            "businessGoal": "consulting_leads",
            "mainPlatforms": ["wechat", "shipinhao"],
            "secondaryPlatforms": ["xiaohongshu", "moments"],
            "tone": "专业直接",
            "visualStyle": "干净可信",
            "conversionPath": "内容->私信->咨询",
            "forbiddenExpressions": "不夸大，不承诺结果",
        }

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def _auth(self, email: str) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/register",
            json={"name": "QA", "email": email, "password": "secret123"},
        )
        if response.status_code == 409:
            response = self.client.post(
                "/api/auth/login",
                json={"email": email, "password": "secret123"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def _create_ip(self) -> str:
        response = self.client.post("/api/ip-assets", json=self.ip_payload, headers=self.owner_headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]["ipId"]

    def _create_foundation_flow(self) -> tuple[str, str, str]:
        ip_id = self._create_ip()
        strategy = self.client.post("/api/strategies/generate", json={"ipId": ip_id}, headers=self.owner_headers)
        self.assertEqual(strategy.status_code, 200, strategy.text)
        strategy_id = strategy.json()["data"]["strategyId"]

        columns = self.client.post(
            "/api/columns/generate",
            json={"ipId": ip_id, "strategyId": strategy_id},
            headers=self.owner_headers,
        )
        self.assertEqual(columns.status_code, 200, columns.text)
        self.assertGreaterEqual(len(columns.json()["data"]["items"]), 6)

        topics = self.client.post(
            "/api/topics/generate",
            json={"ipId": ip_id, "count": 20},
            headers=self.owner_headers,
        )
        self.assertEqual(topics.status_code, 200, topics.text)
        self.assertEqual(len(topics.json()["data"]["items"]), 20)
        return ip_id, topics.json()["data"]["items"][0]["id"], topics.json()["data"]["taskId"]

    def assert_error_code(self, response, status_code: int, code: str) -> None:
        self.assertEqual(response.status_code, status_code, response.text)
        self.assertEqual(response.json()["detail"]["code"], code)

    def test_requires_authentication(self) -> None:
        response = self.client.get("/api/ip-assets")
        self.assertEqual(response.status_code, 401)

    def test_full_sprint_foundation_flow(self) -> None:
        ip_id, topic_id, task_id = self._create_foundation_flow()

        filtered = self.client.get(
            "/api/topics",
            params={"ipId": ip_id, "platform": "wechat", "status": "todo"},
            headers=self.owner_headers,
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        self.assertGreater(filtered.json()["data"]["total"], 0)

        draft = self.client.post(
            "/api/content-drafts/generate",
            json={"ipId": ip_id, "topicId": topic_id},
            headers=self.owner_headers,
        )
        self.assertEqual(draft.status_code, 200, draft.text)
        draft_id = draft.json()["data"]["draftId"]

        saved = self.client.put(
            f"/api/content-drafts/{draft_id}",
            json={
                "painPoint": "痛点",
                "coreViewpoint": "观点",
                "logic": "逻辑",
                "cases": "案例",
                "goldenSentences": ["金句"],
                "conversionAction": "转化",
                "forbiddenExpressions": "禁用",
                "status": "generated",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["data"]["version"], 2)

        material = self.client.post(
            "/api/materials/upload",
            data={"ipId": ip_id},
            files={"file": ("note.txt", b"hello", "text/plain")},
            headers=self.owner_headers,
        )
        self.assertEqual(material.status_code, 200, material.text)
        self.assertEqual(material.json()["data"]["status"], "uploaded")

        task = self.client.get(f"/api/generation-tasks/{task_id}", headers=self.owner_headers)
        self.assertEqual(task.status_code, 200, task.text)
        self.assertEqual(task.json()["data"]["status"], "succeeded")

    def test_validation_and_generation_order_errors(self) -> None:
        missing = self.client.post(
            "/api/ip-assets",
            json={**self.ip_payload, "name": ""},
            headers=self.owner_headers,
        )
        self.assert_error_code(missing, 400, "VALIDATION_ERROR")

        ip_id = self._create_ip()
        no_columns = self.client.post(
            "/api/topics/generate",
            json={"ipId": ip_id, "count": 20},
            headers=self.owner_headers,
        )
        self.assert_error_code(no_columns, 400, "VALIDATION_ERROR")

        invalid_ip = self.client.post(
            "/api/strategies/generate",
            json={"ipId": "ip_bad"},
            headers=self.owner_headers,
        )
        self.assert_error_code(invalid_ip, 400, "VALIDATION_ERROR")

    def test_user_isolation(self) -> None:
        ip_id, _topic_id, task_id = self._create_foundation_flow()

        cross_user_ip = self.client.get(f"/api/ip-assets/{ip_id}", headers=self.other_headers)
        self.assert_error_code(cross_user_ip, 404, "IP_ASSET_NOT_FOUND")

        cross_user_task = self.client.get(f"/api/generation-tasks/{task_id}", headers=self.other_headers)
        self.assert_error_code(cross_user_task, 404, "TASK_NOT_FOUND")

    def test_material_upload_restrictions(self) -> None:
        ip_id = self._create_ip()

        bad_type = self.client.post(
            "/api/materials/upload",
            data={"ipId": ip_id},
            files={"file": ("bad.exe", b"bad", "application/octet-stream")},
            headers=self.owner_headers,
        )
        self.assert_error_code(bad_type, 400, "MATERIAL_UPLOAD_FAILED")

        oversized = self.client.post(
            "/api/materials/upload",
            data={"ipId": ip_id},
            files={"file": ("big.txt", b"x" * (5 * 1024 * 1024 + 1), "text/plain")},
            headers=self.owner_headers,
        )
        self.assert_error_code(oversized, 400, "MATERIAL_UPLOAD_FAILED")

    def test_prompt_template_admin_crud(self) -> None:
        categories = self.client.get("/api/copilot/prompt-template-categories")
        self.assertEqual(categories.status_code, 200, categories.text)
        self.assertGreaterEqual(len(categories.json()["data"]), 6)

        category_key = f"qa_prompt_{os.getpid()}"
        created_category = self.client.post(
            "/api/copilot/prompt-template-categories",
            json={
                "key": category_key,
                "name": "QA提示词分类",
                "description": "用于接口回归测试",
                "sort_order": 999,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(created_category.status_code, 200, created_category.text)
        self.assertEqual(created_category.json()["data"]["key"], category_key)

        anonymous_write = self.client.post(
            "/api/copilot/prompt-template-categories",
            json={
                "key": f"qa_prompt_anonymous_{os.getpid()}",
                "name": "匿名分类",
                "description": "不应成功",
                "sort_order": 1000,
            },
        )
        self.assertEqual(anonymous_write.status_code, 401, anonymous_write.text)

        user_write = self.client.post(
            "/api/copilot/prompt-template-categories",
            json={
                "key": f"qa_prompt_user_{os.getpid()}",
                "name": "普通用户分类",
                "description": "不应成功",
                "sort_order": 1001,
            },
            headers=self.owner_headers,
        )
        self.assertEqual(user_write.status_code, 403, user_write.text)

        template_key = f"qa_template_{os.getpid()}"
        created_template = self.client.post(
            "/api/copilot/prompt-templates",
            json={
                "key": template_key,
                "category_key": category_key,
                "platform": "wechat",
                "scene": "二创",
                "step": "正文生成",
                "name": "QA口播模板",
                "description": "测试后台提示词模板",
                "scenario": "接口回归",
                "output_structure": "开头 -> 内容 -> CTA",
                "writing_rules": ["规则一", "规则二"],
                "prompt_body": "严格按 QA 模板生成。",
                "version": "1.0.0",
                "change_note": "创建 QA 模板",
                "is_default": True,
                "sort_order": 999,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(created_template.status_code, 200, created_template.text)
        template_id = created_template.json()["data"]["id"]
        self.assertGreater(created_template.json()["data"]["versionId"], 0)

        anonymous_detail = self.client.get(f"/api/copilot/prompt-templates/{template_id}")
        self.assertEqual(anonymous_detail.status_code, 401, anonymous_detail.text)

        detail = self.client.get(f"/api/copilot/prompt-templates/{template_id}")
        self.assertEqual(detail.status_code, 401, detail.text)

        detail = self.client.get(f"/api/copilot/prompt-templates/{template_id}", headers=self.admin_headers)
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["data"]["prompt_body"], "严格按 QA 模板生成。")
        self.assertEqual(detail.json()["data"]["writing_rules"], ["规则一", "规则二"])
        self.assertEqual(detail.json()["data"]["platform"], "wechat")
        self.assertEqual(detail.json()["data"]["step"], "正文生成")

        updated_template = self.client.put(
            f"/api/copilot/prompt-templates/{template_id}",
            json={
                "key": template_key,
                "category_key": category_key,
                "platform": "wechat",
                "scene": "二创",
                "step": "正文生成",
                "name": "QA口播模板更新版",
                "description": "测试后台提示词模板更新",
                "scenario": "接口回归",
                "output_structure": "钩子 -> 观点 -> CTA",
                "writing_rules": ["更新规则"],
                "prompt_body": "严格按更新后的 QA 模板生成。",
                "version": "1.0.1",
                "change_note": "更新 QA 模板",
                "is_default": True,
                "is_active": True,
                "sort_order": 998,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(updated_template.status_code, 200, updated_template.text)
        self.assertEqual(updated_template.json()["data"]["name"], "QA口播模板更新版")
        self.assertEqual(updated_template.json()["data"]["writing_rules"], ["更新规则"])
        self.assertGreater(updated_template.json()["data"]["versionId"], created_template.json()["data"]["versionId"])

        versions = self.client.get(f"/api/copilot/prompt-templates/{template_id}/versions", headers=self.admin_headers)
        self.assertEqual(versions.status_code, 200, versions.text)
        self.assertGreaterEqual(versions.json()["data"]["total"], 2)
        self.assertIn("正文生成", [item["step"] for item in versions.json()["data"]["items"]])

        deleted_template = self.client.delete(f"/api/copilot/prompt-templates/{template_id}", headers=self.admin_headers)
        self.assertEqual(deleted_template.status_code, 200, deleted_template.text)

        remaining_templates = self.client.get(
            "/api/copilot/prompt-templates",
            params={"category_key": category_key},
        )
        self.assertEqual(remaining_templates.status_code, 200, remaining_templates.text)
        self.assertEqual(remaining_templates.json()["data"], [])

        with SessionLocal() as db:
            actions = [
                row.action
                for row in db.query(AdminOperationLog)
                .filter(AdminOperationLog.resource_key.in_([category_key, template_key]))
                .order_by(AdminOperationLog.id)
                .all()
            ]
        self.assertIn("prompt_category.create", actions)
        self.assertIn("prompt_template.create", actions)
        self.assertIn("prompt_template.update", actions)
        self.assertIn("prompt_template.disable", actions)

    def test_full_case_generation_records_template_snapshots(self) -> None:
        suffix = os.getpid()

        def create_template(template_type: str, label: str) -> int:
            category_key = f"qa_{template_type}_{suffix}"
            category = self.client.post(
                "/api/copilot/prompt-template-categories",
                json={
                    "key": category_key,
                    "template_type": template_type,
                    "name": f"QA{label}分类",
                    "description": "用于生成历史快照测试",
                    "sort_order": 998,
                },
                headers=self.admin_headers,
            )
            self.assertEqual(category.status_code, 200, category.text)
            template = self.client.post(
                "/api/copilot/prompt-templates",
                json={
                    "key": f"qa_{template_type}_template_{suffix}",
                    "template_type": template_type,
                    "category_key": category_key,
                    "platform": "douyin",
                    "scene": "口播全案",
                    "step": label,
                    "name": f"QA{label}模板",
                    "description": "验证生成历史记录模板快照",
                    "scenario": "接口回归",
                    "output_structure": "按测试结构输出",
                    "writing_rules": ["必须注入后台模板正文"],
                    "prompt_body": f"{label}内部正文，不应暴露给普通前端。",
                    "version": "9.9.0",
                    "change_note": "创建快照测试模板",
                    "is_default": False,
                    "sort_order": 998,
                },
                headers=self.admin_headers,
            )
            self.assertEqual(template.status_code, 200, template.text)
            return template.json()["data"]["id"]

        text_template_id = create_template("text_script", "口播")
        cover_template_id = create_template("image_cover", "封面")
        video_template_id = create_template("video_clip", "视频")
        captured_messages: list[str] = []
        fake_responses = iter(["QA口播文案", "QA视频提示词", "QA封面提示词"])

        async def fake_chat(*args, **kwargs):
            messages = args[0] if args and isinstance(args[0], list) else kwargs.get("messages", [])
            captured_messages.append(json.dumps(messages, ensure_ascii=False))
            return AIResponse(content=next(fake_responses))

        with patch("api.copilot_routes.AIService.chat", side_effect=fake_chat):
            generated = self.client.post(
                "/api/copilot/generate",
                json={
                    "extracted_content": "测试生成历史模板快照",
                    "persona_id": 0,
                    "target_platform": "douyin",
                    "extra_requirements": "保持专业",
                    "prompt_template_id": text_template_id,
                    "cover_prompt_template_id": cover_template_id,
                    "video_prompt_template_id": video_template_id,
                    "cover_aspect_ratio": "4:5",
                    "cover_title": "测试封面",
                    "video_aspect_ratio": "9:16",
                    "video_duration": "15秒",
                    "video_workflow_type": "product_tvc",
                },
                headers=self.owner_headers,
            )
        self.assertEqual(generated.status_code, 200, generated.text)
        data = generated.json()["data"]
        self.assertEqual(data["prompt_template_version"], "9.9.0")
        self.assertNotIn("prompt_body", data["prompt_template"])
        self.assertNotIn("prompt_body", data["cover_prompt_template"])
        self.assertNotIn("prompt_body", data["video_prompt_template"])
        self.assertIn("口播内部正文", "\n".join(captured_messages))
        self.assertIn("封面内部正文", "\n".join(captured_messages))
        self.assertIn("视频内部正文", "\n".join(captured_messages))

        with SessionLocal() as db:
            history = db.query(GenerationHistory).filter(GenerationHistory.id == data["history_id"]).first()
            self.assertIsNotNone(history)
            params = json.loads(history.generation_params_json)

        self.assertEqual(params["cover_aspect_ratio"], "4:5")
        self.assertEqual(params["templates"]["text_script"]["version"], "9.9.0")
        self.assertEqual(params["templates"]["image_cover"]["id"], cover_template_id)
        self.assertEqual(params["templates"]["video_clip"]["id"], video_template_id)
        self.assertNotIn("prompt_body", params["templates"]["text_script"])
        self.assertNotIn("prompt_body", params["templates"]["image_cover"])
        self.assertNotIn("prompt_body", params["templates"]["video_clip"])


if __name__ == "__main__":
    unittest.main()
