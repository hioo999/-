"""内容合规样本回归测试。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"ip_system_compliance_test_{os.getpid()}.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

HIGH_RISK_TERMS = ["包过", "稳赚", "躺赚", "百分百", "保证有效", "全网唯一", "第一", "最强"]


class ComplianceSampleTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.headers = self._auth()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def _auth(self) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/register",
            json={"name": "Compliance", "email": "compliance@example.com", "password": "secret123"},
        )
        if response.status_code == 409:
            response = self.client.post(
                "/api/auth/login",
                json={"email": "compliance@example.com", "password": "secret123"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def _assert_low_risk_text(self, value: str) -> None:
        for term in HIGH_RISK_TERMS:
            self.assertNotIn(term, value, f"生成内容包含高风险表达：{term}")

    def test_generated_foundation_copy_avoids_high_risk_terms(self) -> None:
        ip_payload = {
            "name": "教育咨询IP",
            "type": "expert",
            "industry": "职业教育",
            "targetAudience": "大学生和职场新人",
            "businessGoal": "consulting_leads",
            "mainPlatforms": ["wechat", "shipinhao"],
            "secondaryPlatforms": ["xiaohongshu", "moments"],
            "tone": "专业、直接、审慎",
            "visualStyle": "可信、干净",
            "conversionPath": "内容科普 -> 私信咨询 -> 预约诊断",
            "forbiddenExpressions": "不承诺保offer，不使用包过、稳赚、百分百等表达",
        }
        created = self.client.post("/api/ip-assets", json=ip_payload, headers=self.headers)
        self.assertEqual(created.status_code, 200, created.text)
        ip_id = created.json()["data"]["ipId"]

        strategy = self.client.post("/api/strategies/generate", json={"ipId": ip_id}, headers=self.headers)
        self.assertEqual(strategy.status_code, 200, strategy.text)
        strategy_data = strategy.json()["data"]
        self._assert_low_risk_text(strategy_data["positioning"])
        self._assert_low_risk_text(strategy_data["targetUserProfile"])
        self.assertIn("不制造过度焦虑", strategy_data["forbiddenDirections"])

        columns = self.client.post(
            "/api/columns/generate",
            json={"ipId": ip_id, "strategyId": strategy_data["strategyId"]},
            headers=self.headers,
        )
        self.assertEqual(columns.status_code, 200, columns.text)
        for column in columns.json()["data"]["items"]:
            self._assert_low_risk_text(column["positioning"])
            self._assert_low_risk_text(column["conversionAction"])

        topics = self.client.post("/api/topics/generate", json={"ipId": ip_id, "count": 20}, headers=self.headers)
        self.assertEqual(topics.status_code, 200, topics.text)
        topic = topics.json()["data"]["items"][0]
        self._assert_low_risk_text(topic["title"])
        self._assert_low_risk_text(topic["coreViewpoint"])

        draft = self.client.post(
            "/api/content-drafts/generate",
            json={"ipId": ip_id, "topicId": topic["id"]},
            headers=self.headers,
        )
        self.assertEqual(draft.status_code, 200, draft.text)
        draft_data = draft.json()["data"]
        for key in ["painPoint", "coreViewpoint", "logic", "cases", "conversionAction", "forbiddenExpressions"]:
            self._assert_low_risk_text(str(draft_data[key]))
        for sentence in draft_data["goldenSentences"]:
            self._assert_low_risk_text(sentence)


if __name__ == "__main__":
    unittest.main()
