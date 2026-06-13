import inspect

from services.ai.coach.continuum_turn_agent import _TURN_SYSTEM_PROMPT
from services.ai.coach.plan_modifier_agent import SYSTEM_PROMPT as PLAN_MODIFIER_SYSTEM_PROMPT
from services.ai.daily.daily_update_agent import DAILY_SYSTEM_PROMPT
from services.ai.langgraph.nodes.activity_expert_node import ACTIVITY_EXPERT_USER_PROMPT
from services.ai.langgraph.nodes.metrics_expert_node import METRICS_SYSTEM_PROMPT_BASE, METRICS_USER_PROMPT
from services.ai.langgraph.nodes.physiology_expert_node import PHYSIOLOGY_SYSTEM_PROMPT_BASE, PHYSIOLOGY_USER_PROMPT
from services.ai.langgraph.nodes.plan_formatter_node import WEEKLY_FORMATTER_SYSTEM_PROMPT
from services.ai.langgraph.nodes.season_formatter_node import season_formatter_node
from services.ai.langgraph.nodes.season_planner_node import (
    SEASON_PLANNER_SYSTEM_PROMPT,
    SEASON_PLANNER_UPDATE_ONLY_PROMPT,
    SEASON_PLANNER_USER_PROMPT,
)
from services.ai.langgraph.nodes.weekly_formatter_node import WEEKLY_FORMATTER_USER_PROMPT_TEMPLATE
from services.ai.langgraph.nodes.weekly_planner_node import (
    WEEKLY_PLANNER_FINAL_CHECKLIST,
    WEEKLY_PLANNER_SYSTEM_PROMPT,
    WEEKLY_PLANNER_USER_PROMPT,
)
from services.ai.recap.weekly_recap_agent import RECAP_SYSTEM_PROMPT


def test_weekly_planner_prompt_requires_segment_zone_targets():
    combined_prompt = f"{WEEKLY_PLANNER_SYSTEM_PROMPT} {WEEKLY_PLANNER_USER_PROMPT} {WEEKLY_PLANNER_FINAL_CHECKLIST}"

    assert "intervals, laps, reps, or changing segments" in combined_prompt
    assert "calendar session" in combined_prompt
    assert "lap/rep/segment" in combined_prompt


def test_planning_prompts_treat_custom_instructions_as_requirements():
    combined_prompt = (
        f"{SEASON_PLANNER_USER_PROMPT} "
        f"{SEASON_PLANNER_UPDATE_ONLY_PROMPT} "
        f"{WEEKLY_PLANNER_USER_PROMPT} "
        f"{WEEKLY_PLANNER_FINAL_CHECKLIST}"
    )

    assert "Planning Context and Custom Instructions" in combined_prompt
    assert "Honor Custom Instructions" in combined_prompt
    assert "challenge requests" in combined_prompt
    assert "visibly reflected or" in combined_prompt
    assert "Do NOT reuse an existing season plan" in combined_prompt


def test_planning_prompts_create_and_execute_creative_micro_challenges():
    season_prompt = f"{SEASON_PLANNER_SYSTEM_PROMPT} {SEASON_PLANNER_USER_PROMPT} {SEASON_PLANNER_UPDATE_ONLY_PROMPT}"
    weekly_prompt = f"{WEEKLY_PLANNER_USER_PROMPT} {WEEKLY_PLANNER_FINAL_CHECKLIST}"

    assert "Creative challenge architecture" in season_prompt
    assert "weekly micro-challenges and larger signature/breakthrough challenges" in season_prompt
    assert "Do not hardcode stock challenges" in season_prompt
    assert "purpose, timing window, progression target, and safety" in season_prompt
    assert "lacks a competition-aware creative challenge thread" in season_prompt
    assert "push my limits" in season_prompt
    assert "psychologically" in season_prompt
    assert "protected by safety caps" in season_prompt
    assert "NOT just a normal race-distance goal" in season_prompt
    assert "weird, memorable constraint system" in season_prompt

    assert "Activate Challenge Architecture" in weekly_prompt
    assert "1-2 micro-challenge moments per week" in weekly_prompt
    assert "success condition, safety cap, and fallback version" in weekly_prompt
    assert "larger signature/breakthrough challenge" in weekly_prompt
    assert "Do not shrink every big challenge into a tiny" in weekly_prompt
    assert "plain distance goals" in weekly_prompt
    assert "non-standard constraint" in weekly_prompt
    assert "season-level micro/signature challenges are translated" in weekly_prompt


def test_weekly_planner_prompt_requires_transition_continuity():
    combined_prompt = f"{WEEKLY_PLANNER_USER_PROMPT} {WEEKLY_PLANNER_FINAL_CHECKLIST}"

    assert "Transition Context" in combined_prompt
    assert "Honor Continuity" in combined_prompt
    assert "first 3-7 days" in combined_prompt
    assert "fresh easy reset" in combined_prompt
    assert "transition rationale" in combined_prompt


def test_planning_prompts_require_generic_volume_floors_for_capable_athletes():
    season_prompt = f"{SEASON_PLANNER_SYSTEM_PROMPT} {SEASON_PLANNER_UPDATE_ONLY_PROMPT}"
    weekly_prompt = f"{WEEKLY_PLANNER_SYSTEM_PROMPT} {WEEKLY_PLANNER_USER_PROMPT} {WEEKLY_PLANNER_FINAL_CHECKLIST}"

    assert "Volume floors" in season_prompt
    assert "healthy, ambitious athletes with demonstrated recent load tolerance" in season_prompt
    assert "sport-specific volume" in season_prompt
    assert "Cross-training is supportive, not a universal substitute" in season_prompt
    assert "Long-horizon durability goals" in season_prompt
    assert "short sessions as recovery, shakeouts, taper touches" in season_prompt

    assert "Volume floors, not only safety caps" in weekly_prompt
    assert "Calibrate Volume Ambition" in weekly_prompt
    assert "Protect Specificity" in weekly_prompt
    assert "Prefer Easy Volume Before Extra Intensity" in weekly_prompt
    assert "healthy, ambitious athletes with demonstrated load tolerance" in weekly_prompt
    assert "short sessions are used as recovery/taper/shakeouts" in weekly_prompt


def test_expert_prompts_carry_transition_context_to_weekly_planner():
    combined_prompt = f"{METRICS_USER_PROMPT} {ACTIVITY_EXPERT_USER_PROMPT} {PHYSIOLOGY_USER_PROMPT}"

    assert "Transition Context for Planning Continuity" in combined_prompt
    assert "Continuity Requirement" in combined_prompt
    assert "starting load state" in combined_prompt
    assert "last meaningful stimuli" in combined_prompt
    assert "readiness corridor for the first 3-7 days" in combined_prompt


def test_weekly_formatter_prompts_keep_lap_guidance_visible():
    combined_prompt = f"{WEEKLY_FORMATTER_SYSTEM_PROMPT}\n{WEEKLY_FORMATTER_USER_PROMPT_TEMPLATE}"

    assert "per-lap/per-rep" in combined_prompt
    assert 'disclosure_mode="inline"' in combined_prompt
    assert "immediately visible in the calendar side panel" in combined_prompt
    assert "Preserve named challenge elements" in combined_prompt
    assert "micro-challenges and larger signature/breakthrough challenges as first-class content" in combined_prompt
    assert "success condition, safety cap, and fallback version" in combined_prompt
    assert "stepping stone toward a larger signature challenge" in combined_prompt


def test_season_formatter_preserves_custom_planning_instructions():
    # Source-level guard because the prompt is intentionally assembled inline in the formatter.
    source = inspect.getsource(season_formatter_node)
    assert "Priority 3 — Custom planning instructions" in source
    assert "challenge requests" in source
    assert "Priority 4 — Creative challenge thread" in source
    assert "signature/breakthrough challenges" in source
    assert "Do not flatten distinctive challenge names" in source


def test_coach_prompts_require_self_contained_segment_intensity_guidance():
    combined_prompt = f"{PLAN_MODIFIER_SYSTEM_PROMPT}\n{_TURN_SYSTEM_PROMPT}"

    assert "keep the session self-contained" in combined_prompt
    assert "each lap, rep, work block, recovery block, and cool-down" in combined_prompt
    assert "calendar session" in combined_prompt


def test_coach_turn_prompt_requires_fetching_plan_ids_before_skipping_ops():
    assert "call `get_current_weekly_plan` to obtain the relevant identifiers" in _TURN_SYSTEM_PROMPT


def test_coach_turn_prompt_mentions_structured_ui_context():
    assert "structured `ui_context`" in _TURN_SYSTEM_PROMPT


def test_coach_turn_prompt_mentions_evidence_profile_limits():
    assert "Read `evidence_profile` from the context pack" in _TURN_SYSTEM_PROMPT
    assert "activity-completeness claims are unsupported" in _TURN_SYSTEM_PROMPT


def test_daily_and_recap_prompts_require_proxy_handling():
    assert "`evidence_profile` and `claims_policy`" in DAILY_SYSTEM_PROMPT
    assert "proxy-only" in DAILY_SYSTEM_PROMPT
    assert "`evidence_profile` and `claims_policy`" in RECAP_SYSTEM_PROMPT
    assert "recovery certainty is limited" in RECAP_SYSTEM_PROMPT


def test_season_and_weekly_planner_prompts_require_declared_only_boundaries():
    combined_prompt = f"{SEASON_PLANNER_USER_PROMPT}\n{SEASON_PLANNER_UPDATE_ONLY_PROMPT}\n{WEEKLY_PLANNER_USER_PROMPT}"

    assert "Training Evidence Profile" in combined_prompt
    assert "should_acknowledge_no_connected_sources" in combined_prompt
    assert "declared profile, goals, competitions, and custom notes only" in combined_prompt
    assert (
        "do not claim recent activity history, training load, compliance, sleep, HRV, recovery, or readiness trends"
        in combined_prompt
    )
    assert "unavailable rather than inferred" in combined_prompt


def test_daily_and_coach_prompts_use_subjective_check_ins_and_volume_floors():
    combined_prompt = f"{DAILY_SYSTEM_PROMPT}\n{_TURN_SYSTEM_PROMPT}"

    assert "Subjective athlete check-ins are real coaching evidence" in DAILY_SYSTEM_PROMPT
    assert "Use them alongside device data" in DAILY_SYSTEM_PROMPT
    assert "weekly sport-specific volume floor" in DAILY_SYSTEM_PROMPT
    assert "low-risk adjustment such as easy volume" in DAILY_SYSTEM_PROMPT
    assert "Treat subjective check-ins" in _TURN_SYSTEM_PROMPT
    assert "Volume-floor awareness" in _TURN_SYSTEM_PROMPT
    assert "protect sport-specific volume" in _TURN_SYSTEM_PROMPT
    assert "Strong readiness does not automatically mean extra intensity" in combined_prompt


def test_expert_prompts_distinguish_provider_native_load_and_proxy_physiology():
    assert "vendor-specific load proxy" not in METRICS_SYSTEM_PROMPT_BASE
    assert "provider-native load series" in METRICS_SYSTEM_PROMPT_BASE
    assert "proxy-only activity stress signals" in PHYSIOLOGY_SYSTEM_PROMPT_BASE
