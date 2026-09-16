# LEGAL TODO

Status date: 2026-09-16
Scope: `web/app` public legal pages (`/impressum`, `/privacy`, `/terms`, `/support`, `/delete`)

## Local-First OSS Review

- [x] Re-review Privacy, Terms, Support, and Delete pages for the local-first OSS posture.
- [x] Re-review all five pages for factual consistency with the self-hosted build; remove retired hosted-sign-in and training-connector descriptions. This is an engineering copy review, not legal clearance.
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
- [x] Verify backup retention wording against the current local setup: backups remain operator-controlled; no automatic backup deletion or fixed retention period is promised.
- [ ] Confirm legal basis and wording for health-related data processing with counsel.

## Data Rights Operations

- [ ] Define a GDPR request runbook: identity check, deadlines, evidence log, and response templates.
- [ ] Compare the deletion checklist against the local-first setup: database, queues, generated artifacts, and backups.
- [x] Run local privacy reset against a copy of disposable synthetic data: default UI/API guards and cancellation preserved the plan; confirmation removed populated application/checkpoint rows and preserved the technical owner. `/delete` matched the observed result. This does not certify external-provider, backup or filesystem deletion.

## External Review

The maintainer confirmed on 2026-09-16 that external review has not yet occurred.
The distribution in scope is self-hosted open-source code; a managed service or
separate website deployment is not planned by this release. Review the legal
pages included in that application against this distribution model. Do not
infer legal clearance from the already published v2.2.0 tag.

- [ ] Run one legal review by a Germany-based lawyer before broad public distribution.
- [ ] Review the `v2.3.0` release candidate's `/impressum`, `/privacy`, `/terms`, `/support`, and `/delete` pages against the local-first distribution model.
- [ ] Apply counsel-required corrections, then rerun the public release audit and exact-commit CI before publication.
- [ ] Recheck all legal pages after each major product change, especially new data sources or managed hosting.
