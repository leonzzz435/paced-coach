# Changelog

## Unreleased

## 2.2.0 - 2026-07-13

- Turned paced.coach into a complete local-first endurance coaching app: describe your training context, generate a season roadmap and 28-day execution block, then keep working with the coach in chat.
- Made the useful first run provider-free. A supported LLM key and athlete-declared profile, goals, availability, and constraints are enough; no wearable is required.
- Shipped v2.2.0 provider-free: external training-data OAuth, sync, recap, and import surfaces are not part of the public runtime.
- Reset the public repository to an open-source baseline without hosted auth, payment, deployment, private athlete data, or generated personal artifacts.
- Replaced historical database migrations with a single local-first baseline migration for fresh installs.
- Updated DOMPurify and js-yaml and retained the full frontend, backend, build, and version-governance CI gates.
