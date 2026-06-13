# Now

**Cadence:** update when focus shifts.

## Current Focus

Ship the repository as a clean local-first open-source AI endurance coach:

- One local owner by default.
- Manual profile, competitions, and plan generation work without connected providers.
- Strava and WHOOP are optional OAuth data connectors.
- No public setup dependency on hosted auth, payments, managed deployment, or vendor secrets.
- No tracked local env files, private athlete data, generated personal artifacts, or stale internal marketing tooling.

## Active Workstreams

### 1) Public Repo Cleanliness

- [x] Remove hosted deployment and payment operations from the source tree.
- [x] Remove hosted auth and payment product surfaces.
- [x] Remove internal video, social-story, and example-capture tooling.
- [x] Replace historical migration chains with a single local-first baseline migration.
- [ ] Run final tracked-file scans before publishing.

### 2) Local Happy Path

- [x] `http://localhost:3000` opens the app path.
- [x] Plan generation works from local profile, competitions, and an LLM key.
- [x] Daily sync and weekly recap remain available when connected data exists.
- [x] Strava and WHOOP OAuth remain optional.

### 3) Contributor Readiness

- [x] Keep `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `docs/local-first/**` aligned with local-first setup.
- [x] Keep repo agent guidance focused on current web/API/worker/AI workflows.
- [ ] Run full backend and frontend verification after cleanup.

## Not In Scope Now

- Public internet hosting without adding real auth and hardening.
- Multi-user accounts.
- Managed cloud deployment.
- Legacy provider integrations as default OSS connectors.
- Managed commercial product surfaces.
