#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/deploy.sh test
  scripts/deploy.sh prod

Environment overrides:
  REMOTE_HOST=root@1.14.161.41
  REMOTE_DIR=/opt/aip-test
  APP_URL=https://aip.test.seaai.com.cn
  BACKEND_HEALTH=http://127.0.0.1:18300/health
  SKIP_LOCAL_CHECKS=1
  SKIP_PUBLIC_CHECK=1
  DRY_RUN=1

Production requires CONFIRM_PROD_DEPLOY=YES.
USAGE
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

ENVIRONMENT="$1"
case "$ENVIRONMENT" in
  test)
    REMOTE_HOST="${REMOTE_HOST:-root@1.14.161.41}"
    REMOTE_DIR="${REMOTE_DIR:-/opt/aip-test}"
    APP_URL="${APP_URL:-https://aip.test.seaai.com.cn}"
    BACKEND_HEALTH="${BACKEND_HEALTH:-http://127.0.0.1:18300/health}"
    ;;
  prod)
    if [[ "${CONFIRM_PROD_DEPLOY:-}" != "YES" ]]; then
      echo "Refusing production deploy without CONFIRM_PROD_DEPLOY=YES" >&2
      exit 3
    fi
    REMOTE_HOST="${REMOTE_HOST:-root@1.14.161.41}"
    REMOTE_DIR="${REMOTE_DIR:-/opt/aip-prod}"
    APP_URL="${APP_URL:-https://aip.seaai.com.cn}"
    BACKEND_HEALTH="${BACKEND_HEALTH:-http://127.0.0.1:18310/health}"
    ;;
  *)
    usage
    exit 2
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RELEASE_NAME="aip-system-${ENVIRONMENT}-${TIMESTAMP}"
TMP_DIR="$(mktemp -d)"
ARCHIVE="${TMP_DIR}/${RELEASE_NAME}.tar.gz"
REMOTE_TMP="/tmp/${RELEASE_NAME}.tar.gz"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cd "$ROOT_DIR"

if [[ "${SKIP_LOCAL_CHECKS:-0}" != "1" ]]; then
  echo "[deploy] Running frontend build"
  (cd frontend && npm run build)

  echo "[deploy] Running backend regression checks"
  (cd backend && python -m pytest tests/test_wechat_security.py tests/test_platform_assets_tasks_api.py -q)
else
  echo "[deploy] Skipping local checks because SKIP_LOCAL_CHECKS=1"
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [[ -n "$(git status --short)" ]]; then
    echo "[deploy] Worktree has uncommitted changes; packaging current working tree." >&2
  fi
fi

echo "[deploy] Creating release archive ${ARCHIVE}"
tar -czf "$ARCHIVE" \
  --exclude='.git' \
  --exclude='.DS_Store' \
  --exclude='node_modules' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/dist' \
  --exclude='frontend/test-results' \
  --exclude='frontend/playwright-report' \
  --exclude='backend/.env' \
  --exclude='backend/*.db' \
  --exclude='backend/data' \
  --exclude='backend/venv' \
  --exclude='backend/.venv' \
  --exclude='backend/__pycache__' \
  --exclude='backend/*/__pycache__' \
  --exclude='backend/*/*/__pycache__' \
  --exclude='backend/.pytest_cache' \
  --exclude='backend/output' \
  --exclude='backend/uploads' \
  --exclude='backend/video_engine/config.yaml' \
  --exclude='backend/video_engine/data' \
  --exclude='backend/video_engine/output' \
  --exclude='backend/video_engine/**/__pycache__' \
  --exclude='.env' \
  --exclude='.env.*' \
  backend frontend nginx docker-compose.deploy.yml

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "[deploy] Dry run archive created: ${ARCHIVE}"
  tar -tzf "$ARCHIVE" | sed -n '1,80p'
  echo "[deploy] Dry run completed without upload."
  exit 0
fi

echo "[deploy] Uploading archive to ${REMOTE_HOST}:${REMOTE_TMP}"
scp "$ARCHIVE" "${REMOTE_HOST}:${REMOTE_TMP}"

echo "[deploy] Applying release on ${REMOTE_HOST}:${REMOTE_DIR}"
ssh "$REMOTE_HOST" bash -s -- "$REMOTE_DIR" "$REMOTE_TMP" "$BACKEND_HEALTH" <<'REMOTE_SCRIPT'
set -Eeuo pipefail

remote_dir="$1"
archive="$2"
backend_health="$3"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="${remote_dir}/.deploy-backups/${timestamp}"
secret_dir="$(mktemp -d)"

cleanup() {
  rm -rf "$secret_dir"
  rm -f "$archive"
}
trap cleanup EXIT

mkdir -p "$remote_dir" "$backup_dir"
cd "$remote_dir"

for path in .env backend/.env backend/video_engine/config.yaml; do
  if [[ -f "$path" ]]; then
    mkdir -p "${secret_dir}/$(dirname "$path")"
    cp "$path" "${secret_dir}/${path}"
  fi
done

for path in backend frontend nginx docker-compose.deploy.yml; do
  if [[ -e "$path" ]]; then
    cp -a "$path" "$backup_dir/"
    rm -rf "$path"
  fi
done

tar -xzf "$archive" -C "$remote_dir"

for path in .env backend/.env backend/video_engine/config.yaml; do
  if [[ -f "${secret_dir}/${path}" ]]; then
    mkdir -p "$(dirname "$path")"
    cp "${secret_dir}/${path}" "$path"
  fi
done

if [[ ! -f .env ]]; then
  echo "Missing ${remote_dir}/.env; cannot deploy" >&2
  exit 10
fi

if [[ ! -f backend/.env ]]; then
  echo "Missing ${remote_dir}/backend/.env; cannot deploy" >&2
  exit 11
fi

if [[ ! -f backend/video_engine/config.yaml ]]; then
  echo "Missing ${remote_dir}/backend/video_engine/config.yaml; cannot deploy" >&2
  exit 12
fi

docker compose --env-file .env -f docker-compose.deploy.yml up -d --build

echo "[remote] Waiting for backend health: ${backend_health}"
for attempt in $(seq 1 30); do
  if curl -fsS "$backend_health" >/dev/null; then
    echo "[remote] Backend health check passed"
    exit 0
  fi
  sleep 2
done

echo "Backend health check failed after retries" >&2
docker compose --env-file .env -f docker-compose.deploy.yml ps >&2
exit 20
REMOTE_SCRIPT

if [[ "${SKIP_PUBLIC_CHECK:-0}" != "1" ]]; then
  echo "[deploy] Checking public app URL: ${APP_URL}"
  curl -fsS -L --max-time 30 "$APP_URL" >/dev/null
fi

echo "[deploy] ${ENVIRONMENT} deployment completed: ${APP_URL}"
