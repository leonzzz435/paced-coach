#!/usr/bin/env bash
set -uo pipefail

GITLEAKS_VERSION="v8.30.1"
GITLEAKS_IMAGE="zricethezav/gitleaks:${GITLEAKS_VERSION}"
MAX_TRACKED_BYTES="${RELEASE_AUDIT_MAX_TRACKED_BYTES:-10485760}"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repo_root" ]]; then
  echo "[ERROR] release audit must run inside a Git repository"
  exit 1
fi

cd "$repo_root"
report_dir="${RELEASE_AUDIT_REPORT_DIR:-$repo_root/.tmp/release-audit}"
tracked_export="$report_dir/tracked"
history_repo="$report_dir/history.git"
gitleaks_config="$repo_root/.gitleaks.toml"
error_count=0

ok() {
  echo "[OK] $1"
}

info() {
  echo "[INFO] $1"
}

error() {
  echo "[ERROR] $1"
  error_count=$((error_count + 1))
}

prepare_report_directory() {
  mkdir -p "$report_dir"
  rm -rf "$tracked_export" "$history_repo"
  rm -f "$report_dir/history.json" "$report_dir/history.scanner.log"
  rm -f "$report_dir/tracked.json" "$report_dir/tracked.scanner.log"
  mkdir -p "$tracked_export"
}

check_working_tree() {
  local status
  status="$(git status --porcelain --untracked-files=all)"
  if [[ -n "$status" ]]; then
    error "working tree is not clean"
    printf '%s\n' "$status" | sed 's/^/  /'
    return
  fi
  ok "working tree is clean"
}

report_ignored_local_paths() {
  local candidates=(
    ".env"
    "web/app/.env.local"
    "data"
    "logs"
    "celerybeat-schedule"
  )
  local present=()
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -e "$candidate" ]] && git check-ignore -q -- "$candidate"; then
      present+=("$candidate")
    fi
  done

  if [[ ${#present[@]} -eq 0 ]]; then
    ok "no ignored local secret/config paths detected"
    return
  fi

  local joined
  joined="$(IFS=', '; echo "${present[*]}")"
  info "local secret/config paths present (contents not inspected): $joined"
}

is_forbidden_tracked_path() {
  local path="$1"
  local basename="${path##*/}"

  case "$path" in
    .env.example|web/app/.env.example)
      return 1
      ;;
    data/*|logs/*|tmp/*|.tmp/*)
      return 0
      ;;
  esac

  case "$basename" in
    .env|.env.*|*.db|*.dump|*.ipynb|*.log|*.sqlite|*.sqlite3)
      return 0
      ;;
  esac

  return 1
}

check_tracked_paths() {
  local path
  local path_errors=0
  while IFS= read -r path; do
    if is_forbidden_tracked_path "$path"; then
      error "forbidden tracked release path: $path"
      path_errors=$((path_errors + 1))
      continue
    fi

    if [[ -f "$path" ]]; then
      local size
      size="$(wc -c < "$path")"
      if ((size > MAX_TRACKED_BYTES)); then
        error "oversized tracked release artifact: $path (${size} bytes)"
        path_errors=$((path_errors + 1))
      fi
    fi
  done < <(git ls-files)

  if [[ $path_errors -eq 0 ]]; then
    ok "tracked paths contain no forbidden private/generated artifacts"
  fi
}

check_workflow_secret_references() {
  local matches
  matches="$(git grep -n -E 'secrets\.[A-Za-z0-9_]+' -- '.github/workflows/*.yml' '.github/workflows/*.yaml' 2>/dev/null || true)"
  if [[ -n "$matches" ]]; then
    error "workflow secret references require explicit release review"
    printf '%s\n' "$matches" | sed -E 's/(secrets\.)[A-Za-z0-9_]+/\1[redacted-name]/g' | sed 's/^/  /'
    return
  fi
  ok "workflows contain no repository secret references"
}

check_network_bindings() {
  if [[ ! -f docker-compose.yml ]]; then
    ok "no Docker Compose port surface present"
    return
  fi

  local unsafe_bindings
  unsafe_bindings="$(
    grep -n -E "^[[:space:]]*-[[:space:]]*[\"']?((0\\.0\\.0\\.0|\\[?::\\]?):)?[0-9]+:[0-9]+" docker-compose.yml || true
  )"
  if [[ -n "$unsafe_bindings" ]]; then
    error "Docker Compose contains a non-loopback host port binding"
    printf '%s\n' "$unsafe_bindings" | sed 's/^/  /'
    return
  fi
  ok "Docker Compose host ports remain explicitly loopback-bound"
}

check_hosted_ops_files() {
  local matches
  matches="$(
    git ls-files | grep -E '(^|/)(fly\.toml|vercel\.json|netlify\.toml|render\.yaml|serverless\.yml)$|(^|/)(terraform|k8s|kubernetes)/' || true
  )"
  if [[ -n "$matches" ]]; then
    error "hosted deployment artifacts require explicit release review"
    printf '%s\n' "$matches" | sed 's/^/  /'
    return
  fi
  ok "no hosted deployment artifacts detected"
}

export_tracked_files() {
  if ! git archive --format=tar HEAD | tar -xf - -C "$tracked_export"; then
    error "failed to create isolated tracked-file export"
    return 1
  fi
  ok "isolated tracked-file export created"
}

export_release_history() {
  if ! git init --bare -q "$history_repo"; then
    error "failed to initialize isolated history repository"
    return 1
  fi

  local ref
  local ref_count=0
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    if ! git --git-dir="$history_repo" fetch -q "$repo_root" "+$ref:$ref"; then
      error "failed to copy release history ref: $ref"
      return 1
    fi
    ref_count=$((ref_count + 1))
  done < <(git for-each-ref --format='%(refname)' refs/heads refs/tags)

  if [[ $ref_count -eq 0 ]]; then
    error "no release history refs found"
    return 1
  fi
  ok "isolated release history created from $ref_count branch/tag refs"
}

run_gitleaks_direct() {
  local mode="$1"
  local target="$2"
  local report_path="$3"
  local scanner_log="$4"
  "$RELEASE_AUDIT_GITLEAKS_BIN" "$mode" \
    --config "$gitleaks_config" \
    --redact=100 \
    --report-format json \
    --report-path "$report_path" \
    "$target" >"$scanner_log" 2>&1
}

run_gitleaks_docker() {
  local mode="$1"
  local target="$2"
  local report_name="$3"
  local scanner_log="$4"
  docker run --rm --network none \
    --mount "type=bind,src=$target,dst=/scan,readonly" \
    --mount "type=bind,src=$gitleaks_config,dst=/config/.gitleaks.toml,readonly" \
    --mount "type=bind,src=$report_dir,dst=/reports" \
    "$GITLEAKS_IMAGE" "$mode" \
    --config /config/.gitleaks.toml \
    --redact=100 \
    --report-format json \
    --report-path "/reports/$report_name" \
    /scan >"$scanner_log" 2>&1
}

run_secret_scan() {
  local label="$1"
  local mode="$2"
  local target="$3"
  local report_name="$4"
  local report_path="$report_dir/$report_name"
  local scanner_log="${report_path%.json}.scanner.log"
  local status=0

  if [[ -n "${RELEASE_AUDIT_GITLEAKS_BIN:-}" ]]; then
    run_gitleaks_direct "$mode" "$target" "$report_path" "$scanner_log" || status=$?
  else
    if ! command -v docker >/dev/null 2>&1; then
      error "$label secret scan unavailable: Docker is required"
      return
    fi
    run_gitleaks_docker "$mode" "$target" "$report_name" "$scanner_log" || status=$?
  fi

  if [[ $status -ne 0 ]]; then
    error "$label secret scan failed; inspect the fully redacted report under .tmp/release-audit"
    return
  fi
  ok "$label secret scan passed"
}

prepare_report_directory
check_working_tree
report_ignored_local_paths
check_tracked_paths
check_workflow_secret_references
check_network_bindings
check_hosted_ops_files

if export_tracked_files; then
  run_secret_scan "tracked-file" "dir" "$tracked_export" "tracked.json"
fi

if export_release_history; then
  run_secret_scan "history" "git" "$history_repo" "history.json"
fi

if [[ $error_count -ne 0 ]]; then
  echo "[ERROR] public-release audit failed with $error_count issue(s)"
  exit 1
fi

echo "[OK] public-release audit passed"
