"""安全静态扫描回归测试。"""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "src"
BACKEND_SRC = ROOT / "backend"


class SecurityStaticScanTest(unittest.TestCase):
    def iter_source_files(self):
        include_suffixes = {".py", ".ts", ".vue", ".js"}
        ignored_parts = {"node_modules", "venv", "dist", "__pycache__", "test-results"}
        for base in (FRONTEND_SRC, BACKEND_SRC):
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix not in include_suffixes:
                    continue
                if ignored_parts.intersection(path.parts):
                    continue
                yield path

    def test_frontend_does_not_use_dangerous_html_rendering(self) -> None:
        offenders = []
        for path in FRONTEND_SRC.rglob("*.vue"):
            text = path.read_text(encoding="utf-8")
            if "v-html" in text:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], f"发现 v-html 风险渲染：{offenders}")

    def test_no_hardcoded_secret_like_values(self) -> None:
        secret_patterns = [
            re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
            re.compile(r"(?i)(api[_-]?key|secret|token)\s*=\s*['\"][A-Za-z0-9_./+=-]{24,}['\"]"),
        ]
        offenders: list[str] = []
        for path in self.iter_source_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in secret_patterns:
                if pattern.search(text):
                    offenders.append(str(path.relative_to(ROOT)))
                    break
        self.assertEqual(offenders, [], f"疑似硬编码密钥：{offenders}")

    def test_sprint_routes_require_authenticated_user(self) -> None:
        route_file = BACKEND_SRC / "api" / "sprint1_routes.py"
        text = route_file.read_text(encoding="utf-8")
        self.assertIn("Depends(get_current_user)", text)
        self.assertIn("user_id == user.id", text)
        self.assertIn("TASK_NOT_FOUND", text)

    def test_material_upload_has_size_and_type_limits(self) -> None:
        route_file = BACKEND_SRC / "api" / "sprint1_routes.py"
        text = route_file.read_text(encoding="utf-8")
        self.assertIn("MAX_MATERIAL_SIZE", text)
        self.assertIn("ALLOWED_MATERIAL_EXTENSIONS", text)
        self.assertIn("ALLOWED_MATERIAL_TYPES", text)
        self.assertIn("MATERIAL_UPLOAD_FAILED", text)

    def test_prompt_template_admin_routes_require_admin_user(self) -> None:
        route_file = BACKEND_SRC / "api" / "copilot_routes.py"
        text = route_file.read_text(encoding="utf-8")
        self.assertIn("get_admin_user", text)
        self.assertIn("Depends(get_admin_user)", text)
        self.assertIn("AdminOperationLog", text)
        self.assertIn("prompt_template.update", text)


if __name__ == "__main__":
    unittest.main()
