---
name: langgraph-workflows
description: Current patterns for Head Coach agents, durable LangGraph lifecycles, checkpoints, interrupts, and domain ownership in services/ai.
---

# Head Coach and LangGraph Patterns

## Choose the runtime intentionally

- Use `langchain.agents.create_agent` for bounded model/tool loops, middleware, dynamic tools, and structured output.
- Use `StateGraph` around an agent when the product lifecycle needs durable stages, interrupts, resume, deterministic review, or atomic commit boundaries.
- Do not recreate an agent loop with manual `AIMessage`/`ToolMessage` routing or use the deprecated prebuilt `create_react_agent` helper.
- Do not introduce a multi-agent framework until a grounded eval shows that a focused specialist materially improves the Head Coach's result.

## Shared Head Coach factory

- Instantiate models only through `services.ai.model_config.ModelSelector`.
- Select behavior through an explicit semantic run profile from `services/ai/head_coach/run_profiles.py`.
- Build ongoing agents through `services/ai/head_coach/agent.py` so identity, middleware, call limits, reasoning effort, and `ToolStrategy` repair remain consistent.
- Use strict Pydantic response schemas. Return validation errors to the responsible model for bounded repair; after exhaustion, fail visibly.
- Never synthesize rule-authored coaching content as a fallback.

## Context and tools

- Pass the complete relevant local context. Do not truncate or pre-score it to save tokens.
- Expose tools by semantic capability. Provider tools exist only when a connected provider is observable at run start.
- Tools are read-only unless a profile and deterministic service boundary explicitly grant proposal authority.
- Specialists and research tools advise; the Head Coach owns the final judgment.

## Durable graph state

- Keep graph state typed and serializable. Use Pydantic or `TypedDict`; use reducers only where merge semantics are required.
- Use explicit `START`/`END` edges for deterministic lifecycle stages.
- Use `Command(update=..., goto=...)` when a node owns both its state update and route.
- Use `interrupt(value)` for material clarification, then resume the same thread with `Command(resume=...)`.
- Compile production graphs with the process-safe PostgreSQL checkpointer provider. In-memory savers are test-only.
- Always pass a stable owner-scoped `thread_id`. Keep root `checkpoint_ns` empty/reserved for LangGraph internals.

## Ownership and side effects

- LangGraph checkpoints own execution progress, not canonical product state.
- PostgreSQL domain rows and Coach Events own accepted plans, decisions, and user-visible history.
- Keep side effects in idempotent service/commit nodes. A retry or resume must not duplicate events, quota consumption, costs, or plan writes.
- Acquire the per-run execution claim before advancing a durable graph. Cancellation and terminal domain state win over stale delivery.
- The model may propose changes; deterministic services validate schema/version and commit only after the correct product approval boundary.

## Observability

- Emit semantic product lifecycle events, not internal graph node names.
- Trace sanitized metadata, tool names, artifact IDs, validation outcomes, and cost/token totals.
- Never trace credentials, provider tokens, database sessions, raw private context, or hidden reasoning.

## Verification

- Test successful structured output and model self-repair exhaustion.
- Test provider-free tool exposure and optional-provider capability gating.
- Test checkpoint resume, duplicate delivery, cancellation, concurrency claims, and atomic commit recovery.
- Test that no direct mutation occurs before proposal acceptance.
- Run Ruff, Mypy, mocked provider tests, and the affected frontend schema/rendering tests.
