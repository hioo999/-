#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${AGENT_PYTHON:-python3}"
exec "${PYTHON_BIN}" "${SCRIPT_DIR}/export-diagnostics.py" "$@"
