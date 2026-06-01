#!/usr/bin/env python3
from __future__ import annotations

import base64
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


agent_server = load_module("agent_server_m12_security", ROOT / "services" / "agent-api" / "server.py")


class M12SecurityHardeningTest(unittest.TestCase):
    def test_admin_password_is_hashed_and_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            row = store.conn.execute("SELECT * FROM local_users WHERE account = 'admin'").fetchone()
            self.assertTrue(row["password_hash"].startswith("pbkdf2_sha256$"))
            self.assertNotEqual(row["password_hash"], agent_server.ADMIN_PASSWORD)
            login = store.login("admin", agent_server.ADMIN_PASSWORD)
            self.assertEqual(login["user"]["account"], "admin")
            with self.assertRaises(PermissionError):
                store.login("admin", "wrong-password")

    def test_expired_sessions_are_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            store.conn.execute("INSERT INTO local_sessions VALUES (?, ?, ?, ?, ?, ?)", ("expired", "u_admin", "admin", "agent_admin", 1, 1))
            store.conn.commit()
            removed = store.cleanup_expired_sessions()
            self.assertEqual(removed, 1)
            self.assertIsNone(store.conn.execute("SELECT * FROM local_sessions WHERE token = 'expired'").fetchone())

    def test_api_key_uses_v1_encryption_and_legacy_base64_still_decrypts(self) -> None:
        secret = "sk-local-secret"
        encrypted = agent_server.encrypt_secret(secret)
        self.assertTrue(encrypted.startswith("v1$"))
        self.assertNotIn(secret, encrypted)
        self.assertEqual(agent_server.decrypt_secret(encrypted), secret)
        legacy = base64.urlsafe_b64encode(secret.encode("utf-8")).decode("ascii")
        self.assertEqual(agent_server.decrypt_secret(legacy), secret)

    def test_model_base_url_rejects_public_hosts_and_allows_local_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = agent_server.Store(Path(tmp) / "agent.db")
            payload = {
                "provider": "openai-compatible",
                "base_url": "https://example.com/v1",
                "chat_model": "chat",
                "embedding_model": "embedding",
                "api_key": "sk-test",
            }
            with self.assertRaises(ValueError):
                store.save_model_config(payload)
            payload["base_url"] = "http://127.0.0.1:11434/v1"
            saved = store.save_model_config(payload)
            self.assertEqual(saved["base_url"], "http://127.0.0.1:11434/v1")

    def test_qdrant_public_url_is_not_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_qdrant_url = agent_server.QDRANT_URL
            try:
                store = agent_server.Store(Path(tmp) / "agent.db")
                agent_server.QDRANT_URL = "https://example.com"
                self.assertFalse(store.qdrant_enabled())
                agent_server.QDRANT_URL = "http://10.0.0.2:6333"
                self.assertTrue(store.qdrant_enabled())
            finally:
                agent_server.QDRANT_URL = original_qdrant_url


if __name__ == "__main__":
    unittest.main()
