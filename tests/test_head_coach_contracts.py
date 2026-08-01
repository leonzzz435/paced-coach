from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from api.services.coach_context import package_head_coach_brief
from services.ai.ai_settings import AgentRole
from services.ai.head_coach.prompts import build_head_coach_system_prompt
from services.ai.head_coach.run_profiles import (
    MutationAuthority,
    RunProfileName,
    get_run_profile,
)
from services.ai.head_coach.schemas import (
    EvidenceAuthority,
    EvidenceProvenance,
    EvidenceSourceKind,
    HeadCoachBrief,
)


@pytest.mark.parametrize("profile_name", list(RunProfileName))
def test_every_supported_run_profile_uses_an_explicit_semantic_configuration(profile_name):
    profile = get_run_profile(profile_name)

    assert profile.name is profile_name
    assert profile.model_role in {
        AgentRole.HEAD_COACH,
        AgentRole.MEMORY,
        AgentRole.SPECIALIST,
        AgentRole.UI_COMPOSER,
    }
    assert profile.reasoning_effort in {"low", "medium", "high", "xhigh"}


def test_reasoning_and_authority_follow_task_semantics():
    initial = get_run_profile(RunProfileName.INITIAL_PLANNING)
    replan = get_run_profile(RunProfileName.MATERIAL_REPLANNING)
    coach_turn = get_run_profile(RunProfileName.COACH_TURN)
    recap = get_run_profile(RunProfileName.WEEKLY_RECAP)
    composer = get_run_profile(RunProfileName.UI_COMPOSER)

    assert initial.reasoning_effort == "medium"
    assert initial.mutation_authority is MutationAuthority.INITIAL_COMMIT
    assert replan.reasoning_effort == "xhigh"
    assert replan.mutation_authority is MutationAuthority.PROPOSE
    assert coach_turn.reasoning_effort == "medium"
    assert coach_turn.mutation_authority is MutationAuthority.PROPOSE
    assert recap.reasoning_effort == "high"
    assert recap.mutation_authority is MutationAuthority.PROPOSE
    assert composer.reasoning_effort == "low"
    assert composer.mutation_authority is MutationAuthority.NONE


def test_only_research_specialist_enables_native_web_search():
    enabled_profiles = {
        profile_name for profile_name in RunProfileName if get_run_profile(profile_name).enable_native_web_search
    }

    assert enabled_profiles == {RunProfileName.RESEARCH_SPECIALIST}


def test_unknown_run_profile_fails_before_model_selection():
    with pytest.raises(ValueError, match="Unsupported Head Coach run profile"):
        get_run_profile("magic_mode")


def test_head_coach_brief_preserves_full_local_context_and_serializes():
    context_pack = {
        "now_utc": "2026-07-19T08:30:00+00:00",
        "athlete_model": {"experience": "advanced", "nested": {"keep": [1, 2, 3]}},
        "upcoming_competitions": [{"name": "Synthetic A race", "priority": "A"}],
        "current_weekly_plan_identity": {"plan_id": "plan-1", "version": 4},
        "evidence_profile": {"claims_policy": {"readiness": "unsupported"}},
    }

    brief = package_head_coach_brief(
        owner_id="owner-1",
        run_id="run-1",
        profile_name=RunProfileName.COACH_TURN,
        context_pack=context_pack,
    )

    assert brief.as_of_utc == datetime(2026, 7, 19, 8, 30, tzinfo=UTC)
    assert brief.local_context == context_pack
    assert brief.model_dump(mode="json")["local_context"] == context_pack
    assert "database" not in brief.model_dump_json()


def test_head_coach_brief_rejects_an_untyped_profile_name():
    with pytest.raises(ValidationError, match="profile_name"):
        HeadCoachBrief.model_validate(
            {
                "owner_id": "owner-1",
                "run_id": "run-1",
                "profile_name": "magic_mode",
                "as_of_utc": datetime(2026, 7, 19, 8, 30, tzinfo=UTC),
                "local_context": {},
            }
        )


def test_consultative_evidence_cannot_claim_athlete_declared_authority():
    with pytest.raises(ValidationError, match="athlete-declared"):
        EvidenceProvenance(
            source_kind=EvidenceSourceKind.SPECIALIST,
            authority=EvidenceAuthority.ATHLETE_DECLARED,
            source_id="specialist:training-research",
        )


def test_prompt_keeps_one_identity_and_scopes_task_instructions():
    planning_prompt = build_head_coach_system_prompt(get_run_profile(RunProfileName.INITIAL_PLANNING))
    coach_prompt = build_head_coach_system_prompt(get_run_profile(RunProfileName.COACH_TURN))

    assert planning_prompt.startswith("You are the athlete's persistent Head Coach.")
    assert coach_prompt.startswith("You are the athlete's persistent Head Coach.")
    assert "Season Strategy" in planning_prompt
    assert "proposal intent" in coach_prompt
    assert "Do not invent wearable" in planning_prompt
