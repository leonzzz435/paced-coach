from __future__ import annotations

from services.ai.langgraph.schemas.html_sanitizer import sanitize_html
from services.ai.langgraph.schemas.ui_blocks import (
    UiAnalysis,
    UiDayPlan,
    UiDisclosureNode,
    UiHtmlBlock,
    UiKpi,
    UiSeasonPlan,
    UiWeeklyPlan,
    UiWeekPlan,
)


def _dedup_keys(blocks: list[UiHtmlBlock]) -> list[UiHtmlBlock]:
    seen: set[str] = set()
    out = []
    for block in blocks:
        key = block.key
        if key in seen:
            n = 1
            while f"{key}-{n}" in seen:
                n += 1
            key = f"{key}-{n}"
            out.append(block.model_copy(update={"key": key}))
        else:
            out.append(block)
        seen.add(key)
    return out


def _sanitize_block(block: UiHtmlBlock) -> UiHtmlBlock:
    return block.model_copy(
        update={
            "content_html": sanitize_html(block.content_html),
            "tone": block.tone if block.variant == "callout" else None,
        }
    )


def _dedup_kpis(kpis: list[UiKpi]) -> list[UiKpi]:
    seen: set[str] = set()
    sanitized: list[UiKpi] = []
    for kpi in kpis:
        kpi_id = kpi.kpi_id
        if kpi_id in seen:
            suffix = 1
            while f"{kpi_id}-{suffix}" in seen:
                suffix += 1
            kpi_id = f"{kpi_id}-{suffix}"
            sanitized.append(kpi.model_copy(update={"kpi_id": kpi_id}))
        else:
            sanitized.append(kpi)
        seen.add(kpi_id)
    return sanitized[:6]


def _sanitize_node(node: UiDisclosureNode, *, allow_meta: bool) -> UiDisclosureNode:
    blocks = [block for block in node.blocks if allow_meta or block.variant != "meta"]
    return node.model_copy(
        update={
            "blocks": _dedup_keys([_sanitize_block(block) for block in blocks]),
            "children": [_sanitize_node(child, allow_meta=allow_meta) for child in node.children],
        }
    )


def _sanitize_day(day: UiDayPlan) -> UiDayPlan:
    blocks = _dedup_keys([_sanitize_block(b) for b in day.blocks if b.variant != "meta"])
    return day.model_copy(
        update={
            "blocks": blocks,
            "nodes": [_sanitize_node(node, allow_meta=False) for node in day.nodes],
        }
    )


def _sanitize_week(week: UiWeekPlan) -> UiWeekPlan:
    return week.model_copy(
        update={
            "notes_blocks": _dedup_keys([_sanitize_block(b) for b in week.notes_blocks]),
            "notes_nodes": [_sanitize_node(node, allow_meta=True) for node in week.notes_nodes],
            "days": [_sanitize_day(day) for day in week.days],
        }
    )


def sanitize_weekly_plan(plan: UiWeeklyPlan) -> UiWeeklyPlan:
    return plan.model_copy(
        update={
            "global_blocks": _dedup_keys([_sanitize_block(b) for b in plan.global_blocks]),
            "global_nodes": [_sanitize_node(node, allow_meta=True) for node in plan.global_nodes],
            "weeks": [_sanitize_week(week) for week in plan.weeks],
        }
    )


def sanitize_season_plan(plan: UiSeasonPlan) -> UiSeasonPlan:
    return plan.model_copy(
        update={
            "global_blocks": _dedup_keys([_sanitize_block(b) for b in plan.global_blocks]),
            "global_nodes": [_sanitize_node(node, allow_meta=True) for node in plan.global_nodes],
            "phases": [
                phase.model_copy(
                    update={
                        "blocks": _dedup_keys([_sanitize_block(b) for b in phase.blocks]),
                        "nodes": [_sanitize_node(node, allow_meta=True) for node in phase.nodes],
                    }
                )
                for phase in plan.phases
            ],
        }
    )


def sanitize_analysis(analysis: UiAnalysis) -> UiAnalysis:
    return analysis.model_copy(
        update={
            "dashboard_kpis": _dedup_kpis(analysis.dashboard_kpis),
            "sections": [
                section.model_copy(
                    update={
                        "blocks": _dedup_keys([_sanitize_block(b) for b in section.blocks]),
                        "nodes": [_sanitize_node(node, allow_meta=True) for node in section.nodes],
                    }
                )
                for section in analysis.sections
            ]
        }
    )
