# SA Assistant

Помощник системного аналитика. Полный план — в `PLAN.md`.

## Структура

- `backend/` — FastAPI + SQLAlchemy 2 + Alembic + Procrastinate.
- `frontend/` — React + TypeScript (Vite) *(в разработке)*.
- `deploy/` — docker-compose для локального запуска (PostgreSQL, Redis, MinIO).

## Быстрый старт (backend)

```bash
cp .env.example .env
cd deploy && docker compose up -d
cd ../backend && uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Healthcheck: `GET /health`. OpenAPI: `/docs`.

## Тесты

```bash
cd backend && uv run pytest
uv run ruff check .
```
