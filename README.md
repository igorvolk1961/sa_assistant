# SA Assistant

Помощник системного аналитика. Полный план — в `PLAN.md`.

## Структура

- `backend/` — FastAPI + SQLAlchemy 2 + Alembic + Procrastinate.
- `frontend/` — React + TypeScript (Vite).
- `deploy/` — docker-compose для локального запуска (PostgreSQL, Redis, MinIO).

## Быстрый старт (скрипты)

Скрипты POSIX-совместимы: запускайте как `./scripts/start.sh`, либо
`sh scripts/start.sh`, либо `bash scripts/start.sh`.

```bash
./scripts/start.sh       # инфраструктура + миграции + backend + frontend
./scripts/status.sh      # статус сервисов
./scripts/stop.sh        # остановить приложение
./scripts/stop.sh --all  # + остановить инфраструктуру
```

После старта: UI — http://127.0.0.1:5173, API — http://127.0.0.1:5000/docs,
логин `admin` / `owner12345` (dev). Логи процессов — в `.run/`.

## Быстрый старт (backend)

```bash
cp .env.example .env
cd deploy && docker compose up -d
cd ../backend && uv sync --python /usr/bin/python3 --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 5000
```

Healthcheck: `GET /health`. OpenAPI: `/docs`.

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, прокси /api -> http://localhost:5000
```

Страницы: вход/регистрация, выбор проекта, задачи (мои/все, фильтры, карточка с
подзадачами, зависимостями, файлами, комментариями и приёмкой), требования
(создание задач из карточки), встречи (журнал, импорт внешних транскриптов,
незаданные обязательные вопросы), сотрудники/стейкхолдеры, участники и роли.

## Тесты

Тесты используют отдельную БД `sa_assistant_test` (создаётся автоматически,
миграции накатываются, данные очищаются перед прогоном) — dev-БД не затрагивается.

```bash
cd backend && uv run pytest
uv run ruff check .
cd ../frontend && npm run typecheck
```

## Сброс dev-БД

```bash
cd backend && uv run python scripts/reset_db.py   # отказ при APP_ENV=production
```

