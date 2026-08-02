from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from services.ai.head_coach.artifacts import HeadCoachArtifactV3, SeasonStrategyArtifactV3


class UiCompositionError(ValueError):
    pass


class ContainerComposition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    container_id: str = Field(min_length=1, max_length=300)
    block_order: list[str] = Field(default_factory=list, max_length=30)
    disclosure_intent: str | None = Field(default=None, pattern=r"^(inline|collapsible|summary_first)$")

    @field_validator("block_order")
    @classmethod
    def validate_unique_block_order(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("block_order must not contain duplicate IDs")
        return value


class PresentationCompositionV3(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[3] = 3
    artifact_id: str = Field(min_length=1, max_length=200)
    semantic_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    section_order: list[str] = Field(default_factory=list, max_length=30)
    containers: list[ContainerComposition] = Field(default_factory=list, max_length=200)
    featured_block_ids: list[str] = Field(default_factory=list, max_length=3)
    collapsed_section_ids: list[str] = Field(default_factory=list, max_length=30)


ComposerCallable = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def artifact_semantic_hash(artifact: HeadCoachArtifactV3) -> str:
    canonical = json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _artifact_containers(artifact: HeadCoachArtifactV3) -> dict[str, list[str]]:
    containers = {
        f"section:{section.section_id}": [block.block_id for block in section.blocks]
        for section in artifact.sections
        if section.blocks
    }
    if isinstance(artifact, SeasonStrategyArtifactV3):
        containers.update(
            {
                f"phase:{phase.phase_id}": [block.block_id for block in phase.blocks]
                for phase in artifact.phases
                if phase.blocks
            }
        )
        return containers
    for week in artifact.weeks:
        if week.blocks:
            containers[f"week:{week.week_id}"] = [block.block_id for block in week.blocks]
        for day in week.days:
            if day.blocks:
                containers[f"day:{day.day_id}"] = [block.block_id for block in day.blocks]
            for session in day.sessions:
                if session.blocks:
                    containers[f"session:{session.session_id}"] = [block.block_id for block in session.blocks]
    return containers


def validate_composition(
    artifact: HeadCoachArtifactV3,
    composition: PresentationCompositionV3,
) -> PresentationCompositionV3:
    if composition.artifact_id != artifact.plan_id:
        raise UiCompositionError("Composition artifact_id does not match the immutable artifact")
    if composition.semantic_hash != artifact_semantic_hash(artifact):
        raise UiCompositionError("Composition semantic_hash does not match the immutable artifact")

    expected_section_ids = [section.section_id for section in artifact.sections]
    if len(composition.section_order) != len(set(composition.section_order)) or set(composition.section_order) != set(
        expected_section_ids
    ):
        raise UiCompositionError("Composition section_order must contain every artifact section exactly once")

    expected_containers = _artifact_containers(artifact)
    supplied_containers = {container.container_id: container for container in composition.containers}
    if len(supplied_containers) != len(composition.containers) or set(supplied_containers) != set(expected_containers):
        raise UiCompositionError("Composition must include every non-empty semantic-block container exactly once")
    for container_id, expected_block_ids in expected_containers.items():
        if set(supplied_containers[container_id].block_order) != set(expected_block_ids):
            raise UiCompositionError(f"Composition block_order does not preserve blocks for {container_id}")

    all_block_ids = {block_id for block_ids in expected_containers.values() for block_id in block_ids}
    if not set(composition.featured_block_ids).issubset(all_block_ids):
        raise UiCompositionError("Composition featured_block_ids contains an unknown semantic block")
    if not set(composition.collapsed_section_ids).issubset(set(expected_section_ids)):
        raise UiCompositionError("Composition collapsed_section_ids contains an unknown section")
    return composition


async def compose_with_repair(
    artifact: HeadCoachArtifactV3,
    composer: ComposerCallable,
    *,
    max_attempts: int = 2,
) -> PresentationCompositionV3:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")

    request: dict[str, Any] = {
        "artifact": artifact.model_dump(mode="json"),
        "semantic_hash": artifact_semantic_hash(artifact),
        "allowed_container_ids": sorted(_artifact_containers(artifact)),
    }
    last_error = "unknown validation error"
    for attempt in range(max_attempts):
        raw_output = await composer(request)
        try:
            return validate_composition(artifact, PresentationCompositionV3.model_validate(raw_output))
        except (ValidationError, UiCompositionError) as exc:
            last_error = str(exc)
            if attempt + 1 == max_attempts:
                break
            request = {
                **request,
                "rejected_output": raw_output,
                "validation_errors": [last_error],
                "repair_attempt": attempt + 1,
            }
    raise UiCompositionError(f"UI Composer repair budget exhausted: {last_error}")
