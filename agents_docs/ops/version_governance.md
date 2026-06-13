# Version Governance

How versioning is managed across `paced.coach`.

## Source of Truth

- Canonical manifest: `config/version_manifest.yaml`
- Generated web artifact: `web/app/src/lib/generated/version-manifest.ts`
- Python loader: `core/version_manifest.py`

## What the Manifest Tracks

- `release` — cross-product release version (synced with `pyproject.toml` + `package.json`)
- `ui_schema` — current schema version + supported versions for renderer dispatch
- `db_schema` — alembic head for migration sanity checks

## Schema Compatibility

- Supported schema versions are defined in manifest compatibility section.
- Every supported version must have:
  - Renderer files in `web/app/src/components/plan-viewer/versioned/`
  - Fixture directory in `web/app/src/lib/demo/fixtures/`
- Unknown schema versions show an explicit unsupported UI state.
- Pre-versioning plans (null `schema_version`) render as v2 for backwards compatibility.

## Canonical Plan Revision

- `version` is the canonical artifact revision.
- DB row version and payload `version` must always match.
- Worker and coach flows are responsible for synchronized increments.

## CI Gates

- Manifest validates via `core/version_manifest.py` Pydantic models.
- Drift check: generated TS artifact must match manifest (`pixi run check-version-manifest`).
- Renderer/fixture coverage check for all supported schema versions (`pixi run check-version-governance`).
- Release consistency: manifest release version must match `pyproject.toml` and `web/app/package.json`.

## Commands

- `pixi run sync-version-manifest` — regenerate web artifact from YAML
- `pixi run check-version-manifest` — verify artifact is up to date
- `pixi run check-version-governance` — renderer coverage + release consistency

## Release Checklist

- [ ] `config/version_manifest.yaml` updated if schema or release version changed
- [ ] `pixi run check-version-manifest` passes
- [ ] `pixi run check-version-governance` passes
- [ ] `db_schema.alembic_head` matches latest migration revision
