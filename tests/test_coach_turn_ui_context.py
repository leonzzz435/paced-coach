import uuid
from types import SimpleNamespace

import pytest

from api.services.coach_turn import _resolve_turn_ui_context


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, *, active_weekly):
        self._active_weekly = active_weekly

    async def execute(self, _statement):
        return _FakeResult(self._active_weekly)


def _active_weekly_plan_row():
    return SimpleNamespace(
        plan_data={
            "type": "weekly_plan",
            "plan_id": "plan-1",
            "schema_version": 1,
            "version": 7,
            "athlete_name": "Runner",
            "global_blocks": [],
            "weeks": [
                {
                    "week_id": "wk-2026-03-27",
                    "week_label": "Build",
                    "week_theme": "Consistency",
                    "start_date": "2026-03-27",
                    "end_date": "2026-04-02",
                    "notes_blocks": [],
                    "days": [
                        {
                            "day_id": "2026-03-27",
                            "date": "2026-03-27",
                            "day_label": "Fri - Strength-Endurance",
                            "focus_type": "strength-endurance",
                            "workout_title": "Strength-Endurance",
                            "blocks": [],
                            "estimated_duration_min": 75,
                            "estimated_intensity": "high",
                            "readiness_note": "Go if legs feel normal.",
                            "is_completed": False,
                        }
                    ],
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_resolve_turn_ui_context_returns_validated_today_mission_day():
    payload = await _resolve_turn_ui_context(
        _FakeDb(active_weekly=_active_weekly_plan_row()),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        ui_context={
            "source": "today_mission",
            "day_id": "2026-03-27",
            "week_id": "wk-2026-03-27",
            "date": "2026-03-27",
            "day_label": "Something stale from the browser",
        },
    )

    assert payload == {
        "source": "today_mission",
        "day": {
            "day_id": "2026-03-27",
            "date": "2026-03-27",
            "day_label": "Fri - Strength-Endurance",
            "workout_title": "Strength-Endurance",
            "focus_type": "strength-endurance",
            "estimated_duration_min": 75,
            "estimated_intensity": "high",
            "readiness_note": "Go if legs feel normal.",
            "is_completed": False,
            "week_id": "wk-2026-03-27",
            "week_label": "Build",
            "week_theme": "Consistency",
        },
    }


@pytest.mark.asyncio
async def test_resolve_turn_ui_context_rejects_mismatched_week_id():
    payload = await _resolve_turn_ui_context(
        _FakeDb(active_weekly=_active_weekly_plan_row()),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
        ui_context={
            "source": "today_mission",
            "day_id": "2026-03-27",
            "week_id": "wk-2026-03-20",
        },
    )

    assert payload is None
