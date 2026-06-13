import uuid

from api.services.coach_turn import _build_turn_request_hash


def test_turn_request_hash_is_deterministic():
    thread_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    first = _build_turn_request_hash(
        action="proposal_reject",
        thread_id=thread_id,
        message=None,
        proposal_id=proposal_id,
        reason="Need lower load",
        ui_context=None,
    )
    second = _build_turn_request_hash(
        action="proposal_reject",
        thread_id=thread_id,
        message=None,
        proposal_id=proposal_id,
        reason="Need lower load",
        ui_context=None,
    )
    assert first == second


def test_turn_request_hash_changes_with_payload():
    thread_id = uuid.uuid4()
    base = _build_turn_request_hash(
        action="text",
        thread_id=thread_id,
        message="How was my week?",
        proposal_id=None,
        reason=None,
        ui_context=None,
    )
    changed = _build_turn_request_hash(
        action="text",
        thread_id=thread_id,
        message="How was my week exactly?",
        proposal_id=None,
        reason=None,
        ui_context=None,
    )
    assert base != changed


def test_turn_request_hash_changes_with_ui_context():
    thread_id = uuid.uuid4()
    base = _build_turn_request_hash(
        action="text",
        thread_id=thread_id,
        message="Assess today's session.",
        proposal_id=None,
        reason=None,
        ui_context={"source": "today_mission", "day_id": "2026-03-27"},
    )
    changed = _build_turn_request_hash(
        action="text",
        thread_id=thread_id,
        message="Assess today's session.",
        proposal_id=None,
        reason=None,
        ui_context={"source": "today_mission", "day_id": "2026-03-28"},
    )
    assert base != changed
