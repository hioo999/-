#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cat <<'WARNING'
Production deploy target: https://aip.seaai.com.cn

Deploy production only after test environment validation passes.
Type deploy-prod to continue.
WARNING

read -r confirmation
if [[ "$confirmation" != "deploy-prod" ]]; then
  echo "Production deploy cancelled."
  exit 0
fi

CONFIRM_PROD_DEPLOY=YES exec "${ROOT_DIR}/scripts/deploy.sh" prod
