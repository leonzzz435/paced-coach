import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, cast

import openai
from billiard.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]
from langgraph.types import Command
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import Session

from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.ai_run_cost import AiRunCost
from api.models.coach_event import CoachEvent
from api.models.coach_thread import CoachThread
from api.models.coach_turn_request import CoachTurnRequest
from api.models.job import AnalysisJob, JobStatus
from api.models.local_usage import LocalUsageEvent
from api.models.user import User
from api.services.ai_run_costs import (
    AiRunCostSnapshot,
    build_ai_run_cost_record,
)
from api.services.analysis_attempts import with_attempt_started_at
from api.services.analysis_resume import terminal_resume_receipt
from api.services.coach_memory import maybe_update_thread_memory
from api.services.local_usage.usage import FEATURE_FULL_RUN, FEATURE_INITIAL_DRAFT_PLAN, INITIAL_DRAFT_PLAN_SOURCE_TYPE
from api.services.status_messages import (
    complete_active_analysis_progress_steps,
    initial_head_coach_progress_steps,
    mark_analysis_progress_step_started,
    normalize_analysis_progress_steps,
)
from core.task_timeouts import get_analysis_task_soft_time_limit_seconds
from services.ai.head_coach.artifacts import ExecutionPlanArtifactV3, SeasonStrategyArtifactV3
from services.ai.head_coach.checkpointing import derive_advisory_lock_key, get_process_checkpointer_provider
from services.ai.head_coach.initial_planning import (
    build_initial_planning_context,
    build_model_planner,
    run_initial_planning,
)
from services.ai.head_coach.middleware import LifecyclePhase
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)

_ANALYSIS_AUTORETRY_EXCEPTIONS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
)

# Postgres JSONB rejects null bytes and certain control characters that LLMs occasionally emit.
_CONTROL_CHAR_RE = __import__("re").compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
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


def _artifact_commit_already_completed(
    *,
    current_job: AnalysisJob,
    season_row: ActiveSeasonPlan | None,
    weekly_row: ActiveWeeklyPlan | None,
    job_uuid: uuid.UUID,
) -> bool:
    if current_job.cancel_requested_at is not None:
        raise _HeadCoachRunStopped("Head Coach result cannot be committed for an inactive job")
    if current_job.status == JobStatus.COMPLETED.value:
        if (
            season_row is not None
            and weekly_row is not None
            and season_row.source_job_id == job_uuid
            and weekly_row.source_job_id == job_uuid
        ):
            return True
        raise RuntimeError("Completed Head Coach job has no matching active-plan commit receipt")
    if current_job.status != JobStatus.RUNNING.value:
        raise _HeadCoachRunStopped("Head Coach result cannot be committed for an inactive job")
    return False


def _upsert_active_plan_rows(
    *,
    async_db: Any,
    user_id: uuid.UUID,
    job_uuid: uuid.UUID,
    season_row: ActiveSeasonPlan | None,
    weekly_row: ActiveWeeklyPlan | None,
    season_data: dict[str, Any],
    weekly_data: dict[str, Any],
    season_version: int,
    weekly_version: int,
) -> None:
    if season_row is None:
        async_db.add(
            ActiveSeasonPlan(
                user_id=user_id,
                version=season_version,
                plan_data=season_data,
                source_job_id=job_uuid,
            )
        )
    else:
        season_row.version = season_version
        season_row.plan_data = season_data
        season_row.source_job_id = job_uuid

    if weekly_row is None:
        async_db.add(
            ActiveWeeklyPlan(
                user_id=user_id,
                version=weekly_version,
                plan_data=weekly_data,
                source_job_id=job_uuid,
            )
        )
    else:
        weekly_row.version = weekly_version
        weekly_row.plan_data = weekly_data
        weekly_row.source_job_id = job_uuid


def _format_analysis_task_error_message(exc: Exception) -> str:
    if isinstance(exc, SoftTimeLimitExceeded):
        soft_limit_seconds = get_analysis_task_soft_time_limit_seconds()
        if soft_limit_seconds is not None:
            return f"Job timed out (soft time limit exceeded after {soft_limit_seconds}s)"
        return "Job timed out (worker soft time limit exceeded)"
    message = str(exc) or "Analysis task failed"
    normalized_message = message.lower()
    if "insufficient_quota" in normalized_message or "exceeded your current quota" in normalized_message:
        return "OpenAI API quota exhausted. Add billing credit to the configured OpenAI account, then retry."
    return message


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


def _release_initial_draft_claim(db: Session, *, user_id: uuid.UUID):
    event = _get_initial_draft_claim_event(db, user_id=user_id)
    if event is None:
        return
    metadata = event.payload_metadata if isinstance(event.payload_metadata, dict) else {}
    state = str(metadata.get("state") or "").strip().lower()
    if state != "pending":
        return
    db.delete(event)


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


def _job_progress_steps(job: object) -> list[dict[str, Any]] | None:
    return cast("list[dict[str, Any]] | None", getattr(job, "progress_steps", None))


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
    job.config = with_attempt_started_at(
        {**job.config, "_celery_task_id": celery_task_id},
        started_at=datetime.now(UTC),
    )
    job.progress_steps = normalize_analysis_progress_steps(
        _job_progress_steps(job) or initial_head_coach_progress_steps()
    )
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
    if job.status in {JobStatus.COMPLETED.value, JobStatus.FAILED.value}:
        logger.info("Job %s already reached terminal status %s", job_id, job.status)
        return False
    if job.status == JobStatus.AWAITING_INPUT.value and not isinstance(
        (job.config or {}).get("_head_coach_resume"),
        dict,
    ):
        logger.info("Job %s remains paused awaiting athlete input", job_id)
        return False
    if job.status == JobStatus.RUNNING.value:
        active_task_id = str((job.config or {}).get("_celery_task_id") or "")
        if not active_task_id or active_task_id != celery_task_id:
            logger.info("Job %s is already owned by Celery task %s", job_id, active_task_id or "unknown")
            return False
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


class _HeadCoachRunStopped(RuntimeError):
    pass


_HEAD_COACH_PHASE_NODES: dict[LifecyclePhase, str] = {
    LifecyclePhase.UNDERSTANDING_CONTEXT: "head_coach_understanding_context",
    LifecyclePhase.DESIGNING_STRATEGY: "head_coach_designing_strategy",
    LifecyclePhase.REVIEWING_CONSTRAINTS: "head_coach_reviewing_constraints",
    LifecyclePhase.AWAITING_INPUT: "head_coach_awaiting_input",
    LifecyclePhase.BUILDING_EXECUTION_BLOCK: "head_coach_building_execution_block",
    LifecyclePhase.SAVING_PLAN: "head_coach_saving_plan",
}


def _load_head_coach_prior_plan(
    db: Session,
    *,
    model: type[ActiveSeasonPlan] | type[ActiveWeeklyPlan],
    user_id: uuid.UUID,
    is_initial_draft_run: bool,
) -> dict[str, Any] | None:
    if is_initial_draft_run:
        return None
    row = db.execute(select(model).where(model.user_id == user_id)).scalar_one_or_none()
    plan_data = getattr(row, "plan_data", None)
    return cast("dict[str, Any]", plan_data) if isinstance(plan_data, dict) else None


def _load_head_coach_memory(db: Session, *, user_id: uuid.UUID) -> dict[str, Any]:
    memory_summary = db.execute(select(User.memory_summary).where(User.id == user_id)).scalar_one_or_none()
    return {"memory_summary": memory_summary or ""}


async def _run_head_coach_workflow_for_job(  # noqa: C901 - transaction branches enforce atomic ownership
    *,
    job_uuid: uuid.UUID,
    user_id: uuid.UUID,
    config: dict[str, Any],
    prior_season_plan: dict[str, Any] | None,
    prior_weekly_plan: dict[str, Any] | None,
    coach_memory: dict[str, Any],
    is_initial_draft_run: bool,
) -> dict[str, Any]:
    from api.deps import async_session_maker

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for Head Coach checkpointing")
    provider = get_process_checkpointer_provider(database_url=database_url)

    async def ensure_active() -> None:
        async with async_session_maker() as async_db:
            row = await async_db.execute(
                select(AnalysisJob.status, AnalysisJob.cancel_requested_at).where(AnalysisJob.id == job_uuid)
            )
            current = row.one_or_none()
            if current is None or current.status != JobStatus.RUNNING.value or current.cancel_requested_at is not None:
                raise _HeadCoachRunStopped("Head Coach run is no longer active")

    async def report_status(phase: LifecyclePhase) -> None:
        async with async_session_maker() as async_db:
            row = await async_db.execute(select(AnalysisJob).where(AnalysisJob.id == job_uuid).with_for_update())
            current_job = row.scalar_one_or_none()
            if current_job is None or current_job.status not in {
                JobStatus.RUNNING.value,
                JobStatus.COMPLETED.value,
            }:
                return
            now = datetime.now(UTC)
            steps = complete_active_analysis_progress_steps(current_job.progress_steps, timestamp=now)
            node_name = _HEAD_COACH_PHASE_NODES.get(phase)
            if node_name is not None:
                steps, _ = mark_analysis_progress_step_started(steps, node_name=node_name, timestamp=now)
            current_job.progress_steps = steps
            async_db.add(current_job)
            await async_db.commit()

    async def commit_artifacts(
        season: SeasonStrategyArtifactV3,
        execution: ExecutionPlanArtifactV3,
    ) -> None:
        async with async_session_maker() as async_db:
            async with async_db.begin():
                await async_db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": derive_advisory_lock_key(f"owner:{user_id}:active-plan")},
                )
                job_row = await async_db.execute(
                    select(AnalysisJob).where(AnalysisJob.id == job_uuid).with_for_update()
                )
                current_job = job_row.scalar_one_or_none()
                if current_job is None:
                    raise _HeadCoachRunStopped("Head Coach result cannot be committed for an inactive job")

                season_row = (
                    await async_db.execute(
                        select(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == user_id).with_for_update()
                    )
                ).scalar_one_or_none()
                weekly_row = (
                    await async_db.execute(
                        select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id).with_for_update()
                    )
                ).scalar_one_or_none()
                if _artifact_commit_already_completed(
                    current_job=current_job,
                    season_row=season_row,
                    weekly_row=weekly_row,
                    job_uuid=job_uuid,
                ):
                    return
                season_version = (season_row.version + 1) if season_row is not None else 1
                weekly_version = (weekly_row.version + 1) if weekly_row is not None else 1
                season_data = _as_json_dict(_sanitize_for_db(season.model_dump(mode="json")))
                weekly_data = _as_json_dict(_sanitize_for_db(execution.model_dump(mode="json")))
                season_data["version"] = season_version
                weekly_data["version"] = weekly_version

                _upsert_active_plan_rows(
                    async_db=async_db,
                    user_id=user_id,
                    job_uuid=job_uuid,
                    season_row=season_row,
                    weekly_row=weekly_row,
                    season_data=season_data,
                    weekly_data=weekly_data,
                    season_version=season_version,
                    weekly_version=weekly_version,
                )

                thread = (
                    await async_db.execute(
                        select(CoachThread)
                        .where(CoachThread.user_id == user_id, CoachThread.status == "active")
                        .order_by(CoachThread.updated_at.desc(), CoachThread.created_at.desc())
                        .limit(1)
                        .with_for_update()
                    )
                ).scalar_one_or_none()
                if thread is None:
                    thread = CoachThread(user_id=user_id, latest_seq=0, status="active", title="Head Coach")
                    async_db.add(thread)
                    await async_db.flush()
                thread.latest_seq += 1
                thread.last_full_run_job_id = job_uuid
                thread.last_full_run_at = datetime.now(UTC)
                async_db.add(
                    CoachEvent(
                        thread_id=thread.id,
                        seq=thread.latest_seq,
                        event_type="plan_decision_recorded",
                        actor="coach",
                        payload={
                            "source_job_id": str(job_uuid),
                            "season_plan_id": season.plan_id,
                            "execution_plan_id": execution.plan_id,
                            "season_decision": season.decision_ledger_entry.model_dump(mode="json"),
                            "execution_decision": execution.decision_ledger_entry.model_dump(mode="json"),
                        },
                    )
                )

                existing_usage = (
                    await async_db.execute(
                        select(LocalUsageEvent).where(
                            LocalUsageEvent.feature_key == FEATURE_FULL_RUN,
                            LocalUsageEvent.source_type == "analysis_job",
                            LocalUsageEvent.source_id == str(job_uuid),
                        )
                    )
                ).scalar_one_or_none()
                if existing_usage is None:
                    async_db.add(
                        LocalUsageEvent(
                            user_id=user_id,
                            feature_key=FEATURE_FULL_RUN,
                            source_type="analysis_job",
                            source_id=str(job_uuid),
                            consumed_at=datetime.now(UTC),
                        )
                    )
                if is_initial_draft_run:
                    claim = (
                        await async_db.execute(
                            select(LocalUsageEvent)
                            .where(
                                LocalUsageEvent.user_id == user_id,
                                LocalUsageEvent.feature_key == FEATURE_INITIAL_DRAFT_PLAN,
                                LocalUsageEvent.source_type == INITIAL_DRAFT_PLAN_SOURCE_TYPE,
                            )
                            .with_for_update()
                        )
                    ).scalar_one_or_none()
                    if claim is not None:
                        claim.payload_metadata = {
                            **(claim.payload_metadata or {}),
                            "state": "consumed",
                            "analysis_job_id": str(job_uuid),
                            "finalized_at": datetime.now(UTC).isoformat(),
                        }
                        claim.consumed_at = datetime.now(UTC)

                existing_cost = (
                    await async_db.execute(
                        select(AiRunCost.id).where(
                            AiRunCost.source_type == "analysis_job",
                            AiRunCost.source_id == str(job_uuid),
                        )
                    )
                ).scalar_one_or_none()
                if existing_cost is None:
                    async_db.add(
                        build_ai_run_cost_record(
                            user_id=user_id,
                            thread_id=thread.id,
                            feature="initial_planning",
                            source_type="analysis_job",
                            source_id=job_uuid,
                            run_name="head_coach_initial_planning",
                            trace_metadata=None,
                            cost_snapshot=AiRunCostSnapshot(cost_status="missing"),
                            source_metadata={"workflow_version": "head_coach_v1"},
                        )
                    )

                current_job.status = JobStatus.COMPLETED.value
                current_job.result = {
                    "analysis_blocks": None,
                    "season_plan_blocks": season_data,
                    "weekly_plan_blocks": weekly_data,
                    "decision_ledger": {
                        "season": season.decision_ledger_entry.model_dump(mode="json"),
                        "execution": execution.decision_ledger_entry.model_dump(mode="json"),
                    },
                    "workflow_version": "head_coach_v1",
                }
                current_job.completed_at = datetime.now(UTC)
                completed_config = {
                    key: value
                    for key, value in (current_job.config or {}).items()
                    if key != "_head_coach_interrupt"
                }
                receipt = terminal_resume_receipt(completed_config.get("_head_coach_resume"))
                if receipt is None:
                    completed_config.pop("_head_coach_resume", None)
                else:
                    completed_config["_head_coach_resume"] = receipt
                current_job.config = completed_config
                current_job.progress_steps = complete_active_analysis_progress_steps(
                    current_job.progress_steps,
                    timestamp=datetime.now(UTC),
                )

    plan_start_date = str(config.get("plan_start_date") or datetime.now(UTC).date().isoformat())
    context_pack = build_initial_planning_context(
        now_utc=datetime.now(UTC),
        athlete_name=str(config.get("athlete_name") or "Athlete"),
        athlete_profile=cast("dict[str, Any]", config.get("athlete_profile") or {}),
        competitions=cast("list[dict[str, Any]]", config.get("competitions") or []),
        plan_start_date=plan_start_date,
        run_overrides=cast("dict[str, Any]", config.get("run_overrides") or {}),
        prior_season_plan=prior_season_plan,
        prior_weekly_plan=prior_weekly_plan,
        coach_memory=coach_memory,
    )
    resume_payload = config.get("_head_coach_resume")
    resume: Command | None = Command(resume=resume_payload["answer"]) if isinstance(resume_payload, dict) else None
    return await run_initial_planning(
        provider=provider,
        owner_id=user_id,
        job_id=job_uuid,
        context_pack=context_pack,
        planner=build_model_planner(),
        commit=commit_artifacts,
        resume=resume,
        ensure_active=ensure_active,
        status=report_status,
    )


def _persist_head_coach_interrupt(db: Session, *, job_uuid: uuid.UUID, result: dict[str, Any]) -> bool:
    interrupts = result.get("__interrupt__")
    if not isinstance(interrupts, tuple | list) or not interrupts:
        return False
    value = getattr(interrupts[0], "value", None)
    if not isinstance(value, dict):
        raise RuntimeError("Head Coach returned an invalid clarification interrupt")
    current_job = db.execute(select(AnalysisJob).where(AnalysisJob.id == job_uuid).with_for_update()).scalar_one()
    if current_job.status != JobStatus.RUNNING.value:
        raise _HeadCoachRunStopped("Head Coach clarification belongs to an inactive job")
    current_job.status = JobStatus.AWAITING_INPUT.value
    current_job.config = {
        **(current_job.config or {}),
        "_head_coach_interrupt": _as_json_dict(_sanitize_for_db(value)),
    }
    db.commit()
    return True


def _handle_analysis_task_exception(
    self,
    db: Session,
    *,
    job: AnalysisJob,
    job_id: str,
    exc: Exception,
    is_initial_draft_run: bool,
) -> None:
    db.rollback()
    db.expire_all()
    committed_status = db.execute(select(AnalysisJob.status).where(AnalysisJob.id == job.id)).scalar_one_or_none()
    if committed_status == JobStatus.COMPLETED.value:
        logger.warning(
            "Ignoring post-commit Head Coach failure for job %s; the domain commit is authoritative",
            job_id,
        )
        return
    if _should_defer_failure_to_autoretry(self, exc):
        logger.warning(
            "Analysis task hit retriable error for job %s; leaving claim pending until retry exhaustion",
            job_id,
            exc_info=True,
        )
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
        job = db.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_uuid).with_for_update()
        ).scalar_one_or_none()

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
            config = dict(job.config or {})
            prior_season_plan = _load_head_coach_prior_plan(
                db,
                model=ActiveSeasonPlan,
                user_id=job.user_id,
                is_initial_draft_run=is_initial_draft_run,
            )
            prior_weekly_plan = _load_head_coach_prior_plan(
                db,
                model=ActiveWeeklyPlan,
                user_id=job.user_id,
                is_initial_draft_run=is_initial_draft_run,
            )
            coach_memory = _load_head_coach_memory(db, user_id=job.user_id)
            result = _run_async_in_worker_loop(
                _run_head_coach_workflow_for_job(
                    job_uuid=job_uuid,
                    user_id=job.user_id,
                    config=config,
                    prior_season_plan=prior_season_plan,
                    prior_weekly_plan=prior_weekly_plan,
                    coach_memory=coach_memory,
                    is_initial_draft_run=is_initial_draft_run,
                )
            )
            db.expire_all()
            if _persist_head_coach_interrupt(db, job_uuid=job_uuid, result=result):
                logger.info("Head Coach job %s is awaiting athlete input", job_id)
                return
            logger.info("Head Coach job completed for job %s", job_id)
            return

        except _HeadCoachRunStopped:
            db.rollback()
            logger.info("Head Coach job %s stopped without committing output", job_id)
            return

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


@celery_app.task(name="worker.tasks.recover_pending_analysis_dispatches_task")
def recover_pending_analysis_dispatches_task():
    """Re-enqueue durable dispatch intents stranded before broker delivery."""
    cutoff = datetime.now(UTC) - timedelta(seconds=30)
    with get_sync_session() as db:
        job_ids = list(
            db.execute(
                select(AnalysisJob.id)
                .where(
                    AnalysisJob.status == JobStatus.PENDING.value,
                    AnalysisJob.created_at <= cutoff,
                    AnalysisJob.config["_workflow_version"].astext == "head_coach_v1",
                )
                .order_by(AnalysisJob.created_at.asc())
                .with_for_update(skip_locked=True)
            ).scalars()
        )
        db.commit()

    recovered = 0
    for job_id in job_ids:
        try:
            run_analysis_task.delay(str(job_id))
            recovered += 1
        except Exception:
            logger.exception("Failed to recover pending analysis dispatch for job %s", job_id)
    logger.info("Recovered %s pending analysis dispatch(es)", recovered)
    return recovered


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


async def _run_head_coach_checkpoint_cleanup_async():
    from api.config import get_settings
    from api.deps import async_session_maker
    from api.services.head_coach_checkpoint_retention import cleanup_expired_head_coach_checkpoints

    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.head_coach_checkpoint_retention_days)
    async with async_session_maker() as db:
        summary = await cleanup_expired_head_coach_checkpoints(db, cutoff=cutoff)
        await db.commit()
    return summary


@celery_app.task(name="worker.tasks.run_head_coach_checkpoint_cleanup_task")
def run_head_coach_checkpoint_cleanup_task():
    summary = _run_async_in_worker_loop(_run_head_coach_checkpoint_cleanup_async())
    logger.info("Head Coach checkpoint cleanup completed summary=%s", summary)
