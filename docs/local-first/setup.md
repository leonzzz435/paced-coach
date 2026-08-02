# Local-First Setup

This app is designed for a single local operator on `localhost`.

## Prerequisites

- Docker with Docker Compose v2
- Pixi
- Node.js 24 and npm
- One OpenAI API key: `OPENAI_API_KEY`

## Setup

```bash
cp .env.example .env
cp web/app/.env.example web/app/.env.local

make setup

make start
```

`make setup` runs `pixi install` and installs web dependencies with `npm ci --ignore-scripts`
for reproducible local setup.

Open `http://localhost:3000/app`.

## First Useful Run

No wearable is required. With an OpenAI API key configured:

1. Describe your training history, availability, constraints, and primary goals in the athlete profile.
2. Add a target race or a primary goal.
3. Generate your season roadmap and 28-day execution block.
4. Open the plan calendar, then continue the same context in coach chat.

Version 2.2.0 has no external training-data connectors. The complete release path is profile, goal/race, plan, calendar, and coach chat.

## Required Configuration

Set `OPENAI_API_KEY` in `.env`:

```bash
OPENAI_API_KEY=...
AI_MODE=cost_effective
```

The default local mode is:

```bash
APP_ENV=local
AUTH_MODE=local
DATABASE_NAME=paced_coach
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/paced_coach
REDIS_URL=redis://localhost:6379/0
```

## Existing Local Database

If you already have data, keep your current `DATABASE_NAME` and `DATABASE_URL`.

If the app needs to bind local mode to an existing owner, set:

```bash
LOCAL_OWNER_USER_ID=<existing users.id UUID>
```

Use the report script to identify the owner without changing data:

```bash
pixi run python scripts/local_owner_report.py
```

Do not reset or recreate the database when preserving an existing training plan.

Detailed backup and dry-run migration guidance lives in [data-preservation.md](data-preservation.md).

## Network Boundary

The no-login app is for localhost only. Do not expose it on a LAN or public internet without adding authentication, TLS, and a separate security review.

Docker Compose binds exposed ports to `127.0.0.1` by default.

## Common Commands

```bash
make start
make stop
make test

cd web/app
npm run test
npm run type-check
npm run lint
npm run build
```
