import json
from typing import cast

from services.ai.langgraph.nodes.activity_summarizer_node import extract_activity_data
from services.ai.langgraph.nodes.metrics_summarizer_node import extract_metrics_data
from services.ai.langgraph.nodes.physiology_summarizer_node import extract_physiology_data
from services.ai.langgraph.nodes.training_data_projection import (
    build_training_transition_context,
    compact_training_data_for_state,
)
from services.ai.langgraph.state.training_analysis_state import TrainingAnalysisState


def _sample_state() -> TrainingAnalysisState:
    return cast(
        "TrainingAnalysisState",
        {
            "training_data": {
                "generated_at_utc": "2026-05-11T21:14:07Z",
                "source_gaps": [],
                "evidence_profile": {"connected_mode": "strava_whoop"},
                "sources": {
                    "strava": {
                        "athlete_profile": {"id": 123, "weight": 75.0},
                        "activity_summary": {"count": 1},
                        "training_load_history": [{"date": "2026-05-11", "load_value": 12.3}],
                        "recent_activities": [
                            {
                                "id": 18461012431,
                                "resource_state": 2,
                                "name": "Morning Run",
                                "sport_type": "Run",
                                "start_date": "2026-05-11T08:02:15Z",
                                "distance": 8128.2,
                                "moving_time": 2979,
                                "elapsed_time": 2979,
                                "total_elevation_gain": 51.0,
                                "average_watts": 309.8,
                                "average_heartrate": 146.4,
                                "map": {"summary_polyline": "encoded-polyline"},
                                "upload_id": 19566202235,
                                "external_id": "device_upload_123",
                                "kudos_count": 3,
                            },
                        ],
                    },
                    "whoop": {
                        "profile_basic": {"user_id": 999, "email": "athlete@example.test"},
                        "body_measurement": {"height_meter": 1.8, "weight_kilogram": 75.0},
                        "workouts": [
                            {
                                "id": "workout-1",
                                "user_id": 999,
                                "created_at": "2026-05-11T09:16:29.589Z",
                                "updated_at": "2026-05-11T09:17:52.574Z",
                                "start": "2026-05-11T08:02:15.000Z",
                                "end": "2026-05-11T08:51:54.056Z",
                                "sport_name": "running",
                                "score": {
                                    "strain": 13.9,
                                    "average_heart_rate": 145,
                                    "max_heart_rate": 181,
                                    "zone_durations": {"zone_two_milli": 668980},
                                },
                            },
                        ],
                        "cycles": [
                            {
                                "id": 1490275548,
                                "user_id": 999,
                                "start": "2026-05-10T21:13:52.820Z",
                                "end": None,
                                "score": {"strain": 14.7, "average_heart_rate": 58},
                            },
                        ],
                        "sleeps": [
                            {
                                "id": "sleep-1",
                                "cycle_id": 1490275548,
                                "user_id": 999,
                                "start": "2026-05-10T21:13:52.820Z",
                                "end": "2026-05-11T06:44:20.980Z",
                                "score": {
                                    "sleep_performance_percentage": 82.0,
                                    "stage_summary": {"total_in_bed_time_milli": 34228160},
                                },
                            }
                        ],
                        "recoveries": [
                            {
                                "cycle_id": 1490275548,
                                "sleep_id": "sleep-1",
                                "user_id": 999,
                                "created_at": "2026-05-11T06:56:22.431Z",
                                "score": {
                                    "recovery_score": 87.0,
                                    "resting_heart_rate": 39.0,
                                    "hrv_rmssd_milli": 167.7,
                                },
                            }
                        ],
                    },
                },
            }
        },
    )


def test_activity_projection_merges_provider_sessions_and_drops_vendor_metadata():
    payload = extract_activity_data(_sample_state())

    assert "activities" in payload
    assert len(payload["activities"]) == 1
    assert payload["activities"][0]["sources"] == ["strava", "whoop"]
    assert payload["activities"][0]["strava"]["distance_m"] == 8128.2
    assert payload["activities"][0]["whoop"]["strain"] == 13.9

    serialized = json.dumps(payload)
    assert "summary_polyline" not in serialized
    assert "upload_id" not in serialized
    assert "external_id" not in serialized
    assert "user_id" not in serialized
    assert "created_at" not in serialized


def test_metrics_projection_excludes_activity_detail_domain():
    payload = extract_metrics_data(_sample_state())

    assert payload["strava"]["training_load_history"] == [{"date": "2026-05-11", "load_value": 12.3}]
    assert "recent_activities" not in payload["strava"]
    assert payload["whoop"]["cycles"] == [
        {
            "start": "2026-05-10T21:13:52.820Z",
            "strain": 14.7,
            "average_heart_rate": 58,
        }
    ]


def test_physiology_projection_uses_measured_biometrics_without_load_series():
    payload = extract_physiology_data(_sample_state())

    assert "proxy_activity_signals" not in payload
    assert "cycles" not in payload["whoop"]
    assert payload["whoop"]["recoveries"] == [
        {
            "cycle_start": "2026-05-10T21:13:52.820Z",
            "sleep_start": "2026-05-10T21:13:52.820Z",
            "sleep_end": "2026-05-11T06:44:20.980Z",
            "recovery_score": 87.0,
            "resting_heart_rate": 39.0,
            "hrv_rmssd_milli": 167.7,
        }
    ]


def test_compact_training_data_for_state_keeps_only_context_metadata():
    compacted = compact_training_data_for_state(_sample_state()["training_data"])

    assert compacted == {
        "generated_at_utc": "2026-05-11T21:14:07Z",
        "sources_present": ["strava", "whoop"],
        "evidence_profile": {"connected_mode": "strava_whoop"},
    }


def test_transition_context_preserves_recent_load_sessions_recovery_and_existing_plan():
    context = build_training_transition_context(
        _sample_state()["training_data"],
        current_date={"date": "2026-05-12", "day_name": "Tuesday"},
        existing_weekly_plan="- 2026-05-10 | Easy Run | intensity=low\n- 2026-05-11 | Rest | intensity=rest",
    )

    assert "## Transition Context" in context
    assert "Recent Executed Sessions" in context
    assert "Morning Run" in context
    assert "8.1 km" in context
    assert "Recent Training Load" in context
    assert "load 12.3" in context
    assert "Recent WHOOP Recovery" in context
    assert "recovery 87" in context
    assert "Existing Active Weekly Plan" in context
    assert "intensity=low" in context
    assert "first 3-7 days" in context
