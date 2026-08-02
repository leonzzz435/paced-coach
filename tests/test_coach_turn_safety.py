from pathlib import Path

from api.services.coach_turn import _with_disclaimer_if_needed
from services.ai.evals.head_coach_eval import load_eval_suite


def test_disclaimer_added_for_health_keywords():
    output = _with_disclaimer_if_needed(
        base_message="Let's reduce intensity for a few days.",
        user_message="My knee pain got worse after intervals.",
        requires_disclaimer=False,
    )
    assert "consult a qualified medical professional" in output.lower()


def test_disclaimer_not_added_when_not_needed():
    output = _with_disclaimer_if_needed(
        base_message="Nice consistency this week. Keep the easy run easy.",
        user_message="Can we move my long run to Thursday?",
        requires_disclaimer=False,
    )
    assert "consult a qualified medical professional" not in output.lower()


def test_disclaimer_not_added_for_generic_fatigue_when_model_flag_is_true_without_health_signal():
    output = _with_disclaimer_if_needed(
        base_message="Monday as a rest day makes sense. Keep Tuesday disciplined.",
        user_message="Yeah legs feel tired. Tomorrow rest day totally make sense!",
        requires_disclaimer=True,
        safety_flags=[],
    )
    assert "consult a qualified medical professional" not in output.lower()


def test_disclaimer_added_when_safety_flags_call_out_health_concern():
    output = _with_disclaimer_if_needed(
        base_message="Back off intensity and monitor the symptoms closely.",
        user_message="Can we adjust the plan?",
        requires_disclaimer=True,
        safety_flags=["injury concern"],
    )
    assert "consult a qualified medical professional" in output.lower()


def test_head_coach_release_gate_keeps_pain_safety_as_hard_invariant():
    suite = load_eval_suite(Path("tests/fixtures/head_coach_eval_cases.json"))
    pain_case = next(case for case in suite.cases if case.category == "pain_or_illness")

    assert set(pain_case.required_invariants) >= {
        "safety_boundary_preserved",
        "health_disclaimer_present",
    }
