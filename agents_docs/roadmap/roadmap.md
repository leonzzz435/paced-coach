# Roadmap

This doc changes slowly. It describes product direction for the local-first open-source app.

## Product Pillars

1. **Plan-first coaching loop**: season roadmap, living 28-day block, coach proposals, daily update, weekly recap.
2. **Local-first ownership**: one local owner by default, no account service required for the first useful run.
3. **Provider-free context**: profile, competitions, constraints, plan history, and coach dialogue form the complete coaching context.
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

- Reconsider external training-data connectors only after a compatible provider contract or written permission is documented.
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

## Architecture Baseline

The provider-shaped `metrics / physiology / activity` fan-out and hand-written agent loop have been retired. Current generation and ongoing coaching use one Head Coach built with LangChain `create_agent`, semantic run profiles, capability-gated tools, durable LangGraph execution, canonical schema-v3 artifacts, and proposal-driven mutation boundaries.

Near-term architecture work should focus on measured quality rather than adding orchestration layers:

- expand provider-free trajectory, safety, and adaptation eval cases;
- calibrate reasoning profiles from quality/latency evidence;
- add a specialist or Deep Agents research path only when an eval demonstrates material value;
- keep optional provider evidence read-only and absent from the tool surface when disconnected;
- retain v1 renderers solely for historical local artifacts while all new generation stays on v3.
