from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel

from services.ai.head_coach.middleware import build_head_coach_middleware
from services.ai.head_coach.prompts import build_head_coach_system_prompt
from services.ai.head_coach.run_profiles import get_run_profile
from services.ai.head_coach.schemas import RunProfileName
from services.ai.model_config import ModelSelector
from services.ai.utils.structured_output import coerce_structured_output


def build_head_coach_agent(
    *,
    profile_name: RunProfileName,
    response_schema: type[BaseModel],
    tools: Sequence[Any],
    task_instructions: str,
    name: str,
):
    """Build one bounded Head Coach agent for an explicit product entry point."""
    profile = get_run_profile(profile_name)
    model = ModelSelector.get_llm(
        profile.model_role,
        reasoning_effort=profile.reasoning_effort,
        enable_native_web_search=profile.enable_native_web_search,
    )
    system_prompt = (
        f"{build_head_coach_system_prompt(profile)}\n\n"
        f"{profile.name.value.replace('_', ' ').title()} operating instructions:\n{task_instructions}"
    )
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=build_head_coach_middleware(profile),
        response_format=ToolStrategy(
            response_schema,
            handle_errors=(
                f"Your response did not satisfy the {response_schema.__name__} contract. Correct the validation "
                "errors and return a valid structured response without changing well-supported coaching judgment."
            ),
        ),
        name=name,
    )


async def invoke_head_coach_agent[ResponseT: BaseModel](
    *,
    agent,
    user_prompt: str,
    response_schema: type[ResponseT],
    invoke_config: dict[str, Any] | None = None,
) -> ResponseT:
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_prompt}]},
        config=invoke_config,
    )
    if not isinstance(result, dict) or result.get("structured_response") is None:
        raise RuntimeError(f"Head Coach agent completed without {response_schema.__name__}")
    return coerce_structured_output(result["structured_response"], response_schema)
