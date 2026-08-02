from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import pytest
from langchain.agents.structured_output import ToolStrategy
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from services.ai.head_coach import agent as head_coach_agent
from services.ai.head_coach.checkpointing import (
    CheckpointScope,
    HeadCoachCheckpointerProvider,
    build_checkpoint_config,
    build_checkpoint_identity,
)
from services.ai.head_coach.graph import (
    HeadCoachGraphNodes,
    HeadCoachGraphState,
    build_head_coach_graph,
    run_head_coach_execution,
)
from services.ai.head_coach.middleware import build_head_coach_middleware
from services.ai.head_coach.run_profiles import RunProfileName, get_run_profile

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
RUN_ID = UUID("00000000-0000-0000-0000-000000000002")


class _FactoryOutput(BaseModel):
    answer: str


def _node(
    name: str,
    calls: list[str],
    *,
    update: dict[str, Any] | None = None,
) -> Callable[[HeadCoachGraphState], Awaitable[dict[str, Any]]]:
    async def run(_state: HeadCoachGraphState) -> dict[str, Any]:
        calls.append(name)
        return update or {}

    return run


@pytest.mark.asyncio
async def test_head_coach_graph_runs_stable_lifecycle_spine_with_checkpointing():
    calls: list[str] = []
    graph = build_head_coach_graph(
        nodes=HeadCoachGraphNodes(
            load_context=_node("load", calls, update={"context_loaded": True}),
            design_strategy=_node("strategy", calls, update={"strategy": {"answer": "synthetic"}}),
            review_strategy=_node("strategy_review", calls, update={"strategy_reviewed": True}),
            build_execution=_node("execution", calls, update={"draft": {"answer": "synthetic"}}),
            review_result=_node("review", calls, update={"reviewed": True}),
            commit_result=_node("commit", calls, update={"committed": True}),
        ),
        checkpointer=InMemorySaver(),
    )
    identity = build_checkpoint_identity(
        owner_id=OWNER_ID,
        scope=CheckpointScope.INITIAL_PLANNING,
        resource_id=RUN_ID,
    )

    result = await graph.ainvoke(
        {"owner_id": str(OWNER_ID), "run_id": str(RUN_ID)},
        config=build_checkpoint_config(identity),
    )

    assert calls == ["load", "strategy", "strategy_review", "execution", "review", "commit"]
    assert result["committed"] is True


@pytest.mark.asyncio
async def test_resume_does_not_repeat_completed_expensive_node():
    calls: list[str] = []
    review_attempts = 0

    async def flaky_review(_state: HeadCoachGraphState) -> dict[str, Any]:
        nonlocal review_attempts
        review_attempts += 1
        calls.append("review")
        if review_attempts == 1:
            raise RuntimeError("synthetic review failure")
        return {"reviewed": True}

    checkpointer = InMemorySaver()
    graph = build_head_coach_graph(
        nodes=HeadCoachGraphNodes(
            load_context=_node("load", calls),
            design_strategy=_node("strategy", calls, update={"strategy": {"answer": "expensive"}}),
            review_strategy=_node("strategy_review", calls),
            build_execution=_node("execution", calls, update={"draft": {"answer": "expensive"}}),
            review_result=flaky_review,
            commit_result=_node("commit", calls, update={"committed": True}),
        ),
        checkpointer=checkpointer,
    )
    identity = build_checkpoint_identity(
        owner_id=OWNER_ID,
        scope=CheckpointScope.INITIAL_PLANNING,
        resource_id=RUN_ID,
    )
    config = build_checkpoint_config(identity)

    with pytest.raises(RuntimeError, match="synthetic review failure"):
        await graph.ainvoke({"owner_id": str(OWNER_ID), "run_id": str(RUN_ID)}, config=config)

    result = await graph.ainvoke(None, config=config)

    assert calls == ["load", "strategy", "strategy_review", "execution", "review", "review", "commit"]
    assert result["committed"] is True


def test_middleware_uses_limits_and_retries_without_context_summarization():
    profile = get_run_profile(RunProfileName.INITIAL_PLANNING)

    middleware = build_head_coach_middleware(profile)
    middleware_names = {type(item).__name__ for item in middleware}

    assert middleware_names == {
        "ModelCallLimitMiddleware",
        "ModelRetryMiddleware",
        "ToolCallLimitMiddleware",
        "ToolRetryMiddleware",
    }
    assert "SummarizationMiddleware" not in middleware_names


def test_shared_agent_factory_applies_profile_model_prompt_middleware_and_tool_strategy(monkeypatch):
    fake_model = object()
    fake_agent = object()
    model_calls: list[tuple[object, dict[str, object]]] = []
    create_calls: list[dict[str, Any]] = []

    def fake_get_llm(role, **kwargs):
        model_calls.append((role, kwargs))
        return fake_model

    def fake_create_agent(**kwargs):
        create_calls.append(kwargs)
        return fake_agent

    monkeypatch.setattr(head_coach_agent.ModelSelector, "get_llm", fake_get_llm)
    monkeypatch.setattr(head_coach_agent, "create_agent", fake_create_agent)

    result = head_coach_agent.build_head_coach_agent(
        profile_name=RunProfileName.COACH_TURN,
        response_schema=_FactoryOutput,
        tools=[],
        task_instructions="Answer the current coaching question.",
        name="test_head_coach",
    )

    assert result is fake_agent
    assert model_calls[0][1] == {
        "reasoning_effort": "medium",
        "enable_native_web_search": False,
    }
    create_call = create_calls[0]
    assert create_call["model"] is fake_model
    assert "persistent Head Coach" in create_call["system_prompt"]
    assert "Answer the current coaching question." in create_call["system_prompt"]
    assert isinstance(create_call["response_format"], ToolStrategy)
    assert create_call["response_format"].schema is _FactoryOutput
    assert {type(item).__name__ for item in create_call["middleware"]} == {
        "ModelCallLimitMiddleware",
        "ModelRetryMiddleware",
        "ToolCallLimitMiddleware",
        "ToolRetryMiddleware",
    }


@pytest.mark.asyncio
async def test_duplicate_delivery_returns_terminal_checkpoint_without_duplicate_commit():
    calls: list[str] = []
    identity = build_checkpoint_identity(
        owner_id=OWNER_ID,
        scope=CheckpointScope.INITIAL_PLANNING,
        resource_id=RUN_ID,
    )
    provider = HeadCoachCheckpointerProvider(
        database_url="postgresql://unused",
        injected_checkpointer=InMemorySaver(),
    )
    nodes = HeadCoachGraphNodes(
        load_context=_node("load", calls),
        design_strategy=_node("strategy", calls),
        review_strategy=_node("strategy_review", calls),
        build_execution=_node("execution", calls),
        review_result=_node("review", calls),
        commit_result=_node("commit", calls, update={"committed": True}),
    )
    initial_state: HeadCoachGraphState = {"owner_id": str(OWNER_ID), "run_id": str(RUN_ID)}

    first = await run_head_coach_execution(
        provider=provider,
        identity=identity,
        nodes=nodes,
        graph_input=initial_state,
    )
    duplicate = await run_head_coach_execution(
        provider=provider,
        identity=identity,
        nodes=nodes,
        graph_input=initial_state,
    )

    assert first["committed"] is True
    assert duplicate["committed"] is True
    assert calls == ["load", "strategy", "strategy_review", "execution", "review", "commit"]


@pytest.mark.asyncio
async def test_cancellation_guard_wins_before_domain_commit():
    calls: list[str] = []
    guard_checks = 0

    async def ensure_active() -> None:
        nonlocal guard_checks
        guard_checks += 1
        if guard_checks > 1:
            raise RuntimeError("cancelled")

    identity = build_checkpoint_identity(
        owner_id=OWNER_ID,
        scope=CheckpointScope.INITIAL_PLANNING,
        resource_id=RUN_ID,
    )
    provider = HeadCoachCheckpointerProvider(
        database_url="postgresql://unused",
        injected_checkpointer=InMemorySaver(),
    )
    nodes = HeadCoachGraphNodes(
        load_context=_node("load", calls),
        design_strategy=_node("strategy", calls),
        review_strategy=_node("strategy_review", calls),
        build_execution=_node("execution", calls),
        review_result=_node("review", calls),
        commit_result=_node("commit", calls, update={"committed": True}),
    )

    with pytest.raises(RuntimeError, match="cancelled"):
        await run_head_coach_execution(
            provider=provider,
            identity=identity,
            nodes=nodes,
            graph_input={"owner_id": str(OWNER_ID), "run_id": str(RUN_ID)},
            ensure_active=ensure_active,
        )

    assert calls == ["load", "strategy", "strategy_review", "execution", "review"]
