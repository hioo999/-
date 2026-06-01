"""Platform API configuration scaffolding.

The current runnable prototype still uses ``server.py``. These settings are the
target FastAPI/PostgreSQL configuration for the M2 migration.
"""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class PlatformSettings:
    host: str = os.environ.get("PLATFORM_HOST", "127.0.0.1")
    port: int = int(os.environ.get("PLATFORM_PORT", "8100"))
    database_url: str = os.environ.get(
        "PLATFORM_DATABASE_URL",
        "postgresql://platform:platform_password@localhost:5432/platform_control",
    )
    log_level: str = os.environ.get("PLATFORM_LOG_LEVEL", "INFO")


settings = PlatformSettings()
