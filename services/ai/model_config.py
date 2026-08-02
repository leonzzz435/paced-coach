import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

from langchain_openai import ChatOpenAI

from core.config import get_config
from services.ai.langgraph.config.langsmith_config import LangSmithConfig

from .ai_settings import AgentRole, ai_settings

logger = logging.getLogger(__name__)

ReasoningEffort = Literal["low", "medium", "high", "xhigh"]


@dataclass
class ModelConfiguration:
    name: str
    base_url: str


class ModelSelector:
    PROVIDER_PARAM_ALLOWLIST = {
        "model",
        "api_key",
        "base_url",
        "include",
        "use_responses_api",
        "reasoning",
        "model_kwargs",
    }
    THINKING_DISABLED_ROLES: set[AgentRole] = set()
    XHIGH_REASONING_MODEL_ALIASES: set[str] = {
        "gpt-5.6-sol-search",
        "gpt-5.5-search",
        "gpt-5.4-search",
    }

    ROLE_DEFAULTS: dict[AgentRole, dict[str, Any]] = {
        AgentRole.HEAD_COACH: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.SPECIALIST: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
        AgentRole.UI_COMPOSER: {
            "reasoning": {"effort": "low"},
            "model_kwargs": {"text": {"verbosity": "low"}},
        },
        AgentRole.MEMORY: {
            "reasoning": {"effort": "low"},
            "model_kwargs": {"text": {"verbosity": "low"}},
        },
        AgentRole.COACH_TRIAGE: {
            "reasoning": {"effort": "high"},
            "model_kwargs": {"text": {"verbosity": "medium"}},
        },
    }

    CONFIGURATIONS: dict[str, ModelConfiguration] = {
        # OpenAI Models
        "gpt-4o": ModelConfiguration(
            name="gpt-4o",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-4.1": ModelConfiguration(
            name="gpt-4.1",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-4.5": ModelConfiguration(
            name="gpt-4.5-preview",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-4o-mini": ModelConfiguration(
            name="gpt-4o-mini",
            base_url="https://api.openai.com/v1",
        ),
        "o1": ModelConfiguration(
            name="o1-preview",
            base_url="https://api.openai.com/v1",
        ),
        "o1-mini": ModelConfiguration(
            name="o1-mini",
            base_url="https://api.openai.com/v1",
        ),
        "o3": ModelConfiguration(
            name="o3",
            base_url="https://api.openai.com/v1",
        ),
        "o3-mini": ModelConfiguration(
            name="o3-mini",
            base_url="https://api.openai.com/v1",
        ),
        "o4-mini": ModelConfiguration(
            name="o4-mini",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5": ModelConfiguration(
            name="gpt-5.5",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.6-sol": ModelConfiguration(
            name="gpt-5.6-sol",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.6-sol-search": ModelConfiguration(
            name="gpt-5.6-sol",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.5": ModelConfiguration(
            name="gpt-5.5",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.4": ModelConfiguration(
            name="gpt-5.4",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.2-pro": ModelConfiguration(
            name="gpt-5.2-pro",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5-mini": ModelConfiguration(
            name="gpt-5-mini",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5-search": ModelConfiguration(
            name="gpt-5.5",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.5-search": ModelConfiguration(
            name="gpt-5.5",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.4-search": ModelConfiguration(
            name="gpt-5.4",
            base_url="https://api.openai.com/v1",
        ),
        "gpt-5.2-pro-search": ModelConfiguration(
            name="gpt-5.2-pro",
            base_url="https://api.openai.com/v1",
        ),
    }

    MODEL_CONFIGS: dict[str, dict[str, Any]] = {
        "gpt-5": {
            "use_responses_api": True,
            "model_kwargs": {"max_output_tokens": 100000},
            "log": "Using GPT-5.5 with Responses API for {role}",
        },
        "gpt-5.6-sol": {
            "use_responses_api": True,
            "model_kwargs": {"max_output_tokens": 128000},
            "log": "Using GPT-5.6 Sol with Responses API for {role}",
        },
        "gpt-5.6-sol-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "max_output_tokens": 128000,
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.6 Sol with web search + Responses API for {role}",
        },
        "gpt-5.5": {
            "use_responses_api": True,
            "model_kwargs": {"max_output_tokens": 100000},
            "log": "Using GPT-5.5 with Responses API for {role}",
        },
        "gpt-5.4": {
            "use_responses_api": True,
            "model_kwargs": {"max_output_tokens": 100000},
            "log": "Using GPT-5.4 with Responses API for {role}",
        },
        "gpt-5.2-pro": {
            "use_responses_api": True,
            "log": "Using GPT-5.2 Pro with Responses API for {role}",
        },
        "gpt-5-mini": {
            "use_responses_api": True,
            "log": "Using GPT-5-mini with Responses API for {role}",
        },
        "gpt-5-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.5 with web search + Responses API for {role}",
        },
        "gpt-5.5-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.5 with web search + Responses API for {role}",
        },
        "gpt-5.4-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.4 with web search + Responses API for {role}",
        },
        "gpt-5.2-pro-search": {
            "use_responses_api": True,
            "model_kwargs": {
                "tools": [{"type": "web_search"}],
            },
            "include": ["web_search_call.action.sources"],
            "log": "Using GPT-5.2 Pro with web search + Responses API for {role}",
        },
    }

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def _filter_params_for_provider(cls, provider: str, llm_params: dict[str, Any]) -> dict[str, Any]:
        filtered = {key: value for key, value in llm_params.items() if key in cls.PROVIDER_PARAM_ALLOWLIST}
        if provider == "openai" and "model_kwargs" in filtered:
            model_kwargs = filtered["model_kwargs"].copy()
            if "text" in model_kwargs:
                text_config = model_kwargs["text"].copy()
                if "verbosity" in text_config:
                    text_config.pop("verbosity")
                if text_config:
                    model_kwargs["text"] = text_config
                else:
                    model_kwargs.pop("text")
            if model_kwargs:
                filtered["model_kwargs"] = model_kwargs
            else:
                filtered.pop("model_kwargs")
        return filtered

    @classmethod
    def _apply_model_config(
        cls,
        model_name: str,
        role: AgentRole,
        provider: str,
        llm_params: dict[str, Any],
        *,
        reasoning_effort: ReasoningEffort | None = None,
        enable_native_web_search: bool | None = None,
    ) -> None:
        if model_name not in cls.MODEL_CONFIGS:
            config_data: dict[str, Any] = {}
        else:
            config_data = cls.MODEL_CONFIGS[model_name].copy()

        role_overrides = cls.ROLE_DEFAULTS.get(role, {})
        merged = cls._deep_merge(config_data, role_overrides)
        if model_name in cls.XHIGH_REASONING_MODEL_ALIASES:
            merged["reasoning"] = {"effort": "xhigh"}

        cls._apply_openai_runtime_overrides(
            merged,
            reasoning_effort=reasoning_effort,
            enable_native_web_search=enable_native_web_search,
        )

        output_token_limit = merged.pop("output_token_limit", None)
        if output_token_limit is not None:
            model_kwargs = merged.setdefault("model_kwargs", {})
            model_kwargs["max_output_tokens"] = output_token_limit

        if role in cls.THINKING_DISABLED_ROLES:
            removed_thinking = "thinking" in merged or "output_config" in merged or "effort" in merged
            merged.pop("thinking", None)
            merged.pop("output_config", None)
            merged.pop("effort", None)
            if removed_thinking:
                merged["log"] = "Using {model_name} without extended reasoning for {role}"

        log_msg = merged.pop("log", None)
        llm_params.update(merged)
        if log_msg:
            logger.info(str(log_msg).format(role=role.value, model_name=model_name))

    @staticmethod
    def _apply_openai_runtime_overrides(
        merged: dict[str, Any],
        *,
        reasoning_effort: ReasoningEffort | None,
        enable_native_web_search: bool | None,
    ) -> None:
        if reasoning_effort is not None:
            merged["reasoning"] = {"effort": reasoning_effort}
        if enable_native_web_search is None:
            return

        model_kwargs = merged.setdefault("model_kwargs", {})
        existing_tools = model_kwargs.get("tools", [])
        non_search_tools = [
            tool for tool in existing_tools if not (isinstance(tool, dict) and tool.get("type") == "web_search")
        ]
        if enable_native_web_search:
            model_kwargs["tools"] = [*non_search_tools, {"type": "web_search"}]
            merged["include"] = ["web_search_call.action.sources"]
            return

        if non_search_tools:
            model_kwargs["tools"] = non_search_tools
        else:
            model_kwargs.pop("tools", None)
        merged.pop("include", None)

    @classmethod
    def get_llm(
        cls,
        role: AgentRole,
        *,
        reasoning_effort: ReasoningEffort | None = None,
        enable_native_web_search: bool | None = None,
    ):
        if role is AgentRole.COACH_TRIAGE and enable_native_web_search is None:
            enable_native_web_search = False
        model_name = ai_settings.get_model_for_role(role)
        selected_config = cls.CONFIGURATIONS.get(model_name)
        if not selected_config:
            raise RuntimeError(f"Unknown model '{model_name}' in configuration")
        config = get_config()

        # Ensure LangSmith tracing is enabled for API usage too (not only LangGraph workflows).
        # We keep this opt-in via presence of LANGSMITH_API_KEY.
        LangSmithConfig.setup_langsmith(project_name=os.getenv("LANGSMITH_PROJECT", "paced_coach"))

        base_url = selected_config.base_url
        final_model_name = selected_config.name
        provider = "openai"
        api_key = config.openai_api_key
        if not api_key:
            raise RuntimeError("OpenAI API key is required")

        logger.info("Configuring LLM for role %s with model %s", role.value, final_model_name)

        llm_params: dict[str, Any] = {"model": final_model_name, "api_key": api_key}

        cls._apply_model_config(
            model_name,
            role,
            provider,
            llm_params,
            reasoning_effort=reasoning_effort,
            enable_native_web_search=enable_native_web_search,
        )

        llm_params = cls._filter_params_for_provider(provider, llm_params)
        llm_params["base_url"] = base_url
        return ChatOpenAI(**llm_params, max_retries=3)
