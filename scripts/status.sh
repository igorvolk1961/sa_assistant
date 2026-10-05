#!/bin/sh
# Статус сервисов приложения.
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"
RUN_DIR="$ROOT_DIR/.run"

BACKEND_PORT="${BACKEND_PORT:-5000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

check_http() {
  url="$1"; name="$2"
  if curl -fsS -m 2 "$url" >/dev/null 2>&1; then
    printf '  %-10s UP    %s\n' "$name" "$url"
  else
    printf '  %-10s DOWN  %s\n' "$name" "$url"
  fi
}

check_pid() {
  name="$1"; file="$RUN_DIR/$1.pid"
  if [ -f "$file" ] && kill -0 "$(cat "$file")" 2>/dev/null; then
    printf '  %-10s UP    pid %s\n' "$name" "$(cat "$file")"
  else
    printf '  %-10s DOWN\n' "$name"
  fi
}

echo "Приложение:"
check_pid backend
check_pid frontend
check_http "http://127.0.0.1:$BACKEND_PORT/health" "api"
check_http "http://127.0.0.1:$FRONTEND_PORT/" "ui"
echo
echo "Инфраструктура:"
docker compose -f deploy/docker-compose.yml ps
