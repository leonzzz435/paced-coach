from __future__ import annotations

import copy

from services.ai.coach.schemas import (
    DeleteDayBlockOp,
    DeleteWeekNotesBlockOp,
    PatchApplicationResult,
    ReplaceDayBlocksOp,
    UpdateDayFieldsOp,
    UpsertDayBlockOp,
    UpsertWeekNotesBlockOp,
)
from services.ai.langgraph.schemas.ui_blocks import UiDisclosureNode, UiHtmlBlock, UiWeeklyPlan

_DAY_FIELD_NAMES = (
    "day_label",
    "workout_title",
    "focus_type",
    "focus_color",
    "estimated_duration_min",
    "estimated_intensity",
    "readiness_note",
)


def _flatten_node_blocks(nodes: list[UiDisclosureNode]) -> list[UiHtmlBlock]:
    out: list[UiHtmlBlock] = []
    for node in nodes:
        out.extend(node.blocks)
        if node.children:
            out.extend(_flatten_node_blocks(node.children))
    return out


def _find_block_in_nodes(nodes: list[UiDisclosureNode], key: str) -> UiHtmlBlock | None:
    for node in nodes:
        for block in node.blocks:
            if block.key == key:
                return block
        found = _find_block_in_nodes(node.children, key)
        if found is not None:
            return found
    return None


def _materialize_day_blocks(*, blocks: list[UiHtmlBlock], nodes: list[UiDisclosureNode]) -> list[UiHtmlBlock]:
    merged = list(blocks)
    if not nodes:
        return merged
    existing_keys = {block.key for block in merged}
    for block in _flatten_node_blocks(nodes):
        if block.key in existing_keys:
            continue
        merged.append(block)
        existing_keys.add(block.key)
    return merged


def apply_update_day_fields(plan: UiWeeklyPlan, op: UpdateDayFieldsOp) -> PatchApplicationResult:
    updated = copy.deepcopy(plan)

    provided_fields = [field for field in _DAY_FIELD_NAMES if field in op.model_fields_set]
    if not provided_fields:
        return PatchApplicationResult(updated_plan=updated, changed=False)

    if all(getattr(op, field) is None for field in provided_fields):
        return PatchApplicationResult(updated_plan=updated, changed=False)

    update = {field: getattr(op, field) for field in provided_fields}

    for week in updated.weeks:
        for idx, day in enumerate(week.days):
            if day.day_id != op.day_id:
                continue

            updated_day = day.model_copy(update=update)
            if updated_day == day:
                return PatchApplicationResult(updated_plan=updated, changed=False)

            week.days[idx] = updated_day
            return PatchApplicationResult(updated_plan=updated, changed=True)

    return PatchApplicationResult(updated_plan=updated, changed=False)


def apply_delete_day_block(plan: UiWeeklyPlan, op: DeleteDayBlockOp) -> PatchApplicationResult:
    updated = copy.deepcopy(plan)

    for week in updated.weeks:
        for idx, day in enumerate(week.days):
            if day.day_id != op.day_id:
                continue

            in_blocks = next((block for block in day.blocks if block.key == op.key), None) is not None
            in_nodes = _find_block_in_nodes(day.nodes, op.key) is not None
            if not in_blocks and not in_nodes:
                return PatchApplicationResult(updated_plan=updated, changed=False)

            blocks = _materialize_day_blocks(blocks=list(day.blocks), nodes=day.nodes)
            blocks = [block for block in blocks if block.key != op.key]
            update: dict = {"blocks": blocks}
            if day.nodes:
                update["nodes"] = []
            week.days[idx] = day.model_copy(update=update)
            return PatchApplicationResult(updated_plan=updated, changed=True)

    return PatchApplicationResult(updated_plan=updated, changed=False)


def apply_replace_day_blocks(plan: UiWeeklyPlan, op: ReplaceDayBlocksOp) -> PatchApplicationResult:
    updated = copy.deepcopy(plan)

    for week in updated.weeks:
        for idx, day in enumerate(week.days):
            if day.day_id != op.day_id:
                continue

            if not day.nodes and day.blocks == op.blocks:
                return PatchApplicationResult(updated_plan=updated, changed=False)

            update: dict = {"blocks": op.blocks}
            if day.nodes:
                update["nodes"] = []
            week.days[idx] = day.model_copy(update=update)
            return PatchApplicationResult(updated_plan=updated, changed=True)

    return PatchApplicationResult(updated_plan=updated, changed=False)


def apply_upsert_day_block(plan: UiWeeklyPlan, op: UpsertDayBlockOp) -> PatchApplicationResult:
    updated = copy.deepcopy(plan)

    for week in updated.weeks:
        for idx, day in enumerate(week.days):
            if day.day_id != op.day_id:
                continue

            existing_in_blocks = next((block for block in day.blocks if block.key == op.block.key), None)
            if existing_in_blocks is not None and existing_in_blocks == op.block:
                return PatchApplicationResult(updated_plan=updated, changed=False)

            existing_in_nodes = _find_block_in_nodes(day.nodes, op.block.key)
            if existing_in_blocks is None and existing_in_nodes is not None and existing_in_nodes == op.block:
                return PatchApplicationResult(updated_plan=updated, changed=False)

            blocks = _materialize_day_blocks(blocks=list(day.blocks), nodes=day.nodes)
            block_index = next((i for i, block in enumerate(blocks) if block.key == op.block.key), None)

            if block_index is None:
                blocks.append(op.block)
            else:
                blocks[block_index] = op.block

            update: dict = {"blocks": blocks}
            if day.nodes:
                update["nodes"] = []
            week.days[idx] = day.model_copy(update=update)
            return PatchApplicationResult(updated_plan=updated, changed=True)

    return PatchApplicationResult(updated_plan=updated, changed=False)


def apply_upsert_week_notes_block(plan: UiWeeklyPlan, op: UpsertWeekNotesBlockOp) -> PatchApplicationResult:
    updated = copy.deepcopy(plan)

    for idx, week in enumerate(updated.weeks):
        if week.week_id != op.week_id:
            continue

        existing_in_blocks = next((block for block in week.notes_blocks if block.key == op.block.key), None)
        if existing_in_blocks is not None and existing_in_blocks == op.block:
            return PatchApplicationResult(updated_plan=updated, changed=False)

        existing_in_nodes = _find_block_in_nodes(week.notes_nodes, op.block.key)
        if existing_in_blocks is None and existing_in_nodes is not None and existing_in_nodes == op.block:
            return PatchApplicationResult(updated_plan=updated, changed=False)

        notes = _materialize_day_blocks(blocks=list(week.notes_blocks), nodes=week.notes_nodes)
        block_index = next((i for i, block in enumerate(notes) if block.key == op.block.key), None)
        if block_index is None:
            notes.append(op.block)
        else:
            notes[block_index] = op.block

        update: dict = {"notes_blocks": notes}
        if week.notes_nodes:
            update["notes_nodes"] = []
        updated_week = week.model_copy(update=update)
        if updated_week == week:
            return PatchApplicationResult(updated_plan=updated, changed=False)

        updated.weeks[idx] = updated_week
        return PatchApplicationResult(updated_plan=updated, changed=True)

    return PatchApplicationResult(updated_plan=updated, changed=False)


def apply_delete_week_notes_block(plan: UiWeeklyPlan, op: DeleteWeekNotesBlockOp) -> PatchApplicationResult:
    updated = copy.deepcopy(plan)

    for idx, week in enumerate(updated.weeks):
        if week.week_id != op.week_id:
            continue

        in_blocks = next((block for block in week.notes_blocks if block.key == op.key), None) is not None
        in_nodes = _find_block_in_nodes(week.notes_nodes, op.key) is not None
        if not in_blocks and not in_nodes:
            return PatchApplicationResult(updated_plan=updated, changed=False)

        notes = _materialize_day_blocks(blocks=list(week.notes_blocks), nodes=week.notes_nodes)
        notes = [block for block in notes if block.key != op.key]

        update: dict = {"notes_blocks": notes}
        if week.notes_nodes:
            update["notes_nodes"] = []
        updated.weeks[idx] = week.model_copy(update=update)
        return PatchApplicationResult(updated_plan=updated, changed=True)

    return PatchApplicationResult(updated_plan=updated, changed=False)
