#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
echo "Agent PostgreSQL migrations are scaffolded in migrations/agent/."
echo "Wire this script to psql or Alembic when FastAPI/PostgreSQL implementation lands."
