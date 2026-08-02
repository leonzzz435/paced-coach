import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.active_analysis import ActiveAnalysis
from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from services.ai.head_coach.artifacts import ExecutionPlanArtifactV3


async def get_active_analysis(db: AsyncSession, *, user_id: uuid.UUID) -> dict | None:
    row = await db.execute(select(ActiveAnalysis).where(ActiveAnalysis.user_id == user_id))
    active = row.scalar_one_or_none()
    if not active:
        return None
    analysis_payload = dict(active.analysis_data or {})
    analysis_payload["version"] = active.version
    return {
        "version": active.version,
        "analysis": analysis_payload,
        "expert_context": active.expert_context,
        "source_job_id": str(active.source_job_id),
        "updated_at": active.updated_at.isoformat(),
    }


async def get_active_season_plan(db: AsyncSession, *, user_id: uuid.UUID) -> dict | None:
    row = await db.execute(select(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == user_id))
    active = row.scalar_one_or_none()
    if not active:
        return None
    season_payload = dict(active.plan_data or {})
    season_payload["version"] = active.version
    return {
        "version": active.version,
        "season_plan": season_payload,
        "source_job_id": str(active.source_job_id),
        "updated_at": active.updated_at.isoformat(),
    }


async def get_active_weekly_plan(db: AsyncSession, *, user_id: uuid.UUID) -> dict | None:
    row = await db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id))
    active = row.scalar_one_or_none()
    if not active:
        return None
    weekly_payload = dict(active.plan_data or {})
    weekly_payload["version"] = active.version
    return {
        "version": active.version,
        "weekly_plan": weekly_payload,
        "source_job_id": str(active.source_job_id),
        "updated_at": active.updated_at.isoformat(),
    }


async def get_active_plans_bundle(db: AsyncSession, *, user_id: uuid.UUID) -> dict | None:
    analysis = await get_active_analysis(db, user_id=user_id)
    season = await get_active_season_plan(db, user_id=user_id)
    weekly = await get_active_weekly_plan(db, user_id=user_id)
    if not analysis and not season and not weekly:
        return None
    return {
        "analysis": analysis,
        "season": season,
        "weekly": weekly,
    }


async def toggle_day_completion(db: AsyncSession, *, user_id: uuid.UUID, day_id: str, is_completed: bool) -> dict:
    row = await db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id).with_for_update())
    active = row.scalar_one_or_none()
    if not active or not active.plan_data:
        raise ValueError("No active weekly plan found")

    plan_data = set_day_completion(dict(active.plan_data), day_id=day_id, is_completed=is_completed)

    active.plan_data = plan_data
    # SQLAlchemy requires flagging JSONB mutations manually
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(active, "plan_data")

    await db.commit()
    await db.refresh(active)

    result_payload = dict(active.plan_data)
    result_payload["version"] = active.version
    return {
        "version": active.version,
        "weekly_plan": result_payload,
        "source_job_id": str(active.source_job_id),
        "updated_at": active.updated_at.isoformat(),
    }


def set_day_completion(plan_data: dict, *, day_id: str, is_completed: bool) -> dict:
    schema_version = plan_data.get("schema_version", 1)
    if schema_version not in {1, 3}:
        raise ValueError(f"Unsupported weekly-plan schema version: {schema_version}")
    if schema_version == 3:
        validated = ExecutionPlanArtifactV3.model_validate(plan_data)
        plan_data = validated.model_dump(mode="json")

    for week in plan_data.get("weeks", []):
        for day in week.get("days", []):
            if day.get("day_id") != day_id:
                continue
            day["is_completed"] = is_completed
            if schema_version == 3:
                return ExecutionPlanArtifactV3.model_validate(plan_data).model_dump(mode="json")
            return plan_data
    raise ValueError(f"Day ID {day_id} not found in active weekly plan")
