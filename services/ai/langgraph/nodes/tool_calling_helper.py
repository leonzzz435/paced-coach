import asyncio
import inspect
import json
import logging
from collections.abc import Callable
from typing import Any

from langchain_core.messages import ToolMessage

from api.services.status_messages import tool_status_message
from langgraph.errors import GraphInterrupt
from services.ai.utils.concurrency import get_tool_semaphore

logger = logging.getLogger(__name__)
_TOOL_TRACE_PREVIEW_CHARS = 4000


def extract_text_content(response) -> str:
    if hasattr(response, "content_blocks"):
        try:
            blocks = response.content_blocks
            text_parts = [b["text"] for b in blocks if b.get("type") == "text" and "text" in b]
            if text_parts:
                return "".join(text_parts)
        except Exception as e:
            logger.debug("Failed to extract from content_blocks: %s", e)

    content = response.content if hasattr(response, "content") else response

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_item = next(
            (
                item["text"]
                for item in content
                if isinstance(item, dict) and item.get("type") == "text" and "text" in item
            ),
            None,
        )
        if text_item:
            return text_item

        text_item = next((item["text"] for item in content if isinstance(item, dict) and "text" in item), None)
        if text_item:
            return text_item

    return str(content)


def _serialize_tool_result(result: object) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(result)


async def invoke_tool(tool, tool_name: str, tool_args):
    if hasattr(tool, "ainvoke"):
        return await tool.ainvoke(tool_args)
    if hasattr(tool, "invoke"):
        return tool.invoke(tool_args)
    if callable(tool):
        return await tool.ainvoke(tool_args)
    return f"Unable to invoke tool {tool_name}"


async def _emit_tool_trace(
    tool_trace_collector: Callable[[dict[str, Any]], Any] | None,
    payload: dict[str, Any],
):
    if tool_trace_collector is None:
        return
    collector_result = tool_trace_collector(payload)
    if inspect.isawaitable(collector_result):
        await collector_result


async def _emit_status(
    status_emitter: Callable[[dict[str, Any]], Any] | None,
    payload: dict[str, Any],
):
    if status_emitter is None:
        return
    emitter_result = status_emitter(payload)
    if inspect.isawaitable(emitter_result):
        await emitter_result


def _find_tool(tool_name: str, tools: list):
    return next(
        (t for t in tools if hasattr(t, "name") and t.name == tool_name),
        None,
    )


async def _execute_single_tool_call(
    tool_call,
    tools: list,
    *,
    tool_trace_collector: Callable[[dict[str, Any]], Any] | None = None,
    status_emitter: Callable[[dict[str, Any]], Any] | None = None,
    iteration: int | None = None,
) -> ToolMessage:
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    tool_id = tool_call["id"]

    logger.info("Executing tool: %s", tool_name)
    await _emit_status(
        status_emitter,
        {
            "step": "tool_call_start",
            "tool_name": tool_name,
            "message": tool_status_message(tool_name, tool_args if isinstance(tool_args, dict) else None),
            "iteration": iteration,
        },
    )

    tool = _find_tool(tool_name, tools)
    if tool is None:
        error_msg = f"Tool {tool_name} not found"
        logger.error(error_msg)
        await _emit_tool_trace(
            tool_trace_collector,
            {
                "tool_name": tool_name,
                "args": tool_args,
                "result_preview": error_msg,
                "char_len": len(error_msg),
                "truncated": False,
            },
        )
        await _emit_status(
            status_emitter,
            {
                "step": "tool_call_end",
                "tool_name": tool_name,
                "message": f"Unable to run {tool_name}. Continuing...",
                "iteration": iteration,
            },
        )
        return ToolMessage(content=error_msg, tool_call_id=tool_id)

    try:
        tool_semaphore = get_tool_semaphore()
        async with tool_semaphore:
            tool_result = await invoke_tool(tool, tool_name, tool_args)
        serialized_result = _serialize_tool_result(tool_result)
        preview = serialized_result[:_TOOL_TRACE_PREVIEW_CHARS]
        logger.info("Tool %s executed successfully", tool_name)
        await _emit_tool_trace(
            tool_trace_collector,
            {
                "tool_name": tool_name,
                "args": tool_args,
                "result_preview": preview,
                "char_len": len(serialized_result),
                "truncated": len(serialized_result) > len(preview),
            },
        )
        await _emit_status(
            status_emitter,
            {
                "step": "tool_call_end",
                "tool_name": tool_name,
                "message": "Applying the latest retrieved context...",
                "iteration": iteration,
            },
        )
        return ToolMessage(content=serialized_result, tool_call_id=tool_id)
    except GraphInterrupt:
        logger.info("Tool %s triggered HITL interrupt - pausing workflow", tool_name)
        raise
    except Exception as exc:
        error_msg = f"Tool {tool_name} failed: {type(exc).__name__}: {exc}"
        logger.warning(error_msg, exc_info=True)
        await _emit_tool_trace(
            tool_trace_collector,
            {
                "tool_name": tool_name,
                "args": tool_args,
                "result_preview": error_msg,
                "char_len": len(error_msg),
                "truncated": False,
            },
        )
        await _emit_status(
            status_emitter,
            {
                "step": "tool_call_end",
                "tool_name": tool_name,
                "message": f"Tool {tool_name} encountered an error. Continuing...",
                "iteration": iteration,
            },
        )
        return ToolMessage(content=error_msg, tool_call_id=tool_id)


async def handle_tool_calling_in_node(
    llm_with_tools,
    messages: list[dict[str, str]],
    tools: list,
    max_iterations: int = 5,
    final_output_llm=None,
    invoke_config: dict[str, Any] | None = None,
    tool_trace_collector: Callable[[dict[str, Any]], Any] | None = None,
    status_emitter: Callable[[dict[str, Any]], Any] | None = None,
):
    conversation: list[Any] = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
        if msg["role"] in ("system", "user", "assistant")
    ]

    if not tools and final_output_llm is not None:
        await _emit_status(
            status_emitter,
            {
                "step": "thinking",
                "message": "Preparing your final coaching response...",
                "iteration": 1,
            },
        )
        return await final_output_llm.ainvoke(conversation, config=invoke_config)

    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        logger.debug("Tool calling iteration %s", iteration)
        await _emit_status(
            status_emitter,
            {
                "step": "thinking",
                "message": "Thinking through the next best step...",
                "iteration": iteration,
            },
        )

        response = await llm_with_tools.ainvoke(conversation, config=invoke_config)

        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info("LLM requested %s tool calls", len(response.tool_calls))

            conversation.append(response)

            tool_messages = await asyncio.gather(
                *[
                    _execute_single_tool_call(
                        tool_call,
                        tools,
                        tool_trace_collector=tool_trace_collector,
                        status_emitter=status_emitter,
                        iteration=iteration,
                    )
                    for tool_call in response.tool_calls
                ]
            )
            conversation.extend(tool_messages)
        else:
            logger.info("Final response received after %s iterations", iteration)
            await _emit_status(
                status_emitter,
                {
                    "step": "thinking",
                    "message": "Preparing your final coaching response...",
                    "iteration": iteration,
                },
            )
            if final_output_llm is not None:
                return await final_output_llm.ainvoke(conversation, config=invoke_config)
            return response

    logger.warning("Max iterations (%s) reached in tool calling", max_iterations)
    if final_output_llm is not None:
        return await final_output_llm.ainvoke(conversation, config=invoke_config)
    return response
