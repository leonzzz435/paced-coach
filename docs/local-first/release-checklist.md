# Public Release Checklist

Use this checklist for each public release. It is a release gate, not a general development checklist.

## Safety Boundary

- [ ] Work from a dedicated release branch and a fixed candidate commit.
- [x] Do not read, copy, reset, migrate, or delete the maintainer's local athlete database.
- [x] Keep `.env`, `web/app/.env.local`, database volumes, logs, exports, and model traces out of release evidence.
- [x] Keep the no-login app bound to loopback.

## Repository Audit

- [ ] The working tree is clean.
- [ ] `scripts/release_audit.sh` passes using pinned Gitleaks for the clean candidate commit.
- [x] The current working-tree candidate export passes the pinned Gitleaks content scan.
- [x] Any scanner report under `.tmp/release-audit/` is fully redacted and remains untracked.
- [x] Screenshots and synthetic fixtures have been inspected visually for private athlete data.
- [ ] Any suspected credential has been rotated before further investigation.
- [x] No history rewrite or destructive cleanup was performed without explicit maintainer approval.

## Automated Verification

- [x] Backend Ruff checks pass.
- [x] Backend MyPy checks pass.
- [x] Python tests pass.
- [x] Frontend lint, type-check, tests, and production build pass.
- [x] Version-manifest and version-governance checks pass.
- [ ] GitHub CI passes for the exact candidate commit.

## Clean-Install Acceptance

- [x] A fresh Ubuntu/Linux environment follows only the public setup documentation.
- [x] The smoke stack uses a unique Compose project and disposable volumes.
- [x] Only one supported LLM key is configured; optional observability remains unset.
- [x] A synthetic profile and A-race produce a season roadmap and 28-day plan.
- [x] Coach chat answers a plan-specific question without provider-derived claims.
- [x] Normal restart preserves the disposable synthetic plan.
- [x] Cleanup changes only the disposable Compose namespace.
- [x] Non-sensitive results are recorded for the exact candidate commit.

## Legal And Publication Gate

- [ ] External legal review is complete and required corrections are applied.
- [x] `LEGAL_TODO.md` reflects the actual remaining work.
- [x] Release notes state the localhost, AI, medical, privacy, and provider-free boundaries.
- [ ] The GitHub release exists as a reviewed draft tied to the audited commit.
- [ ] The maintainer gives an explicit final Go before publishing the immutable release.

Any unchecked required item is a No-Go. After publication, preserve the tag. Correct defects with a newly audited patch release instead of moving or reusing the published tag.
