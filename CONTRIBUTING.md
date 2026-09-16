# Contributing

Build an agent that turns declared athlete context into plans that survive real
application boundaries: interrupted runs, retries, approval and changing schedules.

## Local Setup

Follow [docs/local-first/setup.md](docs/local-first/setup.md).

The default development target is the local-first single-user app. Do not add hosted auth, payment, or deploy assumptions to the normal setup path.

## Development Checks

Run the checks relevant to your change:

```bash
pixi run ruff-fix
pixi run type-check
pixi run test
```

For frontend changes:

```bash
cd web/app
npm run test
npm run type-check
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests use synthetic fixtures and mocked API responses; no OpenAI key is
needed. On Linux, `npx playwright install --with-deps chromium` also installs
browser system libraries. Failure recordings stay in ignored `.tmp/` storage.
Never attach a browser trace or video from a real athlete database to a public PR.

PostgreSQL durability tests require a disposable database; follow
[the release checklist](docs/local-first/release-checklist.md). The optional
`test_plans_integration_db.py` suite truncates tables and requires both
`DATABASE_URL_ASYNC` and `ALLOW_DESTRUCTIVE_INTEGRATION_DB=true`. Never point it
at the database holding your own training history.

## Data Safety

Do not run destructive database commands in shared/local preservation work unless the issue explicitly requires it and the operator has backed up data.

Avoid `docker compose down -v` unless you intentionally want to delete local Postgres data.

## Secrets

Never commit `.env`, `.env.local`, provider tokens, LLM keys, database dumps, screenshots with private data, generated training exports, or local config files.

Before opening a PR, check:

```bash
git status --short
git diff --check
```

## Product Boundaries

- Provider-free planning and coach chat must work from athlete-declared context alone.
- External training-data connectors are not part of the current runtime.
- No-provider outputs must not invent activity, load, sleep, HRV, recovery, or readiness claims.
- The public setup path must not require hosted auth, hosted payments, vendor deployment accounts, or production infrastructure accounts.

## Pull Requests

Keep PRs focused. Include the verification commands you ran and call out any skipped checks.

## Where to start

- **Frontend:** accessibility, mobile plan navigation, clear loading and failure states.
- **Agent evaluation:** synthetic constraint conflicts, clarification, proposal approval
  and missing evidence. Separate observed model behavior from mocked contract tests.
- **Local setup:** reproduce the documented install on macOS, Linux or Windows and
  report the exact failing step without pasting credentials.
- **Documentation:** improve explanations of model choice, architecture and privacy.

Read [the architecture](docs/architecture/overview.md) and
[model selection](docs/local-first/models.md) before changing orchestration.
Changes to canonical plans belong behind the existing transaction, ownership and
approval boundaries. Let the model reason about coaching; keep validation,
idempotency and access control deterministic.

Open a [GitHub issue](https://github.com/leonzzz435/paced-coach/issues) before a
large feature or architecture change. Include a small synthetic reproduction,
expected behavior, actual behavior and version. See [SECURITY.md](SECURITY.md)
for private vulnerability reporting.
