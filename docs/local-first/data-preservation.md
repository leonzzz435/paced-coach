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

Then restart the API/web app. Your active season plan, weekly plan, coach threads, and competitions should resolve through that local owner.

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

## Schema Migration Status

Fresh public installs first create the application schema at `001_initial_local_first`, then apply the additive `002_head_coach_checkpoints` upgrade. Revision `002` adds only LangGraph execution-state tables (`checkpoint_migrations`, `checkpoints`, `checkpoint_blobs`, and `checkpoint_writes`); it does not rewrite existing users, profiles, jobs, competitions, plans, coach threads, or coaching events.

Run both revisions with:

```bash
pixi run alembic upgrade head
```

The declared Alembic head is `002_head_coach_checkpoints`.

If you used a pre-public branch before the migration history was squashed, your local database may still contain an older `alembic_version` even though the tables already match the local-first schema. In that case:

1. Take a backup.
2. Confirm your data owner with `scripts/local_owner_report.py`.
3. Set `LOCAL_OWNER_USER_ID` if needed.
4. Stamp the existing schema to the public baseline:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/paced_coach \
  pixi run alembic stamp --purge 001_initial_local_first
```

Then run `pixi run alembic upgrade head` to create the additive checkpoint tables from revision `002`. Do not use `stamp --purge` on an unknown database; it only changes Alembic bookkeeping and assumes the revision-001 application schema already matches the app.

## Head Coach Checkpoints

The new checkpoint tables store disposable execution progress so a long-running Head Coach run can pause or resume. Canonical profiles, plans, and Coach Events remain in their existing domain tables. Backups of the Postgres volume include both kinds of data.

Terminal-run checkpoints are normally removed after seven days. The protected local data reset removes checkpoint rows for the local owner together with their profile, plans, jobs, and coaching data while preserving the technical local-owner row.
