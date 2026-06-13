from __future__ import annotations

import os
from collections.abc import Mapping

from core.config import AIMode, get_config


def required_llm_provider_key_names() -> tuple[str, ...]:
    config = get_config()
    if config.ai_mode == AIMode.ANTHROPIC:
        return ("ANTHROPIC_API_KEY",)
    return ("OPENAI_API_KEY",)


def has_llm_provider_key(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return any(str(env.get(key) or "").strip() for key in required_llm_provider_key_names())


def format_llm_provider_key_names() -> str:
    return " or ".join(required_llm_provider_key_names())
