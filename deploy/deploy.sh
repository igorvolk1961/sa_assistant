#!/bin/sh
# Обновление и перезапуск прод-развёртывания на VPS.
#   sh deploy/deploy.sh
set -eu

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Нет deploy/.env — скопируйте пример: cp env.production.example .env (и заполните)"
  exit 1
fi

echo "[deploy] git pull"
git -C .. pull --ff-only

echo "[deploy] build & up"
docker compose -f docker-compose.prod.yml up -d --build

echo "[deploy] status"
docker compose -f docker-compose.prod.yml ps
