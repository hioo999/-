#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import os
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


agent_server = load_module("agent_server_m10_ocr", ROOT / "services" / "agent-api" / "server.py")


class M10OcrAdapterTest(unittest.TestCase):
    def test_image_extract_returns_pending_when_ocr_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_ocr_command = agent_server.OCR_COMMAND
            try:
                agent_server.OCR_COMMAND = ""
                image = Path(tmp) / "scan.png"
                image.write_bytes(b"fake-image")
                text = agent_server.extract_text(image)
                self.assertIn("[OCR_PENDING]", text)
            finally:
                agent_server.OCR_COMMAND = original_ocr_command

    def test_image_parse_uses_configured_local_ocr_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_ocr_command = agent_server.OCR_COMMAND
            original_storage_dir = agent_server.STORAGE_DIR
            try:
                script = Path(tmp) / "ocr.py"
                script.write_text("import sys\nprint('扫描件显示乙方已经付款 ' + sys.argv[1])\n", "utf-8")
                agent_server.OCR_COMMAND = f"python3 {script} {{file}}"
                agent_server.STORAGE_DIR = Path(tmp) / "storage"
                store = agent_server.Store(Path(tmp) / "agent.db")
                case = store.create_case({"title": "扫描件案件"})
                content = base64.b64encode(b"fake-image").decode("ascii")
                file = store.save_uploaded_file(case["id"], "scan.png", content)
                result = store.run_pending_tasks()
                self.assertEqual(result["success_count"], 1)
                chunks = store.conn.execute("SELECT chunk_text FROM document_chunks WHERE file_id = ?", (file["id"],)).fetchall()
                self.assertEqual(len(chunks), 1)
                self.assertIn("扫描件显示乙方已经付款", chunks[0]["chunk_text"])
                answer = store.ask(case["id"], "乙方是否付款？")
                self.assertFalse(answer["insufficient_evidence"])
                self.assertGreaterEqual(len(answer["citations"]), 1)
                self.assertTrue(store.status_payload()["ocr_configured"])
            finally:
                agent_server.OCR_COMMAND = original_ocr_command
                agent_server.STORAGE_DIR = original_storage_dir

    def test_ocr_command_failure_is_captured_as_local_text_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_ocr_command = agent_server.OCR_COMMAND
            try:
                script = Path(tmp) / "ocr_fail.py"
                script.write_text("import sys\nsys.stderr.write('engine failed')\nsys.exit(2)\n", "utf-8")
                agent_server.OCR_COMMAND = f"python3 {script} {{file}}"
                image = Path(tmp) / "scan.jpg"
                image.write_bytes(b"fake-image")
                text = agent_server.extract_text(image)
                self.assertIn("[OCR_FAILED]", text)
                self.assertIn("engine failed", text)
            finally:
                agent_server.OCR_COMMAND = original_ocr_command


if __name__ == "__main__":
    unittest.main()
