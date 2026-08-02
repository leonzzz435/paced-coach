from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.coach_turn_run import CoachTurnRun
from api.models.job import AnalysisJob, JobStatus
from services.ai.head_coach.checkpointing import (
    CheckpointScope,
    build_checkpoint_identity,
    delete_checkpoint_thread,
)


class CheckpointCleanupSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    analysis_threads_deleted: int = 0
    coach_executions_deleted: int = 0
    checkpoint_rows_deleted: int = 0


async def cleanup_expired_head_coach_checkpoints(
    db: AsyncSession,
    *,
    cutoff: datetime,
) -> CheckpointCleanupSummary:
    analysis_result = await db.execute(
        select(AnalysisJob.user_id, AnalysisJob.id).where(
            AnalysisJob.status.in_(
                [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]
            ),
            AnalysisJob.completed_at.is_not(None),
            AnalysisJob.completed_at < cutoff,
        )
    )
    coach_result = await db.execute(
        select(CoachTurnRun.user_id, CoachTurnRun.thread_id, CoachTurnRun.id).where(
            CoachTurnRun.status.in_(["completed", "failed", "cancelled"]),
            CoachTurnRun.created_at < cutoff,
        )
    )

    analysis_rows = analysis_result.all()
    coach_rows = coach_result.all()
    deleted_rows = 0
    for owner_id, analysis_id in analysis_rows:
        identity = build_checkpoint_identity(
            owner_id=owner_id,
            scope=CheckpointScope.INITIAL_PLANNING,
            resource_id=analysis_id,
        )
        deleted_rows += await delete_checkpoint_thread(db, thread_id=identity.thread_id)

    for owner_id, thread_id, run_id in coach_rows:
        identity = build_checkpoint_identity(
            owner_id=owner_id,
            scope=CheckpointScope.COACH_TURN,
            resource_id=thread_id,
            execution_id=run_id,
        )
        deleted_rows += await delete_checkpoint_thread(db, thread_id=identity.thread_id)

    return CheckpointCleanupSummary(
        analysis_threads_deleted=len(analysis_rows),
        coach_executions_deleted=len(coach_rows),
        checkpoint_rows_deleted=deleted_rows,
    )
