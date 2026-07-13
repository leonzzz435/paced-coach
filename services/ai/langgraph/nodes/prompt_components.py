from typing import Literal

AgentType = Literal[
    "metrics_summarizer",
    "physiology_summarizer",
    "activity_summarizer",
    "metrics",
    "physiology",
    "activity",
    "synthesis",
    "season_planner",
    "weekly_planner",
]

PROVIDER_OPTIONAL_COACHING_POLICY = """
## Provider-Optional Coaching Contract
- Connected activity and recovery sources are optional precision enhancements, never prerequisites for useful coaching.
- Treat declared goals, availability, physiology anchors, constraints, competitions, and athlete check-ins as valid coaching
  evidence. Lead with what those inputs support instead of centering absent device data.
- If no connected source or measurements are available, state measured trends as unavailable once and neutrally. Never
  interpret zero records as inactivity, rest, detraining, poor compliance, or a need to rebuild.
- Do not tell the athlete to connect, reconnect, restore, or start tracking. Do not make connecting a source the primary
  action, a safety requirement, or a condition for following the plan.
- Do not prescribe conservative training solely because optional device data is absent. Calibrate from declared context,
  explicit uncertainty, athlete-reported response, and event demands; provide practical self-checks and adjustment cues.
- You may mention optional sources only as a secondary way to increase future precision, never as the coaching outcome.
"""


def get_workflow_context(agent_type: AgentType) -> str:
    # Summarizer agents
    if agent_type in ["metrics_summarizer", "physiology_summarizer", "activity_summarizer"]:
        domain = agent_type.replace("_summarizer", "")
        return f"""
## System Role
You are the **{agent_type.replace('_', ' ').title()}**.
- **Input**: Raw `training_data`
- **Output**: Structured `{domain}_summary`
- **Goal**: Condense raw data into a factual, structured summary for the {domain} expert. Do NOT interpret."""

    # Expert agents
    if agent_type in ["metrics", "physiology", "activity"]:
        return f"""
## System Role
You are the **{agent_type.title()} Expert**.
- **Input**: `{agent_type}_summary`
- **Output**: `{agent_type}_outputs` with 3 fields:
  1. `for_synthesis`: For the comprehensive report.
  2. `for_season_planner`: Strategic insights (12-24 weeks).
  3. `for_weekly_planner`: Tactical details (next 28 days).
- **Goal**: Analyze patterns and provide specific insights for each consumer.
- **Context**: You are 1 of 3 parallel experts. Focus ONLY on your domain."""

    # Synthesis agent
    if agent_type == "synthesis":
        return """
## System Role
You are the **Synthesis Agent**.
- **Input**: `for_synthesis` fields from Metrics, Physiology, and Activity experts.
- **Output**: `synthesis_result` (Comprehensive Athlete Report).
- **Goal**: Integrate domain insights into a coherent story. Focus on historical patterns, not future planning."""

    # Planner agents
    if agent_type in ["season_planner", "weekly_planner"]:
        timeframe = "12-24 week strategy" if agent_type == "season_planner" else "next 28-day workouts"
        return f"""
## System Role
You are the **{agent_type.replace('_', ' ').title()}**.
- **Input**: `for_{agent_type}` fields from Metrics, Physiology, and Activity experts.
- **Output**: `{agent_type.replace('_planner', '_plan')}` ({timeframe}).
- **Goal**: Translate expert insights into a concrete {timeframe}.
- **Context**: Use the expert signals as your primary constraints and guides."""

    return ""


def get_plotting_instructions(agent_name: str) -> str:
    return f"""
## Visualization Rules
- **Constraint**: Create plots ONLY for unique insights not visible in standard wearable dashboards. Max 2 plots.
- **Reference**: You MUST reference each plot EXACTLY ONCE in your text using `[PLOT:{agent_name}_TIMESTAMP_ID]`.
- **Placement**: Place the reference where it best supports your analysis. Do not repeat it."""


def get_hitl_instructions(agent_name: str) -> str:
    return """
## Human Interaction
- **Questions**: If you need clarification, set `output` to a list of Question items.
- **Otherwise**: Set `output` to your node's normal output schema.
- **Criteria**: Only ask if data is ambiguous or user preference is required. Do not ask for obvious info.
- **Process**: If you ask questions, your execution pauses until the user answers."""


def get_hitl_clamp(max_questions: int = 2) -> str:
    return f"""
## HITL Clamp
- Ask at most **{max_questions}** questions.
- Each question must include the minimum context needed.
- If unsure, proceed with conservative assumptions and list them.
"""
