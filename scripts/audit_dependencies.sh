#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
audit_dir="$repo_root/.tmp/dependency-audit"
mkdir -p "$audit_dir"

# Keep the scanner outside the application dependency environment.
pixi run python -m venv "$audit_dir/venv"
"$audit_dir/venv/bin/python" -m pip install --quiet 'pip-audit==2.10.1'
pixi run python -m pip list --format=freeze --exclude paced-coach > "$audit_dir/python-packages.txt"
"$audit_dir/venv/bin/pip-audit" --no-deps --disable-pip \
  -r "$audit_dir/python-packages.txt" --format=json --output="$audit_dir/python.json"
npm --prefix web/app audit --json > "$audit_dir/npm.json"
echo "Dependency advisories: passed for this installed Python environment and npm lockfile. Reports: .tmp/dependency-audit/"
