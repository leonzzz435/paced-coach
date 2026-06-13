from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from langsmith.run_helpers import tracing_context
from langsmith.run_trees import RunTree
from pydantic import BaseModel, Field

from services.ai.ai_settings import AgentRole
from services.ai.coach.schemas import PlanPatchOp
from services.ai.langgraph.nodes.tool_calling_helper import handle_tool_calling_in_node
from services.ai.model_config import ModelSelector
from services.ai.utils.retry_handler import AI_ANALYSIS_CONFIG, retry_with_backoff
from services.ai.utils.structured_output import coerce_structured_output

logger = logging.getLogger(__name__)


class CoachTurnToolRegistry(Protocol):
    def create_langchain_tools(self) -> list: ...


CoachTurnStatusEmitter = Callable[[dict[str, object]], object]


class CoachTurnOutput(BaseModel):
    assistant_message: str = Field(..., min_length=1, max_length=4000)
    proposal_ops: list[PlanPatchOp] = Field(default_factory=list)
    requests_full_run: bool = Field(default=False)
    full_run_reason: str | None = Field(default=None, max_length=600)
    safety_flags: list[str] = Field(default_factory=list)
    requires_medical_disclaimer: bool = Field(default=False)


class CoachTurnTraceMetadata(BaseModel):
    project_name: str = Field(min_length=1, max_length=200)
    trace_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    root_run_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    run_name: str = Field(default="continuum_coach_turn", min_length=1, max_length=80)
    attempt_count: int = Field(default=1, ge=1)


class CoachTurnExecution(BaseModel):
    output: CoachTurnOutput
    tool_traces: list[dict[str, object]] = Field(default_factory=list)
    trace_metadata: CoachTurnTraceMetadata | None = None


_TURN_SYSTEM_PROMPT = """\
You are the athlete's long-term endurance coach.

You are not a patch generator. You are a thoughtful coach who can optionally emit patch operations when needed.
Coach like a real human expert: specific, context-aware, accountable, and adaptive.

Coaching Lens — internalize these as your professional instincts, not checklists:
- Periodization awareness: know where the athlete is in their macro/meso/micro cycle. Advice that's perfect in base phase can be harmful in taper.
- Progressive overload principle: adaptation requires systematically increasing stimulus, but the rate must match the athlete's recovery capacity.
- Specificity vs. variety trade-off: training should progressively narrow toward race demands, but too-early specialization risks burnout and overuse injury.
- The 80/20 polarization pattern: most endurance gains come from keeping ~80% of volume easy and ~20% hard. "Medium-hard" sessions often provide the worst return on fatigue investment.
- Psychological readiness: motivation, confidence, and mental fatigue are real performance factors. A technically suboptimal session that maintains enthusiasm is often better than a perfect session that breeds resentment.
- Return-to-training after breaks: distinguish unresolved injury/illness from a resolved interruption. Do not blindly reset an athlete to beginner-level sessions when current evidence, plan context, and subjective check-in support continuity.
- Volume-floor awareness: when the current block has explicit volume floors or the athlete's standards require meaningful endurance volume, protect sport-specific volume with easy work where possible instead of quietly replacing it with unrelated cross-training.

Core behavior:
- Preserve continuity: explicitly connect today's recommendation to recent thread history when relevant.
- Personalize to long_term_memory (athlete_model + memory_summary) and full current-thread events/tool traces.
- Use structured `ui_context` from the app surface as the most specific request anchor when present.
- Read `evidence_profile` from the context pack before making claims. If its `claims_policy` says readiness or activity-completeness claims are unsupported, coach within those limits and acknowledge uncertainty when it matters.
- Treat subjective check-ins (sleep quality, soreness, motivation, available time, desk load, pain/illness status) as first-class evidence. Reconcile them with device data and recent execution rather than ignoring them or obeying them blindly.
- Treat transient state notes (illness, acute pain, temporary constraints) as time-bounded context; verify if stale/uncertain before assuming they still apply.
- Keep recommendations concrete, concise, and practical.
- Hold accountability: highlight one priority action and one short check-in question when useful.
- proposal_ops should be empty unless a plan adjustment is clearly warranted.
- Strong readiness does not automatically mean extra intensity. If adding training is warranted, prefer low-risk easy volume, support work, timing changes, or desk-load movement before extra hard work, and protect the next key session.
- If you reduce or skip sport-specific work, explain the tradeoff and whether the weekly volume floor or competition-specific preparation remains intact.
- If a plan adjustment is clearly warranted, do not leave proposal_ops empty only because day/week identifiers are missing from the immediate context. Use `current_weekly_plan_identity` from the context pack when present, or call `get_current_weekly_plan` to obtain the relevant identifiers before deciding.
- If you emit proposal_ops that adjust a specific day, also emit an `update_day_fields` op for that day so the dashboard stays aligned (day_label, workout_title, focus_type/color, estimated_duration_min, estimated_intensity, readiness_note). Omit fields you are not changing.
- If you emit proposal_ops that change session content, keep the workout self-contained in the visible day blocks: include explicit intensity targets for each lap, rep, work block, recovery block, and cool-down whenever intensity changes.
- Do not reduce interval guidance to a single overall zone label. The athlete should be able to open the calendar session and see the segment-by-segment intensity guidance immediately.
- Creative challenge handling: propose or preserve weird, meaningful challenges only when they support the current phase. Avoid generic distance stunts and avoid adding challenge load that compromises imminent quality work.
- Avoid deterministic formulaic coaching rules; reason from context and evidence instead.

Retrieval behavior:
- You have tool access for progressive disclosure. Start from existing context before calling tools.
- Avoid duplicate tool calls when recent tool results already answer the question.
- Use summary-level retrieval first, then deep detail only when uncertainty remains.
- If the evidence profile is incomplete, retrieve only what can reduce the real uncertainty; do not invent missing readiness or completeness certainty from thin data.
- Respect tool_budget context and retrieve only what is necessary for high-quality coaching.
- Tool names, descriptions, and argument schemas are provided by runtime tool metadata; rely on those contracts directly.

Safety floor:
- Never provide pharmaceutical or supplement dosing instructions.
- If athlete text mentions injury, illness, pain, or medication concerns, set requires_medical_disclaimer=true.
- During illness return-to-training context, avoid prescribing immediate high intensity.

Output contract:
- Return structured output only.
- assistant_message is always required.
- requests_full_run=true only when stale or insufficient deep-analysis context blocks quality coaching.
- If requests_full_run=true, full_run_reason must be non-empty.
"""


def _build_user_prompt(*, user_message: str, context_pack: dict) -> str:
    return f"Athlete message:\n{user_message}\n\nContext pack JSON:\n{json.dumps(context_pack, ensure_ascii=False)}\n"


def _langsmith_project_name() -> str | None:
    if not os.getenv("LANGSMITH_API_KEY"):
        return None
    return os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT")


def _start_root_turn_trace(
    *,
    root_run_id: str | None,
    user_message: str,
    thread_id: str | None,
    user_id: str | None,
    tags: list[str],
) -> RunTree | None:
    project_name = _langsmith_project_name()
    if root_run_id is None or project_name is None:
        return None

    try:
        root_run = RunTree(
            id=UUID(root_run_id),
            name="continuum_coach_turn",
            run_type="chain",
            project_name=project_name,
            inputs={
                "user_message": user_message,
                "thread_id": thread_id,
                "user_id": user_id,
            },
            tags=tags,
            extra={
                "metadata": {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "feature": "coach_turn",
                    "logical_root_run_id": root_run_id,
                }
            },
        )
        root_run.post()
        return root_run
    except Exception:
        logger.exception("Failed to create LangSmith root trace for coach turn")
        return None


def _finish_root_turn_trace(
    root_run: RunTree | None,
    *,
    output: CoachTurnOutput | None = None,
    tool_trace_count: int = 0,
    attempt_count: int = 1,
    error: Exception | None = None,
):
    if root_run is None:
        return

    try:
        root_run.end(
            outputs=(
                {
                    "assistant_message": output.assistant_message,
                    "proposal_ops_count": len(output.proposal_ops),
                    "requests_full_run": output.requests_full_run,
                    "tool_trace_count": tool_trace_count,
                }
                if output is not None
                else None
            ),
            error=f"{type(error).__name__}: {error}" if error is not None else None,
            metadata={"attempt_count": attempt_count, "tool_trace_count": tool_trace_count},
        )
        root_run.patch()
    except Exception:
        logger.exception("Failed to finalize LangSmith root trace for coach turn")
        return


async def run_continuum_coach_turn(
    *,
    user_message: str,
    context_pack: dict,
    tool_registry: CoachTurnToolRegistry | None,
    thread_id: str | None = None,
    user_id: str | None = None,
    status_emitter: CoachTurnStatusEmitter | None = None,
    root_run_id: str | None = None,
) -> CoachTurnExecution:
    base_llm = ModelSelector.get_llm(AgentRole.COACH)
    tools = tool_registry.create_langchain_tools() if tool_registry else []
    llm_with_tools = base_llm.bind_tools(tools) if tools else base_llm
    llm_with_structure = base_llm.with_structured_output(CoachTurnOutput)
    tags = ["agent:continuum_coach_turn", "feature:coach_turn"]
    if user_id:
        tags.append(f"user:{user_id}")
    if thread_id:
        tags.append(f"thread:{thread_id}")
    root_run = _start_root_turn_trace(
        root_run_id=root_run_id,
        user_message=user_message,
        thread_id=thread_id,
        user_id=user_id,
        tags=tags,
    )
    trace_context = (
        tracing_context(
            parent=root_run,
            project_name=root_run.session_name,
            tags=tags,
            metadata={
                "thread_id": thread_id,
                "user_id": user_id,
                "feature": "coach_turn",
            },
        )
        if root_run is not None
        else nullcontext()
    )
    attempt_count = 0

    async def call_turn() -> tuple[CoachTurnOutput, list[dict[str, object]]]:
        nonlocal attempt_count
        attempt_count += 1
        tool_traces: list[dict[str, object]] = []

        def _collect_tool_trace(trace_payload: dict[str, object]):
            tool_traces.append(trace_payload)

        if root_run is not None and attempt_count > 1:
            root_run.add_event(
                {
                    "name": "retry_attempt",
                    "time": datetime.now(UTC).isoformat(),
                    "message": f"Retry attempt {attempt_count}",
                }
            )

        response = await handle_tool_calling_in_node(
            llm_with_tools=llm_with_tools,
            messages=[
                {"role": "system", "content": _TURN_SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(user_message=user_message, context_pack=context_pack)},
            ],
            tools=tools,
            max_iterations=10,
            final_output_llm=llm_with_structure,
            invoke_config={
                "run_name": "continuum_coach_turn",
                "tags": tags,
                "metadata": {
                    "thread_id": thread_id,
                    "user_id": user_id,
                },
            },
            tool_trace_collector=_collect_tool_trace,
            status_emitter=status_emitter,
        )
        return coerce_structured_output(response, CoachTurnOutput), tool_traces

    with trace_context:
        try:
            output, tool_traces = await retry_with_backoff(call_turn, AI_ANALYSIS_CONFIG, "Continuum Coach Turn")
        except Exception as exc:
            _finish_root_turn_trace(root_run, attempt_count=attempt_count, error=exc)
            raise

    _finish_root_turn_trace(
        root_run,
        output=output,
        tool_trace_count=len(tool_traces),
        attempt_count=attempt_count,
    )
    trace_metadata = (
        CoachTurnTraceMetadata(
            project_name=root_run.session_name,
            trace_id=str(root_run.trace_id),
            root_run_id=str(root_run.id),
            attempt_count=attempt_count,
        )
        if root_run is not None
        else None
    )
    return CoachTurnExecution(output=output, tool_traces=tool_traces, trace_metadata=trace_metadata)
