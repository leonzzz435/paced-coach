import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from api.models.integration_connection import IntegrationConnection
from api.services.athlete_time import AthleteTimeContext
from api.services.dashboard_state import (
    _build_first_run_state,
    _build_html_preview,
    _extract_html_text,
    build_dashboard_state,
)
from api.services.full_run_policy import WeeklyRecapAvailability

_NO_FAKE_RESULT = object()


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        if isinstance(self._value, list):
            return self._value
        return []

    def first(self):
        if isinstance(self._value, list):
            return self._value[0] if self._value else None
        return self._value


class _FakeAsyncSession:
    def __init__(
        self,
        *,
        profile,
        competitions,
        daily_run,
        completed_daily_runs=None,
        pending_proposal,
        strava=None,
        whoop=None,
        connection_history=None,
        require_active_thread_filter=False,
        recap_run=None,
        recap_proposal_status=None,
    ):
        self.profile = profile
        self.competitions = competitions
        self.daily_run = daily_run
        self.completed_daily_runs = completed_daily_runs if completed_daily_runs is not None else (
            [daily_run] if str(getattr(daily_run, "status", "")).strip().lower() in {"done", "completed"} else []
        )
        self.pending_proposal = pending_proposal
        self.strava = strava
        self.whoop = whoop
        self.connection_history = connection_history or []
        self.require_active_thread_filter = require_active_thread_filter
        self.recap_run = recap_run
        self.recap_proposal_status = recap_proposal_status
        self.commits = 0

    def _primary_result_for_sql(self, sql: str):
        if "FROM athlete_profiles" in sql:
            return _FakeScalarResult(self.profile)
        if "FROM competitions" in sql:
            return _FakeScalarResult(self.competitions)
        if "FROM strava_credentials" in sql:
            return _FakeScalarResult(self.strava)
        if "FROM whoop_credentials" in sql:
            return _FakeScalarResult(self.whoop)
        if "FROM integration_connections" in sql:
            return _FakeScalarResult(self.connection_history)
        if "FROM oauth_sessions" in sql or "FROM local_usage_plan_overrides" in sql:
            return _FakeScalarResult(None)
        return _NO_FAKE_RESULT

    def _run_result_for_sql(self, sql: str):
        if "FROM daily_update_runs" in sql and "daily_update_runs.target_date =" in sql:
            return _FakeScalarResult(self.daily_run)
        if "FROM daily_update_runs" in sql:
            return _FakeScalarResult(self.completed_daily_runs)
        if "FROM weekly_recap_runs" in sql:
            return _FakeScalarResult(self.recap_run)
        return _NO_FAKE_RESULT

    def _coach_result_for_sql(self, sql: str):
        if "SELECT coach_proposals.status" in sql:
            return _FakeScalarResult(self.recap_proposal_status)
        if "FROM coach_proposals" not in sql:
            return _NO_FAKE_RESULT
        if self.require_active_thread_filter:
            assert "JOIN coach_threads" in sql
            assert "coach_threads.status" in sql
        return _FakeScalarResult(self.pending_proposal)

    async def execute(self, statement, *_args, **_kwargs):
        sql = str(statement)
        for resolver in (self._primary_result_for_sql, self._run_result_for_sql, self._coach_result_for_sql):
            result = resolver(sql)
            if result is not _NO_FAKE_RESULT:
                return result
        raise AssertionError(f"Unexpected SQL in test: {sql}")

    async def commit(self):
        self.commits += 1


def _weekly_plan_payload() -> dict:
    return {
        "type": "weekly_plan",
        "plan_id": "plan-1",
        "schema_version": 1,
        "version": 7,
        "athlete_name": "Test Athlete",
        "created_at": "2026-03-01T08:00:00Z",
        "global_blocks": [],
        "global_nodes": [],
        "weeks": [
            {
                "week_id": "wk-2026-03-02",
                "start_date": "2026-03-02",
                "end_date": "2026-03-08",
                "notes_blocks": [],
                "notes_nodes": [],
                "days": [
                    {
                        "day_id": "2026-03-05",
                        "date": "2026-03-05",
                        "day_label": "Thu - Session",
                        "focus_type": "threshold",
                        "readiness_note": "Base readiness note.",
                        "estimated_duration_min": 65,
                        "estimated_intensity": "moderate",
                        "blocks": [],
                        "nodes": [
                            {
                                "node_id": "node-1",
                                "title": "Primary Set",
                                "blocks": [
                                    {
                                        "key": "planned-threshold",
                                        "variant": "workout",
                                        "content_html": "<p>Planned threshold set</p>",
                                    }
                                ],
                                "children": [],
                            }
                        ],
                        "is_completed": False,
                    }
                ],
            }
        ],
    }


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
        "<p><strong>Green light today.</strong> The 3-5 day trend says you have bounced back well from the dip on "
        "Saturday: HRV has risen from 85 to 126 to 141, resting HR is down to 39, and both Strava and WHOOP show "
        "strong recovery this morning.</p>"
    )

    assert preview.endswith("strong recovery this morning.")
    assert "resting HR is down to 39" in preview


def test_first_run_state_routes_missing_llm_key_before_profile_or_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    state = _build_first_run_state(
        profile=None,
        has_competitions=False,
        has_active_plan=False,
        has_connected_source=False,
    )

    assert state["mode"] == "manual"
    assert state["evidence_level"] == "declared_only"
    assert state["next_step"] == "llm_key"
    assert state["primary_action"] is None
    assert "OPENAI_API_KEY" in state["blockers"][0]
    assert "Strava" not in " ".join(state["blockers"])
    assert "WHOOP" not in " ".join(state["blockers"])


def test_first_run_state_routes_profile_and_goal_without_provider_setup(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    missing_profile_state = _build_first_run_state(
        profile={"preferences": {"sports": ["run"]}},
        has_competitions=False,
        has_active_plan=False,
        has_connected_source=False,
    )
    assert missing_profile_state["next_step"] == "profile"
    assert missing_profile_state["primary_action"] == {"label": "Complete profile", "href": "/app/profile"}

    profile_without_goal = {
        "physiology": {"ftp": 250},
        "preferences": {"sports": ["run"]},
        "availability": {"days_per_week": 5, "time_windows": "mornings"},
        "goals": {},
    }
    missing_goal_state = _build_first_run_state(
        profile=profile_without_goal,
        has_competitions=False,
        has_active_plan=False,
        has_connected_source=False,
    )
    assert missing_goal_state["next_step"] == "goal"
    assert missing_goal_state["primary_action"] == {"label": "Add goal or race", "href": "/app/competitions"}

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
    assert ready_state["next_step"] == "generate"
    assert ready_state["primary_action"] == {"label": "Generate plan", "href": "/app/new"}
    assert "No wearable required" in ready_state["body"]
    assert "Draft Mode" not in ready_state["body"]


def test_first_run_state_routes_generated_plan_to_plan_view(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    state = _build_first_run_state(
        profile=None,
        has_competitions=False,
        has_active_plan=True,
        has_connected_source=False,
    )

    assert state["next_step"] == "generated"
    assert state["primary_action"] == {"label": "Open training plan", "href": "/app/plan"}
    assert state["secondary_actions"] == [{"label": "Ask coach", "href": "/app/coach"}]


@pytest.mark.asyncio
async def test_build_dashboard_state_prepends_daily_focus_blocks_and_exposes_banner(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-05T06:00:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return None

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="America/Los_Angeles",
            window_start=None,
            window_end=None,
            next_allowed_at=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
            existing_run_id=None,
        )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )

    daily_run = SimpleNamespace(
        id=uuid.uuid4(),
        target_date=date(2026, 3, 5),
        status="completed",
        error_message=None,
        proposal_id=None,
        updated_at=datetime(2026, 3, 5, 6, 10, tzinfo=UTC),
        context_snapshot={
            "prefetched_recovery_readiness": {
                "sources": {
                    "strava": {"activity_summary": {"activity_count": 1}},
                    "whoop": {"recoveries": [{"score": {"recovery_score": 87}}]},
                }
            }
        },
        update_payload={
            "dashboard_kpis": [
                {
                    "kpi_id": "sleep-duration-score",
                    "label": "Sleep (duration + score)",
                    "value": "8.6-9.3 h; scores 86-97",
                    "status": "good",
                    "trend": "Strong rebound vs 2026-02-22 collapse",
                    "domain": "sleep",
                    "trend_points": [29, 61, 86, 91, 97],
                }
            ],
            "today_focus_blocks": [
                {
                    "key": "focus-verdict",
                    "variant": "callout",
                    "tone": "warning",
                    "content_html": "<p><strong>Protect today.</strong> Keep the set controlled.</p>",
                }
            ]
        },
    )
    pending_proposal = SimpleNamespace(
        id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        origin="daily_update",
        assistant_message="Coach proposed a plan adjustment.",
    )
    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[],
        daily_run=daily_run,
        pending_proposal=pending_proposal,
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["athlete_time"]["timezone"] == "America/Los_Angeles"
    assert state["daily_sync"]["status"] == "idle"
    assert state["daily_sync"]["visible"] is False
    assert state["daily_sync"]["verdict_preview"] is None
    assert state["daily_sync"]["sources_used"] == []
    assert state["daily_sync"]["can_run"] is False
    assert state["daily_sync"]["attention_message"] == "Daily Sync is not included in the provider-free v2.2.0 release."
    assert state["status_surface"]["source"] == "none"
    assert state["status_surface"]["kpis"] == []
    assert state["coach_surface"]["source"] == "none"
    assert state["pending_proposal_banner"]["proposal_id"] == str(pending_proposal.id)
    assert state["pending_proposal_banner"]["thread_id"] == str(pending_proposal.thread_id)
    assert state["weekly_recap"]["status"] == "hidden"
    assert state["weekly_recap"]["can_run"] is False
    assert state["weekly_recap"]["attention_message"] == "Weekly Recap is not included in the provider-free v2.2.0 release."
    assert "Fill key profile fields to improve intensity and constraint handling." in state["today_mission"]["warnings"]
    assert "Add at least one competition to anchor periodization and race specificity." in state["today_mission"]["warnings"]
    assert all("training source" not in warning for warning in state["today_mission"]["warnings"])

    day_override = state["today_mission"]["day_override"]
    assert day_override is not None
    assert day_override["nodes"] == []
    assert day_override["blocks"][0]["key"] == "planned-threshold"
    assert day_override["readiness_note"] == "Base readiness note."


@pytest.mark.asyncio
async def test_build_dashboard_state_surfaces_provider_attention_before_daily_sync(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-05T06:00:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return None

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="America/Los_Angeles",
            window_start=None,
            window_end=None,
            next_allowed_at=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
            existing_run_id=None,
        )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )
    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    strava = SimpleNamespace(
        encrypted_access_token=b"access-token",
        encrypted_refresh_token=b"refresh-token",
        expires_at=datetime(2026, 3, 6, tzinfo=UTC),
        scope="activity:read_all",
        strava_athlete_id=12345,
    )
    whoop = SimpleNamespace(
        encrypted_access_token=b"access-token",
        encrypted_refresh_token=None,
        expires_at=datetime(2026, 3, 4, tzinfo=UTC),
        scope="offline read:recovery",
        whoop_user_id=42,
    )
    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[uuid.uuid4()],
        daily_run=None,
        pending_proposal=None,
        strava=strava,
        whoop=whoop,
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["daily_sync"]["visible"] is False
    assert state["daily_sync"]["can_run"] is False
    assert state["daily_sync"]["attention_message"] == "Daily Sync is not included in the provider-free v2.2.0 release."
    assert state["weekly_recap"]["attention_message"] == "Weekly Recap is not included in the provider-free v2.2.0 release."
    assert all("WHOOP" not in warning for warning in state["today_mission"]["warnings"])
    assert "Fill key profile fields to improve intensity and constraint handling." in state["today_mission"]["warnings"]
    assert state["pending_proposal_banner"] is None


@pytest.mark.asyncio
async def test_build_dashboard_state_converts_stale_pending_daily_sync_to_failed(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-05T06:00:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return None

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="America/Los_Angeles",
            window_start=None,
            window_end=None,
            next_allowed_at=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
            existing_run_id=None,
        )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )
    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    daily_run = SimpleNamespace(
        id=uuid.uuid4(),
        status="pending",
        error_message=None,
        proposal_id=None,
        created_at=datetime(2026, 3, 5, 5, 20, tzinfo=UTC),
        updated_at=datetime(2026, 3, 5, 5, 20, tzinfo=UTC),
        context_snapshot=None,
        update_payload=None,
    )
    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[uuid.uuid4()],
        daily_run=daily_run,
        pending_proposal=None,
        whoop=SimpleNamespace(
            encrypted_access_token=b"access-token",
            encrypted_refresh_token=b"refresh-token",
            expires_at=datetime(2026, 3, 6, tzinfo=UTC),
            scope="offline read:recovery",
            whoop_user_id=42,
        ),
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert fake_db.commits == 1
    assert daily_run.status == "failed"
    assert state["daily_sync"]["status"] == "idle"
    assert state["daily_sync"]["error_message"] is None
    assert state["daily_sync"]["can_run"] is False


@pytest.mark.asyncio
async def test_build_dashboard_state_blocks_weekly_recap_when_provider_was_disconnected(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-05T06:00:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return None

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=True,
            reason="eligible",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=datetime(2026, 3, 9, 8, 0, tzinfo=UTC),
            timezone="America/Los_Angeles",
            window_start=datetime(2026, 3, 9, 8, 0, tzinfo=UTC),
            window_end=datetime(2026, 3, 16, 8, 0, tzinfo=UTC),
            next_allowed_at=None,
            existing_run_id=None,
        )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )
    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    monkeypatch.setattr("api.services.dashboard_state.has_weekly_recap_feature_access", lambda *_args, **_kwargs: True)

    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[uuid.uuid4()],
        daily_run=None,
        pending_proposal=None,
        connection_history=[
            IntegrationConnection(
                user_id=user_id,
                provider="whoop",
                first_connected_at=datetime(2026, 3, 1, tzinfo=UTC),
                last_connected_at=datetime(2026, 3, 4, tzinfo=UTC),
                last_disconnected_at=datetime(2026, 3, 5, tzinfo=UTC),
                last_disconnect_reason="user_initiated",
            )
        ],
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["weekly_recap"]["visible"] is False
    assert state["weekly_recap"]["status"] == "hidden"
    assert state["weekly_recap"]["can_run"] is False
    assert state["weekly_recap"]["attention_message"] == "Weekly Recap is not included in the provider-free v2.2.0 release."
    assert all("WHOOP" not in warning for warning in state["today_mission"]["warnings"])


@pytest.mark.asyncio
async def test_build_dashboard_state_skips_archived_thread_pending_proposal_banner(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-05T06:00:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return None

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="America/Los_Angeles",
            window_start=None,
            window_end=None,
            next_allowed_at=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
            existing_run_id=None,
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(has_access=False, effective_plan=None)

    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    monkeypatch.setattr("api.services.dashboard_state.has_weekly_recap_feature_access", lambda *_args, **_kwargs: False)

    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[],
        daily_run=None,
        pending_proposal=None,
        require_active_thread_filter=True,
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["status_surface"]["source"] == "none"
    assert state["status_surface"]["label"] is None
    assert state["status_surface"]["target_date"] is None
    assert state["status_surface"]["kpis"] == []
    assert state["coach_surface"]["source"] == "none"
    assert state["pending_proposal_banner"] is None


@pytest.mark.asyncio
async def test_build_dashboard_state_uses_analysis_dashboard_kpis_when_no_daily_overlay(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-05T06:00:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return {
            "version": 7,
            "analysis": {
                "type": "analysis",
                "analysis_id": "analysis-1",
                "schema_version": 1,
                "version": 7,
                "athlete_name": "Test Athlete",
                "created_at": "2026-03-01T08:00:00Z",
                "headline_brief": "Protect recovery today.",
                "dashboard_kpis": [
                    {
                        "kpi_id": "sleep-duration-score",
                        "label": "Sleep (duration + score)",
                        "value": "8.6-9.3 h; scores 86-97",
                        "status": "good",
                        "trend": "Strong rebound vs 2026-02-22 collapse",
                        "domain": "sleep",
                        "trend_points": [29, 61, 86, 91, 97],
                    }
                ],
                "kpis": [],
                "sections": [],
            },
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-05T05:45:00+00:00",
        }

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="America/Los_Angeles",
            window_start=None,
            window_end=None,
            next_allowed_at=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
            existing_run_id=None,
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(has_access=False, effective_plan=None)

    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    monkeypatch.setattr("api.services.dashboard_state.has_weekly_recap_feature_access", lambda *_args, **_kwargs: False)

    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[],
        daily_run=None,
        pending_proposal=None,
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["status_surface"]["source"] == "analysis"
    assert state["status_surface"]["label"] == "Baseline analysis"
    assert state["status_surface"]["updated_at"] == "2026-03-05T05:45:00+00:00"
    assert state["status_surface"]["target_date"] is None
    assert state["status_surface"]["kpis"][0]["kpi_id"] == "sleep-duration-score"
    assert state["coach_surface"]["source"] == "analysis"
    assert state["coach_surface"]["scope"] == "training_block"
    assert state["coach_surface"]["primary_label"] == "Block Focus"
    assert state["coach_surface"]["primary_text"] == "Protect recovery today."


@pytest.mark.asyncio
async def test_build_dashboard_state_reuses_latest_completed_daily_kpis_before_new_sync(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 6, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-06T06:00:00+00:00",
        today_local_date=date(2026, 3, 6),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return {
            "version": 7,
            "analysis": {
                "type": "analysis",
                "analysis_id": "analysis-1",
                "schema_version": 1,
                "version": 7,
                "athlete_name": "Test Athlete",
                "created_at": "2026-03-01T08:00:00Z",
                "headline_brief": "Baseline guidance for the block.",
                "coach_action": "Keep the build steady.",
                "dashboard_kpis": [
                    {
                        "kpi_id": "baseline-sleep",
                        "label": "Sleep baseline",
                        "value": "8.2 h",
                        "status": "good",
                        "trend": "Baseline still solid",
                        "domain": "sleep",
                        "trend_points": [78, 81, 82, 84],
                    }
                ],
                "kpis": [],
                "sections": [],
            },
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-06T05:45:00+00:00",
        }

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="America/Los_Angeles",
            window_start=None,
            window_end=None,
            next_allowed_at=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
            existing_run_id=None,
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(has_access=False, effective_plan=None)

    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    monkeypatch.setattr("api.services.dashboard_state.has_weekly_recap_feature_access", lambda *_args, **_kwargs: False)

    previous_daily_run = SimpleNamespace(
        id=uuid.uuid4(),
        target_date=date(2026, 3, 5),
        status="completed",
        error_message=None,
        proposal_id=None,
        updated_at=datetime(2026, 3, 5, 16, 10, tzinfo=UTC),
        context_snapshot={
            "prefetched_recovery_readiness": {
                "sources": {
                    "strava": {"activity_summary": {"activity_count": 1}},
                }
            }
        },
        update_payload={
            "dashboard_kpis": [
                {
                    "kpi_id": "daily-sleep",
                    "label": "Sleep last night",
                    "value": "8.75 h",
                    "status": "good",
                    "trend": "Carried forward from the most recent daily sync",
                    "domain": "sleep",
                    "trend_points": [7.4, 7.8, 8.1, 8.75],
                }
            ],
            "today_focus_blocks": [
                {
                    "key": "focus-verdict",
                    "variant": "callout",
                    "tone": "good",
                    "content_html": "<p><strong>Green light today.</strong> Yesterday's summary.</p>",
                }
            ],
        },
    )

    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[],
        daily_run=None,
        completed_daily_runs=[previous_daily_run],
        pending_proposal=None,
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["status_surface"]["source"] == "analysis"
    assert state["status_surface"]["kpis"][0]["kpi_id"] == "baseline-sleep"
    assert state["coach_surface"]["source"] == "analysis"
    assert state["daily_sync"]["status"] == "idle"


@pytest.mark.asyncio
async def test_build_dashboard_state_labels_older_carried_forward_daily_kpis_with_date(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 8, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-08T06:00:00+00:00",
        today_local_date=date(2026, 3, 8),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return None

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="window_not_open",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=None,
            timezone="America/Los_Angeles",
            window_start=None,
            window_end=None,
            next_allowed_at=datetime(2026, 3, 15, 8, 0, tzinfo=UTC),
            existing_run_id=None,
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(has_access=False, effective_plan=None)

    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    monkeypatch.setattr("api.services.dashboard_state.has_weekly_recap_feature_access", lambda *_args, **_kwargs: False)

    older_daily_run = SimpleNamespace(
        id=uuid.uuid4(),
        target_date=date(2026, 3, 5),
        status="completed",
        error_message=None,
        proposal_id=None,
        updated_at=datetime(2026, 3, 5, 16, 10, tzinfo=UTC),
        context_snapshot={},
        update_payload={
            "dashboard_kpis": [
                {
                    "kpi_id": "daily-sleep",
                    "label": "Sleep last night",
                    "value": "8.75 h",
                    "status": "good",
                    "trend": "Carried forward from the most recent daily sync",
                    "domain": "sleep",
                    "trend_points": [7.4, 7.8, 8.1, 8.75],
                }
            ],
            "today_focus_blocks": [],
        },
    )

    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[],
        daily_run=None,
        completed_daily_runs=[older_daily_run],
        pending_proposal=None,
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["status_surface"]["source"] == "none"
    assert state["status_surface"]["kpis"] == []


@pytest.mark.asyncio
async def test_build_dashboard_state_prefers_newer_weekly_recap_over_earlier_daily_sync(monkeypatch):
    user_id = uuid.uuid4()
    recap_run_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 16, 19, 0, tzinfo=UTC),
        now_local_iso="2026-03-16T19:00:00+00:00",
        today_local_date=date(2026, 3, 16),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return {
            "version": 7,
            "analysis": {
                "type": "analysis",
                "analysis_id": "analysis-1",
                "schema_version": 1,
                "version": 7,
                "athlete_name": "Test Athlete",
                "created_at": "2026-03-01T08:00:00Z",
                "headline_brief": "Baseline block guidance.",
                "coach_action": "Keep the overall build controlled.",
                "dashboard_kpis": [],
                "kpis": [],
                "sections": [],
            },
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-15T08:00:00+00:00",
        }

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="already_ran_in_window",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=datetime(2026, 3, 14, 23, 0, tzinfo=UTC),
            timezone="America/Los_Angeles",
            window_start=datetime(2026, 3, 9, 23, 0, tzinfo=UTC),
            window_end=datetime(2026, 3, 16, 22, 59, tzinfo=UTC),
            next_allowed_at=datetime(2026, 3, 21, 23, 0, tzinfo=UTC),
            existing_run_id=recap_run_id,
        )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )
    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    monkeypatch.setattr("api.services.dashboard_state.has_weekly_recap_feature_access", lambda *_args, **_kwargs: True)

    daily_run = SimpleNamespace(
        id=uuid.uuid4(),
        status="completed",
        error_message=None,
        proposal_id=None,
        updated_at=datetime(2026, 3, 16, 8, 30, tzinfo=UTC),
        context_snapshot={},
        update_payload={
            "dashboard_kpis": [],
            "today_focus_blocks": [
                {
                    "key": "focus-verdict",
                    "variant": "callout",
                    "tone": "warning",
                    "content_html": "<p><strong>Keep it easy today.</strong> Stay disciplined and protect recovery.</p>",
                }
            ],
        },
    )
    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[],
        daily_run=daily_run,
        pending_proposal=None,
        recap_run=SimpleNamespace(
            id=recap_run_id,
            user_id=user_id,
            proposal_id=None,
            recap_event_id=None,
            updated_at=datetime(2026, 3, 16, 18, 45, tzinfo=UTC),
            follow_up_question=None,
            athlete_response=None,
            recap_payload={
                "narrative": {
                    "this_week_blocks": [
                        {
                            "key": "compliance",
                            "title": "High compliance, but load rose faster than ideal",
                            "content_html": "<p>The week landed well, but the load climbed quickly.</p>",
                        }
                    ],
                    "looking_ahead_blocks": [
                        {
                            "key": "next-step",
                            "title": "Absorb the work before pushing again",
                            "content_html": "<p>Keep Tuesday controlled and do not chase extra volume.</p>",
                        }
                    ],
                }
            },
        ),
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["daily_sync"]["status"] == "idle"
    assert state["weekly_recap"]["status"] == "hidden"
    assert state["coach_surface"]["source"] == "analysis"
    assert state["coach_surface"]["primary_text"] == "Keep the overall build controlled."


@pytest.mark.asyncio
async def test_build_dashboard_state_hides_weekly_recap_cta_without_entitlement(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 9, 6, 0, tzinfo=UTC),
        now_local_iso="2026-03-09T06:00:00+00:00",
        today_local_date=date(2026, 3, 9),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return None

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=True,
            reason="eligible",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
            timezone="America/Los_Angeles",
            window_start=datetime(2026, 3, 2, 8, 0, tzinfo=UTC),
            window_end=datetime(2026, 3, 9, 7, 59, tzinfo=UTC),
            next_allowed_at=None,
            existing_run_id=None,
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(has_access=False, effective_plan=None)

    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    monkeypatch.setattr("api.services.dashboard_state.has_weekly_recap_feature_access", lambda *_args, **_kwargs: False)

    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[],
        daily_run=None,
        pending_proposal=None,
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["weekly_recap"]["visible"] is False
    assert state["weekly_recap"]["allowed"] is False
    assert state["weekly_recap"]["status"] == "hidden"


@pytest.mark.asyncio
async def test_build_dashboard_state_keeps_recap_outcome_visible_after_follow_up_answered(monkeypatch):
    user_id = uuid.uuid4()
    recap_run_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 16, 7, 0, tzinfo=UTC),
        now_local_iso="2026-03-16T07:00:00+00:00",
        today_local_date=date(2026, 3, 16),
    )

    async def fake_get_active_analysis(*_args, **_kwargs):
        return None

    async def fake_get_active_season_plan(*_args, **_kwargs):
        return None

    async def fake_get_active_weekly_plan(*_args, **_kwargs):
        return {
            "version": 7,
            "weekly_plan": _weekly_plan_payload(),
            "source_job_id": str(uuid.uuid4()),
            "updated_at": "2026-03-01T08:00:00+00:00",
        }

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    async def fake_evaluate_weekly_recap_availability(*_args, **_kwargs):
        return WeeklyRecapAvailability(
            allowed=False,
            reason="already_ran_in_window",
            last_full_run_at=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            current_anchor_utc=datetime(2026, 3, 14, 23, 0, tzinfo=UTC),
            timezone="America/Los_Angeles",
            window_start=datetime(2026, 3, 9, 23, 0, tzinfo=UTC),
            window_end=datetime(2026, 3, 16, 22, 59, tzinfo=UTC),
            next_allowed_at=datetime(2026, 3, 21, 23, 0, tzinfo=UTC),
            existing_run_id=recap_run_id,
        )

    async def fake_get_local_usage_context(*_args, **_kwargs):
        return SimpleNamespace(
            has_access=True,
            effective_plan=SimpleNamespace(weekly_recap_included=True),
        )

    monkeypatch.setattr("api.services.dashboard_state.get_active_analysis", fake_get_active_analysis)
    monkeypatch.setattr("api.services.dashboard_state.get_active_season_plan", fake_get_active_season_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_active_weekly_plan", fake_get_active_weekly_plan)
    monkeypatch.setattr("api.services.dashboard_state.get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        "api.services.dashboard_state.evaluate_weekly_recap_availability",
        fake_evaluate_weekly_recap_availability,
    )
    monkeypatch.setattr("api.services.dashboard_state.get_local_usage_context", fake_get_local_usage_context)
    monkeypatch.setattr("api.services.dashboard_state.has_weekly_recap_feature_access", lambda *_args, **_kwargs: True)

    fake_db = _FakeAsyncSession(
        profile={"preferences": {"timezone": "America/Los_Angeles"}},
        competitions=[],
        daily_run=None,
        pending_proposal=None,
        recap_run=SimpleNamespace(
            id=recap_run_id,
            user_id=user_id,
            proposal_id=None,
            recap_event_id=None,
            updated_at=datetime(2026, 3, 16, 7, 15, tzinfo=UTC),
            follow_up_question="Did the climbs feel smooth?",
            athlete_response="Yes, they felt good.",
            recap_payload={
                "narrative": {
                    "this_week_blocks": [
                        {
                            "key": "compliance",
                            "title": "High compliance, but load rose fast",
                            "content_html": "<p><strong>This week:</strong> strong compliance, but load rose fast.</p>",
                        }
                    ],
                    "looking_ahead_blocks": [
                        {
                            "key": "next-step",
                            "title": "Next week: stay disciplined on the long run",
                            "content_html": "<p>Keep the long run controlled and start fueling earlier.</p>",
                        }
                    ],
                }
            },
        ),
    )

    state = await build_dashboard_state(cast("Any", fake_db), user_id=user_id)

    assert state["weekly_recap"]["visible"] is False
    assert state["weekly_recap"]["status"] == "hidden"
    assert state["weekly_recap"]["pending_action"] == "none"
    assert state["weekly_recap"]["follow_up_question"] is None
    assert state["weekly_recap"]["summary_preview"] is None
    assert state["coach_surface"]["source"] == "none"
