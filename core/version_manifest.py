from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


def _validate_semver(value: str) -> str:
    if not _SEMVER_RE.match(value):
        raise ValueError(f"Invalid semver value: {value}")
    return value


class ReleaseVersion(BaseModel):
    version: str

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_semver(value)


class UiSchemaComponent(BaseModel):
    version: str
    current_schema_version: int = Field(ge=1)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_semver(value)


class DbSchemaComponent(BaseModel):
    version: str
    alembic_head: str = Field(min_length=1)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_semver(value)


class Components(BaseModel):
    ui_schema: UiSchemaComponent
    db_schema: DbSchemaComponent


class UiSchemaCompatibility(BaseModel):
    supported_versions: list[int]
    supported_versions_by_kind: dict[Literal["analysis", "season", "weekly"], list[int]]
    default_version: int = Field(ge=1)

    @field_validator("supported_versions")
    @classmethod
    def validate_supported_versions(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("supported_versions must not be empty")
        if any(v <= 0 for v in value):
            raise ValueError("supported_versions must be positive integers")
        return sorted(set(value))

    @field_validator("default_version")
    @classmethod
    def validate_default_version(cls, value: int, info) -> int:
        supported_versions = info.data.get("supported_versions", [])
        if supported_versions and value not in supported_versions:
            raise ValueError("default_version must be included in supported_versions")
        return value

    @model_validator(mode="after")
    def validate_kind_support(self) -> UiSchemaCompatibility:
        expected_kinds = {"analysis", "season", "weekly"}
        if set(self.supported_versions_by_kind) != expected_kinds:
            raise ValueError("supported_versions_by_kind must define analysis, season, and weekly")
        globally_supported = set(self.supported_versions)
        for kind, versions in self.supported_versions_by_kind.items():
            if not versions or any(version not in globally_supported for version in versions):
                raise ValueError(f"{kind} schema versions must be a non-empty subset of supported_versions")
        return self


class Compatibility(BaseModel):
    ui_schema: UiSchemaCompatibility


class VersionManifest(BaseModel):
    manifest_version: int = Field(ge=1)
    release: ReleaseVersion
    components: Components
    compatibility: Compatibility


_MANIFEST_ENV_VAR = "VERSION_MANIFEST_PATH"
_DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "config" / "version_manifest.yaml"


def get_manifest_path() -> Path:
    raw_path = os.getenv(_MANIFEST_ENV_VAR, "").strip()
    return Path(raw_path) if raw_path else _DEFAULT_MANIFEST_PATH


@lru_cache(maxsize=1)
def get_version_manifest() -> VersionManifest:
    manifest_path = get_manifest_path()
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid version manifest payload at {manifest_path}")
    return VersionManifest.model_validate(payload)


def reload_version_manifest() -> VersionManifest:
    get_version_manifest.cache_clear()
    return get_version_manifest()


def get_release_version() -> str:
    return get_version_manifest().release.version


def get_supported_schema_versions() -> list[int]:
    return get_version_manifest().compatibility.ui_schema.supported_versions


def get_default_schema_version() -> int:
    return get_version_manifest().compatibility.ui_schema.default_version


def get_supported_schema_versions_for_kind(kind: Literal["analysis", "season", "weekly"]) -> list[int]:
    return get_version_manifest().compatibility.ui_schema.supported_versions_by_kind[kind]
