# Public Release Checklist

Use this checklist for each public release. It is a release gate, not a general development checklist.

## Safety Boundary

- [ ] Work from a dedicated release branch and a fixed candidate commit.
- [ ] Do not read, copy, reset, migrate, or delete the maintainer's local athlete database.
- [ ] Keep `.env`, `web/app/.env.local`, database volumes, logs, exports, and model traces out of release evidence.
- [ ] Keep the no-login app bound to loopback.

## Repository Audit

- [ ] The working tree is clean.
- [ ] `scripts/release_audit.sh` passes using pinned Gitleaks for the clean candidate commit, including local and remote-tracking refs.
- [ ] The current working-tree candidate export passes the pinned Gitleaks content scan.
- [ ] Any scanner report under `.tmp/release-audit/` is fully redacted and remains untracked.
- [ ] README screenshots are recaptured from sanitized schema-v3 fixtures and inspected visually for private athlete data. The July pre-Head-Coach assets are not candidate evidence.
- [ ] Any suspected credential has been rotated before further investigation.
- [ ] No history rewrite or destructive cleanup was performed without explicit maintainer approval.

## Automated Verification

- [ ] Backend Ruff checks pass.
- [ ] Backend MyPy checks pass.
- [ ] Python tests pass.
- [ ] Frontend lint, type-check, tests, and production build pass.
- [ ] Version-manifest and version-governance checks pass.
- [ ] GitHub CI passes for the exact candidate commit.

## Clean-Install Acceptance

- [ ] A fresh Ubuntu/Linux environment follows only the public setup documentation.
- [ ] The smoke stack uses a unique Compose project and disposable volumes.
- [ ] Only `OPENAI_API_KEY` is configured; optional observability remains unset.
- [ ] A synthetic profile and A-race produce schema-v3 Season Strategy and 28-day Execution artifacts.
- [ ] Coach chat answers a plan-specific question without provider-derived claims.
- [ ] Normal restart preserves the disposable synthetic plan and does not duplicate canonical artifacts.
- [ ] Cleanup changes only the disposable Compose namespace.
- [ ] Non-sensitive results are recorded for the exact candidate commit.

## Legal And Publication Gate

- [ ] External legal review is complete and required corrections are applied.
- [ ] `LEGAL_TODO.md` reflects the actual remaining work.
- [ ] Release notes state the localhost, AI, medical, privacy, and provider-free boundaries.
- [ ] The GitHub release exists as a reviewed draft tied to the audited commit.
- [ ] The maintainer gives an explicit final Go before publishing the immutable release.

Any unchecked required item is a No-Go. After publication, preserve the tag. Correct defects with a newly audited patch release instead of moving or reusing the published tag.
