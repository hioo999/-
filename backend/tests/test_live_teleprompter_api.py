"""直播提词器 HTML 台本生成接口回归测试。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"ip_system_live_teleprompter_test_{os.getpid()}.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
os.environ.setdefault("ADMIN_PASSWORD", "secret123")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


class LiveTeleprompterApiTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def _auth(self, email: str = "live@example.com") -> dict[str, str]:
        response = self.client.post(
            "/api/auth/register",
            json={"name": "Live", "email": email, "password": "secret123"},
        )
        if response.status_code == 409:
            response = self.client.post("/api/auth/login", json={"email": email, "password": "secret123"})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def _payload(self) -> dict:
        return {
            "title": "抗炎季<script>alert(1)</script>",
            "platform": "视频号",
            "liveStart": "20:00",
            "liveDurationMinutes": 60,
            "gmvTarget": "8W",
            "audience": "换季敏感、泛红、爆痘用户",
            "style": "专业强转化",
            "hostCount": 2,
            "hosts": [
                {"name": "萱萱", "role": "主讲控场"},
                {"name": "YK", "role": "副播互动"},
            ],
            "benefits": "看满 15 分钟送体验权益",
            "extraRequirements": "避免绝对化效果承诺",
            "complianceMode": True,
            "templateKey": "medical_beauty",
            "themeKey": "medical_green",
            "aiEnhance": False,
            "saveHistory": False,
            "products": [
                {
                    "name": "春日抗炎修复卡",
                    "category": "医美卡项",
                    "positioning": "main",
                    "originalPrice": "1378",
                    "livePrice": "499",
                    "offer": "可抵扣 1180",
                    "sellingPoints": ["修复屏障", "舒缓退红"],
                    "painPoints": ["泛红", "刺痛"],
                    "suitableUsers": "换季敏感肌用户",
                    "faq": ["不确定适不适合怎么办？先拍下锁价，到店检测。"],
                    "notes": "以门店面诊为准",
                    "durationMinutes": 15,
                }
            ],
        }

    def test_generate_two_host_html_script_and_escape_user_input(self) -> None:
        response = self.client.post(
            "/api/teleprompter/live-script/generate",
            json=self._payload(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["generatedBy"], "rule_based_v1")
        self.assertEqual(payload["templateKey"], "medical_beauty")
        self.assertEqual(payload["themeKey"], "medical_green")
        self.assertIn("萱萱：", payload["plainText"])
        self.assertIn("YK：", payload["plainText"])
        self.assertIn("主播必背清单", payload["plainText"])
        self.assertIn("quick-nav", payload["html"])
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", payload["html"])
        self.assertNotIn("<script>alert(1)</script>", payload["html"])

    def test_templates_and_authenticated_history_flow(self) -> None:
        headers = self._auth()
        templates = self.client.get("/api/teleprompter/live-script/templates")
        self.assertEqual(templates.status_code, 200, templates.text)
        keys = {item["key"] for item in templates.json()["data"]["items"]}
        self.assertIn("medical_beauty", keys)

        payload = {**self._payload(), "saveHistory": True}
        generated = self.client.post("/api/teleprompter/live-script/generate", json=payload, headers=headers)
        self.assertEqual(generated.status_code, 200, generated.text)
        script_id = generated.json()["data"]["scriptId"]
        self.assertIsInstance(script_id, int)

        listed = self.client.get("/api/teleprompter/live-script/history", headers=headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertGreaterEqual(listed.json()["data"]["total"], 1)

        detail = self.client.get(f"/api/teleprompter/live-script/history/{script_id}", headers=headers)
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertIn("html", detail.json()["data"])

        deleted = self.client.delete(f"/api/teleprompter/live-script/history/{script_id}", headers=headers)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertTrue(deleted.json()["data"]["deleted"])

    def test_import_preflight_review_themes_and_template_admin(self) -> None:
        headers = self._auth("admin-live@example.com")
        # Promote the user for template management in this focused API test.
        from database import SessionLocal
        from models.persona import UserAccount

        with SessionLocal() as db:
            user = db.query(UserAccount).filter(UserAccount.email == "admin-live@example.com").first()
            user.is_admin = True
            db.commit()

        themes = self.client.get("/api/teleprompter/live-script/themes")
        self.assertEqual(themes.status_code, 200, themes.text)
        self.assertIn("black_gold", {item["key"] for item in themes.json()["data"]["items"]})

        imported = self.client.post("/api/teleprompter/live-script/import-products", json={"rawText": "产品名称,类别,直播价,原价,权益,卖点,痛点\n修复卡,医美,499,1378,抵扣,修复屏障；舒缓退红,泛红；刺痛"})
        self.assertEqual(imported.status_code, 200, imported.text)
        self.assertEqual(imported.json()["data"]["items"][0]["name"], "修复卡")

        bad_payload = self._payload()
        bad_payload["products"][0]["livePrice"] = ""
        preflight = self.client.post("/api/teleprompter/live-script/preflight", json={"request": bad_payload})
        self.assertEqual(preflight.status_code, 200, preflight.text)
        self.assertFalse(preflight.json()["data"]["passed"])

        review = self.client.post("/api/teleprompter/live-script/review", json={
            "title": "复盘",
            "actualGmv": "10W",
            "productResults": [{"name": "修复卡", "sales": "20", "conversion": "强"}],
            "winningLines": "499 锁价",
            "weakProducts": "",
            "audienceQuestions": "多久见效",
            "notes": "下次提前讲 FAQ",
        })
        self.assertEqual(review.status_code, 200, review.text)
        self.assertIn("下次优化建议", review.json()["data"]["markdown"])

        template = self.client.post("/api/teleprompter/live-script/templates", headers=headers, json={
            "key": "qa_custom_live",
            "name": "QA 自定义模板",
            "description": "测试模板",
            "defaultStyle": "强转化",
            "openingFocus": "福利",
            "productFocus": "痛点-权益",
            "complianceTips": ["复核价格"],
            "sectionBlueprint": ["开场", "返场"],
        })
        self.assertEqual(template.status_code, 200, template.text)
        template_id = template.json()["data"]["templateId"]

        updated = self.client.put(f"/api/teleprompter/live-script/templates/{template_id}", headers=headers, json={
            "key": "qa_custom_live_updated",
            "name": "QA 自定义模板新版",
            "description": "测试模板",
            "defaultStyle": "强转化",
            "openingFocus": "福利",
            "productFocus": "痛点-权益",
            "complianceTips": ["复核价格"],
            "sectionBlueprint": ["开场", "返场"],
        })
        self.assertEqual(updated.status_code, 200, updated.text)

        removed = self.client.delete(f"/api/teleprompter/live-script/templates/{template_id}", headers=headers)
        self.assertEqual(removed.status_code, 200, removed.text)


if __name__ == "__main__":
    unittest.main()
