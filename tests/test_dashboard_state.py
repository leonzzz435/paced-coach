import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from api.services.athlete_time import AthleteTimeContext
from api.services.dashboard_state import (
    _build_first_run_state,
    _build_html_preview,
    _extract_html_text,
    build_dashboard_state,
)


class _FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def first(self):
        if isinstance(self.value, list):
            return self.value[0] if self.value else None
        return self.value


class _DashboardDb:
    def __init__(self, *, profile: dict | None, competitions: list[object], pending_proposal=None):
        self.profile = profile
        self.competitions = competitions
        self.pending_proposal = pending_proposal

    async def execute(self, statement, *_args, **_kwargs):
        sql = str(statement)
        if "FROM athlete_profiles" in sql:
            return _FakeResult(self.profile)
        if "FROM competitions" in sql:
            return _FakeResult(self.competitions)
        if "FROM coach_proposals" in sql:
            assert "JOIN coach_threads" in sql
            assert "coach_threads.status" in sql
            return _FakeResult(self.pending_proposal)
        raise AssertionError(f"Unexpected SQL in dashboard test: {sql}")


def test_build_html_preview_prefers_clause_boundary_for_truncation():
    preview = _build_html_preview(
        (
            "<p>Green light today. The 3-5 day trend says you have bounced back well from the dip on Saturday: "
            "HRV has risen from 85 to 126 to 141, resting HR is down to 39, and readiness looks much better.</p>"
        ),
        max_chars=120,
    )

    assert preview == "Green light today. The 3-5 day trend says you have bounced back well from the dip on Saturday..."


def test_extract_html_text_returns_full_plain_text_without_truncation():
    preview = _extract_html_text(
        "<p><strong>Green light today.</strong> The athlete reports strong recovery this morning.</p>"
    )

    assert preview.endswith("strong recovery this morning.")


def test_first_run_state_routes_missing_llm_key_before_profile(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    state = _build_first_run_state(
        profile=None,
        has_competitions=False,
        has_active_plan=False,
        has_connected_source=False,
    )

    assert state["mode"] == "manual"
    assert state["evidence_level"] == "declared_only"
    assert state["next_step"] == "llm_key"
    assert "OPENAI_API_KEY" in state["blockers"][0]
    assert "Strava" not in " ".join(state["blockers"])
    assert "WHOOP" not in " ".join(state["blockers"])


def test_first_run_state_routes_profile_goal_and_generated_plan(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    complete_profile = {
        "physiology": {"ftp": 250},
        "preferences": {"sports": ["run"]},
        "availability": {"days_per_week": 5, "time_windows": "mornings"},
        "goals": {"primary_goal": "Run a strong fall half marathon"},
    }

    ready_state = _build_first_run_state(
        profile=complete_profile,
        has_competitions=False,
        has_active_plan=False,
        has_connected_source=False,
    )
    generated_state = _build_first_run_state(
        profile=complete_profile,
        has_competitions=False,
        has_active_plan=True,
        has_connected_source=False,
    )

    assert ready_state["next_step"] == "generate"
    assert "No wearable required" in ready_state["body"]
    assert generated_state["primary_action"] == {"label": "Open training plan", "href": "/app/plan"}


@pytest.mark.asyncio
async def test_dashboard_is_provider_free_and_hides_retired_automation(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="Europe/Berlin",
        timezone_source="profile",
        now_local=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        now_local_iso="2026-08-01T12:00:00+02:00",
        today_local_date=date(2026, 8, 1),
    )
    weekly_payload = {
        "version": 1,
        "weekly_plan": {"schema_version": 3, "plan_id": "execution-1"},
        "source_job_id": str(uuid.uuid4()),
        "updated_at": "2026-08-01T08:00:00+00:00",
    }

    async def active_analysis(*_args, **_kwargs):
        return None

    async def active_season(*_args, **_kwargs):
        return None

    async def active_weekly(*_args, **_kwargs):
        return weekly_payload

    async def athlete_context(*_args, **_kwargs):
        return athlete_time

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", active_season)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", active_weekly)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", athlete_context)

    state = await build_dashboard_state(
        cast("Any", _DashboardDb(profile={"goals": {"primary_goal": "Finish healthy"}}, competitions=[])),
        user_id=user_id,
    )

    assert state["weekly"] == weekly_payload
    assert state["first_run"]["has_connected_source"] is False
    assert state["daily_sync"]["visible"] is False
    assert state["daily_sync"]["can_run"] is False
    assert state["weekly_recap"]["visible"] is False
    assert state["weekly_recap"]["can_run"] is False
    assert state["today_mission"]["day_override"] is None


@pytest.mark.asyncio
async def test_dashboard_exposes_only_active_thread_pending_proposal(monkeypatch):
    user_id = uuid.uuid4()
    proposal = SimpleNamespace(
        id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        origin="coach_chat",
        assistant_message="Want me to move Tuesday's session?",
    )

    async def no_plan(*_args, **_kwargs):
        return None

    async def athlete_context(*_args, **_kwargs):
        return AthleteTimeContext(
            timezone="UTC",
            timezone_source="fallback_utc",
            now_local=datetime(2026, 8, 1, tzinfo=UTC),
            now_local_iso="2026-08-01T00:00:00+00:00",
            today_local_date=date(2026, 8, 1),
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", no_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", no_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", no_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", athlete_context)

    state = await build_dashboard_state(
        cast("Any", _DashboardDb(profile=None, competitions=[], pending_proposal=proposal)),
        user_id=user_id,
    )

    assert state["pending_proposal_banner"]["proposal_id"] == str(proposal.id)
    assert state["pending_proposal_banner"]["thread_id"] == str(proposal.thread_id)
