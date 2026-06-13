from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

ProgressStepStatus = Literal["pending", "active", "completed"]

TOOL_STATUS_MESSAGES: dict[str, str] = {
    "get_training_snapshot": "Checking your current training snapshot...",
    "get_recent_activities": "Reviewing your recent activities...",
    "get_activity_detail": "Checking full details of an activity...",
    "get_training_load_history": "Reviewing your training load history...",
    "get_recovery_readiness_signals": "Checking recovery and readiness signals...",
    "get_expert_analysis_summary": "Reviewing your latest analysis results...",
    "get_expert_output": "Pulling expert insights...",
    "get_current_analysis": "Loading your current dashboard analysis...",
    "get_current_weekly_plan": "Loading your current weekly plan...",
    "get_current_season_plan": "Loading your season plan...",
    "get_upcoming_competitions": "Checking your upcoming races...",
}

NODE_STATUS_MESSAGES: dict[str, str] = {
    "metrics_summarizer": "Summarizing training metrics...",
    "physiology_summarizer": "Summarizing physiology data...",
    "activity_summarizer": "Summarizing recent activities...",
    "training_data_compaction": "Compacting source context...",
    "metrics_expert": "Expert analyzing training metrics...",
    "physiology_expert": "Expert analyzing physiology signals...",
    "activity_expert": "Expert analyzing activity patterns...",
    "master_orchestrator": "Coordinating analysis results...",
    "synthesis": "Synthesizing findings...",
    "plot_resolution": "Preparing visualizations...",
    "analysis_formatter": "Formatting analysis report...",
    "season_planner": "Planning your season...",
    "data_integration": "Integrating data for weekly planning...",
    "weekly_planner": "Building your weekly plan...",
    "season_formatter": "Formatting season plan...",
    "weekly_formatter": "Formatting weekly plan...",
    "finalize": "Finalizing results...",
}

ANALYSIS_PROGRESS_NODE_ORDER: list[str] = [
    "metrics_summarizer",
    "physiology_summarizer",
    "activity_summarizer",
    "training_data_compaction",
    "metrics_expert",
    "physiology_expert",
    "activity_expert",
    "master_orchestrator",
    "synthesis",
    "plot_resolution",
    "analysis_formatter",
    "season_planner",
    "data_integration",
    "weekly_planner",
    "season_formatter",
    "weekly_formatter",
    "finalize",
]


def _try_parse_iso_date(raw_value: object) -> datetime | None:
    if not isinstance(raw_value, str):
        return None
    cleaned = raw_value.strip()
    if not cleaned:
        return None
    normalized = cleaned.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _render_date_range_label(args: dict[str, Any] | None) -> str | None:
    if not args:
        return None
    date_from = _try_parse_iso_date(args.get("date_from"))
    date_to = _try_parse_iso_date(args.get("date_to"))
    if date_from and date_to:
        return f"{date_from.strftime('%b %d')} to {date_to.strftime('%b %d')}"
    if date_from:
        return f"since {date_from.strftime('%b %d')}"
    if date_to:
        return f"through {date_to.strftime('%b %d')}"
    return None


def tool_status_message(tool_name: str, args: dict[str, Any] | None = None) -> str:
    if tool_name == "get_recent_activities":
        date_range_label = _render_date_range_label(args)
        if date_range_label:
            return f"Reviewing your activities from {date_range_label}..."
    return TOOL_STATUS_MESSAGES.get(tool_name, "Reviewing your training context...")


def node_status_message(node_name: str) -> str:
    return NODE_STATUS_MESSAGES.get(node_name, "Working through analysis steps...")


def normalize_analysis_progress_steps(progress_steps: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    by_node: dict[str, dict[str, Any]] = {}
    extra_steps: list[dict[str, Any]] = []
    known_nodes = set(ANALYSIS_PROGRESS_NODE_ORDER)

    for raw_step in progress_steps or []:
        node_name = str(raw_step.get("node", "")).strip()
        if not node_name:
            continue
        status_raw = str(raw_step.get("status", "pending")).strip().lower()
        status_value: ProgressStepStatus = (
            cast("ProgressStepStatus", status_raw) if status_raw in {"pending", "active", "completed"} else "pending"
        )
        step: dict[str, Any] = {
            "node": node_name,
            "label": str(raw_step.get("label") or node_status_message(node_name)),
            "status": status_value,
        }
        for key in ("started_at", "completed_at"):
            timestamp_value = raw_step.get(key)
            if isinstance(timestamp_value, str) and timestamp_value.strip():
                step[key] = timestamp_value
        for key in ("actual_started_at", "actual_completed_at"):
            timestamp_value = raw_step.get(key)
            if isinstance(timestamp_value, str) and timestamp_value.strip():
                step[key] = timestamp_value
        duration_value = raw_step.get("duration_seconds")
        if isinstance(duration_value, int | float):
            step["duration_seconds"] = float(duration_value)

        if node_name in known_nodes:
            by_node[node_name] = step
        else:
            extra_steps.append(step)

    ordered_steps = [
        by_node.get(
            node_name,
            {
                "node": node_name,
                "label": node_status_message(node_name),
                "status": "pending",
            },
        )
        for node_name in ANALYSIS_PROGRESS_NODE_ORDER
    ]
    return ordered_steps + extra_steps


def initial_analysis_progress_steps() -> list[dict[str, Any]]:
    return normalize_analysis_progress_steps(None)


def mark_analysis_progress_step_started(
    progress_steps: list[dict[str, Any]] | None,
    *,
    node_name: str,
    timestamp: datetime | None = None,
) -> tuple[list[dict[str, Any]], str]:
    current_steps = normalize_analysis_progress_steps(progress_steps)
    now_iso = (timestamp or datetime.now(UTC)).astimezone(UTC).isoformat()

    target_step: dict[str, Any] | None = None
    for step in current_steps:
        if step["node"] == node_name:
            target_step = step

    if target_step is None:
        target_step = {
            "node": node_name,
            "label": node_status_message(node_name),
            "status": "pending",
        }
        current_steps.append(target_step)

    if target_step["status"] == "pending" and "started_at" not in target_step:
        target_step["started_at"] = now_iso
    target_step["status"] = "active"
    target_step.pop("completed_at", None)
    return current_steps, str(target_step["label"])


def mark_analysis_progress_step_completed(
    progress_steps: list[dict[str, Any]] | None,
    *,
    node_name: str,
    timestamp: datetime | None = None,
) -> list[dict[str, Any]]:
    current_steps = normalize_analysis_progress_steps(progress_steps)
    now_iso = (timestamp or datetime.now(UTC)).astimezone(UTC).isoformat()

    target_step: dict[str, Any] | None = None
    for step in current_steps:
        if step["node"] == node_name:
            target_step = step
            break

    if target_step is None:
        target_step = {
            "node": node_name,
            "label": node_status_message(node_name),
            "status": "pending",
        }
        current_steps.append(target_step)

    if "started_at" not in target_step:
        target_step["started_at"] = now_iso
    target_step["status"] = "completed"
    target_step["completed_at"] = now_iso
    return current_steps


def complete_active_analysis_progress_steps(
    progress_steps: list[dict[str, Any]] | None,
    *,
    timestamp: datetime | None = None,
) -> list[dict[str, Any]]:
    current_steps = normalize_analysis_progress_steps(progress_steps)
    now_iso = (timestamp or datetime.now(UTC)).astimezone(UTC).isoformat()
    for step in current_steps:
        if step["status"] == "active":
            step["status"] = "completed"
            step["completed_at"] = now_iso
    return current_steps


def record_analysis_step_timing(
    progress_steps: list[dict[str, Any]] | None,
    *,
    node_name: str,
    duration_seconds: float,
    timestamp: datetime | None = None,
) -> list[dict[str, Any]]:
    current_steps = normalize_analysis_progress_steps(progress_steps)
    completed_at = (timestamp or datetime.now(UTC)).astimezone(UTC)
    safe_duration_seconds = max(float(duration_seconds), 0.0)
    started_at = completed_at - timedelta(seconds=safe_duration_seconds)

    target_step: dict[str, Any] | None = None
    for step in current_steps:
        if step["node"] == node_name:
            target_step = step
            break

    if target_step is None:
        target_step = {
            "node": node_name,
            "label": node_status_message(node_name),
            "status": "pending",
        }
        current_steps.append(target_step)

    target_step["actual_started_at"] = started_at.isoformat()
    target_step["actual_completed_at"] = completed_at.isoformat()
    target_step["duration_seconds"] = round(safe_duration_seconds, 3)
    return current_steps


def current_analysis_step(progress_steps: list[dict[str, Any]] | None) -> str | None:
    active_labels = [
        str(step["label"])
        for step in normalize_analysis_progress_steps(progress_steps)
        if step["status"] == "active"
    ]
    if not active_labels:
        return None
    if len(active_labels) == 1:
        return active_labels[0]
    return f"{active_labels[0]} (+{len(active_labels) - 1} more)"
