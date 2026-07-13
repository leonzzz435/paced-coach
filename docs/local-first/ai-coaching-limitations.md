# AI Coaching Limitations

paced.coach is training-support software, not medical care.

## What The Coach Can Do

- Turn your saved profile, goals, constraints, races, and plan history into coaching context.
- Generate a season roadmap and a 28-day execution block.
- Answer plan questions and propose adaptations.

No wearable is required. A supported LLM key plus athlete-declared training history, goals, availability, constraints, and feedback can support a specific, useful plan. Version 2.2.0 does not connect to external training-data providers.

## What The Coach Must Not Claim

Outputs must not claim knowledge of information the athlete did not provide, including:

- recent activity history
- training load or compliance
- sleep, HRV, recovery, or readiness trends
- injury status beyond what you explicitly entered

When athlete-provided context is stale, partial, or unavailable, the coach should say so and reason with uncertainty.

## Human Responsibility

You are responsible for deciding whether a session is safe. Stop or modify training if you feel pain, illness, dizziness, unusual fatigue, or other warning signs.

Consult a qualified professional before making medical, rehabilitation, nutrition, or high-risk training decisions.

## LLM Data Boundary

Plan generation and coaching send relevant prompt context to the configured LLM provider. That context can include profile details, goals, constraints, plan content, and coach history.

Do not enter information you do not want sent to your configured LLM provider.

## Local-First Boundary

The default app stores data locally and has no hidden telemetry requirement. External network paths are:

- the configured LLM provider
- LangSmith, if `LANGSMITH_API_KEY` is configured

Leave LangSmith unset if you do not want the optional tracing path.
