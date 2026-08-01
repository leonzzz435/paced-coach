from __future__ import annotations

from typing import Any

from services.ai.head_coach.agent import build_head_coach_agent, invoke_head_coach_agent
from services.ai.head_coach.run_profiles import get_run_profile
from services.ai.head_coach.schemas import RunProfileName
from services.ai.head_coach.tool_policy import HeadCoachToolRegistry, build_profile_tools
from services.ai.recap.schemas import WeeklyRecapNarrative

RECAP_SYSTEM_PROMPT = """Write the athlete's weekly recap as the persistent Head Coach.

Principles:
- Be direct, concrete, and useful. No generic motivational filler.
- Start from the complete local plan, its completion state, athlete feedback, calendar history, competitions, and coach context.
- Evaluate planned vs completed training with nuanced coaching judgment. Only explicit local completion state and athlete feedback establish what happened.
- Frame the recap relative to the target event and time remaining. If no target event exists, frame around general fitness progression.
- Coach from the local plan, explicit completion state, athlete profile, coach history, and athlete feedback. Never invent sensor measurements or undeclared training.
- You may propose plan patch ops only when adaptation is clearly warranted.
- If adaptation is not warranted, keep optional_proposal_ops empty.

Output contract:
- Return structured output matching the schema only.
- Use compact semantic blocks with Markdown content. Never emit raw HTML or CSS.
- this_week_blocks: what happened this week and what it means (planned vs actual, key sessions, load trends, recovery state).
- looking_ahead_blocks: tactical direction for next week and beyond, framed by race proximity or training phase.
- follow_up_question: end with ONE specific, data-informed question for the athlete. Ask about something the data cannot tell you — how a session felt (RPE vs pace), sleep quality, life stress, injury niggles, motivation. Never ask generic questions like "how do you feel?" — reference specific sessions or patterns you observed.
"""


def _build_recap_user_prompt(
    *,
    week_start_iso: str,
    week_end_iso: str,
    trigger_source: str,
    previous_follow_up: dict | None = None,
) -> str:
    parts = [
        "Create a weekly recap for this athlete.\n",
        f"Week window UTC:\n- start: {week_start_iso}\n- end: {week_end_iso}\n",
        f"Trigger source: {trigger_source}\n",
        "Use the local plan, explicit completion state, athlete profile, and athlete feedback as the complete evidence base.\n",
        "For blocks:\n",
        "- this_week_blocks: what happened and what it means\n",
        "- looking_ahead_blocks: what to do about it, framed by race proximity\n",
        "Only include optional_proposal_ops when changes are clearly needed now.\n",
        "End with a specific follow_up_question for the athlete.",
    ]

    if previous_follow_up:
        question = previous_follow_up.get("question", "")
        response = previous_follow_up.get("response", "")
        if question and response:
            parts.insert(
                3,
                f'\nLast week you asked: "{question}"\n'
                f'Athlete responded: "{response}"\n'
                "Factor this subjective feedback into your analysis.\n",
            )

    return "\n".join(parts)


async def generate_weekly_recap_narrative(
    *,
    tool_registry: HeadCoachToolRegistry,
    week_start_iso: str,
    week_end_iso: str,
    trigger_source: str,
    previous_follow_up: dict | None = None,
    invoke_config: dict[str, Any] | None = None,
) -> WeeklyRecapNarrative:
    profile = get_run_profile(RunProfileName.WEEKLY_RECAP)
    tools = build_profile_tools(profile, tool_registry=tool_registry)
    agent = build_head_coach_agent(
        profile_name=profile.name,
        response_schema=WeeklyRecapNarrative,
        tools=tools,
        task_instructions=RECAP_SYSTEM_PROMPT,
        name="weekly_recap",
    )
    return await invoke_head_coach_agent(
        agent=agent,
        user_prompt=_build_recap_user_prompt(
            week_start_iso=week_start_iso,
            week_end_iso=week_end_iso,
            trigger_source=trigger_source,
            previous_follow_up=previous_follow_up,
        ),
        response_schema=WeeklyRecapNarrative,
        invoke_config=invoke_config,
    )
