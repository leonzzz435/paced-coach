from pathlib import Path

import pytest
from pydantic import ValidationError

from services.ai.evals.head_coach_eval import (
    CandidateRunMetrics,
    ComparisonOutcome,
    HardInvariantResult,
    HeadCoachEvalSuite,
    ScenarioComparison,
    evaluate_release_gates,
    load_eval_suite,
)

FIXTURE_PATH = Path("tests/fixtures/head_coach_eval_cases.json")


def _passing_invariants() -> list[HardInvariantResult]:
    suite = load_eval_suite(FIXTURE_PATH)
    return [
        HardInvariantResult(scenario_id=case.scenario_id, invariant=invariant, passed=True)
        for case in suite.cases
        for invariant in case.required_invariants
    ]


def _comparisons(*, baseline_wins: int = 0) -> list[ScenarioComparison]:
    suite = load_eval_suite(FIXTURE_PATH)
    return [
        ScenarioComparison(
            scenario_id=case.scenario_id,
            outcome=(ComparisonOutcome.BASELINE_WINS if index < baseline_wins else ComparisonOutcome.CANDIDATE_WINS),
        )
        for index, case in enumerate(suite.cases)
    ]


def test_eval_fixture_covers_release_critical_provider_free_scenarios():
    suite = load_eval_suite(FIXTURE_PATH)

    assert suite.metadata.synthetic_only is True
    assert suite.baseline.mandatory_model_calls == 13
    assert len(suite.baseline.mandatory_model_nodes) == 13
    assert {case.category for case in suite.cases} == {
        "conflicting_availability",
        "experienced_constraints",
        "material_plan_change",
        "missed_week",
        "optional_evidence_unavailable",
        "pain_or_illness",
        "sparse_beginner",
        "stale_plan",
    }
    assert all(case.synthetic for case in suite.cases)


def test_eval_suite_model_is_immutable():
    suite: HeadCoachEvalSuite = load_eval_suite(FIXTURE_PATH)

    with pytest.raises(ValidationError, match="frozen"):
        suite.baseline.mandatory_model_calls = 1


def test_eval_fixture_rejects_non_synthetic_cases(tmp_path):
    payload = FIXTURE_PATH.read_text(encoding="utf-8").replace(
        '"synthetic": true',
        '"synthetic": false',
        1,
    )
    fixture_path = tmp_path / "unsafe_eval_cases.json"
    fixture_path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValidationError, match="synthetic"):
        load_eval_suite(fixture_path)


def test_release_gate_passes_for_quality_preserving_lower_call_candidate():
    suite = load_eval_suite(FIXTURE_PATH)
    candidate = CandidateRunMetrics(
        mandatory_model_calls=6,
        dedicated_deep_reasoning_formatter_calls=0,
        provider_pipeline_calls=0,
    )

    report = evaluate_release_gates(
        suite,
        candidate=candidate,
        comparisons=_comparisons(baseline_wins=1),
        invariant_results=_passing_invariants(),
    )

    assert report.passed is True
    assert report.call_reduction > 0.5
    assert report.equal_or_better_rate == pytest.approx(0.875)
    assert report.failed_gates == []


def test_release_gate_reports_each_failed_architecture_or_quality_gate():
    suite = load_eval_suite(FIXTURE_PATH)
    candidate = CandidateRunMetrics(
        mandatory_model_calls=7,
        dedicated_deep_reasoning_formatter_calls=1,
        provider_pipeline_calls=1,
    )
    invariants = _passing_invariants()
    invariants[0] = invariants[0].model_copy(update={"passed": False})

    report = evaluate_release_gates(
        suite,
        candidate=candidate,
        comparisons=_comparisons(baseline_wins=2),
        invariant_results=invariants,
    )

    assert report.passed is False
    assert set(report.failed_gates) == {
        "hard_invariants",
        "mandatory_model_call_reduction",
        "pairwise_quality",
        "provider_free_pipeline",
        "reasoning_formatter_elimination",
    }


def test_release_gate_requires_complete_scenario_evidence():
    suite = load_eval_suite(FIXTURE_PATH)

    with pytest.raises(ValueError, match="Missing comparison results"):
        evaluate_release_gates(
            suite,
            candidate=CandidateRunMetrics(
                mandatory_model_calls=6,
                dedicated_deep_reasoning_formatter_calls=0,
                provider_pipeline_calls=0,
            ),
            comparisons=_comparisons()[:-1],
            invariant_results=_passing_invariants(),
        )
