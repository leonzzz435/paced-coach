from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RunProfileName(str, Enum):
    INITIAL_PLANNING = "initial_planning"
    MATERIAL_REPLANNING = "material_replanning"
    COACH_TURN = "coach_turn"
    WEEKLY_RECAP = "weekly_recap"
    DAILY_ADAPTATION = "daily_adaptation"
    MEMORY_EXTRACTION = "memory_extraction"
    RESEARCH_SPECIALIST = "research_specialist"
    UI_COMPOSER = "ui_composer"


class EvidenceSourceKind(str, Enum):
    ATHLETE_DECLARED = "athlete_declared"
    DOMAIN_RECORD = "domain_record"
    PROVIDER_OBSERVATION = "provider_observation"
    RESEARCH = "research"
    SPECIALIST = "specialist"


class EvidenceAuthority(str, Enum):
    ATHLETE_DECLARED = "athlete_declared"
    CANONICAL_DOMAIN = "canonical_domain"
    OBSERVATIONAL = "observational"
    CONSULTATIVE = "consultative"
    INFERRED = "inferred"


class ToolCapability(str, Enum):
    ATHLETE_PROFILE = "athlete_profile"
    COMPETITIONS = "competitions"
    ACTIVE_PLANS = "active_plans"
    CALENDAR = "calendar"
    COACH_HISTORY = "coach_history"
    SPECIALIST_CONSULTATION = "specialist_consultation"
    WEB_RESEARCH = "web_research"


class EvidenceProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_kind: EvidenceSourceKind
    authority: EvidenceAuthority
    source_id: str = Field(min_length=1, max_length=300)
    observed_at: datetime | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source_authority(self) -> EvidenceProvenance:
        if (
            self.authority is EvidenceAuthority.ATHLETE_DECLARED
            and self.source_kind is not EvidenceSourceKind.ATHLETE_DECLARED
        ):
            raise ValueError("Only athlete-declared evidence may have athlete-declared authority")
        if (
            self.authority is EvidenceAuthority.CANONICAL_DOMAIN
            and self.source_kind is not EvidenceSourceKind.DOMAIN_RECORD
        ):
            raise ValueError("Only a domain record may have canonical-domain authority")
        return self


class CoachAssumption(BaseModel):
    model_config = ConfigDict(frozen=True)

    statement: str = Field(min_length=1, max_length=1000)
    consequence: str = Field(min_length=1, max_length=1000)
    needs_confirmation: bool = False


class CoachSafetyConcern(BaseModel):
    model_config = ConfigDict(frozen=True)

    concern: str = Field(min_length=1, max_length=1000)
    athlete_message_required: bool = True


class HeadCoachBrief(BaseModel):
    """Serializable full-context envelope passed into Head Coach graph state."""

    model_config = ConfigDict(frozen=True)

    owner_id: str = Field(min_length=1, max_length=200)
    run_id: str = Field(min_length=1, max_length=200)
    profile_name: RunProfileName
    as_of_utc: datetime
    local_context: dict[str, Any]


class SharedDecisionContext(BaseModel):
    """Fields shared by focused output schemas without forcing one mega-response."""

    model_config = ConfigDict(frozen=True)

    assumptions: list[CoachAssumption] = Field(default_factory=list)
    evidence: list[EvidenceProvenance] = Field(default_factory=list)
    safety_concerns: list[CoachSafetyConcern] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
