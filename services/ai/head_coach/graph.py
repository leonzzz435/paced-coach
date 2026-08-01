from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from services.ai.head_coach.checkpointing import (
    CheckpointIdentity,
    HeadCoachCheckpointerProvider,
    build_checkpoint_config,
)


class HeadCoachGraphState(TypedDict, total=False):
    owner_id: str
    run_id: str
    context_loaded: bool
    brief: dict[str, Any]
    strategy: dict[str, Any]
    strategy_reviewed: bool
    draft: dict[str, Any]
    reviewed: bool
    clarification_answer: object
    committed: bool


HeadCoachNode = Callable[
    [HeadCoachGraphState],
    dict[str, Any] | Awaitable[dict[str, Any]],
]


async def _invoke_node(node: HeadCoachNode, state: HeadCoachGraphState) -> dict[str, Any]:
    result = node(state)
    if isawaitable(result):
        return await result
    return result


@dataclass(frozen=True, slots=True)
class HeadCoachGraphNodes:
    load_context: HeadCoachNode
    design_strategy: HeadCoachNode
    review_strategy: HeadCoachNode
    build_execution: HeadCoachNode
    review_result: HeadCoachNode
    commit_result: HeadCoachNode


def build_head_coach_graph(
    *,
    nodes: HeadCoachGraphNodes,
    checkpointer: BaseCheckpointSaver[Any],
):
    builder = StateGraph(HeadCoachGraphState)

    async def load_context(state: HeadCoachGraphState) -> dict[str, Any]:
        return await _invoke_node(nodes.load_context, state)

    async def design_strategy(state: HeadCoachGraphState) -> dict[str, Any]:
        return await _invoke_node(nodes.design_strategy, state)

    async def review_strategy(state: HeadCoachGraphState) -> dict[str, Any]:
        return await _invoke_node(nodes.review_strategy, state)

    async def build_execution(state: HeadCoachGraphState) -> dict[str, Any]:
        return await _invoke_node(nodes.build_execution, state)

    async def review_result(state: HeadCoachGraphState) -> dict[str, Any]:
        return await _invoke_node(nodes.review_result, state)

    async def commit_result(state: HeadCoachGraphState) -> dict[str, Any]:
        return await _invoke_node(nodes.commit_result, state)

    builder.add_node("load_context", load_context)
    builder.add_node("design_strategy", design_strategy)
    builder.add_node("review_strategy", review_strategy)
    builder.add_node("build_execution", build_execution)
    builder.add_node("review_result", review_result)
    builder.add_node("commit_result", commit_result)
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "design_strategy")
    builder.add_edge("design_strategy", "review_strategy")
    builder.add_edge("review_strategy", "build_execution")
    builder.add_edge("build_execution", "review_result")
    builder.add_edge("review_result", "commit_result")
    builder.add_edge("commit_result", END)
    return builder.compile(checkpointer=checkpointer)


async def run_head_coach_execution(
    *,
    provider: HeadCoachCheckpointerProvider,
    identity: CheckpointIdentity,
    nodes: HeadCoachGraphNodes,
    graph_input: HeadCoachGraphState | Command | None,
    ensure_active: Callable[[], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """Run or resume one claimed execution without replaying a terminal checkpoint.

    The domain commit callback must still be transactionally idempotent: a process
    can fail after the domain transaction commits but before LangGraph persists the
    node completion checkpoint.
    """
    config = build_checkpoint_config(identity)
    claim_identity = f"{identity.thread_id}|{identity.checkpoint_ns}"
    async with provider.claim(claim_identity):
        checkpointer = await provider.get()
        checkpoint = await checkpointer.aget(config)
        if checkpoint is not None:
            checkpoint_state = dict(checkpoint["channel_values"])
            if checkpoint_state.get("committed") is True:
                return checkpoint_state

        if ensure_active is not None:
            await ensure_active()

        async def guarded_commit(state: HeadCoachGraphState) -> dict[str, Any]:
            if ensure_active is not None:
                await ensure_active()
            return await _invoke_node(nodes.commit_result, state)

        guarded_nodes = HeadCoachGraphNodes(
            load_context=nodes.load_context,
            design_strategy=nodes.design_strategy,
            review_strategy=nodes.review_strategy,
            build_execution=nodes.build_execution,
            review_result=nodes.review_result,
            commit_result=guarded_commit,
        )
        graph = build_head_coach_graph(nodes=guarded_nodes, checkpointer=checkpointer)
        invocation_input = graph_input
        if checkpoint is not None and not isinstance(graph_input, Command):
            invocation_input = None
        result = await graph.ainvoke(invocation_input, config=config)
        return dict(result)
