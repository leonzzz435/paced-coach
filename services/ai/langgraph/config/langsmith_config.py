import logging
import os

import langsmith
from langsmith import utils as langsmith_utils

logger = logging.getLogger(__name__)


class LangSmithConfig:

    @staticmethod
    def _refresh_env_cache():
        clear_env_cache = getattr(langsmith_utils.get_env_var, "cache_clear", None)
        if callable(clear_env_cache):
            clear_env_cache()
        clear_project_cache = getattr(langsmith_utils.get_tracer_project, "cache_clear", None)
        if callable(clear_project_cache):
            clear_project_cache()

    @staticmethod
    def setup_langsmith(
        project_name: str = "paced_coach_analysis", api_key: str | None = None
    ) -> bool:
        try:
            if api_key:
                os.environ["LANGSMITH_API_KEY"] = api_key

            if not os.getenv("LANGSMITH_API_KEY"):
                logger.warning("LANGSMITH_API_KEY not set - observability disabled")
                return False
            if not os.getenv("LANGCHAIN_API_KEY"):
                os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

            os.environ["LANGSMITH_PROJECT"] = project_name
            os.environ["LANGCHAIN_PROJECT"] = project_name
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_TRACING"] = "true"
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            if os.getenv("LANGSMITH_ENDPOINT") and not os.getenv("LANGCHAIN_ENDPOINT"):
                os.environ["LANGCHAIN_ENDPOINT"] = os.environ["LANGSMITH_ENDPOINT"]

            LangSmithConfig._refresh_env_cache()
            langsmith.configure(enabled=True, project_name=project_name)

            logger.info("LangSmith observability enabled for project: %s", project_name)
            return True

        except Exception:
            logger.exception("Failed to setup LangSmith")
            return False

    @staticmethod
    def get_project_name(user_id: str, analysis_type: str = "training_analysis") -> str:
        return f"paced_coach_{analysis_type}_{user_id!s}"

    @staticmethod
    def disable_langsmith():
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGSMITH_TRACING_V2"] = "false"
        os.environ["LANGCHAIN_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        LangSmithConfig._refresh_env_cache()
        langsmith.configure(enabled=False)
        logger.info("LangSmith observability disabled")


def configure_langsmith_for_user(user_id: str, analysis_type: str = "training_analysis") -> bool:
    project_name = LangSmithConfig.get_project_name(user_id, analysis_type)
    return LangSmithConfig.setup_langsmith(project_name)
