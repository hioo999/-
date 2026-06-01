# ip-system Knowledge Map

## About This Project

ip-system — A project using Harness Engineering practices (basic adoption level).

## Documentation

- Main docs: `docs/`
- Architecture decisions: `docs/architecture.md`
- Confirmed product requirements must be captured as PRD documents under `docs/`.

## Requirement Documentation Workflow

- When the user discusses a new product requirement, first clarify only the necessary ambiguous points and confirm the intended scope.
- After the requirement is confirmed, automatically create or update a PRD in `docs/` without waiting for an extra documentation request.
- The PRD should cover background, goals, user flow, functional scope, page/API/data needs, priorities, acceptance criteria, risks, and implementation phases when applicable.
- Keep related but separable requirements in separate PRDs, and link them from `docs/index.md`.
- Current confirmed requirements include video AIP media-task execution and WeChat official account article formatting/draft publishing.

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
