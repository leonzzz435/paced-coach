import logging
import uuid
from datetime import datetime

from services.ai.ai_settings import AgentRole
from services.ai.langgraph.schemas.ui_block_sanitizer import sanitize_weekly_plan
from services.ai.langgraph.schemas.ui_blocks import LlmWeeklyPlan, UiWeeklyPlan
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState
from services.ai.langgraph.utils.output_helper import extract_agent_content
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff

from .node_base import create_cost_entry, execute_node_with_error_handling, log_node_completion
from .plan_formatter_node import WEEKLY_FORMATTER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

WEEKLY_FORMATTER_USER_PROMPT_TEMPLATE = """Convert this weekly training plan into a `UiWeeklyPlan` object.

## Source Markdown
```markdown
{weekly_plan_md}
```

## Priority 1 — Surface fields (athlete reads these)
- `plan_brief`: 2-3 sentence Monday-morning coaching message for the block.
- `week.week_theme`: short theme per week ('Build Week 2', 'Recovery', 'Race Week').
- Per day: `readiness_note`, `workout_title`, `icon`, `focus_type`, `focus_color`, `estimated_duration_min`, `estimated_intensity` (set for ALL days including rest).
- `workout_title` must name the actual session (e.g. "Z2 ride + strides", "3x8' LT"), never a generic wrapper like "Session overview" or "Workout details".

## Priority 2 — Day content
- Each non-rest day should usually include a `variant='workout'` block and a `variant='checklist'` block.
- Add extra day blocks or nodes when a single workout/checklist pair would omit meaningful execution detail.
- Rest days: no blocks needed (metadata fields are enough).
- Use `.workout` / `.workout-title` / `.workout-meta` + `.focus` pill.
- Checklists: `.checklist task--{{activity}}`, no `<input>` elements.
- Keep `day_label` compact (<= 32 chars).
- If a workout block uses `title`, make it session-specific or leave it null; do not use generic titles that would be useless on a compact calendar card.
- Preserve segment-level execution detail. If the source session has intervals, laps, reps, or changing segments, show the zone/intensity target for each one inside the day content.
- Do not collapse lap/rep targets into only `workout_title`, `day_label`, or a single `.workout-meta` summary line.
- Prefer `day.blocks` for the primary workout/checklist so the main execution guidance is immediately visible in the calendar side panel. If you use `day.nodes`, keep the main execution node `disclosure_mode="inline"` so the athlete sees lap-by-lap zone targets without extra clicks.
- Use a checklist or compact `.table` whenever that makes per-lap/per-rep zone guidance clearer.
- Preserve named challenge elements, creative constraints, or novelty requests from the source markdown as visible
  day/week content. Prefer day `checklist` or `callout` blocks when the challenge affects execution; use week
  `notes_nodes` only for challenge rules that apply across multiple days.
- Preserve creative micro-challenges and larger signature/breakthrough challenges as first-class content, not generic
  notes. Keep the challenge name, purpose, success condition, safety cap, and fallback version visible. Prefer day
  `callout` + `checklist` blocks for concrete challenges and week `notes_blocks` for multi-day challenge rules.
- If this week is a stepping stone toward a larger signature challenge, keep that relationship visible in week notes
  or the relevant day callout.

## Priority 3 — Agent context (NOT shown by default)
- `global_nodes`: prefer a small set of concise nodes for zones, readiness rules, and guardrails, but keep meaningful rules and constraints.
- `week.notes_nodes`: include week-specific context whenever it materially affects execution, scheduling, or coaching interpretation.

## IDs
- `week_id` = 'wk-YYYY-MM-DD', `day_id` = ISO date.
- Block keys: '{{date}}-{{variant}}' within day.
"""


async def weekly_formatter_node(state: TrainingAnalysisState) -> dict:
    logger.info("Starting weekly formatter node")

    weekly_plan_md = extract_agent_content(state.get("weekly_plan"))

    if not weekly_plan_md:
        logger.warning("No weekly plan markdown to format")
        return {}

    agent_start_time = datetime.now()
    base_llm = ModelSelector.get_llm(AgentRole.PLAN_FORMATTER)
    llm_weekly = base_llm.with_structured_output(LlmWeeklyPlan, method="function_calling")

    async def call_weekly_formatter():
        return await llm_weekly.ainvoke(
            [
                {"role": "system", "content": WEEKLY_FORMATTER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": WEEKLY_FORMATTER_USER_PROMPT_TEMPLATE.format(weekly_plan_md=weekly_plan_md),
                },
            ]
        )

    async def node_execution():
        llm_result = await retry_with_backoff(call_weekly_formatter, AI_ANALYSIS_CONFIG, "Weekly Plan Formatting")

        weekly_plan_blocks = UiWeeklyPlan(
            **llm_result.model_dump(),
            plan_id=f"weekly_{state.get('user_id', 'user')}_{uuid.uuid4().hex[:10]}",
            athlete_name=state["athlete_name"],
            created_at=datetime.now().isoformat(),
        )

        execution_time = (datetime.now() - agent_start_time).total_seconds()
        log_node_completion("Weekly formatting", execution_time)

        return {
            "weekly_plan_blocks": sanitize_weekly_plan(weekly_plan_blocks),
            "costs": [create_cost_entry("weekly_formatter", execution_time)],
        }

    return await execute_node_with_error_handling(
        node_name="Weekly formatter",
        node_function=node_execution,
        error_message_prefix="Weekly formatting failed",
    )
