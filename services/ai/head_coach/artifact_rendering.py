from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from pydantic import ValidationError

from services.ai.head_coach.artifacts import (
    ExecutionPlanArtifactV3,
    HeadCoachArtifactV3,
    SeasonStrategyArtifactV3,
)
from services.ai.head_coach.ui_composer import PresentationCompositionV3, validate_composition

ArtifactType = Literal["season_plan", "weekly_plan"]
ArtifactRepairCallable = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ArtifactValidationError(ValueError):
    pass


def validate_artifact_payload(payload: dict[str, Any], *, artifact_type: ArtifactType) -> HeadCoachArtifactV3:
    if artifact_type == "season_plan":
        return SeasonStrategyArtifactV3.model_validate(payload)
    return ExecutionPlanArtifactV3.model_validate(payload)


async def validate_artifact_with_repair(
    payload: dict[str, Any],
    *,
    artifact_type: ArtifactType,
    repair: ArtifactRepairCallable,
    max_repair_attempts: int = 1,
) -> HeadCoachArtifactV3:
    if max_repair_attempts < 0:
        raise ValueError("max_repair_attempts must not be negative")

    rejected_output = payload
    last_error = "unknown validation error"
    for repair_attempt in range(max_repair_attempts + 1):
        try:
            return validate_artifact_payload(rejected_output, artifact_type=artifact_type)
        except ValidationError as exc:
            last_error = str(exc)
            if repair_attempt == max_repair_attempts:
                break
            rejected_output = await repair(
                {
                    "artifact_type": artifact_type,
                    "rejected_output": rejected_output,
                    "validation_errors": exc.errors(include_url=False),
                    "repair_attempt": repair_attempt + 1,
                }
            )
    raise ArtifactValidationError(f"Head Coach artifact repair budget exhausted: {last_error}")


def _reorder_blocks(blocks: list[dict[str, Any]], order: list[str]) -> list[dict[str, Any]]:
    by_id = {block["block_id"]: block for block in blocks}
    return [by_id[block_id] for block_id in order]


def render_artifact_payload(
    artifact: HeadCoachArtifactV3,
    composition: PresentationCompositionV3 | None = None,
) -> dict[str, Any]:
    payload = artifact.model_dump(mode="json")
    if composition is None:
        return payload

    validated = validate_composition(artifact, composition)
    container_specs = {container.container_id: container for container in validated.containers}
    sections = {section["section_id"]: section for section in payload["sections"]}
    payload["sections"] = [sections[section_id] for section_id in validated.section_order]
    for section in payload["sections"]:
        container_id = f"section:{section['section_id']}"
        if container_id in container_specs:
            spec = container_specs[container_id]
            section["blocks"] = _reorder_blocks(section["blocks"], spec.block_order)
            if spec.disclosure_intent is not None:
                section["disclosure_intent"] = spec.disclosure_intent

    if isinstance(artifact, ExecutionPlanArtifactV3):
        for week in payload["weeks"]:
            _apply_container_order(week, f"week:{week['week_id']}", container_specs)
            for day in week["days"]:
                _apply_container_order(day, f"day:{day['day_id']}", container_specs)
                for session in day["sessions"]:
                    _apply_container_order(session, f"session:{session['session_id']}", container_specs)
    else:
        for phase in payload["phases"]:
            _apply_container_order(phase, f"phase:{phase['phase_id']}", container_specs)

    payload["presentation"] = validated.model_dump(mode="json")
    return payload


def _apply_container_order(
    container: dict[str, Any],
    container_id: str,
    specs: dict[str, Any],
):
    spec = specs.get(container_id)
    if spec is not None:
        container["blocks"] = _reorder_blocks(container["blocks"], spec.block_order)
