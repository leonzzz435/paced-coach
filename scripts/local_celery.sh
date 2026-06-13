#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

load_root_env() {
  local env_file="$ROOT_DIR/.env"
  if [[ ! -f "$env_file" ]]; then
    return 0
  fi

  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}

load_root_env

running_services() {
  docker compose ps --services --status running 2>/dev/null || true
}

if command -v docker >/dev/null 2>&1 && running_services | grep -qx "worker"; then
  exec docker compose exec -T worker /app/.pixi/envs/default/bin/celery -A worker.celery_app "$@"
fi

export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@localhost:5432/${DATABASE_NAME:-paced_coach}}"

if command -v celery >/dev/null 2>&1; then
  CELERY_BIN="$(command -v celery)"
elif [[ -x "$ROOT_DIR/.pixi/envs/default/bin/celery" ]]; then
  CELERY_BIN="$ROOT_DIR/.pixi/envs/default/bin/celery"
else
  echo "Celery binary not found. Run via 'pixi run ...' or install the Pixi environment first." >&2
  exit 1
fi

cd "$ROOT_DIR"
exec "$CELERY_BIN" -A worker.celery_app "$@"
