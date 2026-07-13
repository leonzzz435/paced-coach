import json
import logging
from datetime import datetime

from services.ai.ai_settings import AgentRole
from services.ai.langgraph.schemas import MetricsExpertOutputs
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState
from services.ai.langgraph.utils.message_helper import normalize_langchain_messages
from services.ai.model_config import ModelSelector
from services.ai.tools.plotting import PlotStorage
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff

from .node_base import (
    configure_node_tools,
    create_cost_entry,
    create_plot_entries,
    execute_node_with_error_handling,
    log_node_completion,
)
from .prompt_components import (
    PROVIDER_OPTIONAL_COACHING_POLICY,
    get_hitl_clamp,
    get_hitl_instructions,
    get_plotting_instructions,
    get_workflow_context,
)
from .tool_calling_helper import handle_tool_calling_in_node

logger = logging.getLogger(__name__)

METRICS_SYSTEM_PROMPT_BASE = """## Goal
Analyze training metrics and competition readiness with data-driven precision.
## Principles
- Analyze: Focus on load patterns, fitness trends, and readiness.
- Objectivity: Do not speculate beyond the data.
- Clarity: Explain complex relationships simply.

## Multi-Provider Notes
- You may have training load signals from multiple providers (for example, Strava relative effort / suffer score versus WHOOP strain or cycle load).
- These are NOT on the same scale. Do not apply fixed thresholds across providers.
- Prefer relative-to-athlete baselines and trend/volatility patterns when comparing sources.

## Coaching Lens
Consider these concepts when interpreting metrics — not as rules, but as reasoning frameworks:
- Supercompensation: fitness gains emerge during recovery, not during the stimulus itself.
- Functional overreaching vs. non-functional overreaching: short-term performance dips can be intentional (planned overload) or pathological (accumulated fatigue without recovery).
- Dose-response relationship: adaptation is non-linear. More load does not always mean more fitness — there are diminishing returns and breakpoints.
- Individual load tolerance: the same ACWR or ramp rate can be safe for one athlete and dangerous for another. Calibrate to the athlete's history, not population averages.
- Competition proximity: acceptable risk profiles change as events approach. Conservative load management near race day; bolder progression in base phases.

## Gap Tolerance (Crucial)
- Moving averages (ATL/CTL) mechanically plummet during short breaks (3-7 days due to illness, travel, etc.).
- Do NOT treat acute load drops from short breaks as catastrophic fitness loss. True fitness decays over weeks, not days.
- Do NOT prescribe massive "re-build" phases just because ATL dropped for a few days.
- Advise a smooth, brief resumption of volume rather than a hard reset.

## New Metrics Definitions (ACWR V2)

You may be provided with "ACWR v2" metrics derived from daily training load when a provider-native load series is available.

### EWMA metrics (smooth, responsive)
- **Acute EWMA (7d)**: short-term load (fatigue proxy).
- **Chronic EWMA (28d)**: longer-term load (fitness/preparedness proxy).
- **Shifted Chronic EWMA (t-7)**: chronic EWMA evaluated 7 days earlier (approximate uncoupling).
- **ACWR (EWMA shifted)**: Acute EWMA / Shifted Chronic EWMA. Use as a spike indicator, but note thresholds require calibration.
- **Risk Index**: ln(ACWR) (symmetric measure of “doubling vs halving”).
- **TSB**: Chronic EWMA - Acute EWMA (negative = accumulating fatigue).
- **Ramp Rate (7d)**: change in Chronic EWMA vs 7 days ago (detects fast load increases).
- **Monotony (7d)**: mean(daily load over last 7d) / SD(last 7d). High values indicate low variation.
- **Strain (7d)**: (total weekly load) x Monotony.

Note: Thresholds are heuristics and should be calibrated to the athlete and to the chosen ACWR definition.

### Rolling-sum metrics (provider-native load scale, if present)
These use 7-day rolling sums of the available daily load series:
- **Acute 7d Sum**: sum of daily loads over last 7 days.
- **Chronic 28d Avg (of Acute 7d Sum)**: average of the last 28 values of Acute 7d Sum (smoothed baseline).
- **ACWR 7d/28d (coupled)**: Acute 7d Sum / Chronic 28d Avg.
- **ACWR 7d/28d (uncoupled)**: Acute 7d Sum / Chronic 28d Avg computed up to (t-7), excluding the most recent week (preferred when avoiding coupling).
"""

METRICS_USER_PROMPT = """## Task
Analyze the metrics summary to identify patterns and trends.

## Constraints
- Focus on **global training metrics** (load, VO2max, status).
- Do NOT describe specific workouts (Activity Expert's job).
- Do NOT infer internal physiology (Physiology Expert's job).
- Focus on **how the training stimulus behaves over time**.

## Inputs
### Metrics Summary
{data}
### Context
- Competitions: ```json {competitions} ```
- Date: ```json {current_date} ```
- **User Context**: ``` {analysis_context} ```

### Transition Context for Planning Continuity
```markdown
{transition_context}
```

## Output Requirements
Produce 3 structured fields. For EACH field, use this internal layout:
- **Signals**: what changed (concise)
- **Evidence**: numbers + date ranges
- **Implications**: constraints/opportunities for this receiver
- **Uncertainty**: gaps/low coverage if any

**Important**: Tailor content for each consumer.

### 1. `for_synthesis` (Comprehensive Report)
- **Context**: This provides the **"Quantitative Backbone"** (load/stress reality) for the report.
- **Goal**: Provide the quantitative truth of training load.
- **Freedom**: Highlight load behavior, fitness trends, or important ratios.

### 2. `for_season_planner` (12-24 Weeks)
- **Context**: This informs **"Load Architecture"** (ramp rates, volume ceilings) for the season.
- **Goal**: Provide high-level guidance on capacity and structural patterns.
- **Freedom**: Identify safe ramp rates, max sustainable chronic load, or volatility limits.

### 3. `for_weekly_planner` (Next 28 Days)
- **Context**: This acts as the **"Acute Load Guardrail"** for the next few weeks.
- **Goal**: Provide immediate load guidance and limits.
- **Freedom**: Define safety limits, push/pull signals, or specific load targets.
- **Continuity Requirement**: Carry forward transition-relevant metrics from the Transition Context:
  starting load state, recent 3-7 day load posture, acute-vs-baseline behavior, and whether the next block
  should resume progression, absorb load, or hold steady from a load-management perspective.
- **CRITICAL**: Do NOT prescribe specific workouts. Provide limits and load guidance."""

METRICS_FINAL_CHECKLIST = """
## Final Checklist
- Use Signals/Evidence/Implications/Uncertainty per receiver.
- Stay within metrics domain only.
- No prescriptions for specific workouts.
"""


async def metrics_expert_node(state: TrainingAnalysisState) -> dict[str, list | str | dict]:
    logger.info("Starting metrics expert analysis node")

    plot_storage = PlotStorage(state["execution_id"])
    plotting_enabled = state.get("plotting_enabled", False)
    hitl_enabled = state.get("hitl_enabled", True)

    logger.info(
        "Metrics expert: Plotting %s, HITL %s",
        "enabled" if plotting_enabled else "disabled",
        "enabled" if hitl_enabled else "disabled",
    )

    tools = configure_node_tools(
        agent_name="metrics",
        plot_storage=plot_storage,
        plotting_enabled=plotting_enabled,
    )

    system_prompt = (
        get_workflow_context("metrics")
        + METRICS_SYSTEM_PROMPT_BASE
        + PROVIDER_OPTIONAL_COACHING_POLICY
        + (get_plotting_instructions("metrics") if plotting_enabled else "")
        + (get_hitl_instructions("metrics") if hitl_enabled else "")
        + (get_hitl_clamp(2) if hitl_enabled else "")
        + METRICS_FINAL_CHECKLIST
    )

    base_llm = ModelSelector.get_llm(AgentRole.METRICS_EXPERT)

    llm_with_tools = base_llm.bind_tools(tools) if tools else base_llm
    final_llm = base_llm.with_structured_output(MetricsExpertOutputs)

    agent_start_time = datetime.now()

    async def call_metrics_with_tools():
        qa_messages = normalize_langchain_messages(state.get("metrics_expert_messages", []))

        base_messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": METRICS_USER_PROMPT.format(
                    data=state.get("metrics_summary", "No metrics summary available"),
                    competitions=json.dumps(state["competitions"], indent=2),
                    current_date=json.dumps(state["current_date"], indent=2),
                    analysis_context=state["analysis_context"],
                    transition_context=state.get("transition_context", ""),
                ),
            },
        ]

        return await handle_tool_calling_in_node(
            llm_with_tools=llm_with_tools,
            messages=base_messages + qa_messages,
            tools=tools,
            max_iterations=15,
            final_output_llm=final_llm,
        )

    async def node_execution():
        agent_output = await retry_with_backoff(call_metrics_with_tools, AI_ANALYSIS_CONFIG, "Metrics Agent with Tools")
        logger.info("Metrics expert analysis completed")

        execution_time = (datetime.now() - agent_start_time).total_seconds()

        plots, plot_storage_data, available_plots = create_plot_entries("metrics", plot_storage)

        log_node_completion("Metrics expert analysis", execution_time, len(available_plots))

        return {
            "metrics_outputs": agent_output,
            "plots": plots,
            "plot_storage_data": plot_storage_data,
            "costs": [create_cost_entry("metrics", execution_time)],
            "available_plots": available_plots,
        }

    return await execute_node_with_error_handling(
        node_name="Metrics expert analysis",
        node_function=node_execution,
        error_message_prefix="Metrics expert analysis failed",
    )
