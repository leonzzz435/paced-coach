# AGENTS.md — Worker (worker)

## Role: Worker Engineer
**Scope**: `worker/**`

## Context
Background task processing using Celery and Redis.
-   **Broker**: Redis
-   **Backend**: Redis
-   **Tasks**: Long-running AI jobs, data sync, email sending.

## Rules
1.  **Idempotency**: Tasks should be idempotent whenever possible.
2.  **Serialization**: Pass IDs, not full objects, to tasks. Fetch data inside the task.
3.  **Error Handling**: Use `self.retry()` for transient errors (network, limits).
4.  **No HTTP directly**: Use internal service calls or shared libraries where possible.

## Local Runbook
-   **Start Worker**: `pixi run worker`

## Definition of Done
-   [ ] `pixi run ruff-fix`
-   [ ] `pixi run type-check`
-   [ ] Test coverage for the task logic
-   [ ] Worker process starts without errors
