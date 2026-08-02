---
title: Hardening agentic plan generation across durable boundaries
date: 2026-08-01
category: best-practices
module: head-coach-release-pipeline
problem_type: best_practice
component: development_workflow
severity: high
applies_when:
  - releasing an owner-scoped LLM workflow that creates durable domain artifacts
  - resuming LangGraph runs after human clarification
  - relying on PostgreSQL locks, checkpoints, migrations, or transaction semantics
  - replacing provider-backed workflows while retaining historical local data
  - migrating UI payloads from legacy HTML blocks to versioned semantic blocks
related_components: [api, background-job, database, frontend, continuous-integration, release-audit]
tags: [head-coach, langgraph, postgresql, idempotency, advisory-locks, durable-resume, provider-free, release-hardening]
---

# Hardening agentic plan generation across durable boundaries

## Context

An agentic workflow can look correct in mocked tests while still allowing duplicate expensive runs, ambiguous human-in-the-loop retries, or contradictory terminal state. The Head Coach release review found that correctness crossed several independently failing boundaries: HTTP admission, Celery delivery, LangGraph checkpoints, the canonical plan transaction, PostgreSQL-only semantics, and historical UI payloads.

The reusable lesson is to treat durable agent execution and canonical domain publication as coordinated but independently failing state machines. Agent intelligence owns coaching judgment; deterministic infrastructure owns concurrency, idempotency, validation, persistence, and schema dispatch.

## Guidance

### Serialize admission per owner

Acquire a PostgreSQL transaction-scoped advisory lock before checking availability and inserting the job. Derive a stable signed 64-bit key from the owner ID:

```python
async def lock_owner_plan_generation(db: AsyncSession, *, user_id: UUID) -> None:
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": owner_plan_generation_lock_key(user_id)},
    )
```

The lock, availability check, job insert, persisted input snapshot within the mutable lifecycle config, and commit must share the same transaction lifetime. Every nonterminal ownership state reserves the slot, including `awaiting_input`:

```python
AnalysisJob.status.in_(("pending", "running", "awaiting_input"))
```

A normal check-then-insert query is not a concurrency boundary: two transactions can both observe no active job before either commit becomes visible.

### Make the domain transaction authoritative

Commit the active season plan, active execution plan, Decision Ledger event, usage record, cost record, and terminal job result in one transaction under an owner-scoped active-plan lock. An idempotent repeat is valid only when both active plans already reference the same `source_job_id`.

After any later worker error, roll back the same synchronous SQLAlchemy worker session and reload the committed job status before deciding to fail it:

```python
db.rollback()
db.expire_all()
committed_status = db.execute(
    select(AnalysisJob.status).where(AnalysisJob.id == job.id)
).scalar_one_or_none()
if committed_status == "completed":
    return
```

This prevents a checkpoint-finalization failure from overwriting a successful canonical plan publication with `failed`. Checkpoints remain resumable execution state, not the source of truth for activated plans.

### Bind resume identity to request content

An idempotency key alone does not identify the request. Bind it to a deterministic hash of the clarification answer after request-schema normalization:

```python
{
    "idempotency_key": request.idempotency_key,
    "answer": request.answer,
    "answer_hash": sha256(request.answer.encode("utf-8")).hexdigest(),
}
```

The state machine must enforce:

- same key and same answer: return the existing state without another enqueue;
- same key and different answer: `409 Conflict`;
- enqueue failure: restore `awaiting_input`, preserve the interrupt, and remove the unconsumed resume payload;
- terminal success: remove the extra plaintext answer from the job config but retain the key plus hash as a size-bounded terminal receipt for the job's lifetime.

This supports exact retries before and after completion without retaining another plaintext copy in the job config. The durable LangGraph checkpoint can still contain the answer until the configured checkpoint-retention cleanup runs.

### Treat the database row as a durable dispatch intent

Queue delivery is not atomic with the API transaction. A process can stop after the `pending` job commit and before the first broker publish. Periodically scan sufficiently old `pending` rows with `FOR UPDATE SKIP LOCKED` and re-enqueue them. Worker admission must lock the job row and reject a `running` row owned by another Celery task ID, so duplicate broker deliveries remain harmless while same-task retries can continue.

### Verify production database semantics in CI

Mocked sessions and SQLite cannot certify PostgreSQL advisory locks, production JSONB behavior, LangGraph checkpoint durability, or the migration chain. CI should start disposable PostgreSQL, apply Alembic to `head`, and explicitly execute durability tests before the broad suite.

The focused PostgreSQL suite should prove:

- checkpoint restoration after graph and pool recreation;
- overlapping worker-claim exclusion;
- owner-scoped generation admission serializes across two transactions;
- duplicate workflow delivery does not increment versions or duplicate events, usage, or cost;
- a fresh database and an existing-data fixture migrate to the declared head.

Release history verification has the same fail-closed property: compare `git ls-remote --heads --tags` with local tracking refs before scanning history, so a stale clone cannot certify an incomplete public surface.

### Keep provider-free runtime ownership truthful

Removing provider UI is insufficient if runtime projections still query provider-era workflows. Establish provider-free behavior at mounted routes, task registration, agent tool policy, prompts, dependencies, dashboard queries, copy, tests, and assets.

Provider-era tables may remain solely for non-destructive reset and local data ownership. Historical UI payloads can also outlive their producer. Keep current V3 plan rendering strict, but use a narrow, explicit compatibility union for persisted recap blocks:

```ts
type RecapBlock = SemanticBlockV3 | UiHtmlBlock;

if ("content_html" in block) {
  return <HtmlSnippet html={block.content_html} />;
}
return <SemanticBlock block={block} />;
```

The HTML path must sanitize its input. This compatibility boundary does not permit HTML in new V3 artifacts.

## Why This Matters

The architecture becomes coherent when every durable boundary has one owner:

- the advisory lock owns generation admission;
- the nonterminal job owns the generation slot;
- the answer-bound receipt owns resume idempotency;
- the atomic database transaction owns active artifacts and terminal success;
- the checkpoint owns only resumable execution progress;
- the schema-versioned renderer owns current artifacts;
- a narrow compatibility adapter owns persisted legacy payloads.

Without these boundaries, partial failure creates split-brain state: a failed job with active plans, two generations for one owner, a resume key that aliases different answers, or a current renderer guessing at old data.

## When to Apply

- A long-running agent can pause for human input or survive worker restarts.
- One run activates multiple related domain artifacts.
- Queue delivery and checkpoint persistence happen outside the canonical commit.
- Correctness depends on PostgreSQL-specific transaction behavior.
- Provider or schema migrations retain locally persisted historical data.
- A release claim must be bound to one exact commit rather than a mutable branch or stale clone.

## Examples

For each new lifecycle state, answer these questions in code review and executable tests:

1. Does the state still own the generation slot?
2. Is it terminal, retryable, or resumable?
3. Which database row or transaction is authoritative?
4. Is retry identity bound to request content?
5. What happens if enqueue, checkpoint, or transport fails immediately before or after commit?
6. Is the behavior covered against PostgreSQL rather than only mocks?
7. Does the UI dispatch by `schema_version` or an explicit legacy discriminator?

The certified failure-injection suite includes concurrent starts, duplicate deliveries, stranded-dispatch recovery, same/different-answer resumes, broker failure, post-commit failure reconciliation, partial active-plan receipts, fresh database migrations, stale remote refs, and legacy recap rendering. An injected real-checkpointer failure after the canonical commit and an existing-data migration fixture remain valuable follow-up coverage where the release environment can support them safely.

## Related

- [Head Coach runtime refactor plan](../../plans/2026-07-19-001-refactor-head-coach-runtime-plan.md)
- [Head Coach, artifact, and UI ownership contract](../../../agents_docs/architecture/ai_ui_contract.md)
- [Head Coach architecture requirements](../../brainstorms/2026-07-19-head-coach-agent-architecture-requirements.md)
- [v2.2 release-candidate certification plan](../../plans/2026-08-01-001-fix-certify-v2-2-release-candidate-plan.md)
- [Architecture decision log](../../../agents_docs/roadmap/decision_log.md)
