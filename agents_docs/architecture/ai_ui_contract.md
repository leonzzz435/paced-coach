# Head Coach, Artifact, and UI Ownership Contract

## Source of ownership

paced.coach has one accountable coaching owner: the Head Coach. Initial planning, plan refreshes, coach chat, and memory extraction use semantic run profiles over the shared LangChain `create_agent` factory. A run profile selects the model role, reasoning effort, tool capabilities, mutation authority, and call limits; entry points do not select model names directly. The v2.2 runtime has no wearable/training-data connectors, daily sync, or weekly recap producer.

The runtime has four distinct ownership layers:

| Layer | Owns | Must not own |
| --- | --- | --- |
| Head Coach | Coaching judgment, assumptions, uncertainty, proposal intent, semantic presentation intent | Direct database mutation, auth, quota, retries, CSS |
| LangGraph execution | Durable progress, checkpoints, interrupts, resume state | Canonical plans or user-visible history |
| API/worker services | Owner checks, idempotency, validation, proposal acceptance, atomic persistence, cost linkage | Coaching heuristics or rule-authored fallback plans |
| React | Accessible components, layout, responsive behavior, safe Markdown rendering | Reinterpreting coaching decisions or accepting arbitrary model CSS/HTML |

PostgreSQL owns canonical athlete/profile/calendar records, Coach Events, accepted plans, and proposal state. LangGraph checkpoints are execution state with bounded retention; they are never the canonical coaching record.

## Runtime flow

```text
Athlete-declared context + canonical local records
                         │
                         ▼
              semantic Head Coach profile
           (complete context, capability tools)
                         │
               validated structured output
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
     direct answer              proposal or plan artifacts
                                        │
                              deterministic validation
                                        │
                          explicit commit / accept boundary
                                        │
                                        ▼
                              canonical PostgreSQL state
```

Athlete declarations and canonical local records are the planning evidence. The active tool registry reads the athlete profile, competitions, current season strategy, and current execution block; it contains no provider tools. Historical provider-era rows remain only where required for non-destructive local reset and data ownership.

## Artifact contract

New season and execution plans use `schema_version: 3` Pydantic artifacts from `services/ai/head_coach/artifacts.py`.

They contain:

- stable plan, week, day, session, section, and block IDs;
- typed dates, duration, intensity, completion, assumptions, evidence, safety concerns, and unresolved questions;
- a Decision Ledger entry explaining material choices;
- semantic blocks such as workout, intervals, callout, checklist, fueling, recovery, notes, data table, timeline, and disclosure;
- Markdown narrative fields, never model-authored HTML or CSS.

The Head Coach chooses content hierarchy and semantic component intent. React maps that intent to a bounded component catalog. An optional UI Composer may reorganize presentation only when it preserves the artifact semantic hash; it cannot alter coaching facts or prescriptions.

Stored v1 artifacts remain readable through their versioned historical renderers. New generation and mutation paths emit v3. Unknown schema versions fail visibly instead of being guessed.

## Validation, repair, and failure

Pydantic structured output is the runtime boundary. Invalid model output is returned to the responsible model for a bounded repair attempt through `ToolStrategy`. Deterministic code may validate identity, dates, schemas, authorization, idempotency, and mutation conflicts.

There is no rule-authored coaching fallback. If repair is exhausted, the run fails visibly, sanitized diagnostics are recorded, and the previous canonical artifact remains untouched.

## Mutation contract

The model may return proposal operations but cannot write an active plan. Services dispatch operations by the active artifact's `schema_version`, build a before/after preview, and persist the proposal against the expected plan version. Only explicit acceptance applies it; stale versions fail with a conflict, and retries remain idempotent.

Initial or full plan generation commits the Season Strategy, 28-day Execution Plan, Decision Ledger events, usage linkage, and job result atomically. A clarification pauses through a durable interrupt and resumes the same execution thread.

Generation admission is serialized per owner with a PostgreSQL transaction advisory lock. `pending`, `running`, and `awaiting_input` all retain the generation slot. Resume idempotency binds the request key to an answer hash; terminal state retains only the key-plus-hash receipt. If checkpoint finalization fails after the domain transaction commits, the committed job and matching `source_job_id` plan rows remain authoritative and cannot be rewritten as failed.

## Observability contract

Product progress uses semantic lifecycle events such as understanding context, designing strategy, reviewing constraints, awaiting input, building the execution block, and saving the plan. Traces may contain sanitized run metadata, tool names, artifact IDs, token/cost totals, and validation outcomes. They must not contain credentials, provider tokens, raw private context, or hidden reasoning.

## Source files

- Shared agent factory and profiles: `services/ai/head_coach/agent.py`, `run_profiles.py`
- Durable execution: `services/ai/head_coach/graph.py`, `checkpointing.py`
- Canonical artifacts: `services/ai/head_coach/artifacts.py`
- Proposal validation: `services/ai/coach/schemas.py`, `patch_apply.py`
- API mutation boundary: `api/services/coach_turn.py`, `coach_patch_ops.py`
- Planning lifecycle: `api/services/plan_generation_lock.py`, `analysis_resume.py`, `worker/tasks.py`
- Versioned React rendering: `web/app/src/components/plan-viewer/versioned/`
