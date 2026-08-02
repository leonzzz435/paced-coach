# LEGAL TODO

Status date: 2026-07-13
Scope: `web/app` public legal pages (`/impressum`, `/privacy`, `/terms`, `/support`, `/delete`)

## Local-First OSS Review

- [x] Re-review Privacy, Terms, Support, and Delete pages for the local-first OSS posture.
- [ ] Re-review all legal pages once more before publishing the open-source repository.
- [ ] Decide whether public legal pages should remain in the OSS web app or move into documentation.

## Business Facts

- [x] Sync provider name, business designation, and address with the confirmed Gewerbeanmeldung.
- [ ] Decide whether to add a direct legal contact email alias in addition to `support@paced.coach`.
- [ ] Confirm if a phone number is required for the intended legal/support posture.
- [ ] Add the VAT ID or W-IdNr. once it has been issued and is required to be shown.

## Privacy Hardening

- [x] Document the local-first processor posture: local infrastructure, configured AI APIs, no hidden telemetry, and optional LangSmith.
- [x] Review the current Strava and WHOOP API terms and remove both connectors from the v2.2.0 public runtime and launch claims.
- [ ] Reassess a future connector only after written provider permission or a clearly compatible API contract is documented.
- [x] Add cookie/tracking wording that reflects the current essential-technology posture.
- [ ] Verify exact hosting and storage regions before publishing any region-specific privacy claim.
- [ ] Verify backup retention wording against the current local setup.
- [ ] Confirm legal basis and wording for health-related data processing with counsel.

## Data Rights Operations

- [ ] Define a GDPR request runbook: identity check, deadlines, evidence log, and response templates.
- [ ] Compare the deletion checklist against the local-first setup: database, queues, generated artifacts, and backups.
- [ ] Run one local privacy reset against disposable data and confirm `/delete` matches observed behavior.

## External Review

- [ ] Run one legal review by a Germany-based lawyer before broad public distribution.
- [ ] Review the `v2.2.0` release candidate's `/impressum`, `/privacy`, `/terms`, `/support`, and `/delete` pages against the local-first distribution model.
- [ ] Apply counsel-required corrections, then rerun the public release audit and exact-commit CI before publication.
- [ ] Recheck all legal pages after each major product change, especially new data sources or managed hosting.
