from typing import cast

from api.services.evidence_profile import build_evidence_profile


def test_build_evidence_profile_for_no_connected_sources_declared_only():
    payload = build_evidence_profile()
    dimensions = cast("dict[str, dict[str, object]]", payload["dimensions"])
    claims_policy = cast("dict[str, object]", payload["claims_policy"])

    assert payload["connected_mode"] == "none"
    assert dimensions["activity_history"]["availability"] == "none"
    assert dimensions["training_load"]["availability"] == "none"
    assert dimensions["recovery_biometrics"]["availability"] == "none"
    assert claims_policy["has_connected_training_source"] is False
    assert claims_policy["can_use_declared_profile_claims"] is True
    assert claims_policy["can_use_declared_goal_claims"] is True
    assert claims_policy["should_acknowledge_no_connected_sources"] is True
    assert claims_policy["should_frame_activity_load_as_unavailable"] is True
    assert claims_policy["should_frame_recovery_readiness_as_unavailable"] is True


def test_build_evidence_profile_for_strava_only():
    payload = build_evidence_profile(available_sources=["strava"])
    dimensions = cast("dict[str, dict[str, object]]", payload["dimensions"])
    claims_policy = cast("dict[str, object]", payload["claims_policy"])

    assert payload["connected_mode"] == "strava_only"
    assert dimensions["activity_history"]["availability"] == "strong"
    assert dimensions["readiness_guidance"]["availability"] == "proxy_only"
    assert claims_policy["can_make_activity_completeness_claims"] is True
    assert claims_policy["can_make_readiness_claims"] is False


def test_build_evidence_profile_for_whoop_only():
    payload = build_evidence_profile(available_sources=["whoop"])
    dimensions = cast("dict[str, dict[str, object]]", payload["dimensions"])
    claims_policy = cast("dict[str, object]", payload["claims_policy"])

    assert payload["connected_mode"] == "whoop_only"
    assert dimensions["activity_history"]["availability"] == "partial"
    assert dimensions["recovery_biometrics"]["availability"] == "strong"
    assert claims_policy["should_acknowledge_missing_activity_history"] is True
    assert claims_policy["can_make_readiness_claims"] is True


def test_build_evidence_profile_for_both():
    payload = build_evidence_profile(available_sources=["strava", "whoop"])
    dimensions = cast("dict[str, dict[str, object]]", payload["dimensions"])
    claims_policy = cast("dict[str, object]", payload["claims_policy"])

    assert payload["connected_mode"] == "both"
    assert dimensions["activity_history"]["availability"] == "strong"
    assert dimensions["recovery_biometrics"]["availability"] == "strong"
    assert claims_policy["can_make_activity_completeness_claims"] is True
    assert claims_policy["can_make_readiness_claims"] is True
