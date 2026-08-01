from __future__ import annotations

import json
from typing import Any

from services.ai.daily.schemas import DailyUpdateNarrative
from services.ai.head_coach.agent import build_head_coach_agent, invoke_head_coach_agent
from services.ai.head_coach.run_profiles import get_run_profile
from services.ai.head_coach.schemas import RunProfileName
from services.ai.head_coach.tool_policy import HeadCoachToolRegistry, build_profile_tools

DAILY_SYSTEM_PROMPT = """Perform today's coaching check as the athlete's persistent Head Coach.

Coaching Lens — reason through these concepts, not as formulas, but as the way an experienced coach thinks:
- Readiness is multi-dimensional. Reason from the athlete's subjective check-in, declared health context, plan, and coaching history.
- Distinguish between pre-competition nerves and genuine fatigue by asking about lived symptoms and context when evidence is insufficient.
- Recovery debt accumulates non-linearly: two moderate days of under-recovery are manageable, but three or more can cascade into overreaching.
- Session timing within the microcycle: a hard day following a rest day is expected; a hard day following two hard days requires strong readiness signals.
- Athlete momentum: sometimes maintaining the training rhythm matters more than perfect readiness numbers, especially for consistency-building phases.
- Subjective athlete check-ins are first-class coaching evidence; do not invent device measurements.
- Athlete standards matter: if the current plan has explicit volume floors or the athlete normally tolerates meaningful volume, do not treat short sessions as the default build stimulus.

Principles:
- Your goal is to evaluate if today's planned training is still appropriate given athlete-declared context and today's explicit completion status.
- Start from the active plan, its completion state, athlete check-in, calendar context, and coach history.
- Use tools to fetch the current active weekly plan to see exactly what blocks are scheduled.
- Determine if today's training is already done. The plan's `is_completed` state is authoritative local evidence; optional recent activities may add evidence but their absence never proves non-completion.
- If athlete-declared readiness is compromised by sickness, pain, or sustained poor sleep, propose appropriate Plan Patch Operations. Protect the athlete.
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
- `today_focus_blocks` should use compact semantic blocks with Markdown content for deterministic rendering at the top of the dashboard. Never emit raw HTML or CSS.
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
        "The athlete-owned local context is the ground truth for this run.",
        "1. Fetch the active weekly plan to see what is scheduled today.",
        "2. Read the athlete profile, season strategy, competition context, and coach history when useful.",
        "3. Reconcile the athlete check-in with the plan without inventing device metrics or completion evidence.",
        "4. Evaluate if today's plan is optimal. If not, generate CoachPatchOps to shift or modify it.",
        "5. Write today_focus_blocks that make the assessment and next action concrete.",
        "6. Populate dashboard_kpis only with claims supported by local athlete-owned context.",
    ]

    if athlete_check_in:
        parts.extend(
            [
                "",
                "Athlete subjective check-in for today:",
                athlete_check_in,
                "",
                "Use this check-in as first-class context. Reconcile it with the current plan, declared constraints, and the next key session before changing the plan.",
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
    tool_registry: HeadCoachToolRegistry,
    target_date_iso: str,
    trigger_source: str,
    athlete_check_in: str | None = None,
    prefetched_recovery_readiness: dict | None = None,
    prefetched_weekly_plan: dict | None = None,
    invoke_config: dict[str, Any] | None = None,
) -> DailyUpdateNarrative:
    profile = get_run_profile(RunProfileName.DAILY_ADAPTATION)
    tools = build_profile_tools(profile, tool_registry=tool_registry)
    agent = build_head_coach_agent(
        profile_name=profile.name,
        response_schema=DailyUpdateNarrative,
        tools=tools,
        task_instructions=DAILY_SYSTEM_PROMPT,
        name="daily_adaptation",
    )
    return await invoke_head_coach_agent(
        agent=agent,
        user_prompt=_build_daily_user_prompt(
            trigger_source=trigger_source,
            target_date_iso=target_date_iso,
            athlete_check_in=athlete_check_in,
            prefetched_recovery_readiness=prefetched_recovery_readiness,
            prefetched_weekly_plan=prefetched_weekly_plan,
        ),
        response_schema=DailyUpdateNarrative,
        invoke_config=invoke_config,
    )
