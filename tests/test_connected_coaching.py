from __future__ import annotations

from api.services.connected_coaching import resolve_connected_coaching_gate
from api.services.integration_status import IntegrationsStatus


def _integrations_status(*, strava_operational: bool, whoop_operational: bool, whoop_attention: str | None = None):
    return IntegrationsStatus.model_validate(
        {
            "strava": {
                "linked": strava_operational,
                "ever_connected": strava_operational,
                "connected": strava_operational,
                "operational": strava_operational,
                "state": "connected" if strava_operational else "disconnected",
                "connection_state": "connected_usable" if strava_operational else "disconnected",
                "configured": strava_operational,
                "oauth_enabled": strava_operational,
                "attention_message": None,
            },
            "whoop": {
                "linked": whoop_operational or whoop_attention is not None,
                "ever_connected": whoop_operational or whoop_attention is not None,
                "connected": whoop_operational,
                "operational": whoop_operational,
                "state": "attention_needed" if whoop_attention else ("connected" if whoop_operational else "disconnected"),
                "connection_state": (
                    "token_expired" if whoop_attention else ("connected_usable" if whoop_operational else "disconnected")
                ),
                "configured": whoop_operational or whoop_attention is not None,
                "oauth_enabled": whoop_operational or whoop_attention is not None,
                "attention_message": whoop_attention,
            },
        }
    )


def test_resolve_connected_coaching_gate_uses_settings_target_for_disabled_feature():
    gate = resolve_connected_coaching_gate(
        feature_enabled=False,
        integrations_status=_integrations_status(strava_operational=True, whoop_operational=False),
        locked_message="Coach chat requires connected setup.",
    )

    assert gate.allowed is False
    assert gate.attention_message == "Coach chat requires connected setup."
    assert gate.gate_target == "settings"
    assert gate.evidence_profile["connected_mode"] == "strava_only"


def test_resolve_connected_coaching_gate_allows_connected_source_but_keeps_attention_notice():
    gate = resolve_connected_coaching_gate(
        feature_enabled=True,
        integrations_status=_integrations_status(
            strava_operational=True,
            whoop_operational=False,
            whoop_attention="WHOOP connection expired and cannot refresh. Reconnect WHOOP.",
        ),
        locked_message="Coach chat requires connected setup.",
    )

    assert gate.allowed is True
    assert gate.attention_message == "WHOOP connection expired and cannot refresh. Reconnect WHOOP."
    assert gate.gate_target == "settings"
    assert gate.evidence_profile["connected_mode"] == "strava_only"
