from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import check_version_governance


def _write_release_files(root: Path, *, pixi_version: str) -> None:
    (root / "web/app").mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nversion = "2.2.0"\n', encoding="utf-8")
    (root / "pixi.toml").write_text(f'[project]\nversion = "{pixi_version}"\n', encoding="utf-8")
    (root / "web/app/package.json").write_text(json.dumps({"version": "2.2.0"}), encoding="utf-8")


def test_release_consistency_includes_pixi_manifest(monkeypatch, tmp_path: Path):
    _write_release_files(tmp_path, pixi_version="2.2.0")
    monkeypatch.setattr(check_version_governance, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        check_version_governance,
        "get_version_manifest",
        lambda: SimpleNamespace(release=SimpleNamespace(version="2.2.0")),
    )

    assert check_version_governance._check_release_consistency() == []


def test_release_consistency_rejects_pixi_version_drift(monkeypatch, tmp_path: Path):
    _write_release_files(tmp_path, pixi_version="2.1.0")
    monkeypatch.setattr(check_version_governance, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        check_version_governance,
        "get_version_manifest",
        lambda: SimpleNamespace(release=SimpleNamespace(version="2.2.0")),
    )

    assert check_version_governance._check_release_consistency() == [
        "Release version mismatch: manifest=2.2.0, pixi.toml=2.1.0"
    ]
