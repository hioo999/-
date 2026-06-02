# Frontend Notes

## Scope

`frontend/` is the Vue 3 + Vite product UI for the IP creation workspace.

## Entry Points

- `frontend/src/main.ts` mounts the Vue app.
- `frontend/src/App.vue` is the current top-level UI shell.
- `frontend/src/api/index.ts` is the current API client. It is intentionally still monolithic and should be split by domain in a later refactor.

## Configuration

- `VITE_API_BASE_URL`: API origin for browser requests. Empty value uses same-origin/proxy mode.
- `VITE_DEV_API_PROXY`: Vite development proxy target for `/api`; defaults to `http://127.0.0.1:8000`.

## Refactor Direction

Split `frontend/src/api/index.ts` into domain clients before adding more API surface. Reconnect existing workspace views through Vue Router if the product direction is the full IP workspace.
