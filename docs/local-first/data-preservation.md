# Data Preservation

This app is local-first, but the database is still user-scoped internally. The local app resolves one owner with this priority:

1. `LOCAL_OWNER_USER_ID` if it points at an existing `users.id`.
2. The single existing user that already owns training data.
3. A new synthetic local owner on a fresh database.

The safest path for an existing local database is to pin `LOCAL_OWNER_USER_ID` to the user that already owns your plans. That avoids rewriting rows.

## Report Existing Data

Run the report before changing owner settings or running migrations:

```bash
pixi run python scripts/local_owner_report.py --show-database-url
```

The report masks email and local owner identifiers by default. To inspect exact identifiers locally:

```bash
pixi run python scripts/local_owner_report.py --show-identifiers
```

Use the reported `Owner user id` as:

```bash
LOCAL_OWNER_USER_ID=<users.id from report>
```

Then restart the API/web app. Your active season plan, weekly plan, coach threads, competitions, and connected-provider state should resolve through that local owner.

## Backup First

Before any row rewrite, take a database backup. For the default Docker Compose database:

```bash
mkdir -p backups
docker compose exec -T db pg_dump -U postgres -d paced_coach > backups/paced_coach_$(date +%Y%m%d_%H%M%S).sql
```

Do not use `docker compose down -v` unless you intentionally want to delete the local Postgres volume.

## Dry-Run Migration

Most existing databases should not need row migration. Use migration only when you deliberately created a new local owner and need to move rows from an older user to that owner.

Dry-run first:

```bash
pixi run python scripts/local_owner_migrate.py \
  --source-user-id <old users.id> \
  --target-user-id <local owner users.id>
```

The dry-run checks unique-key conflicts before any update. It refuses risky cases such as both users having active weekly plans, active season plans, provider credentials, daily runs for the same date, or weekly recaps for the same week.

## Execute Migration

Only after reviewing the report, taking a backup, and confirming there are no conflicts:

```bash
pixi run python scripts/local_owner_migrate.py \
  --source-user-id <old users.id> \
  --target-user-id <local owner users.id> \
  --execute
```

The script runs in one database transaction. If any update fails, the transaction rolls back.

The script updates `user_id` references only. It does not delete users, plans, provider credentials, jobs, coach threads, or local usage history.

## Schema Baseline Status

Fresh public installs use a single Alembic baseline revision: `001_initial_local_first`. New contributors should not need to replay historical private migrations.

If you used a pre-public branch before the migration history was squashed, your local database may still contain an older `alembic_version` even though the tables already match the local-first schema. In that case:

1. Take a backup.
2. Confirm your data owner with `scripts/local_owner_report.py`.
3. Set `LOCAL_OWNER_USER_ID` if needed.
4. Stamp the existing schema to the public baseline:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/paced_coach \
  pixi run alembic stamp --purge 001_initial_local_first
```

Then `pixi run alembic upgrade head` should be a no-op. Do not use `stamp --purge` on an unknown database; it only changes Alembic bookkeeping and assumes the schema already matches the app.
