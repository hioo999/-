#!/usr/bin/env bash
set -euo pipefail
python3 --version
if command -v docker >/dev/null 2>&1; then
  docker --version
else
  echo "docker not found; required before formal Docker Compose deployment"
fi
if docker compose version >/dev/null 2>&1; then
  docker compose version
else
  echo "docker compose not available; required before formal Docker Compose deployment"
fi
python3 - <<'PY'
import importlib.util

missing = [name for name in ("fastapi", "uvicorn") if importlib.util.find_spec(name) is None]
if missing:
    print("FastAPI target runtime dependencies missing: " + ", ".join(missing))
    print("stdlib HTTP prototype remains runnable; install services/agent-api for FastAPI entrypoint checks")
else:
    print("FastAPI target runtime dependencies found")
PY
echo "harness-engineering environment looks usable for V4.1 MVP prototype and target scaffolds"
