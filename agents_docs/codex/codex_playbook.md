# Codex Local Playbook

## 1. Default Workflow

- Work from a feature branch.
- Keep local secrets in gitignored `.env` files only.
- Use scoped `AGENTS.md` files before changing `web/`, `api/`, `worker/`, or `services/ai/`.
- Run the affected Definition of Done before committing.

## 2. Review Requests

Use a code-review mindset for local review requests:

- **[BLOCKER]**: security risk, data loss, broken local-first setup, or leaked private data.
- **[WARN]**: confusing logic, missing coverage, brittle behavior, or maintainability risk.
- **[INFO]**: small cleanup or optional polish.

## 3. Public Release Gate

Do not publish until the public release gate passes:

- no secrets or private athlete data in tracked files
- no generated personal artifacts in the public tree
- no hosted auth, payment, or deployment requirements in setup docs
- fresh local happy path manually verified
