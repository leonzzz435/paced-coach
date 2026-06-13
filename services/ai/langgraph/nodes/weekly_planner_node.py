import json
import logging
from datetime import datetime

from services.ai.ai_settings import AgentRole
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState
from services.ai.langgraph.utils.message_helper import normalize_langchain_messages
from services.ai.langgraph.utils.output_helper import extract_agent_content, extract_expert_output
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff

from .node_base import (
    create_cost_entry,
    execute_node_with_error_handling,
    log_node_completion,
)
from .prompt_components import get_hitl_clamp, get_hitl_instructions, get_workflow_context
from .tool_calling_helper import extract_text_content

logger = logging.getLogger(__name__)

WEEKLY_PLANNER_SYSTEM_PROMPT = """## Goal
Create detailed, practical training plans that balance stress and recovery.
## Principles
- Adaptation: Progressive overload with adequate recovery.
- Specificity: Training must match the demands of the event.
- Individualization: Adapt to the athlete's current state and history.

## Coaching Lens
Apply these concepts when designing the training week — as professional instincts, not rigid formulas:
- Microcycle stress distribution: alternate stimulus and recovery days. Back-to-back high-intensity days require exceptional readiness or deliberate overreaching intent.
- Session sequencing: the order of session types within a week matters. Quality key sessions need fresh legs; place them after rest or easy days.
- The 80/20 polarization pattern: most endurance gains come from keeping ~80% of volume easy and ~20% genuinely hard. Avoid the "moderate intensity trap" of too many medium-effort sessions.
- Recovery is training: rest days and easy sessions are not wasted time — they are where adaptation consolidates. Prescribe them with the same intention as hard sessions.
- Connective tissue adaptation: tendons, ligaments, and bones adapt slower than cardiovascular fitness. Volume increases should respect this lag, especially for running.
- Race-week tapering: reduce volume while maintaining intensity to arrive fresh without detraining. The taper length depends on event duration and athlete history.
- Volume floors, not only safety caps: for healthy, ambitious athletes with demonstrated recent load tolerance,
  do not default to minimum-effective-dose plans. Prescribe enough sport-specific volume to move the athlete toward
  the priority event demands, then control risk through distribution, easy intensity, fueling, timing, and fallback
  versions.
- Athlete-standard calibration: if the athlete states that short sessions are not their normal training stimulus,
  use those short sessions mainly as recovery, shakeouts, taper touches, or explicit safety modifications. Normal
  build days should feel substantial relative to the athlete's history.
- Cross-training supports but does not fully replace specificity. Bike, strength, hike, swim, or other modalities can
  add aerobic and durability load, but the plan must still protect the sport-specific volume required by the current
  and downstream priority events.
- Timing tolerance matters: if the athlete reports handling volume or intensity better at specific times of day,
  honor that in session placement and downgrade late-session intensity when needed.

## Output Format
Write your training plan in **rich markdown**. Structure it as:
- One section per week from the provided `week_dates`
- Each week covers all training days
- Each day: workout title, duration, zones, detailed steps
- Use standard notation (e.g., "4x(5' Z4, 2' r)") to keep compact
- For any session with intervals, laps, reps, or changing segments, write the target intensity for EACH segment directly in the steps.
- Do not rely on only an overall session zone. The athlete must be able to open the calendar session and immediately see the zone target for each lap/rep/work block/recovery block.
- When exact numeric zone boundaries are unavailable, still use the most specific zone labels you know for each segment (for example Z1/Z2/Z4, easy/threshold, aerobic/VO2max).
- Include coaching notes and recovery guidance where relevant

Use tables, checklists, and emphasis for clarity."""

WEEKLY_PLANNER_USER_PROMPT = """## Task
Create a detailed training plan covering the upcoming weeks.

## Constraints
- **Honor the Phase**: Prioritize the Season Plan's phase intent.
- **Honor Continuity**: Do not treat every new 28-day plan as a fresh onboarding block. Use Transition Context,
  expert outputs, and recent planned/executed load to continue the athlete's actual training process.
- **Respect Readiness**: Adjust intensity based on Physiology/Metrics signals.
- **Integrate Signals**: Use Activity Expert advice for session structure.
- **Calibrate Volume Ambition**: Use volume floors as well as safety caps. For a healthy athlete with demonstrated
  recent load tolerance, choose an ambitious but coherent build instead of a conservative maintenance block.
- **Protect Specificity**: Track sport-specific volume separately from total training load. Do not let supportive
  cross-training crowd out the modality that matters most for the current priority event and downstream season goals.
- **Respect Athlete Standards**: If the athlete says short sessions are not a normal training stimulus, do not use them
  as the default build prescription. Reserve them for recovery, taper, shakeouts, or explicit risk-control reasons.
- **Prefer Easy Volume Before Extra Intensity**: When the plan needs more load for a capable athlete, first add
  controlled easy volume, medium-long aerobic work, or frequency before adding another hard session.
- **Honor Timing Tolerance**: If the athlete handles intensity/volume better earlier in the day, avoid prescribing
  late hard sessions; convert late work to easy aerobic support when needed.
- **Activate Challenge Architecture**: If the Season Plan contains creative challenge threads, translate them into
  concrete weekly/day execution. This includes small weekly micro-challenges and larger signature/breakthrough
  challenge preparation. Challenges should feel distinctive and demanding, not generic motivation blurbs. Scale them
  by readiness and phase intent; skip or downshift only when unsafe or clearly counterproductive.
- **Honor Custom Instructions**: Treat explicit run-specific planning instructions as hard requirements unless unsafe,
  infeasible, or contradicted by stronger athlete constraints. If you modify or decline one, state why in the plan.
- If the user asks for challenges, creative constraints, or novelty, make them visible in the week/day content rather
  than burying them in generic notes.
- **Brevity**: Use standard notation to keep the plan compact.
- Every interval, lap, rep, or segment with a different intensity must include its own target zone/intensity inside the written steps.
- Make each day's session self-contained for the calendar drill-down. The athlete should not need to infer lap zones from only a title, a single workout-meta line, or global notes.
- The first 3-7 days must explicitly bridge from recent training. If the prior days were already easy/rest and
  readiness supports it, do not repeat a generic easy reset unless you explain the safety reason.
- The block should not quietly underdose a stated priority. If readiness is usable but the plan intentionally keeps
  sport-specific volume below the athlete's recent proven baseline, explain the tradeoff.
- Include a short transition rationale in the plan brief or Week 1 notes.
- Include 1-2 micro-challenge moments per week when the season plan, competition prep, and readiness support it.
  Micro-challenges can use unusual constraints, repeated-loop formats, terrain missions, lap-count puzzles,
  fuel-under-fatigue tasks, or mental-durability formats. These are categories, not fixed templates.
- If the Season Plan includes a larger signature/breakthrough challenge, either schedule it when the week is the
  correct window or prescribe a concrete stepping-stone toward it. Do not shrink every big challenge into a tiny
  novelty task; preserve the intended edge while controlling risk.
- Do not turn signature challenges into plain distance goals. If a challenge looks like "run X distance", add the
  planned non-standard constraint from the Season Plan or defer until that constraint can be executed safely.
- Make every challenge actionable: name, purpose, success condition, safety cap, and fallback version.
- Do NOT add extra weeks outside `week_dates`.
- Keep each day scannable: avoid long narrative paragraphs.

## Inputs
### Season Plan
```markdown
{season_plan}
```
### Athlete Context
- Name: {athlete_name}
- Date: ```json {current_date} ```
- Upcoming Weeks: ```json {week_dates} ```
- Competitions: ```json {competitions} ```
- Training Evidence Profile: ```json {training_evidence} ```

### Evidence Boundaries
- Respect `training_evidence.evidence_profile.claims_policy` before making any data-backed claim.
- If `should_acknowledge_no_connected_sources` is true, build from declared profile, goals, competitions, custom notes,
  the current season plan, and transition context only.
- In declared-only mode, do not claim recent activity history, training load, compliance, sleep, HRV, recovery, or
  readiness trends.
- If load or recovery evidence is unavailable, say it is unavailable and use conservative declared-context planning
  rather than invented proxy certainty.

### Planning Context and Custom Instructions
```markdown
{planning_context}
```

### Transition Context
```markdown
{transition_context}
```

### Expert Analysis
- Metrics: ``` {metrics_analysis} ```
- Activity: ``` {activity_analysis} ```
- Physiology: ``` {physiology_analysis} ```

Write a detailed, structured weekly training plan in markdown.
"""

WEEKLY_PLANNER_FINAL_CHECKLIST = """
## Final Checklist
- Cover all weeks from the provided `week_dates`.
- Do not contradict expert constraints.
- Keep output compact and structured.
- Verify that any workout with changing intensity explicitly shows the target zone for each lap/rep/segment.
- Verify that custom planning instructions, challenge requests, and creative constraints are visibly reflected or
  explicitly declined with a reason.
- Verify that the first 3-7 days continue from Transition Context rather than defaulting to a fresh easy reset.
- Verify that healthy, ambitious athletes with demonstrated load tolerance receive meaningful sport-specific volume
  floors, not only conservative safety caps.
- Verify that short sessions are used as recovery/taper/shakeouts when the athlete says they are not a normal training
  stimulus, unless a clear safety reason is stated.
- Verify that season-level micro/signature challenges are translated into concrete weekly/day content or explicitly deferred
  with a reason.
"""


async def weekly_planner_node(state: TrainingAnalysisState) -> dict[str, list | str]:
    logger.info("Starting weekly planner node")

    hitl_enabled = state.get("hitl_enabled", True)
    logger.info("Weekly planner node: HITL %s", "enabled" if hitl_enabled else "disabled")

    agent_start_time = datetime.now()

    system_prompt = (
        get_workflow_context("weekly_planner")
        + WEEKLY_PLANNER_SYSTEM_PROMPT
        + (get_hitl_instructions("weekly_planner") if hitl_enabled else "")
        + (get_hitl_clamp(2) if hitl_enabled else "")
        + WEEKLY_PLANNER_FINAL_CHECKLIST
    )

    qa_messages = normalize_langchain_messages(state.get("weekly_planner_messages", []))
    user_message = {
        "role": "user",
        "content": WEEKLY_PLANNER_USER_PROMPT.format(
            season_plan=extract_agent_content(state.get("season_plan")),
            athlete_name=state["athlete_name"],
            current_date=json.dumps(state["current_date"], indent=2),
            week_dates=json.dumps(state["week_dates"], indent=2),
            competitions=json.dumps(state["competitions"], indent=2),
            training_evidence=json.dumps(state.get("training_data", {}), indent=2),
            planning_context=state["planning_context"],
            transition_context=state.get("transition_context", ""),
            metrics_analysis=extract_expert_output(state.get("metrics_outputs"), "for_weekly_planner"),
            activity_analysis=extract_expert_output(state.get("activity_outputs"), "for_weekly_planner"),
            physiology_analysis=extract_expert_output(state.get("physiology_outputs"), "for_weekly_planner"),
        ),
    }
    base_messages = [{"role": "system", "content": system_prompt}, user_message]

    base_llm = ModelSelector.get_llm(AgentRole.WEEKLY_PLANNER)

    async def call_weekly_planning():
        messages_with_qa = base_messages + qa_messages
        response = await base_llm.ainvoke(messages_with_qa)
        return extract_text_content(response)

    async def node_execution():
        weekly_plan_md = await retry_with_backoff(call_weekly_planning, AI_ANALYSIS_CONFIG, "Weekly Planning")

        execution_time = (datetime.now() - agent_start_time).total_seconds()
        log_node_completion("Weekly planning", execution_time)

        return {
            "weekly_plan": weekly_plan_md,
            "costs": [create_cost_entry("weekly_planner", execution_time)],
        }

    return await execute_node_with_error_handling(
        node_name="Weekly planner",
        node_function=node_execution,
        error_message_prefix="Weekly planning failed",
    )
