# paced.coach

Local-first AI endurance coaching app for self-coached athletes.

paced.coach gives you a full web app, FastAPI backend, Celery worker, local Postgres/Redis stack, and LangGraph-based coaching workflows. It runs on your machine by default. There is no hosted auth, no hosted payments, no production deploy requirement, and no required training-provider connection.

You bring one LLM key. Strava and WHOOP OAuth are optional when you want connected daily sync and weekly recaps.

Not affiliated with Strava or WHOOP. Not medical advice.

![paced.coach local-first AI endurance coach](docs/assets/readme/paced-coach-hero.png)

## Preview

The screenshots below are generated from the public `/demo` route using sanitized fixture data. They do not read a local database or real athlete account.

<p>
  <img src="docs/assets/readme/paced-coach-dashboard.png" alt="paced.coach dashboard with daily focus, recovery gates, weekly recap, daily sync, and season progress" width="49%" />
  <img src="docs/assets/readme/paced-coach-plan.png" alt="paced.coach generated training plan with season roadmap and 28-day calendar" width="49%" />
</p>

![paced.coach coach workspace preview](docs/assets/readme/paced-coach-coach.png)

Open the same preview locally at `http://localhost:3000/demo` after `make start`.

## What You Get

- A local web app for profile, race calendar, plan generation, active plan review, and coach conversations.
- AI-generated season roadmap plus a 28-day execution block.
- Versioned plan renderers for coach report, season strategy, and calendar-style weekly plan views.
- Optional Strava and WHOOP OAuth for connected daily sync and weekly recap.
- Explicit confidence boundaries when only declared profile/goals are available.
- Local-first data posture: your app database is your local Postgres volume.

## Requirements

- Docker with Docker Compose v2
- Pixi
- Node.js 24 and npm
- One LLM key: `OPENAI_API_KEY` for the default mode, or `ANTHROPIC_API_KEY` with `AI_MODE=anthropic`

## Quick Start

```bash
git clone https://github.com/leonzzz435/paced-coach.git
cd paced-coach

cp .env.example .env
cp web/app/.env.example web/app/.env.local

# Edit .env and set OPENAI_API_KEY.
# Alternative: set AI_MODE=anthropic and ANTHROPIC_API_KEY instead.
# Optional for Strava/WHOOP later: generate FERNET_KEY and provider OAuth values.

make setup
make start
```

Open:

- Web app: `http://localhost:3000`
- Demo preview: `http://localhost:3000/demo`
- API docs: `http://localhost:8000/docs`

`make setup` installs Python dependencies with Pixi and web dependencies with `npm ci --ignore-scripts`.
`make start` starts local Postgres, Redis, API, worker, beat, runs migrations, and starts the Next.js dev server.

## First Useful Run

1. Open `http://localhost:3000/app`.
2. Complete `/app/profile`.
3. Add a primary race or goal in `/app/competitions`.
4. Generate a plan from `/app/new`.
5. Read the active plan at `/app/plan`.
6. Ask questions in `/app/coach`.

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

More detail:

- [Privacy and data](docs/local-first/privacy-and-data.md)
- [Data preservation](docs/local-first/data-preservation.md)
- [AI coaching limitations](docs/local-first/ai-coaching-limitations.md)

## Safety Model

The default app has no login because it is intended for localhost single-user use. Do not expose it to a LAN or the public internet without adding authentication, TLS, network hardening, and a separate security review.

Docker Compose binds API, Postgres, and Redis to loopback by default. Keep it that way for local use.

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md). Never commit real credentials, local `.env` files, provider tokens, database dumps, or private athlete exports.

## License

MIT License. See [LICENSE](LICENSE).
