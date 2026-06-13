import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, cast

import anthropic
import httpx
import openai
from billiard.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models.active_analysis import ActiveAnalysis
from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.coach_thread import CoachThread
from api.models.coach_turn_request import CoachTurnRequest
from api.models.credentials import StravaCredentials, WhoopCredentials
from api.models.job import AnalysisJob, JobStatus
from api.models.local_usage import LocalUsageEvent
from api.services.ai_run_costs import (
    build_ai_run_cost_record,
    capture_langsmith_run_costs,
    snapshot_from_legacy_cost_summary,
    trace_metadata_from_execution_metadata,
)
from api.services.coach_memory import maybe_update_thread_memory
from api.services.crypto import get_crypto_service
from api.services.evidence_profile import build_evidence_profile
from api.services.local_usage.usage import FEATURE_FULL_RUN, FEATURE_INITIAL_DRAFT_PLAN, INITIAL_DRAFT_PLAN_SOURCE_TYPE
from api.services.status_messages import (
    complete_active_analysis_progress_steps,
    initial_analysis_progress_steps,
    mark_analysis_progress_step_completed,
    mark_analysis_progress_step_started,
    normalize_analysis_progress_steps,
    record_analysis_step_timing,
)
from core.task_timeouts import get_analysis_task_soft_time_limit_seconds
from services.ai.langgraph.nodes.training_data_projection import build_training_transition_context
from services.ai.langgraph.schemas.ui_blocks import UiSeasonPlan, UiWeeklyPlan
from services.ai.langgraph.workflows.planning_workflow import run_complete_analysis_and_planning
from services.strava import StravaApiClient
from services.strava.oauth import compute_expires_at as strava_compute_expires_at
from services.strava.oauth import refresh_tokens as strava_refresh_tokens
from services.whoop import WhoopApiClient
from services.whoop.oauth import compute_expires_at as whoop_compute_expires_at
from services.whoop.oauth import refresh_tokens as whoop_refresh_tokens
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)

_ANALYSIS_AUTORETRY_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
)

# Postgres JSONB rejects null bytes and certain control characters that LLMs occasionally emit.
_CONTROL_CHAR_RE = __import__("re").compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML_TAG_RE = __import__("re").compile(r"<[^>]+>")
_worker_event_loops: dict[int, asyncio.AbstractEventLoop] = {}


def _get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """Return a stable event loop for the current Celery worker process.

    ``asyncio.run()`` creates a fresh event loop on every invocation. That is
    fine for isolated coroutines, but these scheduled Celery tasks use the
    shared async SQLAlchemy engine from ``api.deps``. Reusing the process-local
    loop avoids asyncpg connections being returned to a different event loop on
    a later task execution.
    """
    process_id = os.getpid()
    loop = _worker_event_loops.get(process_id)
    if loop is None or loop.is_closed():
        _worker_event_loops.clear()
        loop = asyncio.new_event_loop()
        _worker_event_loops[process_id] = loop
        logger.info("Initialized worker event loop for pid=%s", process_id)
    return loop


def _run_async_in_worker_loop(coro: Any) -> Any:
    loop = _get_worker_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _sanitize_for_db(obj: object) -> object:
    if isinstance(obj, str):
        return _CONTROL_CHAR_RE.sub("", obj)
    if isinstance(obj, dict):
        return {k: _sanitize_for_db(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_db(v) for v in obj]
    return obj


def _as_json_dict(value: object) -> dict[str, Any]:
    """Narrow an unknown JSON-ish value to a dict for SQLAlchemy JSONB columns."""
    return cast("dict[str, Any]", value)


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _strava_activity_date_key(activity: dict) -> str | None:
    raw_start = activity.get("start_date_local") or activity.get("start_date")
    if not isinstance(raw_start, str) or not raw_start.strip():
        return None
    return raw_start[:10]


def _build_strava_training_load_history(activities: list[dict]) -> list[dict]:
    daily_totals: dict[str, dict[str, object]] = {}
    for activity in activities:
        date_key = _strava_activity_date_key(activity)
        if not date_key:
            continue
        bucket = daily_totals.setdefault(
            date_key,
            {
                "date": date_key,
                "activity_count": 0,
                "relative_effort_total": 0.0,
                "suffer_score_total": 0.0,
                "moving_time_minutes_total": 0.0,
                "distance_m_total": 0.0,
                "_has_relative_effort": False,
                "_has_suffer_score": False,
            },
        )
        bucket["activity_count"] = cast("int", bucket["activity_count"]) + 1

        relative_effort = _safe_float(activity.get("relative_effort"))
        if relative_effort is not None:
            bucket["relative_effort_total"] = cast("float", bucket["relative_effort_total"]) + relative_effort
            bucket["_has_relative_effort"] = True

        suffer_score = _safe_float(activity.get("suffer_score"))
        if suffer_score is not None:
            bucket["suffer_score_total"] = cast("float", bucket["suffer_score_total"]) + suffer_score
            bucket["_has_suffer_score"] = True

        moving_time = _safe_float(activity.get("moving_time"))
        if moving_time is not None:
            bucket["moving_time_minutes_total"] = cast("float", bucket["moving_time_minutes_total"]) + (moving_time / 60.0)

        distance_m = _safe_float(activity.get("distance"))
        if distance_m is not None:
            bucket["distance_m_total"] = cast("float", bucket["distance_m_total"]) + distance_m

    payload: list[dict] = []
    for date_key in sorted(daily_totals.keys()):
        bucket = dict(daily_totals[date_key])
        has_relative_effort = bool(bucket.pop("_has_relative_effort", False))
        has_suffer_score = bool(bucket.pop("_has_suffer_score", False))
        load_value = None
        load_type = "strava_activity_count"
        if has_relative_effort:
            load_value = bucket.get("relative_effort_total")
            load_type = "strava_relative_effort"
        elif has_suffer_score:
            load_value = bucket.get("suffer_score_total")
            load_type = "strava_suffer_score"
        bucket["load_type"] = load_type
        bucket["load_value"] = load_value
        payload.append(bucket)
    return payload


def _list_strava_activities_with_pagination(
    *,
    client: StravaApiClient,
    after: int,
    before: int,
) -> list[dict]:
    activities: list[dict] = []
    page = 1
    per_page = 100
    while True:
        batch = client.list_activities(page=page, per_page=per_page, after=after, before=before)
        if not batch:
            break
        activities.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return activities


def _build_strava_activity_summary(activities: list[dict]) -> dict[str, Any]:
    total_distance_m = 0.0
    total_moving_time_seconds = 0.0
    total_relative_effort = 0.0
    total_suffer_score = 0.0
    has_relative_effort = False
    has_suffer_score = False
    for activity in activities:
        distance_m = _safe_float(activity.get("distance"))
        if distance_m is not None:
            total_distance_m += distance_m
        moving_time = _safe_float(activity.get("moving_time"))
        if moving_time is not None:
            total_moving_time_seconds += moving_time
        relative_effort = _safe_float(activity.get("relative_effort"))
        if relative_effort is not None:
            total_relative_effort += relative_effort
            has_relative_effort = True
        suffer_score = _safe_float(activity.get("suffer_score"))
        if suffer_score is not None:
            total_suffer_score += suffer_score
            has_suffer_score = True

    return {
        "activity_count": len(activities),
        "distance_km_total": round(total_distance_m / 1000.0, 2) if total_distance_m else 0.0,
        "moving_time_minutes_total": round(total_moving_time_seconds / 60.0, 1) if total_moving_time_seconds else 0.0,
        "relative_effort_total": total_relative_effort if has_relative_effort else None,
        "suffer_score_total": total_suffer_score if has_suffer_score else None,
    }


_ATHLETE_PROFILE_CONTEXT_PROMPT = """You are provided an athlete profile snapshot (persisted per user).
Use it to tailor analysis and planning, unless it conflicts with fresh device training data.

Athlete profile snapshot (JSON):
{athlete_profile_json}
"""


def _build_run_override_contexts(run_overrides: dict[str, Any] | None) -> tuple[str, str]:
    if not run_overrides:
        return "", ""

    def _clean(raw_value: Any) -> str:
        if raw_value is None:
            return ""
        if not isinstance(raw_value, str):
            raw_value = str(raw_value)
        return raw_value.strip()

    analysis_notes = _clean(run_overrides.get("analysis_notes"))
    planning_notes = _clean(run_overrides.get("planning_notes"))
    temporary_constraints = _clean(run_overrides.get("temporary_constraints"))

    analysis_sections: list[str] = []
    planning_sections: list[str] = []

    if analysis_notes:
        analysis_sections.append(f"Run overrides (analysis focus):\n{analysis_notes}")
    if planning_notes:
        analysis_sections.append(
            "Custom planning instructions for downstream planner fields "
            "(do not distort factual analysis; propagate relevant implications into "
            "`for_season_planner` and `for_weekly_planner`):\n"
            f"{planning_notes}"
        )
        planning_sections.append(
            "Custom planning instructions for this run "
            "(must preserve unless unsafe, infeasible, or contradicted by stronger athlete constraints):\n"
            f"{planning_notes}"
        )
    if temporary_constraints:
        constraint_section = f"Temporary constraints for this run (must constrain analysis and planning):\n{temporary_constraints}"
        analysis_sections.append(constraint_section)
        planning_sections.append(constraint_section)

    return "\n\n".join(analysis_sections).strip(), "\n\n".join(planning_sections).strip()


def _resolve_plotting_enabled(config: dict[str, Any], job_id: str) -> bool:
    requested_plotting = bool(config.get("enable_plotting", False))
    if requested_plotting:
        logger.warning(
            "Ignoring enable_plotting=true for job %s: plotting execution is disabled by policy",
            job_id,
        )
    return False


def _format_analysis_task_error_message(exc: Exception) -> str:
    if isinstance(exc, SoftTimeLimitExceeded):
        soft_limit_seconds = get_analysis_task_soft_time_limit_seconds()
        if soft_limit_seconds is not None:
            return f"Job timed out (soft time limit exceeded after {soft_limit_seconds}s)"
        return "Job timed out (worker soft time limit exceeded)"
    return str(exc) or "Analysis task failed"


def _get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Set DATABASE_URL (or configure the app to avoid importing "
            "worker tasks in environments without a database)."
        )
    return database_url.replace("+asyncpg", "")


@lru_cache(maxsize=1)
def _get_engine():
    return create_engine(_get_database_url())


def _whoop_access_token(db: Session, *, user_id: uuid.UUID, force_refresh: bool = False) -> str:
    creds = db.execute(
        select(WhoopCredentials).where(WhoopCredentials.user_id == user_id).with_for_update()
    ).scalar_one_or_none()
    if creds is None:
        raise ValueError("No Whoop credentials found for user")

    crypto = get_crypto_service()
    now = datetime.now(UTC)
    if not force_refresh and (
        creds.expires_at is not None and creds.expires_at.astimezone(UTC) > (now + timedelta(seconds=30))
    ):
        return crypto.decrypt(creds.encrypted_access_token)

    if not creds.encrypted_refresh_token:
        raise ValueError("Whoop refresh token is missing. Please reconnect Whoop.")

    settings = get_settings()
    if not settings.whoop_oauth_client_id or not settings.whoop_oauth_client_secret:
        raise RuntimeError("Whoop OAuth is not configured (missing client_id/client_secret)")

    refresh_token = crypto.decrypt(creds.encrypted_refresh_token)
    try:
        payload = whoop_refresh_tokens(
            refresh_token=refresh_token,
            client_id=settings.whoop_oauth_client_id,
            client_secret=settings.whoop_oauth_client_secret,
            scope="offline",
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in {400, 401}:
            db.delete(creds)
            db.commit()
            raise ValueError("Whoop connection expired. Please reconnect Whoop.") from exc
        raise

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise RuntimeError("Whoop token refresh returned an invalid access token")

    new_refresh = payload.get("refresh_token")
    creds.encrypted_access_token = crypto.encrypt(access_token)
    if isinstance(new_refresh, str) and new_refresh.strip():
        creds.encrypted_refresh_token = crypto.encrypt(new_refresh)
    creds.expires_at = whoop_compute_expires_at(now=now, expires_in=payload.get("expires_in"))
    creds.scope = str(payload.get("scope") or creds.scope or "")
    db.add(creds)
    db.commit()

    return access_token


def _strava_access_token(db: Session, *, user_id: uuid.UUID, force_refresh: bool = False) -> str:
    creds = db.execute(
        select(StravaCredentials).where(StravaCredentials.user_id == user_id).with_for_update()
    ).scalar_one_or_none()
    if creds is None:
        raise ValueError("No Strava credentials found for user")

    crypto = get_crypto_service()
    now = datetime.now(UTC)
    if not force_refresh and (
        creds.expires_at is not None and creds.expires_at.astimezone(UTC) > (now + timedelta(seconds=30))
    ):
        return crypto.decrypt(creds.encrypted_access_token)

    if not creds.encrypted_refresh_token:
        raise ValueError("Strava refresh token is missing. Please reconnect Strava.")

    settings = get_settings()
    if not settings.strava_oauth_client_id or not settings.strava_oauth_client_secret:
        raise RuntimeError("Strava OAuth is not configured (missing client_id/client_secret)")

    refresh_token = crypto.decrypt(creds.encrypted_refresh_token)
    try:
        payload = strava_refresh_tokens(
            refresh_token=refresh_token,
            client_id=settings.strava_oauth_client_id,
            client_secret=settings.strava_oauth_client_secret,
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in {400, 401}:
            db.delete(creds)
            db.commit()
            raise ValueError("Strava connection expired. Please reconnect Strava.") from exc
        raise

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise RuntimeError("Strava token refresh returned an invalid access token")

    new_refresh = payload.get("refresh_token")
    creds.encrypted_access_token = crypto.encrypt(access_token)
    if isinstance(new_refresh, str) and new_refresh.strip():
        creds.encrypted_refresh_token = crypto.encrypt(new_refresh)
    creds.expires_at = strava_compute_expires_at(
        now=now,
        expires_at=payload.get("expires_at"),
        expires_in=payload.get("expires_in"),
    )
    creds.scope = str(creds.scope or "")
    db.add(creds)
    db.commit()

    return access_token


def _extract_whoop_snapshot(
    db: Session,
    *,
    user_id: uuid.UUID,
    activities_days: int,
    metrics_days: int,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    workouts_start = now - timedelta(days=max(1, activities_days))
    metrics_start = now - timedelta(days=max(1, metrics_days))

    def _fetch_with_token(access_token: str) -> dict[str, Any]:
        client = WhoopApiClient(access_token=access_token)
        try:
            return {
                "profile_basic": client.get_basic_profile(),
                "body_measurement": client.get_body_measurement(),
                "workouts": client.list_workouts(start=workouts_start, end=now),
                "cycles": client.list_cycles(start=metrics_start, end=now),
                "recoveries": client.list_recoveries(start=metrics_start, end=now),
                "sleeps": client.list_sleeps(start=metrics_start, end=now),
            }
        finally:
            client.close()

    access_token = _whoop_access_token(db, user_id=user_id)
    try:
        return _fetch_with_token(access_token)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code != 401:
            raise
        # Best-effort: refresh and retry once if the stored access token was rejected.
        access_token = _whoop_access_token(db, user_id=user_id, force_refresh=True)
        return _fetch_with_token(access_token)


def _extract_strava_snapshot(
    db: Session,
    *,
    user_id: uuid.UUID,
    activities_days: int,
    metrics_days: int,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    activities_after = int((now - timedelta(days=max(1, activities_days))).timestamp())
    metrics_after = int((now - timedelta(days=max(1, metrics_days))).timestamp())
    before = int(now.timestamp())

    def _fetch_with_token(access_token: str) -> dict[str, Any]:
        client = StravaApiClient(access_token=access_token)
        try:
            recent_activities = _list_strava_activities_with_pagination(
                client=client,
                after=activities_after,
                before=before,
            )
            metrics_activities = _list_strava_activities_with_pagination(
                client=client,
                after=metrics_after,
                before=before,
            )
            return {
                "athlete_profile": client.get_logged_in_athlete(),
                "recent_activities": recent_activities,
                "training_load_history": _build_strava_training_load_history(metrics_activities),
                "activity_summary": _build_strava_activity_summary(recent_activities),
            }
        finally:
            client.close()

    access_token = _strava_access_token(db, user_id=user_id)
    try:
        return _fetch_with_token(access_token)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code != 401:
            raise
        access_token = _strava_access_token(db, user_id=user_id, force_refresh=True)
        return _fetch_with_token(access_token)


def get_sync_session() -> Session:
    return Session(_get_engine())


def _get_initial_draft_claim_event(db: Session, *, user_id: uuid.UUID) -> LocalUsageEvent | None:
    return db.execute(
        select(LocalUsageEvent).where(
            LocalUsageEvent.user_id == user_id,
            LocalUsageEvent.feature_key == FEATURE_INITIAL_DRAFT_PLAN,
            LocalUsageEvent.source_type == INITIAL_DRAFT_PLAN_SOURCE_TYPE,
        )
    ).scalar_one_or_none()


def _finalize_initial_draft_claim(db: Session, *, user_id: uuid.UUID, job_id: uuid.UUID):
    event = _get_initial_draft_claim_event(db, user_id=user_id)
    if event is None:
        return
    metadata = dict(event.payload_metadata or {})
    metadata["state"] = "consumed"
    metadata["analysis_job_id"] = str(job_id)
    metadata["finalized_at"] = datetime.now(UTC).isoformat()
    event.payload_metadata = metadata
    event.consumed_at = datetime.now(UTC)
    db.add(event)


def _release_initial_draft_claim(db: Session, *, user_id: uuid.UUID):
    event = _get_initial_draft_claim_event(db, user_id=user_id)
    if event is None:
        return
    metadata = event.payload_metadata if isinstance(event.payload_metadata, dict) else {}
    state = str(metadata.get("state") or "").strip().lower()
    if state != "pending":
        return
    db.delete(event)


def _record_full_run_consumption(db: Session, *, user_id: uuid.UUID, job_id: uuid.UUID):
    existing = db.execute(
        select(LocalUsageEvent).where(
            LocalUsageEvent.feature_key == FEATURE_FULL_RUN,
            LocalUsageEvent.source_type == "analysis_job",
            LocalUsageEvent.source_id == str(job_id),
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    db.add(
        LocalUsageEvent(
            user_id=user_id,
            feature_key=FEATURE_FULL_RUN,
            source_type="analysis_job",
            source_id=str(job_id),
            consumed_at=datetime.now(UTC),
        )
    )


def _should_defer_failure_to_autoretry(task: Any, exc: BaseException) -> bool:
    if not isinstance(exc, _ANALYSIS_AUTORETRY_EXCEPTIONS):
        return False
    request = getattr(task, "request", None)
    retries = int(getattr(request, "retries", 0) or 0)
    max_retries = int(getattr(task, "max_retries", 0) or 0)
    return retries < max_retries


def _cancel_requested(db: Session, job_id: uuid.UUID) -> bool:
    requested_at = db.execute(
        select(AnalysisJob.cancel_requested_at).where(AnalysisJob.id == job_id)
    ).scalar_one_or_none()
    return requested_at is not None


def _pydantic_dump(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _extract_expert_context(result: dict) -> dict:
    return {
        "metrics_outputs": _pydantic_dump(result.get("metrics_outputs")),
        "activity_outputs": _pydantic_dump(result.get("activity_outputs")),
        "physiology_outputs": _pydantic_dump(result.get("physiology_outputs")),
    }


def _extract_plan_markdown(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        output = value.get("output")
        if isinstance(output, str):
            return output
    return None


def _render_season_plan_blocks_as_markdown(plan: UiSeasonPlan) -> str:
    # Best-effort: keep full content by embedding existing HTML fragments.
    lines: list[str] = []
    lines.append("# Season Plan (from stored UI blocks)")
    lines.append("")
    lines.append(f"- Start: {plan.start_date}")
    lines.append(f"- End: {plan.end_date}")
    if plan.season_summary_line:
        lines.append(f"- Summary: {plan.season_summary_line}")
    lines.append("")

    if plan.global_nodes:
        lines.append("## Global Notes (nodes)")
        lines.append("```json")
        lines.append(
            json.dumps(
                [node.model_dump(mode="json") for node in plan.global_nodes],
                indent=2,
                ensure_ascii=False,
            )
        )
        lines.append("```")
        lines.append("")
    if plan.global_blocks:
        lines.append("## Global Notes (blocks)")
        for block in plan.global_blocks:
            lines.append(f"### {block.title or block.key}")
            lines.append(block.content_html)
            lines.append("")

    lines.append("## Phases")
    lines.append("")
    for phase in plan.phases:
        lines.append(f"### {phase.title} ({phase.start_date} -> {phase.end_date})")
        if phase.summary:
            lines.append(f"_Summary_: {phase.summary}")
        if phase.nodes:
            lines.append("```json")
            lines.append(
                json.dumps(
                    [node.model_dump(mode="json") for node in phase.nodes],
                    indent=2,
                    ensure_ascii=False,
                )
            )
            lines.append("```")
        for block in phase.blocks:
            lines.append(f"#### {block.title or block.key}")
            lines.append(block.content_html)
        lines.append("")

    return "\n".join(lines).strip()


def _compact_html_fragment(value: str, *, limit: int = 360) -> str:
    text = " ".join(_HTML_TAG_RE.sub(" ", value).split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _append_compact_block_context(lines: list[str], blocks: list[Any], *, prefix: str, limit: int):
    for block in blocks[:limit]:
        content = _compact_html_fragment(block.content_html)
        if content:
            lines.append(f"- {prefix}{block.title or block.key}: {content}")


def _weekly_day_details(day: Any) -> list[str | None]:
    return [
        str(day.date),
        day.workout_title or day.day_label or "Rest / no primary workout",
        f"focus={day.focus_type}" if day.focus_type else None,
        f"intensity={day.estimated_intensity}" if day.estimated_intensity else None,
        f"duration={day.estimated_duration_min} min" if day.estimated_duration_min is not None else None,
        f"distance={day.primary_distance_km} km" if day.primary_distance_km is not None else None,
        "completed=true" if day.is_completed else None,
    ]


def _append_weekly_day_context(lines: list[str], day: Any):
    lines.append(f"- {' | '.join(detail for detail in _weekly_day_details(day) if detail)}")
    if day.readiness_note:
        lines.append(f"  - Readiness: {day.readiness_note}")
    for block in day.blocks[:2]:
        content = _compact_html_fragment(block.content_html)
        if content:
            lines.append(f"  - {block.title or block.key}: {content}")


def _render_weekly_plan_blocks_as_markdown(plan: UiWeeklyPlan) -> str:
    # Best-effort compact context for continuity. Keep day-level intent and
    # intensity visible without replaying the full rendered UI payload.
    lines: list[str] = []
    lines.append("# Active Weekly Plan (from stored UI blocks)")
    lines.append("")
    if plan.plan_brief:
        lines.append(f"- Brief: {plan.plan_brief}")
    if plan.created_at:
        lines.append(f"- Created at: {plan.created_at}")
    if plan.version:
        lines.append(f"- Version: {plan.version}")
    lines.append("")

    if plan.global_blocks:
        lines.append("## Global Notes")
        _append_compact_block_context(lines, plan.global_blocks, prefix="", limit=3)
        lines.append("")

    for week in plan.weeks:
        week_label = week.week_label or week.week_theme or week.week_id
        lines.append(f"## {week_label} ({week.start_date} -> {week.end_date})")
        if week.week_theme and week.week_theme != week_label:
            lines.append(f"- Theme: {week.week_theme}")
        _append_compact_block_context(lines, week.notes_blocks, prefix="Week note - ", limit=2)
        for day in week.days:
            _append_weekly_day_context(lines, day)
        lines.append("")

    return "\n".join(lines).strip()


def _job_progress_steps(job: object) -> list[dict[str, Any]] | None:
    return cast("list[dict[str, Any]] | None", getattr(job, "progress_steps", None))


def _upsert_active_results(
    db: Session,
    *,
    user_id: uuid.UUID,
    source_job_id: uuid.UUID,
    result: dict,
) -> None:
    season_plan_reused = bool(result.get("season_plan_reused", False))

    analysis_blocks = result.get("analysis_blocks")
    season_plan_blocks = result.get("season_plan_blocks")
    weekly_plan_blocks = result.get("weekly_plan_blocks")

    if analysis_blocks is None or season_plan_blocks is None or weekly_plan_blocks is None:
        logger.warning(
            "Skipping active plan upsert for job %s (missing blocks)",
            source_job_id,
        )
        return

    analysis_data = _as_json_dict(_sanitize_for_db(analysis_blocks.model_dump(mode="json")))
    season_plan_data = _as_json_dict(_sanitize_for_db(season_plan_blocks.model_dump(mode="json")))
    weekly_plan_data = _as_json_dict(_sanitize_for_db(weekly_plan_blocks.model_dump(mode="json")))

    expert_context = _extract_expert_context(result)

    active_analysis = db.execute(select(ActiveAnalysis).where(ActiveAnalysis.user_id == user_id)).scalar_one_or_none()
    if active_analysis:
        next_analysis_version = active_analysis.version + 1
        active_analysis.version = next_analysis_version
        analysis_data["version"] = next_analysis_version
        active_analysis.analysis_data = analysis_data
        active_analysis.expert_context = expert_context
        active_analysis.source_job_id = source_job_id
    else:
        analysis_data["version"] = 1
        db.add(
            ActiveAnalysis(
                user_id=user_id,
                version=1,
                analysis_data=analysis_data,
                expert_context=expert_context,
                source_job_id=source_job_id,
            )
        )

    active_season_plan = db.execute(
        select(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == user_id)
    ).scalar_one_or_none()
    if active_season_plan:
        if season_plan_reused:
            logger.info("Season plan reused; leaving active_season_plan unchanged (user_id=%s)", user_id)
        else:
            next_season_version = active_season_plan.version + 1
            active_season_plan.version = next_season_version
            season_plan_data["version"] = next_season_version
            active_season_plan.plan_data = season_plan_data
            active_season_plan.source_job_id = source_job_id
    else:
        season_plan_data["version"] = 1
        db.add(
            ActiveSeasonPlan(
                user_id=user_id,
                version=1,
                plan_data=season_plan_data,
                source_job_id=source_job_id,
            )
        )

    active_weekly_plan = db.execute(
        select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id)
    ).scalar_one_or_none()
    if active_weekly_plan:
        next_weekly_version = active_weekly_plan.version + 1
        active_weekly_plan.version = next_weekly_version
        weekly_plan_data["version"] = next_weekly_version
        active_weekly_plan.plan_data = weekly_plan_data
        active_weekly_plan.source_job_id = source_job_id
    else:
        weekly_plan_data["version"] = 1
        db.add(
            ActiveWeeklyPlan(
                user_id=user_id,
                version=1,
                plan_data=weekly_plan_data,
                source_job_id=source_job_id,
            )
        )


def _is_initial_draft_run(job: AnalysisJob) -> bool:
    return str(job.config.get("_plan_generation_access_mode") or "").strip().lower() == "free_initial"


def _finish_job_as_cancelled(
    db: Session,
    *,
    job: AnalysisJob,
    release_initial_draft_claim: bool,
) -> None:
    job.status = JobStatus.CANCELLED.value
    job.completed_at = datetime.now()
    job.progress_steps = complete_active_analysis_progress_steps(
        _job_progress_steps(job),
        timestamp=datetime.now(UTC),
    )
    if release_initial_draft_claim:
        _release_initial_draft_claim(db, user_id=job.user_id)
    db.commit()


def _cancel_if_requested(
    db: Session,
    *,
    job: AnalysisJob,
    job_uuid: uuid.UUID,
    job_id: str,
    reason: str,
    release_initial_draft_claim: bool,
) -> bool:
    if not _cancel_requested(db, job_uuid):
        return False
    logger.info("Job %s %s", job_id, reason)
    _finish_job_as_cancelled(db, job=job, release_initial_draft_claim=release_initial_draft_claim)
    return True


def _mark_job_running(db: Session, *, job: AnalysisJob, celery_task_id: str) -> None:
    job.status = JobStatus.RUNNING.value
    job.config = {**job.config, "_celery_task_id": celery_task_id}
    job.progress_steps = normalize_analysis_progress_steps(_job_progress_steps(job) or initial_analysis_progress_steps())
    db.commit()


def _load_training_sources(
    db: Session,
    *,
    user_id: uuid.UUID,
    job_id: str,
    activities_days: int,
    metrics_days: int,
) -> tuple[dict[str, Any], list[str]]:
    sources: dict[str, Any] = {}
    extraction_errors: list[str] = []

    strava_creds = db.execute(select(StravaCredentials).where(StravaCredentials.user_id == user_id)).scalar_one_or_none()
    if strava_creds:
        try:
            sources["strava"] = _extract_strava_snapshot(
                db,
                user_id=user_id,
                activities_days=activities_days,
                metrics_days=metrics_days,
            )
        except Exception:
            logger.warning("Strava extraction failed for job %s; continuing with other sources", job_id, exc_info=True)
            extraction_errors.append("strava")

    whoop_creds = db.execute(select(WhoopCredentials).where(WhoopCredentials.user_id == user_id)).scalar_one_or_none()
    if whoop_creds:
        try:
            sources["whoop"] = _extract_whoop_snapshot(
                db,
                user_id=user_id,
                activities_days=activities_days,
                metrics_days=metrics_days,
            )
        except Exception:
            logger.warning("Whoop extraction failed for job %s; continuing with other sources", job_id, exc_info=True)
            extraction_errors.append("whoop")

    return sources, extraction_errors


def _build_training_data(*, sources: dict[str, Any], extraction_errors: list[str]) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "sources": sources,
        "source_gaps": sorted(set(extraction_errors)),
        "evidence_profile": build_evidence_profile(available_sources=sources.keys()),
    }


def _resolve_run_calendar(config: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, str]]]:
    now = datetime.now()
    start_date_value = config.get("plan_start_date")
    plan_start = datetime.strptime(start_date_value, "%Y-%m-%d") if start_date_value else now
    current_date = {"date": now.strftime("%Y-%m-%d"), "day_name": now.strftime("%A")}
    week_dates = [
        {
            "date": (plan_start + timedelta(days=offset)).strftime("%Y-%m-%d"),
            "day_name": (plan_start + timedelta(days=offset)).strftime("%A"),
        }
        for offset in range(28)
    ]
    return current_date, week_dates


def _athlete_profile_json(config: dict[str, Any]) -> str:
    athlete_profile = config.get("athlete_profile") or {}
    try:
        return json.dumps(athlete_profile, ensure_ascii=False, sort_keys=True, indent=2)
    except Exception:
        return str(athlete_profile)


def _build_workflow_contexts(config: dict[str, Any]) -> tuple[str, str]:
    persisted_context = _ATHLETE_PROFILE_CONTEXT_PROMPT.format(athlete_profile_json=_athlete_profile_json(config))
    analysis_override_context, planning_override_context = _build_run_override_contexts(config.get("run_overrides"))
    analysis_context = (
        persisted_context + ("\n\n" + analysis_override_context if analysis_override_context else "")
    ).strip()
    planning_context = (
        persisted_context + ("\n\n" + planning_override_context if planning_override_context else "")
    ).strip()
    return analysis_context, planning_context


def _validate_existing_season_plan(plan_data: object, *, user_id: uuid.UUID) -> UiSeasonPlan | None:
    if not isinstance(plan_data, dict):
        return None
    try:
        return UiSeasonPlan.model_validate(plan_data)
    except Exception:
        logger.warning("Failed to validate existing season plan blocks for user %s", user_id, exc_info=True)
        return None


def _season_markdown_from_source_job(db: Session, *, source_job_id: object) -> str | None:
    if source_job_id is None:
        return None
    source_job = db.execute(select(AnalysisJob).where(AnalysisJob.id == source_job_id)).scalar_one_or_none()
    if source_job is None:
        return None
    source_result = getattr(source_job, "result", None)
    if not isinstance(source_result, dict):
        return None
    return _extract_plan_markdown(source_result.get("season_plan"))


def _load_existing_season_context(
    db: Session,
    *,
    user_id: uuid.UUID,
    is_initial_draft_run: bool,
) -> tuple[str | None, UiSeasonPlan | None]:
    if is_initial_draft_run:
        return None, None
    try:
        active_season = db.execute(select(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == user_id)).scalar_one_or_none()
        if active_season is None:
            return None, None

        season_blocks = _validate_existing_season_plan(getattr(active_season, "plan_data", None), user_id=user_id)
        season_markdown = _season_markdown_from_source_job(
            db,
            source_job_id=getattr(active_season, "source_job_id", None),
        )
        if season_markdown is None and season_blocks is not None:
            season_markdown = _render_season_plan_blocks_as_markdown(season_blocks)
        return season_markdown, season_blocks
    except Exception:
        logger.warning("Failed to load existing season plan for user %s", user_id, exc_info=True)
        return None, None


def _load_existing_weekly_context(
    db: Session,
    *,
    user_id: uuid.UUID,
    is_initial_draft_run: bool,
) -> str | None:
    if is_initial_draft_run:
        return None
    try:
        active_weekly = db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id)).scalar_one_or_none()
        if active_weekly is None or not isinstance(getattr(active_weekly, "plan_data", None), dict):
            return None
        weekly_plan_blocks = UiWeeklyPlan.model_validate(active_weekly.plan_data)
        return _render_weekly_plan_blocks_as_markdown(weekly_plan_blocks)
    except Exception:
        logger.warning("Failed to load existing weekly plan for user %s", user_id, exc_info=True)
        return None


def _build_progress_callbacks(db: Session, *, job: AnalysisJob, job_id: str):
    async def node_started_callback(node_name: str):
        current_step = next(
            (
                step
                for step in (_job_progress_steps(job) or [])
                if isinstance(step, dict) and step.get("node") == node_name
            ),
            None,
        )
        if isinstance(current_step, dict) and current_step.get("status") == "active":
            return
        updated_steps, current_label = mark_analysis_progress_step_started(
            _job_progress_steps(job),
            node_name=node_name,
            timestamp=datetime.now(UTC),
        )
        job.progress_steps = updated_steps
        db.add(job)
        db.commit()
        logger.info("Job %s progress -> %s (%s)", job_id, node_name, current_label)

    async def node_completed_callback(node_name: str):
        current_step = next(
            (
                step
                for step in (_job_progress_steps(job) or [])
                if isinstance(step, dict) and step.get("node") == node_name
            ),
            None,
        )
        if isinstance(current_step, dict) and current_step.get("status") == "completed":
            return
        job.progress_steps = mark_analysis_progress_step_completed(
            _job_progress_steps(job),
            node_name=node_name,
            timestamp=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        logger.info("Job %s completed -> %s", job_id, node_name)

    async def node_timing_callback(node_name: str, duration_seconds: float):
        job.progress_steps = record_analysis_step_timing(
            _job_progress_steps(job),
            node_name=node_name,
            duration_seconds=duration_seconds,
            timestamp=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        logger.info("Job %s timing -> %s (%.3fs)", job_id, node_name, duration_seconds)

    return node_started_callback, node_completed_callback, node_timing_callback


def _cost_totals_from_result(result: dict[str, Any]) -> tuple[float, int]:
    cost_total = float(
        result.get("cost_summary", {}).get("total_cost_usd", 0.0)
        or result.get("execution_metadata", {}).get("total_cost_usd", 0.0)
        or sum(cost.get("total_cost", 0) for cost in result.get("costs", []))
    )
    total_tokens = int(
        result.get("cost_summary", {}).get("total_tokens", 0)
        or result.get("execution_metadata", {}).get("total_tokens", 0)
    )
    return cost_total, total_tokens


def _serializable_analysis_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "analysis_blocks": (
            analysis_blocks.model_dump(mode="json") if (analysis_blocks := result.get("analysis_blocks")) is not None else None
        ),
        "weekly_plan_blocks": (
            weekly_blocks.model_dump(mode="json") if (weekly_blocks := result.get("weekly_plan_blocks")) is not None else None
        ),
        "season_plan_blocks": (
            season_blocks.model_dump(mode="json") if (season_blocks := result.get("season_plan_blocks")) is not None else None
        ),
        "season_plan": result.get("season_plan"),
        "weekly_plan": result.get("weekly_plan"),
        "execution_id": result.get("execution_id"),
        "cost_summary": result.get("cost_summary"),
        "execution_metadata": result.get("execution_metadata"),
    }


def _record_analysis_cost(db: Session, *, job: AnalysisJob, result: dict[str, Any]) -> None:
    execution_trace_metadata = trace_metadata_from_execution_metadata(
        cast("dict[str, Any] | None", result.get("execution_metadata")),
        default_run_name="paced_coach_workflow",
    )
    ai_cost_snapshot = capture_langsmith_run_costs(execution_trace_metadata)
    if ai_cost_snapshot.cost_status == "missing":
        ai_cost_snapshot = snapshot_from_legacy_cost_summary(cast("dict[str, Any] | None", result.get("cost_summary")))
    db.add(
        build_ai_run_cost_record(
            user_id=job.user_id,
            thread_id=None,
            feature="analysis_workflow",
            source_type="analysis_job",
            source_id=job.id,
            run_name="paced_coach_workflow",
            trace_metadata=execution_trace_metadata,
            cost_snapshot=ai_cost_snapshot,
            source_metadata={"execution_id": result.get("execution_id")},
        )
    )


def _complete_analysis_job(
    db: Session,
    *,
    job: AnalysisJob,
    job_uuid: uuid.UUID,
    result: dict[str, Any],
    finalize_initial_draft_claim: bool,
) -> None:
    cost_total, total_tokens = _cost_totals_from_result(result)
    job.status = JobStatus.COMPLETED.value
    job.result = _as_json_dict(_sanitize_for_db(_serializable_analysis_result(result)))
    job.cost_usd = cost_total
    job.tokens_used = total_tokens
    _record_analysis_cost(db, job=job, result=result)
    job.completed_at = datetime.now()
    job.progress_steps = complete_active_analysis_progress_steps(
        _job_progress_steps(job),
        timestamp=datetime.now(UTC),
    )

    _upsert_active_results(db, user_id=job.user_id, source_job_id=job_uuid, result=result)
    _record_full_run_consumption(db, user_id=job.user_id, job_id=job_uuid)
    if finalize_initial_draft_claim:
        _finalize_initial_draft_claim(db, user_id=job.user_id, job_id=job_uuid)
    db.commit()


def _fail_analysis_job(
    db: Session,
    *,
    job: AnalysisJob,
    exc: Exception,
    release_initial_draft_claim: bool,
) -> None:
    job.status = JobStatus.FAILED.value
    job.error_message = _format_analysis_task_error_message(exc)
    job.completed_at = datetime.now()
    job.progress_steps = complete_active_analysis_progress_steps(
        _job_progress_steps(job),
        timestamp=datetime.now(UTC),
    )
    if release_initial_draft_claim:
        _release_initial_draft_claim(db, user_id=job.user_id)
    db.commit()


def _prepare_analysis_job_for_run(
    db: Session,
    *,
    job: AnalysisJob,
    job_uuid: uuid.UUID,
    job_id: str,
    celery_task_id: str,
    is_initial_draft_run: bool,
) -> bool:
    if job.status == JobStatus.CANCELLED.value:
        logger.info("Job %s cancelled before start", job_id)
        _finish_job_as_cancelled(
            db,
            job=job,
            release_initial_draft_claim=is_initial_draft_run,
        )
        return False

    if _cancel_if_requested(
        db,
        job=job,
        job_uuid=job_uuid,
        job_id=job_id,
        reason="cancelled before start",
        release_initial_draft_claim=is_initial_draft_run,
    ):
        return False

    _mark_job_running(db, job=job, celery_task_id=celery_task_id)
    return True


def _run_analysis_workflow_for_job(
    db: Session,
    *,
    job: AnalysisJob,
    job_uuid: uuid.UUID,
    job_id: str,
    is_initial_draft_run: bool,
) -> dict[str, Any] | None:
    if _cancel_if_requested(
        db,
        job=job,
        job_uuid=job_uuid,
        job_id=job_id,
        reason="cancellation requested; stopping early",
        release_initial_draft_claim=is_initial_draft_run,
    ):
        return None

    config = job.config
    activities_days = int(config.get("activities_days", 7) or 7)
    metrics_days = int(config.get("metrics_days", 14) or 14)
    sources, extraction_errors = _load_training_sources(
        db,
        user_id=job.user_id,
        job_id=job_id,
        activities_days=activities_days,
        metrics_days=metrics_days,
    )
    training_data = _build_training_data(sources=sources, extraction_errors=extraction_errors)
    if not sources:
        logger.info("Job %s proceeding in providerless Draft Mode", job_id)

    if _cancel_if_requested(
        db,
        job=job,
        job_uuid=job_uuid,
        job_id=job_id,
        reason="cancellation requested after data extraction; stopping",
        release_initial_draft_claim=is_initial_draft_run,
    ):
        return None

    current_date, week_dates = _resolve_run_calendar(config)
    analysis_context, planning_context = _build_workflow_contexts(config)
    existing_season_plan_md, existing_season_plan_blocks = _load_existing_season_context(
        db,
        user_id=job.user_id,
        is_initial_draft_run=is_initial_draft_run,
    )
    if existing_season_plan_md:
        logger.info(
            "Loaded existing season plan for reuse (chars=%s, has_blocks=%s)",
            len(existing_season_plan_md),
            bool(existing_season_plan_blocks),
        )

    existing_weekly_plan_md = _load_existing_weekly_context(
        db,
        user_id=job.user_id,
        is_initial_draft_run=is_initial_draft_run,
    )
    if existing_weekly_plan_md:
        logger.info("Loaded existing weekly plan for transition context (chars=%s)", len(existing_weekly_plan_md))

    node_started_callback, node_completed_callback, node_timing_callback = _build_progress_callbacks(
        db,
        job=job,
        job_id=job_id,
    )
    result = asyncio.run(
        run_complete_analysis_and_planning(
            user_id=str(job.user_id),
            athlete_name=config.get("athlete_name", "Athlete"),
            training_data=training_data,
            analysis_context=analysis_context,
            planning_context=planning_context,
            competitions=config.get("competitions", []),
            current_date=current_date,
            week_dates=week_dates,
            plotting_enabled=_resolve_plotting_enabled(config, job_id),
            hitl_enabled=False,
            skip_synthesis=False,
            existing_season_plan=existing_season_plan_md,
            existing_season_plan_blocks=existing_season_plan_blocks,
            existing_weekly_plan=existing_weekly_plan_md,
            transition_context=build_training_transition_context(
                training_data,
                current_date=current_date,
                existing_weekly_plan=existing_weekly_plan_md,
            ),
            node_started_callback=node_started_callback,
            node_completed_callback=node_completed_callback,
            node_timing_callback=node_timing_callback,
        )
    )

    if _cancel_if_requested(
        db,
        job=job,
        job_uuid=job_uuid,
        job_id=job_id,
        reason="cancelled during workflow; discarding result",
        release_initial_draft_claim=is_initial_draft_run,
    ):
        return None
    return result


def _handle_analysis_task_exception(
    self,
    db: Session,
    *,
    job: AnalysisJob,
    job_id: str,
    exc: Exception,
    is_initial_draft_run: bool,
) -> None:
    if _should_defer_failure_to_autoretry(self, exc):
        logger.warning(
            "Analysis task hit retriable error for job %s; leaving claim pending until retry exhaustion",
            job_id,
            exc_info=True,
        )
        db.rollback()
        raise exc
    logger.exception("Analysis task failed for job %s: %s", job_id, exc)
    _fail_analysis_job(
        db,
        job=job,
        exc=exc,
        release_initial_draft_claim=is_initial_draft_run,
    )
    raise exc


@celery_app.task(
    bind=True,
    autoretry_for=_ANALYSIS_AUTORETRY_EXCEPTIONS,
    retry_backoff=60,
    retry_backoff_max=600,
    max_retries=2,
)
def run_analysis_task(self, job_id: str):
    logger.info("Starting analysis task for job %s", job_id)

    with get_sync_session() as db:
        job_uuid = uuid.UUID(job_id)
        job = db.execute(select(AnalysisJob).where(AnalysisJob.id == job_uuid)).scalar_one_or_none()

        if not job:
            logger.error("Job %s not found", job_id)
            return

        is_initial_draft_run = _is_initial_draft_run(job)

        if not _prepare_analysis_job_for_run(
            db,
            job=job,
            job_uuid=job_uuid,
            job_id=job_id,
            celery_task_id=self.request.id,
            is_initial_draft_run=is_initial_draft_run,
        ):
            return

        try:
            result = _run_analysis_workflow_for_job(
                db,
                job=job,
                job_uuid=job_uuid,
                job_id=job_id,
                is_initial_draft_run=is_initial_draft_run,
            )
            if result is None:
                return

            _complete_analysis_job(
                db,
                job=job,
                job_uuid=job_uuid,
                result=result,
                finalize_initial_draft_claim=is_initial_draft_run,
            )

            logger.info("Analysis task completed for job %s", job_id)

        except SoftTimeLimitExceeded as exc:
            logger.warning("Analysis task hit soft time limit for job %s", job_id)
            _fail_analysis_job(
                db,
                job=job,
                exc=exc,
                release_initial_draft_claim=is_initial_draft_run,
            )
            raise

        except Exception as exc:
            _handle_analysis_task_exception(
                self,
                db,
                job=job,
                job_id=job_id,
                exc=exc,
                is_initial_draft_run=is_initial_draft_run,
            )


@celery_app.task(name="worker.tasks.run_daily_coach_proactive_eval_task")
def run_daily_coach_proactive_eval_task():
    logger.info("Daily coach proactive eval is disabled")


async def _run_nightly_coach_memory_compaction_async():
    from api.deps import async_session_maker

    async with async_session_maker() as db:
        row = await db.execute(select(CoachThread).order_by(CoachThread.updated_at.asc()))
        thread_ids = [thread.id for thread in row.scalars().all()]
    compacted = 0
    for thread_id in thread_ids:
        try:
            async with async_session_maker() as db:
                row = await db.execute(select(CoachThread).where(CoachThread.id == thread_id))
                thread = row.scalar_one_or_none()
                if thread is None:
                    continue
                updated = await maybe_update_thread_memory(
                    db,
                    thread=thread,
                    force=True,
                )
                if updated:
                    await db.commit()
                    compacted += 1
        except Exception:
            logger.exception("Memory compaction failed for thread %s", thread_id)
    return compacted


@celery_app.task(name="worker.tasks.run_nightly_coach_memory_compaction_task")
def run_nightly_coach_memory_compaction_task():
    logger.info("Running nightly coach memory compaction")
    compacted = _run_async_in_worker_loop(_run_nightly_coach_memory_compaction_async())
    logger.info("Nightly coach memory compaction completed compacted=%s", compacted)


async def _run_coach_idempotency_cleanup_async():
    from api.deps import async_session_maker

    cutoff = datetime.now(UTC)
    async with async_session_maker() as db:
        result = await db.execute(
            delete(CoachTurnRequest).where(
                CoachTurnRequest.expires_at < cutoff,
            )
        )
        await db.commit()
    deleted_count = cast("int | None", getattr(result, "rowcount", None))
    return deleted_count or 0


@celery_app.task(name="worker.tasks.run_coach_idempotency_cleanup_task")
def run_coach_idempotency_cleanup_task():
    deleted = _run_async_in_worker_loop(_run_coach_idempotency_cleanup_async())
    logger.info("Coach idempotency cleanup completed deleted=%s", deleted)
