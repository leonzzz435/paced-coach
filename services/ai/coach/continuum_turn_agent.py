from __future__ import annotations

import inspect
import json
import logging
import os
from collections.abc import Callable
from contextlib import nullcontext
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, ToolMessage
from langsmith.run_helpers import tracing_context
from langsmith.run_trees import RunTree
from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.services.status_messages import tool_status_message
from services.ai.coach.schemas import AnyPlanPatchOp
from services.ai.head_coach.agent import build_head_coach_agent
from services.ai.head_coach.run_profiles import get_run_profile
from services.ai.head_coach.schemas import RunProfileName
from services.ai.head_coach.tool_policy import HeadCoachToolRegistry, build_profile_tools
from services.ai.utils.structured_output import coerce_structured_output

logger = logging.getLogger(__name__)


CoachTurnStatusEmitter = Callable[[dict[str, object]], object]


class CoachTurnOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    assistant_message: str = Field(..., min_length=1, max_length=4000)
    proposal_ops: list[AnyPlanPatchOp] = Field(default_factory=list)
    requests_full_run: bool = Field(default=False)
    full_run_reason: str | None = Field(default=None, max_length=600)
    safety_flags: list[str] = Field(default_factory=list)
    requires_medical_disclaimer: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_full_run_request(self) -> CoachTurnOutput:
        if self.requests_full_run and not self.full_run_reason:
            raise ValueError("full_run_reason is required when requests_full_run is true")
        if not self.requests_full_run and self.full_run_reason:
            raise ValueError("full_run_reason must be empty when requests_full_run is false")
        return self


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


_TURN_INSTRUCTIONS = """\
You are not a patch generator. Coach like a real human expert: specific, context-aware, accountable, and adaptive.

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
- Treat subjective check-ins (sleep quality, soreness, motivation, available time, desk load, pain/illness status) as first-class athlete-declared evidence. Reconcile them with the local plan, coaching history, and declared constraints rather than inventing measurements.
- Treat transient state notes (illness, acute pain, temporary constraints) as time-bounded context; verify if stale/uncertain before assuming they still apply.
- Keep recommendations concrete, concise, and practical.
- Hold accountability: highlight one priority action and one short check-in question when useful.
- proposal_ops should be empty unless a plan adjustment is clearly warranted.
- Match proposal operations to `current_weekly_plan_identity.schema_version`: schema v1 uses the legacy operations; schema v3 uses only `update_day_fields_v3`, `update_session_fields_v3`, and `replace_semantic_block_v3`.
- Schema v3 content is Markdown and typed semantic blocks. Never emit raw HTML or CSS for schema v3.
- For schema v3, target the exact day_id, session_id, or semantic container/block IDs supplied by `current_weekly_plan_identity` or `get_current_weekly_plan`; never translate a v3 plan into legacy fields.
- When changing a schema-v3 session duration, the runtime derives the containing day's total duration from all sessions. Do not emit a separate `update_day_fields_v3.total_duration_min` merely to mirror that session change.
- Strong readiness does not automatically mean extra intensity. If adding training is warranted, prefer low-risk easy volume, support work, timing changes, or desk-load movement before extra hard work, and protect the next key session.
- If you reduce or skip sport-specific work, explain the tradeoff and whether the weekly volume floor or competition-specific preparation remains intact.
- If a plan adjustment is clearly warranted, do not leave proposal_ops empty only because day/week identifiers are missing from the immediate context. Use `current_weekly_plan_identity` from the context pack when present, or call `get_current_weekly_plan` to obtain the relevant identifiers before deciding.
- For schema v1 only, if you adjust a specific day, also emit an `update_day_fields` op so the legacy dashboard fields stay aligned. Omit fields you are not changing.
- Keep changed session content self-contained in the visible schema-appropriate workout or semantic blocks: include explicit intensity targets for each lap, rep, work block, recovery block, and cool-down whenever intensity changes.
- Do not reduce interval guidance to a single overall zone label. The athlete should be able to open the calendar session and see the segment-by-segment intensity guidance immediately.
- Creative challenge handling: propose or preserve weird, meaningful challenges only when they support the current phase. Avoid generic distance stunts and avoid adding challenge load that compromises imminent quality work.
- Avoid deterministic formulaic coaching rules; reason from context and evidence instead.

Retrieval behavior:
- You have tool access for progressive disclosure. Start from existing context before calling tools.
- Avoid duplicate tool calls when recent tool results already answer the question.
- Use summary-level retrieval first, then deep detail only when uncertainty remains.
- Ask a focused follow-up when athlete-owned context cannot resolve a material uncertainty; never invent readiness metrics or completion evidence.
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

_TOOL_TRACE_PREVIEW_CHARS = 4000
_STRUCTURED_OUTPUT_TOOL_NAME = CoachTurnOutput.__name__


def _build_user_prompt(*, user_message: str, context_pack: dict) -> str:
    return f"Athlete message:\n{user_message}\n\nContext pack JSON:\n{json.dumps(context_pack, ensure_ascii=False)}\n"


def _serialize_message_content(content: object) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(content)


async def _emit_status(
    status_emitter: CoachTurnStatusEmitter | None,
    payload: dict[str, object],
) -> None:
    if status_emitter is None:
        return
    result = status_emitter(payload)
    if inspect.isawaitable(result):
        await result


async def _record_ai_tool_calls(
    *,
    message: AIMessage,
    iteration: int,
    tool_calls: dict[str, dict[str, object]],
    status_emitter: CoachTurnStatusEmitter | None,
) -> None:
    for call in message.tool_calls:
        call_id = str(call.get("id", ""))
        tool_name = str(call.get("name", ""))
        if tool_name == _STRUCTURED_OUTPUT_TOOL_NAME:
            continue
        args = call.get("args") if isinstance(call.get("args"), dict) else {}
        tool_calls[call_id] = {"tool_name": tool_name, "args": args}
        await _emit_status(
            status_emitter,
            {
                "step": "tool_call_start",
                "tool_name": tool_name,
                "message": tool_status_message(tool_name, args),
                "iteration": iteration,
            },
        )


async def _record_tool_result(
    *,
    message: ToolMessage,
    iteration: int,
    tool_calls: dict[str, dict[str, object]],
    tool_traces: list[dict[str, object]],
    status_emitter: CoachTurnStatusEmitter | None,
) -> None:
    if message.name == _STRUCTURED_OUTPUT_TOOL_NAME:
        return
    content = _serialize_message_content(message.content)
    preview = content[:_TOOL_TRACE_PREVIEW_CHARS]
    call = tool_calls.get(str(message.tool_call_id), {})
    tool_name = str(call.get("tool_name") or message.name or "unknown_tool")
    tool_traces.append(
        {
            "tool_name": tool_name,
            "args": call.get("args", {}),
            "result_preview": preview,
            "char_len": len(content),
            "truncated": len(content) > len(preview),
        }
    )
    await _emit_status(
        status_emitter,
        {
            "step": "tool_call_end",
            "tool_name": tool_name,
            "message": "Applying the latest retrieved context...",
            "iteration": max(iteration, 1),
        },
    )


async def _process_agent_update(
    *,
    update: object,
    iteration: int,
    tool_calls: dict[str, dict[str, object]],
    tool_traces: list[dict[str, object]],
    status_emitter: CoachTurnStatusEmitter | None,
) -> tuple[object | None, int]:
    if not isinstance(update, dict):
        return None, iteration
    structured_response: object | None = None
    for node_update in update.values():
        if not isinstance(node_update, dict):
            continue
        if node_update.get("structured_response") is not None:
            structured_response = node_update["structured_response"]
        messages = node_update.get("messages", [])
        for message in messages if isinstance(messages, list) else [messages]:
            if isinstance(message, AIMessage):
                iteration += 1
                await _record_ai_tool_calls(
                    message=message,
                    iteration=iteration,
                    tool_calls=tool_calls,
                    status_emitter=status_emitter,
                )
            elif isinstance(message, ToolMessage):
                await _record_tool_result(
                    message=message,
                    iteration=iteration,
                    tool_calls=tool_calls,
                    tool_traces=tool_traces,
                    status_emitter=status_emitter,
                )
    return structured_response, iteration


async def _run_agent_stream(
    *,
    agent,
    user_prompt: str,
    invoke_config: dict[str, Any],
    status_emitter: CoachTurnStatusEmitter | None,
) -> tuple[CoachTurnOutput, list[dict[str, object]]]:
    tool_calls: dict[str, dict[str, object]] = {}
    tool_traces: list[dict[str, object]] = []
    structured_response: object | None = None
    iteration = 0

    await _emit_status(
        status_emitter,
        {"step": "thinking", "message": "Thinking through the next best step...", "iteration": 1},
    )
    async for update in agent.astream(
        {"messages": [{"role": "user", "content": user_prompt}]},
        config=invoke_config,
        stream_mode="updates",
    ):
        candidate, iteration = await _process_agent_update(
            update=update,
            iteration=iteration,
            tool_calls=tool_calls,
            tool_traces=tool_traces,
            status_emitter=status_emitter,
        )
        if candidate is not None:
            structured_response = candidate

    if structured_response is None:
        raise RuntimeError("Head Coach turn completed without a structured response")
    return coerce_structured_output(structured_response, CoachTurnOutput), tool_traces


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
    tool_registry: HeadCoachToolRegistry | None,
    thread_id: str | None = None,
    user_id: str | None = None,
    status_emitter: CoachTurnStatusEmitter | None = None,
    root_run_id: str | None = None,
) -> CoachTurnExecution:
    profile = get_run_profile(RunProfileName.COACH_TURN)
    tools = build_profile_tools(profile, tool_registry=tool_registry)
    agent = build_head_coach_agent(
        profile_name=RunProfileName.COACH_TURN,
        response_schema=CoachTurnOutput,
        tools=tools,
        task_instructions=_TURN_INSTRUCTIONS,
        name="continuum_coach_turn",
    )
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
    attempt_count = 1
    with trace_context:
        try:
            output, tool_traces = await _run_agent_stream(
                agent=agent,
                user_prompt=_build_user_prompt(user_message=user_message, context_pack=context_pack),
                invoke_config={
                    "run_name": "continuum_coach_turn",
                    "tags": tags,
                    "metadata": {"thread_id": thread_id, "user_id": user_id},
                },
                status_emitter=status_emitter,
            )
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
