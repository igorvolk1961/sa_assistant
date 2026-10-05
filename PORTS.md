# Порты сервисов

Справочник портов, занимаемых сервисами проекта при локальном запуске.

| Сервис | Хост-порт | Порт внутри | Назначение | Источник |
| --- | --- | --- | --- | --- |
| Frontend (Vite dev) | 5173 | — | Веб-интерфейс, прокси `/api` -> backend | `frontend/vite.config.ts:7` |
| Backend (FastAPI/uvicorn) | 5000 | — | REST API, `/health`, `/docs` | `README.md:28`, `frontend/vite.config.ts:10` |
| PostgreSQL | 5435 | 5432 | Основная БД | `deploy/docker-compose.yml:9`, `backend/app/core/config.py:23` |
| Redis | 6380 | 6379 | Pub/sub, live STT-сессии | `deploy/docker-compose.yml:21`, `backend/app/core/config.py:26` |
| MinIO (S3 API) | 9005 | 9000 | S3-совместимое хранилище | `deploy/docker-compose.yml:37`, `backend/app/core/config.py:29` |
| MinIO (Console) | 9006 | 9001 | Веб-консоль MinIO | `deploy/docker-compose.yml:38` |

## Примечания

- Все порты инфраструктуры (PostgreSQL, Redis, MinIO) проброшены только на `127.0.0.1`.
- CORS backend по умолчанию разрешает `http://localhost:5173` (`CORS_ORIGINS`).
- Backend запускается командой `uv run uvicorn app.main:app --reload --port 5000` (порт 8000 в этом окружении занят другим сервисом).
