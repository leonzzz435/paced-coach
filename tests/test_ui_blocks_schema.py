from datetime import date
from typing import cast

from services.ai.langgraph.schemas.ui_blocks import (
    UiAnalysisSection,
    UiDisclosureNode,
    UiHtmlBlock,
    UiKpi,
    UiWeeklyPlan,
    UiWeekPlan,
)


def test_ui_weekly_plan_clamps_invalid_dates():
    plan = UiWeeklyPlan(
        weeks=[
            UiWeekPlan(
                week_id="wk-2026-02-24",
                start_date=date(2026, 2, 24),
                end_date=cast("date", "2026-02-30"),
                days=[],
            )
        ]
    )

    assert plan.weeks[0].end_date.isoformat() == "2026-02-28"


def test_ui_signal_tone_aliases_are_normalized():
    block = UiHtmlBlock.model_validate(
        {
            "key": "key-insight",
            "variant": "callout",
            "tone": "accent",
            "content_html": '<div class="callout-accent">Key insight</div>',
        }
    )
    node = UiDisclosureNode.model_validate({"node_id": "load", "title": "Load", "tone": "info"})
    section = UiAnalysisSection.model_validate({"section_id": "readiness", "title": "Readiness", "tone": "accent"})
    kpi = UiKpi.model_validate({"kpi_id": "sleep-score", "label": "Sleep", "value": "82", "status": "warn"})

    assert block.tone == "neutral"
    assert node.tone == "neutral"
    assert section.tone == "neutral"
    assert kpi.status == "warning"
