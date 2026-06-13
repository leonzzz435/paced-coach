# Connect WHOOP Locally

WHOOP is an optional data connector. It is not used for login, and the manual profile/plan flow works without it.

## What WHOOP Adds

- Recovery, cycles, workout, sleep, profile, and body-measurement context.
- Better daily sync and weekly recap evidence when recovery/readiness data is available.
- No Strava activity stream replacement. Use Strava for activity-history context if desired.

## Create A WHOOP App

1. Open the WHOOP Developer Dashboard and create an app.
2. Register this redirect URI:

```text
http://localhost:3000/app/api/oauth/whoop/callback
```

WHOOP requires the redirect URI in the OAuth request to match a value registered in the developer dashboard.

## Environment

Set these values in the root `.env`:

```bash
FERNET_KEY=<generated-fernet-key>
WHOOP_OAUTH_ENABLED=true
WHOOP_OAUTH_CLIENT_ID=<whoop-client-id>
WHOOP_OAUTH_CLIENT_SECRET=<whoop-client-secret>
WHOOP_OAUTH_REDIRECT_URI=http://localhost:3000/app/api/oauth/whoop/callback
```

Set this value in `web/app/.env.local`:

```bash
NEXT_PUBLIC_WHOOP_OAUTH_ENABLED=true
```

Generate a local token-encryption key with:

```bash
pixi run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If you already connected providers, do not change `FERNET_KEY` unless you are willing to reconnect them. Existing encrypted tokens cannot be decrypted with a new key.

## Requested Scopes

The app requests:

```text
read:recovery read:cycles read:workout read:sleep read:profile read:body_measurement offline
```

`offline` is required so WHOOP returns a refresh token for local reconnect-free operation. The app does not use WHOOP as an identity provider.

## Connect

1. Start the local stack with `make start`.
2. Open `http://localhost:3000/app/settings`.
3. Click `Connect WHOOP`.
4. Approve the requested scopes.
5. Return to Settings and confirm WHOOP is active.

The backend stores encrypted access and refresh tokens in local Postgres. OAuth state is random, single-use, and expires after 10 minutes.

## Disconnect Or Reconnect

- Use `Settings -> Disconnect WHOOP` to remove local WHOOP tokens and invalidate pending WHOOP OAuth sessions.
- The app attempts WHOOP access revocation. If provider revocation fails, local tokens are still removed and the failure is logged without token values.
- If Settings shows `token_expired` or `stale`, reconnect WHOOP.
- WHOOP refresh responses can rotate refresh tokens; the backend serializes refresh updates for one local owner/provider.

## Daily Sync And Weekly Recap

Daily sync and weekly recap are optional connected-mode actions. They should run only when at least one connected training provider is usable. Without Strava/WHOOP, manual plan generation and coach chat still work, but the coach must not claim recent activity or recovery trends.

## References

- WHOOP OAuth docs: https://developer.whoop.com/docs/developing/oauth/
- WHOOP API scopes: https://developer.whoop.com/api
