from __future__ import annotations

import json
from typing import Any

from api.services.ongoing_tools import OngoingToolRegistry
from services.ai.ai_settings import AgentRole
from services.ai.daily.schemas import DailyUpdateNarrative
from services.ai.langgraph.nodes.tool_calling_helper import handle_tool_calling_in_node
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff
from services.ai.utils.structured_output import coerce_structured_output

DAILY_SYSTEM_PROMPT = """You are an elite endurance coach performing a daily coaching check.

Coaching Lens — reason through these concepts, not as formulas, but as the way an experienced coach thinks:
- Readiness is multi-dimensional: a single bad night doesn't necessarily mean downgrade. Look at the 3-5 day trend in HRV, sleep, and RHR together.
- Distinguish between pre-competition taper nervousness (elevated RHR, restless sleep) and genuine fatigue. Context matters.
- Recovery debt accumulates non-linearly: two moderate days of under-recovery are manageable, but three or more can cascade into overreaching.
- Session timing within the microcycle: a hard day following a rest day is expected; a hard day following two hard days requires strong readiness signals.
- Athlete momentum: sometimes maintaining the training rhythm matters more than perfect readiness numbers, especially for consistency-building phases.
- Subjective athlete check-ins are real coaching evidence. Use them alongside device data, not below it and not above it.
- Athlete standards matter: if the current plan has explicit volume floors or the athlete normally tolerates meaningful volume, do not treat short sessions as the default build stimulus.

Principles:
- Your goal is to evaluate if today's planned training is still appropriate given recent recovery data and today's completion status.
- Read the deterministic `evidence_profile` and `claims_policy` before making any readiness or activity-completeness claims.
- Use available tools to fetch WHOOP and Strava data from the last few days.
- Treat WHOOP as readiness/recovery evidence and Strava as activity-history/execution evidence.
- If the evidence profile says readiness guidance is proxy-only, do not speak as if HRV, sleep, or resting HR were measured. Coach from recent load/execution and say that recovery certainty is limited.
- Use tools to fetch the current active weekly plan to see exactly what blocks are scheduled.
- Determine if today's training is already done. Check BOTH: the `is_completed` flag in the plan AND actual recent activities via `get_recent_activities`. If a matching activity exists for today (same sport, plausible duration) but `is_completed` is false, treat the session as done. If already trained, do not propose changes for today, but perhaps propose recovery adjustments for tomorrow.
- If readiness is compromised (e.g., tanked HRV, sickness, poor sleep trend), you MUST propose Plan Patch Operations to downgrade or rest. Protect the athlete.
- If readiness is strong and the plan is already optimal, leave `optional_proposal_ops` empty and tell the athlete to execute. Good readiness is not a license to randomly add intensity.
- If readiness is strong, the athlete has usable time, and the weekly/season intent benefits from it, you MAY propose a low-risk adjustment such as easy volume, support work, better timing, or an optional desk-load movement add-on. Protect the next key session and avoid stress stacking.
- If you downgrade or shorten sport-specific training, explain whether the weekly sport-specific volume floor is still protected. When appropriate, propose how to preserve that volume later with easy work instead of silently losing it.
- You can propose changes for as many days ahead as necessary (e.g., pushing hard workouts out 3 days if sick).
- Do NOT generate a whole new plan. Use `optional_proposal_ops` to issue surgical JSON patch operations that modify ONLY the isolated blocks that need to change.
- Do NOT silently override the plan. All changes must go through `optional_proposal_ops` so the user can review and explicitly accept/reject your diff.
- If you emit `optional_proposal_ops` that change session content, keep the workout self-contained: include explicit intensity targets for each lap, rep, work block, recovery block, and cool-down whenever intensity changes.
- Creative challenge handling: if the active plan includes a challenge today, help the athlete execute it intelligently. Do not invent a disruptive challenge unless it clearly fits today's readiness, phase intent, and recovery cost.

Output contract:
- Return structured output matching the schema ONLY.
- `dashboard_kpis` must always contain the KPI strip that should be shown at the top of the dashboard immediately after this sync.
  Use today's freshest evidence to decide that strip.
  If the baseline strip is still correct, restate it explicitly instead of leaving this empty.
  If you mention live recovery or readiness in `today_focus_blocks`, the KPI strip must visibly reflect those same live signals.
- 'today_focus_blocks' should be compact, scannable HTML meant to be displayed at the very top of the user's dashboard today.
- Focus on ACTIONABLE advice for today's session based on today's state. Don't waste space with generic pleasantries.
"""


def _build_daily_user_prompt(
    *,
    trigger_source: str,
    target_date_iso: str,
    athlete_check_in: str | None = None,
    prefetched_recovery_readiness: dict | None = None,
    prefetched_weekly_plan: dict | None = None,
) -> str:
    parts = [
        "Perform the daily coaching update for this athlete.\n",
        f"Target Date: {target_date_iso}\n",
        f"Trigger source: {trigger_source}\n",
        "Deterministic context has already been collected for this run. Treat it as the primary ground truth.",
        "1. Inspect the deterministic evidence_profile and claims_policy in the prefetched bundle or tool outputs before making claims.",
        "2. Fetch recent recovery/readiness evidence for the last few days. Use sleep/HRV/RHR when available; otherwise treat activity-derived stress as proxy-only evidence.",
        "3. Fetch the active weekly plan to see what is scheduled today.",
        "4. Fetch the current analysis if you need to compare today's front-row dashboard metrics against the baseline strip you may want to restate.",
        "5. Read the relevant background context (season plan, recent full analysis run) if you need the big picture.",
        "6. Evaluate if today's plan is optimal. If not, generate CoachPatchOps to shift or modify it.",
        "7. Write the today_focus_blocks to explain your assessment and what they should focus on today.",
        "8. Always populate dashboard_kpis with the KPI strip that should be visible after this sync; if the baseline strip still fits, restate it explicitly.",
    ]

    if athlete_check_in:
        parts.extend(
            [
                "",
                "Athlete subjective check-in for today:",
                athlete_check_in,
                "",
                "Use this check-in as first-class context. Reconcile it with device evidence, recent load, the current weekly plan, and the next key session before changing the plan.",
            ]
        )

    if prefetched_recovery_readiness:
        parts.extend(
            [
                "",
                "Prefetched recovery/readiness bundle (all providers active at run start should appear under `sources`):",
                "```json",
                json.dumps(prefetched_recovery_readiness, ensure_ascii=False, sort_keys=True, indent=2),
                "```",
            ]
        )

    if prefetched_weekly_plan:
        parts.extend(
            [
                "",
                "Prefetched active weekly plan (ground truth for what is currently scheduled):",
                "```json",
                json.dumps(prefetched_weekly_plan, ensure_ascii=False, sort_keys=True, indent=2),
                "```",
            ]
        )

    return "\n".join(parts)


async def generate_daily_update_narrative(
    *,
    tool_registry: OngoingToolRegistry,
    target_date_iso: str,
    trigger_source: str,
    athlete_check_in: str | None = None,
    prefetched_recovery_readiness: dict | None = None,
    prefetched_weekly_plan: dict | None = None,
    invoke_config: dict[str, Any] | None = None,
) -> DailyUpdateNarrative:
    tools = tool_registry.create_langchain_tools()
    base_llm = ModelSelector.get_llm(AgentRole.DAILY_UPDATE)
    llm_with_tools = base_llm.bind_tools(tools) if tools else base_llm
    llm_with_structure = base_llm.with_structured_output(DailyUpdateNarrative)

    base_messages = [
        {"role": "system", "content": DAILY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_daily_user_prompt(
                trigger_source=trigger_source,
                target_date_iso=target_date_iso,
                athlete_check_in=athlete_check_in,
                prefetched_recovery_readiness=prefetched_recovery_readiness,
                prefetched_weekly_plan=prefetched_weekly_plan,
            ),
        },
    ]

    async def call_daily():
        return await handle_tool_calling_in_node(
            llm_with_tools=llm_with_tools,
            messages=base_messages,
            tools=tools,
            max_iterations=12,
            final_output_llm=llm_with_structure,
            invoke_config=invoke_config,
        )

    response = await retry_with_backoff(call_daily, AI_ANALYSIS_CONFIG, "Daily Update Agent")
    return coerce_structured_output(response, DailyUpdateNarrative)
