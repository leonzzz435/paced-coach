---
name: fastapi-backend
description: Best practices for FastAPI routes, dependency injection, and error handling. Use when working in api/.
---

# FastAPI Backend Patterns

## 1. Routers
-   **Prefix**: Use `APIRouter(prefix="/v1/resource")`.
-   **Tags**: Always categorize routes with `tags=["Resource"]`.

## 2. Dependencies
-   **Injection**: Use `Depends()` for services and DB sessions.
-   **Auth**: Use `get_current_user` dependency for protected routes.

## 3. Error Handling
-   **Exceptions**: Raise `HTTPException` with clear detail.
-   **Global Handler**: Don't catch generic `Exception` in routes; let global middleware handle 500s.

## 4. Schema
-   **Request/Response**: Use Pydantic models (v2).
-   **Examples**: Provide `model_config["json_schema_extra"]` examples.
