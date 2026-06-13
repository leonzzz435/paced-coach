# Dashboard UI

Start with the question the user should answer in one glance. Then choose the chart and layout that make that answer obvious.

## Question -> chart mapping

- **How is this changing over time?** -> line chart or area chart
- **How do categories compare right now?** -> horizontal or vertical bar chart
- **How close are we to a target?** -> bullet chart, progress bar, or explicit delta treatment
- **What is this composed of?** -> stacked bar only when the composition matters more than exact comparisons
- **What happened in sequence?** -> timeline, event list, or stepped progression
- **What is the single most important number?** -> stat card with supporting trend or delta, not a chart by default

## Layout order

1. Primary takeaway
2. Supporting trend or comparison
3. Context, breakdown, or explanation

Do not give tertiary breakdowns the same visual weight as the primary takeaway.

## Data density rules

- Use compact chrome; spend visual budget on the data.
- Labels should be readable without hover-only interpretation.
- Use accent color to signal importance or state change, not every trace.
- Show units, time windows, and baselines explicitly.
- Prefer fewer, clearer series over a dense legend nobody can parse.

## Coaching product notes

- Progress, load, readiness, and adherence screens should bias toward trends and deltas, not decorative widgets.
- If a metric has uncertainty or caveats, show the caveat near the metric instead of hiding it in body copy.
- When in doubt, prioritize "what should the user do next?" over showing every available dimension.
