#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -n "${PIXI_BIN:-}" ] && [ -x "${PIXI_BIN}" ]; then
  RESOLVED_PIXI_BIN="${PIXI_BIN}"
elif [ -x "${PROJECT_ROOT}/.pixi/bin/pixi" ]; then
  RESOLVED_PIXI_BIN="${PROJECT_ROOT}/.pixi/bin/pixi"
else
  RESOLVED_PIXI_BIN="$(command -v pixi 2>/dev/null || true)"
fi

if [ -z "${RESOLVED_PIXI_BIN:-}" ] || [ ! -x "${RESOLVED_PIXI_BIN}" ]; then
  echo "Pixi binary not found. Checked \$PIXI_BIN, ${PROJECT_ROOT}/.pixi/bin/pixi, and PATH." >&2
  exit 1
fi

if [ -z "${GIT_SHA:-}" ] && command -v git >/dev/null 2>&1 && [ -d "${PROJECT_ROOT}/.git" ]; then
  export GIT_SHA="$(git -C "${PROJECT_ROOT}" rev-parse HEAD)"
fi

exec "$RESOLVED_PIXI_BIN" run uvicorn api.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}"
