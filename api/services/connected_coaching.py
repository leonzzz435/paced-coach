from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException

from api.services.evidence_profile import build_evidence_profile
from api.services.integration_status import (
    IntegrationsStatus,
    training_provider_notice_message,
    training_provider_requirement_message,
)

GateTarget = Literal["settings"]


@dataclass(frozen=True)
class ConnectedCoachingGateState:
    allowed: bool
    attention_message: str | None
    gate_target: GateTarget | None
    evidence_profile: dict[str, object]


def _provider_status_payload(status: IntegrationsStatus) -> dict[str, dict[str, object]]:
    return {
        "strava": {
            "available": status.strava.operational,
            "state": status.strava.state,
            "linked": status.strava.linked,
        },
        "whoop": {
            "available": status.whoop.operational,
            "state": status.whoop.state,
            "linked": status.whoop.linked,
        },
    }


def resolve_connected_coaching_gate(
    *,
    feature_enabled: bool,
    integrations_status: IntegrationsStatus,
    locked_message: str,
) -> ConnectedCoachingGateState:
    evidence_profile = build_evidence_profile(
        provider_status=_provider_status_payload(integrations_status),
    )
    connected_mode = str(evidence_profile.get("connected_mode") or "none").strip().lower()
    has_relevant_evidence = connected_mode != "none"
    provider_notice = training_provider_notice_message(integrations_status)

    if not feature_enabled:
        return ConnectedCoachingGateState(
            allowed=False,
            attention_message=locked_message,
            gate_target="settings",
            evidence_profile=evidence_profile,
        )

    if not has_relevant_evidence:
        return ConnectedCoachingGateState(
            allowed=False,
            attention_message=provider_notice or training_provider_requirement_message(integrations_status),
            gate_target="settings",
            evidence_profile=evidence_profile,
        )

    if provider_notice:
        return ConnectedCoachingGateState(
            allowed=True,
            attention_message=provider_notice,
            gate_target="settings",
            evidence_profile=evidence_profile,
        )

    return ConnectedCoachingGateState(
        allowed=True,
        attention_message=None,
        gate_target=None,
        evidence_profile=evidence_profile,
    )


def assert_connected_coaching_available(
    *,
    feature_enabled: bool,
    integrations_status: IntegrationsStatus,
    locked_message: str,
) -> ConnectedCoachingGateState:
    gate_state = resolve_connected_coaching_gate(
        feature_enabled=feature_enabled,
        integrations_status=integrations_status,
        locked_message=locked_message,
    )
    if gate_state.allowed:
        return gate_state

    raise HTTPException(status_code=400, detail=gate_state.attention_message or locked_message)
