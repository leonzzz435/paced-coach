import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

import openai
from langchain_core.exceptions import OutputParserException
from langgraph.errors import GraphInterrupt
from pydantic import ValidationError

from services.ai.utils.concurrency import get_llm_semaphore

logger = logging.getLogger(__name__)


def _is_truncation_error(exc: Exception) -> bool:
    if not isinstance(exc, ValidationError):
        return False
    msg = str(exc)
    return "\u0000" in msg or "EOF while parsing" in msg


class RetryableError(Exception):
    pass


class APIOverloadError(RetryableError):
    pass


def _extract_retry_after(exc: Exception) -> float | None:
    """Extract Retry-After seconds from OpenAI 429 responses."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        retry_after = headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except (ValueError, TypeError):
                pass
    return None


class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: set[type[Exception]] | None = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or {
            # OpenAI
            openai.RateLimitError,  # 429 - rate limits
            openai.APIConnectionError,  # Network/connection issues
            openai.APITimeoutError,  # Timeouts
            openai.InternalServerError,  # 5xx - server errors
            openai.ConflictError,  # 409 - conflicts
            # LangChain structured output — model may skip tool call when thinking is enabled
            OutputParserException,
            # Custom
            APIOverloadError,  # Custom local exception
        }

    def calculate_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)
        if self.jitter:
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)
        return max(delay, 0.1)


async def retry_with_backoff(
    func: Callable[[], Awaitable[Any]],
    config: RetryConfig | None = None,
    context: str = "operation",
) -> Any:
    if config is None:
        config = RetryConfig()

    semaphore = get_llm_semaphore()
    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            logger.debug(
                "Attempting %s (attempt %s/%s)",
                context,
                attempt + 1,
                config.max_retries + 1,
            )
            async with semaphore:
                return await func()

        except GraphInterrupt:
            raise

        except Exception as exc:
            last_exception = exc
            attempt_number = attempt + 1
            total_attempts = config.max_retries + 1

            is_retryable = any(isinstance(exc, exc_type) for exc_type in config.retryable_exceptions)

            if is_retryable:
                logger.warning(
                    "%s failed with retryable %s on attempt %s/%s: %s",
                    context,
                    type(exc).__name__,
                    attempt_number,
                    total_attempts,
                    exc,
                    exc_info=True,
                )
            else:
                if _is_truncation_error(exc):
                    logger.error(
                        "%s: OUTPUT TRUNCATION DETECTED — model hit output token ceiling. "
                        "Null bytes / EOF in JSON confirm the response was cut off mid-generation. "
                        "Check max_output_tokens config and prompt length constraints.",
                        context,
                    )
                logger.exception(
                    "%s failed with non-retryable %s on attempt %s/%s: %s",
                    context,
                    type(exc).__name__,
                    attempt_number,
                    total_attempts,
                    exc,
                )
                break

            if attempt < config.max_retries:
                delay = config.calculate_delay(attempt)
                retry_after = _extract_retry_after(exc)
                if retry_after is not None:
                    delay = max(delay, retry_after)
                    logger.info(
                        "%s: Retry-After header requested %.1fs delay",
                        context,
                        retry_after,
                    )
                logger.info(
                    "%s failed on attempt %s/%s, retrying in %.1fs",
                    context,
                    attempt_number,
                    total_attempts,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.exception(
                    "%s failed after %s attempts: %s",
                    context,
                    total_attempts,
                    exc,
                )

    if last_exception is None:
        raise RuntimeError(f"{context} failed without capturing an exception")
    raise last_exception


def with_retry(config: RetryConfig | None = None, context: str | None = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_context = context or func.__name__

            async def call_func():
                return await func(*args, **kwargs)

            return await retry_with_backoff(call_func, config, func_context)

        return wrapper

    return decorator


DEFAULT_CONFIG = RetryConfig(max_retries=3, base_delay=1.0, max_delay=60.0)

AI_ANALYSIS_CONFIG = RetryConfig(
    max_retries=5,
    base_delay=2.0,
    max_delay=120.0,
    exponential_base=2.5,
)

QUICK_RETRY_CONFIG = RetryConfig(max_retries=2, base_delay=0.5, max_delay=10.0)
