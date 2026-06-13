# Security Policy

## Supported Use

The current public target is a local-first, single-user app running on `localhost`.

Do not expose the no-login app to a LAN or public internet without adding authentication, TLS, network controls, and a separate security review.

## Reporting Issues

Please report security issues privately to the maintainer instead of opening a public issue with exploit details.

Include:

- affected commit or version
- impacted component
- reproduction steps
- expected impact
- any suggested remediation

## Secrets

Never commit real credentials. This includes:

- LLM API keys
- Strava/WHOOP OAuth secrets
- provider access or refresh tokens
- database URLs with nonlocal credentials
- Fernet keys
- local `.env` files
- training exports, screenshots, or logs containing private athlete data

If a secret is committed or shared, rotate it immediately.

## Local Data

Local Postgres data can contain sensitive training and coaching history. Back up before destructive operations and do not include database dumps in issues or PRs.

## External Data Processors

The local app can send data to:

- the configured LLM provider during generation/coaching
- Strava/WHOOP if OAuth is configured
- LangSmith if `LANGSMITH_API_KEY` is set

Leave optional integrations unset if you do not want those network paths.

## Public Release Gate

Before publishing a public release, run a release audit covering:

- working tree cleanliness
- ignored local secret files
- git history secret scan
- generated files and caches
- workflow secret references
- screenshots and fixtures
- hosted ops leftovers
