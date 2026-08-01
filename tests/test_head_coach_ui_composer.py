from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from services.ai.head_coach.artifact_rendering import render_artifact_payload
from services.ai.head_coach.artifacts import (
    ArtifactSection,
    DecisionLedgerEntry,
    NarrativeBlock,
    SeasonPhase,
    SeasonStrategyArtifactV3,
)
from services.ai.head_coach.ui_composer import (
    ContainerComposition,
    PresentationCompositionV3,
    UiCompositionError,
    artifact_semantic_hash,
    compose_with_repair,
    validate_composition,
)


def _artifact() -> SeasonStrategyArtifactV3:
    return SeasonStrategyArtifactV3(
        plan_id="season-synthetic",
        version=1,
        athlete_name="Sample Athlete",
        created_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
        title="Autumn foundation",
        summary_markdown="Build repeatability before specificity.",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 11, 1),
        phases=[
            SeasonPhase(
                phase_id="phase-foundation",
                title="Foundation",
                start_date=date(2026, 8, 3),
                end_date=date(2026, 8, 30),
                objective_markdown="Establish repeatable training frequency.",
            )
        ],
        sections=[
            ArtifactSection(
                section_id="principles",
                title="Principles",
                blocks=[NarrativeBlock(block_id="principle-1", markdown="Consistency compounds.")],
            ),
            ArtifactSection(
                section_id="guardrails",
                title="Guardrails",
                blocks=[NarrativeBlock(block_id="guardrail-1", markdown="Never make up missed work.")],
            ),
        ],
        decision_ledger_entry=DecisionLedgerEntry(
            decision_id="decision-1",
            decided_at=datetime(2026, 8, 3, 9, tzinfo=UTC),
            title="Foundation first",
            rationale_markdown="Repeatability is the limiting factor.",
            changes_markdown="Created the first season strategy.",
        ),
    )


def _valid_composition(artifact: SeasonStrategyArtifactV3) -> dict:
    return PresentationCompositionV3(
        artifact_id=artifact.plan_id,
        semantic_hash=artifact_semantic_hash(artifact),
        section_order=["guardrails", "principles"],
        containers=[
            ContainerComposition(container_id="section:principles", block_order=["principle-1"]),
            ContainerComposition(container_id="section:guardrails", block_order=["guardrail-1"]),
        ],
        featured_block_ids=["guardrail-1"],
    ).model_dump(mode="json")


def test_ui_composer_can_reorder_presentation_but_not_change_semantics():
    artifact = _artifact()
    composition = PresentationCompositionV3.model_validate(_valid_composition(artifact))

    validated = validate_composition(artifact, composition)

    assert validated.section_order == ["guardrails", "principles"]
    assert validated.semantic_hash == artifact_semantic_hash(artifact)
    assert artifact.sections[0].section_id == "principles"

    rendered = render_artifact_payload(artifact, validated)
    assert [section["section_id"] for section in rendered["sections"]] == ["guardrails", "principles"]
    assert rendered["presentation"]["featured_block_ids"] == ["guardrail-1"]
    assert artifact_semantic_hash(artifact) == validated.semantic_hash


def test_ui_composition_rejects_non_v3_schema_version():
    payload = _valid_composition(_artifact())
    payload["schema_version"] = 2

    with pytest.raises(ValidationError, match="Input should be 3"):
        PresentationCompositionV3.model_validate(payload)


@pytest.mark.asyncio
async def test_invalid_composition_is_returned_to_model_for_one_bounded_repair():
    artifact = _artifact()
    invalid = _valid_composition(artifact)
    invalid["semantic_hash"] = "changed-coaching-content"
    composer = AsyncMock(side_effect=[invalid, _valid_composition(artifact)])

    result = await compose_with_repair(artifact, composer, max_attempts=2)

    assert result.semantic_hash == artifact_semantic_hash(artifact)
    assert composer.await_count == 2
    repair_request = composer.await_args_list[1].args[0]
    assert repair_request["rejected_output"] == invalid
    assert repair_request["validation_errors"]
    assert "fallback" not in repair_request


@pytest.mark.asyncio
async def test_exhausted_ui_composer_repair_fails_visibly_without_fallback():
    artifact = _artifact()
    invalid = _valid_composition(artifact)
    invalid["section_order"] = ["principles"]
    composer = AsyncMock(return_value=invalid)

    with pytest.raises(UiCompositionError, match="repair budget exhausted"):
        await compose_with_repair(artifact, composer, max_attempts=2)

    assert composer.await_count == 2
