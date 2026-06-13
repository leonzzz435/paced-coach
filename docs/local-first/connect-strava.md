# Connect Strava Locally

Strava is an optional data connector. It is not used for login, and the manual profile/plan flow works without it.

## What Strava Adds

- Activity history and recent execution context.
- Better daily sync and weekly recap evidence when you have recent activities.
- No recovery, sleep, HRV, or readiness data. Use WHOOP for that context if desired.

## Create A Strava App

1. Open the Strava developer settings and create an application.
2. Set the callback domain to `localhost` or `127.0.0.1`.
3. Use this local callback URL:

```text
http://localhost:3000/app/api/oauth/strava/callback
```

Strava's OAuth docs state that `localhost` and `127.0.0.1` are allow-listed callback domains.

## Environment

Set these values in the root `.env`:

```bash
FERNET_KEY=<generated-fernet-key>
STRAVA_OAUTH_ENABLED=true
STRAVA_OAUTH_CLIENT_ID=<strava-client-id>
STRAVA_OAUTH_CLIENT_SECRET=<strava-client-secret>
STRAVA_OAUTH_REDIRECT_URI=http://localhost:3000/app/api/oauth/strava/callback
```

Set this value in `web/app/.env.local`:

```bash
NEXT_PUBLIC_STRAVA_OAUTH_ENABLED=true
```

Generate a local token-encryption key with:

```bash
pixi run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If you already connected providers, do not change `FERNET_KEY` unless you are willing to reconnect them. Existing encrypted tokens cannot be decrypted with a new key.

## Requested Scope

The app requests:

```text
activity:read_all
```

This is intentionally narrow for this product path: it reads activity history, including private activities, so the coach can reason about actual training execution. The app does not request write scopes.

## Connect

1. Start the local stack with `make start`.
2. Open `http://localhost:3000/app/settings`.
3. Click `Connect Strava`.
4. Approve the requested scope.
5. Return to Settings and confirm Strava is active.

The backend stores encrypted access and refresh tokens in local Postgres. OAuth state is random, single-use, and expires after 10 minutes.

## Disconnect Or Reconnect

- Use `Settings -> Disconnect Strava` to remove local Strava tokens and invalidate pending Strava OAuth sessions.
- The app attempts Strava deauthorization. If provider revocation fails, local tokens are still removed and the failure is logged without token values.
- If Settings shows `partial_permissions`, reconnect and approve `activity:read_all`.
- If Settings shows `token_expired` or `stale`, reconnect Strava.

## Daily Sync And Weekly Recap

Daily sync and weekly recap are optional connected-mode actions. They should run only when at least one connected training provider is usable. Without Strava/WHOOP, manual plan generation and coach chat still work, but the coach must not claim recent activity or recovery trends.

## References

- Strava OAuth authentication docs: https://developers.strava.com/docs/authentication/
