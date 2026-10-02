# SA Assistant

Помощник системного аналитика. Полный план — в `PLAN.md`.

## Структура

- `backend/` — FastAPI + SQLAlchemy 2 + Alembic + Procrastinate.
- `frontend/` — React + TypeScript (Vite).
- `deploy/` — docker-compose для локального запуска (PostgreSQL, Redis, MinIO).

## Быстрый старт (backend)

```bash
cp .env.example .env
cd deploy && docker compose up -d
cd ../backend && uv sync --python /usr/bin/python3 --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Healthcheck: `GET /health`. OpenAPI: `/docs`.

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, прокси /api -> http://localhost:8000
```

Страницы: вход/регистрация, выбор проекта, задачи (мои/все, фильтры, карточка с
подзадачами, зависимостями, файлами, комментариями и приёмкой), требования
(создание задач из карточки), встречи (журнал, импорт внешних транскриптов,
незаданные обязательные вопросы), сотрудники/стейкхолдеры, участники и роли.

## Тесты

```bash
cd backend && uv run pytest
uv run ruff check .
cd ../frontend && npm run typecheck
```

