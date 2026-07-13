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
- LangSmith if `LANGSMITH_API_KEY` is set

Leave optional integrations unset if you do not want those network paths.

## Public Release Gate

Before publishing a public release, run the non-destructive audit from a clean release-candidate commit:

```bash
bash scripts/release_audit.sh
```

The audit uses pinned Gitleaks `v8.30.1` scans against isolated copies of tracked files and publishable Git history. It reports ignored local secret/data paths by name only and never scans their contents. Redacted reports and temporary scan repositories stay under ignored `.tmp/release-audit/`.

The gate covers:

- working tree cleanliness
- ignored local secret files
- git history secret scan
- generated files and caches
- workflow secret references
- screenshots and fixtures
- hosted ops leftovers

If the audit reports a possible secret, rotate the credential first. Do not rewrite history, delete local artifacts, or remove Docker volumes without explicit maintainer approval and a backup/data-preservation check.
