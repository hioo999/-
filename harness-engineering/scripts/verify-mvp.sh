#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${AGENT_PYTHON:-}" ]; then
  PYTHON_BIN="$AGENT_PYTHON"
elif [ -x ".venv-agent-api/bin/python" ]; then
  PYTHON_BIN=".venv-agent-api/bin/python"
else
  PYTHON_BIN="python3"
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[MVP] Checking local environment"
bash scripts/check-env.sh

echo "[MVP] Running pytest regression suite with ${PYTHON_BIN}"
"$PYTHON_BIN" -m pytest

echo "[MVP] Exporting Agent OpenAPI schema"
if "$PYTHON_BIN" scripts/export-agent-openapi.py --output "$TMP_DIR/agent-api-openapi.json" >/dev/null 2>&1; then
  test -s "$TMP_DIR/agent-api-openapi.json"
else
  echo "[MVP] Skipping OpenAPI export because FastAPI runtime is unavailable for ${PYTHON_BIN}"
fi

echo "[MVP] Previewing redacted diagnostics export"
set +e
"$PYTHON_BIN" scripts/export-diagnostics.py --output-dir "$TMP_DIR/diagnostics" >/dev/null 2>"$TMP_DIR/diagnostics.err"
DIAG_STATUS=$?
set -e
if [ "$DIAG_STATUS" -ne 3 ]; then
  cat "$TMP_DIR/diagnostics.err" >&2
  echo "[MVP] Diagnostics preview must refuse export without --confirm" >&2
  exit 1
fi

echo "[MVP] Exporting platform-invisibility acceptance report"
"$PYTHON_BIN" scripts/export-platform-invisibility-report.py --output "$TMP_DIR/platform-invisibility-report.json" >/dev/null
test -s "$TMP_DIR/platform-invisibility-report.json"

echo "[MVP] Scanning platform-invisibility report redlines"
"$PYTHON_BIN" scripts/scan-platform-invisibility-redlines.py --path "$TMP_DIR/platform-invisibility-report.json" >/dev/null

echo "[MVP] Checking script syntax"
bash -n scripts/run-agent.sh
bash -n scripts/run-agent-fastapi.sh
bash -n scripts/run-agent-worker.sh
bash -n scripts/export-diagnostics.sh
bash -n scripts/verify-mvp.sh

if [ -d apps/agent-console/node_modules ]; then
  echo "[MVP] Checking Agent Console scaffold and delivery UI"
  (cd apps/agent-console && npm run check:scaffold && npm run check:delivery-ui && npm run check:browser-smoke)

  echo "[MVP] Checking Agent Console types"
  (cd apps/agent-console && npm run check)

  echo "[MVP] Building Agent Console"
  (cd apps/agent-console && npm run build && npm run check:delivery-ui)
else
  echo "[MVP] Skipping Agent Console checks because node_modules is missing"
fi

echo "[MVP] Checking Platform Console invisibility UI contract"
node apps/platform-console/scripts/check-invisibility-ui.mjs

echo "[MVP] Validating deployment config security"
"$PYTHON_BIN" scripts/validate-deploy-config.py --mode example

echo "[MVP] Scanning delivery artifacts for leaks"
"$PYTHON_BIN" scripts/scan-delivery-artifacts.py

echo "[MVP] Checking delivery package boundary"
"$PYTHON_BIN" scripts/check-delivery-package.py

echo "[MVP] Exporting delivery package smoke archive"
"$PYTHON_BIN" scripts/export-delivery-package.py --output "$TMP_DIR/harness-engineering-delivery.tar.gz" >/dev/null
test -s "$TMP_DIR/harness-engineering-delivery.tar.gz"

echo "[MVP] Verifying delivery package smoke archive"
"$PYTHON_BIN" scripts/verify-delivery-package.py --archive "$TMP_DIR/harness-engineering-delivery.tar.gz" --require-checksum --extract-smoke >/dev/null

echo "[MVP] Exporting delivery acceptance evidence report"
"$PYTHON_BIN" scripts/export-delivery-acceptance-report.py --archive "$TMP_DIR/harness-engineering-delivery.tar.gz" --output "$TMP_DIR/delivery-acceptance-report.json" >/dev/null
test -s "$TMP_DIR/delivery-acceptance-report.json"

echo "[MVP] Verifying delivery acceptance evidence report"
"$PYTHON_BIN" scripts/verify-delivery-acceptance-report.py --report "$TMP_DIR/delivery-acceptance-report.json" >/dev/null
"$PYTHON_BIN" scripts/scan-delivery-acceptance-report.py --report "$TMP_DIR/delivery-acceptance-report.json" >/dev/null
"$PYTHON_BIN" scripts/scan-platform-invisibility-redlines.py --path "$TMP_DIR/delivery-acceptance-report.json" >/dev/null

echo "[MVP] Exporting verified delivery bundle"
"$PYTHON_BIN" scripts/export-delivery-bundle.py --output-dir "$TMP_DIR/delivery-bundle" >/dev/null
test -s "$TMP_DIR/delivery-bundle/harness-engineering-delivery.tar.gz"
test -s "$TMP_DIR/delivery-bundle/harness-engineering-delivery.tar.gz.sha256"
test -s "$TMP_DIR/delivery-bundle/delivery-acceptance-report.json"
test -s "$TMP_DIR/delivery-bundle/delivery-bundle-manifest.json"

echo "[MVP] Verifying delivery bundle manifest"
"$PYTHON_BIN" scripts/verify-delivery-bundle.py --manifest "$TMP_DIR/delivery-bundle/delivery-bundle-manifest.json" >/dev/null
"$PYTHON_BIN" scripts/scan-platform-invisibility-redlines.py --path "$TMP_DIR/delivery-bundle/delivery-bundle-manifest.json" >/dev/null

echo "[MVP] Smoking extracted delivery bundle"
"$PYTHON_BIN" scripts/smoke-delivery-bundle-extract.py --bundle-dir "$TMP_DIR/delivery-bundle" >/dev/null

if command -v docker >/dev/null 2>&1; then
  echo "[MVP] Validating platform compose"
  docker compose -f deploy/docker-compose.platform.yml config >/dev/null

  echo "[MVP] Validating agent compose"
  docker compose -f deploy/docker-compose.agent.yml config >/dev/null
else
  echo "[MVP] Skipping compose validation because docker is unavailable"
fi

echo "[MVP] Verification passed"
