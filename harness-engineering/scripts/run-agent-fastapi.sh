#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${AGENT_FASTAPI_HOST:-${AGENT_HOST:-127.0.0.1}}"
PORT="${AGENT_FASTAPI_PORT:-8201}"
PYTHON_BIN="${AGENT_PYTHON:-}"

if [ -z "$PYTHON_BIN" ]; then
  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
  elif command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  else
    PYTHON_BIN="python3"
  fi
fi

"$PYTHON_BIN" - <<'PY'
import importlib.util
import sys

missing = [name for name in ("fastapi", "uvicorn") if importlib.util.find_spec(name) is None]
if missing:
    print("Missing FastAPI runtime dependencies: " + ", ".join(missing), file=sys.stderr)
    print("Install the agent-api target runtime with Python 3.11/3.12, for example:", file=sys.stderr)
    print("  python3.11 -m venv .venv-agent-api", file=sys.stderr)
    print("  .venv-agent-api/bin/python -m pip install -e 'services/agent-api[test]'", file=sys.stderr)
    print("  AGENT_PYTHON=.venv-agent-api/bin/python bash scripts/run-agent-fastapi.sh", file=sys.stderr)
    sys.exit(1)
PY

exec "$PYTHON_BIN" -m uvicorn app.main:app --app-dir services/agent-api --host "$HOST" --port "$PORT"
