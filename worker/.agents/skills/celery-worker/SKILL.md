---
name: celery-worker
description: Best practices for Celery tasks, idempotency, and retry handling. Use when working in worker/.
---

# Celery Worker Patterns

## 1. Task Definition
-   **Decorator**: Use `@shared_task(bind=True)`.
-   **Naming**: `verb_noun` (e.g., `process_activity`).

## 2. Idempotency
-   **Rule**: Tasks must be safe to retry. Check state before side effects.
-   **Locking**: Use Redis locks for exclusive tasks.

## 3. Retries
-   **Transient**: Use `self.retry(exc=e, countdown=backoff)`.
-   **Max Retries**: Always set a limit to avoid zombie tasks.

## 4. Serialization
-   **Payload**: Pass IDs, not objects. Fetch fresh data in the task.
