import pytest
from pydantic import ValidationError

from api.services.active_plans import set_day_completion


def test_schema_v3_completion_rejects_malformed_artifact_before_mutation():
    day = {"day_id": "day-1", "is_completed": False}
    malformed = {
        "type": "weekly_plan",
        "schema_version": 3,
        "plan_id": "incomplete-plan",
        "weeks": [{"week_id": "week-1", "days": [day]}],
    }

    with pytest.raises(ValidationError):
        set_day_completion(malformed, day_id="day-1", is_completed=True)

    assert day["is_completed"] is False


def test_completion_rejects_unknown_schema_instead_of_guessing():
    with pytest.raises(ValueError, match="Unsupported weekly-plan schema version"):
        set_day_completion({"schema_version": 99, "weeks": []}, day_id="day-1", is_completed=True)


def test_legacy_completion_shape_remains_unchanged():
    legacy = {"schema_version": 1, "weeks": [{"days": [{"day_id": "day-1", "is_completed": False}]}]}

    updated = set_day_completion(legacy, day_id="day-1", is_completed=True)

    assert updated == {"schema_version": 1, "weeks": [{"days": [{"day_id": "day-1", "is_completed": True}]}]}
