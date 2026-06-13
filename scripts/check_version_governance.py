#!/usr/bin/env python3
from __future__ import annotations

import json
import tomllib
from pathlib import Path

from core.version_manifest import get_version_manifest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _check_renderer_coverage() -> list[str]:
    manifest = get_version_manifest()
    errors: list[str] = []
    supported_versions = manifest.compatibility.ui_schema.supported_versions

    for version in supported_versions:
        analysis_renderer = REPO_ROOT / f"web/app/src/components/plan-viewer/versioned/analysis-view-v{version}.tsx"
        season_renderer = REPO_ROOT / f"web/app/src/components/plan-viewer/versioned/season-plan-view-v{version}.tsx"
        weekly_renderer = REPO_ROOT / f"web/app/src/components/plan-viewer/versioned/weekly-plan-view-v{version}.tsx"
        fixture_dir = REPO_ROOT / f"web/app/src/lib/demo/fixtures/v{version}"

        if not analysis_renderer.exists():
            errors.append(f"Missing renderer file: {analysis_renderer}")
        if not season_renderer.exists():
            errors.append(f"Missing renderer file: {season_renderer}")
        if not weekly_renderer.exists():
            errors.append(f"Missing renderer file: {weekly_renderer}")
        if not fixture_dir.exists():
            errors.append(f"Missing fixture directory: {fixture_dir}")

    return errors


def _check_release_consistency() -> list[str]:
    manifest = get_version_manifest()
    errors: list[str] = []
    release_version = manifest.release.version

    pyproject_data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pyproject_version = pyproject_data.get("project", {}).get("version")
    if pyproject_version != release_version:
        errors.append(f"Release version mismatch: manifest={release_version}, pyproject.toml={pyproject_version}")

    package_json_data = json.loads((REPO_ROOT / "web/app/package.json").read_text(encoding="utf-8"))
    web_version = package_json_data.get("version")
    if web_version != release_version:
        errors.append(f"Release version mismatch: manifest={release_version}, web/app/package.json={web_version}")

    return errors


def main() -> int:
    errors = _check_renderer_coverage()
    errors.extend(_check_release_consistency())

    if errors:
        print("[ERROR] Version governance checks failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("[OK] Version governance checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
