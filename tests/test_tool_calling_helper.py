from __future__ import annotations

import asyncio

import pytest

from services.ai.langgraph.nodes import tool_calling_helper
from services.ai.langgraph.nodes.tool_calling_helper import handle_tool_calling_in_node


class _FakeResponse:
    def __init__(self, *, tool_calls=None, content: str = ""):
        self.tool_calls = tool_calls or []
        self.content = content


class _FakeLlmWithTools:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = iter(responses)
        self.calls = 0

    async def ainvoke(self, _conversation, config=None):
        _ = config
        self.calls += 1
        return next(self._responses)


class _FakeFinalLlm:
    def __init__(self, payload: dict):
        self._payload = payload
        self.calls = 0

    async def ainvoke(self, _conversation, config=None):
        _ = config
        self.calls += 1
        return self._payload


class _FakeTool:
    def __init__(self, *, name: str, result: dict):
        self.name = name
        self._result = result

    async def ainvoke(self, _args):
        return self._result


@pytest.mark.asyncio
async def test_handle_tool_calling_emits_status_and_traces_for_successful_tool_call():
    llm = _FakeLlmWithTools(
        responses=[
            _FakeResponse(tool_calls=[{"name": "get_training_snapshot", "args": {"window": 7}, "id": "tool-1"}]),
            _FakeResponse(content="final"),
        ]
    )
    final_llm = _FakeFinalLlm({"assistant_message": "done"})
    tool = _FakeTool(name="get_training_snapshot", result={"sessions_7d": 5})
    statuses: list[dict] = []
    traces: list[dict] = []

    result = await handle_tool_calling_in_node(
        llm_with_tools=llm,
        messages=[{"role": "system", "content": "You are a coach"}, {"role": "user", "content": "How was my week?"}],
        tools=[tool],
        max_iterations=3,
        final_output_llm=final_llm,
        status_emitter=statuses.append,
        tool_trace_collector=traces.append,
    )

    assert result == {"assistant_message": "done"}
    assert any(status["step"] == "thinking" for status in statuses)
    assert any(status["step"] == "tool_call_start" for status in statuses)
    assert any(status["step"] == "tool_call_end" for status in statuses)
    assert len(traces) == 1
    assert traces[0]["tool_name"] == "get_training_snapshot"
    assert traces[0]["truncated"] is False
    assert traces[0]["char_len"] > 0


@pytest.mark.asyncio
async def test_handle_tool_calling_continues_when_requested_tool_is_missing():
    llm = _FakeLlmWithTools(
        responses=[
            _FakeResponse(tool_calls=[{"name": "missing_tool", "args": {"x": 1}, "id": "tool-1"}]),
            _FakeResponse(content="final"),
        ]
    )
    final_llm = _FakeFinalLlm({"assistant_message": "fallback complete"})
    statuses: list[dict] = []
    traces: list[dict] = []

    result = await handle_tool_calling_in_node(
        llm_with_tools=llm,
        messages=[{"role": "system", "content": "You are a coach"}, {"role": "user", "content": "Help"}],
        tools=[_FakeTool(name="other_tool", result={"ok": True})],
        max_iterations=3,
        final_output_llm=final_llm,
        status_emitter=statuses.append,
        tool_trace_collector=traces.append,
    )

    assert result == {"assistant_message": "fallback complete"}
    assert len(traces) == 1
    assert traces[0]["tool_name"] == "missing_tool"
    assert "not found" in traces[0]["result_preview"].lower()
    assert any(status["step"] == "tool_call_end" for status in statuses)


@pytest.mark.asyncio
async def test_handle_tool_calling_uses_structured_llm_directly_when_no_tools():
    llm = _FakeLlmWithTools(responses=[_FakeResponse(content="unstructured")])
    final_llm = _FakeFinalLlm({"assistant_message": "structured"})
    statuses: list[dict] = []

    result = await handle_tool_calling_in_node(
        llm_with_tools=llm,
        messages=[{"role": "system", "content": "You are a coach"}, {"role": "user", "content": "Help"}],
        tools=[],
        max_iterations=3,
        final_output_llm=final_llm,
        status_emitter=statuses.append,
    )

    assert result == {"assistant_message": "structured"}
    assert llm.calls == 0
    assert final_llm.calls == 1
    assert statuses == [
        {
            "step": "thinking",
            "message": "Preparing your final coaching response...",
            "iteration": 1,
        }
    ]


@pytest.mark.asyncio
async def test_handle_tool_calling_respects_shared_tool_semaphore(monkeypatch):
    llm = _FakeLlmWithTools(
        responses=[
            _FakeResponse(
                tool_calls=[
                    {"name": "tool_a", "args": {}, "id": "tool-1"},
                    {"name": "tool_b", "args": {}, "id": "tool-2"},
                ]
            ),
            _FakeResponse(content="final"),
        ]
    )
    final_llm = _FakeFinalLlm({"assistant_message": "done"})

    max_active = 0
    active = 0

    class _TrackingTool:
        def __init__(self, name: str):
            self.name = name

        async def ainvoke(self, _args):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return {"ok": self.name}

    shared_semaphore = asyncio.Semaphore(1)
    monkeypatch.setattr(tool_calling_helper, "get_tool_semaphore", lambda: shared_semaphore)

    result = await handle_tool_calling_in_node(
        llm_with_tools=llm,
        messages=[{"role": "system", "content": "You are a coach"}, {"role": "user", "content": "Help"}],
        tools=[_TrackingTool("tool_a"), _TrackingTool("tool_b")],
        max_iterations=3,
        final_output_llm=final_llm,
    )

    assert result == {"assistant_message": "done"}
    assert max_active == 1
