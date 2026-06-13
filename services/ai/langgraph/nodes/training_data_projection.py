from datetime import UTC, datetime
from typing import Any

from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _without_empty(payload: dict[str, Any]) -> dict[str, Any]:
    filtered: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, (dict, list)) and not value:
            continue
        filtered[key] = value
    return filtered


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _timestamp_second(value: object) -> str | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat()


def _sort_key(payload: dict[str, Any]) -> datetime:
    parsed = _parse_datetime(payload.get("start"))
    if parsed is None:
        return datetime.min.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _date_sort_key(value: object) -> datetime:
    parsed = _parse_datetime(str(value)) if value is not None else None
    if parsed is None:
        return datetime.min.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _source_names(training_data: dict[str, Any]) -> list[str]:
    return sorted(name for name in _as_dict(training_data.get("sources")).keys() if isinstance(name, str))


def compact_training_data_for_state(training_data: object) -> dict[str, Any]:
    training_data_dict = _as_dict(training_data)
    return _without_empty(
        {
            "generated_at_utc": training_data_dict.get("generated_at_utc"),
            "sources_present": _source_names(training_data_dict),
            "source_gaps": training_data_dict.get("source_gaps", []),
            "evidence_profile": training_data_dict.get("evidence_profile", {}),
        }
    )


def _lean_strava_activity(activity: dict[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "distance_m": activity.get("distance"),
            "moving_time_s": activity.get("moving_time"),
            "elapsed_time_s": activity.get("elapsed_time"),
            "elevation_gain_m": activity.get("total_elevation_gain"),
            "average_speed_mps": activity.get("average_speed"),
            "max_speed_mps": activity.get("max_speed"),
            "average_cadence": activity.get("average_cadence"),
            "average_temp_c": activity.get("average_temp"),
            "average_watts": activity.get("average_watts"),
            "max_watts": activity.get("max_watts"),
            "weighted_average_watts": activity.get("weighted_average_watts"),
            "kilojoules": activity.get("kilojoules"),
            "average_heartrate": activity.get("average_heartrate"),
            "max_heartrate": activity.get("max_heartrate"),
            "device_watts": activity.get("device_watts"),
            "elev_high_m": activity.get("elev_high"),
            "elev_low_m": activity.get("elev_low"),
        }
    )


def _lean_whoop_workout(workout: dict[str, Any]) -> dict[str, Any]:
    score = _as_dict(workout.get("score"))
    return _without_empty(
        {
            "end": workout.get("end"),
            "sport_name": workout.get("sport_name"),
            "strain": score.get("strain"),
            "average_heart_rate": score.get("average_heart_rate"),
            "max_heart_rate": score.get("max_heart_rate"),
            "kilojoule": score.get("kilojoule"),
            "percent_recorded": score.get("percent_recorded"),
            "distance_meter": score.get("distance_meter"),
            "altitude_gain_meter": score.get("altitude_gain_meter"),
            "altitude_change_meter": score.get("altitude_change_meter"),
            "zone_durations": score.get("zone_durations"),
        }
    )


def _lean_whoop_cycle(cycle: dict[str, Any]) -> dict[str, Any]:
    score = _as_dict(cycle.get("score"))
    return _without_empty(
        {
            "start": cycle.get("start"),
            "end": cycle.get("end"),
            "strain": score.get("strain"),
            "kilojoule": score.get("kilojoule"),
            "average_heart_rate": score.get("average_heart_rate"),
            "max_heart_rate": score.get("max_heart_rate"),
        }
    )


def _lean_whoop_sleep(sleep: dict[str, Any]) -> dict[str, Any]:
    score = _as_dict(sleep.get("score"))
    stage_summary = _as_dict(score.get("stage_summary"))
    sleep_needed = _as_dict(score.get("sleep_needed"))
    return _without_empty(
        {
            "start": sleep.get("start"),
            "end": sleep.get("end"),
            "nap": sleep.get("nap"),
            "total_in_bed_time_milli": stage_summary.get("total_in_bed_time_milli"),
            "total_awake_time_milli": stage_summary.get("total_awake_time_milli"),
            "total_light_sleep_time_milli": stage_summary.get("total_light_sleep_time_milli"),
            "total_slow_wave_sleep_time_milli": stage_summary.get("total_slow_wave_sleep_time_milli"),
            "total_rem_sleep_time_milli": stage_summary.get("total_rem_sleep_time_milli"),
            "sleep_cycle_count": stage_summary.get("sleep_cycle_count"),
            "disturbance_count": stage_summary.get("disturbance_count"),
            "baseline_sleep_need_milli": sleep_needed.get("baseline_milli"),
            "sleep_debt_need_milli": sleep_needed.get("need_from_sleep_debt_milli"),
            "recent_strain_need_milli": sleep_needed.get("need_from_recent_strain_milli"),
            "recent_nap_need_milli": sleep_needed.get("need_from_recent_nap_milli"),
            "respiratory_rate": score.get("respiratory_rate"),
            "sleep_performance_percentage": score.get("sleep_performance_percentage"),
            "sleep_consistency_percentage": score.get("sleep_consistency_percentage"),
            "sleep_efficiency_percentage": score.get("sleep_efficiency_percentage"),
        }
    )


def _lean_whoop_recovery(
    recovery: dict[str, Any],
    *,
    cycles_by_id: dict[Any, dict[str, Any]],
    sleeps_by_id: dict[Any, dict[str, Any]],
) -> dict[str, Any]:
    score = _as_dict(recovery.get("score"))
    cycle = cycles_by_id.get(recovery.get("cycle_id"), {})
    sleep = sleeps_by_id.get(recovery.get("sleep_id"), {})
    return _without_empty(
        {
            "cycle_start": cycle.get("start"),
            "cycle_end": cycle.get("end"),
            "sleep_start": sleep.get("start"),
            "sleep_end": sleep.get("end"),
            "user_calibrating": score.get("user_calibrating"),
            "recovery_score": score.get("recovery_score"),
            "resting_heart_rate": score.get("resting_heart_rate"),
            "hrv_rmssd_milli": score.get("hrv_rmssd_milli"),
            "spo2_percentage": score.get("spo2_percentage"),
            "skin_temp_celsius": score.get("skin_temp_celsius"),
        }
    )


def _lean_profile(profile: object) -> dict[str, Any]:
    profile_dict = _as_dict(profile)
    metadata_keys = {
        "id",
        "user_id",
        "email",
        "first_name",
        "last_name",
        "created_at",
        "updated_at",
        "resource_state",
        "profile",
        "profile_medium",
    }
    return _without_empty(
        {
            key: value
            for key, value in profile_dict.items()
            if key not in metadata_keys and not key.endswith("_id")
        }
    )


def build_canonical_activity_sessions(training_data: dict[str, Any]) -> list[dict[str, Any]]:
    sources = _as_dict(training_data.get("sources"))
    strava = _as_dict(sources.get("strava"))
    whoop = _as_dict(sources.get("whoop"))

    whoop_workouts = [_as_dict(workout) for workout in _as_list(whoop.get("workouts"))]
    whoop_by_start = {
        timestamp: workout
        for workout in whoop_workouts
        if (timestamp := _timestamp_second(workout.get("start"))) is not None
    }
    used_whoop_starts: set[str] = set()
    sessions: list[dict[str, Any]] = []

    for activity in [_as_dict(item) for item in _as_list(strava.get("recent_activities"))]:
        start = activity.get("start_date")
        whoop_start = _timestamp_second(start)
        whoop_workout = whoop_by_start.get(whoop_start) if whoop_start is not None else None
        if whoop_start is not None and whoop_workout is not None:
            used_whoop_starts.add(whoop_start)

        sessions.append(
            _without_empty(
                {
                    "start": start,
                    "sport": activity.get("sport_type") or activity.get("type"),
                    "title": activity.get("name"),
                    "sources": ["strava", "whoop"] if whoop_workout else ["strava"],
                    "strava": _lean_strava_activity(activity),
                    "whoop": _lean_whoop_workout(whoop_workout) if whoop_workout else None,
                }
            )
        )

    for workout in whoop_workouts:
        whoop_start = _timestamp_second(workout.get("start"))
        if whoop_start is not None and whoop_start in used_whoop_starts:
            continue
        sessions.append(
            _without_empty(
                {
                    "start": workout.get("start"),
                    "sport": workout.get("sport_name"),
                    "sources": ["whoop"],
                    "whoop": _lean_whoop_workout(workout),
                }
            )
        )

    return sorted(sessions, key=_sort_key, reverse=True)


def project_metrics_data(state: TrainingAnalysisState) -> dict[str, Any]:
    training_data = _as_dict(state.get("training_data"))
    sources = _as_dict(training_data.get("sources"))
    strava = _as_dict(sources.get("strava"))
    whoop = _as_dict(sources.get("whoop"))

    return {
        **compact_training_data_for_state(training_data),
        "strava": _without_empty(
            {
                "training_load_history": strava.get("training_load_history", []),
                "activity_summary": strava.get("activity_summary", {}),
                "athlete_profile": _lean_profile(strava.get("athlete_profile")),
            }
        ),
        "whoop": _without_empty(
            {
                "cycles": [_lean_whoop_cycle(_as_dict(cycle)) for cycle in _as_list(whoop.get("cycles"))],
                "profile_basic": _lean_profile(whoop.get("profile_basic")),
            }
        ),
    }


def project_activity_data(state: TrainingAnalysisState) -> dict[str, Any]:
    training_data = _as_dict(state.get("training_data"))
    return {
        **compact_training_data_for_state(training_data),
        "activities": build_canonical_activity_sessions(training_data),
    }


def project_physiology_data(state: TrainingAnalysisState) -> dict[str, Any]:
    training_data = _as_dict(state.get("training_data"))
    sources = _as_dict(training_data.get("sources"))
    strava = _as_dict(sources.get("strava"))
    whoop = _as_dict(sources.get("whoop"))
    cycles = [_as_dict(cycle) for cycle in _as_list(whoop.get("cycles"))]
    sleeps = [_as_dict(sleep) for sleep in _as_list(whoop.get("sleeps"))]
    recoveries = [_as_dict(recovery) for recovery in _as_list(whoop.get("recoveries"))]
    has_measured_biometrics = bool(sleeps or recoveries)

    cycles_by_id = {cycle.get("id"): cycle for cycle in cycles if cycle.get("id") is not None}
    sleeps_by_id = {sleep.get("id"): sleep for sleep in sleeps if sleep.get("id") is not None}

    payload = {
        **compact_training_data_for_state(training_data),
        "whoop": _without_empty(
            {
                "profile_basic": _lean_profile(whoop.get("profile_basic")),
                "body_measurement": _lean_profile(whoop.get("body_measurement")),
                "recoveries": [
                    _lean_whoop_recovery(
                        recovery,
                        cycles_by_id=cycles_by_id,
                        sleeps_by_id=sleeps_by_id,
                    )
                    for recovery in recoveries
                ],
                "sleeps": [_lean_whoop_sleep(sleep) for sleep in sleeps],
            }
        ),
    }

    if not has_measured_biometrics:
        payload["proxy_activity_signals"] = _without_empty(
            {
                "strava_activity_summary": strava.get("activity_summary", {}),
                "strava_training_load_history": strava.get("training_load_history", []),
                "whoop_cycles": [_lean_whoop_cycle(cycle) for cycle in cycles],
            }
        )

    return payload


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _format_number(value: object, *, digits: int = 1) -> str | None:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return None
    if numeric_value.is_integer():
        return str(int(numeric_value))
    return f"{numeric_value:.{digits}f}"


def _format_minutes(seconds: object) -> str | None:
    numeric_value = _as_float(seconds)
    if numeric_value is None:
        return None
    return f"{round(numeric_value / 60)} min"


def _format_distance_km(meters: object) -> str | None:
    numeric_value = _as_float(meters)
    if numeric_value is None:
        return None
    return f"{numeric_value / 1000:.1f} km"


def _session_transition_line(session: dict[str, Any]) -> str:
    strava = _as_dict(session.get("strava"))
    whoop = _as_dict(session.get("whoop"))

    label_parts = [
        str(session.get("start") or "unknown date")[:10],
        str(session.get("sport") or "activity"),
    ]
    if session.get("title"):
        label_parts.append(str(session["title"]))

    detail_parts = [
        _format_minutes(strava.get("moving_time_s") or strava.get("elapsed_time_s")),
        _format_distance_km(strava.get("distance_m") or whoop.get("distance_meter")),
    ]

    average_heart_rate = _format_number(strava.get("average_heartrate") or whoop.get("average_heart_rate"))
    if average_heart_rate is not None:
        detail_parts.append(f"avg HR {average_heart_rate}")

    average_watts = _format_number(
        strava.get("weighted_average_watts") or strava.get("average_watts"),
    )
    if average_watts is not None:
        detail_parts.append(f"avg watts {average_watts}")

    strain = _format_number(whoop.get("strain"))
    if strain is not None:
        detail_parts.append(f"WHOOP strain {strain}")

    details = " | ".join(part for part in detail_parts if part)
    suffix = f" - {details}" if details else ""
    return f"- {' | '.join(label_parts)}{suffix}"


def _load_value(load_entry: dict[str, Any]) -> float | None:
    for key in (
        "load_value",
        "relative_effort_total",
        "suffer_score_total",
        "strain_total",
        "activity_count",
    ):
        numeric_value = _as_float(load_entry.get(key))
        if numeric_value is not None:
            return numeric_value
    return None


def _load_transition_line(load_entry: dict[str, Any]) -> str:
    label = str(load_entry.get("date") or load_entry.get("start") or "unknown date")[:10]
    parts = [label]

    load_value = _load_value(load_entry)
    if load_value is not None:
        load_type = load_entry.get("load_type")
        load_label = f"load {load_value:.1f}" if not load_value.is_integer() else f"load {int(load_value)}"
        if isinstance(load_type, str) and load_type:
            load_label += f" ({load_type})"
        parts.append(load_label)

    activity_count = _format_number(load_entry.get("activity_count"), digits=0)
    if activity_count is not None:
        parts.append(f"activities {activity_count}")

    moving_minutes = _format_number(load_entry.get("moving_time_minutes_total"))
    if moving_minutes is not None:
        parts.append(f"moving min {moving_minutes}")

    distance_km = _format_distance_km(load_entry.get("distance_m_total"))
    if distance_km is not None:
        parts.append(distance_km)

    return f"- {' | '.join(parts)}"


def _load_window_total(load_entries: list[dict[str, Any]]) -> float | None:
    values = [_load_value(entry) for entry in load_entries]
    known_values = [value for value in values if value is not None]
    if not known_values:
        return None
    return sum(known_values)


def _recovery_transition_line(recovery: dict[str, Any]) -> str:
    score = _as_dict(recovery.get("score"))
    label = str(recovery.get("created_at") or recovery.get("updated_at") or recovery.get("cycle_id") or "unknown")[:10]
    parts = [label]

    recovery_score = _format_number(score.get("recovery_score"))
    if recovery_score is not None:
        parts.append(f"recovery {recovery_score}")

    hrv = _format_number(score.get("hrv_rmssd_milli"))
    if hrv is not None:
        parts.append(f"HRV {hrv} ms")

    resting_heart_rate = _format_number(score.get("resting_heart_rate"))
    if resting_heart_rate is not None:
        parts.append(f"RHR {resting_heart_rate}")

    return f"- {' | '.join(parts)}"


def _truncate_context(value: str, *, limit: int = 12000) -> str:
    stripped = value.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[:limit].rstrip() + "\n\n[truncated existing plan context]"


def build_training_transition_context(
    training_data: object,
    *,
    current_date: dict[str, str] | None = None,
    existing_weekly_plan: str | None = None,
) -> str:
    """Build compact runtime context that prevents fresh-plan resets.

    The payload is descriptive only: it preserves recent evidence and the active
    block context, while leaving training decisions to the planner agents.
    """
    training_data_dict = _as_dict(training_data)
    sources = _as_dict(training_data_dict.get("sources"))
    strava = _as_dict(sources.get("strava"))
    whoop = _as_dict(sources.get("whoop"))

    lines = [
        "## Transition Context",
        "",
        "Purpose: preserve continuity from the current training state into the next 28-day plan.",
        "Use this together with expert outputs. It is evidence for continuity, not a deterministic prescription.",
    ]

    if current_date and current_date.get("date"):
        lines.extend(["", f"- Generation date: {current_date['date']}"])

    sessions = build_canonical_activity_sessions(training_data_dict)[:10]
    if sessions:
        lines.extend(["", "### Recent Executed Sessions (newest first)"])
        lines.extend(_session_transition_line(session) for session in sessions)
    else:
        lines.extend(["", "### Recent Executed Sessions", "- No recent executed sessions in the extracted window."])

    load_entries = sorted(
        [_as_dict(entry) for entry in _as_list(strava.get("training_load_history"))],
        key=lambda entry: _date_sort_key(entry.get("date") or entry.get("start")),
        reverse=True,
    )[:14]
    if load_entries:
        lines.extend(["", "### Recent Training Load (newest first)"])
        lines.extend(_load_transition_line(entry) for entry in load_entries)

        recent_total = _load_window_total(load_entries[:7])
        previous_total = _load_window_total(load_entries[7:14])
        if recent_total is not None:
            if previous_total is not None:
                lines.append(f"- Recent 7-entry load total: {recent_total:.1f}; previous 7-entry total: {previous_total:.1f}")
            else:
                lines.append(f"- Recent 7-entry load total: {recent_total:.1f}")

    recoveries = sorted(
        [_as_dict(recovery) for recovery in _as_list(whoop.get("recoveries"))],
        key=lambda recovery: _date_sort_key(recovery.get("created_at") or recovery.get("updated_at")),
        reverse=True,
    )[:5]
    if recoveries:
        lines.extend(["", "### Recent WHOOP Recovery (newest first)"])
        lines.extend(_recovery_transition_line(recovery) for recovery in recoveries)

    if existing_weekly_plan and existing_weekly_plan.strip():
        lines.extend(
            [
                "",
                "### Existing Active Weekly Plan / Current Block",
                "This is the compact plan context the new block is replacing or extending. Use it to avoid repeating an already-absorbed easy reset.",
                "```markdown",
                _truncate_context(existing_weekly_plan),
                "```",
            ]
        )

    lines.extend(
        [
            "",
            "### Continuity Handling",
            "- Do not treat the next 28-day plan as a fresh onboarding block by default.",
            "- Let recent executed load, recent planned intensity, and recovery signals determine the first 3-7 days.",
            "- If recent days were already low stress and readiness supports it, consider continuing progression rather than repeating generic easy days.",
            "- If recent load or physiology shows unresolved fatigue, absorb first and state why.",
        ]
    )

    return "\n".join(lines).strip()


async def training_data_compaction_node(state: TrainingAnalysisState) -> dict[str, Any]:
    return {"training_data": compact_training_data_for_state(state.get("training_data"))}
