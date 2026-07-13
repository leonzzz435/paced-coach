from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_AUDIT_SCRIPT = REPO_ROOT / "scripts/release_audit.sh"


def _run(command: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=check, capture_output=True, text=True)


def _initialize_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _run(["git", "init", "-b", "main"], cwd=repository)
    _run(["git", "config", "user.email", "release-audit@example.test"], cwd=repository)
    _run(["git", "config", "user.name", "Release Audit Test"], cwd=repository)
    (repository / ".gitignore").write_text(".env\n.tmp/\n", encoding="utf-8")
    (repository / ".gitleaks.toml").write_text('title = "test"\n', encoding="utf-8")
    (repository / "README.md").write_text("Synthetic release fixture.\n", encoding="utf-8")
    (repository / "scripts").mkdir()
    shutil.copy2(RELEASE_AUDIT_SCRIPT, repository / "scripts/release_audit.sh")
    _run(["git", "add", "."], cwd=repository)
    _run(["git", "commit", "-m", "initial"], cwd=repository)
    return repository


def _write_fake_gitleaks(tmp_path: Path) -> Path:
    fake_gitleaks = tmp_path / "fake-gitleaks"
    fake_gitleaks.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
report_path=""
target=""
mode=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --report-path)
      report_path="$2"
      shift 2
      ;;
    --config|--report-format|--log-opts)
      shift 2
      ;;
    --redact=*)
      shift
      ;;
    git|dir)
      mode="$1"
      shift
      ;;
    *)
      target="$1"
      shift
      ;;
  esac
done
mkdir -p "$(dirname "$report_path")"
printf '[]\n' > "$report_path"
if [[ -f "${FAKE_GITLEAKS_FAIL_MARKER:-}" ]]; then
  printf '[{"RuleID":"synthetic","Secret":"%s"}]\n' "${FAKE_SECRET_VALUE:-hidden}" > "$report_path"
  exit 1
fi
if [[ -n "${FORBIDDEN_CONTENT:-}" ]] && grep -R -F -q -- "$FORBIDDEN_CONTENT" "$target" 2>/dev/null; then
  exit 9
fi
if [[ "$mode" == "git" && -n "${HISTORY_SECRET_MARKER:-}" ]]; then
  history="$(git --git-dir="$target" log -p --all)"
  if grep -F -q -- "$HISTORY_SECRET_MARKER" <<< "$history"; then
    printf '[{"RuleID":"synthetic-history","Secret":"redacted"}]\n' > "$report_path"
    exit 1
  fi
fi
""",
        encoding="utf-8",
    )
    fake_gitleaks.chmod(0o755)
    return fake_gitleaks


def _audit(repository: Path, fake_gitleaks: Path, **extra_env: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(extra_env)
    env["RELEASE_AUDIT_GITLEAKS_BIN"] = str(fake_gitleaks)
    return subprocess.run(
        [str(repository / "scripts/release_audit.sh")],
        cwd=repository,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_release_audit_ignores_local_secret_contents_and_preserves_repository(tmp_path: Path):
    repository = _initialize_repository(tmp_path)
    fake_gitleaks = _write_fake_gitleaks(tmp_path)
    secret_value = "local-secret-must-never-be-scanned-or-printed"
    (repository / ".env").write_text(f"OPENAI_API_KEY={secret_value}\n", encoding="utf-8")
    before_head = _run(["git", "rev-parse", "HEAD"], cwd=repository).stdout
    before_refs = _run(["git", "show-ref"], cwd=repository).stdout

    result = _audit(repository, fake_gitleaks, FORBIDDEN_CONTENT=secret_value)

    assert result.returncode == 0, result.stdout + result.stderr
    assert secret_value not in result.stdout
    assert secret_value not in result.stderr
    assert "local secret/config paths present (contents not inspected): .env" in result.stdout
    assert _run(["git", "rev-parse", "HEAD"], cwd=repository).stdout == before_head
    assert _run(["git", "show-ref"], cwd=repository).stdout == before_refs
    assert _run(["git", "status", "--short"], cwd=repository).stdout == ""


def test_release_audit_redacts_scanner_failure_output(tmp_path: Path):
    repository = _initialize_repository(tmp_path)
    fake_gitleaks = _write_fake_gitleaks(tmp_path)
    fail_marker = tmp_path / "fail"
    fail_marker.touch()
    secret_value = "synthetic-secret-that-must-not-reach-output"

    result = _audit(
        repository,
        fake_gitleaks,
        FAKE_GITLEAKS_FAIL_MARKER=str(fail_marker),
        FAKE_SECRET_VALUE=secret_value,
    )

    assert result.returncode != 0
    assert secret_value not in result.stdout
    assert secret_value not in result.stderr
    assert "secret scan failed" in result.stdout
    reports = list((repository / ".tmp" / "release-audit").glob("*.json"))
    assert reports
    assert any(secret_value in report.read_text(encoding="utf-8") for report in reports)


def test_release_audit_scans_secret_reachable_only_from_another_branch(tmp_path: Path):
    repository = _initialize_repository(tmp_path)
    fake_gitleaks = _write_fake_gitleaks(tmp_path)
    secret_marker = "historical-secret-on-release-branch"
    _run(["git", "switch", "-c", "historical-secret"], cwd=repository)
    (repository / "legacy.txt").write_text(f"token={secret_marker}\n", encoding="utf-8")
    _run(["git", "add", "legacy.txt"], cwd=repository)
    _run(["git", "commit", "-m", "add historical fixture"], cwd=repository)
    _run(["git", "switch", "main"], cwd=repository)

    result = _audit(repository, fake_gitleaks, HISTORY_SECRET_MARKER=secret_marker)

    assert result.returncode != 0
    assert secret_marker not in result.stdout
    assert secret_marker not in result.stderr
    assert "history secret scan failed" in result.stdout


@pytest.mark.parametrize(
    "tracked_path",
    [
        ".env.production",
        "data/storage/athlete.json",
        "backup/database.dump",
        "logs/coach.log",
    ],
)
def test_release_audit_rejects_tracked_private_or_generated_paths(tmp_path: Path, tracked_path: str):
    repository = _initialize_repository(tmp_path)
    fake_gitleaks = _write_fake_gitleaks(tmp_path)
    path = repository / tracked_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic fixture\n", encoding="utf-8")
    _run(["git", "add", "-f", tracked_path], cwd=repository)
    _run(["git", "commit", "-m", "add forbidden artifact"], cwd=repository)

    result = _audit(repository, fake_gitleaks)

    assert result.returncode != 0
    assert tracked_path in result.stdout
    assert "forbidden tracked release path" in result.stdout


def test_release_audit_rejects_dirty_release_candidate(tmp_path: Path):
    repository = _initialize_repository(tmp_path)
    fake_gitleaks = _write_fake_gitleaks(tmp_path)
    (repository / "README.md").write_text("dirty\n", encoding="utf-8")

    result = _audit(repository, fake_gitleaks)

    assert result.returncode != 0
    assert "working tree is not clean" in result.stdout
    assert "README.md" in result.stdout
