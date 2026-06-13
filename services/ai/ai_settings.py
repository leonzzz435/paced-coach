from dataclasses import dataclass, field
from enum import Enum

from core.config import AIMode, get_config


class AgentRole(Enum):
    SUMMARIZER = "summarizer"
    METRICS_EXPERT = "metrics_expert"
    PHYSIOLOGY_EXPERT = "physiology_expert"
    ACTIVITY_EXPERT = "activity_expert"
    SYNTHESIS = "synthesis"
    WORKOUT = "workout"  # DEPRECATED alias — use WEEKLY_PLANNER
    WEEKLY_PLANNER = "weekly_planner"
    SEASON_PLANNER = "season_planner"
    ANALYSIS_FORMATTER = "analysis_formatter"
    PLAN_FORMATTER = "plan_formatter"
    COACH = "coach"
    COACH_TRIAGE = "coach_triage"
    WEEKLY_RECAP = "weekly_recap"
    DAILY_UPDATE = "daily_update"


def _gpt_5_5_search_assignments() -> dict[AgentRole, str]:
    return {
        AgentRole.SUMMARIZER: "gpt-5.5-search",
        AgentRole.ANALYSIS_FORMATTER: "gpt-5.5-search",
        AgentRole.PLAN_FORMATTER: "gpt-5.5-search",
        AgentRole.METRICS_EXPERT: "gpt-5.5-search",
        AgentRole.PHYSIOLOGY_EXPERT: "gpt-5.5-search",
        AgentRole.ACTIVITY_EXPERT: "gpt-5.5-search",
        AgentRole.SYNTHESIS: "gpt-5.5-search",
        AgentRole.WEEKLY_PLANNER: "gpt-5.5-search",
        AgentRole.SEASON_PLANNER: "gpt-5.5-search",
        AgentRole.COACH: "gpt-5.5-search",
        AgentRole.COACH_TRIAGE: "gpt-5.5-search",
        AgentRole.WEEKLY_RECAP: "gpt-5.5-search",
        AgentRole.DAILY_UPDATE: "gpt-5.5-search",
    }


def _gpt_5_5_assignments() -> dict[AgentRole, str]:
    return {
        AgentRole.SUMMARIZER: "gpt-5.5",
        AgentRole.ANALYSIS_FORMATTER: "gpt-5.5",
        AgentRole.PLAN_FORMATTER: "gpt-5.5",
        AgentRole.METRICS_EXPERT: "gpt-5.5-search",
        AgentRole.PHYSIOLOGY_EXPERT: "gpt-5.5-search",
        AgentRole.ACTIVITY_EXPERT: "gpt-5.5-search",
        AgentRole.SYNTHESIS: "gpt-5.5",
        AgentRole.WEEKLY_PLANNER: "gpt-5.5-search",
        AgentRole.SEASON_PLANNER: "gpt-5.5-search",
        AgentRole.COACH: "gpt-5.5",
        AgentRole.COACH_TRIAGE: "gpt-5.5",
        AgentRole.WEEKLY_RECAP: "gpt-5.5-search",
        AgentRole.DAILY_UPDATE: "gpt-5.5-search",
    }


def _claude_assignments() -> dict[AgentRole, str]:
    return {
        AgentRole.SUMMARIZER: "claude-4",
        AgentRole.ANALYSIS_FORMATTER: "claude-4",
        AgentRole.PLAN_FORMATTER: "claude-4",
        AgentRole.METRICS_EXPERT: "claude-4",
        AgentRole.PHYSIOLOGY_EXPERT: "claude-4",
        AgentRole.ACTIVITY_EXPERT: "claude-4",
        AgentRole.SYNTHESIS: "claude-4",
        AgentRole.WEEKLY_PLANNER: "claude-4",
        AgentRole.SEASON_PLANNER: "claude-4",
        AgentRole.COACH: "claude-4",
        AgentRole.COACH_TRIAGE: "claude-4",
        AgentRole.WEEKLY_RECAP: "claude-4",
        AgentRole.DAILY_UPDATE: "claude-4",
    }


@dataclass
class AISettings:
    mode: AIMode

    model_assignments: dict[AIMode, dict[AgentRole, str]] = field(
        default_factory=lambda: {
            AIMode.STANDARD: _gpt_5_5_search_assignments(),
            AIMode.COST_EFFECTIVE: _gpt_5_5_assignments(),
            AIMode.DEVELOPMENT: _gpt_5_5_assignments(),
            AIMode.PRO: _gpt_5_5_assignments(),
            AIMode.ANTHROPIC: _claude_assignments(),
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
