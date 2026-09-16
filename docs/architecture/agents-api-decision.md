# Agent runtime decision

Date: 2026-09-16. Scope: the next local-first release.

## Decision

Keep the existing LangGraph workflow and local PostgreSQL checkpoints. Add
GPT-6 Astra through the central model configuration, independently of a harness
migration. The Agents API remains a separate experiment, not a release dependency.

The [Agents API architecture](https://developers.openai.com/api/docs/guides/agents-api/architecture)
places the agent harness and session at OpenAI. An environment can be absent,
OpenAI-hosted, or self-hosted; self-hosting the environment does not self-host the
harness. Application function tools still require a caller to execute them and
return results. These distinctions matter for this app's local execution-state
contract.

## What the application already owns

| Requirement | Current implementation | What a replacement must demonstrate |
| --- | --- | --- |
| Local durable clarification | Owner-scoped PostgreSQL checkpoints; same job resumes after restart | Durable answer identity, recovery after disconnect, explicit remote retention |
| Canonical plan ownership | Active plans, decision event and terminal job committed together | No direct model writes; preserve the same domain transaction |
| Duplicate delivery | Owner locks, execution claims and idempotency receipts | Replayed events cannot duplicate versions, usage or changes |
| Athlete approval | Coach proposals precede material plan changes | Approval is checked by application code at mutation time |
| Full declared context | Profile, race calendar, active plans, history and memory | Demonstrate that session compaction does not discard material constraints |
| Failure visibility | Job status, progress and explicit interruption | Distinguish completed, failed, cancelled and waiting turns |

These are acceptance criteria, not claims that the Agents API cannot satisfy
them. A managed harness could reduce orchestration code. It would also introduce
remote session lifecycle, event reconciliation and deletion work. The current
release has no feature that requires a shell or cloud sandbox.

## Experiment boundary

Use only a synthetic athlete and `environment.type=none`, without repository
files, personal context, production credentials in tools, or database mutation
tools. Confirm access separately from Responses API access. Save the actual turn
outcome; an idle session alone does not prove success. Delete the experimental
session after collecting evidence.

The [official quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart)
documents the beta namespace, required permissions, turn completion events and
session deletion. A successful smoke test would establish API compatibility,
not coaching quality, cost superiority or production readiness.

Revisit migration only with a concrete capability gap and a comparison covering
clarification/restart, interrupted tools, duplicate events, rejected proposals,
deletion, missing athlete evidence, latency and measured usage. Keep those
results separate from deterministic contract tests.

## Observed smoke check

On 2026-09-16, OpenAI Python 3.14.1 completed one synthetic Astra turn with no
environment or application tools. The prompt specified a half marathon on a
Sunday but only 40 minutes of Sunday availability. The response asked how much
time was available on race day instead of inventing an exception. The completed
turn and saved message were both checked; the experimental session was deleted
successfully. Elapsed time was 25.74 seconds for this one request sequence.

This establishes access and the basic session lifecycle. It does not test
function-call recovery, app ownership, plan publication, or relative performance.
The production LangGraph flow is tested separately with a complete synthetic
athlete, a real pause/restart/resume, and plan persistence.
