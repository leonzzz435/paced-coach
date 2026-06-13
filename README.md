# paced.coach

Local-first AI endurance coaching app.

This repo contains a single-user web app, FastAPI backend, Celery worker, Postgres/Redis local stack, and LangGraph-based coaching workflows. The default public setup runs on localhost, uses your local database, and does not require hosted auth, hosted payments, production deploy tooling, or a connected training provider.

You need one LLM key to generate plans. Strava and WHOOP are optional connected-data sources; the app works without them.

Not affiliated with Strava or WHOOP. Not medical advice.

## What It Does

- Builds a season roadmap and a 28-day training block.
- Uses a saved athlete profile, goals/race calendar, constraints, and optional generation notes.
- Lets you view the active plan and ask the coach questions about it.
- Supports optional Strava/WHOOP OAuth for connected daily sync and weekly recap.
- Keeps confidence boundaries explicit when no connected activity/recovery data exists.

## Requirements

- Docker with Docker Compose v2
- Pixi
- Node.js 24 and npm
- One LLM API key: `OPENAI_API_KEY` for the default mode, or `ANTHROPIC_API_KEY` with `AI_MODE=anthropic`

## Quick Start

```bash
git clone <repo-url>
cd <repo-directory>

cp .env.example .env
cp web/app/.env.example web/app/.env.local

# Edit .env and set OPENAI_API_KEY.
# Alternative: set AI_MODE=anthropic and ANTHROPIC_API_KEY instead.
# Optional if you want Strava/WHOOP later: generate FERNET_KEY and provider OAuth values.

make setup

make start
```

`make setup` installs Python dependencies with Pixi and web dependencies with `npm ci --ignore-scripts`.
The ignored lifecycle scripts are intentional for reproducible local setup; CI still validates the normal npm install path.

Open:

- Web app: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

`make start` starts local Postgres, Redis, API, worker, beat, runs migrations, and starts the Next.js dev server. It is a wrapper around `pixi run dev-all`.

## First Useful Run

1. Open `http://localhost:3000/app`.
2. Complete `/app/profile`.
3. Add a primary goal or race in `/app/competitions`.
4. Generate a plan from `/app/new`.
5. Read the plan at `/app/plan`.
6. Ask plan questions at `/app/coach`.

Strava and WHOOP are not required for this path. Without connected data, the coach must not claim recent load, compliance, HRV, sleep, recovery, or readiness trends.

## Environment

The root `.env` is the main local config source. The web app also reads `web/app/.env.local`.

Minimum root `.env`:

```bash
OPENAI_API_KEY=...
AI_MODE=cost_effective
AUTH_MODE=local
APP_ENV=local
DATABASE_NAME=paced_coach
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/paced_coach
REDIS_URL=redis://localhost:6379/0
```

Anthropic alternative:

```bash
ANTHROPIC_API_KEY=...
AI_MODE=anthropic
```

Optional connected-mode values:

```bash
FERNET_KEY=...
STRAVA_OAUTH_ENABLED=true
STRAVA_OAUTH_CLIENT_ID=...
STRAVA_OAUTH_CLIENT_SECRET=...
STRAVA_OAUTH_REDIRECT_URI=http://localhost:3000/app/api/oauth/strava/callback

WHOOP_OAUTH_ENABLED=true
WHOOP_OAUTH_CLIENT_ID=...
WHOOP_OAUTH_CLIENT_SECRET=...
WHOOP_OAUTH_REDIRECT_URI=http://localhost:3000/app/api/oauth/whoop/callback
```

Generate `FERNET_KEY` with:

```bash
pixi run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Detailed connector setup:

- [Strava local OAuth](docs/local-first/connect-strava.md)
- [WHOOP local OAuth](docs/local-first/connect-whoop.md)

## Local Data

Postgres data is stored in the Docker volume `postgres_data`. Normal restarts preserve your plans and profile.

Do not run destructive Docker commands unless you intentionally want to wipe local data:

```bash
docker compose down -v
```

For existing local databases, `LOCAL_OWNER_USER_ID` can point the local app at an existing `users.id` without moving rows. To inspect current owner/data counts:

```bash
pixi run python scripts/local_owner_report.py
```

Fresh installs use `LOCAL_OWNER_KEY=local-owner` as the stable owner key. Existing databases should prefer `LOCAL_OWNER_USER_ID` when there is already training data.

Fresh public installs use one baseline database migration: `001_initial_local_first`. If you already ran a pre-public branch with older migration revisions, back up your database and follow [docs/local-first/data-preservation.md](docs/local-first/data-preservation.md) before running the app.

More detail: [docs/local-first/privacy-and-data.md](docs/local-first/privacy-and-data.md) and [docs/local-first/data-preservation.md](docs/local-first/data-preservation.md).

## Safety Model

The default app has no login because it is intended for localhost single-user use. Do not expose it to the public internet without adding authentication, TLS, network hardening, and a separate security review.

Docker Compose binds API, Postgres, and Redis to loopback by default. Keep it that way for local use.

AI coaching limitations are documented in [docs/local-first/ai-coaching-limitations.md](docs/local-first/ai-coaching-limitations.md).

## Development

```bash
make test
make lint
make type-check

cd web/app
npm run test
npm run type-check
npm run lint
npm run build
```

Useful services:

```bash
make start
make stop
pixi run api
pixi run worker
pixi run worker-beat
```

## Project Layout

```text
api/                 FastAPI routes, models, migrations, local owner auth
worker/              Celery app and background plan generation tasks
services/ai/         LangGraph workflows, prompts, schemas, coach agents
web/app/             Next.js app
docs/local-first/    Local setup, privacy, and data docs
agents_docs/         Internal planning and architecture notes
tests/               Python tests
```

## Privacy

Your local profile, competitions, provider tokens, plans, jobs, and coaching history live in your local Postgres database. Plan generation sends relevant prompt context to your configured LLM provider. If `LANGSMITH_API_KEY` is set, traces can include prompt and response content.

There is no hidden telemetry required for local-first use.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT License. See [LICENSE](LICENSE).
