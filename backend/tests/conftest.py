"""Shared backend test environment configuration."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

TEST_DB_PATH = Path(tempfile.gettempdir()) / f"ip_system_pytest_{os.getpid()}.db"
TEST_UPLOAD_DIR = Path(tempfile.gettempdir()) / f"ip_system_pytest_uploads_{os.getpid()}"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("ADMIN_PASSWORD", "secret123")
os.environ.setdefault("PLATFORM_UPLOAD_DIR", str(TEST_UPLOAD_DIR))


def pytest_sessionfinish(session, exitstatus):
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if TEST_UPLOAD_DIR.exists():
        shutil.rmtree(TEST_UPLOAD_DIR)
