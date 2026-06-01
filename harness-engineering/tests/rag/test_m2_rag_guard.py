#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rag_guard = load_module("rag_guard", ROOT / "services" / "agent-api" / "app" / "services" / "rag_guard.py")


class M2RagGuardTest(unittest.TestCase):
    def test_refuses_when_no_citations(self) -> None:
        result = rag_guard.answer_or_refuse("unsupported answer", [])
        self.assertTrue(result["insufficient_evidence"])
        self.assertIn("未检索到充分依据", result["answer"])

    def test_allows_answer_with_citations(self) -> None:
        result = rag_guard.answer_or_refuse("source-backed answer", [{"chunk_id": "chunk_1"}])
        self.assertFalse(result["insufficient_evidence"])
        self.assertEqual(result["answer"], "source-backed answer")


if __name__ == "__main__":
    unittest.main()
