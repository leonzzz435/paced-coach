from __future__ import annotations

from typing import Any

from api.services.ongoing_tools import OngoingToolRegistry
from services.ai.ai_settings import AgentRole
from services.ai.langgraph.nodes.tool_calling_helper import handle_tool_calling_in_node
from services.ai.model_config import ModelSelector
from services.ai.recap.schemas import WeeklyRecapNarrative
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff
from services.ai.utils.structured_output import coerce_structured_output

RECAP_SYSTEM_PROMPT = """You are an elite endurance coach writing weekly recaps.

Principles:
- Be direct, concrete, and useful. No generic motivational filler.
- Use available tools to fetch only the data needed.
- Evaluate planned vs actual training with nuanced coaching judgment.
- Fetch at least 28 days of training load history to evaluate multi-week progression, not just this week in isolation.
- Fetch upcoming competitions. Frame everything relative to the target event and time remaining. If no target event exists, frame around general fitness progression.
- Inspect the deterministic `evidence_profile` and `claims_policy` from tool outputs before making readiness or activity-completeness claims.
- If readiness guidance is proxy-only, keep the recap load/execution-oriented and say recovery certainty is limited.
- You may propose plan patch ops only when adaptation is clearly warranted.
- If adaptation is not warranted, keep optional_proposal_ops empty.

Output contract:
- Return structured output matching the schema only.
- Use compact, scannable HTML blocks.
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
        "Use tools to gather plan, actuals, competitions, training load (28+ days), and recovery/readiness signals.\n",
        "Before making claims, inspect evidence_profile and claims_policy in the retrieved tool payloads.\n",
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
    tool_registry: OngoingToolRegistry,
    week_start_iso: str,
    week_end_iso: str,
    trigger_source: str,
    previous_follow_up: dict | None = None,
    invoke_config: dict[str, Any] | None = None,
) -> WeeklyRecapNarrative:
    tools = tool_registry.create_langchain_tools()
    base_llm = ModelSelector.get_llm(AgentRole.WEEKLY_RECAP)
    llm_with_tools = base_llm.bind_tools(tools) if tools else base_llm
    llm_with_structure = base_llm.with_structured_output(WeeklyRecapNarrative)

    base_messages = [
        {"role": "system", "content": RECAP_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_recap_user_prompt(
                week_start_iso=week_start_iso,
                week_end_iso=week_end_iso,
                trigger_source=trigger_source,
                previous_follow_up=previous_follow_up,
            ),
        },
    ]

    async def call_recap():
        return await handle_tool_calling_in_node(
            llm_with_tools=llm_with_tools,
            messages=base_messages,
            tools=tools,
            max_iterations=12,
            final_output_llm=llm_with_structure,
            invoke_config=invoke_config,
        )

    response = await retry_with_backoff(call_recap, AI_ANALYSIS_CONFIG, "Weekly Recap Agent")
    return coerce_structured_output(response, WeeklyRecapNarrative)
