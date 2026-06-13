import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import api.deps as deps_module
from api.main import create_app
from api.models.ai_run_cost import AiRunCost
from api.models.credentials import WhoopCredentials
from api.models.daily_update_run import DailyUpdateRun
from api.models.integration_connection import IntegrationConnection
from api.routers import daily as daily_router
from api.services.ai_run_costs import AiRunCostSnapshot
from api.services.athlete_time import AthleteTimeContext
from services.ai.daily.schemas import DailyUpdateNarrative
from services.ai.langgraph.schemas.ui_blocks import UiHtmlBlock, UiKpi


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


class _FakeAsyncSession:
    def __init__(self, *, active_weekly, whoop=None, connection_history=None):
        self.active_weekly = active_weekly
        self.whoop = whoop
        self.connection_history = connection_history or []
        self.daily_run: DailyUpdateRun | None = None
        self._added: list[DailyUpdateRun] = []
        self.ai_run_costs: list[AiRunCost] = []

    async def execute(self, statement, *_args, **_kwargs):
        sql = str(statement)
        if "FROM daily_update_runs" in sql:
            return _FakeScalarResult(self.daily_run)
        if "FROM active_weekly_plans" in sql:
            return _FakeScalarResult(self.active_weekly)
        if "FROM strava_credentials" in sql:
            return _FakeScalarResult(None)
        if "FROM whoop_credentials" in sql:
            return _FakeScalarResult(self.whoop)
        if "FROM integration_connections" in sql:
            return _FakeScalarResult(self.connection_history)
        return _FakeScalarResult(None)

    def add(self, obj):
        if isinstance(obj, DailyUpdateRun):
            self._added.append(obj)
            self.daily_run = obj
        if isinstance(obj, AiRunCost):
            self.ai_run_costs.append(obj)

    async def flush(self):
        for obj in self._added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def commit(self):
        await self.flush()

    async def rollback(self):
        return None

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()


def _weekly_plan_payload() -> dict:
    return {
        "type": "weekly_plan",
        "plan_id": "plan-1",
        "schema_version": 1,
        "version": 4,
        "athlete_name": "Test Athlete",
        "created_at": "2026-03-01T08:00:00Z",
        "global_blocks": [],
        "global_nodes": [],
        "weeks": [
            {
                "week_id": "wk-2026-03-02",
                "week_label": "Race Specific",
                "start_date": "2026-03-02",
                "end_date": "2026-03-08",
                "notes_blocks": [],
                "notes_nodes": [],
                "days": [
                    {
                        "day_id": "2026-03-05",
                        "date": "2026-03-05",
                        "day_label": "Thu - Threshold",
                        "focus_type": "threshold",
                        "blocks": [],
                        "nodes": [
                            {
                                "node_id": "threshold-node",
                                "title": "Main Set",
                                "blocks": [
                                    {
                                        "key": "planned-main-set",
                                        "variant": "workout",
                                        "content_html": "<p>4 x 8 min threshold.</p>",
                                    }
                                ],
                                "children": [],
                            }
                        ],
                        "estimated_duration_min": 70,
                        "estimated_intensity": "moderate",
                        "readiness_note": "Execute as planned if recovery is normal.",
                        "is_completed": False,
                    }
                ],
            }
        ],
    }


@pytest.mark.integration
def test_daily_run_route_returns_contract_with_today_override(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 30, tzinfo=UTC),
        now_local_iso="2026-03-05T06:30:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    active_weekly = SimpleNamespace(
        plan_data=_weekly_plan_payload(),
        version=4,
        source_job_id=uuid.uuid4(),
    )
    fake_session = _FakeAsyncSession(
        active_weekly=active_weekly,
        whoop=WhoopCredentials(
            user_id=user_id,
            encrypted_access_token=b"access-token",
            encrypted_refresh_token=b"refresh-token",
            expires_at=datetime(2026, 3, 6, tzinfo=UTC),
            scope="offline read:recovery",
            whoop_user_id=42,
        ),
    )
    captured_generate_kwargs: dict = {}

    async def fake_get_db():
        yield fake_session

    async def fake_get_current_user():
        return user_id

    async def fake_generate_daily_update_narrative(**kwargs):
        captured_generate_kwargs.update(kwargs)
        return DailyUpdateNarrative(
            dashboard_kpis=[
                UiKpi(
                    kpi_id="sleep-duration-score",
                    label="Sleep (duration + score)",
                    value="8.6-9.3 h; scores 86-97",
                    status="good",
                    trend="Strong rebound vs 2026-02-22 collapse",
                    domain="sleep",
                    trend_points=[29, 61, 86, 91, 97],
                )
            ],
            today_focus_blocks=[
                UiHtmlBlock(
                    key="readiness-verdict",
                    variant="callout",
                    tone="warning",
                    content_html="<p><strong>Protect today.</strong> Shorten the final interval if legs stay heavy.</p>",
                )
            ],
            optional_proposal_ops=[],
        )

    class _FakeToolRegistry:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get_recovery_readiness_signals(self, *, days: int):
            assert days == 7
            return {
                "window_days": 7,
                "as_of_utc": "2026-03-05T06:30:00+00:00",
                "sources": {
                    "strava": {
                        "activity_summary": {"activity_count": 3},
                    },
                    "whoop": {
                        "recoveries": [{"score": {"recovery_score": 87}}],
                        "sleeps": [{"score": {"sleep_performance_percentage": 94}}],
                    },
                },
                "provider_status": {
                    "strava": {"available": True},
                    "whoop": {"available": True},
                },
            }

        def get_observability_snapshot(self):
            return {"tools_called": ["get_recovery_readiness_signals"]}

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    monkeypatch.setattr(daily_router, "generate_daily_update_narrative", fake_generate_daily_update_narrative)
    monkeypatch.setattr(daily_router, "build_ongoing_tool_registry", lambda *_args, **_kwargs: _FakeToolRegistry())
    monkeypatch.setattr(daily_router, "get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        daily_router,
        "capture_langsmith_run_costs",
        lambda *_args, **_kwargs: AiRunCostSnapshot(cost_status="captured", total_cost_usd=0.015, total_tokens=321),
    )
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")
    monkeypatch.setattr(
        daily_router,
        "get_settings",
        lambda: SimpleNamespace(
            local_usage_dev_bypass=True,
            web_app_url="http://localhost:3000",
            strava_oauth_client_id="client-id",
            strava_oauth_client_secret="client-secret",
            whoop_oauth_client_id="client-id",
            whoop_oauth_client_secret="client-secret",
        ),
    )

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post(
        "/api/daily/run",
        headers={"Authorization": "Bearer test"},
        json={"athlete_check_in": "Slept well, no pain, motivated, heavy desk day."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["run_id"]
    assert payload["sources_used"] == ["strava", "whoop"]
    assert payload["proposal_id"] is None
    assert payload["thread_id"] is None
    assert payload["preview_weekly_plan"] is None
    assert payload["narrative"]["dashboard_kpis"][0]["kpi_id"] == "sleep-duration-score"
    assert payload["narrative"]["today_focus_blocks"][0]["key"] == "readiness-verdict"
    assert payload["today_override"]["day_label"] == "Thu - Threshold"
    assert payload["today_override"]["nodes"] == []
    assert payload["today_override"]["blocks"][0]["key"] == "readiness-verdict"
    assert payload["today_override"]["blocks"][1]["key"] == "planned-main-set"
    assert fake_session.daily_run is not None
    assert fake_session.daily_run.status == "completed"
    assert len(fake_session.ai_run_costs) == 1
    assert fake_session.ai_run_costs[0].feature == "daily_update"
    assert fake_session.ai_run_costs[0].source_type == "daily_update_run"
    assert fake_session.ai_run_costs[0].total_cost_usd is not None
    assert float(fake_session.ai_run_costs[0].total_cost_usd) == 0.015
    context_snapshot = fake_session.daily_run.context_snapshot
    assert isinstance(context_snapshot, dict)
    assert context_snapshot["athlete_check_in"] == "Slept well, no pain, motivated, heavy desk day."
    assert context_snapshot["tool_observability"]["tools_called"] == ["get_recovery_readiness_signals"]
    assert (
        context_snapshot["prefetched_recovery_readiness"]["sources"]["whoop"]["recoveries"][0]["score"][
            "recovery_score"
        ]
        == 87
    )
    assert (
        captured_generate_kwargs["prefetched_recovery_readiness"]["sources"]["strava"]["activity_summary"][
            "activity_count"
        ]
        == 3
    )
    assert (
        captured_generate_kwargs["prefetched_recovery_readiness"]["sources"]["whoop"]["sleeps"][0]["score"][
            "sleep_performance_percentage"
        ]
        == 94
    )
    assert captured_generate_kwargs["prefetched_weekly_plan"]["weeks"][0]["days"][0]["day_id"] == "2026-03-05"
    assert captured_generate_kwargs["athlete_check_in"] == "Slept well, no pain, motivated, heavy desk day."


@pytest.mark.integration
def test_daily_run_route_reuses_stale_pending_run(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 30, tzinfo=UTC),
        now_local_iso="2026-03-05T06:30:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    active_weekly = SimpleNamespace(
        plan_data=_weekly_plan_payload(),
        version=4,
        source_job_id=uuid.uuid4(),
    )
    stale_run_id = uuid.uuid4()
    fake_session = _FakeAsyncSession(
        active_weekly=active_weekly,
        whoop=WhoopCredentials(
            user_id=user_id,
            encrypted_access_token=b"access-token",
            encrypted_refresh_token=b"refresh-token",
            expires_at=datetime(2026, 3, 6, tzinfo=UTC),
            scope="offline read:recovery",
            whoop_user_id=42,
        ),
    )
    fake_session.daily_run = DailyUpdateRun(
        id=stale_run_id,
        user_id=user_id,
        target_date=date(2026, 3, 5),
        trigger_source="manual",
        status="pending",
        error_message=None,
        created_at=datetime(2026, 3, 5, 5, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 5, 5, 0, tzinfo=UTC),
    )

    async def fake_get_db():
        yield fake_session

    async def fake_get_current_user():
        return user_id

    async def fake_generate_daily_update_narrative(**_kwargs):
        return DailyUpdateNarrative(
            dashboard_kpis=[
                UiKpi(
                    kpi_id="recovery-score",
                    label="Recovery score",
                    value="87%",
                    status="good",
                    trend="Recovered enough to keep the day controlled, not inflated.",
                    domain="recovery",
                    trend_points=[61, 73, 87],
                )
            ],
            today_focus_blocks=[
                UiHtmlBlock(
                    key="readiness-verdict",
                    variant="callout",
                    tone="warning",
                    content_html="<p><strong>Protect today.</strong> Keep the set controlled.</p>",
                )
            ],
            optional_proposal_ops=[],
        )

    class _FakeToolRegistry:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get_recovery_readiness_signals(self, *, days: int):
            assert days == 7
            return {
                "sources": {
                    "whoop": {
                        "recoveries": [{"score": {"recovery_score": 87}}],
                    }
                }
            }

        def get_observability_snapshot(self):
            return {"tools_called": ["get_recovery_readiness_signals"]}

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    monkeypatch.setattr(daily_router, "generate_daily_update_narrative", fake_generate_daily_update_narrative)
    monkeypatch.setattr(daily_router, "build_ongoing_tool_registry", lambda *_args, **_kwargs: _FakeToolRegistry())
    monkeypatch.setattr(daily_router, "get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        daily_router,
        "capture_langsmith_run_costs",
        lambda *_args, **_kwargs: AiRunCostSnapshot(cost_status="captured", total_cost_usd=0.0, total_tokens=12),
    )
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")
    monkeypatch.setattr(
        daily_router,
        "get_settings",
        lambda: SimpleNamespace(
            local_usage_dev_bypass=True,
            web_app_url="http://localhost:3000",
            strava_oauth_client_id="client-id",
            strava_oauth_client_secret="client-secret",
            whoop_oauth_client_id="client-id",
            whoop_oauth_client_secret="client-secret",
        ),
    )

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post("/api/daily/run", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json()["run_id"] == str(stale_run_id)
    assert response.json()["narrative"]["dashboard_kpis"][0]["kpi_id"] == "recovery-score"
    assert fake_session.daily_run is not None
    assert fake_session.daily_run.id == stale_run_id
    assert fake_session.daily_run.status == "completed"
    assert fake_session.daily_run.error_message is None


@pytest.mark.integration
def test_daily_run_route_blocks_when_linked_provider_needs_reconnect(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 30, tzinfo=UTC),
        now_local_iso="2026-03-05T06:30:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    active_weekly = SimpleNamespace(
        plan_data=_weekly_plan_payload(),
        version=4,
        source_job_id=uuid.uuid4(),
    )
    fake_session = _FakeAsyncSession(
        active_weekly=active_weekly,
        whoop=WhoopCredentials(
            user_id=user_id,
            encrypted_access_token=b"access-token",
            encrypted_refresh_token=None,
            expires_at=datetime(2026, 3, 4, tzinfo=UTC),
            scope="offline read:recovery",
            whoop_user_id=42,
        ),
    )

    async def fake_get_db():
        yield fake_session

    async def fake_get_current_user():
        return user_id

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    monkeypatch.setattr(daily_router, "get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        daily_router,
        "get_settings",
        lambda: SimpleNamespace(
            local_usage_dev_bypass=True,
            web_app_url="http://localhost:3000",
            strava_oauth_client_id="client-id",
            strava_oauth_client_secret="client-secret",
            whoop_oauth_client_id="client-id",
            whoop_oauth_client_secret="client-secret",
        ),
    )

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post("/api/daily/run", headers={"Authorization": "Bearer test"})

    assert response.status_code == 400
    assert "Reconnect WHOOP" in response.text


@pytest.mark.integration
def test_daily_run_route_blocks_with_reconnect_copy_for_previously_disconnected_provider(monkeypatch):
    user_id = uuid.uuid4()
    athlete_time = AthleteTimeContext(
        timezone="America/Los_Angeles",
        timezone_source="profile",
        now_local=datetime(2026, 3, 5, 6, 30, tzinfo=UTC),
        now_local_iso="2026-03-05T06:30:00+00:00",
        today_local_date=date(2026, 3, 5),
    )

    active_weekly = SimpleNamespace(
        plan_data=_weekly_plan_payload(),
        version=4,
        source_job_id=uuid.uuid4(),
    )
    fake_session = _FakeAsyncSession(
        active_weekly=active_weekly,
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

    async def fake_get_db():
        yield fake_session

    async def fake_get_current_user():
        return user_id

    async def fake_get_athlete_time_context(*_args, **_kwargs):
        return athlete_time

    monkeypatch.setattr(daily_router, "get_athlete_time_context", fake_get_athlete_time_context)
    monkeypatch.setattr(
        daily_router,
        "get_settings",
        lambda: SimpleNamespace(
            local_usage_dev_bypass=True,
            web_app_url="http://localhost:3000",
            strava_oauth_client_id="client-id",
            strava_oauth_client_secret="client-secret",
            whoop_oauth_client_id="client-id",
            whoop_oauth_client_secret="client-secret",
        ),
    )

    app = create_app()
    app.dependency_overrides[deps_module.get_db] = fake_get_db
    app.dependency_overrides[deps_module.get_current_user] = fake_get_current_user

    client = TestClient(app)
    response = client.post("/api/daily/run", headers={"Authorization": "Bearer test"})

    assert response.status_code == 400
    assert response.json()["detail"] == "WHOOP was disconnected. Reconnect it in Settings before starting a run."
