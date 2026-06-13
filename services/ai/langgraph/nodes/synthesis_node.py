import json
import logging
from datetime import datetime

from services.ai.ai_settings import AgentRole
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState
from services.ai.langgraph.utils.output_helper import extract_expert_output
from services.ai.model_config import ModelSelector
from services.ai.tools.plotting import PlotStorage
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff

from .node_base import (
    create_cost_entry,
    execute_node_with_error_handling,
    log_node_completion,
)
from .tool_calling_helper import extract_text_content, handle_tool_calling_in_node

logger = logging.getLogger(__name__)


SYNTHESIS_SYSTEM_PROMPT = """You are a performance integration specialist.
## Goal
Synthesize multiple data streams into a comprehensive athlete performance report.
## Principles
- Integrate: Connect insights from metrics, activity, and physiology.
- Contextualize: Relate data to the athlete's history and goals.
- Simplify: Make complex relationships understandable.
- Rich Content: Write detailed, narrative analysis — match the quality of a professional coaching report.

## Output Format
Write your analysis in **rich markdown**. Structure it with:
- Key performance indicators (KPIs) summary
- Detailed analysis sections covering load, recovery, performance trends
- Implications and risks (non-prescriptive)
- Data tables, trend descriptions, and coaching insights

Use tables, bullet lists, blockquotes, and emphasis for clarity."""

SYNTHESIS_PLOT_INSTRUCTIONS = """
## Plot Integration
- Include plot references as `[PLOT:plot_id]` in your markdown.
- These will become interactive charts."""

SYNTHESIS_USER_PROMPT = """Synthesize the expert analyses into a comprehensive athlete performance report.

## Inputs
### Metrics
```markdown
{metrics_result}
```
### Activity
```markdown
{activity_result}
```
### Physiology
```markdown
{physiology_result}
```
### Context
- Athlete: {athlete_name}
- Competitions: ```json {competitions} ```
- Date: ```json {current_date} ```
- Style: ```markdown {style_guide} ```

{plot_instructions}

## Task
1. **Integrate**: Connect load (metrics), execution (activity), and response (physiology).
2. **Identify Patterns**: Spot trends in performance and adaptation.
3. **Synthesize**: Create a coherent story, not just a list of facts.
4. **Be Rich**: Include detailed narrative, data tables, trend analysis.

## Scope Guardrails
- Do NOT output a training plan.
- Do NOT prescribe specific workouts.
- If you include advice, keep it at the level of observations, implications, and risks.

Write a comprehensive, structured performance report in markdown.
"""

SYNTHESIS_PLOT_USER_INSTRUCTIONS = """
## Plot References
- Include each unique `[PLOT:plot_id]` EXACTLY ONCE in the appropriate section.
- Do not duplicate references."""


async def synthesis_node(state: TrainingAnalysisState) -> dict[str, list | str | bool]:
    logger.info("Starting synthesis node")

    plot_storage = PlotStorage(state["execution_id"])
    plotting_enabled = state.get("plotting_enabled", False)

    logger.info(
        "Synthesis node: Plotting %s - %s plot integration instructions",
        "enabled" if plotting_enabled else "disabled",
        "including" if plotting_enabled else "no",
    )

    agent_start_time = datetime.now()

    system_prompt = (
        SYNTHESIS_SYSTEM_PROMPT
        + (SYNTHESIS_PLOT_INSTRUCTIONS if plotting_enabled else "")
    )

    user_prompt = SYNTHESIS_USER_PROMPT.format(
        athlete_name=state["athlete_name"],
        metrics_result=extract_expert_output(state.get("metrics_outputs"), "for_synthesis"),
        activity_result=extract_expert_output(state.get("activity_outputs"), "for_synthesis"),
        physiology_result=extract_expert_output(state.get("physiology_outputs"), "for_synthesis"),
        competitions=json.dumps(state["competitions"], indent=2),
        current_date=json.dumps(state["current_date"], indent=2),
        style_guide=state["style_guide"],
        plot_instructions=(SYNTHESIS_PLOT_USER_INSTRUCTIONS if plotting_enabled else ""),
    )

    base_llm = ModelSelector.get_llm(AgentRole.SYNTHESIS)
    tools: list[object] = []

    async def call_synthesis():
        response = await handle_tool_calling_in_node(
            base_llm, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ], tools,
        )
        return extract_text_content(response)

    async def node_execution():
        synthesis_md = await retry_with_backoff(
            call_synthesis, AI_ANALYSIS_CONFIG, "Synthesis Analysis"
        )

        execution_time = (datetime.now() - agent_start_time).total_seconds()
        log_node_completion("Synthesis analysis", execution_time)

        return {
            "synthesis_result": synthesis_md,
            "synthesis_complete": True,
            "costs": [create_cost_entry("synthesis", execution_time)],
            "available_plots": plot_storage.list_available_plots(),
        }

    return await execute_node_with_error_handling(
        node_name="Synthesis",
        node_function=node_execution,
        error_message_prefix="Synthesis analysis failed",
    )
