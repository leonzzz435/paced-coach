This is the paced.coach web app (Next.js).

## Getting Started

### 1) Configure environment

The public development target is local-first single-user mode. The web app talks to the local FastAPI service and does
not require hosted auth, hosted payments, or deployment credentials.

Required:

- `API_BASE_URL` (defaults to `http://localhost:8000` if unset)

Create `web/app/.env.local` (gitignored) from the template:

```bash
cp web/app/.env.example web/app/.env.local
```

Tip: See `web/app/.env.example` for the complete local template.

### 2) Run the development server

First, install deps and run:

```bash
node --version # expected: 24.x
npm ci --ignore-scripts
npm run dev
```

From the repository root, prefer `make setup` for the full backend + frontend dependency install.

Open [http://localhost:3000](http://localhost:3000) with your browser.

### 3) Run backend services

In the repo root:

```bash
docker compose up db redis -d
pixi run api
pixi run worker
```

The usual all-in-one local path is:

```bash
make start
```

Run this from the repository root. It wraps `pixi run dev-all`.

### Pages

- `/` local app entry
- `/app` dashboard
- `/app/settings` local readiness plus Strava / WHOOP connector status
- `/app/competitions` competitions editor
- `/app/new` plan generation
- `/app/plan` active plan viewer
- `/app/coach` coach chat
- `/delete`, `/privacy`, `/terms`, `/support`, `/impressum` local-first public/legal pages

### Connected Mode

Strava and WHOOP are optional data connectors, not login providers. Configure their OAuth values in the root `.env`
only if you want connected daily sync and weekly recap.

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Local setup](../../docs/local-first/setup.md)
