import json
from pathlib import Path

from services.ai.coach.quality_eval import QualityDimensions, QualityScenarioResult, summarize_quality_results


def test_coach_quality_fixture_covers_required_scenarios():
    fixture_path = Path("tests/fixtures/coach_quality_eval_cases.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    categories = {item["category"] for item in payload}
    assert "progression" in categories
    assert "taper_week" in categories
    assert "injury_mention" in categories
    assert "plan_change_negotiation" in categories


def test_quality_summary_calculation():
    results = [
        QualityScenarioResult(
            scenario_id="a",
            dimensions=QualityDimensions(
                specificity=0.95,
                continuity=0.96,
                personalization=0.94,
                safety=0.99,
                behavior_change_utility=0.92,
            ),
        ),
        QualityScenarioResult(
            scenario_id="b",
            dimensions=QualityDimensions(
                specificity=0.93,
                continuity=0.91,
                personalization=0.92,
                safety=0.98,
                behavior_change_utility=0.9,
            ),
        ),
    ]
    summary = summarize_quality_results(results)
    assert summary.scenario_count == 2
    assert summary.overall_median > 0.9
    assert summary.overall_p90 > 0.9
