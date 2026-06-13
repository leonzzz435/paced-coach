---
name: repo-router
description: Logic for routing tasks to the correct role and skill set. Use at the start of complex multi-file tasks.
---

# Repo Router: Triage & Dispatch

## 1. Path -> Role Mapping

| Path Pattern | Role | Primary Context |
| :--- | :--- | :--- |
| `web/**` | **Frontend** | `web/AGENTS.md`, `nextjs-frontend` |
| `web/app/src/app/{impressum,privacy,terms,support,delete}/**`, `LEGAL_TODO.md` | **Public Legal Pages** | factual local-first public copy; no legal-advice claims |
| `api/**` | **Backend** | `api/AGENTS.md`, `fastapi-backend` |
| `worker/**` | **Worker** | `worker/AGENTS.md`, `celery-worker` |
| `services/ai/**` | **AI Engineer** | `services/ai/AGENTS.md`, `langgraph-workflows` |
| `docker-compose.yml`, `scripts/dev_all.sh`, `scripts/local_celery.sh` | **Local Ops** | local-first setup docs and shell verification |
| `AGENTS.md`, `*/AGENTS.md`, `.agents/**`, `agents_docs/**`, `.codex/**` | **Agent/Docs Maintainer** | keep instructions local-first, secret-safe, and consistent with current repo direction |

## 2. Dispatch Process

1.  **Analyze Intent**: Read the user request.
2.  **Identify Paths**: Which files will likely change?
3.  **Activate Skills**:
    *   **Always**: `python-style`, `testing` (if Python).
    *   **Domain**: Activate the skill matching the Role above.
    *   **Agent/docs cleanup**: Prefer read-only scans first, delete stale docs decisively, and keep only current contributor-facing guidance plus roadmap state.
    *   **Public legal pages**: Keep facts exact, avoid legal-advice claims, and update `LEGAL_TODO.md` when follow-ups remain.
4.  **Check Constraints**:
    *   Does it expose the no-login app outside loopback? -> **HALT**. Ask for approval.
    *   Can it delete or rewrite local training-plan data? -> **HALT**. Ask for approval.
    *   Does it read/write secret-bearing files? -> **HALT**. Ask for approval.

## 3. Verification Plan

*   **Frontend**: `npm run lint` && `npm run build`
*   **Legal content (web)**: `npm run lint` && `npm run build` + update `LEGAL_TODO.md` when follow-ups remain.
*   **Backend**: `pixi run ruff-fix` && `pixi run type-check` && `pixi run test`
*   **AI**: `pixi run test services/ai`
