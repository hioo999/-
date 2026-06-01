#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
echo "Platform PostgreSQL migrations are scaffolded in migrations/platform/."
echo "Wire this script to psql or Alembic when FastAPI/PostgreSQL implementation lands."
