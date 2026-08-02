from dataclasses import dataclass, field
from enum import Enum

from core.config import AIMode, get_config


class AgentRole(Enum):
    HEAD_COACH = "head_coach"
    SPECIALIST = "specialist"
    UI_COMPOSER = "ui_composer"
    MEMORY = "memory"
    COACH_TRIAGE = "coach_triage"


def _gpt_5_6_sol_search_assignments() -> dict[AgentRole, str]:
    return {
        AgentRole.HEAD_COACH: "gpt-5.6-sol-search",
        AgentRole.SPECIALIST: "gpt-5.6-sol-search",
        AgentRole.UI_COMPOSER: "gpt-5.6-sol-search",
        AgentRole.MEMORY: "gpt-5.6-sol-search",
        AgentRole.COACH_TRIAGE: "gpt-5.6-sol-search",
    }


def _gpt_5_5_assignments() -> dict[AgentRole, str]:
    return {
        AgentRole.HEAD_COACH: "gpt-5.5",
        AgentRole.SPECIALIST: "gpt-5.5-search",
        AgentRole.UI_COMPOSER: "gpt-5.5",
        AgentRole.MEMORY: "gpt-5.5",
        AgentRole.COACH_TRIAGE: "gpt-5.5",
    }


@dataclass
class AISettings:
    mode: AIMode

    model_assignments: dict[AIMode, dict[AgentRole, str]] = field(
        default_factory=lambda: {
            AIMode.STANDARD: _gpt_5_6_sol_search_assignments(),
            AIMode.COST_EFFECTIVE: _gpt_5_5_assignments(),
            AIMode.DEVELOPMENT: _gpt_5_5_assignments(),
            AIMode.PRO: _gpt_5_5_assignments(),
        }
    )

    def get_model_for_role(self, role: AgentRole) -> str:
        return self.model_assignments[self.mode][role]

    @classmethod
    def load_settings(cls) -> "AISettings":
        return cls(mode=get_config().ai_mode)

    def reload(self) -> None:
        self.mode = get_config().ai_mode


# Global settings instance
ai_settings = AISettings.load_settings()
