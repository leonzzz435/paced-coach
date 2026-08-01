from pathlib import Path

import pytest

from services.ai.evals.head_coach_eval import load_eval_suite


@pytest.mark.unit
def test_public_api_excludes_training_data_provider_routes(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")

    from api.config import get_settings
    from api.main import create_app

    get_settings.cache_clear()
    route_paths = {path for route in create_app().routes if (path := getattr(route, "path", None)) is not None}

    excluded_paths = {
        "/api/oauth/strava/start",
        "/api/oauth/strava/callback",
        "/api/oauth/whoop/start",
        "/api/oauth/whoop/callback",
        "/api/integrations/status",
        "/api/account/strava/disconnect",
        "/api/account/whoop/disconnect",
        "/api/daily/run",
        "/api/weekly-recap/latest",
    }

    assert route_paths.isdisjoint(excluded_paths)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coach_registry_never_loads_external_training_providers():
    from api.services.ongoing_tools import build_ongoing_tool_registry

    async with build_ongoing_tool_registry(
        object(),  # type: ignore[arg-type]
        user_id="owner-1",
    ) as registry:
        assert registry.registered_tool_names() == {
            "get_athlete_profile",
            "get_current_season_plan",
            "get_current_weekly_plan",
            "get_upcoming_competitions",
        }


@pytest.mark.unit
def test_local_first_eval_cases_forbid_fabricated_external_evidence():
    suite = load_eval_suite(Path("tests/fixtures/head_coach_eval_cases.json"))
    provider_free_cases = {
        case.scenario_id: case.required_invariants
        for case in suite.cases
        if "no_fabricated_provider_evidence" in case.required_invariants
    }

    assert provider_free_cases == {
        "missed_training_week": [
            "schema_valid",
            "athlete_report_used",
            "no_fabricated_provider_evidence",
        ],
        "optional_evidence_unavailable": [
            "schema_valid",
            "tool_gap_disclosed",
            "no_fabricated_provider_evidence",
        ],
        "sparse_beginner_first_plan": [
            "schema_valid",
            "declared_constraints_preserved",
            "no_fabricated_provider_evidence",
        ],
    }


@pytest.mark.unit
def test_public_demo_does_not_advertise_removed_provider_or_recap_paths():
    demo_source = Path("web/app/src/app/demo/page.tsx").read_text()

    assert "optional provider" not in demo_source.lower()
    assert "provider data" not in demo_source.lower()
    assert "questions, recaps" not in demo_source.lower()
