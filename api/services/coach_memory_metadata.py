from __future__ import annotations

from datetime import UTC, datetime


def _as_utc_datetime(raw_value: object) -> datetime | None:
    if isinstance(raw_value, datetime):
        parsed = raw_value
    elif isinstance(raw_value, str):
        try:
            parsed = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def derive_memory_freshness(athlete_model: object, *, now: datetime) -> tuple[str | None, int | None]:
    if not isinstance(athlete_model, dict):
        return None, None
    meta = athlete_model.get("_meta")
    if not isinstance(meta, dict):
        return None, None

    updated_at = _as_utc_datetime(meta.get("updated_at"))
    if updated_at is None:
        return None, None

    age_days = max((now - updated_at).days, 0)
    return updated_at.isoformat(), age_days


def extract_transient_state_notes(athlete_model: object) -> list[dict[str, str | None]]:
    if not isinstance(athlete_model, dict):
        return []
    raw_notes = athlete_model.get("transient_state_notes")
    if not isinstance(raw_notes, list):
        return []

    normalized: list[dict[str, str | None]] = []
    for note in raw_notes:
        if not isinstance(note, dict):
            continue
        topic = str(note.get("topic", "")).strip()
        summary = str(note.get("summary", "")).strip()
        if not topic or not summary:
            continue
        status = str(note.get("status", "unknown")).strip().lower() or "unknown"
        normalized.append(
            {
                "topic": topic,
                "status": status,
                "summary": summary,
                "first_observed_at": (
                    parsed.isoformat()
                    if (parsed := _as_utc_datetime(note.get("first_observed_at"))) is not None
                    else None
                ),
                "last_observed_at": (
                    parsed.isoformat()
                    if (parsed := _as_utc_datetime(note.get("last_observed_at"))) is not None
                    else None
                ),
            }
        )
    return normalized
