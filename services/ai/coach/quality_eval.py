from __future__ import annotations

from statistics import median

from pydantic import BaseModel, Field


class QualityDimensions(BaseModel):
    specificity: float = Field(..., ge=0.0, le=1.0)
    continuity: float = Field(..., ge=0.0, le=1.0)
    personalization: float = Field(..., ge=0.0, le=1.0)
    safety: float = Field(..., ge=0.0, le=1.0)
    behavior_change_utility: float = Field(..., ge=0.0, le=1.0)

    @property
    def overall(self) -> float:
        return (
            self.specificity
            + self.continuity
            + self.personalization
            + self.safety
            + self.behavior_change_utility
        ) / 5.0


class QualityScenarioResult(BaseModel):
    scenario_id: str = Field(..., min_length=1)
    dimensions: QualityDimensions


class QualitySummary(BaseModel):
    scenario_count: int = Field(..., ge=1)
    overall_median: float = Field(..., ge=0.0, le=1.0)
    overall_p90: float = Field(..., ge=0.0, le=1.0)


def summarize_quality_results(results: list[QualityScenarioResult]) -> QualitySummary:
    if not results:
        raise ValueError("At least one quality result is required")
    overall_scores = sorted(result.dimensions.overall for result in results)
    p90_index = max(0, min(len(overall_scores) - 1, round((len(overall_scores) - 1) * 0.9)))
    return QualitySummary(
        scenario_count=len(results),
        overall_median=median(overall_scores),
        overall_p90=overall_scores[p90_index],
    )


def passes_quality_gate(
    summary: QualitySummary,
    *,
    median_threshold: float = 0.95,
    p90_threshold: float = 0.9,
) -> bool:
    return summary.overall_median >= median_threshold and summary.overall_p90 >= p90_threshold
