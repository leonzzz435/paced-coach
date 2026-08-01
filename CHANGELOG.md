# Changelog

## 2.2.0 - Unreleased

- Turned paced.coach into a complete local-first endurance coaching app: describe your training context, generate a season roadmap and 28-day execution block, then keep working with the coach in chat.
- Made the useful first run wearable- and training-data-provider-free. An OpenAI API key and athlete-declared profile, goals, availability, and constraints are enough; no wearable is required.
- Replaced the provider-shaped multi-expert planning graph with one durable Head Coach runtime for initial plans, plan refreshes, coach chat, recap, daily adaptation, and memory extraction.
- Added schema-v3 Season Strategy and 28-day Execution artifacts with rich semantic React components, bounded model self-repair, durable clarification/resume, and version-safe proposal previews.
- Added PostgreSQL LangGraph checkpoints with owner-scoped execution IDs, restart-safe resume, commit-once publication, and bounded terminal retention.
- Made the compact 28-day calendar the primary plan surface while keeping coach rationale and rich semantic guidance available through progressive disclosure.
- Shipped v2.2.0 provider-free: external training-data OAuth, automated source sync, and import surfaces are not part of the public runtime.
- Reset the public repository to an open-source baseline without hosted auth, payment, deployment, private athlete data, or generated personal artifacts.
- Replaced historical database migrations with a local-first baseline and an additive checkpoint-table upgrade for fresh installs.
- Removed the hand-written tool loop, dedicated deep-reasoning formatter agents, unsafe plotting tools, and the `legacy_v1` generation fallback.
- Updated DOMPurify and js-yaml and retained the full frontend, backend, build, and version-governance CI gates.
