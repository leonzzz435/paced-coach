from typing import Any
from uuid import UUID

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt

from services.ai.head_coach.checkpointing import (
    CheckpointScope,
    build_checkpoint_config,
    build_checkpoint_identity,
)
from services.ai.head_coach.graph import HeadCoachGraphNodes, HeadCoachGraphState, build_head_coach_graph

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
RUN_ID = UUID("00000000-0000-0000-0000-000000000002")


async def _passthrough(_state: HeadCoachGraphState) -> dict[str, Any]:
    return {}


@pytest.mark.asyncio
async def test_clarification_interrupt_survives_graph_recreation_and_resumes_once():
    commits: list[str] = []

    async def ask_for_context(_state: HeadCoachGraphState) -> dict[str, Any]:
        answer = interrupt(
            {
                "kind": "clarification",
                "question": "Which four days are available?",
            }
        )
        return {"clarification_answer": answer}

    async def commit(state: HeadCoachGraphState) -> dict[str, Any]:
        commits.append(str(state["clarification_answer"]))
        return {"committed": True}

    checkpointer = InMemorySaver()
    nodes = HeadCoachGraphNodes(
        load_context=_passthrough,
        design_strategy=_passthrough,
        review_strategy=ask_for_context,
        build_execution=_passthrough,
        review_result=_passthrough,
        commit_result=commit,
    )
    identity = build_checkpoint_identity(
        owner_id=OWNER_ID,
        scope=CheckpointScope.INITIAL_PLANNING,
        resource_id=RUN_ID,
    )
    config = build_checkpoint_config(identity)

    first_graph = build_head_coach_graph(nodes=nodes, checkpointer=checkpointer)
    paused = await first_graph.ainvoke(
        {"owner_id": str(OWNER_ID), "run_id": str(RUN_ID)},
        config=config,
    )
    assert paused["__interrupt__"][0].value["kind"] == "clarification"

    recreated_graph = build_head_coach_graph(nodes=nodes, checkpointer=checkpointer)
    resumed = await recreated_graph.ainvoke(
        Command(resume="Monday, Tuesday, Thursday, Saturday"),
        config=config,
    )

    assert resumed["committed"] is True
    assert commits == ["Monday, Tuesday, Thursday, Saturday"]
