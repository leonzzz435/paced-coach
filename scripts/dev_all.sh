#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/web/app"

resolve_pixi() {
  if [[ -n "${PIXI:-}" ]]; then
    printf "%s" "$PIXI"
    return 0
  fi

  if command -v pixi >/dev/null 2>&1; then
    command -v pixi
    return 0
  fi

  local home_dir="${HOME:-}"
  if [[ -z "$home_dir" ]]; then
    home_dir="$(python3 -c 'from pathlib import Path; print(Path.home())')"
  fi

  local home_pixi="${home_dir}/.pixi/bin/pixi"
  if [[ -x "$home_pixi" ]]; then
    printf "%s" "$home_pixi"
    return 0
  fi

  return 1
}

PIXI_BIN="$(resolve_pixi || true)"

load_root_env() {
  local env_file="$ROOT_DIR/.env"
  if [[ ! -f "$env_file" ]]; then
    return 0
  fi

  # Export root .env so local overrides apply to docker compose and Alembic.
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}

load_root_env

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker is not installed (needed for 'docker compose up')" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "error: 'docker compose' is not available. Install Docker Compose v2." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm is not installed (needed for the Next.js dev server)" >&2
  exit 1
fi

if [[ ! -d "$WEB_DIR" ]]; then
  echo "error: expected Next.js app at $WEB_DIR" >&2
  exit 1
fi

ensure_web_dependencies() {
  if [[ -d "$WEB_DIR/node_modules" ]]; then
    return 0
  fi

  echo "Installing web dependencies..."
  (cd "$WEB_DIR" && npm ci --ignore-scripts)
}

cleanup() {
  echo
  echo "Stopping dev processes..."
  docker compose down >/dev/null 2>&1 || true
}
trap cleanup INT TERM EXIT

ensure_infra_up() {
  echo "Starting infra (db/redis) via docker compose..."
  docker compose up -d db redis >/dev/null
}

wait_for_db() {
  local attempts="${DB_READY_ATTEMPTS:-60}"
  local sleep_s="${DB_READY_SLEEP_SECONDS:-1}"

  echo "Waiting for Postgres health..."
  for ((i = 1; i <= attempts; i++)); do
    if docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
      echo "Postgres is ready."
      return 0
    fi
    sleep "$sleep_s"
  done

  echo "warning: Postgres not reported healthy after $((attempts * sleep_s))s; continuing anyway." >&2
  return 0
}

resolve_database_url() {
  local db_url="${DATABASE_URL:-}"
  if [[ -z "$db_url" ]]; then
    local db_name="${DATABASE_NAME:-paced_coach}"
    # When `docker compose up -d db` runs, the database is on the local host port.
    # Using localhost avoids DNS issues and matches typical dev setups.
    db_url="postgresql+asyncpg://postgres:postgres@localhost:5432/${db_name}"
  fi

  printf "%s" "$db_url"
}

resolve_database_name() {
  local db_url="$1"
  local url_no_query="${db_url%%\?*}"
  local db_name="${url_no_query##*/}"
  printf "%s" "$db_name"
}

sync_compose_database_name() {
  local db_url
  db_url="$(resolve_database_url)"
  local db_name
  db_name="$(resolve_database_name "$db_url")"

  if [[ -z "$db_name" ]]; then
    echo "warning: could not infer database name from DATABASE_URL; using DATABASE_NAME='${DATABASE_NAME:-paced_coach}' for compose." >&2
    return 0
  fi

  if [[ ! "$db_name" =~ ^[A-Za-z0-9_]+$ ]]; then
    echo "warning: inferred database name '$db_name' contains unsupported characters; using DATABASE_NAME='${DATABASE_NAME:-paced_coach}' for compose." >&2
    return 0
  fi

  export DATABASE_NAME="$db_name"
  echo "Using compose database name: '${DATABASE_NAME}'."
}

ensure_database_exists() {
  local db_url
  db_url="$(resolve_database_url)"
  local db_name
  db_name="$(resolve_database_name "$db_url")"

  if [[ -z "$db_name" ]]; then
    echo "warning: could not infer database name from DATABASE_URL; skipping pre-create check." >&2
    return 0
  fi

  if [[ ! "$db_name" =~ ^[A-Za-z0-9_]+$ ]]; then
    echo "warning: inferred database name '$db_name' contains unsupported characters; skipping pre-create check." >&2
    return 0
  fi

  if docker compose exec -T db psql -U postgres -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${db_name}'" \
    | grep -q 1; then
    echo "Database '${db_name}' already exists."
    return 0
  fi

  echo "Database '${db_name}' not found; creating it..."
  docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d postgres -c \
    "CREATE DATABASE \"${db_name}\""
}

run_migrations() {
  if [[ -z "$PIXI_BIN" ]]; then
    echo "warning: pixi not found; skipping alembic migrations." >&2
    return 0
  fi

  local db_url
  db_url="$(resolve_database_url)"

  if [[ "$db_url" != *"+asyncpg"* ]]; then
    echo "warning: DATABASE_URL must use +asyncpg for alembic in this repo; got: $db_url" >&2
    echo "warning: skipping migrations (set DATABASE_URL=postgresql+asyncpg://... to enable)" >&2
    return 0
  fi

  echo "Running DB migrations (alembic upgrade head)..."
  # Ensure the async URL is set as well; settings may prefer DATABASE_URL_ASYNC.
  DATABASE_URL="$db_url" DATABASE_URL_ASYNC="$db_url" "$PIXI_BIN" run alembic -c alembic.ini upgrade head
}

compose_project_name() {
  if [[ -n "${COMPOSE_PROJECT_NAME:-}" ]]; then
    printf "%s" "$COMPOSE_PROJECT_NAME"
    return 0
  fi
  basename "$ROOT_DIR"
}

backend_image_exists() {
  local project_name
  project_name="$(compose_project_name)"
  docker image inspect "${project_name}-$1:latest" >/dev/null 2>&1
}

backend_manifest_hash() {
  sha256sum \
    "$ROOT_DIR/pixi.toml" \
    "$ROOT_DIR/pixi.lock" \
    "$ROOT_DIR/Dockerfile" \
    "$ROOT_DIR/docker-compose.yml" \
    | sha256sum \
    | awk '{print $1}'
}

sync_backend_dependencies() {
  local desired_hash
  desired_hash="$(backend_manifest_hash)"

  local should_build="${DEV_ALL_FORCE_BUILD:-0}"
  if [[ "$should_build" != "1" ]] \
    && backend_image_exists api \
    && backend_image_exists worker \
    && backend_image_exists beat; then
    echo "Backend Docker images already exist; skipping rebuild."
    echo "Set DEV_ALL_FORCE_BUILD=1 to rebuild them."
  fi

  if [[ "$should_build" == "1" ]] \
    || ! backend_image_exists api \
    || ! backend_image_exists worker \
    || ! backend_image_exists beat; then
    echo "Building backend Docker images..."
    echo "This can take a few minutes on first run or after Dockerfile changes."
    local buildx_builder="${BUILDX_BUILDER:-}"
    if [[ -z "$buildx_builder" ]] && docker buildx inspect default >/dev/null 2>&1; then
      buildx_builder="default"
    fi

    if [[ -n "$buildx_builder" ]]; then
      echo "Using Docker Buildx builder: $buildx_builder"
    fi

    if [[ -n "$buildx_builder" ]]; then
      if ! BUILDX_BUILDER="$buildx_builder" docker compose build api worker beat; then
        echo "error: backend image build failed." >&2
        echo "error: if Docker reported a missing snapshot parent, restart Docker Desktop or prune Buildx cache with 'docker buildx prune -af' and retry." >&2
        return 1
      fi
    elif ! docker compose build api worker beat; then
      echo "error: backend image build failed." >&2
      echo "error: if Docker reported a missing snapshot parent, restart Docker Desktop or prune Buildx cache with 'docker buildx prune -af' and retry." >&2
      return 1
    fi
  fi

  local current_hash
  current_hash="$(
    docker compose run --rm --no-deps api bash -lc 'cat /app/.pixi/.dev_all_backend_manifest_hash 2>/dev/null || true'
  )"

  if [[ "$current_hash" == "$desired_hash" ]]; then
    echo "Backend Pixi environment already matches current manifests; skipping sync."
    return 0
  fi

  echo "Syncing backend Pixi environment in Docker volume..."
  echo "This usually only runs when backend manifests changed or on first setup."
  docker compose run --rm --no-deps \
    -e DEV_ALL_BACKEND_MANIFEST_HASH="$desired_hash" \
    api \
    bash -lc "/root/.pixi/bin/pixi install --locked && printf '%s' \"\$DEV_ALL_BACKEND_MANIFEST_HASH\" > /app/.pixi/.dev_all_backend_manifest_hash"
}

start_backend() {
  local services=(api worker)
  if [[ "${DEV_ALL_INCLUDE_BEAT:-1}" != "0" ]]; then
    services+=(beat)
  fi

  echo "Starting backend (${services[*]}) via docker compose..."
  docker compose up "${services[@]}" &
  compose_pid=$!
}

wait_for_backend() {
  local base="${API_BASE_URL:-http://localhost:8000}"
  base="${base%/}"
  local url="${base}/ready"
  local attempts="${BACKEND_READY_ATTEMPTS:-60}"
  local sleep_s="${BACKEND_READY_SLEEP_SECONDS:-1}"

  if ! command -v curl >/dev/null 2>&1; then
    echo "Note: curl not found; skipping backend readiness wait." >&2
    return 0
  fi

  echo "Waiting for backend readiness at ${url} ..."
  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "Backend is ready."
      return 0
    fi
    if ! kill -0 "${compose_pid:-0}" >/dev/null 2>&1; then
      echo "error: docker compose process exited while waiting for backend readiness" >&2
      return 1
    fi
    sleep "$sleep_s"
  done

  echo "warning: backend not ready after $((attempts * sleep_s))s; starting web anyway." >&2
  return 0
}

sync_compose_database_name
ensure_infra_up
wait_for_db
ensure_database_exists
run_migrations
sync_backend_dependencies
ensure_web_dependencies
start_backend
wait_for_backend

echo "Starting web (Next.js) via npm..."
cd "$WEB_DIR"
PATH="./node_modules/.bin:$PATH" npm run dev
