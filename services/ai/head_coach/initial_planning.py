from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.types import Command, interrupt
from pydantic import BaseModel, ConfigDict, Field, RootModel, TypeAdapter, ValidationError, model_validator

from services.ai.head_coach.artifacts import ExecutionPlanArtifactV3, SeasonStrategyArtifactV3
from services.ai.head_coach.checkpointing import (
    CheckpointScope,
    HeadCoachCheckpointerProvider,
    build_checkpoint_identity,
)
from services.ai.head_coach.graph import HeadCoachGraphNodes, HeadCoachGraphState, run_head_coach_execution
from services.ai.head_coach.middleware import LifecyclePhase
from services.ai.head_coach.prompts import build_head_coach_system_prompt
from services.ai.head_coach.run_profiles import RunProfileName, get_run_profile
from services.ai.head_coach.runtime_context import build_head_coach_brief
from services.ai.model_config import ModelSelector


class InitialPlanningError(RuntimeError):
    pass


class InitialPlanningModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlanningClarification(InitialPlanningModel):
    kind: Literal["clarification"] = "clarification"
    question: str = Field(min_length=1, max_length=600)
    reason_markdown: str = Field(min_length=1, max_length=2_000)
    requested_field: str = Field(min_length=1, max_length=100)


class PlanningArtifacts(InitialPlanningModel):
    kind: Literal["artifacts"] = "artifacts"
    season_strategy: SeasonStrategyArtifactV3
    execution_plan: ExecutionPlanArtifactV3

    @model_validator(mode="after")
    def validate_artifact_relationship(self) -> PlanningArtifacts:
        if self.execution_plan.season_plan_id != self.season_strategy.plan_id:
            raise ValueError("Execution plan must reference the generated season strategy")
        if self.execution_plan.athlete_name != self.season_strategy.athlete_name:
            raise ValueError("Season and execution artifacts must name the same athlete")
        if not (
            self.season_strategy.start_date
            <= self.execution_plan.start_date
            <= self.execution_plan.end_date
            <= self.season_strategy.end_date
        ):
            raise ValueError("The 28-day execution block must remain inside the season strategy")
        return self


class PlanningStrategy(InitialPlanningModel):
    kind: Literal["strategy"] = "strategy"
    season_strategy: SeasonStrategyArtifactV3


InitialPlanningDecision = Annotated[PlanningClarification | PlanningArtifacts, Field(discriminator="kind")]


class InitialPlanningDecisionEnvelope(RootModel[InitialPlanningDecision]):
    pass


StrategyPlanningDecision = Annotated[PlanningClarification | PlanningStrategy, Field(discriminator="kind")]


class StrategyPlanningDecisionEnvelope(RootModel[StrategyPlanningDecision]):
    pass


PlannerCallable = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
CommitCallable = Callable[[SeasonStrategyArtifactV3, ExecutionPlanArtifactV3], Awaitable[None]]
StatusCallable = Callable[[LifecyclePhase], Awaitable[None]]
_DECISION_ADAPTER: TypeAdapter[InitialPlanningDecision] = TypeAdapter(InitialPlanningDecision)
_STRATEGY_DECISION_ADAPTER: TypeAdapter[StrategyPlanningDecision] = TypeAdapter(StrategyPlanningDecision)


async def _ignore_status(_phase: LifecyclePhase):
    return None


def _require_planning_artifacts(value: object) -> PlanningArtifacts:
    decision = _DECISION_ADAPTER.validate_python(value)
    if not isinstance(decision, PlanningArtifacts):
        raise InitialPlanningError("Only complete planning artifacts may reach final review or commit")
    return decision


def build_initial_planning_context(
    *,
    now_utc: datetime,
    athlete_name: str,
    athlete_profile: dict[str, Any],
    competitions: list[dict[str, Any]],
    plan_start_date: str,
    run_overrides: dict[str, Any] | None = None,
    prior_season_plan: dict[str, Any] | None = None,
    prior_weekly_plan: dict[str, Any] | None = None,
    coach_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if now_utc.tzinfo is None:
        raise ValueError("Initial planning context requires a timezone-aware now_utc")
    return {
        "now_utc": now_utc.astimezone(UTC).isoformat(),
        "athlete_name": athlete_name.strip() or "Athlete",
        "plan_start_date": plan_start_date,
        "athlete_profile": athlete_profile,
        "competitions": competitions,
        "run_overrides": run_overrides or {},
        "prior_season_plan": prior_season_plan,
        "prior_weekly_plan": prior_weekly_plan,
        "coach_memory": coach_memory,
        "evidence_policy": {
            "baseline": "athlete_declared_and_local_domain",
            "provider_evidence_required": False,
            "missing_provider_data": "do_not_invent",
        },
    }


def build_model_planner() -> PlannerCallable:
    profile = get_run_profile(RunProfileName.INITIAL_PLANNING)
    base_model = ModelSelector.get_llm(
        profile.model_role,
        reasoning_effort=profile.reasoning_effort,
        enable_native_web_search=profile.enable_native_web_search,
    )
    strategy_model = base_model.with_structured_output(
        convert_to_openai_tool(StrategyPlanningDecisionEnvelope),
        method="function_calling",
        include_raw=True,
    )
    execution_model = base_model.with_structured_output(
        convert_to_openai_tool(ExecutionPlanArtifactV3),
        method="function_calling",
        include_raw=True,
    )

    async def plan(request: dict[str, Any]) -> dict[str, Any]:
        planning_stage = request.get("planning_stage")
        if planning_stage == "strategy":
            strategy = await _invoke_structured_with_repair(
                model=strategy_model,
                schema=StrategyPlanningDecisionEnvelope,
                request=request,
                prompt_builder=_strategy_user_prompt,
                stage_name="season strategy",
            )
            return strategy.root.model_dump(mode="json")
        if planning_stage == "execution":
            execution = await _invoke_structured_with_repair(
                model=execution_model,
                schema=ExecutionPlanArtifactV3,
                request=request,
                prompt_builder=_execution_user_prompt,
                stage_name="28-day execution plan",
            )
            return execution.model_dump(mode="json")
        raise InitialPlanningError(f"Unsupported initial-planning stage: {planning_stage!r}")

    return plan


async def _invoke_structured_with_repair[StructuredModelT: BaseModel](
    *,
    model: Any,
    schema: type[StructuredModelT],
    request: dict[str, Any],
    prompt_builder: Callable[[dict[str, Any]], str],
    stage_name: str,
) -> StructuredModelT:
    current_request = request
    for attempt in range(2):
        response = await model.ainvoke(
            [
                SystemMessage(content=str(current_request["system_prompt"])),
                HumanMessage(content=prompt_builder(current_request)),
            ]
        )
        if not isinstance(response, dict):
            raise InitialPlanningError("Head Coach structured-output adapter returned an invalid response")
        parsed = response.get("parsed")
        if parsed is not None:
            try:
                return schema.model_validate(parsed)
            except ValidationError as exc:
                parsing_error: BaseException | None = exc
        else:
            parsing_error = response.get("parsing_error")
        if attempt == 1:
            raise InitialPlanningError(
                f"Head Coach {stage_name} repair budget exhausted: "
                f"{_validation_error_summary(parsing_error)}"
            )
        current_request = {
            **request,
            "rejected_output": parsed if parsed is not None else _extract_rejected_tool_output(response.get("raw")),
            "validation_errors": _validation_error_payload(parsing_error),
            "repair_attempt": attempt + 1,
        }
    raise InitialPlanningError(f"Head Coach {stage_name} repair budget exhausted")


def _repair_payload(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "rejected_output": request.get("rejected_output"),
        "validation_errors": request.get("validation_errors"),
        "repair_attempt": request.get("repair_attempt"),
    }


def _strategy_user_prompt(request: dict[str, Any]) -> str:
    payload = {
        "coach_brief": request["coach_brief"],
        "clarification_answer": request.get("clarification_answer"),
        **_repair_payload(request),
    }
    return (
        "Produce the initial season-strategy decision. Ask one clarification only when the missing answer would "
        "materially change the season or next 28 days. Otherwise return one complete schema-v3 Season Strategy. "
        "Do not produce the 28-day execution plan in this stage. Do not invent wearable or provider observations. "
        "When rejected_output and validation_errors are present, correct that output against the errors and return "
        "the complete corrected strategy decision.\n\n"
        f"Input JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def _execution_user_prompt(request: dict[str, Any]) -> str:
    payload = {
        "coach_brief": request["coach_brief"],
        "season_strategy": request["season_strategy"],
        **_repair_payload(request),
    }
    return (
        "Create the complete schema-v3 28-day Execution Plan owned by the supplied validated Season Strategy. It "
        "must reference that strategy's plan_id and contain exactly four seven-day weeks with 28 consecutive "
        "calendar days. Preserve its decisions, assumptions, evidence boundaries, safety concerns, dates, and athlete "
        "identity. Do not invent wearable or provider observations. When rejected_output and validation_errors are "
        "present, correct that output against the errors and return the complete corrected execution plan.\n\n"
        f"Input JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def _extract_rejected_tool_output(raw_message: object) -> object:
    tool_calls = getattr(raw_message, "tool_calls", None)
    if not isinstance(tool_calls, list) or not tool_calls:
        return None
    first_call = tool_calls[0]
    if not isinstance(first_call, dict):
        return None
    return first_call.get("args")


def _validation_error_payload(error: BaseException | None) -> list[dict[str, str]]:
    if isinstance(error, ValidationError):
        return [
            {
                "path": ".".join(str(part) for part in item["loc"]),
                "type": str(item["type"]),
                "message": str(item["msg"]),
            }
            for item in error.errors(include_url=False, include_context=False, include_input=False)
        ]
    return [
        {
            "path": "",
            "type": type(error).__name__ if error is not None else "unknown_parse_error",
            "message": str(error or "unknown parse error"),
        }
    ]


def _validation_error_summary(error: BaseException | None) -> str:
    errors = _validation_error_payload(error)
    return "; ".join(
        f"{item['path'] or '<root>'}: {item['type']} ({item['message']})"
        for item in errors
    )


def _validate_requested_artifact_contract(
    decision: PlanningArtifacts,
    *,
    context_pack: dict[str, Any],
) -> PlanningArtifacts:
    requested_name = str(context_pack.get("athlete_name") or "").strip()
    requested_start = str(context_pack.get("plan_start_date") or "").strip()
    if not requested_name or not requested_start:
        raise InitialPlanningError("Initial planning context is missing its athlete identity or plan start date")
    try:
        requested_start_date = datetime.fromisoformat(requested_start).date()
    except ValueError as exc:
        raise InitialPlanningError("Initial planning context has an invalid plan start date") from exc
    if decision.season_strategy.athlete_name != requested_name or decision.execution_plan.athlete_name != requested_name:
        raise InitialPlanningError("Generated artifacts do not match the requested athlete identity")
    if decision.execution_plan.start_date != requested_start_date:
        raise InitialPlanningError("Generated execution plan does not match the requested start date")
    return decision


async def run_initial_planning(
    *,
    provider: HeadCoachCheckpointerProvider,
    owner_id: UUID,
    job_id: UUID,
    context_pack: dict[str, Any],
    planner: PlannerCallable,
    commit: CommitCallable,
    resume: Command | None = None,
    ensure_active: Callable[[], Awaitable[None]] | None = None,
    status: StatusCallable | None = None,
) -> dict[str, Any]:
    profile = get_run_profile(RunProfileName.INITIAL_PLANNING)
    brief = build_head_coach_brief(
        owner_id=str(owner_id),
        run_id=str(job_id),
        profile=profile,
        context_pack=context_pack,
    )
    emit = status or _ignore_status

    system_prompt = build_head_coach_system_prompt(profile)

    def request_for(state: HeadCoachGraphState) -> dict[str, Any]:
        return {"system_prompt": system_prompt, "coach_brief": state["brief"]}

    async def load_context(_state: HeadCoachGraphState) -> dict[str, Any]:
        await emit(LifecyclePhase.UNDERSTANDING_CONTEXT)
        return {"context_loaded": True, "brief": brief.model_dump(mode="json")}

    async def design_strategy(state: HeadCoachGraphState) -> dict[str, Any]:
        await emit(LifecyclePhase.DESIGNING_STRATEGY)
        return {"strategy": await planner({**request_for(state), "planning_stage": "strategy"})}

    async def review_strategy(state: HeadCoachGraphState) -> dict[str, Any]:
        await emit(LifecyclePhase.REVIEWING_CONSTRAINTS)
        decision = _STRATEGY_DECISION_ADAPTER.validate_python(state["strategy"])
        if isinstance(decision, PlanningClarification):
            await emit(LifecyclePhase.AWAITING_INPUT)
            answer = interrupt(decision.model_dump(mode="json"))
            repaired = _STRATEGY_DECISION_ADAPTER.validate_python(
                await planner(
                    {
                        **request_for(state),
                        "planning_stage": "strategy",
                        "clarification_answer": answer,
                    }
                )
            )
            if isinstance(repaired, PlanningClarification):
                raise InitialPlanningError("Head Coach requested another clarification after resume")
            decision = repaired
        return {
            "strategy": decision.season_strategy.model_dump(mode="json"),
            "strategy_reviewed": True,
        }

    async def build_execution(state: HeadCoachGraphState) -> dict[str, Any]:
        await emit(LifecyclePhase.BUILDING_EXECUTION_BLOCK)
        season_strategy = SeasonStrategyArtifactV3.model_validate(state["strategy"])
        execution_plan = ExecutionPlanArtifactV3.model_validate(
            await planner(
                {
                    **request_for(state),
                    "planning_stage": "execution",
                    "season_strategy": season_strategy.model_dump(mode="json"),
                }
            )
        )
        return {
            "draft": PlanningArtifacts(
                season_strategy=season_strategy,
                execution_plan=execution_plan,
            ).model_dump(mode="json")
        }

    async def review_result(state: HeadCoachGraphState) -> dict[str, Any]:
        await emit(LifecyclePhase.REVIEWING_CONSTRAINTS)
        decision = _validate_requested_artifact_contract(
            _require_planning_artifacts(state["draft"]),
            context_pack=context_pack,
        )
        return {"draft": decision.model_dump(mode="json"), "reviewed": True}

    async def commit_result(state: HeadCoachGraphState) -> dict[str, Any]:
        decision = _require_planning_artifacts(state["draft"])
        await emit(LifecyclePhase.SAVING_PLAN)
        await commit(decision.season_strategy, decision.execution_plan)
        await emit(LifecyclePhase.COMPLETED)
        return {
            "committed": True,
            "artifact_ids": [decision.season_strategy.plan_id, decision.execution_plan.plan_id],
        }

    initial_state: HeadCoachGraphState = {
        "owner_id": str(owner_id),
        "run_id": str(job_id),
    }
    graph_input: HeadCoachGraphState | Command = resume if resume is not None else initial_state
    return await run_head_coach_execution(
        provider=provider,
        identity=build_checkpoint_identity(
            owner_id=owner_id,
            scope=CheckpointScope.INITIAL_PLANNING,
            resource_id=job_id,
        ),
        nodes=HeadCoachGraphNodes(
            load_context=load_context,
            design_strategy=design_strategy,
            review_strategy=review_strategy,
            build_execution=build_execution,
            review_result=review_result,
            commit_result=commit_result,
        ),
        graph_input=graph_input,
        ensure_active=ensure_active,
    )
