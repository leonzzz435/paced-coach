import logging
import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.models.athlete_profile import AthleteProfile
from api.models.competition import Competition
from api.models.job import AnalysisJob, JobStatus
from api.services.local_readiness import format_llm_provider_key_names, has_llm_provider_key
from api.services.local_usage import ensure_plan_generation_available, release_initial_draft_plan_claim
from api.services.status_messages import (
    complete_active_analysis_progress_steps,
    current_analysis_step,
    initial_analysis_progress_steps,
    normalize_analysis_progress_steps,
)
from core.task_timeouts import (
    get_analysis_running_job_max_age_seconds,
    get_analysis_task_time_limit_seconds,
)

logger = logging.getLogger(__name__)
router = APIRouter()

def _is_free_initial_job(job: AnalysisJob) -> bool:
    config = getattr(job, "config", None)
    if not isinstance(config, dict):
        return False
    return str(config.get("_plan_generation_access_mode") or "").strip().lower() == "free_initial"


class RunOverrides(BaseModel):
    analysis_notes: str | None = None
    planning_notes: str | None = None
    temporary_constraints: str | None = None

    @field_validator("analysis_notes", "planning_notes", "temporary_constraints", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        trimmed = value.strip()
        return trimmed or None


class AnalysisConfig(BaseModel):
    athlete_name: str = "Athlete"
    activities_days: int = 30
    metrics_days: int = 60
    plan_start_date: date_type | None = None
    run_overrides: RunOverrides = Field(default_factory=RunOverrides)
    enable_plotting: bool = False

    @field_validator("athlete_name", mode="before")
    @classmethod
    def normalize_athlete_name(cls, value: str | None) -> str:
        if value is None:
            return "Athlete"
        trimmed = value.strip()
        return trimmed or "Athlete"


class ProgressStepResponse(BaseModel):
    node: str
    label: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    actual_started_at: str | None = None
    actual_completed_at: str | None = None
    duration_seconds: float | None = None


class AnalysisJobResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    cost_usd: float | None = None
    tokens_used: int | None = None
    progress_steps: list[ProgressStepResponse] | None = None
    current_step: str | None = None


class AnalysisResultResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error_message: str | None = None


@router.post("/run", status_code=202)
async def run_analysis(
    config: AnalysisConfig,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> AnalysisJobResponse:
    if not has_llm_provider_key():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Plan generation requires one local LLM key. Add {format_llm_provider_key_names()} "
                "to .env, restart the API, then retry."
            ),
        )

    plan_generation_access = await ensure_plan_generation_available(db, user_id=user_id)
    try:
        # Create job
        job = AnalysisJob(
            user_id=user_id,
            config=config.model_dump(mode="json"),
            progress_steps=initial_analysis_progress_steps(),
        )
        db.add(job)
        await db.flush()

        # Build immutable job input snapshot (persisted profile + competitions). Avoid in-place JSONB mutation
        # because SQLAlchemy won't reliably mark JSONB dict edits as dirty.
        job_config = {
            **job.config,
            "_plan_generation_access_mode": plan_generation_access.mode,
        }

        profile_result = await db.execute(select(AthleteProfile).where(AthleteProfile.user_id == user_id))
        profile_row = profile_result.scalar_one_or_none()
        job_config = {**job_config, "athlete_profile": (profile_row.profile if profile_row else {})}

        # Load persisted competitions for this user (if any) and store as immutable job input snapshot.
        comps_result = await db.execute(select(Competition).where(Competition.user_id == user_id))
        competitions = comps_result.scalars().all()
        job_config = {
            **job_config,
            "competitions": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "date": c.date.isoformat() if c.date else None,
                    "date_text": c.date_text,
                    "race_type": c.race_type,
                    "priority": c.priority,
                    "target_time": c.target_time,
                    "notes": c.notes,
                }
                for c in competitions
            ],
        }
        job.config = job_config
        db.add(job)
        await db.flush()

        # Persist the job before enqueueing so the worker never races a not-yet-committed row.
        await db.commit()
    except Exception:
        raise

    try:
        from worker.tasks import run_analysis_task

        run_analysis_task.delay(str(job.id))
    except Exception as exc:
        logger.exception("Failed to enqueue analysis job %s", job.id)
        failed_at = datetime.now(UTC)
        job.status = JobStatus.FAILED.value
        job.error_message = "Failed to enqueue analysis job"
        job.completed_at = failed_at
        job.progress_steps = complete_active_analysis_progress_steps(
            getattr(job, "progress_steps", None),
            timestamp=failed_at,
        )
        db.add(job)
        await db.commit()
        raise HTTPException(status_code=503, detail="Unable to start analysis job") from exc

    return AnalysisJobResponse(
        job_id=str(job.id),
        status=job.status,
        created_at=job.created_at,
        progress_steps=[ProgressStepResponse.model_validate(step) for step in (job.progress_steps or [])],
        current_step=current_analysis_step(job.progress_steps),
    )


@router.get("/{job_id}")
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> AnalysisJobResponse:
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id,
            AnalysisJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_progress_steps = getattr(job, "progress_steps", None)

    # Celery hard-kills (SIGKILL) can leave jobs stuck in RUNNING. Only auto-fail them when
    # an analysis task time limit is explicitly configured.
    if job.status == JobStatus.RUNNING.value:
        now = datetime.now(UTC)
        age_seconds = (now - job.created_at).total_seconds()
        stale_threshold_seconds = get_analysis_running_job_max_age_seconds()
        if stale_threshold_seconds is not None and age_seconds > stale_threshold_seconds:
            task_limit_seconds = get_analysis_task_time_limit_seconds()
            job.status = JobStatus.FAILED.value
            if task_limit_seconds is None:
                job.error_message = "Job timed out (exceeded maximum execution time)"
            else:
                job.error_message = f"Job timed out (exceeded maximum execution time of {task_limit_seconds}s)"
            job.completed_at = now
            job.progress_steps = complete_active_analysis_progress_steps(job_progress_steps, timestamp=now)
            job_progress_steps = job.progress_steps
            if _is_free_initial_job(job):
                await release_initial_draft_plan_claim(db, user_id=user_id)
            await db.commit()

    return AnalysisJobResponse(
        job_id=str(job.id),
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        cost_usd=float(job.cost_usd) if job.cost_usd else None,
        tokens_used=job.tokens_used,
        progress_steps=[
            ProgressStepResponse.model_validate(step) for step in normalize_analysis_progress_steps(job_progress_steps)
        ],
        current_step=current_analysis_step(job_progress_steps),
    )


@router.get("/{job_id}/results")
async def get_job_results(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> AnalysisResultResponse:
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id,
            AnalysisJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Job is still pending")

    if job.status == JobStatus.RUNNING.value:
        raise HTTPException(status_code=400, detail="Job is still running")

    if job.status == JobStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Job was cancelled")

    return AnalysisResultResponse(
        job_id=str(job.id),
        status=job.status,
        result=job.result,
        error_message=job.error_message,
    )


@router.post("/{job_id}/cancel", status_code=202)
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
) -> dict[str, str]:
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id,
            AnalysisJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value):
        return {"job_id": str(job.id), "status": job.status}

    celery_task_id = job.config.get("_celery_task_id") if job.config else None
    job.cancel_requested_at = datetime.now()
    job.status = JobStatus.CANCELLED.value
    job.completed_at = datetime.now()
    job.progress_steps = complete_active_analysis_progress_steps(
        getattr(job, "progress_steps", None),
        timestamp=datetime.now(UTC),
    )
    if _is_free_initial_job(job):
        await release_initial_draft_plan_claim(db, user_id=user_id)
    await db.commit()

    if celery_task_id:
        from worker.celery_app import celery_app

        celery_app.control.revoke(celery_task_id, terminate=True, signal="SIGTERM")
        logger.info("Revoked Celery task %s for job %s", celery_task_id, job_id)

    return {"job_id": str(job.id), "status": "cancelled"}
