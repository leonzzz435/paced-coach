# AGENTS.md — Backend (api)

## Role: Backend Engineer
**Scope**: `api/**`, `data/**` (db models)

## Context
This is the core FastAPI service providing the REST API and Database access.
-   **Framework**: FastAPI
-   **Database**: PostgreSQL (AsyncPG) + SQLAlchemy (DeclarativeBase)
-   **Migrations**: Alembic

## Rules
1.  **Async First**: All route handlers and DB operations must be `async`.
2.  **Pydantic V2**: Use `pydantic` v2 models for schemas.
3.  **Dependencies**: Use `Depends()` for injection (DB sessions, current user).
4.  **No Logic in Routers**: Keep business logic in `services/` or `core/`, routers are for protocol translation.
5.  **Migrations**: Never modify DB schema without an Alembic migration (`pixi run alembic revision --autogenerate`).

## Local Runbook
-   **Start API**: `pixi run api` (localhost:8000)
-   **Make Migration**: `pixi run alembic revision --autogenerate -m "message"`
-   **Apply Migration**: `pixi run alembic upgrade head`

## Definition of Done
-   [ ] `pixi run ruff-fix` (Lint)
-   [ ] `pixi run type-check` (MyPy)
-   [ ] `pixi run test` (Pytest)
-   [ ] API starts successfully locally
