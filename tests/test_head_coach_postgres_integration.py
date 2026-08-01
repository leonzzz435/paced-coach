import asyncio
import os
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException
from langgraph.types import Command, interrupt
from psycopg import AsyncConnection
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.ai_run_cost import AiRunCost
from api.models.coach_event import CoachEvent
from api.models.coach_thread import CoachThread
from api.models.job import AnalysisJob, JobStatus
from api.models.local_usage import LocalUsageEvent
from api.models.user import User
from api.services.local_usage import ensure_plan_generation_available
from api.services.plan_generation_lock import lock_owner_plan_generation
from services.ai.head_coach.checkpointing import (
    CheckpointScope,
    HeadCoachCheckpointerProvider,
    RunAlreadyClaimedError,
    build_checkpoint_config,
    build_checkpoint_identity,
)
from services.ai.head_coach.graph import HeadCoachGraphNodes, HeadCoachGraphState, build_head_coach_graph
from tests.test_head_coach_initial_planning import _artifacts


async def _passthrough(_state: HeadCoachGraphState) -> dict[str, Any]:
    return {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_checkpoint_resumes_after_pool_and_graph_recreation():
    database_url = os.getenv("HEAD_COACH_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("HEAD_COACH_TEST_DATABASE_URL is not configured")

    owner_id = uuid4()
    run_id = uuid4()
    calls: list[str] = []
    identity = build_checkpoint_identity(
        owner_id=owner_id,
        scope=CheckpointScope.INITIAL_PLANNING,
        resource_id=run_id,
    )
    config = build_checkpoint_config(identity)

    async def load_context(_state: HeadCoachGraphState) -> dict[str, Any]:
        calls.append("load")
        return {"context_loaded": True}

    async def review_strategy(_state: HeadCoachGraphState) -> dict[str, Any]:
        calls.append("strategy_review")
        answer = interrupt({"kind": "clarification", "question": "Which days are available?"})
        return {"clarification_answer": answer}

    async def review_result(_state: HeadCoachGraphState) -> dict[str, Any]:
        calls.append("review")
        return {"reviewed": True}

    async def commit_result(_state: HeadCoachGraphState) -> dict[str, Any]:
        calls.append("commit")
        return {"committed": True}

    nodes = HeadCoachGraphNodes(
        load_context=load_context,
        design_strategy=_passthrough,
        review_strategy=review_strategy,
        build_execution=_passthrough,
        review_result=review_result,
        commit_result=commit_result,
    )
    first_provider = HeadCoachCheckpointerProvider(database_url=database_url)
    second_provider = HeadCoachCheckpointerProvider(database_url=database_url)
    try:
        first_graph = build_head_coach_graph(nodes=nodes, checkpointer=await first_provider.get())
        paused = await first_graph.ainvoke(
            {"owner_id": str(owner_id), "run_id": str(run_id)},
            config=config,
        )
        assert paused["__interrupt__"][0].value["kind"] == "clarification"
        await first_provider.close()

        recreated_graph = build_head_coach_graph(nodes=nodes, checkpointer=await second_provider.get())
        resumed = await recreated_graph.ainvoke(Command(resume="Monday, Wednesday, Saturday"), config=config)

        assert resumed["committed"] is True
        assert calls == ["load", "strategy_review", "strategy_review", "review", "commit"]
    finally:
        await first_provider.close()
        await second_provider.close()
        async with await AsyncConnection.connect(database_url, autocommit=True) as connection:
            for table_name in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                await connection.execute(
                    f"DELETE FROM {table_name} WHERE thread_id = %s",
                    (identity.thread_id,),
                )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_claim_blocks_overlapping_workers_and_releases_on_exit():
    database_url = os.getenv("HEAD_COACH_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("HEAD_COACH_TEST_DATABASE_URL is not configured")

    run_identity = f"integration:{uuid4()}"
    first_provider = HeadCoachCheckpointerProvider(database_url=database_url)
    second_provider = HeadCoachCheckpointerProvider(database_url=database_url)
    try:
        async with first_provider.claim(run_identity):
            with pytest.raises(RunAlreadyClaimedError):
                async with second_provider.claim(run_identity):
                    pass

        async with second_provider.claim(run_identity):
            pass
    finally:
        await first_provider.close()
        await second_provider.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_plan_generation_start_lock_serializes_owner_admission():
    database_url = os.getenv("HEAD_COACH_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("HEAD_COACH_TEST_DATABASE_URL is not configured")
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    owner_id = uuid4()
    owner_key = f"head-coach-admission-{owner_id}"
    second_start_entered = asyncio.Event()

    async def attempt_second_start() -> None:
        async with sessions() as second_db:
            second_start_entered.set()
            await lock_owner_plan_generation(second_db, user_id=owner_id)
            await ensure_plan_generation_available(second_db, user_id=owner_id)

    try:
        async with sessions() as setup_db:
            setup_db.add(User(id=owner_id, local_owner_key=owner_key, email=f"{owner_key}@paced.local"))
            await setup_db.commit()

        async with sessions() as first_db:
            await lock_owner_plan_generation(first_db, user_id=owner_id)
            first_db.add(
                AnalysisJob(
                    user_id=owner_id,
                    status=JobStatus.PENDING.value,
                    config={"_workflow_version": "head_coach_v1"},
                )
            )
            await first_db.flush()

            second_start = asyncio.create_task(attempt_second_start())
            await second_start_entered.wait()
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(second_start), timeout=0.05)
            await first_db.commit()

        with pytest.raises(HTTPException) as exc:
            await second_start
        assert exc.value.status_code == 409
    finally:
        async with sessions() as cleanup_db:
            await cleanup_db.execute(delete(AnalysisJob).where(AnalysisJob.user_id == owner_id))
            await cleanup_db.execute(delete(User).where(User.id == owner_id))
            await cleanup_db.commit()
        await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_head_coach_commit_is_atomic_and_idempotent(monkeypatch):
    database_url = os.getenv("HEAD_COACH_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("HEAD_COACH_TEST_DATABASE_URL is not configured")
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    owner_id = uuid4()
    job_id = uuid4()
    owner_key = f"head-coach-test-{owner_id}"
    season, execution = _artifacts()

    async def planner(request: dict[str, Any]) -> dict[str, Any]:
        if request["planning_stage"] == "strategy":
            return {"kind": "strategy", "season_strategy": season.model_dump(mode="json")}
        return execution.model_dump(mode="json")

    monkeypatch.setattr("worker.tasks.build_model_planner", lambda: planner)
    from worker.tasks import _run_head_coach_workflow_for_job

    identity = build_checkpoint_identity(
        owner_id=owner_id,
        scope=CheckpointScope.INITIAL_PLANNING,
        resource_id=job_id,
    )
    try:
        async with sessions() as db:
            db.add(User(id=owner_id, local_owner_key=owner_key, email=f"{owner_key}@paced.local"))
            await db.flush()
            db.add(
                AnalysisJob(
                    id=job_id,
                    user_id=owner_id,
                    status=JobStatus.RUNNING.value,
                    config={"_workflow_version": "head_coach_v1"},
                )
            )
            await db.commit()

        async def run_once():
            return await _run_head_coach_workflow_for_job(
                job_uuid=job_id,
                user_id=owner_id,
                config={
                    "athlete_name": "Sample Athlete",
                    "athlete_profile": {"availability": ["Monday", "Thursday", "Saturday"]},
                    "competitions": [],
                    "plan_start_date": "2026-08-03",
                },
                prior_season_plan=None,
                prior_weekly_plan=None,
                coach_memory={"memory_summary": "Prefers consistency over hero workouts."},
                is_initial_draft_run=False,
            )

        first = await run_once()
        second = await run_once()

        assert first["committed"] is True
        assert second["committed"] is True
        async with sessions() as db:
            job = await db.get(AnalysisJob, job_id)
            active_season = (
                await db.execute(select(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == owner_id))
            ).scalar_one()
            active_weekly = (
                await db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == owner_id))
            ).scalar_one()
            event_count = (
                await db.execute(
                    select(func.count(CoachEvent.id))
                    .join(CoachThread, CoachThread.id == CoachEvent.thread_id)
                    .where(CoachThread.user_id == owner_id, CoachEvent.event_type == "plan_decision_recorded")
                )
            ).scalar_one()
            assert job is not None and job.status == JobStatus.COMPLETED.value and job.result is not None
            assert job.result["season_plan_blocks"]["schema_version"] == 3
            assert active_season.source_job_id == job_id
            assert active_weekly.source_job_id == job_id
            assert event_count == 1
            assert (
                await db.execute(
                    select(func.count(LocalUsageEvent.id)).where(
                        LocalUsageEvent.user_id == owner_id,
                        LocalUsageEvent.source_id == str(job_id),
                    )
                )
            ).scalar_one() == 1
            assert (
                await db.execute(
                    select(func.count(AiRunCost.id)).where(
                        AiRunCost.user_id == owner_id,
                        AiRunCost.source_id == str(job_id),
                    )
                )
            ).scalar_one() == 1
    finally:
        async with sessions() as db:
            await db.execute(
                delete(CoachEvent).where(
                    CoachEvent.thread_id.in_(select(CoachThread.id).where(CoachThread.user_id == owner_id))
                )
            )
            await db.execute(delete(AiRunCost).where(AiRunCost.user_id == owner_id))
            await db.execute(delete(LocalUsageEvent).where(LocalUsageEvent.user_id == owner_id))
            await db.execute(delete(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == owner_id))
            await db.execute(delete(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == owner_id))
            await db.execute(delete(CoachThread).where(CoachThread.user_id == owner_id))
            for table_name in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                await db.execute(
                    text(f"DELETE FROM {table_name} WHERE thread_id = :thread_id"),
                    {"thread_id": identity.thread_id},
                )
            await db.execute(delete(AnalysisJob).where(AnalysisJob.id == job_id))
            await db.execute(delete(User).where(User.id == owner_id))
            await db.commit()
        await engine.dispose()
