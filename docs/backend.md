# Backend Notes

## Scope

`backend/` is the product API runtime. It owns authentication, personas, Copilot generation, Sprint workspace APIs, short-video workflow APIs, teleprompter APIs, and the integrated video runtime bridge.

## Entry Point

- `backend/main.py` creates the FastAPI app, loads `backend/.env`, configures CORS, initializes the database, starts the video runtime, and registers API routers.
- `backend/database.py` owns SQLAlchemy engine/session setup and local schema creation.

## Configuration

- `DATABASE_URL`: database connection. Development defaults to SQLite.
- `BACKEND_CORS_ORIGINS`: comma-separated browser origins allowed by CORS.
- `AI_PRIMARY_*` and `AI_FALLBACK_*`: content generation providers.
- `VIDEO_LLM_*` and `backend/video_engine/config.yaml`: video generation provider/runtime configuration.

## Refactor Direction

Keep routes thin and move business behavior into services. Split large model and route files by bounded context before adding more features.
