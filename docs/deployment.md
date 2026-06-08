# Deployment

This project uses a two-environment rollout.

| Environment | Domain | Server directory | Containers |
|---|---|---|---|
| Test | `https://aip.test.seaai.com.cn` | `/opt/aip-test` | `aip-test-backend`, `aip-test-frontend`, `aip-test-nginx` |
| Production | `https://aip.seaai.com.cn` | `/opt/aip-prod` | `aip-prod-backend`, `aip-prod-frontend`, `aip-prod-nginx` |

Local builds and commits do not automatically deploy. `docker-compose.deploy.yml` is a deployment composition file, not CI/CD.

## Test Deploy

Run from the repository root:

```bash
npm run deploy:test
```

The script will:

1. Run `npm run build` in `frontend/`.
2. Run key backend regression tests.
3. Create a source release archive excluding secrets, databases, local dependencies, caches, and runtime outputs.
4. Upload the archive to `root@1.14.161.41`.
5. Preserve existing server secrets and runtime config:
   - `/opt/aip-test/.env`
   - `/opt/aip-test/backend/.env`
   - `/opt/aip-test/backend/video_engine/config.yaml`
6. Rebuild and restart the test Docker Compose stack.
7. Check backend health and the public test URL.

Useful overrides:

```bash
SKIP_LOCAL_CHECKS=1 npm run deploy:test
SKIP_PUBLIC_CHECK=1 npm run deploy:test
REMOTE_HOST=root@1.14.161.41 npm run deploy:test
DRY_RUN=1 SKIP_LOCAL_CHECKS=1 npm run deploy:test
```

Use `SKIP_LOCAL_CHECKS=1` only when the same checks have just passed locally.
Use `DRY_RUN=1` to verify archive creation without uploading or restarting the server.

## Production Deploy

Production is intentionally not automatic. Deploy it only after validating test.

```bash
npm run deploy:prod
```

The script requires typing:

```text
deploy-prod
```

It also requires the lower-level guard `CONFIRM_PROD_DEPLOY=YES`, which the wrapper sets only after the typed confirmation.

## Rollback

Each deploy stores a source backup on the server:

```text
/opt/aip-test/.deploy-backups/<timestamp>/
/opt/aip-prod/.deploy-backups/<timestamp>/
```

Manual rollback example for test:

```bash
ssh root@1.14.161.41
cd /opt/aip-test
cp -a .deploy-backups/<timestamp>/backend .
cp -a .deploy-backups/<timestamp>/frontend .
cp -a .deploy-backups/<timestamp>/nginx .
cp -a .deploy-backups/<timestamp>/docker-compose.deploy.yml .
docker compose --env-file .env -f docker-compose.deploy.yml up -d --build
curl -fsS http://127.0.0.1:18300/health
```

Do not copy local `.env` files, databases, generated outputs, or video engine runtime data into server directories.

## Database Migrations

Schema changes use Alembic under `backend/alembic/`. Existing deployments still rely on `create_all` plus startup column patches; revision `0001` is a baseline stamp only.

Manual upgrade on the server:

```bash
./scripts/db-upgrade.sh
```

Optional automatic upgrade on backend startup:

```bash
ALEMBIC_UPGRADE_ON_START=1
```

New schema changes should add Alembic revisions instead of expanding `database.py` patch helpers.
