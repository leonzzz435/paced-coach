from pydantic import ValidationError

from core.version_manifest import (
    VersionManifest,
    get_default_schema_version,
    get_supported_schema_versions,
    get_supported_schema_versions_for_kind,
    get_version_manifest,
)


def test_version_manifest_loads():
    manifest = get_version_manifest()
    assert manifest.release.version
    assert manifest.components.db_schema.alembic_head
    assert get_default_schema_version() in get_supported_schema_versions()
    assert get_supported_schema_versions_for_kind("analysis") == [1]
    assert get_supported_schema_versions_for_kind("season") == [1, 3]


def test_version_manifest_rejects_invalid_semver():
    payload = get_version_manifest().model_dump(mode="json")
    payload["release"]["version"] = "not-semver"
    try:
        VersionManifest.model_validate(payload)
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for invalid semver")
