# Video Engine Notes

## Scope

`backend/video_engine/` is the integrated Pixelle runtime used by product backend APIs.

`Pixelle-Video/` is currently treated as a reference/vendor copy. Avoid changing both copies independently. Promote one source of truth before major video-engine work.

## Runtime

- `backend/video_engine/runtime.py` starts and stops the runtime and tracks in-memory task state.
- `backend/api/video_routes.py` exposes generation, task status, options, and file endpoints.

## Configuration

- `backend/video_engine/config.yaml`: local Pixelle runtime config.
- `backend/video_engine/config.example.yaml`: reference config template.
- `PIXELLE_VIDEO_ROOT`: optional override when the runtime is mounted elsewhere.

## Production Constraint

Video task state should be persisted before running multiple backend workers or scaling containers. The current runtime-local state is appropriate for local development only.
