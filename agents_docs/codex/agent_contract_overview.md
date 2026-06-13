# Agent Contract Overview

## 1. Instruction Sources
Codex behavior is driven by a layered architecture:
-   **Root `AGENTS.md`**: Global contract, branch rules, and secrets policy.
-   **Scoped `AGENTS.md`** (e.g., `web/`, `api/`): Domain-specific rules.
-   **Skills (`.agents/skills`)**: On-demand capabilities loaded via metadata.

## 2. Critical Paths
Modifications to these paths require extreme caution and often strict review:
-   `services/ai/model_config.py`: AI model selection and cost-estimate logic.
-   `.github/workflows/**`: CI/CD pipelines and guardrails.
-   `api/deps.py` & `web/app/src/middleware.ts`: Authentication and authorization logic.
-   `api/migrations/**`: Persistent data migrations.

## 3. Definition of Green (CI Success)
A change is considered "Green" only if it passes the following automated checks:

### Python (Backend/AI/Worker)
-   **Linting**: `pixi run lint-ruff` (Must pass without error)
-   **Type Checking**: `pixi run type-check` (Strict mypy compliance)
-   **Tests**: `pixi run test` (All unit and integration tests fail-free)

### Infrastructure
-   Hosted vendor deployment paths were removed for local-first OSS.
-   Local Docker Compose config should keep DB, Redis, API, and web services bound to loopback unless the app adds real auth and hardening.

## 4. High-Risk Edits (HITL Required)
The Agent must **pause and request confirmation** (HITL) before finalizing changes to:
1.  **Local Runtime Exposure**: Any change that exposes the no-login app beyond loopback.
2.  **AI Cost Modeling**: Changes to `model_config.py` or local AI usage controls.
3.  **Authentication**: Changes to local-owner resolution, local auth safety checks, or user identity schema.
4.  **Data Preservation**: Migrations, local-owner rewrites, or any operation that can delete local training plan data.
5.  **Secrets**: Any operation involving reading/writing `.env` or Vault values.
