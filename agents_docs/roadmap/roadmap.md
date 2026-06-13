# Roadmap

This doc changes slowly. It describes product direction for the local-first open-source app.

## Product Pillars

1. **Plan-first coaching loop**: season roadmap, living 28-day block, coach proposals, daily update, weekly recap.
2. **Local-first ownership**: one local owner by default, no account service required for the first useful run.
3. **Provider-optional context**: manual profile and competitions work alone; Strava and WHOOP add richer context when configured.
4. **Confidence-aware AI coaching**: the coach should state limits clearly when data is sparse or disconnected.
5. **Agent-native architecture**: agents receive rich context and make coaching judgments; deterministic code handles infrastructure, validation, and persistence.
6. **Mobile-ready web app**: responsive PWA first, native wrapper only if real usage justifies it.

## Positioning

Publicly, paced.coach should be presented as:

**A local-first AI endurance coach for self-coached athletes.**

The public promise should center on:

- building a season roadmap,
- maintaining a living 28-day training block,
- adapting the plan when life changes,
- and using connected training history when available.

Avoid positioning the product as:

- a connector-specific product,
- a medical or diagnostic product,
- a generic health-data dashboard,
- or a hosted service that requires accounts before it is useful.

## Phases

### Phase 1 — Clean OSS Baseline

- Keep setup to `make start` or equivalent local commands.
- Keep only source, public docs, tests, and synthetic demo assets tracked.
- Keep database setup on one local-first baseline migration.
- Keep CI focused on lint, type-check, tests, and frontend build.

### Phase 2 — Better Cold Start Planning

- Improve profile, goals, constraints, and recent-training intake.
- Make first plans useful without connected providers.
- Keep no-provider confidence boundaries explicit in generated plans and coach responses.

### Phase 3 — Connected Coach Context

- Make Strava activity history and WHOOP readiness inputs feed provider-neutral context.
- Keep provider data read-only in v1.
- Preserve source snapshots enough to debug connector parsing.
- Make provider failures non-blocking for manual planning.

### Phase 4 — Coach Loop Quality

- Improve proposal quality, daily update usefulness, and weekly recap follow-up.
- Keep one coherent coach surface across plan, recap, and adaptations.
- Treat full plan generation as recalibration, not the only interaction pattern.

### Phase 5 — Mobile And Internationalization

- Keep the PWA reliable on mobile.
- Add German UI and AI-response support before broader localization.
- Consider a native wrapper only after mobile usage proves the need.

## Technical Debt Backlog

### Plan-First Migration

The current analysis/planning graph still carries some `metrics / physiology / activity` workflow shape.

Target:

- provider-neutral sufficiency gating,
- canonical activity history,
- plan-first orchestration,
- proposal-driven execution coaching.

### LangGraph Agent Loop

`handle_tool_calling_in_node` is a hand-rolled agentic loop. It works, but tool executions are not ideal for tracing.

Target:

- Evaluate LangGraph's `create_react_agent` for recap and coach agents.
- Keep structured-output validation after the agent loop.
- Preserve existing behavior until replacement tests are strong.
