# paced.coach

**An open-source endurance coach that turns your constraints into a plan—and keeps the conversation connected to it.**

Describe your goals, training history, availability, and constraints. paced.coach turns that athlete-declared context into a personal season strategy and a day-by-day execution block, then carries the same context into coach chat.

**No wearable required.** Bring an OpenAI API key and the context only you know. No activity-platform or recovery-device account is connected to the app. GPT-6 Astra is available through the opt-in `AI_MODE=astra` configuration.

The complete app runs on your machine by default: Next.js frontend, FastAPI backend, Celery/LangGraph coaching workflows, and local Postgres/Redis. There is no hosted auth, hosted payment, or production deployment requirement.

Not medical advice.

The next release is being prepared on this branch. See the
[release verification record](docs/releases/v2.3.0-verification.md) for completed
checks, live-model evidence and remaining gates. Published tags remain unchanged.

![paced.coach local-first AI endurance coach](docs/assets/readme/paced-coach-hero.png)

## Preview

The screenshots below use the public `/demo` route and synthetic fixture data.
They do not read a local database or a real athlete account. The sample coach
conversation is illustrative; it is not a recorded model response.

<p>
  <img src="docs/assets/readme/paced-coach-plan.png" alt="paced.coach generated training plan with season roadmap and 28-day calendar" width="100%" />
</p>

![paced.coach coach workspace preview](docs/assets/readme/paced-coach-coach.png)

Open the same preview locally at `http://localhost:3000/demo` after `make start`.

## What You Get

- One continuous coaching flow: athlete profile and goals, season roadmap, 28-day execution block, then coach conversations against the actual plan.
- A calendar-first view of every generated session, with the longer season strategy always in reach.
- Versioned plan renderers for coach report, season strategy, and calendar-style weekly plan views.
- A provider-free coaching model that reasons from what the athlete explicitly declares and what the app has generated.
- Explicit confidence boundaries: missing activity, load, sleep, HRV, recovery, and readiness evidence is never invented.
- Local-first data posture: your app database is your local Postgres volume.

## Requirements

- Docker with Docker Compose v2 and the Buildx plugin
- Pixi
- Node.js 24 and npm
- One OpenAI API key: `OPENAI_API_KEY`

The software is MIT-licensed; OpenAI API usage is billed separately. The app and
database run locally, while relevant coaching context is sent to OpenAI.

## Quick Start

```bash
git clone https://github.com/leonzzz435/paced-coach.git
cd paced-coach

cp .env.example .env
cp web/app/.env.example web/app/.env.local

# Edit .env and set OPENAI_API_KEY.

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

No wearable is required for this path. Your OpenAI API key plus your declared profile, goals, availability, constraints, and race calendar form the coaching baseline. The coach must not claim recent load, compliance, HRV, sleep, recovery, or readiness trends unless you explicitly provide that information.

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

For GPT-6 Astra, change `AI_MODE=cost_effective` to `AI_MODE=astra` and restart the
API and worker. See [model selection](docs/local-first/models.md) for role mapping
and reasoning profiles. The default remains unchanged.

External training-data connectors are intentionally not shipped. The full plan and coach flow works from declared context alone.

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

Fresh public installs apply the local-first baseline `001_initial_local_first` and then the additive Head Coach checkpoint upgrade `002_head_coach_checkpoints`. If you already ran a pre-public branch with older migration revisions, back up your database and follow [docs/local-first/data-preservation.md](docs/local-first/data-preservation.md) before running the app.

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
npx playwright install chromium
npm run test:e2e
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
services/ai/         Shared Head Coach runtime, semantic profiles, artifacts, and evals
web/app/             Next.js app
docs/local-first/    Local setup, privacy, and data docs
agents_docs/         Internal planning and architecture notes
tests/               Python tests
```

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md): setup, checks and useful first
contributions. UI accessibility, synthetic agent evaluations and setup
reproducibility are particularly useful areas.

## Why build this as an agent?

The interesting part starts when a training goal conflicts with real life.
The Head Coach can ask a clarification, preserve the interrupted run, and continue
after the athlete answers. Coach conversations share the saved plan; proposed
changes pass through explicit approval and application validation.

The engineering is designed around those boundaries:

- LangGraph checkpoints in local PostgreSQL preserve execution across restarts.
- Owner locks and idempotency receipts protect against duplicate work and retries.
- A single transaction publishes the canonical plan and decision event.
- Typed artifacts and versioned renderers keep model output separate from UI code.
- Browser tests and PostgreSQL integration tests exercise application behavior;
  live synthetic model runs are reported separately.

See the [architecture](docs/architecture/overview.md) and the
[Agents API evaluation](docs/architecture/agents-api-decision.md). Supporting a
new model does not require replacing the workflow that owns your data.

## From Garmin AI Coach to paced.coach

I’m [Leon Zajchowski](https://github.com/leonzzz435). This project follows
[Garmin AI Coach](https://github.com/leonzzz435/garmin-ai-coach), which I built
around my own endurance training and described in
[the original article](https://medium.com/@leon_zajchowski/i-fired-my-garmin-coach-and-built-an-ai-to-train-for-an-ironman-70-3-heres-what-happened-09a404cecd78).

That project started with activity data. This one starts with the athlete’s
declared goals, history, schedule and constraints. It explores how to build a
complete coaching application around an agent: durable execution, explicit
uncertainty, inspectable decisions and controlled plan changes.

It is an engineering reference and a working local app. It is not clinical
validation, a promise of better race results, or a replacement for qualified
medical advice. See [coaching limitations](docs/local-first/ai-coaching-limitations.md).

## Security

See [SECURITY.md](SECURITY.md). Never commit real credentials, local `.env` files, provider tokens, database dumps, or private athlete exports.

## License

MIT License. See [LICENSE](LICENSE).
