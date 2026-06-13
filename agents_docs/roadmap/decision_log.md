# Decision Log

Keep this file short. It should capture durable product and architecture decisions, not day-by-day cleanup history.

## 2026-06-13 — Public repository becomes local-first baseline

- **Decision:** Treat the repository as the open-source product artifact: a local single-owner AI endurance coach with optional connected providers.
- **Why:** The useful public artifact is the full web app plus API/worker/AI workflow, not a hosted service clone or a return to the older CLI-only project.
- **Implication:** Setup docs, workflows, migrations, agent instructions, and tests must assume local-first operation by default.

## 2026-06-13 — Fresh installs use one baseline database migration

- **Decision:** Replace historical schema migration chains with a single `001_initial_local_first` Alembic baseline.
- **Why:** Public fresh installs should not replay obsolete auth, payment, provider, or deployment history before reaching the current schema.
- **Implication:** Existing private/local databases are personal state; public contributors start from the baseline schema.

## 2026-06-13 — Connected providers are optional data sources, not login

- **Decision:** Keep Strava and WHOOP OAuth as optional data connectors. The app remains useful without either provider.
- **Why:** First-use value should come from profile, competitions, constraints, and coach reasoning. Connected data improves context but should not be a hard requirement.
- **Implication:** Provider failures must stay connector-scoped and must not block manual planning.

## 2026-06-13 — No tracked internal marketing or generated personal artifacts

- **Decision:** Remove internal video/social-story tooling, example-capture tooling, generated personal artifacts, and stale private planning docs from the public tree.
- **Why:** These files confuse contributors, create artifact-risk, and do not help users run the product locally.
- **Implication:** Future proof/demo assets must use synthetic public data and be intentionally documented.

## 2026-04-03 — Plan-first coaching remains the product architecture

- **Decision:** Position the product around season roadmap, living 28-day block, coach proposals, daily updates, and weekly recaps.
- **Why:** The durable product value is an adaptive coaching loop, not a one-off dashboard or connector utility.
- **Implication:** Analysis and readiness views support the coach loop; they are not the product front door.
