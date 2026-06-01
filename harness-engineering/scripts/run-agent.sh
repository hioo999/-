#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUNTIME="${AGENT_RUNTIME:-stdlib}"
PYTHON_BIN="${AGENT_PYTHON:-python3}"

case "$RUNTIME" in
  stdlib)
    if [ "${AGENT_DRY_RUN:-0}" = "1" ]; then
      printf '%q ' "$PYTHON_BIN" services/agent-api/server.py
      printf '\n'
      exit 0
    fi
    exec "$PYTHON_BIN" services/agent-api/server.py
    ;;
  fastapi)
    if [ "${AGENT_DRY_RUN:-0}" = "1" ]; then
      printf 'AGENT_PYTHON=%q bash scripts/run-agent-fastapi.sh\n' "$PYTHON_BIN"
      exit 0
    fi
    exec env AGENT_PYTHON="$PYTHON_BIN" bash scripts/run-agent-fastapi.sh
    ;;
  *)
    echo "Unsupported AGENT_RUNTIME: $RUNTIME" >&2
    echo "Use AGENT_RUNTIME=stdlib or AGENT_RUNTIME=fastapi" >&2
    exit 2
    ;;
esac
