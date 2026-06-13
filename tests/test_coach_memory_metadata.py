from datetime import UTC, datetime

from api.services.coach_memory_metadata import derive_memory_freshness, extract_transient_state_notes


def test_derive_memory_freshness_returns_none_when_meta_absent():
    updated_at, age_days = derive_memory_freshness({}, now=datetime(2026, 2, 28, tzinfo=UTC))
    assert updated_at is None
    assert age_days is None


def test_extract_transient_state_notes_normalizes_and_filters_invalid_rows():
    athlete_model = {
        "transient_state_notes": [
            {
                "topic": "illness",
                "status": "recovering",
                "summary": "Cold symptoms improving.",
                "first_observed_at": "2026-02-20T08:00:00",
                "last_observed_at": "2026-02-23T09:30:00+00:00",
            },
            {"topic": "", "summary": "missing topic"},
            "invalid",
        ]
    }

    notes = extract_transient_state_notes(athlete_model)

    assert len(notes) == 1
    assert notes[0]["topic"] == "illness"
    assert notes[0]["status"] == "recovering"
    assert notes[0]["first_observed_at"] == "2026-02-20T08:00:00+00:00"
    assert notes[0]["last_observed_at"] == "2026-02-23T09:30:00+00:00"
