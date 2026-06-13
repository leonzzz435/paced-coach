"""SQLAlchemy models.

These imports ensure Alembic sees model metadata consistently.
"""

from api.models.active_analysis import ActiveAnalysis
from api.models.active_season_plan import ActiveSeasonPlan
from api.models.active_weekly_plan import ActiveWeeklyPlan
from api.models.ai_run_cost import AiRunCost
from api.models.athlete_profile import AthleteProfile
from api.models.coach_conversation import CoachConversation
from api.models.coach_event import CoachEvent
from api.models.coach_interaction_quota import CoachInteractionQuota
from api.models.coach_message import CoachMessage
from api.models.coach_proposal import CoachProposal
from api.models.coach_thread import CoachThread
from api.models.coach_turn_request import CoachTurnRequest
from api.models.coach_turn_run import CoachTurnRun
from api.models.competition import Competition
from api.models.credentials import StravaCredentials, WhoopCredentials
from api.models.daily_update_run import DailyUpdateRun
from api.models.integration_connection import IntegrationConnection
from api.models.job import AnalysisJob
from api.models.local_usage import LocalUsageCounter, LocalUsageEvent, LocalUsagePlanOverride
from api.models.oauth_session import OAuthSession
from api.models.user import User
from api.models.weekly_recap_run import WeeklyRecapRun

__all__ = [
    "ActiveAnalysis",
    "ActiveSeasonPlan",
    "ActiveWeeklyPlan",
    "AiRunCost",
    "AnalysisJob",
    "AthleteProfile",
    "CoachConversation",
    "CoachEvent",
    "CoachInteractionQuota",
    "CoachMessage",
    "CoachProposal",
    "CoachThread",
    "CoachTurnRequest",
    "CoachTurnRun",
    "Competition",
    "DailyUpdateRun",
    "IntegrationConnection",
    "LocalUsageCounter",
    "LocalUsageEvent",
    "LocalUsagePlanOverride",
    "OAuthSession",
    "StravaCredentials",
    "User",
    "WeeklyRecapRun",
    "WhoopCredentials",
]
