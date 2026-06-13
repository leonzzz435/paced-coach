# AGENTS.md — AI Services (services/ai)

## Role: AI Engineer
**Scope**: `services/ai/**`

## Context
AI Logic using LangGraph, LangChain, and various LLM providers.

> **⚠️ Agent Autonomy Philosophy**: Before building or modifying any AI-powered feature, read the "Agent Autonomy Philosophy" section in the root `AGENTS.md`. It is the #1 design constraint for this scope.

## Rules
1.  **LangGraph**: Use LangGraph for all complex flows (stateful agents).
2.  **Model Config**: ALWAYS use `services.ai.model_config` for model instantiation. Never hardcode model names ("gpt-4").
3.  **Structured Output**: Use Structured Output (Pydantic objects) for all intermediate steps.
4.  **Tracing**: Ensure `LANGSMITH_API_KEY` is set to enable tracing (via `LangSmithConfig`).
5.  **Cost Awareness**: Optimize infrastructure (caching, parallelism, model tier selection), NOT intelligence (never strip context or add heuristic pre-filters). See root `AGENTS.md` for full policy.

## Local Runbook
-   **Test AI Logic**: `pixi run test services/ai` (uses mocks by default)
-   **Run Stack**: `pixi run dev-all` (web + API + worker)

## Definition of Done
-   [ ] `pixi run ruff-fix`
-   [ ] `pixi run type-check`
-   [ ] Tests pass with mocked providers
