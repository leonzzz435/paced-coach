from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from services.ai.coach import continuum_turn_agent
from services.ai.coach.continuum_turn_agent import CoachTurnOutput, run_continuum_coach_turn


@dataclass
class _FakeTool:
    name: str


class _FakeToolRegistry:
    def __init__(self):
        self.tools = [_FakeTool(name="get_athlete_profile"), _FakeTool(name="get_current_weekly_plan")]
        self.allowed_tool_names: set[str] | None = None

    @classmethod
    def registered_tool_names(cls) -> set[str]:
        return {"get_athlete_profile", "get_current_weekly_plan"}

    def create_langchain_tools(self, *, allowed_tool_names=None) -> list:
        self.allowed_tool_names = set(allowed_tool_names) if allowed_tool_names is not None else None
        return [tool for tool in self.tools if allowed_tool_names is None or tool.name in allowed_tool_names]

    def get_observability_snapshot(self) -> dict:
        return {"source_of_truth": "local_athlete_owned"}


class _FakeAgent:
    def __init__(self, output: CoachTurnOutput, *, include_tool_call: bool = True):
        self.output = output
        self.include_tool_call = include_tool_call
        self.stream_calls: list[dict[str, object]] = []

    async def astream(self, agent_input, *, config, stream_mode):
        self.stream_calls.append({"input": agent_input, "config": config, "stream_mode": stream_mode})
        if self.include_tool_call:
            yield {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "get_athlete_profile",
                                    "args": {},
                                    "id": "call-1",
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            }
            yield {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content='{"memory_summary":"consistent athlete"}',
                            tool_call_id="call-1",
                            name="get_athlete_profile",
                        )
                    ]
                }
            }
        yield {
            "model": {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "CoachTurnOutput",
                                "args": self.output.model_dump(mode="json"),
                                "id": "structured-1",
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(
                        content="Returning structured response: CoachTurnOutput",
                        tool_call_id="structured-1",
                        name="CoachTurnOutput",
                    ),
                ],
                "structured_response": self.output,
            }
        }


def _output(message: str) -> CoachTurnOutput:
    return CoachTurnOutput(
        assistant_message=message,
        proposal_ops=[],
        requests_full_run=False,
        full_run_reason=None,
        safety_flags=[],
        requires_medical_disclaimer=False,
    )


def test_coach_turn_output_rejects_incoherent_full_run_request():
    with pytest.raises(ValueError, match="full_run_reason is required"):
        CoachTurnOutput(
            assistant_message="I need a deeper analysis.",
            requests_full_run=True,
        )


@pytest.mark.asyncio
async def test_run_continuum_turn_uses_head_coach_agent_policy_and_projects_standard_tool_events(monkeypatch):
    fake_registry = _FakeToolRegistry()
    fake_agent = _FakeAgent(_output("Keep Thursday easy and reassess Friday."))
    emitted_statuses: list[dict[str, object]] = []
    factory_calls: list[dict[str, Any]] = []

    def _fake_build_head_coach_agent(**kwargs):
        factory_calls.append(kwargs)
        return fake_agent

    monkeypatch.setattr(continuum_turn_agent, "build_head_coach_agent", _fake_build_head_coach_agent)
    monkeypatch.setattr(continuum_turn_agent, "_start_root_turn_trace", lambda **_kwargs: None)

    execution = await run_continuum_coach_turn(
        user_message="How was my week?",
        context_pack={"mode": "coach_chat", "tool_observability": {"source_of_truth": "local_athlete_owned"}},
        tool_registry=fake_registry,
        thread_id="thread-1",
        user_id="user-1",
        status_emitter=emitted_statuses.append,
    )

    assert execution.output.assistant_message.startswith("Keep Thursday easy")
    assert execution.tool_traces == [
        {
            "tool_name": "get_athlete_profile",
            "args": {},
            "result_preview": '{"memory_summary":"consistent athlete"}',
            "char_len": 39,
            "truncated": False,
        }
    ]
    assert fake_registry.allowed_tool_names == {"get_athlete_profile", "get_current_weekly_plan"}

    factory_call = factory_calls[0]
    assert factory_call["profile_name"] is continuum_turn_agent.RunProfileName.COACH_TURN
    assert factory_call["response_schema"] is CoachTurnOutput
    assert factory_call["tools"] == fake_registry.tools
    assert "Coaching Lens" in factory_call["task_instructions"]
    assert fake_agent.stream_calls[0]["stream_mode"] == "updates"
    assert [status["step"] for status in emitted_statuses] == [
        "thinking",
        "tool_call_start",
        "tool_call_end",
    ]
    assert execution.trace_metadata is None


@pytest.mark.asyncio
async def test_run_continuum_turn_exposes_root_trace_metadata(monkeypatch):
    fake_registry = _FakeToolRegistry()
    fake_agent = _FakeAgent(_output("Treat this as fatigue, not lost fitness."), include_tool_call=False)
    root_run_id = uuid4()
    trace_id = uuid4()
    finished_runs: list[dict[str, object]] = []
    tracing_context_calls: list[dict[str, object]] = []

    class _FakeRootRun:
        def __init__(self):
            self.id = root_run_id
            self.trace_id = trace_id
            self.session_name = "paced_coach"

    @contextmanager
    def _fake_tracing_context(**kwargs):
        tracing_context_calls.append(kwargs)
        yield

    def _fake_finish_root_turn_trace(root_run, **kwargs):
        finished_runs.append({"root_run": root_run, **kwargs})

    monkeypatch.setattr(continuum_turn_agent, "build_head_coach_agent", lambda **_kwargs: fake_agent)
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
