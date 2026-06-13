from __future__ import annotations

import html
import re
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.models.athlete_profile import AthleteProfile
from api.models.coach_proposal import CoachProposal
from api.models.coach_thread import CoachThread
from api.models.competition import Competition
from api.models.daily_update_run import DailyUpdateRun
from api.models.weekly_recap_run import WeeklyRecapRun
from api.services.active_plans import get_active_analysis, get_active_season_plan, get_active_weekly_plan
from api.services.athlete_time import get_athlete_time_context
from api.services.connected_coaching import resolve_connected_coaching_gate
from api.services.daily_sync_sources import extract_daily_sync_sources
from api.services.daily_update_runs import fail_stale_pending_daily_update_run
from api.services.full_run_policy import evaluate_weekly_recap_availability
from api.services.html_sanitizer import sanitize_html
from api.services.integration_status import load_integrations_status, training_provider_notice_message
from api.services.local_readiness import format_llm_provider_key_names, has_llm_provider_key
from api.services.local_usage import get_local_usage_context, has_weekly_recap_feature_access
from api.services.recap import (
    extract_recap_action_preview,
    extract_recap_summary_preview,
    get_recap_pending_action,
    get_recap_thread_id,
)
from services.ai.langgraph.schemas.ui_blocks import UiDayPlan, UiDisclosureNode, UiHtmlBlock, UiKpi, UiWeeklyPlan

_HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
_SENTENCE_BREAK_PATTERN = re.compile(r"[.!?](?=\s|$)")
_CLAUSE_BREAK_PATTERN = re.compile(r"[,;:](?=\s|$)")


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _profile_completeness(profile: dict | None) -> int:
    if not isinstance(profile, dict):
        return 0
    physiology = profile.get("physiology", {})
    preferences = profile.get("preferences", {})
    availability = profile.get("availability", {})
    goals = profile.get("goals", {})

    checks = [
        bool((physiology or {}).get("ftp") or (physiology or {}).get("lthr") or (physiology or {}).get("max_hr")),
        bool((preferences or {}).get("sports")),
        bool((availability or {}).get("days_per_week")),
        bool(_normalize_text((availability or {}).get("time_windows"))),
        bool(_normalize_text((goals or {}).get("primary_goal"))),
    ]
    return round((sum(1 for item in checks if item) / len(checks)) * 100)


def _dashboard_warnings(*, profile: dict | None, has_competitions: bool) -> list[str]:
    warnings: list[str] = []
    if _profile_completeness(profile) < 65:
        warnings.append("Fill key profile fields to improve intensity and constraint handling.")
    if not has_competitions:
        warnings.append("Add at least one competition to anchor periodization and race specificity.")
    return warnings


def _profile_has_primary_goal(profile: dict | None) -> bool:
    if not isinstance(profile, dict):
        return False
    goals = profile.get("goals", {})
    return bool(_normalize_text((goals or {}).get("primary_goal")))


def _build_first_run_state(
    *,
    profile: dict | None,
    has_competitions: bool,
    has_active_plan: bool,
    has_connected_source: bool,
) -> dict[str, Any]:
    llm_ready = has_llm_provider_key()
    profile_completeness = _profile_completeness(profile)
    profile_ready = profile_completeness >= 65
    goal_ready = _profile_has_primary_goal(profile) or has_competitions
    blockers: list[str] = []

    if not llm_ready:
        blockers.append(f"Add {format_llm_provider_key_names()} to your local .env and restart the API.")
    if not profile_ready:
        blockers.append("Complete the athlete profile so the planner has constraints, sports, and availability.")
    if not goal_ready:
        blockers.append("Add a primary goal or race calendar entry so the planner can anchor the block.")

    if has_active_plan:
        next_step = "generated"
        title = "Training plan ready"
        body = "Your current plan is available locally. Connected sources can improve daily sync and recaps, but they are not required to view or discuss the plan."
        primary_action = {"label": "Open training plan", "href": "/app/plan"}
        secondary_actions = [{"label": "Ask coach", "href": "/app/coach"}]
    elif not llm_ready:
        next_step = "llm_key"
        title = "Add one LLM key"
        body = "Manual Mode can run without Strava or WHOOP, but local plan generation still needs one supported LLM provider key."
        primary_action = None
        secondary_actions = []
    elif not profile_ready:
        next_step = "profile"
        title = "Complete your athlete profile"
        body = "Manual Mode uses your declared physiology, sports, availability, and constraints as the baseline planning evidence."
        primary_action = {"label": "Complete profile", "href": "/app/profile"}
        secondary_actions = []
    elif not goal_ready:
        next_step = "goal"
        title = "Add a goal or race"
        body = "Give the planner a target before generating the season roadmap and first 28-day block."
        primary_action = {"label": "Add goal or race", "href": "/app/competitions"}
        secondary_actions = [{"label": "Edit profile goal", "href": "/app/profile"}]
    else:
        next_step = "generate"
        title = "Generate your first local plan"
        body = "Ready for Draft Mode: the planner will use your saved profile, goal/race context, and any notes you add on the generation screen."
        primary_action = {"label": "Generate plan", "href": "/app/new"}
        secondary_actions = [
            {"label": "Review profile", "href": "/app/profile"},
            {"label": "Review races", "href": "/app/competitions"},
        ]

    return {
        "mode": "connected" if has_connected_source else "manual",
        "evidence_level": "connected" if has_connected_source else "declared_only",
        "llm_ready": llm_ready,
        "profile_completeness": profile_completeness,
        "profile_ready": profile_ready,
        "goal_ready": goal_ready,
        "has_competitions": has_competitions,
        "has_active_plan": has_active_plan,
        "has_connected_source": has_connected_source,
        "next_step": next_step,
        "title": title,
        "body": body,
        "primary_action": primary_action,
        "secondary_actions": secondary_actions,
        "blockers": blockers,
    }


async def _load_dashboard_integrations_context(db: AsyncSession, *, user_id):
    integrations_status = await load_integrations_status(
        db,
        user_id=user_id,
        settings=get_settings(),
    )
    return integrations_status, training_provider_notice_message(integrations_status)


def _resolve_daily_sync_status(
    *,
    daily_run: DailyUpdateRun | None,
    weekly_plan_available: bool,
) -> tuple[str, bool, str | None]:
    if daily_run is None:
        return "idle", weekly_plan_available, None

    normalized_daily_status = str(daily_run.status or "").strip().lower()
    if normalized_daily_status in {"done", "completed"}:
        return "completed", True, daily_run.error_message
    if normalized_daily_status == "pending":
        return "pending", True, daily_run.error_message
    if normalized_daily_status == "failed":
        return "failed", True, daily_run.error_message
    return "idle", weekly_plan_available, daily_run.error_message


def _resolve_daily_sync_attention(
    *,
    provider_notice: str | None,
) -> str | None:
    return provider_notice


def _truncate_preview_text(preview: str, *, max_chars: int) -> str:
    if len(preview) <= max_chars:
        return preview

    sentence_min_chars = max(48, int(max_chars * 0.35))
    sentence_breaks = [
        match.end()
        for match in _SENTENCE_BREAK_PATTERN.finditer(preview[: max_chars + 1])
        if match.end() >= sentence_min_chars
    ]
    if sentence_breaks:
        return preview[: sentence_breaks[-1]].rstrip()

    clause_min_chars = max(72, int(max_chars * 0.45))
    clause_breaks = [
        match.start()
        for match in _CLAUSE_BREAK_PATTERN.finditer(preview[: max_chars + 1])
        if match.start() >= clause_min_chars
    ]
    if clause_breaks:
        return f"{preview[: clause_breaks[-1]].rstrip()}..."

    candidate = preview[: max_chars + 1]
    word_break = candidate.rfind(" ")
    if word_break >= max(32, int(max_chars * 0.6)):
        candidate = candidate[:word_break]
    else:
        candidate = preview[:max_chars]
    return f"{candidate.rstrip(' ,;:')}..."


def _extract_html_text(content_html: str) -> str:
    normalized = html.unescape(_HTML_TAG_PATTERN.sub(" ", content_html)).replace("\n", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def _build_html_preview(content_html: str, *, max_chars: int = 180) -> str:
    preview = _extract_html_text(content_html)
    return _truncate_preview_text(preview, max_chars=max_chars)


def _split_preview_text(preview: str) -> tuple[str | None, str | None]:
    normalized = _normalize_text(preview)
    if not normalized:
        return None, None

    for match in _SENTENCE_BREAK_PATTERN.finditer(normalized):
        if match.end() < 10:
            continue
        primary = normalized[: match.end()].strip()
        secondary = normalized[match.end() :].strip()
        return primary, secondary or None

    return normalized, None


def _build_coach_surface_payload(
    *,
    source: str,
    scope: str,
    primary_label: str,
    primary_text: str | None,
    secondary_text: str | None,
    updated_at: datetime | None,
) -> dict[str, Any] | None:
    normalized_primary = _normalize_text(primary_text)
    normalized_secondary = _normalize_text(secondary_text)

    if not normalized_primary and normalized_secondary:
        normalized_primary = normalized_secondary
        normalized_secondary = ""

    if not normalized_primary:
        return None

    return {
        "source": source,
        "scope": scope,
        "primary_label": primary_label,
        "primary_text": normalized_primary,
        "secondary_text": normalized_secondary or None,
        "updated_at": updated_at.astimezone(UTC).isoformat() if updated_at is not None else None,
    }


def _empty_coach_surface() -> dict[str, Any]:
    return {
        "source": "none",
        "scope": "none",
        "primary_label": None,
        "primary_text": None,
        "secondary_text": None,
        "updated_at": None,
    }


def _parse_updated_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None


def _sanitize_focus_blocks(raw_blocks: object) -> list[UiHtmlBlock]:
    if not isinstance(raw_blocks, list):
        return []

    sanitized: list[UiHtmlBlock] = []
    seen_keys: set[str] = set()
    for raw_block in raw_blocks:
        try:
            block = UiHtmlBlock.model_validate(raw_block)
        except Exception:
            continue
        key = block.key
        if key in seen_keys:
            suffix = 1
            while f"{key}-{suffix}" in seen_keys:
                suffix += 1
            key = f"{key}-{suffix}"
        seen_keys.add(key)
        sanitized.append(
            block.model_copy(
                update={
                    "key": key,
                    "content_html": sanitize_html(block.content_html),
                }
            )
        )
    return sanitized


def _sanitize_dashboard_kpis(raw_kpis: object) -> list[UiKpi]:
    if not isinstance(raw_kpis, list):
        return []

    sanitized: list[UiKpi] = []
    seen_ids: set[str] = set()
    for raw_kpi in raw_kpis:
        try:
            kpi = UiKpi.model_validate(raw_kpi)
        except Exception:
            continue
        kpi_id = kpi.kpi_id.strip() or "dashboard-kpi"
        if kpi_id in seen_ids:
            suffix = 1
            while f"{kpi_id}-{suffix}" in seen_ids:
                suffix += 1
            kpi_id = f"{kpi_id}-{suffix}"
        seen_ids.add(kpi_id)
        sanitized.append(kpi.model_copy(update={"kpi_id": kpi_id}))
    return sanitized[:6]


def _flatten_day_nodes(nodes: list[UiDisclosureNode]) -> list[UiHtmlBlock]:
    flattened: list[UiHtmlBlock] = []
    for node in nodes:
        flattened.extend(node.blocks)
        if node.children:
            flattened.extend(_flatten_day_nodes(node.children))
    return flattened


def flatten_day_blocks(day: UiDayPlan) -> list[UiHtmlBlock]:
    if day.blocks:
        return list(day.blocks)
    if day.nodes:
        return _flatten_day_nodes(day.nodes)
    return []


def find_day_for_date(weekly_plan: UiWeeklyPlan, *, target_date_iso: str) -> UiDayPlan | None:
    for week in weekly_plan.weeks:
        for day in week.days:
            if str(day.date) == target_date_iso:
                return day
    return None


def compose_day_override(
    *,
    weekly_plan: UiWeeklyPlan | None,
    target_date_iso: str,
    today_focus_blocks: list[UiHtmlBlock],
) -> UiDayPlan | None:
    if weekly_plan is None:
        return None
    base_day = find_day_for_date(weekly_plan, target_date_iso=target_date_iso)
    if base_day is None:
        return None
    return base_day.model_copy(
        update={
            "blocks": [*today_focus_blocks, *flatten_day_blocks(base_day)],
            "nodes": [],
        }
    )


async def _get_daily_thread_id(db: AsyncSession, *, run: DailyUpdateRun | None) -> str | None:
    if run is None or run.proposal_id is None:
        return None
    proposal_row = await db.execute(
        select(CoachProposal.thread_id).where(CoachProposal.id == run.proposal_id)
    )
    thread_id = proposal_row.scalar_one_or_none()
    return str(thread_id) if thread_id is not None else None


def _coerce_target_date_iso(value: object) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _coerce_target_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return date.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _format_sync_date_label(target_date: date) -> str:
    return target_date.strftime("%b %d").replace(" 0", " ")


def _build_daily_status_label(*, target_date: date | None, today_local_date: date) -> str:
    if target_date is None:
        return "Last sync"

    days_ago = (today_local_date - target_date).days
    if days_ago <= 0:
        return "Morning sync"
    if days_ago == 1:
        return "Last sync (yesterday)"
    return f"Last sync ({_format_sync_date_label(target_date)})"


def _build_daily_status_surface(
    *,
    daily_run: DailyUpdateRun,
    dashboard_kpis: list[UiKpi],
    today_local_iso: str,
) -> dict[str, Any]:
    today_local_date = date.fromisoformat(today_local_iso)
    target_date = _coerce_target_date(daily_run.target_date)
    target_date_iso = _coerce_target_date_iso(daily_run.target_date)
    return {
        "kpis": [kpi.model_dump(mode="json") for kpi in dashboard_kpis],
        "source": "daily_update",
        "label": _build_daily_status_label(target_date=target_date, today_local_date=today_local_date),
        "updated_at": daily_run.updated_at.astimezone(UTC).isoformat() if daily_run.updated_at is not None else None,
        "target_date": target_date_iso,
    }


def _build_status_surface(
    *,
    analysis_payload: dict[str, Any] | None,
    today_daily_run: DailyUpdateRun | None,
    completed_daily_runs: Sequence[DailyUpdateRun],
    daily_payload: dict[str, Any],
    today_local_iso: str,
) -> dict[str, Any]:
    daily_dashboard_kpis = _sanitize_dashboard_kpis(daily_payload.get("dashboard_kpis"))
    seen_run_ids: set[object] = set()

    if today_daily_run is not None:
        seen_run_ids.add(today_daily_run.id)
        if daily_dashboard_kpis:
            return _build_daily_status_surface(
                daily_run=today_daily_run,
                dashboard_kpis=daily_dashboard_kpis,
                today_local_iso=today_local_iso,
            )

    for completed_run in completed_daily_runs:
        if completed_run.id in seen_run_ids:
            continue
        seen_run_ids.add(completed_run.id)
        completed_payload = completed_run.update_payload if isinstance(completed_run.update_payload, dict) else {}
        completed_dashboard_kpis = _sanitize_dashboard_kpis(completed_payload.get("dashboard_kpis"))
        if completed_dashboard_kpis:
            return _build_daily_status_surface(
                daily_run=completed_run,
                dashboard_kpis=completed_dashboard_kpis,
                today_local_iso=today_local_iso,
            )

    analysis_dashboard_kpis = _sanitize_dashboard_kpis((analysis_payload or {}).get("analysis", {}).get("dashboard_kpis"))
    if analysis_dashboard_kpis:
        return {
            "kpis": [kpi.model_dump(mode="json") for kpi in analysis_dashboard_kpis],
            "source": "analysis",
            "label": "Baseline analysis",
            "updated_at": analysis_payload["updated_at"] if analysis_payload is not None else None,
            "target_date": None,
        }

    return {
        "kpis": [],
        "source": "none",
        "label": None,
        "updated_at": None,
        "target_date": None,
    }


def _build_analysis_coach_surface(
    analysis_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, datetime | None]:
    if not isinstance(analysis_payload, dict):
        return None, None

    analysis = analysis_payload.get("analysis")
    if not isinstance(analysis, dict):
        return None, None

    updated_at = _parse_updated_at(analysis_payload.get("updated_at"))
    surface = _build_coach_surface_payload(
        source="analysis",
        scope="training_block",
        primary_label="Block Focus",
        primary_text=_normalize_text(analysis.get("coach_action")),
        secondary_text=_normalize_text(analysis.get("headline_brief")),
        updated_at=updated_at,
    )
    return surface, updated_at


def _build_daily_coach_surface(
    *,
    daily_run: DailyUpdateRun | None,
    today_focus_blocks: list[UiHtmlBlock],
) -> tuple[dict[str, Any] | None, datetime | None]:
    if daily_run is None:
        return None, None

    normalized_status = _normalize_text(daily_run.status).lower()
    if normalized_status not in {"done", "completed"}:
        return None, None

    if not today_focus_blocks:
        return None, None

    preview = _extract_html_text(today_focus_blocks[0].content_html)
    primary_text, secondary_text = _split_preview_text(preview)
    updated_at = daily_run.updated_at if isinstance(daily_run.updated_at, datetime) else None
    surface = _build_coach_surface_payload(
        source="daily_sync",
        scope="today",
        primary_label="Today's Action",
        primary_text=primary_text,
        secondary_text=secondary_text,
        updated_at=updated_at,
    )
    return surface, updated_at


def _build_weekly_recap_coach_surface(
    recap_run: WeeklyRecapRun | None,
) -> tuple[dict[str, Any] | None, datetime | None]:
    if recap_run is None:
        return None, None

    summary_preview = extract_recap_summary_preview(recap_run.recap_payload)
    action_preview = extract_recap_action_preview(recap_run.recap_payload, exclude=summary_preview)
    updated_at = recap_run.updated_at if isinstance(recap_run.updated_at, datetime) else None
    surface = _build_coach_surface_payload(
        source="weekly_recap",
        scope="this_week",
        primary_label="This Week's Priority",
        primary_text=summary_preview,
        secondary_text=action_preview,
        updated_at=updated_at,
    )
    return surface, updated_at


def _select_coach_surface(
    *,
    daily_surface: dict[str, Any] | None,
    daily_updated_at: datetime | None,
    recap_surface: dict[str, Any] | None,
    recap_updated_at: datetime | None,
    analysis_surface: dict[str, Any] | None,
) -> dict[str, Any]:
    if daily_surface is not None and recap_surface is not None:
        if recap_updated_at is not None and daily_updated_at is not None:
            if recap_updated_at > daily_updated_at:
                return recap_surface
            return daily_surface
        if daily_updated_at is not None:
            return daily_surface
        if recap_updated_at is not None:
            return recap_surface
        return daily_surface

    if daily_surface is not None:
        return daily_surface
    if recap_surface is not None:
        return recap_surface
    if analysis_surface is not None:
        return analysis_surface
    return _empty_coach_surface()


async def build_dashboard_state(db: AsyncSession, *, user_id) -> dict[str, Any]:
    athlete_time = await get_athlete_time_context(db, user_id=user_id)
    today_local_date = athlete_time.today_local_date
    today_local_iso = today_local_date.isoformat()

    analysis_payload = await get_active_analysis(db, user_id=user_id)
    season_payload = await get_active_season_plan(db, user_id=user_id)
    weekly_payload = await get_active_weekly_plan(db, user_id=user_id)
    profile_row = await db.execute(select(AthleteProfile.profile).where(AthleteProfile.user_id == user_id))
    competitions_row = await db.execute(select(Competition.id).where(Competition.user_id == user_id))
    daily_run_row = await db.execute(
        select(DailyUpdateRun).where(
            DailyUpdateRun.user_id == user_id,
            DailyUpdateRun.target_date == today_local_date,
        )
    )
    completed_daily_runs_row = await db.execute(
        select(DailyUpdateRun)
        .where(
            DailyUpdateRun.user_id == user_id,
            DailyUpdateRun.status.in_(("done", "completed")),
        )
        .order_by(desc(DailyUpdateRun.target_date), desc(DailyUpdateRun.updated_at))
    )
    recap_availability = await evaluate_weekly_recap_availability(db, user_id=user_id)
    usage_context = await get_local_usage_context(db, user_id=user_id)
    recap_feature_enabled = has_weekly_recap_feature_access(usage_context)
    pending_proposal_row = await db.execute(
        select(CoachProposal)
        .join(CoachThread, CoachProposal.thread_id == CoachThread.id)
        .where(
            CoachProposal.user_id == user_id,
            CoachProposal.status == "pending",
            CoachProposal.thread_id.is_not(None),
            CoachThread.status == "active",
        )
        .order_by(CoachProposal.updated_at.desc())
        .limit(1)
    )

    profile_payload = profile_row.scalar_one_or_none()
    has_competitions = bool(competitions_row.scalars().first())
    warnings = _dashboard_warnings(profile=profile_payload, has_competitions=has_competitions)
    integrations_status, provider_notice = await _load_dashboard_integrations_context(
        db,
        user_id=user_id,
    )
    if provider_notice and provider_notice not in warnings:
        warnings.append(provider_notice)

    weekly_plan_model = UiWeeklyPlan.model_validate(weekly_payload["weekly_plan"]) if weekly_payload else None

    daily_run = daily_run_row.scalar_one_or_none()
    completed_daily_runs = completed_daily_runs_row.scalars().all()
    await fail_stale_pending_daily_update_run(db, run=daily_run, now=athlete_time.now_local)
    daily_payload = daily_run.update_payload if daily_run and isinstance(daily_run.update_payload, dict) else {}
    status_surface = _build_status_surface(
        analysis_payload=analysis_payload,
        today_daily_run=daily_run,
        completed_daily_runs=completed_daily_runs,
        daily_payload=daily_payload,
        today_local_iso=today_local_iso,
    )
    analysis_coach_surface, _ = _build_analysis_coach_surface(analysis_payload)
    today_focus_blocks = _sanitize_focus_blocks(daily_payload.get("today_focus_blocks"))
    daily_coach_surface, daily_surface_updated_at = _build_daily_coach_surface(
        daily_run=daily_run,
        today_focus_blocks=today_focus_blocks,
    )
    day_override = compose_day_override(
        weekly_plan=weekly_plan_model,
        target_date_iso=today_local_iso,
        today_focus_blocks=today_focus_blocks,
    )

    daily_thread_id = await _get_daily_thread_id(db, run=daily_run)
    daily_status, daily_visible, daily_error = _resolve_daily_sync_status(
        daily_run=daily_run,
        weekly_plan_available=weekly_plan_model is not None,
    )
    daily_gate = resolve_connected_coaching_gate(
        feature_enabled=True,
        integrations_status=integrations_status,
        locked_message="Daily coaching requires a connected training or recovery source.",
    )
    has_connected_source = str(daily_gate.evidence_profile.get("connected_mode") or "none") != "none"
    has_active_plan = season_payload is not None or weekly_payload is not None
    first_run_state = _build_first_run_state(
        profile=profile_payload,
        has_competitions=has_competitions,
        has_active_plan=has_active_plan,
        has_connected_source=has_connected_source,
    )
    daily_attention_message = _resolve_daily_sync_attention(provider_notice=daily_gate.attention_message)
    daily_can_run = weekly_plan_model is not None and daily_gate.allowed

    verdict_preview = _extract_html_text(today_focus_blocks[0].content_html) if today_focus_blocks else None
    prefetched_recovery_readiness = (
        daily_run.context_snapshot.get("prefetched_recovery_readiness")
        if daily_run is not None and isinstance(daily_run.context_snapshot, dict)
        else None
    )
    sources_used = extract_daily_sync_sources(prefetched_recovery_readiness)

    recap_gate = resolve_connected_coaching_gate(
        feature_enabled=True,
        integrations_status=integrations_status,
        locked_message="Weekly recap requires a connected training or recovery source.",
    )
    recap_attention_message = recap_gate.attention_message
    recap_gate_target = recap_gate.gate_target
    recap_state = {
        "visible": False,
        "allowed": recap_availability.allowed and recap_feature_enabled,
        "status": "hidden",
        "thread_id": None,
        "proposal_id": None,
        "follow_up_question": None,
        "summary_preview": None,
        "pending_action": "none",
        "can_run": False,
        "attention_message": recap_attention_message,
        "gate_target": recap_gate_target,
    }
    recap_coach_surface: dict[str, Any] | None = None
    recap_surface_updated_at: datetime | None = None

    if recap_availability.allowed and recap_feature_enabled:
        recap_state.update(
            {
                "visible": True,
                "allowed": True,
                "status": "ready",
                "can_run": recap_gate.allowed,
                "attention_message": recap_attention_message,
                "gate_target": recap_gate_target,
            }
        )
    elif recap_availability.existing_run_id is not None:
        recap_run_row = await db.execute(
            select(WeeklyRecapRun).where(
                WeeklyRecapRun.id == recap_availability.existing_run_id,
                WeeklyRecapRun.user_id == user_id,
            )
        )
        recap_run = recap_run_row.scalar_one_or_none()
        if recap_run is not None:
            recap_thread_id = await get_recap_thread_id(db, run=recap_run)
            pending_action = await get_recap_pending_action(db, run=recap_run)
            recap_coach_surface, recap_surface_updated_at = _build_weekly_recap_coach_surface(recap_run)
            recap_state.update(
                {
                    "visible": True,
                    "allowed": False,
                    "status": "completed_this_window",
                    "thread_id": recap_thread_id,
                    "proposal_id": str(recap_run.proposal_id) if recap_run.proposal_id else None,
                    "follow_up_question": recap_run.follow_up_question,
                    "summary_preview": extract_recap_summary_preview(recap_run.recap_payload),
                    "pending_action": pending_action,
                    "can_run": False,
                    "attention_message": recap_attention_message,
                    "gate_target": recap_gate_target,
                }
            )

    pending_proposal = pending_proposal_row.scalar_one_or_none()
    coach_surface = _select_coach_surface(
        daily_surface=daily_coach_surface,
        daily_updated_at=daily_surface_updated_at,
        recap_surface=recap_coach_surface,
        recap_updated_at=recap_surface_updated_at,
        analysis_surface=analysis_coach_surface,
    )

    return {
        "athlete_time": {
            "timezone": athlete_time.timezone,
            "timezone_source": athlete_time.timezone_source,
            "today_local_date": today_local_iso,
            "now_local_iso": athlete_time.now_local_iso,
        },
        "analysis": analysis_payload,
        "status_surface": status_surface,
        "coach_surface": coach_surface,
        "season": season_payload,
        "weekly": weekly_payload,
        "first_run": first_run_state,
        "today_mission": {
            "warnings": warnings,
            "day_override": day_override.model_dump(mode="json") if day_override is not None else None,
        },
        "daily_sync": {
            "visible": daily_visible,
            "status": daily_status,
            "run_id": str(daily_run.id) if daily_run is not None else None,
            "verdict_preview": verdict_preview,
            "sources_used": sources_used,
            "proposal_id": str(daily_run.proposal_id) if daily_run and daily_run.proposal_id else None,
            "thread_id": daily_thread_id,
            "error_message": daily_error,
            "can_run": daily_can_run,
            "attention_message": daily_attention_message,
            "gate_target": daily_gate.gate_target,
        },
        "weekly_recap": recap_state,
        "pending_proposal_banner": (
            {
                "proposal_id": str(pending_proposal.id),
                "thread_id": str(pending_proposal.thread_id),
                "origin": pending_proposal.origin,
                "assistant_message": pending_proposal.assistant_message,
            }
            if pending_proposal is not None and pending_proposal.thread_id is not None
            else None
        ),
    }
