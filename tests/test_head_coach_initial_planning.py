from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from services.ai.head_coach.artifacts import (
    DecisionLedgerEntry,
    ExecutionDay,
    ExecutionPlanArtifactV3,
    ExecutionWeek,
    SeasonPhase,
    SeasonStrategyArtifactV3,
    TrainingSession,
)
from services.ai.head_coach.checkpointing import HeadCoachCheckpointerProvider
from services.ai.head_coach.initial_planning import (
    PlanningStrategy,
    StrategyPlanningDecisionEnvelope,
    build_initial_planning_context,
    build_model_planner,
    run_initial_planning,
)
from services.ai.head_coach.middleware import LifecyclePhase

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
JOB_ID = UUID("00000000-0000-0000-0000-000000000002")


def _decision() -> DecisionLedgerEntry:
    return DecisionLedgerEntry(
        decision_id="initial-decision",
        decided_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
        title="Consistency first",
        rationale_markdown="Repeatable training creates the foundation.",
        changes_markdown="Created the initial strategy and execution block.",
    )


def _artifacts() -> tuple[SeasonStrategyArtifactV3, ExecutionPlanArtifactV3]:
    start = date(2026, 8, 3)
    season = SeasonStrategyArtifactV3(
        plan_id="season-initial",
        version=1,
        athlete_name="Sample Athlete",
        created_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
        title="Autumn foundation",
        summary_markdown="Build repeatability before specificity.",
        start_date=start,
        end_date=date(2026, 11, 1),
        phases=[
            SeasonPhase(
                phase_id="foundation",
                title="Foundation",
                start_date=start,
                end_date=date(2026, 8, 30),
                objective_markdown="Establish a repeatable rhythm.",
            )
        ],
        decision_ledger_entry=_decision(),
    )
    weeks = []
    for week_index in range(4):
        week_start = start + timedelta(days=week_index * 7)
        days = []
        for day_index in range(7):
            day_date = week_start + timedelta(days=day_index)
            rest = day_index in {2, 6}
            days.append(
                ExecutionDay(
                    day_id=f"day-{day_date.isoformat()}",
                    date=day_date,
                    label=day_date.strftime("%A"),
                    focus_type="rest" if rest else "aerobic",
                    intensity="rest" if rest else "low",
                    total_duration_min=0 if rest else 40,
                    sessions=[]
                    if rest
                    else [
                        TrainingSession(
                            session_id=f"session-{day_date.isoformat()}",
                            title="Easy aerobic run",
                            sport="running",
                            objective_markdown="Build calm aerobic frequency.",
                            prescription_markdown="Run conversationally and finish with reserve.",
                            duration_min=40,
                            intensity="low",
                        )
                    ],
                )
            )
        weeks.append(
            ExecutionWeek(
                week_id=f"week-{week_index + 1}",
                title=f"Week {week_index + 1}",
                start_date=week_start,
                end_date=week_start + timedelta(days=6),
                intent_markdown="Protect repeatability.",
                days=days,
            )
        )
    execution = ExecutionPlanArtifactV3(
        plan_id="execution-initial",
        season_plan_id=season.plan_id,
        version=1,
        athlete_name=season.athlete_name,
        created_at=season.created_at,
        title="First 28 days",
        summary_markdown="Keep the easy work easy.",
        start_date=start,
        end_date=start + timedelta(days=27),
        weeks=weeks,
        decision_ledger_entry=_decision(),
    )
    return season, execution


def _context() -> dict:
    return build_initial_planning_context(
        now_utc=datetime(2026, 7, 19, 8, tzinfo=UTC),
        athlete_name="Sample Athlete",
        athlete_profile={"experience": "intermediate", "availability": ["Mon", "Tue", "Thu", "Sat"]},
        competitions=[{"id": "goal-1", "name": "Synthetic autumn event", "priority": "A"}],
        plan_start_date="2026-08-03",
        run_overrides={"temporary_constraints": "No training on Wednesdays"},
    )


def _provider() -> HeadCoachCheckpointerProvider:
    return HeadCoachCheckpointerProvider(
        database_url="postgresql://unused",
        injected_checkpointer=InMemorySaver(),
    )


def test_initial_context_preserves_declared_inputs_without_empty_provider_projections():
    context = _context()

    assert context["athlete_profile"]["availability"] == ["Mon", "Tue", "Thu", "Sat"]
    assert context["competitions"][0]["id"] == "goal-1"
    assert context["evidence_policy"]["provider_evidence_required"] is False
    assert "metrics" not in context
    assert "physiology" not in context
    assert "activities" not in context


@pytest.mark.asyncio
async def test_model_planner_returns_invalid_artifact_to_model_for_one_bounded_repair(monkeypatch):
    season, execution = _artifacts()
    parsed_strategy = StrategyPlanningDecisionEnvelope(PlanningStrategy(season_strategy=season))
    invalid_strategy = {"kind": "artifacts", "bad": True}
    strategy_invoke = AsyncMock(
        side_effect=[
            {"raw": None, "parsed": invalid_strategy, "parsing_error": None},
            {"raw": None, "parsed": parsed_strategy.model_dump(mode="json"), "parsing_error": None},
        ]
    )
    invalid_execution = execution.model_dump(mode="json")
    for week in invalid_execution["weeks"]:
        week["is_completed"] = False
    execution_invoke = AsyncMock(
        side_effect=[
            {"raw": None, "parsed": invalid_execution, "parsing_error": None},
            {"raw": None, "parsed": execution.model_dump(mode="json"), "parsing_error": None},
        ]
    )

    def with_structured_output(schema, **kwargs):
        assert kwargs == {"method": "function_calling", "include_raw": True}
        schema_name = schema["function"]["name"]
        if schema_name == "StrategyPlanningDecisionEnvelope":
            return SimpleNamespace(ainvoke=strategy_invoke)
        if schema_name == "ExecutionPlanArtifactV3":
            return SimpleNamespace(ainvoke=execution_invoke)
        pytest.fail("unexpected structured-output schema")

    base_model = SimpleNamespace(with_structured_output=with_structured_output)
    monkeypatch.setattr(
        "services.ai.head_coach.initial_planning.ModelSelector.get_llm", lambda *_args, **_kwargs: base_model
    )

    planner = build_model_planner()
    strategy_result = await planner(
        {
            "system_prompt": "system",
            "coach_brief": {"local_context": _context()},
            "planning_stage": "strategy",
        }
    )
    execution_result = await planner(
        {
            "system_prompt": "system",
            "coach_brief": {"local_context": _context()},
            "planning_stage": "execution",
            "season_strategy": season.model_dump(mode="json"),
        }
    )

    assert strategy_result["kind"] == "strategy"
    assert execution_result["plan_id"] == execution.plan_id
    assert strategy_invoke.await_count == 2
    assert execution_invoke.await_count == 2
    strategy_repair_prompt = strategy_invoke.await_args_list[1].args[0][1].content
    execution_repair_prompt = execution_invoke.await_args_list[1].args[0][1].content
    assert '"bad": true' in strategy_repair_prompt
    assert "is_completed" in execution_repair_prompt
    assert "weeks.0.is_completed" in execution_repair_prompt
    assert "extra_forbidden" in execution_repair_prompt


@pytest.mark.asyncio
async def test_provider_free_initial_planning_commits_one_coherent_v3_pair():
    season, execution = _artifacts()
    planner = AsyncMock(
        side_effect=[
            {"kind": "strategy", "season_strategy": season.model_dump(mode="json")},
            execution.model_dump(mode="json"),
        ]
    )
    commit = AsyncMock()
    phases: list[LifecyclePhase] = []

    async def capture_status(phase: LifecyclePhase):
        phases.append(phase)

    result = await run_initial_planning(
        provider=_provider(),
        owner_id=OWNER_ID,
        job_id=JOB_ID,
        context_pack=_context(),
        planner=planner,
        commit=commit,
        status=capture_status,
    )

    assert result["committed"] is True
    commit.assert_awaited_once_with(season, execution)
    assert LifecyclePhase.UNDERSTANDING_CONTEXT in phases
    assert LifecyclePhase.SAVING_PLAN in phases
    assert planner.await_args is not None
    request = planner.await_args.args[0]
    assert request["coach_brief"]["local_context"] == _context()
    assert request["planning_stage"] == "execution"


@pytest.mark.asyncio
async def test_clarification_resumes_same_checkpoint_and_does_not_repeat_initial_call():
    season, execution = _artifacts()
    planner = AsyncMock(
        side_effect=[
            {
                "kind": "clarification",
                "question": "Which four days are reliably available?",
                "reason_markdown": "Availability materially changes the weekly structure.",
                "requested_field": "availability",
            },
            {
                "kind": "strategy",
                "season_strategy": season.model_dump(mode="json"),
            },
            execution.model_dump(mode="json"),
        ]
    )
    commit = AsyncMock()
    provider = _provider()

    paused = await run_initial_planning(
        provider=provider,
        owner_id=OWNER_ID,
        job_id=JOB_ID,
        context_pack=_context(),
        planner=planner,
        commit=commit,
    )
    assert paused["__interrupt__"][0].value["requested_field"] == "availability"
    commit.assert_not_awaited()

    resumed = await run_initial_planning(
        provider=provider,
        owner_id=OWNER_ID,
        job_id=JOB_ID,
        context_pack=_context(),
        planner=planner,
        commit=commit,
        resume=Command(resume="Monday, Tuesday, Thursday, Saturday"),
    )

    assert resumed["committed"] is True
    assert planner.await_count == 3
    assert planner.await_args_list[1].args[0]["clarification_answer"] == "Monday, Tuesday, Thursday, Saturday"
    commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_execution_retry_resumes_without_repeating_durable_season_strategy():
    season, execution = _artifacts()
    strategy_calls = 0
    execution_calls = 0
    execution_briefs: list[dict] = []

    async def planner(request: dict) -> dict:
        nonlocal strategy_calls, execution_calls
        if request["planning_stage"] == "strategy":
            strategy_calls += 1
            return {"kind": "strategy", "season_strategy": season.model_dump(mode="json")}
        execution_calls += 1
        execution_briefs.append(request["coach_brief"])
        if execution_calls == 1:
            raise RuntimeError("synthetic execution failure")
        return execution.model_dump(mode="json")

    provider = _provider()
    commit = AsyncMock()
    with pytest.raises(RuntimeError, match="synthetic execution failure"):
        await run_initial_planning(
            provider=provider,
            owner_id=OWNER_ID,
            job_id=JOB_ID,
            context_pack=_context(),
            planner=planner,
            commit=commit,
        )

    result = await run_initial_planning(
        provider=provider,
        owner_id=OWNER_ID,
        job_id=JOB_ID,
        context_pack={**_context(), "run_overrides": {"changed_after_failure": True}},
        planner=planner,
        commit=commit,
    )

    assert result["committed"] is True
    assert strategy_calls == 1
    assert execution_calls == 2
    assert execution_briefs[1] == execution_briefs[0]
    assert execution_briefs[1]["local_context"]["run_overrides"] == {
        "temporary_constraints": "No training on Wednesdays"
    }
    commit.assert_awaited_once_with(season, execution)
