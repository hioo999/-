#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[M2] Checking local environment"
bash scripts/check-env.sh

echo "[M2] Running unit tests"
python3 -m unittest discover -s tests -p 'test_*.py'

echo "[M2] Checking worker script syntax"
bash -n scripts/run-agent-worker.sh

echo "[M2] Checking FastAPI script syntax"
bash -n scripts/run-agent-fastapi.sh

if [ -d apps/agent-console/node_modules ]; then
  echo "[M2] Checking frontend types"
  (cd apps/agent-console && npm run check)

  echo "[M2] Building frontend"
  (cd apps/agent-console && npm run build)
else
  echo "[M2] Skipping frontend check/build because node_modules is missing"
fi

echo "[M2] Validating platform compose"
docker compose -f deploy/docker-compose.platform.yml config >/dev/null

echo "[M2] Validating agent compose"
docker compose -f deploy/docker-compose.agent.yml config >/dev/null

echo "[M2] Verification passed"
