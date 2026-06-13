from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from api.models.ai_run_cost import AiRunCost
from api.models.coach_turn_run import CoachTurnRun
from api.services import coach_turn
from api.services.ai_run_costs import AiRunCostSnapshot
from services.ai.coach.continuum_turn_agent import CoachTurnExecution, CoachTurnOutput, CoachTurnTraceMetadata


class _CaptureDb:
    def __init__(self):
        self.added: list[object] = []
        self.flush = AsyncMock()

    def add(self, obj):
        self.added.append(obj)


def _quota_payload() -> dict[str, object]:
    return {
        "is_limited": False,
        "remaining": None,
        "limit": None,
        "used": 0,
        "week_anchor_utc": "",
    }


@pytest.mark.asyncio
async def test_handle_text_turn_records_turn_run_and_provenance(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    db = _CaptureDb()
    thread = SimpleNamespace(id=thread_id, latest_seq=0)
    next_seq = 0
    trace_id = uuid.uuid4()
    captured_turn_kwargs: dict[str, object] = {}
    validated_ui_context = {"source": "today_mission", "day": {"day_id": "2026-03-27"}}

    async def _fake_append_coach_events(_db, *, thread, items):
        nonlocal next_seq
        created = []
        for event_type, actor, payload in items:
            next_seq += 1
            created.append(
                SimpleNamespace(
                    id=uuid.uuid4(),
                    thread_id=thread.id,
                    seq=next_seq,
                    event_type=event_type,
                    actor=actor,
                    payload=payload,
                )
            )
        return created

    @asynccontextmanager
    async def _fake_tool_registry(*_args, **_kwargs):
        yield SimpleNamespace()

    async def _fake_run_continuum_coach_turn(**kwargs):
        captured_turn_kwargs.update(kwargs)
        return CoachTurnExecution(
            output=CoachTurnOutput(
                assistant_message="Treat this as a harder threshold day, not lost fitness.",
                proposal_ops=[],
                requests_full_run=False,
                full_run_reason=None,
                safety_flags=[],
                requires_medical_disclaimer=False,
            ),
            tool_traces=[],
            trace_metadata=CoachTurnTraceMetadata(
                project_name="paced_coach",
                trace_id=str(trace_id),
                root_run_id=str(kwargs["root_run_id"]),
                attempt_count=2,
            ),
        )

    monkeypatch.setattr(coach_turn, "_ensure_thread_iteration_limit", AsyncMock())
    monkeypatch.setattr(coach_turn, "append_coach_events", _fake_append_coach_events)
    monkeypatch.setattr(coach_turn, "_capture_recap_follow_up_response", AsyncMock(return_value=[]))
    monkeypatch.setattr(coach_turn, "ensure_coach_weekly_quota_available", AsyncMock())
    monkeypatch.setattr(coach_turn, "get_thread_events", AsyncMock(return_value=[]))
    monkeypatch.setattr(coach_turn, "build_ongoing_tool_registry", _fake_tool_registry)
    build_turn_context_mock = AsyncMock(return_value={"mode": "coach_chat"})
    monkeypatch.setattr(coach_turn, "build_turn_context", build_turn_context_mock)
    monkeypatch.setattr(coach_turn, "run_continuum_coach_turn", _fake_run_continuum_coach_turn)
    monkeypatch.setattr(coach_turn, "consume_coach_weekly_quota", AsyncMock(return_value=_quota_payload()))
    monkeypatch.setattr(coach_turn, "_append_tool_trace_events", AsyncMock(return_value=[]))
    monkeypatch.setattr(coach_turn, "_resolve_turn_ui_context", AsyncMock(return_value=validated_ui_context))
    monkeypatch.setattr(coach_turn, "sanitize_ops", lambda ops: [])
    monkeypatch.setattr(coach_turn, "maybe_update_thread_memory", AsyncMock())
    monkeypatch.setattr(coach_turn, "_can_request_full_run", AsyncMock(return_value=False))
    monkeypatch.setattr(
        coach_turn,
        "capture_langsmith_run_costs",
        lambda *_args, **_kwargs: AiRunCostSnapshot(cost_status="captured", total_cost_usd=0.02, total_tokens=222),
    )

    turn_payload, created_events = await coach_turn._handle_text_turn(
        cast("Any", db),
        user_id=user_id,
        thread=cast("Any", thread),
        message="Why did this threshold run feel terrible?",
        quota_source_id="quota-source",
        ui_context={"source": "today_mission", "day_id": "2026-03-27"},
    )

    turn_run = next(obj for obj in db.added if isinstance(obj, CoachTurnRun))
    ai_run_cost = next(obj for obj in db.added if isinstance(obj, AiRunCost))

    assert captured_turn_kwargs["root_run_id"] == str(turn_run.id)
    assert turn_run.user_id == user_id
    assert turn_run.thread_id == thread_id
    assert turn_run.user_message_event_id == created_events[0].id
    assert turn_run.response_event_id == created_events[1].id
    assert turn_run.turn_seq_anchor == 1
    assert turn_run.langsmith_project == "paced_coach"
    assert turn_run.langsmith_trace_id == str(trace_id)
    assert turn_run.langsmith_root_run_id == str(turn_run.id)
    assert turn_run.attempt_count == 2
    assert build_turn_context_mock.await_args is not None
    assert build_turn_context_mock.await_args.kwargs["ui_context"] == validated_ui_context
    assert turn_payload["provenance"] == {
        "coach_thread_id": str(thread_id),
        "coach_turn_run_id": str(turn_run.id),
        "user_message_event_id": str(created_events[0].id),
        "response_event_id": str(created_events[1].id),
        "turn_seq_anchor": 1,
        "langsmith_project": "paced_coach",
        "langsmith_trace_id": str(trace_id),
        "langsmith_root_run_id": str(turn_run.id),
    }
    assert ai_run_cost.feature == "coach_turn"
    assert ai_run_cost.source_type == "coach_turn_run"
    assert ai_run_cost.source_id == str(turn_run.id)


@pytest.mark.asyncio
async def test_run_turn_action_blocks_text_when_connected_chat_gate_fails(monkeypatch):
    ensure_chat_gate = AsyncMock(
        side_effect=HTTPException(status_code=400, detail="Coach chat requires connected setup.")
    )
    handle_text_turn = AsyncMock()

    monkeypatch.setattr(coach_turn, "_ensure_connected_coach_chat_available", ensure_chat_gate)
    monkeypatch.setattr(coach_turn, "_handle_text_turn", handle_text_turn)

    with pytest.raises(HTTPException) as exc:
        await coach_turn._run_turn_action(
            cast("Any", object()),
            user_id=uuid.uuid4(),
            thread=cast("Any", SimpleNamespace(id=uuid.uuid4())),
            action="text",
            message="How should I adjust this week?",
            proposal_id=None,
            reason=None,
            quota_source_id="quota-source",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Coach chat requires connected setup."
    ensure_chat_gate.assert_awaited_once()
    handle_text_turn.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_turn_action_routes_text_to_handler_after_connected_chat_gate(monkeypatch):
    expected_payload = {"kind": "message", "assistant_message": "Keep Tuesday easy."}
    expected_events = [SimpleNamespace(id=uuid.uuid4())]
    ensure_chat_gate = AsyncMock()
    handle_text_turn = AsyncMock(return_value=(expected_payload, expected_events))
    thread = SimpleNamespace(id=uuid.uuid4())
    user_id = uuid.uuid4()

    monkeypatch.setattr(coach_turn, "_ensure_connected_coach_chat_available", ensure_chat_gate)
    monkeypatch.setattr(coach_turn, "_handle_text_turn", handle_text_turn)

    payload, created_events = await coach_turn._run_turn_action(
        cast("Any", object()),
        user_id=user_id,
        thread=cast("Any", thread),
        action="text",
        message="How should I adjust this week?",
        proposal_id=None,
        reason=None,
        quota_source_id="quota-source",
    )

    assert payload == expected_payload
    assert created_events == expected_events
    ensure_chat_gate.assert_awaited_once()
    handle_text_turn.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_accept_turn_consumes_adaptive_quota_only_when_plan_changes(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    source_job_id = uuid.uuid4()
    db = _CaptureDb()
    thread = SimpleNamespace(id=thread_id)
    proposal = SimpleNamespace(
        id=proposal_id,
        status="pending",
        weekly_plan_version=3,
        ops={"ops": []},
        thread_id=thread_id,
    )
    active_weekly = SimpleNamespace(
        version=3,
        plan_data={"type": "weekly_plan", "weeks": []},
        source_job_id=source_job_id,
    )
    updated_plan = SimpleNamespace(model_dump=lambda mode="json": {"type": "weekly_plan", "weeks": [], "mode": mode})
    adaptive_usage = SimpleNamespace(model_dump=lambda mode="json": {"used": 1, "limit": 2, "remaining": 1, "mode": mode})
    append_events = [SimpleNamespace(id=uuid.uuid4(), seq=1)]
    consume_adaptive_update = AsyncMock(return_value=adaptive_usage)
    usage_context = SimpleNamespace()
    get_local_usage_context = AsyncMock(return_value=usage_context)

    monkeypatch.setattr(coach_turn, "_get_proposal", AsyncMock(return_value=proposal))
    monkeypatch.setattr(coach_turn, "_get_active_weekly_plan", AsyncMock(return_value=active_weekly))
    monkeypatch.setattr(coach_turn, "parse_patch_ops", lambda ops: ops)
    monkeypatch.setattr(coach_turn, "sanitize_ops", lambda ops: ops)
    monkeypatch.setattr(coach_turn, "apply_ops", lambda *_args, **_kwargs: (updated_plan, True))
    monkeypatch.setattr(coach_turn, "get_local_usage_context", get_local_usage_context)
    monkeypatch.setattr(coach_turn, "consume_adaptive_update", consume_adaptive_update)
    monkeypatch.setattr(coach_turn, "append_coach_events", AsyncMock(return_value=append_events))
    monkeypatch.setattr(coach_turn, "maybe_update_thread_memory", AsyncMock())
    monkeypatch.setattr(coach_turn, "get_coach_weekly_quota", AsyncMock(return_value=_quota_payload()))

    payload, created_events = await coach_turn._handle_accept_turn(
        cast("Any", db),
        user_id=user_id,
        thread=cast("Any", thread),
        proposal_id=proposal_id,
    )

    assert payload["status"] == "accepted"
    assert payload["changed"] is True
    assert payload["adaptive_updates"] == {"used": 1, "limit": 2, "remaining": 1, "mode": "json"}
    assert payload["weekly_version"] == 4
    assert active_weekly.version == 4
    assert active_weekly.plan_data["version"] == 4
    assert created_events == append_events
    get_local_usage_context.assert_awaited_once_with(cast("Any", db), user_id=user_id)
    consume_adaptive_update.assert_awaited_once_with(
        cast("Any", db),
        user_id=user_id,
        source_id=str(proposal_id),
        context=usage_context,
    )


@pytest.mark.asyncio
async def test_handle_accept_turn_skips_adaptive_quota_for_noop_proposal(monkeypatch):
    user_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    db = _CaptureDb()
    thread = SimpleNamespace(id=thread_id)
    proposal = SimpleNamespace(
        id=proposal_id,
        status="pending",
        weekly_plan_version=2,
        ops={"ops": []},
        thread_id=thread_id,
    )
    active_weekly = SimpleNamespace(
        version=2,
        plan_data={"type": "weekly_plan", "weeks": []},
        source_job_id=uuid.uuid4(),
    )
    updated_plan = SimpleNamespace(model_dump=lambda mode="json": {"type": "weekly_plan", "weeks": [], "mode": mode})
    append_events = [SimpleNamespace(id=uuid.uuid4(), seq=1)]
    consume_adaptive_update = AsyncMock()

    monkeypatch.setattr(coach_turn, "_get_proposal", AsyncMock(return_value=proposal))
    monkeypatch.setattr(coach_turn, "_get_active_weekly_plan", AsyncMock(return_value=active_weekly))
    monkeypatch.setattr(coach_turn, "parse_patch_ops", lambda ops: ops)
    monkeypatch.setattr(coach_turn, "sanitize_ops", lambda ops: ops)
    monkeypatch.setattr(coach_turn, "apply_ops", lambda *_args, **_kwargs: (updated_plan, False))
    monkeypatch.setattr(coach_turn, "consume_adaptive_update", consume_adaptive_update)
    monkeypatch.setattr(coach_turn, "append_coach_events", AsyncMock(return_value=append_events))
    monkeypatch.setattr(coach_turn, "maybe_update_thread_memory", AsyncMock())
    monkeypatch.setattr(coach_turn, "get_coach_weekly_quota", AsyncMock(return_value=_quota_payload()))

    payload, created_events = await coach_turn._handle_accept_turn(
        cast("Any", db),
        user_id=user_id,
        thread=cast("Any", thread),
        proposal_id=proposal_id,
    )

    assert payload["status"] == "accepted"
    assert payload["changed"] is False
    assert payload["adaptive_updates"] is None
    assert payload["weekly_version"] == 2
    assert active_weekly.version == 2
    assert "version" in payload["weekly_plan"]
    assert "version" not in active_weekly.plan_data
    assert created_events == append_events
    consume_adaptive_update.assert_not_awaited()
