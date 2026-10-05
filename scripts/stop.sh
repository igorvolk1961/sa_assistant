#!/bin/sh
# Остановка приложения.
#   sh scripts/stop.sh          # backend + frontend
#   sh scripts/stop.sh --all    # + инфраструктура (docker compose down)
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"
RUN_DIR="$ROOT_DIR/.run"

log() { printf '\033[1;34m[stop]\033[0m %s\n' "$*"; }

stop_one() {
  name="$1"; file="$RUN_DIR/$1.pid"
  if [ ! -f "$file" ]; then
    log "$name не запущен (нет $file)"
    return 0
  fi
  pid="$(cat "$file")"
  if kill -0 "$pid" 2>/dev/null; then
    pkill -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
    log "$name остановлен (pid $pid)"
  else
    log "$name уже не работает (pid $pid)"
  fi
  rm -f "$file"
}

stop_one backend
stop_one frontend

if [ "${1:-}" = "--all" ] || [ "${1:-}" = "-a" ]; then
  log "Останавливаю инфраструктуру..."
  docker compose -f deploy/docker-compose.yml down
fi
