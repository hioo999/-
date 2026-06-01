#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


try:
    import fastapi  # noqa: F401
except ImportError:  # pragma: no cover - optional target runtime dependency
    FASTAPI_AVAILABLE = False
else:
    FASTAPI_AVAILABLE = True


EXPECTED_PATHS = {
    "/",
    "/health",
    "/api/agent/auth/login",
    "/api/agent/auth/logout",
    "/api/agent/auth/me",
    "/api/agent/status",
    "/api/agent/status/dependencies",
    "/api/agent/activate",
    "/api/agent/report-health",
    "/api/agent/data-sources/check-permission",
    "/api/agent/data-sources",
    "/api/agent/data-sources/{data_source_id}/scan",
    "/api/agent/knowledge-bases",
    "/api/agent/knowledge-bases/{kb_id}",
    "/api/agent/knowledge-bases/{kb_id}/review",
    "/api/agent/knowledge-bases/{kb_id}/archive",
    "/api/agent/knowledge-bases/{kb_id}/tree",
    "/api/agent/knowledge-bases/{kb_id}/members",
    "/api/agent/knowledge-bases/{kb_id}/members/{member_id}/revoke",
    "/api/agent/knowledge-bases/{kb_id}/stats",
    "/api/agent/folders",
    "/api/agent/folders/{folder_id}",
    "/api/agent/folders/{folder_id}/restore",
    "/api/agent/permissions/resource",
    "/api/agent/permissions/effective",
    "/api/agent/permissions/grant",
    "/api/agent/permissions/deny",
    "/api/agent/permissions/check",
    "/api/agent/permissions/{entry_id}",
    "/api/agent/tasks",
    "/api/agent/tasks/run-pending",
    "/api/agent/tasks/{task_id}",
    "/api/agent/tasks/{task_id}/retry",
    "/api/agent/worker/run-once",
    "/api/agent/cases",
    "/api/agent/cases/{case_id}",
    "/api/agent/cases/summary",
    "/api/agent/files",
    "/api/agent/files/upload",
    "/api/agent/files/parse",
    "/api/agent/files/{file_id}",
    "/api/agent/files/{file_id}/restore",
    "/api/agent/model-configs",
    "/api/agent/model-configs/{config_id}",
    "/api/agent/model-configs/{config_id}/test-chat",
    "/api/agent/model-configs/{config_id}/test-embedding",
    "/api/agent/rag/query",
    "/api/agent/rag/retrieve",
    "/api/agent/vector-store/sync-qdrant",
    "/api/agent/chats",
    "/api/agent/chats/{session_id}",
    "/api/agent/evidences",
    "/api/agent/audit-logs",
}


class M16AgentApiContractTest(unittest.TestCase):
    def test_export_agent_openapi_schema(self) -> None:
        if not FASTAPI_AVAILABLE:
            self.skipTest("FastAPI is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "agent-api-openapi.json"
            completed = subprocess.run(
                [sys.executable, "scripts/export-agent-openapi.py", "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            schema = json.loads(output.read_text("utf-8"))
            self.assertEqual(schema["info"]["title"], "V4.1 Agent Local Data Plane")
            self.assertEqual(schema["info"]["version"], "4.1.0-mvp")
            self.assertEqual(EXPECTED_PATHS - set(schema["paths"].keys()), set())

    def test_contract_document_lists_all_exported_paths(self) -> None:
        contract = (ROOT / "docs" / "agent-api-contract.md").read_text("utf-8")
        for path in sorted(EXPECTED_PATHS):
            self.assertIn(path, contract)


if __name__ == "__main__":
    unittest.main()
