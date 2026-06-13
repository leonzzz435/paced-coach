# Privacy and Data

## Local Storage

The local app stores data in your local Postgres database:

- athlete profile
- competitions and goals
- generated plans
- coach conversations
- jobs and outputs
- optional provider tokens

Docker Compose persists Postgres in the `postgres_data` volume.

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

## Provider Tokens

Strava and WHOOP tokens are stored locally and encrypted with `FERNET_KEY`.

If `FERNET_KEY` is lost, saved provider tokens cannot be decrypted. You can reconnect the provider after setting a new key, but old encrypted tokens are not recoverable.

Disconnecting a provider from Settings deletes local tokens, invalidates pending local OAuth sessions for that provider, and attempts provider-side revocation when the provider supports it. Revocation failures do not keep local tokens.

The local privacy reset is disabled by default. If enabled, it deletes local profile, plans, coaching outputs, jobs, provider tokens, pending OAuth sessions, and legacy local usage rows. In local mode it preserves the technical local owner row so `LOCAL_OWNER_USER_ID` does not become a broken pointer.

## LLM Data Sharing

Plan generation and coaching send relevant prompt context to the configured LLM provider. This can include profile details, goals, constraints, plan content, and connected training context when enabled.

Do not enter private data that you do not want sent to your configured LLM provider.

## Tracing

`LANGSMITH_API_KEY` is optional. If configured, traces can include prompt and response content.

Leave `LANGSMITH_API_KEY` unset for the most local/private default.

## No Hidden Telemetry

Local-first setup does not require hosted telemetry. Optional provider OAuth, LLM calls, and LangSmith tracing are the external network paths relevant to user data.

## Manual Mode Boundaries

When Strava/WHOOP are not connected, the system should use declared profile/goals/context only. It must not claim recent activity history, training load, compliance, sleep, HRV, recovery, or readiness trends.
