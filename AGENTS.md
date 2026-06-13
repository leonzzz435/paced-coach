# AGENTS.md — paced-coach

## Mission
You are assisting with an AI service that:
1.  **Reads training context and activity history** from users and connected sources.
2.  **Runs an agentic workflow** (LangGraph) on that context.
3.  **Returns coaching outputs** (season roadmap, 28-day execution block, insights, and adaptations).
**Architecture**: Python Core (FastAPI/Celery/LangGraph) + Next.js frontend, running local-first by default.

## Repo Topology
-   **Local-first app**: Web app (`web/`), API (`api/`), worker (`worker/`), AI services (`services/ai/`), and local Docker/Pixi/npm tooling.
-   **Public release gate**: Do not publish until secret/history/generated-data/workflow audits are complete.
**Hard Rule**: Never commit secrets, local env files, private athlete data, or generated artifacts that have not passed the public-release audit.

## Global Contracts
### 1. Branch Strategy
-   `main` = stable public baseline.
-   `feat/name` = Feature branches.

### 2. Secrets & Config
-   **Strict Zero-Trust**: No secrets in code, logs, or comments.
-   **Environment Variables**: Use `.env` (gitignored). Refer to `.env.example`.
-   **Rotation**: Rotate compromised keys immediately via the Platform Dashboard.

### 3. Verification Defaults
Before submitting any change, run the **Definition of Done** for the affected scope:
-   **Python**: `pixi run ruff-fix` && `pixi run type-check` && `pixi run test`
-   **Frontend**: `npm run lint` && `npm run build`

## Triage & Routing (Start Here)
Before starting a complex task:
1.  **Identify the Scope**: Is this `web`, `api`, `worker`, `services/ai`, docs, or local ops?
2.  **Read the Scoped AGENTS.md**: e.g. `api/AGENTS.md`.
3.  **Activate Skills**: Use `repo-router` logic to pick the right local skills for the touched paths.
4.  **Legal Pages**: Keep `/impressum`, `/privacy`, `/terms`, `/support`, and `/delete` factual, local-first, and marked as operational drafts rather than legal advice.
5.  **Check Critical Paths**: If touching data migrations, local-owner/data-preservation code, secrets, or no-login network exposure, **ASK FIRST**.
6.  **Wrap-up / Handoff**: For end-of-session closeout, handoff drafting, or repeated-correction promotion, activate `session-wrap-up`.
7.  **Design-heavy UI**: For visual direction, dashboard hierarchy, landing pages, or onboarding flows, activate `frontend-design`.

## Skill Source Of Truth
-   Codex skills live directly under `.agents/skills/` and scoped skill directories such as `web/.agents/skills/`.
-   There is no separate sync/build step for skills.
-   Edit the live skill file directly when changing skill instructions.
-   Keep repo-wide skills in `.agents/skills/` and scope-specific skills in the nearest `*/.agents/skills/` directory.

## Planning & Roadmap (Keep Current)

This repo uses a lightweight planning system under `agents_docs/roadmap/`.

- **Near-term execution:** `agents_docs/roadmap/now.md` (next 7–14 days)
- **Longer-term direction:** `agents_docs/roadmap/roadmap.md` (3–6 months)
- **Key decisions:** `agents_docs/roadmap/decision_log.md`

When a task materially changes priorities, scope, milestones, or delivery dates, propose an update to these docs (or ask the user to confirm the update) so the roadmap stays consistent with reality.

## UI Schema Versioning
- **Contract-first**: UI rendering must branch on `schema_version`.
- **Versioned renderers** live in `web/app/src/components/plan-viewer/versioned/`.
- **Fixtures** should be versioned (e.g., `web/app/src/lib/demo/fixtures/v{n}/`).

## Review Guidelines
When performing a review:
1.  **Check Scope**: Is this a `web`, `api`, or `infra` change? Apply scoped rules.
2.  **Security First**: Scan for secrets, PII logging, and auth bypasses.
3.  **Performance**: Check for N+1 queries or blocking I/O in async paths.
4.  **Verification**: Did the user confirm the tests passed?

### Review Severity Policy
-   **[BLOCKER]**: Security risk, breaking change to valid contract, secret leak. -> **Must Fix**.
-   **[WARN]**: Confusing logic, poor naming, missing coverage, performance risk. -> **Should Fix**.
-   **[INFO]**: Nitpicks, style preference, praise. -> **Optional**.

## Legal Content Guardrails
-   Legal text updates are operational drafts, not legal advice.
-   Keep all business facts exact and consistent across legal pages.
-   If key legal facts are unknown, add explicit placeholders and track follow-ups in `LEGAL_TODO.md`.
-   For material legal changes or public distribution changes, request external legal review before publishing.

## Agent Autonomy Philosophy (AI-Powered Features)

When building features that use LLM agents (coaching, analysis, evaluation, etc.):

### Trust Agent Intelligence
- **Let the agent decide.** Do NOT add deterministic if/else heuristics, scoring thresholds, or formula-based shortcuts that replace the agent's judgment. If you catch yourself writing `if score > X then skip`, stop — that decision belongs to the agent.
- **Full context, always.** Give the agent the richest context available. Do NOT strip, summarize, or pre-filter data to "save tokens." Quality of reasoning depends on complete information. Quality > price.
- **No proxy metrics.** Do not invent deterministic proxy scores (e.g., `load_trend_score`, `readiness_index`) that pre-decide outcomes the agent should reason about.

### Where Determinism IS Appropriate
Deterministic code is correct for **infrastructure concerns**, not reasoning concerns:
- ✅ Schema validation (Pydantic structured output)
- ✅ Deduplication guards (don't emit the same event twice)
- ✅ Rate limiting & circuit breakers
- ✅ Authentication, authorization, quota enforcement
- ✅ Data format normalization (dates, units, casing)
- ❌ "If load is rising, suggest rest" (agent should reason about this)
- ❌ "If no activity in 3 days, trigger alert" (agent should decide relevance)
- ❌ "Summarize activities to 5 bullet points before sending to agent" (send the full data)

### Optimize Infrastructure, Not Intelligence
When reducing costs:
- ✅ Move guards/short-circuits before expensive calls (don't compute what you'll discard)
- ✅ Use appropriate model tiers (no web search for prompts that never search)
- ✅ Parallelize independent work
- ✅ Cache external API responses
- ❌ Strip context to reduce tokens
- ❌ Add heuristic pre-filters that skip agent evaluation
- ❌ Replace agent reasoning with rule-based logic

## Runtime Permissions
-   Codex sandbox, approval, and network permissions are session-specific and may differ from `.codex/config.toml`.
-   Treat `.codex/config.toml` as a conservative project default, not as proof that the current session is restricted.
-   Even with broad local permissions, do not expose the no-login app beyond loopback, publish private data, or commit local env files.

## Completion Report
=== VERIFICATION REPORT ===
Changed Files: [...]
Tests Run: [Command] -> [Result]
Linting: [Command] -> [Result]
Security: [No secrets / Issues]
Async/Performance: [Check]
=== END REPORT ===
