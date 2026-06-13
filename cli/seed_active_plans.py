import argparse
import json
import os
import types
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.models.active_analysis import ActiveAnalysis
from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.job import AnalysisJob, JobStatus
from api.models.user import User
from services.ai.langgraph.schemas.expert_outputs import (
    ActivityExpertOutputs,
    MetricsExpertOutputs,
    PhysiologyExpertOutputs,
)
from services.ai.langgraph.schemas.ui_blocks import UiAnalysis, UiSeasonPlan, UiWeeklyPlan


def _database_url() -> str:
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return database_url.replace("+asyncpg", "")


def _dump_pydantic_or_dict(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    if isinstance(value, types.SimpleNamespace):
        return value.__dict__
    return value


def _jsonable(value):
    return json.loads(json.dumps(value, default=str))


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _upsert_active_plans(
    db: Session,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    analysis: UiAnalysis,
    season: UiSeasonPlan,
    weekly: UiWeeklyPlan,
    expert_context: dict,
) -> None:
    active_weekly = db.execute(select(ActiveWeeklyPlan).where(ActiveWeeklyPlan.user_id == user_id)).scalar_one_or_none()
    if active_weekly:
        active_weekly.plan_data = _jsonable(weekly.model_dump(mode="json"))
        active_weekly.version += 1
        active_weekly.source_job_id = job_id
    else:
        db.add(
            ActiveWeeklyPlan(
                user_id=user_id,
                version=1,
                plan_data=_jsonable(weekly.model_dump(mode="json")),
                source_job_id=job_id,
            )
        )

    active_season = db.execute(select(ActiveSeasonPlan).where(ActiveSeasonPlan.user_id == user_id)).scalar_one_or_none()
    if active_season:
        active_season.plan_data = _jsonable(season.model_dump(mode="json"))
        active_season.version += 1
        active_season.source_job_id = job_id
    else:
        db.add(
            ActiveSeasonPlan(
                user_id=user_id,
                version=1,
                plan_data=_jsonable(season.model_dump(mode="json")),
                source_job_id=job_id,
            )
        )

    active_analysis = db.execute(select(ActiveAnalysis).where(ActiveAnalysis.user_id == user_id)).scalar_one_or_none()
    if active_analysis:
        active_analysis.analysis_data = _jsonable(analysis.model_dump(mode="json"))
        active_analysis.expert_context = expert_context
        active_analysis.version += 1
        active_analysis.source_job_id = job_id
    else:
        db.add(
            ActiveAnalysis(
                user_id=user_id,
                version=1,
                analysis_data=_jsonable(analysis.model_dump(mode="json")),
                expert_context=expert_context,
                source_job_id=job_id,
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed active plans for a local owner from exported analysis artifacts (dev-only)."
    )
    parser.add_argument(
        "--owner-external-id",
        dest="owner_external_id",
        required=True,
        help="Stable local owner identifier.",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing analysis_blocks.json, weekly_plan_blocks.json, season_plan_blocks.json, and *_expert.json",
    )
    parser.add_argument("--athlete-name", default="Athlete")
    parser.add_argument(
        "--allow-missing-markdown",
        action="store_true",
        help="Do not fail if season_plan.md / weekly_plan.md are missing.",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    weekly_path = os.path.join(data_dir, "weekly_plan_blocks.json")
    season_path = os.path.join(data_dir, "season_plan_blocks.json")
    analysis_path = os.path.join(data_dir, "analysis_blocks.json")
    metrics_expert_path = os.path.join(data_dir, "metrics_expert.json")
    activity_expert_path = os.path.join(data_dir, "activity_expert.json")
    physiology_expert_path = os.path.join(data_dir, "physiology_expert.json")
    season_plan_md_path = os.path.join(data_dir, "season_plan.md")
    weekly_plan_md_path = os.path.join(data_dir, "weekly_plan.md")

    required_paths = [weekly_path, season_path, analysis_path]
    for path in required_paths:
        if not os.path.exists(path):
            raise RuntimeError(f"File not found: {path}")

    engine = create_engine(_database_url())
    with Session(engine) as db:
        user = db.execute(select(User).where(User.local_owner_key == args.owner_external_id)).scalar_one_or_none()
        if not user:
            user = User(local_owner_key=args.owner_external_id, email=f"{args.owner_external_id}@local.paced")
            db.add(user)
            db.flush()

        seed_result: dict = {
            "weekly_plan_blocks": _load_json(weekly_path),
            "season_plan_blocks": _load_json(season_path),
            "season_plan": _load_text(season_plan_md_path) if os.path.exists(season_plan_md_path) else None,
            "weekly_plan": _load_text(weekly_plan_md_path) if os.path.exists(weekly_plan_md_path) else None,
            "execution_id": "seed",
        }
        if not args.allow_missing_markdown and not seed_result.get("season_plan"):
            raise RuntimeError(
                f"File not found: {season_plan_md_path} (required for coach chat)."
            )

        job = AnalysisJob(
            user_id=user.id,
            status=JobStatus.COMPLETED.value,
            config={},
            result=_jsonable(seed_result),
        )
        db.add(job)
        db.flush()

        weekly = UiWeeklyPlan.model_validate(_load_json(weekly_path))
        season = UiSeasonPlan.model_validate(_load_json(season_path))
        analysis = UiAnalysis.model_validate(_load_json(analysis_path))

        # Allow overriding athlete_name for nicer UI display.
        if args.athlete_name:
            weekly.athlete_name = args.athlete_name
            season.athlete_name = args.athlete_name
            analysis.athlete_name = args.athlete_name

        metrics_outputs = (
            MetricsExpertOutputs.model_validate(_load_json(metrics_expert_path))
            if os.path.exists(metrics_expert_path)
            else None
        )
        activity_outputs = (
            ActivityExpertOutputs.model_validate(_load_json(activity_expert_path))
            if os.path.exists(activity_expert_path)
            else None
        )
        physiology_outputs = (
            PhysiologyExpertOutputs.model_validate(_load_json(physiology_expert_path))
            if os.path.exists(physiology_expert_path)
            else None
        )

        expert_context = {
            "metrics_outputs": _dump_pydantic_or_dict(metrics_outputs),
            "activity_outputs": _dump_pydantic_or_dict(activity_outputs),
            "physiology_outputs": _dump_pydantic_or_dict(physiology_outputs),
        }

        _upsert_active_plans(
            db,
            user_id=user.id,
            job_id=job.id,
            analysis=analysis,
            season=season,
            weekly=weekly,
            expert_context=expert_context,
        )

        db.commit()

        print(f"Seeded active plans for owner_external_id={args.owner_external_id} user_id={user.id} source_job_id={job.id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
