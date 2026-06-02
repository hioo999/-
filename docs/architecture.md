# ip-system Architecture

## Product Boundary

The product is a full-stack IP creation workspace. The main runtime code lives in:

- `backend/`: FastAPI backend, SQLAlchemy models, AI generation services, content parsing, persona and video APIs.
- `frontend/`: Vue 3 + Vite frontend, workspace views, API client, Playwright end-to-end tests.
- `backend/video_engine/`: integrated Pixelle-based video generation runtime used by backend video APIs.

The following directories are not primary product surfaces:

- `src/`: Harness Engineering scaffold used for tooling checks.
- `Pixelle-Video/`: reference/vendor copy of the upstream Pixelle system. It should be moved out of the product root or converted to a pinned dependency/submodule before major video-engine changes.
- `superpowers/`: external agent/skills toolkit. Treat as vendor/tooling unless explicitly changing that subsystem.

## Runtime Flow

The frontend calls backend APIs under `/api/*`. The backend loads `backend/.env`, initializes the database, registers route modules, and starts the optional video runtime. Video runtime startup failures should not block the main API; video routes report readiness through their own endpoints.

## Configuration

- `DATABASE_URL` controls database connection. Development defaults to local SQLite.
- `BACKEND_CORS_ORIGINS` controls browser origins allowed by CORS. Use explicit origins in production.
- `VITE_API_BASE_URL` controls frontend API requests. Empty value means same-origin/proxy mode in Vite development.

## Current Constraints

- Database schema is currently created by SQLAlchemy metadata at startup. Add Alembic migrations before production schema evolution.
- Video task state is currently runtime-local. Persist task state before running multiple backend workers or scaling containers.
- The frontend API client is intentionally left intact for now, but should be split by bounded context as the next refactor.

## Recommended Module Boundaries

- `backend/api/`: thin HTTP route handlers.
- `backend/services/`: business logic and provider adapters.
- `backend/models/`: SQLAlchemy models split by bounded context.
- `backend/schemas/`: request/response schemas when the API surface stabilizes.
- `frontend/src/api/`: API client modules split by domain.
- `frontend/src/views/`: route-level pages/workspaces.
- `frontend/src/components/`: reusable UI components.
