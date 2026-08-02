from __future__ import annotations

import uuid
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.deps import DB_SKIP_AUTO_COMMIT_FLAG
from api.models.active_analysis import ActiveAnalysis
from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.ai_run_cost import AiRunCost
from api.models.athlete_profile import AthleteProfile
from api.models.coach_conversation import CoachConversation
from api.models.coach_event import CoachEvent
from api.models.coach_interaction_quota import CoachInteractionQuota
from api.models.coach_message import CoachMessage
from api.models.coach_proposal import CoachProposal
from api.models.coach_thread import CoachThread
from api.models.coach_turn_request import CoachTurnRequest
from api.models.coach_turn_run import CoachTurnRun
from api.models.competition import Competition
from api.models.credentials import StravaCredentials, WhoopCredentials
from api.models.daily_update_run import DailyUpdateRun
from api.models.integration_connection import IntegrationConnection
from api.models.job import AnalysisJob
from api.models.local_usage import LocalUsageCounter, LocalUsageEvent, LocalUsagePlanOverride
from api.models.oauth_session import OAuthSession
from api.models.user import User
from api.models.weekly_recap_run import WeeklyRecapRun
from services.ai.head_coach.checkpointing import delete_owner_checkpoints


def _local_reset_success_payload() -> dict[str, str]:
    return {
        "status": "reset",
        "redirect_path": "/delete?status=reset",
    }


def _local_data_delete_allowed() -> bool:
    return bool(get_settings().allow_local_data_delete)


def _local_data_delete_disabled_payload() -> dict[str, object]:
    return {
        "code": "local_data_delete_disabled",
        "message": (
            "Local data reset is disabled by default to protect training data. "
            "Set ALLOW_LOCAL_DATA_DELETE=true only after exporting or backing up your local DB."
        ),
    }


async def _load_user_for_deletion(db: AsyncSession, *, user_id: uuid.UUID) -> SimpleNamespace:
    row = await db.execute(select(User.id).where(User.id == user_id))
    user = row.one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return SimpleNamespace(id=user.id)


async def _delete_local_account_records(db: AsyncSession, *, user_id: uuid.UUID, delete_user: bool = True):
    await delete_owner_checkpoints(db, owner_id=user_id)
    await db.execute(
        delete(CoachMessage).where(
            CoachMessage.conversation_id.in_(select(CoachConversation.id).where(CoachConversation.user_id == user_id))
        )
    )
    await db.execute(delete(AiRunCost).where(AiRunCost.user_id == user_id))
    await db.execute(delete(CoachTurnRun).where(CoachTurnRun.user_id == user_id))
    await db.execute(delete(DailyUpdateRun).where(DailyUpdateRun.user_id == user_id))
    await db.execute(delete(WeeklyRecapRun).where(WeeklyRecapRun.user_id == user_id))
    await db.execute(
        delete(CoachEvent).where(CoachEvent.thread_id.in_(select(CoachThread.id).where(CoachThread.user_id == user_id)))
    )

    await db.execute(delete(CoachTurnRequest).where(CoachTurnRequest.user_id == user_id))
    await db.execute(delete(CoachProposal).where(CoachProposal.user_id == user_id))
    await db.execute(delete(CoachThread).where(CoachThread.user_id == user_id))
    await db.execute(delete(CoachConversation).where(CoachConversation.user_id == user_id))
    await db.execute(delete(CoachInteractionQuota).where(CoachInteractionQuota.user_id == user_id))

    await db.execute(delete(ActiveAnalysis).where(ActiveAnalysis.user_id == user_id))
    await db.execute(delete(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == user_id))
    await db.execute(delete(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id))

    await db.execute(delete(AnalysisJob).where(AnalysisJob.user_id == user_id))

    await db.execute(delete(Competition).where(Competition.user_id == user_id))
    await db.execute(delete(AthleteProfile).where(AthleteProfile.user_id == user_id))
    await db.execute(delete(IntegrationConnection).where(IntegrationConnection.user_id == user_id))

    await db.execute(delete(StravaCredentials).where(StravaCredentials.user_id == user_id))
    await db.execute(delete(WhoopCredentials).where(WhoopCredentials.user_id == user_id))
    await db.execute(delete(OAuthSession).where(OAuthSession.user_id == user_id))

    await db.execute(delete(LocalUsageEvent).where(LocalUsageEvent.user_id == user_id))
    await db.execute(delete(LocalUsageCounter).where(LocalUsageCounter.user_id == user_id))
    await db.execute(delete(LocalUsagePlanOverride).where(LocalUsagePlanOverride.user_id == user_id))

    if delete_user:
        await db.execute(delete(User).where(User.id == user_id))


async def delete_account_and_data(db: AsyncSession, *, user_id: uuid.UUID) -> dict[str, str]:
    if not _local_data_delete_allowed():
        raise HTTPException(status_code=403, detail=_local_data_delete_disabled_payload())

    await _load_user_for_deletion(db, user_id=user_id)
    db.info[DB_SKIP_AUTO_COMMIT_FLAG] = True
    await _delete_local_account_records(db, user_id=user_id, delete_user=False)
    await db.commit()

    return _local_reset_success_payload()
