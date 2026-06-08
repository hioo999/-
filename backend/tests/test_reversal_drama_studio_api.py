"""短剧脚本工坊 Phase 1 API 测试。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f"ip_system_reversal_studio_test_{os.getpid()}.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
os.environ.setdefault("ADMIN_PASSWORD", "secret123")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from services.ai_service import AIResponse  # noqa: E402


SAMPLE_MARKDOWN = """## 一、剧本概览

- **标题**：农总的突击检查
- **时长预估**：45秒
- **痛点**：线下考试组织麻烦
- **推销产品**：AI 在线考试系统 —— 自动组卷判卷
- **反转套路**：A · 打脸老板
- **出场人物**：农总, 淇淇, 海鸥

## 二、分镜表

| 镜号 | 时长 | 画面（场景/动作/运镜） | 台词 / 旁白 | BGM / 音效 |
| :--: | :--: | :--- | :--- | :--- |
| 1 | 4s | 满桌试卷 | 这怎么改得完 | 紧张鼓点 |

## 三、结尾字幕

**【AI 在线考试系统】：省下的是改卷时间，收到的是实时数据。**

## 四、自检清单

- [x] 「起」给了可视化的狼狈画面
- [x] 反转 A / B / C 逻辑链清楚
"""


class ReversalDramaStudioApiTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.headers = self._auth("reversal-owner@example.com")

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def _auth(self, email: str) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/register",
            json={"name": "反转剧测试", "email": email, "password": "secret123"},
        )
        if response.status_code == 409:
            response = self.client.post(
                "/api/auth/login",
                json={"email": email, "password": "secret123"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def test_list_drama_templates(self) -> None:
        response = self.client.get("/api/copilot/drama-templates", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        keys = {item["key"] for item in data}
        self.assertIn("workplace_reversal", keys)
        self.assertIn("product_seed", keys)
        self.assertIn("med_aesthetics_edu", keys)
        self.assertIn("live_stream_clip", keys)
        self.assertIn("custom", keys)
        self.assertGreaterEqual(len(data), 8)

    def test_cast_preset_crud(self) -> None:
        create = self.client.post(
            "/api/copilot/drama-casts",
            headers=self.headers,
            json={
                "name": "测试二人组",
                "project_id": 0,
                "characters": [
                    {"name": "小王", "role": "老板", "drama_role": "pressure"},
                    {"name": "小李", "role": "技术", "drama_role": "reversal_carrier"},
                ],
                "relationship_hint": "老板质疑，技术翻盘",
            },
        )
        self.assertEqual(create.status_code, 200, create.text)
        cast_id = create.json()["data"]["castPresetId"]

        listing = self.client.get("/api/copilot/drama-casts", headers=self.headers)
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertTrue(any(item["castPresetId"] == cast_id for item in listing.json()["data"]))

        updated = self.client.put(
            f"/api/copilot/drama-casts/{cast_id}",
            headers=self.headers,
            json={
                "name": "测试二人组-更新",
                "project_id": 0,
                "characters": [
                    {"name": "小王", "role": "老板", "drama_role": "pressure"},
                    {"name": "小李", "role": "技术", "drama_role": "reversal_carrier"},
                ],
                "relationship_hint": "更新关系",
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["data"]["name"], "测试二人组-更新")

        deleted = self.client.delete(f"/api/copilot/drama-casts/{cast_id}", headers=self.headers)
        self.assertEqual(deleted.status_code, 200, deleted.text)

    def test_generate_with_template_and_cast_preset(self) -> None:
        cast = self.client.post(
            "/api/copilot/drama-casts",
            headers=self.headers,
            json={
                "name": "生成测试组",
                "characters": [{"name": "农总", "role": "CEO", "drama_role": "pressure"}],
            },
        )
        cast_id = cast.json()["data"]["castPresetId"]

        async def fake_chat(*args, **kwargs):
            return AIResponse(content=SAMPLE_MARKDOWN, model="test")

        with patch("api.copilot_routes.AIService.chat", side_effect=fake_chat):
            response = self.client.post(
                "/api/copilot/reversal-drama/generate",
                headers=self.headers,
                json={
                    "product_name": "AI 在线考试系统",
                    "product_function": "自动组卷判卷",
                    "pain_point": "线下考试组织麻烦",
                    "template_key": "workplace_reversal",
                    "reversal_pattern": "A",
                    "cast_source": "preset",
                    "cast_preset_id": cast_id,
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["template_key"], "workplace_reversal")
        self.assertEqual(payload["reversal_pattern"], "A")
        self.assertTrue(payload["overview"]["title"])
        self.assertTrue(payload["history_id"] > 0)

        history = self.client.get("/api/copilot/reversal-drama/history", headers=self.headers)
        self.assertEqual(history.status_code, 200, history.text)
        first = history.json()["data"][0]
        self.assertEqual(first["params"]["template_key"], "workplace_reversal")
        self.assertEqual(first["params"]["cast_preset_id"], cast_id)


if __name__ == "__main__":
    unittest.main()
