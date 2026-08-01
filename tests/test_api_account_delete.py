import uuid
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException


class _RecordingDb:
    def __init__(self):
        self.statements = []
        self.info = {}
        self.committed = False
        self.rollback_calls = 0

    async def execute(self, stmt, *_args, **_kwargs):
        self.statements.append(stmt)
        return SimpleNamespace(
            scalar_one_or_none=lambda: None,
            one_or_none=lambda: None,
        )

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rollback_calls += 1


def _statement_index(statements: list[object], prefix: str) -> int:
    for index, statement in enumerate(statements):
        if str(statement).startswith(prefix):
            return index
    raise AssertionError(f"Statement not found: {prefix}")


@pytest.fixture(autouse=True)
def _allow_local_data_delete(monkeypatch):
    from api.services import account_deletion

    monkeypatch.setattr(account_deletion, "_local_data_delete_allowed", lambda: True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_account_resets_local_data_preserves_user_and_commits(monkeypatch):
    from api.services import account_deletion

    user_id = uuid.uuid4()
    fake_db = _RecordingDb()

    async def fake_load_user_for_deletion(*_args, **_kwargs):
        return SimpleNamespace(id=user_id)

    monkeypatch.setattr(account_deletion, "_load_user_for_deletion", fake_load_user_for_deletion)

    response = await account_deletion.delete_account_and_data(db=fake_db, user_id=user_id)  # type: ignore[arg-type]

    assert response == {"status": "reset", "redirect_path": "/delete?status=reset"}
    assert fake_db.committed is True
    user_deletes = [stmt for stmt in fake_db.statements if str(stmt).startswith("DELETE FROM users")]
    assert user_deletes == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_account_removes_coach_event_dependents_before_events():
    from api.services.account_deletion import _delete_local_account_records

    fake_db = _RecordingDb()

    await _delete_local_account_records(db=fake_db, user_id=uuid.uuid4())  # type: ignore[arg-type]

    checkpoint_writes_index = _statement_index(fake_db.statements, "DELETE FROM checkpoint_writes")
    coach_turn_runs_index = _statement_index(fake_db.statements, "DELETE FROM coach_turn_runs")
    ai_run_costs_index = _statement_index(fake_db.statements, "DELETE FROM ai_run_costs")
    daily_update_runs_index = _statement_index(fake_db.statements, "DELETE FROM daily_update_runs")
    weekly_recap_runs_index = _statement_index(fake_db.statements, "DELETE FROM weekly_recap_runs")
    coach_events_index = _statement_index(fake_db.statements, "DELETE FROM coach_events")
    coach_threads_index = _statement_index(fake_db.statements, "DELETE FROM coach_threads")

    assert checkpoint_writes_index < coach_turn_runs_index
    assert ai_run_costs_index < coach_events_index
    assert coach_turn_runs_index < coach_events_index
    assert daily_update_runs_index < coach_events_index
    assert weekly_recap_runs_index < coach_events_index
    assert coach_turn_runs_index < coach_threads_index


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_reset_skips_remote_auth_cleanup_and_preserves_owner_user(monkeypatch):
    from api.services import account_deletion

    user_id = uuid.uuid4()
    fake_db = _RecordingDb()

    async def fake_load_user_for_deletion(*_args, **_kwargs):
        return SimpleNamespace(id=user_id)

    monkeypatch.setattr(account_deletion, "_load_user_for_deletion", fake_load_user_for_deletion)

    response = await account_deletion.delete_account_and_data(db=fake_db, user_id=user_id)  # type: ignore[arg-type]

    assert response == {"status": "reset", "redirect_path": "/delete?status=reset"}
    assert fake_db.committed is True
    user_deletes = [stmt for stmt in fake_db.statements if str(stmt).startswith("DELETE FROM users")]
    assert user_deletes == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_account_performs_local_reset_without_remote_provider_calls(monkeypatch):
    from api.services import account_deletion

    user_id = uuid.uuid4()
    fake_db = _RecordingDb()
    call_order: list[str] = []

    async def fake_load_user_for_deletion(*_args, **_kwargs):
        return SimpleNamespace(id=user_id)

    async def fake_delete_local(*_args, **kwargs):
        assert kwargs["delete_user"] is False
        call_order.append("delete_local")

    monkeypatch.setattr(account_deletion, "_load_user_for_deletion", fake_load_user_for_deletion)
    monkeypatch.setattr(account_deletion, "_delete_local_account_records", fake_delete_local)

    response = await account_deletion.delete_account_and_data(db=fake_db, user_id=user_id)  # type: ignore[arg-type]

    assert response == {"status": "reset", "redirect_path": "/delete?status=reset"}
    assert call_order == ["delete_local"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_account_blocks_local_delete_unless_explicitly_enabled(monkeypatch):
    from api.services import account_deletion

    monkeypatch.setattr(account_deletion, "_local_data_delete_allowed", lambda: False)

    with pytest.raises(HTTPException) as exc_info:
        await account_deletion.delete_account_and_data(db=_RecordingDb(), user_id=uuid.uuid4())  # type: ignore[arg-type]

    assert exc_info.value.status_code == 403
    detail = cast("dict[str, object]", exc_info.value.detail)
    assert detail["code"] == "local_data_delete_disabled"
