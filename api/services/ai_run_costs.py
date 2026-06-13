from __future__ import annotations

import logging
import os
import uuid
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any, cast

from langsmith.run_helpers import tracing_context
from langsmith.run_trees import RunTree

from api.models.ai_run_cost import AiRunCost
from services.ai.langgraph.utils.langsmith_cost_extractor import LangSmithCostExtractor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AiTraceMetadata:
    project_name: str | None
    trace_id: str | None
    root_run_id: str | None
    run_name: str


@dataclass
class AiRunCostSnapshot:
    cost_status: str
    total_cost_usd: float | None = None
    total_tokens: int | None = None
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_web_searches: int | None = None
    model_breakdown: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass
class AiRootTrace:
    run_name: str
    tags: list[str]
    metadata: dict[str, Any]
    root_run: RunTree | None = None

    def context_manager(self):
        if self.root_run is None:
            return nullcontext()
        return tracing_context(
            parent=self.root_run,
            project_name=self.root_run.session_name,
            tags=self.tags,
            metadata=self.metadata,
        )

    def trace_metadata(self) -> AiTraceMetadata | None:
        if self.root_run is None:
            return None
        return AiTraceMetadata(
            project_name=self.root_run.session_name,
            trace_id=str(self.root_run.trace_id),
            root_run_id=str(self.root_run.id),
            run_name=self.run_name,
        )


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    try:
        return float(cast("Any", value))
    except (TypeError, ValueError):
        return None


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    try:
        return int(cast("Any", value))
    except (TypeError, ValueError):
        return None


def _langsmith_project_name() -> str | None:
    if not os.getenv("LANGSMITH_API_KEY"):
        return None
    return os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT")


def start_ai_root_trace(
    *,
    run_name: str,
    feature: str,
    user_id: str | None,
    inputs: dict[str, Any],
    thread_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    root_run_id: str | None = None,
) -> AiRootTrace:
    trace_tags = [f"feature:{feature}"]
    if tags:
        trace_tags.extend(tags)
    if user_id:
        trace_tags.append(f"user:{user_id}")
    if thread_id:
        trace_tags.append(f"thread:{thread_id}")

    trace_metadata = {"feature": feature}
    if metadata:
        trace_metadata.update(metadata)
    if user_id:
        trace_metadata["user_id"] = user_id
    if thread_id:
        trace_metadata["thread_id"] = thread_id

    project_name = _langsmith_project_name()
    if project_name is None:
        return AiRootTrace(run_name=run_name, tags=trace_tags, metadata=trace_metadata)

    root_uuid = uuid.UUID(root_run_id) if root_run_id is not None else uuid.uuid4()
    try:
        root_run = RunTree(
            id=root_uuid,
            name=run_name,
            run_type="chain",
            project_name=project_name,
            inputs=inputs,
            tags=trace_tags,
            extra={"metadata": trace_metadata},
        )
        root_run.post()
        return AiRootTrace(run_name=run_name, tags=trace_tags, metadata=trace_metadata, root_run=root_run)
    except Exception:
        logger.exception("Failed to create LangSmith root trace for %s", run_name)
        return AiRootTrace(run_name=run_name, tags=trace_tags, metadata=trace_metadata)


def finish_ai_root_trace(
    trace: AiRootTrace,
    *,
    outputs: dict[str, Any] | None = None,
    extra_metadata: dict[str, Any] | None = None,
    error: Exception | None = None,
):
    if trace.root_run is None:
        return

    final_metadata = trace.metadata.copy()
    if extra_metadata:
        final_metadata.update(extra_metadata)

    try:
        trace.root_run.end(
            outputs=outputs,
            error=f"{type(error).__name__}: {error}" if error is not None else None,
            metadata=final_metadata,
        )
        trace.root_run.patch()
    except Exception:
        logger.exception("Failed to finalize LangSmith root trace for %s", trace.run_name)


def trace_metadata_from_values(
    *,
    project_name: str | None,
    trace_id: str | None,
    root_run_id: str | None,
    run_name: str,
) -> AiTraceMetadata | None:
    if trace_id is None and root_run_id is None and project_name is None:
        return None
    return AiTraceMetadata(
        project_name=project_name,
        trace_id=trace_id,
        root_run_id=root_run_id,
        run_name=run_name,
    )


def trace_metadata_from_execution_metadata(
    execution_metadata: dict[str, Any] | None,
    *,
    default_run_name: str,
    project_name: str | None = None,
) -> AiTraceMetadata | None:
    if not isinstance(execution_metadata, dict):
        return None
    return trace_metadata_from_values(
        project_name=project_name,
        trace_id=str(execution_metadata.get("trace_id")) if execution_metadata.get("trace_id") else None,
        root_run_id=(
            str(execution_metadata.get("root_run_id")) if execution_metadata.get("root_run_id") else None
        ),
        run_name=str(execution_metadata.get("run_name") or default_run_name),
    )


def capture_langsmith_run_costs(trace_metadata: AiTraceMetadata | None) -> AiRunCostSnapshot:
    if trace_metadata is None or not trace_metadata.root_run_id:
        return AiRunCostSnapshot(cost_status="missing")

    extractor = LangSmithCostExtractor()
    if extractor.client is None:
        return AiRunCostSnapshot(cost_status="missing")

    payload = extractor.extract_run_costs(trace_metadata.root_run_id)
    if payload.get("trace_id") is None:
        return AiRunCostSnapshot(cost_status="missing")

    model_breakdown = (
        cast("dict[str, Any]", payload["model_breakdown"])
        if isinstance(payload.get("model_breakdown"), dict)
        else {}
    )

    return AiRunCostSnapshot(
        cost_status="captured",
        total_cost_usd=_coerce_float(payload.get("total_cost_usd")),
        total_tokens=_coerce_int(payload.get("total_tokens")),
        total_input_tokens=_coerce_int(payload.get("total_input_tokens")),
        total_output_tokens=_coerce_int(payload.get("total_output_tokens")),
        total_web_searches=_coerce_int(payload.get("total_web_searches")),
        model_breakdown=model_breakdown,
    )


def snapshot_from_legacy_cost_summary(cost_summary: dict[str, Any] | None) -> AiRunCostSnapshot:
    if not isinstance(cost_summary, dict):
        return AiRunCostSnapshot(cost_status="missing")

    model_breakdown = cost_summary.get("model_breakdown")
    normalized_breakdown = model_breakdown if isinstance(model_breakdown, dict) else {}

    total_cost_usd = _coerce_float(cost_summary.get("total_cost_usd"))
    total_tokens = _coerce_int(cost_summary.get("total_tokens"))
    total_input_tokens = sum(
        _coerce_int(model_data.get("input_tokens")) or 0
        for model_data in normalized_breakdown.values()
        if isinstance(model_data, dict)
    )
    total_output_tokens = sum(
        _coerce_int(model_data.get("output_tokens")) or 0
        for model_data in normalized_breakdown.values()
        if isinstance(model_data, dict)
    )
    total_web_searches = sum(
        _coerce_int(model_data.get("web_search_requests")) or 0
        for model_data in normalized_breakdown.values()
        if isinstance(model_data, dict)
    )

    if total_cost_usd in (None, 0.0) and total_tokens in (None, 0) and not normalized_breakdown:
        return AiRunCostSnapshot(cost_status="missing")

    return AiRunCostSnapshot(
        cost_status="fallback",
        total_cost_usd=total_cost_usd,
        total_tokens=total_tokens,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_web_searches=total_web_searches,
        model_breakdown=normalized_breakdown,
    )


def build_ai_run_cost_record(
    *,
    user_id: uuid.UUID,
    feature: str,
    source_type: str,
    source_id: str | uuid.UUID | None,
    run_name: str,
    trace_metadata: AiTraceMetadata | None,
    cost_snapshot: AiRunCostSnapshot,
    thread_id: uuid.UUID | None = None,
    source_metadata: dict[str, Any] | None = None,
) -> AiRunCost:
    return AiRunCost(
        user_id=user_id,
        thread_id=thread_id,
        feature=feature,
        source_type=source_type,
        source_id=str(source_id) if source_id is not None else None,
        cost_status=cost_snapshot.cost_status,
        langsmith_project=trace_metadata.project_name if trace_metadata is not None else None,
        langsmith_trace_id=trace_metadata.trace_id if trace_metadata is not None else None,
        langsmith_root_run_id=trace_metadata.root_run_id if trace_metadata is not None else None,
        run_name=run_name,
        total_cost_usd=cost_snapshot.total_cost_usd,
        total_tokens=cost_snapshot.total_tokens,
        total_input_tokens=cost_snapshot.total_input_tokens,
        total_output_tokens=cost_snapshot.total_output_tokens,
        total_web_searches=cost_snapshot.total_web_searches,
        model_breakdown=cost_snapshot.model_breakdown or None,
        source_metadata=source_metadata,
        error_message=cost_snapshot.error_message,
    )
