import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_MAX_CONCURRENT = int(os.getenv("AI_MAX_CONCURRENT_CALLS", "3"))
_MAX_CONCURRENT_TOOL_CALLS = int(os.getenv("AI_MAX_CONCURRENT_TOOL_CALLS", "6"))
_llm_semaphores: dict[int, asyncio.Semaphore] = {}
_tool_semaphores: dict[int, asyncio.Semaphore] = {}


def _get_loop_scoped_semaphore(
    cache: dict[int, asyncio.Semaphore],
    *,
    max_concurrent: int,
    label: str,
) -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    loop_id = id(loop)
    if loop_id not in cache:
        cache.clear()
        cache[loop_id] = asyncio.Semaphore(max_concurrent)
        logger.info("%s concurrency semaphore initialised (max=%d)", label, max_concurrent)
    return cache[loop_id]


def get_llm_semaphore() -> asyncio.Semaphore:
    """Return a semaphore scoped to the current event loop.

    Each ``asyncio.run()`` invocation (e.g. each Celery task) creates a new
    loop.  Caching by loop-id avoids the "semaphore bound to a different
    loop" crash that occurs when a process-global singleton outlives its loop.
    """
    return _get_loop_scoped_semaphore(
        _llm_semaphores,
        max_concurrent=_MAX_CONCURRENT,
        label="LLM",
    )


def get_tool_semaphore() -> asyncio.Semaphore:
    return _get_loop_scoped_semaphore(
        _tool_semaphores,
        max_concurrent=_MAX_CONCURRENT_TOOL_CALLS,
        label="Tool",
    )
