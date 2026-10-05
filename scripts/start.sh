#!/bin/sh
# Быстрый старт приложения: инфраструктура + backend + frontend.
# POSIX sh (работает через sh, bash и ./scripts/start.sh).
#
# Использование:
#   ./scripts/start.sh
#   BACKEND_PORT=5000 FRONTEND_PORT=5173 sh scripts/start.sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT="${BACKEND_PORT:-5000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
RUN_DIR="$ROOT_DIR/.run"
mkdir -p "$RUN_DIR"

log() { printf '\033[1;34m[start]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

require() {
  command -v "$1" >/dev/null 2>&1 || { err "не найдена команда '$1'"; exit 1; }
}
require docker
require uv
require npm
require curl

# ---- 1. .env ----
if [ ! -f .env ]; then
  cp .env.example .env
  log "Создан .env из .env.example"
fi
if ! grep -q '^SECRET_KEY=.\+' .env; then
  sed -i 's|^SECRET_KEY=.*|SECRET_KEY=dev-secret-key-change-me-32bytes-0001|' .env
  log "Проставлен dev SECRET_KEY"
fi
if ! grep -q '^BOOTSTRAP_OWNER_PASSWORD=.\+' .env; then
  sed -i 's|^BOOTSTRAP_OWNER_PASSWORD=.*|BOOTSTRAP_OWNER_PASSWORD=owner12345|' .env
  log "Проставлен dev пароль владельца"
fi

# ---- 2. Инфраструктура ----
log "Поднимаю PostgreSQL, Redis, MinIO..."
docker compose -f deploy/docker-compose.yml up -d --wait

# ---- 3. Backend ----
log "Устанавливаю зависимости backend (uv sync)..."
(cd backend && uv sync --python /usr/bin/python3 --extra dev >/dev/null)

log "Накатываю миграции..."
(cd backend && uv run alembic upgrade head >/dev/null)

is_running() {
  [ -f "$RUN_DIR/$1.pid" ] && kill -0 "$(cat "$RUN_DIR/$1.pid")" 2>/dev/null
}

if is_running backend; then
  log "Backend уже запущен (pid $(cat "$RUN_DIR/backend.pid"))"
else
  log "Запускаю backend на 127.0.0.1:$BACKEND_PORT..."
  (cd backend && nohup .venv/bin/uvicorn app.main:app \
      --host 127.0.0.1 --port "$BACKEND_PORT" \
      >"$RUN_DIR/backend.log" 2>&1 < /dev/null &
   echo $! >"$RUN_DIR/backend.pid")
fi

# ---- 4. Frontend ----
if [ ! -d frontend/node_modules ]; then
  log "Устанавливаю зависимости frontend (npm install)..."
  (cd frontend && npm install >/dev/null)
fi

if is_running frontend; then
  log "Frontend уже запущен (pid $(cat "$RUN_DIR/frontend.pid"))"
else
  log "Запускаю frontend на 127.0.0.1:$FRONTEND_PORT..."
  (cd frontend && nohup node_modules/.bin/vite \
      --host 127.0.0.1 --port "$FRONTEND_PORT" \
      >"$RUN_DIR/frontend.log" 2>&1 < /dev/null &
   echo $! >"$RUN_DIR/frontend.pid")
fi

# ---- 5. Ожидание готовности ----
wait_for() {
  url="$1"; name="$2"; i=1
  while [ "$i" -le 60 ]; do
    if curl -fsS -m 2 "$url" >/dev/null 2>&1; then
      log "$name готов: $url"
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  err "$name не поднялся за 60с ($url). Смотрите $RUN_DIR/${name}.log"
  return 1
}
wait_for "http://127.0.0.1:$BACKEND_PORT/health" backend
wait_for "http://127.0.0.1:$FRONTEND_PORT/" frontend

cat <<EOF

Готово.
  UI:        http://127.0.0.1:$FRONTEND_PORT
  API/docs:  http://127.0.0.1:$BACKEND_PORT/docs
  Логин:     admin / owner12345 (dev)
  Логи:      .run/backend.log, .run/frontend.log
  Статус:    sh scripts/status.sh
  Остановка: sh scripts/stop.sh          (инфраструктура: sh scripts/stop.sh --all)

EOF
