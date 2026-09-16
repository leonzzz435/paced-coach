# September release readiness

Status: in progress. Started 2026-09-16 from public `main` at
`2664b5e333670cc33f7a3e9cdd10b27560fbe529`.

## Outcome

Prepare a reproducible, audited local-first release with supported GPT-6 Astra
configuration, exercised coaching flows, contributor documentation, and synthetic
demo assets. The published v2.2.0 tag remains immutable. New evidence must identify
the candidate commit and distinguish live model runs from deterministic tests.

Distribution is the complete open-source application: each user runs their own
frontend, API, worker, PostgreSQL and Redis, with their own OpenAI API key. A
separate marketing website or managed hosting service is outside this release.
Vercel, Clerk and Stripe are not setup or release prerequisites.

## Work packages

- [x] Resolve current dependency advisories and verify both dependency trees.
- [x] Audit tracked content, reachable history, workflows, public fixtures, and assets.
- [x] Add opt-in Astra support through the central model selector; preserve existing
  cost-effective defaults and semantic reasoning/tool profiles.
- [x] Record a bounded synthetic GPT-5.5/Astra comparison and a live Astra
  initial-planning and ongoing-coaching lifecycle, without benchmark claims.
- [x] Evaluate the Agents API against current ownership, resume, privacy, and
  mutation contracts; document the decision before changing runtime architecture.
- [x] Run backend and frontend checks, PostgreSQL durability tests, and CI.
- [x] Add reproducible browser coverage for demo and first-run behavior.
- [x] Exercise a live synthetic coaching lifecycle and disposable restart recovery.
- [x] Finish the fresh-install repeat after fixing the profile loading race.
- [x] Recapture and visually inspect screenshots; prepare a synthetic demo recording.
- [x] Align README, release evidence, contributor entry points, and product claims.
- [ ] Prepare a reviewed GitHub release draft for the audited candidate.

## Boundaries and external follow-ups

- Preserve the maintainer's original checkout, credentials, and athlete database.
- Use an isolated checkout and uniquely named disposable services bound to loopback.
- Keep credentials, raw traces, generated evidence, and unpublished launch drafts
  in ignored local storage. Publish only deliberately reviewed synthetic assets.
- Maintainer clarified on 2026-09-16 that distribution means self-hosted source
  code. No website deployment or hosting-account access is needed for this work.
- External legal review is still recorded as outstanding in `LEGAL_TODO.md`;
  completion cannot be inferred from the existing public release.
- Article and social posts remain drafts for maintainer review.
- Private launch drafts and a proposed old-repository notice are prepared in
  ignored local storage, outside the public source tree.

## Initial evidence

- GitHub main CI passed on 2026-08-22 for the base commit.
- Six open Dependabot alerts: Next.js (two critical), sharp, nanoid, js-yaml,
  and @humanfs/node. These are reported advisories, not an exploitability assessment.
- GitHub secret scanning reports zero open alerts; this is not a history audit.
- v2.2.0 was published on 2026-08-02, but its release body still calls it a draft
  and the checked-in verification record does not certify its Head Coach runtime.

Record fresh results and remaining limitations in the candidate verification
document; historical results must not be relabeled as current verification.
