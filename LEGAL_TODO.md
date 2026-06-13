# LEGAL TODO

Status date: 2026-06-13
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

- [x] Document the local-first processor posture: local infrastructure, AI APIs, Strava, WHOOP, no hidden telemetry, and optional LangSmith.
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
- [ ] Recheck all legal pages after each major product change, especially new data sources or managed hosting.
