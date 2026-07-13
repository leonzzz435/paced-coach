---
date: 2026-07-13
topic: athlete-first-oss-release
---

# Athlete-First OSS Release

> **Superseded connector decision (2026-07-13):** v2.2.0 ships without Strava, WHOOP, daily sync, or weekly recap. References below to optional connectors record the original requirements discovery; the provider-free decision in `agents_docs/roadmap/decision_log.md` governs implementation and launch copy.

## Problem Frame

paced.coach has evolved from a Garmin-connected AI coach experiment into a complete local-first coaching application. The current product is already useful without connected training platforms, but its public message and release materials do not yet make that strength unmistakable.

The first polished open-source release is for technically confident, self-coached endurance athletes who are willing to run a local app and provide an LLM API key. They should understand that the product coaches from their profile, goals, competitions, constraints, and training availability. Strava and WHOOP can enrich that context, but they are not prerequisites for receiving a useful plan or coaching support.

## Requirements

**Product Promise**

- R1. Public positioning must lead with paced.coach as a powerful AI endurance coach, not as a data connector, dashboard, or developer showcase.
- R2. The recurring product message must make the boundary explicit: **no wearable required**. Strava and WHOOP are optional context enhancements.
- R3. Product copy must not imply that the coach works without information. It must explain that the baseline coaching context comes from athlete-provided profile, goals, competitions, constraints, training history when available, and weekly availability.
- R4. Technical architecture and local data ownership must support the product story without displacing athlete value from the headline.

**First-Use Experience**

- R5. After completing local setup, a new user must be able to enter the minimum useful athlete context and generate a personal season roadmap plus a living 28-day training block without connecting Strava or WHOOP.
- R6. The generated plan must lead naturally into an ongoing coach conversation so the user can ask questions and discuss or adapt the plan.
- R7. The optional connector path must be visibly secondary and must explain the additional context each provider contributes without suggesting that disconnected coaching is inferior or incomplete.
- R8. A synthetic demo and current screenshots must let prospective users inspect the dashboard, calendar, plan, and coach experience without exposing private athlete data.

**Release Quality**

- R9. The public release must provide a reproducible local happy path, clear prerequisites, honest AI limitations, and troubleshooting guidance appropriate for technically confident users. The first-use path must handle missing prerequisites, insufficient athlete context, failed plan generation, and disconnected or failing optional providers without implying that a provider connection is mandatory.
- R10. Before publication, the repository must pass its backend and frontend verification suites and the public-release audits for tracked and historical secrets, private athlete data, and generated artifacts. Audit evidence must be recorded without printing secret values or private data into logs or release materials.
- R11. Legal and privacy content must remain factual local-first operational drafts. Unresolved facts must remain explicit, and publishing the GitHub release or beginning broader promotion must wait for the external legal review required by the repository's legal guardrails.
- R12. The release must include clear known limitations and must not imply medical, diagnostic, fully autonomous, or production-hosted-service capabilities. The no-login application must remain bound to loopback by default and must not be presented as safe for direct public-network exposure.

**Launch Narrative and Distribution**

- R13. The launch story must frame paced.coach as the evolution of the earlier Garmin AI Coach: a good coach should not depend on one wearable or training platform.
- R14. The GitHub release and a clean-install smoke test must be completed before broader promotion begins.
- R15. The follow-up Medium article and Reddit posts must lead with the athlete problem and the no-wearable-required coaching result, then use the complete local-first end-to-end architecture as supporting proof and a secondary technical story.
- R16. Launch materials must show the concrete product experience: athlete setup, season roadmap, 28-day calendar, dashboard, and continuing coach chat.

## Success Criteria

- A technically confident athlete can follow the public setup from a clean environment and reach a generated season roadmap and 28-day plan without connecting a provider.
- The same athlete can continue from the plan into a useful coach conversation.
- A reader can explain the product in one sentence without describing it as a Garmin, Strava, or WHOOP application.
- README, landing/demo surfaces, screenshots, release notes, Medium article, and Reddit posts consistently communicate **no wearable required** and present connectors as optional.
- Release verification and public-release audits have recorded passing evidence, with any accepted limitations disclosed.
- The public repository contains no secrets, private athlete data, or unreviewed generated personal artifacts.
- Setup instructions and launch materials do not encourage exposing the no-login application beyond the local machine.
- External legal review has been completed before the GitHub release and broad Medium and Reddit promotion, with required corrections or disclaimers incorporated.

## Scope Boundaries

- No hosted multi-user service, public no-login deployment, managed authentication, or payment flow is part of this release.
- No German localization is required for launch.
- No new wearable or training-platform connector is required.
- Strava and WHOOP do not need to become the primary onboarding path or the primary launch story.
- One-click installation for nontechnical users is not required; setup should be dependable and well documented for the stated technical audience.
- The release does not require resolving every long-term LangGraph or plan-first technical-debt item.
- Broad promotion does not begin until the release and clean-install smoke test are complete.

## Key Decisions

- **Athlete-first positioning:** The durable value is the coaching loop; the implementation stack is evidence that the product is real and complete.
- **Technically confident initial audience:** This keeps local-first ownership practical without expanding the release into a consumer installer project.
- **No wearable required:** This is more direct and positive than “works without connected data” or “manual-first coaching.”
- **Personal plan as first success:** The season roadmap and 28-day block demonstrate coaching value more clearly than beginning with an empty chat or demo-only experience.
- **Evolution narrative:** The Garmin origin supplies a credible reason for the product direction without making Garmin the current identity.
- **Release before promotion:** Public storytelling should point to a tested artifact rather than create pressure around an unfinished release candidate.

## Dependencies / Assumptions

- Users in the initial audience can install local prerequisites, run the documented stack, and configure an LLM API key.
- Useful disconnected coaching depends on users providing sufficiently rich and accurate context.
- Provider integrations remain read-only context sources and failures remain non-blocking for manual planning.
- Legal review and any unresolved business facts may constrain how broadly the release is promoted; unresolved items must be disclosed rather than silently assumed complete.

## Outstanding Questions

### Deferred to Planning

- [Affects R9, R10][Needs research] Which clean environments and operating systems must be exercised for the release smoke-test matrix?
- [Affects R5, R9][Needs research] What exact minimum athlete context is required by the current product to generate a useful provider-free plan, and does the UI communicate missing context clearly?
- [Affects R10][Needs research] Which repository-history and generated-artifact audit commands provide sufficient recorded evidence for the public release gate?
- [Affects R14][Technical] Should the release use the existing `2.2.0` version or introduce a new release version after final changes?
- [Affects R15][Needs research] Which relevant subreddits permit project posts, and what self-promotion rules apply at launch time?

## Next Steps

-> `/ce:plan` for structured release planning.
