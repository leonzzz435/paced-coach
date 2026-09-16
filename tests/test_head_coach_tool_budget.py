from typing import Any

import pytest
from langchain.agents import create_agent
from langchain.agents.middleware.tool_call_limit import ToolCallLimitExceededError
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from pydantic import BaseModel

from services.ai.head_coach import agent as head_coach_agent
from services.ai.head_coach.middleware import build_head_coach_middleware
from services.ai.head_coach.run_profiles import get_run_profile
from services.ai.head_coach.schemas import RunProfileName


class BudgetResponse(BaseModel):
    answer: str


class ScriptedToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any):
        return self


def response_message(answer: str = "Synthetic memory") -> AIMessage:
    return AIMessage(content="", tool_calls=[{
        "name": "BudgetResponse", "args": {"answer": answer}, "id": "response",
    }])


@pytest.mark.asyncio
@pytest.mark.parametrize("profile_name", [RunProfileName.MEMORY_EXTRACTION, RunProfileName.UI_COMPOSER])
async def test_zero_tool_profiles_can_return_their_structured_answer(monkeypatch, profile_name):
    model = ScriptedToolModel(responses=[response_message()])
    monkeypatch.setattr(head_coach_agent.ModelSelector, "get_llm", lambda *args, **kwargs: model)
    agent = head_coach_agent.build_head_coach_agent(
        profile_name=profile_name, response_schema=BudgetResponse,
        tools=[], task_instructions="Return the synthetic result.", name="budget-regression",
    )

    result = await head_coach_agent.invoke_head_coach_agent(
        agent=agent, user_prompt="Synthetic context", response_schema=BudgetResponse,
    )

    assert result.answer == "Synthetic memory"


@pytest.mark.asyncio
@pytest.mark.parametrize("call_count,exceeds_budget", [(1, False), (2, True)])
async def test_application_budget_is_preserved_when_the_answer_is_exempt(call_count, exceeds_budget):
    executions = []

    @tool
    def read_context() -> str:
        """Read synthetic application context."""
        executions.append("read")
        return "Synthetic context"

    profile = get_run_profile(RunProfileName.COACH_TURN).model_copy(update={"tool_call_limit": 1})
    model = ScriptedToolModel(responses=[
        AIMessage(content="", tool_calls=[
            {"name": "read_context", "args": {}, "id": f"read-{index}"} for index in range(call_count)
        ]),
        response_message(),
    ])
    agent = create_agent(
        model=model, tools=[read_context], response_format=ToolStrategy(BudgetResponse),
        middleware=build_head_coach_middleware(profile, response_tool_names=frozenset({"BudgetResponse"})),
    )

    if exceeds_budget:
        with pytest.raises(ToolCallLimitExceededError):
            await agent.ainvoke({"messages": [{"role": "user", "content": "Read and answer"}]})
        assert executions == []
    else:
        result = await agent.ainvoke({"messages": [{"role": "user", "content": "Read and answer"}]})
        assert result["structured_response"].answer == "Synthetic memory"
        assert executions == ["read"]


@pytest.mark.asyncio
async def test_zero_tool_budget_still_rejects_an_unregistered_call():
    model = ScriptedToolModel(responses=[AIMessage(content="", tool_calls=[
        {"name": "read_context", "args": {}, "id": "unexpected"},
    ])])
    agent = create_agent(
        model=model, tools=[], response_format=ToolStrategy(BudgetResponse),
        middleware=build_head_coach_middleware(
            get_run_profile(RunProfileName.MEMORY_EXTRACTION),
            response_tool_names=frozenset({"BudgetResponse"}),
        ),
    )
    with pytest.raises(ToolCallLimitExceededError):
        await agent.ainvoke({"messages": [{"role": "user", "content": "Return memory"}]})
