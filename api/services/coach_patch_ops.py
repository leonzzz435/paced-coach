from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, Literal, overload

from api.services.html_sanitizer import sanitize_html
from services.ai.coach.patch_apply import (
    apply_delete_day_block,
    apply_delete_week_notes_block,
    apply_replace_day_blocks,
    apply_replace_v3_semantic_block,
    apply_update_day_fields,
    apply_update_v3_day_fields,
    apply_update_v3_session_fields,
    apply_upsert_day_block,
    apply_upsert_week_notes_block,
)
from services.ai.coach.schemas import (
    AnyPlanPatchOp,
    DeleteDayBlockOp,
    DeleteWeekNotesBlockOp,
    PatchOpType,
    PlanPatchOp,
    ReplaceDayBlocksOp,
    ReplaceV3SemanticBlockOp,
    UpdateDayFieldsOp,
    UpdateV3DayFieldsOp,
    UpdateV3SessionFieldsOp,
    UpsertDayBlockOp,
    UpsertWeekNotesBlockOp,
    V3PatchOpType,
    V3PlanPatchOp,
)
from services.ai.head_coach.artifacts import ExecutionPlanArtifactV3
from services.ai.langgraph.schemas.ui_blocks import UiWeeklyPlan

logger = logging.getLogger(__name__)


def sanitize_ops(ops: list[PlanPatchOp]) -> list[PlanPatchOp]:
    sanitized_ops: list[PlanPatchOp] = []
    for op in ops:
        if isinstance(op, (UpsertDayBlockOp, UpsertWeekNotesBlockOp)):
            op.block = op.block.model_copy(update={"content_html": sanitize_html(op.block.content_html)})
        sanitized_ops.append(op)
    return sanitized_ops


def prepare_ops_for_plan(
    plan: UiWeeklyPlan | ExecutionPlanArtifactV3,
    ops: Sequence[AnyPlanPatchOp],
) -> list[AnyPlanPatchOp]:
    if isinstance(plan, ExecutionPlanArtifactV3):
        if any(isinstance(op, (UpsertDayBlockOp, DeleteDayBlockOp, ReplaceDayBlocksOp, UpsertWeekNotesBlockOp, DeleteWeekNotesBlockOp, UpdateDayFieldsOp)) for op in ops):
            raise ValueError("Schema-v1 patch operations cannot mutate a schema-v3 plan")
        return list(ops)

    legacy_ops: list[PlanPatchOp] = []
    for op in ops:
        if isinstance(op, (UpdateV3DayFieldsOp, UpdateV3SessionFieldsOp, ReplaceV3SemanticBlockOp)):
            raise ValueError("Schema-v3 patch operations cannot mutate a schema-v1 plan")
        legacy_ops.append(op)
    return list(sanitize_ops(legacy_ops))


def apply_ops(
    plan: UiWeeklyPlan | ExecutionPlanArtifactV3,
    ops: Sequence[AnyPlanPatchOp],
) -> tuple[UiWeeklyPlan | ExecutionPlanArtifactV3, bool]:
    if isinstance(plan, ExecutionPlanArtifactV3):
        return _apply_v3_ops(plan, ops)
    return _apply_v1_ops(plan, ops)


def _apply_v1_ops(plan: UiWeeklyPlan, ops: Sequence[AnyPlanPatchOp]) -> tuple[UiWeeklyPlan, bool]:
    if any(isinstance(op, (UpdateV3DayFieldsOp, UpdateV3SessionFieldsOp, ReplaceV3SemanticBlockOp)) for op in ops):
        raise ValueError("Schema-v3 patch operations cannot mutate a schema-v1 plan")

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
        elif isinstance(op, DeleteWeekNotesBlockOp):
            result = apply_delete_week_notes_block(updated_plan, op)
        else:
            raise ValueError("Schema-v3 patch operations cannot mutate a schema-v1 plan")

        if not isinstance(result.updated_plan, UiWeeklyPlan):
            raise TypeError("Schema-v1 patch application returned the wrong plan type")
        updated_plan = result.updated_plan
        changed = changed or result.changed
    return updated_plan, changed


def _apply_v3_ops(
    plan: ExecutionPlanArtifactV3,
    ops: Sequence[AnyPlanPatchOp],
) -> tuple[ExecutionPlanArtifactV3, bool]:
    updated_plan = plan
    changed = False
    for op in ops:
        if isinstance(op, UpdateV3DayFieldsOp):
            result = apply_update_v3_day_fields(updated_plan, op)
        elif isinstance(op, UpdateV3SessionFieldsOp):
            result = apply_update_v3_session_fields(updated_plan, op)
        elif isinstance(op, ReplaceV3SemanticBlockOp):
            result = apply_replace_v3_semantic_block(updated_plan, op)
        else:
            raise ValueError("Schema-v1 patch operations cannot mutate a schema-v3 plan")
        if not isinstance(result.updated_plan, ExecutionPlanArtifactV3):
            raise TypeError("Schema-v3 patch application returned the wrong plan type")
        updated_plan = result.updated_plan
        changed = changed or result.changed
    return updated_plan, changed


@overload
def parse_patch_ops(raw_ops: list[dict], *, schema_version: Literal[1] = 1) -> list[PlanPatchOp]: ...


@overload
def parse_patch_ops(raw_ops: list[dict], *, schema_version: Literal[3]) -> list[V3PlanPatchOp]: ...


@overload
def parse_patch_ops(raw_ops: list[dict], *, schema_version: int) -> list[AnyPlanPatchOp]: ...


def parse_patch_ops(raw_ops: list[dict], *, schema_version: int = 1) -> list[Any]:
    if schema_version == 3:
        return _parse_v3_patch_ops(raw_ops)
    if schema_version != 1:
        raise ValueError(f"Unsupported weekly-plan schema version: {schema_version}")

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


def _parse_v3_patch_ops(raw_ops: list[dict]) -> list[V3PlanPatchOp]:
    ops: list[V3PlanPatchOp] = []
    for raw_op in raw_ops:
        op_type = raw_op.get("op")
        if op_type == V3PatchOpType.UPDATE_DAY_FIELDS.value:
            ops.append(UpdateV3DayFieldsOp.model_validate(raw_op))
        elif op_type == V3PatchOpType.UPDATE_SESSION_FIELDS.value:
            ops.append(UpdateV3SessionFieldsOp.model_validate(raw_op))
        elif op_type == V3PatchOpType.REPLACE_SEMANTIC_BLOCK.value:
            ops.append(ReplaceV3SemanticBlockOp.model_validate(raw_op))
        else:
            raise ValueError(f"Unknown schema-v3 patch operation: {op_type}")
    return ops


def parse_weekly_plan(payload: dict) -> UiWeeklyPlan | ExecutionPlanArtifactV3:
    schema_version = payload.get("schema_version", 1)
    if schema_version == 1:
        return UiWeeklyPlan.model_validate(payload)
    if schema_version == 3:
        return ExecutionPlanArtifactV3.model_validate(payload)
    raise ValueError(f"Unsupported weekly-plan schema version: {schema_version}")
