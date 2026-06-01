"""Agent API configuration scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AgentSettings:
    host: str = os.environ.get("AGENT_HOST", "127.0.0.1")
    port: int = int(os.environ.get("AGENT_PORT", "8200"))
    database_url: str = os.environ.get(
        "AGENT_LOCAL_DATABASE_URL",
        "postgresql://agent:agent_password@localhost:5432/agent_local",
    )
    redis_url: str = os.environ.get("AGENT_REDIS_URL", "redis://localhost:6379/0")
    vector_database_url: str = os.environ.get("AGENT_VECTOR_DATABASE_URL", "http://localhost:6333")
    platform_base_url: str = os.environ.get("AGENT_PLATFORM_BASE_URL", "http://127.0.0.1:8100")
    storage_root: str = os.environ.get("AGENT_LOCAL_STORAGE_ROOT", "services/agent-api/data/storage")
    max_upload_size_mb: int = int(os.environ.get("AGENT_MAX_UPLOAD_SIZE_MB", "100"))
    allowed_file_extensions: tuple[str, ...] = tuple(
        item.strip() for item in os.environ.get(
            "AGENT_ALLOWED_FILE_EXTENSIONS",
            ".pdf,.doc,.docx,.png,.jpg,.jpeg,.txt",
        ).split(",")
    )


settings = AgentSettings()
