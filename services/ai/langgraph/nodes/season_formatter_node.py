import logging
import uuid
from datetime import datetime

from services.ai.ai_settings import AgentRole
from services.ai.langgraph.schemas.ui_block_sanitizer import sanitize_season_plan
from services.ai.langgraph.schemas.ui_blocks import LlmSeasonPlan, UiSeasonPlan
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState
from services.ai.langgraph.utils.output_helper import extract_agent_content
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff

from .node_base import create_cost_entry, execute_node_with_error_handling, log_node_completion
from .plan_formatter_node import SEASON_FORMATTER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def season_formatter_node(state: TrainingAnalysisState) -> dict:
    logger.info("Starting season formatter node")

    if state.get("season_plan_needs_formatting") is False and state.get("season_plan_blocks") is not None:
        logger.info("Season formatter: skipping (season_plan_needs_formatting=False and blocks already present)")
        return {}

    season_plan_md = extract_agent_content(state.get("season_plan"))

    if not season_plan_md:
        logger.warning("No season plan markdown to format")
        return {}

    agent_start_time = datetime.now()
    base_llm = ModelSelector.get_llm(AgentRole.PLAN_FORMATTER)
    llm_season = base_llm.with_structured_output(LlmSeasonPlan, method="function_calling")

    async def call_season_formatter():
        return await llm_season.ainvoke(
            [
                {"role": "system", "content": SEASON_FORMATTER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Convert this season plan into a `UiSeasonPlan` object.\n\n"
                        "## Source Markdown\n```markdown\n"
                        f"{season_plan_md}\n```\n\n"
                        "## Priority 1 — Surface fields\n"
                        "- `season_summary_line`: compact banner (under 80 chars), e.g. 'Week 3 of 12 · Aerobic Base'\n"
                        "- `phase.summary`: one sentence per phase for the timeline view\n\n"
                        "## Priority 2 — Structure\n"
                        "- Extract phases with dates. Each phase: title, dates, summary, and concise blocks that preserve key rationale, targets, and guardrails.\n"
                        "- Keep global notes compact, but retain race calendar, principles, and guardrails that downstream agents may need.\n\n"
                        "## Priority 3 — Custom planning instructions\n"
                        "- Preserve explicit creative constraints, challenge requests, or run-specific planning instructions from the source markdown.\n"
                        "- If they affect the whole season, keep them in global notes. If they affect a phase, keep them in that phase's blocks.\n\n"
                        "## Priority 4 — Creative challenge thread\n"
                        "- Preserve named weekly micro-challenges and larger signature/breakthrough challenges, including purpose, timing window, progression target, and safety guardrails.\n"
                        "- If a signature challenge spans multiple phases, keep the overview in global notes and phase-specific stepping stones in phase blocks.\n"
                        "- Do not flatten distinctive challenge names into generic training notes or shrink big challenges into small novelty tasks.\n\n"
                        "## Formatting\n"
                        "- Use `.tag--a` / `.tag--b` for race priorities, `.focus` pills for phase profiles.\n"
                        "- Use `.big-stat` for volume targets. Keep blocks lean.\n"
                        "- Use `inline` disclosure mode by default. `collapsible` only for dense content."
                    ),
                },
            ]
        )

    async def node_execution():
        llm_result = await retry_with_backoff(call_season_formatter, AI_ANALYSIS_CONFIG, "Season Plan Formatting")

        season_plan_blocks = UiSeasonPlan(
            **llm_result.model_dump(),
            plan_id=f"season_{state.get('user_id', 'user')}_{uuid.uuid4().hex[:10]}",
            athlete_name=state["athlete_name"],
            created_at=datetime.now().isoformat(),
        )

        execution_time = (datetime.now() - agent_start_time).total_seconds()
        log_node_completion("Season formatting", execution_time)

        return {
            "season_plan_blocks": sanitize_season_plan(season_plan_blocks),
            "costs": [create_cost_entry("season_formatter", execution_time)],
        }

    return await execute_node_with_error_handling(
        node_name="Season formatter",
        node_function=node_execution,
        error_message_prefix="Season formatting failed",
    )
