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


agent_server = load_module("agent_server_store_auth", ROOT / "services" / "agent-api" / "server.py")


class AgentStoreAuthTest(unittest.TestCase):
    def test_login_current_user_logout_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            login = store.login("admin", "admin")
            user = store.current_user(login["token"])
            self.assertEqual(user["account"], "admin")
            self.assertEqual(user["role"], "agent_admin")
            self.assertTrue(store.logout(login["token"])["logged_out"])
            with self.assertRaises(PermissionError):
                store.current_user(login["token"])

    def test_invalid_login_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            with self.assertRaises(PermissionError):
                store.login("admin", "wrong-password")

    def test_status_payload_reports_local_dependencies_without_business_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_data_dir = agent_server.DATA_DIR
            original_storage_dir = agent_server.STORAGE_DIR
            agent_server.DATA_DIR = Path(tmp)
            agent_server.STORAGE_DIR = Path(tmp) / "storage"
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                status = store.status_payload()
                self.assertEqual(status["service"], "agent-api")
                self.assertEqual(status["database"], "ok")
                serialized = str(status)
                self.assertNotIn("file_name", serialized)
                self.assertNotIn("case_name", serialized)
            finally:
                agent_server.DATA_DIR = original_data_dir
                agent_server.STORAGE_DIR = original_storage_dir


if __name__ == "__main__":
    unittest.main()
