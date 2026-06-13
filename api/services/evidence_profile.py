from __future__ import annotations

from collections.abc import Iterable, Mapping

_CANONICAL_PROVIDER_ORDER = ("strava", "whoop")
_PROVIDER_CAPABILITIES = {
    "strava": ("activity_history", "activity_detail", "training_load", "readiness_proxy"),
    "whoop": ("recovery_biometrics", "readiness", "sleep", "activity_context"),
}


def _availability_confidence(availability: str) -> str:
    if availability == "strong":
        return "high"
    if availability in {"partial", "proxy_only"}:
        return "medium"
    return "low"


def _provider_names(
    *,
    available_sources: set[str],
    provider_status: Mapping[str, Mapping[str, object]] | None,
) -> list[str]:
    names: list[str] = list(_CANONICAL_PROVIDER_ORDER)
    for source_name in sorted(available_sources):
        if source_name not in names:
            names.append(source_name)
    if provider_status is not None:
        for source_name in provider_status.keys():
            if source_name not in names:
                names.append(source_name)
    return names


def build_evidence_sources(
    *,
    available_sources: Iterable[str] = (),
    provider_status: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, dict[str, object]]:
    available_source_names = {
        source_name.strip().lower()
        for source_name in available_sources
        if isinstance(source_name, str) and source_name.strip()
    }

    sources: dict[str, dict[str, object]] = {}
    for source_name in _provider_names(
        available_sources=available_source_names,
        provider_status=provider_status,
    ):
        status_payload = provider_status.get(source_name) if provider_status is not None else None
        operational = source_name in available_source_names
        if isinstance(status_payload, Mapping) and "available" in status_payload:
            operational = bool(status_payload.get("available"))
        sources[source_name] = {
            "operational": operational,
            "capabilities": list(_PROVIDER_CAPABILITIES.get(source_name, ())),
        }
    return sources


def build_evidence_profile(
    *,
    available_sources: Iterable[str] = (),
    provider_status: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    sources = build_evidence_sources(
        available_sources=available_sources,
        provider_status=provider_status,
    )
    strava_operational = bool(sources.get("strava", {}).get("operational"))
    whoop_operational = bool(sources.get("whoop", {}).get("operational"))

    connected_mode = "none"
    if strava_operational and whoop_operational:
        connected_mode = "both"
    elif strava_operational:
        connected_mode = "strava_only"
    elif whoop_operational:
        connected_mode = "whoop_only"

    activity_history_availability = "strong" if strava_operational else ("partial" if whoop_operational else "none")
    training_load_availability = "strong" if strava_operational else ("partial" if whoop_operational else "none")
    recovery_biometrics_availability = "strong" if whoop_operational else "none"
    readiness_guidance_availability = "strong" if whoop_operational else ("proxy_only" if strava_operational else "none")

    dimensions = {
        "activity_history": {
            "availability": activity_history_availability,
            "confidence": _availability_confidence(activity_history_availability),
        },
        "training_load": {
            "availability": training_load_availability,
            "confidence": _availability_confidence(training_load_availability),
        },
        "recovery_biometrics": {
            "availability": recovery_biometrics_availability,
            "confidence": _availability_confidence(recovery_biometrics_availability),
        },
        "readiness_guidance": {
            "availability": readiness_guidance_availability,
            "confidence": _availability_confidence(readiness_guidance_availability),
        },
        "subjective_feedback": {
            "availability": "none",
            "confidence": "low",
        },
    }

    claims_policy = {
        "can_make_activity_completeness_claims": strava_operational,
        "can_make_training_load_claims": strava_operational or whoop_operational,
        "can_make_readiness_claims": whoop_operational,
        "can_use_declared_profile_claims": True,
        "can_use_declared_goal_claims": True,
        "has_connected_training_source": strava_operational or whoop_operational,
        "should_acknowledge_missing_recovery_evidence": strava_operational and not whoop_operational,
        "should_acknowledge_missing_activity_history": whoop_operational and not strava_operational,
        "should_acknowledge_no_connected_sources": not strava_operational and not whoop_operational,
        "should_frame_guidance_as_proxy_based": strava_operational and not whoop_operational,
        "should_frame_activity_load_as_unavailable": not strava_operational and not whoop_operational,
        "should_frame_recovery_readiness_as_unavailable": not whoop_operational,
    }

    return {
        "connected_mode": connected_mode,
        "sources": sources,
        "dimensions": dimensions,
        "claims_policy": claims_policy,
    }
