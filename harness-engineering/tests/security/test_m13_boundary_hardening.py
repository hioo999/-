#!/usr/bin/env python3
from __future__ import annotations

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


agent_server = load_module("agent_server_m13_boundaries", ROOT / "services" / "agent-api" / "server.py")


class M13BoundaryHardeningTest(unittest.TestCase):
    def test_data_source_must_be_under_allowed_roots_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_allowed = agent_server.ALLOWED_DATA_ROOTS
            original_forbidden = agent_server.FORBIDDEN_DATA_ROOTS
            try:
                allowed_root = Path(tmp) / "allowed"
                allowed_root.mkdir()
                outside_root = Path(tmp) / "outside"
                outside_root.mkdir()
                agent_server.ALLOWED_DATA_ROOTS = [allowed_root.resolve()]
                agent_server.FORBIDDEN_DATA_ROOTS = []
                store = agent_server.Store(Path(tmp) / "agent.db")
                source = store.add_data_source(str(allowed_root))
                self.assertEqual(source["path"], str(allowed_root.resolve()))
                with self.assertRaises(PermissionError):
                    store.add_data_source(str(outside_root))
            finally:
                agent_server.ALLOWED_DATA_ROOTS = original_allowed
                agent_server.FORBIDDEN_DATA_ROOTS = original_forbidden

    def test_forbidden_sensitive_path_segment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_allowed = agent_server.ALLOWED_DATA_ROOTS
            original_forbidden = agent_server.FORBIDDEN_DATA_ROOTS
            try:
                sensitive = Path(tmp) / ".ssh"
                sensitive.mkdir()
                agent_server.ALLOWED_DATA_ROOTS = []
                agent_server.FORBIDDEN_DATA_ROOTS = []
                store = agent_server.Store(Path(tmp) / "agent.db")
                with self.assertRaises(PermissionError):
                    store.add_data_source(str(sensitive))
            finally:
                agent_server.ALLOWED_DATA_ROOTS = original_allowed
                agent_server.FORBIDDEN_DATA_ROOTS = original_forbidden

    def test_ocr_command_must_be_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_ocr = agent_server.OCR_COMMAND
            original_allowed_commands = agent_server.OCR_ALLOWED_COMMANDS
            try:
                image = Path(tmp) / "scan.png"
                image.write_bytes(b"fake-image")
                agent_server.OCR_COMMAND = "sh -c 'echo unsafe' {file}"
                agent_server.OCR_ALLOWED_COMMANDS = {"tesseract", "python3"}
                text = agent_server.extract_text(image)
                self.assertIn("[OCR_BLOCKED]", text)
                self.assertIn("not in the allowed command list", text)
            finally:
                agent_server.OCR_COMMAND = original_ocr
                agent_server.OCR_ALLOWED_COMMANDS = original_allowed_commands


if __name__ == "__main__":
    unittest.main()
