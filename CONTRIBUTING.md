# Contributing

Thanks for considering a contribution.

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
```

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

- Manual Mode must work without Strava/WHOOP.
- Connected Mode is optional.
- No-provider outputs must not invent activity, load, sleep, HRV, recovery, or readiness claims.
- The public setup path must not require hosted auth, hosted payments, vendor deployment accounts, or production infrastructure accounts.

## Pull Requests

Keep PRs focused. Include the verification commands you ran and call out any skipped checks.
