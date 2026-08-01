# Privacy and Data

## Local Storage

The local app stores data in your local Postgres database:

- athlete profile
- competitions and goals
- generated plans
- coach conversations
- jobs and outputs
- LangGraph Head Coach checkpoints used to pause or resume in-progress runs
- legacy connector records when upgrading an older development database

Docker Compose persists Postgres in the `postgres_data` volume.

### Head Coach Checkpoint Content And Retention

Head Coach checkpoints are local execution state, not a second source of truth. They can contain the working context needed to resume a run, including athlete-declared profile and goal context, plan drafts, model messages, tool results, and clarification state. They are stored in the local Postgres `checkpoint_*` tables alongside the app database; they are not stored in Redis or a hosted paced.coach service.

Checkpoints for completed, failed, or cancelled runs are retained for a terminal debugging window of seven days by default and then removed by scheduled cleanup. `HEAD_COACH_CHECKPOINT_RETENTION_DAYS` can configure that window from 1 to 90 days. In-progress or awaiting-input checkpoints remain available so the run can resume.

The protected local privacy reset deletes every checkpoint payload row whose owner-scoped thread belongs to the local owner. It also deletes the owner's profile, plans, jobs, coach conversations, and related app data, while preserving only the technical local-owner row so an explicitly configured `LOCAL_OWNER_USER_ID` does not become invalid.

## Do Not Accidentally Delete Data

Normal restarts preserve data.

This command deletes local Postgres data and should only be used intentionally:

```bash
docker compose down -v
```

Local account/data deletion is disabled by default:

```bash
ALLOW_LOCAL_DATA_DELETE=false
NEXT_PUBLIC_ALLOW_LOCAL_DATA_DELETE=false
```

## Existing Founder/Developer Data

Use `LOCAL_OWNER_USER_ID` to point local mode at an existing `users.id` without moving rows.

Back up your DB before changing owner or reset settings.

## Legacy Connector Records

Version 2.2.0 does not read, refresh, transmit, or expose external training-provider credentials. An older development database may still contain legacy encrypted credential or OAuth rows. The protected local privacy reset deletes those rows together with the local profile, plans, coaching outputs, jobs, and legacy usage rows. It preserves the technical local owner row so `LOCAL_OWNER_USER_ID` does not become a broken pointer.

## LLM Data Sharing

Plan generation and coaching send relevant prompt context to OpenAI. This can include profile details, goals, constraints, plan content, and coach history.

Do not enter private data that you do not want sent to OpenAI.

## Tracing

`LANGSMITH_API_KEY` is optional. If configured, traces can include prompt and response content.

Leave `LANGSMITH_API_KEY` unset for the most local/private default.

## No Hidden Telemetry

Local-first setup does not require hosted telemetry. LLM calls and optional LangSmith tracing are the external network paths relevant to user data.

## Provider-Free Boundaries

The system uses declared profile, goals, races, constraints, notes, generated plans, and coach history. It must not claim recent activity history, training load, compliance, sleep, HRV, recovery, or readiness trends unless the athlete explicitly supplied them.
