from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvalMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    captured_at: str = Field(min_length=1)
    description: str = Field(min_length=1)
    synthetic_only: Literal[True]


class LegacyBaseline(BaseModel):
    model_config = ConfigDict(frozen=True)

    mandatory_model_calls: int = Field(ge=1)
    mandatory_model_nodes: list[str] = Field(min_length=1)
    elapsed_seconds: float = Field(gt=0.0)
    job_api_tokens: int = Field(ge=1)
    job_api_cost_usd: float = Field(ge=0.0)
    trace_tokens: int = Field(ge=1)
    trace_cost_usd: float = Field(ge=0.0)


class ReleaseGateThresholds(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_call_reduction: float = Field(ge=0.0, le=1.0)
    minimum_equal_or_better_rate: float = Field(ge=0.0, le=1.0)


class HeadCoachEvalCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    synthetic: Literal[True]
    description: str = Field(min_length=1)
    required_invariants: list[str] = Field(min_length=1)


class HeadCoachEvalSuite(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: EvalMetadata
    baseline: LegacyBaseline
    gates: ReleaseGateThresholds
    cases: list[HeadCoachEvalCase] = Field(min_length=1)


class CandidateRunMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    mandatory_model_calls: int = Field(ge=0)
    dedicated_deep_reasoning_formatter_calls: int = Field(ge=0)
    provider_pipeline_calls: int = Field(ge=0)


class ComparisonOutcome(str, Enum):
    CANDIDATE_WINS = "candidate_wins"
    TIE = "tie"
    BASELINE_WINS = "baseline_wins"


class ScenarioComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(min_length=1)
    outcome: ComparisonOutcome


class HardInvariantResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(min_length=1)
    invariant: str = Field(min_length=1)
    passed: bool


class ReleaseGateReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    call_reduction: float = Field(ge=0.0, le=1.0)
    equal_or_better_rate: float = Field(ge=0.0, le=1.0)
    failed_gates: list[str]


def load_eval_suite(path: Path) -> HeadCoachEvalSuite:
    """Load a synthetic, version-controlled release evaluation suite."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return HeadCoachEvalSuite.model_validate(payload)


def evaluate_release_gates(
    suite: HeadCoachEvalSuite,
    *,
    candidate: CandidateRunMetrics,
    comparisons: list[ScenarioComparison],
    invariant_results: list[HardInvariantResult],
) -> ReleaseGateReport:
    """Evaluate architecture and quality gates without making coaching decisions."""
    scenario_ids = {case.scenario_id for case in suite.cases}
    comparison_ids = [comparison.scenario_id for comparison in comparisons]
    _require_exact_evidence(
        expected=scenario_ids,
        actual=comparison_ids,
        evidence_name="comparison results",
    )

    expected_invariants = {
        (case.scenario_id, invariant) for case in suite.cases for invariant in case.required_invariants
    }
    actual_invariants = [(result.scenario_id, result.invariant) for result in invariant_results]
    _require_exact_evidence(
        expected=expected_invariants,
        actual=actual_invariants,
        evidence_name="hard invariant results",
    )

    call_reduction = max(
        0.0,
        1.0 - (candidate.mandatory_model_calls / suite.baseline.mandatory_model_calls),
    )
    equal_or_better = sum(comparison.outcome is not ComparisonOutcome.BASELINE_WINS for comparison in comparisons)
    equal_or_better_rate = equal_or_better / len(comparisons)

    failed_gates: list[str] = []
    if any(not result.passed for result in invariant_results):
        failed_gates.append("hard_invariants")
    if call_reduction < suite.gates.minimum_call_reduction:
        failed_gates.append("mandatory_model_call_reduction")
    if equal_or_better_rate < suite.gates.minimum_equal_or_better_rate:
        failed_gates.append("pairwise_quality")
    if candidate.provider_pipeline_calls != 0:
        failed_gates.append("provider_free_pipeline")
    if candidate.dedicated_deep_reasoning_formatter_calls != 0:
        failed_gates.append("reasoning_formatter_elimination")

    return ReleaseGateReport(
        passed=not failed_gates,
        call_reduction=call_reduction,
        equal_or_better_rate=equal_or_better_rate,
        failed_gates=failed_gates,
    )


def _require_exact_evidence[T](
    *,
    expected: set[T],
    actual: list[T],
    evidence_name: str,
) -> None:
    actual_set = set(actual)
    missing = expected - actual_set
    if missing:
        raise ValueError(f"Missing {evidence_name}: {sorted(missing, key=repr)!r}")
    unexpected = actual_set - expected
    if unexpected:
        raise ValueError(f"Unexpected {evidence_name}: {sorted(unexpected, key=repr)!r}")
    if len(actual) != len(actual_set):
        raise ValueError(f"Duplicate {evidence_name} are not allowed")
