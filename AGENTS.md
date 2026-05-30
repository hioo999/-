# ip-system Knowledge Map

## About This Project

ip-system — A project using Harness Engineering practices (basic adoption level).

## Documentation

- Main docs: `docs/`
- Architecture decisions: `docs/architecture.md`

## Source Code

- Product backend: `backend/` (FastAPI, SQLAlchemy, AI/content/video APIs)
- Product frontend: `frontend/` (Vue 3 + Vite)
- Integrated video engine: `backend/video_engine/`
- Harness scaffold entry point: `src/index.ts` (tooling only, not the product runtime)

## Project Boundaries

- `backend/` and `frontend/` are the main product surfaces.
- `backend/video_engine/` is the integrated Pixelle runtime used by backend APIs.
- `Pixelle-Video/` is treated as a reference/vendor copy until it is moved out or converted to a pinned dependency.
- `superpowers/` is treated as an external agent/skills toolkit, not core product runtime.
- Generated dependencies and runtime artifacts such as `node_modules/`, `venv/`, `.venv/`, `dist/`, `output/`, `*.db`, and `__pycache__/` should not be edited as product source.

## Architecture

See `docs/architecture.md` for architectural decisions.
