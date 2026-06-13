# AI Coaching Limitations

paced.coach is training-support software, not medical care.

## What The Coach Can Do

- Turn your saved profile, goals, constraints, races, and plan history into coaching context.
- Generate a season roadmap and a 28-day execution block.
- Answer plan questions and propose adaptations.
- Use Strava and WHOOP context when you intentionally configure and connect those providers.

## What The Coach Must Not Claim

When Strava/WHOOP are not connected, outputs must not claim knowledge of:

- recent activity history
- training load or compliance
- sleep, HRV, recovery, or readiness trends
- injury status beyond what you explicitly entered

When connected data is stale, partial, or unavailable, the coach should say so and reason with uncertainty.

## Human Responsibility

You are responsible for deciding whether a session is safe. Stop or modify training if you feel pain, illness, dizziness, unusual fatigue, or other warning signs.

Consult a qualified professional before making medical, rehabilitation, nutrition, or high-risk training decisions.

## LLM Data Boundary

Plan generation and coaching send relevant prompt context to the configured LLM provider. That context can include profile details, goals, constraints, plan content, coach history, and connected training data.

Do not enter information you do not want sent to your configured LLM provider.

## Local-First Boundary

The default app stores data locally and has no hidden telemetry requirement. External network paths are:

- the configured LLM provider
- Strava, if OAuth is configured and connected
- WHOOP, if OAuth is configured and connected
- LangSmith, if `LANGSMITH_API_KEY` is configured

Leave optional integrations unset if you do not want those paths.
