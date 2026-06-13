from __future__ import annotations

import inspect
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import uuid4

import pytest

from services.ai.coach import continuum_turn_agent
from services.ai.coach.continuum_turn_agent import CoachTurnOutput, run_continuum_coach_turn


@dataclass
class _FakeTool:
    name: str


class _FakeToolRegistry:
    def __init__(self):
        self.tools = [_FakeTool(name="get_training_snapshot"), _FakeTool(name="get_recent_activities")]

    def create_langchain_tools(self) -> list:
        return self.tools


class _FakeBaseLlm:
    def __init__(self):
        self.bound_tools: list | None = None
        self.structured_schema = None
        self.structured_llm = object()

    def bind_tools(self, tools: list):
        self.bound_tools = tools
        return self

    def with_structured_output(self, schema, **_kwargs):
        self.structured_schema = schema
        return self.structured_llm


@pytest.mark.asyncio
async def test_run_continuum_turn_threads_tools_status_and_traces(monkeypatch):
    fake_base_llm = _FakeBaseLlm()
    fake_registry = _FakeToolRegistry()
    emitted_statuses: list[dict[str, object]] = []
    helper_calls: list[dict[str, object]] = []

    def _fake_get_llm(_role):
        return fake_base_llm

    async def _fake_handle_tool_calling_in_node(**kwargs):
        helper_calls.append(kwargs)
        collector = kwargs.get("tool_trace_collector")
        if callable(collector):
            collector(
                {
                    "tool_name": "get_training_snapshot",
                    "args": {"days": 7},
                    "result_preview": '{"sessions_7d": 5}',
                    "char_len": 19,
                    "truncated": False,
                }
            )
        status_emitter = kwargs.get("status_emitter")
        if callable(status_emitter):
            maybe_result = status_emitter({"step": "thinking", "message": "Thinking through the next best step..."})
            if inspect.isawaitable(maybe_result):
                await maybe_result
        return CoachTurnOutput(
            assistant_message="Keep Thursday easy and reassess Friday.",
            proposal_ops=[],
            requests_full_run=False,
            full_run_reason=None,
            safety_flags=[],
            requires_medical_disclaimer=False,
        )

    async def _fake_retry_with_backoff(call, *_args):
        return await call()

    monkeypatch.setattr(continuum_turn_agent.ModelSelector, "get_llm", _fake_get_llm)
    monkeypatch.setattr(continuum_turn_agent, "handle_tool_calling_in_node", _fake_handle_tool_calling_in_node)
    monkeypatch.setattr(continuum_turn_agent, "retry_with_backoff", _fake_retry_with_backoff)
    monkeypatch.setattr(continuum_turn_agent, "_start_root_turn_trace", lambda **_kwargs: None)

    execution = await run_continuum_coach_turn(
        user_message="How was my week?",
        context_pack={"mode": "coach_chat"},
        tool_registry=fake_registry,
        thread_id="thread-1",
        user_id="user-1",
        status_emitter=emitted_statuses.append,
    )

    assert execution.output.assistant_message.startswith("Keep Thursday easy")
    assert len(execution.tool_traces) == 1
    assert execution.tool_traces[0]["tool_name"] == "get_training_snapshot"

    assert fake_base_llm.bound_tools == fake_registry.tools
    assert fake_base_llm.structured_schema is continuum_turn_agent.CoachTurnOutput

    assert len(helper_calls) == 1
    helper_call = helper_calls[0]
    assert helper_call["tools"] == fake_registry.tools
    assert helper_call["final_output_llm"] is fake_base_llm.structured_llm
    assert callable(helper_call["status_emitter"])
    assert getattr(helper_call["status_emitter"], "__self__", None) is emitted_statuses
    assert any(status["step"] == "thinking" for status in emitted_statuses)
    assert execution.trace_metadata is None


@pytest.mark.asyncio
async def test_run_continuum_turn_exposes_root_trace_metadata(monkeypatch):
    fake_base_llm = _FakeBaseLlm()
    fake_registry = _FakeToolRegistry()
    root_run_id = uuid4()
    trace_id = uuid4()
    finished_runs: list[dict[str, object]] = []
    tracing_context_calls: list[dict[str, object]] = []

    class _FakeRootRun:
        def __init__(self):
            self.id = root_run_id
            self.trace_id = trace_id
            self.session_name = "paced_coach"

        def add_event(self, _event):
            return None

    def _fake_get_llm(_role):
        return fake_base_llm

    async def _fake_handle_tool_calling_in_node(**_kwargs):
        return CoachTurnOutput(
            assistant_message="Treat this as fatigue, not lost fitness.",
            proposal_ops=[],
            requests_full_run=False,
            full_run_reason=None,
            safety_flags=[],
            requires_medical_disclaimer=False,
        )

    async def _fake_retry_with_backoff(call, *_args):
        return await call()

    @contextmanager
    def _fake_tracing_context(**kwargs):
        tracing_context_calls.append(kwargs)
        yield

    def _fake_finish_root_turn_trace(root_run, **kwargs):
        finished_runs.append({"root_run": root_run, **kwargs})

    monkeypatch.setattr(continuum_turn_agent.ModelSelector, "get_llm", _fake_get_llm)
    monkeypatch.setattr(continuum_turn_agent, "handle_tool_calling_in_node", _fake_handle_tool_calling_in_node)
    monkeypatch.setattr(continuum_turn_agent, "retry_with_backoff", _fake_retry_with_backoff)
    monkeypatch.setattr(continuum_turn_agent, "_start_root_turn_trace", lambda **_kwargs: _FakeRootRun())
    monkeypatch.setattr(continuum_turn_agent, "_finish_root_turn_trace", _fake_finish_root_turn_trace)
    monkeypatch.setattr(continuum_turn_agent, "tracing_context", _fake_tracing_context)

    execution = await run_continuum_coach_turn(
        user_message="Was this still threshold?",
        context_pack={"mode": "coach_chat"},
        tool_registry=fake_registry,
        thread_id="thread-2",
        user_id="user-2",
        root_run_id=str(root_run_id),
    )

    assert execution.trace_metadata is not None
    assert execution.trace_metadata.project_name == "paced_coach"
    assert execution.trace_metadata.trace_id == str(trace_id)
    assert execution.trace_metadata.root_run_id == str(root_run_id)
    assert execution.trace_metadata.attempt_count == 1
    parent_run = tracing_context_calls[0]["parent"]
    assert isinstance(parent_run, _FakeRootRun)
    assert parent_run.id == root_run_id
    assert finished_runs[0]["output"] == execution.output
