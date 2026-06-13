from __future__ import annotations

import logging

from api.services.html_sanitizer import sanitize_html
from services.ai.coach.patch_apply import (
    apply_delete_day_block,
    apply_delete_week_notes_block,
    apply_replace_day_blocks,
    apply_update_day_fields,
    apply_upsert_day_block,
    apply_upsert_week_notes_block,
)
from services.ai.coach.schemas import (
    DeleteDayBlockOp,
    DeleteWeekNotesBlockOp,
    PatchOpType,
    PlanPatchOp,
    ReplaceDayBlocksOp,
    UpdateDayFieldsOp,
    UpsertDayBlockOp,
    UpsertWeekNotesBlockOp,
)
from services.ai.langgraph.schemas.ui_blocks import UiWeeklyPlan

logger = logging.getLogger(__name__)


def sanitize_ops(ops: list[PlanPatchOp]) -> list[PlanPatchOp]:
    sanitized_ops: list[PlanPatchOp] = []
    for op in ops:
        if isinstance(op, (UpsertDayBlockOp, UpsertWeekNotesBlockOp)):
            op.block = op.block.model_copy(update={"content_html": sanitize_html(op.block.content_html)})
        sanitized_ops.append(op)
    return sanitized_ops


def apply_ops(plan: UiWeeklyPlan, ops: list[PlanPatchOp]) -> tuple[UiWeeklyPlan, bool]:
    updated_plan = plan
    changed = False
    for op in ops:
        if isinstance(op, UpsertDayBlockOp):
            result = apply_upsert_day_block(updated_plan, op)
        elif isinstance(op, DeleteDayBlockOp):
            result = apply_delete_day_block(updated_plan, op)
        elif isinstance(op, ReplaceDayBlocksOp):
            result = apply_replace_day_blocks(updated_plan, op)
        elif isinstance(op, UpsertWeekNotesBlockOp):
            result = apply_upsert_week_notes_block(updated_plan, op)
        elif isinstance(op, UpdateDayFieldsOp):
            result = apply_update_day_fields(updated_plan, op)
        else:
            result = apply_delete_week_notes_block(updated_plan, op)

        updated_plan = result.updated_plan
        changed = changed or result.changed
    return updated_plan, changed


def parse_patch_ops(raw_ops: list[dict]) -> list[PlanPatchOp]:
    ops: list[PlanPatchOp] = []
    for raw_op in raw_ops:
        op_type = raw_op.get("op")
        if op_type == PatchOpType.UPSERT_DAY_BLOCK.value:
            ops.append(UpsertDayBlockOp.model_validate(raw_op))
        elif op_type == PatchOpType.DELETE_DAY_BLOCK.value:
            ops.append(DeleteDayBlockOp.model_validate(raw_op))
        elif op_type == PatchOpType.REPLACE_DAY_BLOCKS.value:
            ops.append(ReplaceDayBlocksOp.model_validate(raw_op))
        elif op_type == PatchOpType.UPSERT_WEEK_NOTES_BLOCK.value:
            ops.append(UpsertWeekNotesBlockOp.model_validate(raw_op))
        elif op_type == PatchOpType.DELETE_WEEK_NOTES_BLOCK.value:
            ops.append(DeleteWeekNotesBlockOp.model_validate(raw_op))
        elif op_type == PatchOpType.UPDATE_DAY_FIELDS.value:
            ops.append(UpdateDayFieldsOp.model_validate(raw_op))
        else:
            logger.warning("Unknown patch op type=%s, skipping", op_type)
    return ops
