import json
import logging
from datetime import datetime

from services.ai.ai_settings import AgentRole
from services.ai.langgraph.schemas.agent_outputs import SeasonPlannerDecision
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState
from services.ai.langgraph.utils.output_helper import extract_agent_content, extract_expert_output
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff

from .node_base import (
    configure_node_tools,
    create_cost_entry,
    execute_node_with_error_handling,
    log_node_completion,
)
from .prompt_components import get_hitl_clamp, get_hitl_instructions, get_workflow_context
from .tool_calling_helper import extract_text_content, handle_tool_calling_in_node

logger = logging.getLogger(__name__)

SEASON_PLANNER_SYSTEM_PROMPT = """You are a strategic season planner.
## Goal
Create strategic season plans for long-term athletic development.
## Principles
- Strategic: Focus on macro-cycles and phases.
- Adaptive: Use expert insights to tailor the plan.
- Systematic: Ensure logical progression towards goals.

## Coaching Lens
Apply these concepts when designing the season arc — as strategic instincts, not rigid templates:
- Classical periodization: base → build → peak → taper is a proven macro-structure, but the durations and transitions depend on the athlete's history, sport demands, and competition calendar.
- Block periodization: concentrating training emphasis (e.g., 3 weeks endurance focus, then 3 weeks intensity focus) can produce stronger adaptations than mixing everything equally.
- Supercompensation timing for races: peak performance requires arriving at the start line with fitness high and fatigue low. Plan the final hard block and subsequent taper to align with this window.
- Training age matters: newer athletes adapt to broader stimuli and need less specificity; experienced athletes need more targeted and varied stimuli to break plateaus.
- Injury prevention through load management: the transition between phases is where injury risk is highest. Gradual ramp-ups between phases are essential.
- A-race vs. B-race distinction: not every competition requires a peak. B-races can serve as high-quality training stimuli without disrupting the macro-plan.
- Volume floors matter as much as ceilings. For healthy, ambitious athletes with demonstrated recent load tolerance,
  do not design the season around the smallest safe dose. Set phase-level sport-specific volume expectations that are
  high enough to prepare the athlete for the actual priority event demands, then manage risk through progression,
  distribution, easy intensity, timing, fueling, and fallback versions.
- Athlete identity and standards matter. If planning context says the athlete considers short sessions insufficient
  for normal training, treat short sessions as recovery, shakeouts, taper touches, or explicit risk-control tools rather
  than the default build stimulus.
- Cross-training is supportive, not a universal substitute. Preserve the specific volume required by the target sport
  and downstream season goals; do not let a strong secondary modality hide underdevelopment in the modality that the
  priority event demands.
- Long-horizon durability goals should shape current phase floors. Do not postpone all durability work until the
  final specific block when the season includes later long, hilly, technical, or otherwise high-durability events.
- Creative challenge architecture: design both weekly micro-challenges and larger signature/breakthrough challenges.
  Micro-challenges add texture and skill practice; signature challenges are deliberately big, memorable stress tests
  that may sit near the edge of the athlete's current capacity. Do not make the plan blandly conservative for an
  ambitious athlete, but distinguish productive suffering from injury risk.
- Signature challenges should be athlete-specific and competition-relevant: unusual loop constraints, high-repeat
  track or hill projects, backyard-style simulations, terrain scavenger missions, fueling-under-fatigue drills,
  night/early-morning durability tasks, or other invented formats. These are illustrative categories only; invent
  context-specific challenges rather than repeating fixed examples.
- A signature challenge is NOT just a normal race-distance goal or generic endurance task. Avoid bland targets like
  "run a marathon" unless there is an unusual constraint system that changes the task: timing rules, repeated loops,
  terrain constraints, execution rituals, progressive cutoffs, mental rules, fueling constraints, or another strange
  format that makes the challenge feel non-standard and story-worthy.

## Output Format
Write your season plan in **rich markdown**. Structure it clearly with:
- Overall plan horizon and goal
- Named phases with start/end dates and training focus
- Competition integration
- A named creative challenge thread across the season: weekly micro-challenges plus bigger signature/breakthrough
  challenges with names, timing, purpose, progression, and guardrails
- Phase-specific goals, guardrails, and success markers

Do NOT prescribe daily workouts (that's the weekly planner's job).
Use tables, bullet lists, and emphasis for clarity."""

SEASON_PLANNER_USER_PROMPT = """Create or update a STRATEGIC, HIGH-LEVEL season plan.

## Inputs
- Athlete: {athlete_name}
- Date: ```json {current_date} ```
- Competitions: ```json {competitions} ```
- Training Evidence Profile: ```json {training_evidence} ```
{existing_season_plan_section}

## Planning Context and Custom Instructions
```markdown
{planning_context}
```

If this section contains custom planning instructions, creative constraints, or challenge requests, treat them as active
requirements for this run. Preserve them unless they are unsafe, infeasible, or contradicted by stronger athlete
constraints. A new custom instruction that the existing season plan does not support is a valid reason to choose
`action="update"` rather than `reuse`.

## Expert Insights
### Metrics
```markdown
{metrics_insights}
```
### Activity
```markdown
{activity_insights}
```
### Physiology
```markdown
{physiology_insights}
```

## Evidence Boundaries
- Respect `training_evidence.evidence_profile.claims_policy` when deciding what can be claimed.
- If `should_acknowledge_no_connected_sources` is true, build from declared profile, goals, competitions, and custom notes only.
- In declared-only mode, do not claim recent activity history, training load, compliance, sleep, HRV, recovery, or readiness trends.
- If load or recovery evidence is unavailable, say it is unavailable instead of inventing proxy certainty.

## Your Task
You MUST choose one action:
- If an existing season plan is still valid: set `action="reuse"` and do NOT rewrite the plan.
- If it needs updating: set `action="update"` and explain why in `rationale`.

Do NOT include the full season plan markdown in this decision response. The markdown will be generated in a separate step only when needed.

### Update Rules (critical)
- Preserve historical phases (phases that are fully in the past relative to `Date`). Do NOT delete them.
- Do NOT "reset" the plan start date to today. Keep continuity so the athlete is not suddenly back in a new "phase 0".
- Keep the plan covering the current date (no gaps between phases).
- Do NOT reuse an existing season plan if it would ignore explicit custom planning instructions in this run.
- Do NOT reuse an existing season plan if it lacks a competition-aware creative challenge thread and the
  athlete's current context can safely support one.

Return the structured fields only.
"""

SEASON_PLANNER_UPDATE_ONLY_PROMPT = """Write a detailed, structured season plan in markdown.

## Inputs
- Athlete: {athlete_name}
- Date: ```json {current_date} ```
- Competitions: ```json {competitions} ```
- Training Evidence Profile: ```json {training_evidence} ```
{existing_season_plan_section}

## Planning Context and Custom Instructions
```markdown
{planning_context}
```

## Expert Insights
### Metrics
```markdown
{metrics_insights}
```
### Activity
```markdown
{activity_insights}
```
### Physiology
```markdown
{physiology_insights}
```

## Constraints
- Respect `training_evidence.evidence_profile.claims_policy`. If no connected source is available, write the season
  from declared profile, goals, competitions, and custom notes only.
- In declared-only mode, explicitly frame activity history, training load, compliance, sleep, HRV, recovery, and
  readiness trends as unavailable rather than inferred.
- Preserve historical phases in the existing plan (do not delete completed phases).
- Keep plan continuity (do not reset the plan start date to today).
- Ensure phases cover the current date without gaps.
- Preserve explicit custom planning instructions, creative constraints, and challenge requests unless unsafe, infeasible,
  or contradicted by stronger athlete constraints. If you must modify or decline one, state why in the plan.
- Use phase-level volume floors as well as safety ceilings. If the athlete is healthy, ambitious, and has demonstrated
  load tolerance, do not make the plan a minimum-effective-dose season. Make the planned volume substantial enough for
  the priority event demands and the downstream season arc.
- Track sport-specific volume separately from total load. Supportive cross-training can add capacity, but it must not
  disguise under-preparation in the modality that priority events require.
- If the athlete says short sessions are not a normal training stimulus, treat short sessions as recovery, shakeouts,
  taper touches, or explicit safety modifications rather than default build sessions.
- If the season contains later high-durability goals, begin laying the durability foundation early through progressive,
  specific volume and challenge progressions rather than waiting until the final phase.
- Include a season-long creative challenge thread with two tiers:
  1. weekly micro-challenges for skill, novelty, and controlled discomfort;
  2. larger signature/breakthrough challenges that are rare, memorable, and deliberately hard.
- Signature challenges should make sense for a "push my limits" athlete: ambitious enough to be psychologically
  meaningful, but staged through progressions and protected by safety caps, fueling rules, and fallback versions.
- Do not use standard distance goals as signature challenges by themselves. "Run X distance" is not enough. Add a
  weird, memorable constraint system or choose a different challenge.
- Do not hardcode stock challenges; invent them from the athlete context, terrain, event demands, recent training,
  and available recovery capacity.
- For each phase, name 1-3 optional challenges with purpose, timing window, progression target, and safety guardrail.
  Keep them high-level so the Weekly Planner can translate them into concrete sessions or stepping stones.
- Return markdown only. Do not wrap it in JSON, code fences, or commentary.
"""


async def season_planner_node(state: TrainingAnalysisState) -> dict[str, object]:
    logger.info("Starting season planner node")

    hitl_enabled = state.get("hitl_enabled", True)
    logger.info("Season planner node: HITL %s", "enabled" if hitl_enabled else "disabled")

    agent_start_time = datetime.now()

    existing_plan_md = extract_agent_content(state.get("season_plan")).strip()
    existing_plan_section = (
        "\n## Existing Season Plan (markdown)\n```markdown\n" + existing_plan_md + "\n```\n" if existing_plan_md else ""
    )

    tools = configure_node_tools(
        agent_name="season_planner",
        plot_storage=None,
        plotting_enabled=False,
    )

    system_prompt = (
        get_workflow_context("season_planner")
        + SEASON_PLANNER_SYSTEM_PROMPT
        + (get_hitl_instructions("season_planner") if hitl_enabled else "")
        + (get_hitl_clamp(2) if hitl_enabled else "")
    )

    base_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": SEASON_PLANNER_USER_PROMPT.format(
                athlete_name=state["athlete_name"],
                current_date=json.dumps(state["current_date"], indent=2),
                competitions=json.dumps(state["competitions"], indent=2),
                training_evidence=json.dumps(state.get("training_data", {}), indent=2),
                existing_season_plan_section=existing_plan_section,
                planning_context=state["planning_context"],
                metrics_insights=extract_expert_output(state.get("metrics_outputs"), "for_season_planner"),
                activity_insights=extract_expert_output(state.get("activity_outputs"), "for_season_planner"),
                physiology_insights=extract_expert_output(state.get("physiology_outputs"), "for_season_planner"),
            ),
        },
    ]

    base_llm = ModelSelector.get_llm(AgentRole.SEASON_PLANNER)
    llm_with_tools = base_llm.bind_tools(tools) if tools else base_llm
    structured_llm = base_llm.with_structured_output(SeasonPlannerDecision, method="json_schema")

    async def call_season_planning():
        # Avoid a double-invoke when no tools are configured.
        if not tools:
            return await structured_llm.ainvoke(base_messages)

        return await handle_tool_calling_in_node(
            llm_with_tools,
            base_messages,
            tools,
            final_output_llm=structured_llm,
        )

    async def _generate_full_plan_markdown() -> str:
        fallback_messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": SEASON_PLANNER_UPDATE_ONLY_PROMPT.format(
                    athlete_name=state["athlete_name"],
                    current_date=json.dumps(state["current_date"], indent=2),
                    competitions=json.dumps(state["competitions"], indent=2),
                    training_evidence=json.dumps(state.get("training_data", {}), indent=2),
                    existing_season_plan_section=existing_plan_section,
                    planning_context=state["planning_context"],
                    metrics_insights=extract_expert_output(state.get("metrics_outputs"), "for_season_planner"),
                    activity_insights=extract_expert_output(state.get("activity_outputs"), "for_season_planner"),
                    physiology_insights=extract_expert_output(state.get("physiology_outputs"), "for_season_planner"),
                ),
            },
        ]
        if not tools:
            response = await base_llm.ainvoke(fallback_messages)
        else:
            response = await handle_tool_calling_in_node(llm_with_tools, fallback_messages, tools)
        return extract_text_content(response)

    async def node_execution():
        if existing_plan_md:
            decision = await retry_with_backoff(call_season_planning, AI_ANALYSIS_CONFIG, "Season Planning")
        else:
            decision = SeasonPlannerDecision(
                action="update",
                rationale="No existing season plan is present, so a new continuous season plan is required.",
            )

        execution_time = (datetime.now() - agent_start_time).total_seconds()
        log_node_completion("Season planning", execution_time)

        if decision.action == "reuse":
            logger.info("Season planner decision: reuse (reason=%s)", decision.rationale[:200])
            return {
                "season_plan_reused": True,
                "season_plan_action": "reuse",
                "season_plan_needs_formatting": False,
                "costs": [create_cost_entry("season_planner", execution_time)],
            }

        updated_md = (
            await retry_with_backoff(
                _generate_full_plan_markdown,
                AI_ANALYSIS_CONFIG,
                "Season Plan Markdown Generation",
            )
        ).strip()

        logger.info("Season planner decision: update (reason=%s)", decision.rationale[:200])
        return {
            "season_plan": updated_md,
            "season_plan_reused": False,
            "season_plan_action": "update",
            "season_plan_needs_formatting": True,
            # Clear stale blocks so downstream consumers don't accidentally use old UI data.
            "season_plan_blocks": None,
            "costs": [create_cost_entry("season_planner", execution_time)],
        }

    return await execute_node_with_error_handling(
        node_name="Season planner",
        node_function=node_execution,
        error_message_prefix="Season planning failed",
    )
