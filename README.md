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

## Развёртывание на VPS (Docker)

Прод-стек: PostgreSQL + Redis + backend (FastAPI) + frontend (nginx).
Наружу открыт только HTTP-порт frontend; БД и Redis доступны лишь внутри docker-сети.

```bash
# 1. Docker на сервере (один раз)
curl -fsSL https://get.docker.com | sh

# 2. Код
git clone https://github.com/igorvolk1961/sa_assistant.git
cd sa_assistant/deploy

# 3. Конфиг
cp env.production.example .env
# заполните .env: POSTGRES_PASSWORD, SECRET_KEY (openssl rand -hex 32),
# BOOTSTRAP_OWNER_PASSWORD; DATABASE_URL должен содержать тот же пароль БД

# 4. Запуск (миграции и сид типов применяются автоматически при старте backend)
docker compose -f docker-compose.prod.yml up -d --build
```

Приложение: `http://212.67.8.112`, вход `admin` / `<BOOTSTRAP_OWNER_PASSWORD>`.

Обновление: `sh deploy/deploy.sh`. Логи: `docker compose -f docker-compose.prod.yml logs -f backend`.

