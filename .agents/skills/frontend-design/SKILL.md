---
name: frontend-design
description: Choose a deliberate visual direction for design-heavy web, dashboard, marketing, and onboarding tasks. Use when deciding layout, hierarchy, typography, color, charts, or motion in web/.
---

# Frontend Design

Use this skill when the task is design-heavy rather than purely mechanical: UI direction, layout polish, landing pages, dashboard hierarchy, empty states, onboarding flows, chart selection, or typography/color decisions in `web/`.

## Inputs to read

- [`AGENTS.md`](../../../AGENTS.md)
- [`web/AGENTS.md`](../../../web/AGENTS.md) when touching `web/**`
- [`references/directions.md`](references/directions.md)
- [`references/anti-patterns.md`](references/anti-patterns.md)
- [`references/color.md`](references/color.md) for palette decisions and surface-specific color families
- [`references/typography.md`](references/typography.md) for font behavior, hierarchy, and pairings
- [`references/pre-delivery-checklist.md`](references/pre-delivery-checklist.md)
- [`references/dashboard-ui.md`](references/dashboard-ui.md) for KPI-, analytics-, or chart-heavy surfaces

## Scope routing

- **`web/app` product surfaces**: default to `product-premium` or `dashboard-technical`
- **`web/app` public setup, docs, or onboarding surfaces**: consider `editorial` or `campaign`
- Do not treat every frontend task as a design-direction task. Small bug fixes, wiring changes, and routine component edits do not need this skill.

## Workflow

1. **Classify the surface**
   - `product-ui`
   - `dashboard`
   - `marketing`
2. **Pick one dominant direction**
   - Use [`references/directions.md`](references/directions.md).
   - Name the chosen direction explicitly in your reasoning.
   - If the user asked for exploration, present at most two viable directions, not a style buffet.
3. **Respect local constraints**
   - In `web/**`, preserve the established local-first coaching language and Next.js/Tailwind patterns.
   - Never bypass `schema_version` routing or versioned renderers for plan views.
4. **Implement with strong hierarchy**
   - Start from the primary user question or story beat.
   - Use type scale, spacing, and contrast to establish a single dominant focal point.
   - Use [`references/color.md`](references/color.md) and [`references/typography.md`](references/typography.md) to stay product-aligned while still improving the visual system.
   - Use motion sparingly in app UI and only when it reinforces hierarchy or state.
   - For dashboards, pick the chart from the question being answered, not from what looks fancy.
5. **Review against failure modes**
   - Use [`references/anti-patterns.md`](references/anti-patterns.md) before finalizing.
   - Run [`references/pre-delivery-checklist.md`](references/pre-delivery-checklist.md) before handoff.

## Hard rules

- Do not turn product coaching screens into campaign posters.
- Do not hide weak hierarchy behind gradients, glass, or animation.
- Do not add visual complexity without clarifying the main action, metric, or story beat.
- Do not introduce arbitrary new visual systems when the existing one only needs a more deliberate evolution.

## Output bar

- Say which direction you chose and why.
- Keep the result intentional, not generic.
- For product UI, evolve the existing language.
- For marketing work, allow more surprise, but keep the message obvious quickly.
