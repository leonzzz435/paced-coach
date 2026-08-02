import logging
import os
from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv

env_file = os.getenv("ENV_FILE", ".env")
load_dotenv(env_file)

logger = logging.getLogger(__name__)

_config_cache: dict[str, "Config"] = {}


class AIMode(Enum):
    STANDARD = "standard"
    COST_EFFECTIVE = "cost_effective"
    DEVELOPMENT = "development"
    PRO = "pro"


@dataclass
class Config:
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    openrouter_api_key: str | None = None

    ai_mode: AIMode = AIMode.STANDARD

    @classmethod
    def from_env(cls) -> "Config":
        openai_api_key = os.getenv("OPENAI_API_KEY")
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

        # Default to cost-effective mode for dev/web usage unless explicitly overridden.
        # This keeps local runs inexpensive by default, while production can set AI_MODE=standard/pro.
        ai_mode_str = os.getenv("AI_MODE", "cost_effective").lower()
        try:
            ai_mode = AIMode(ai_mode_str)
        except ValueError:
            ai_mode = AIMode.STANDARD
            logger.info("Warning: Invalid AI_MODE '%s', using %s", ai_mode_str, ai_mode.value)

        if openai_api_key and not openai_api_key.startswith("sk-"):
            raise ValueError("Invalid OPENAI_API_KEY format")

        return cls(
            ai_mode=ai_mode,
            openai_api_key=openai_api_key,
            deepseek_api_key=deepseek_api_key,
            openrouter_api_key=openrouter_api_key,
        )


def get_config() -> Config:
    cached_config = _config_cache.get("value")
    if cached_config is None:
        cached_config = Config.from_env()
        _config_cache["value"] = cached_config
    return cached_config


def reload_config() -> Config:
    _config_cache.clear()
    return get_config()
