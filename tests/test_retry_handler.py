"""Tests for retry_handler with OpenAI/Anthropic rate-limit resilience."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import openai
import pytest

from services.ai.utils.retry_handler import (
    RetryConfig,
    _extract_retry_after,
    retry_with_backoff,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_openai_rate_limit_error(retry_after: str | None = None):
    """Build a realistic openai.RateLimitError with optional Retry-After header."""
    headers = {"retry-after": retry_after} if retry_after else {}
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = headers
    return openai.RateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body=None,
    )


def _make_anthropic_rate_limit_error():
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    return anthropic.RateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body=None,
    )


def _make_anthropic_internal_server_error():
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.headers = {}
    return anthropic.InternalServerError(
        message="Grammar compilation is temporarily unavailable. Please try again.",
        response=mock_response,
        body={
            "type": "error",
            "error": {
                "type": "overloaded_error",
                "message": "Grammar compilation is temporarily unavailable. Please try again.",
            },
        },
    )


FAST_CONFIG = RetryConfig(max_retries=3, base_delay=0.01, max_delay=0.05, jitter=False)


# ---------------------------------------------------------------------------
# _extract_retry_after
# ---------------------------------------------------------------------------


class TestExtractRetryAfter:
    def test_extracts_float_header(self):
        exc = _make_openai_rate_limit_error(retry_after="5.0")
        assert _extract_retry_after(exc) == 5.0

    def test_extracts_int_header(self):
        exc = _make_openai_rate_limit_error(retry_after="10")
        assert _extract_retry_after(exc) == 10.0

    def test_returns_none_when_no_header(self):
        exc = _make_openai_rate_limit_error(retry_after=None)
        assert _extract_retry_after(exc) is None

    def test_returns_none_for_non_numeric(self):
        exc = _make_openai_rate_limit_error(retry_after="not-a-number")
        assert _extract_retry_after(exc) is None

    def test_returns_none_for_plain_exception(self):
        assert _extract_retry_after(ValueError("oops")) is None


# ---------------------------------------------------------------------------
# retry_with_backoff — retryable exceptions
# ---------------------------------------------------------------------------


class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_openai_rate_limit_is_retried(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _make_openai_rate_limit_error()
            return "ok"

        result = await retry_with_backoff(flaky, FAST_CONFIG, "test")
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_openai_timeout_is_retried(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise openai.APITimeoutError(request=MagicMock())
            return "ok"

        result = await retry_with_backoff(flaky, FAST_CONFIG, "test")
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_anthropic_rate_limit_is_retried(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _make_anthropic_rate_limit_error()
            return "ok"

        result = await retry_with_backoff(flaky, FAST_CONFIG, "test")
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_anthropic_internal_server_error_is_retried(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _make_anthropic_internal_server_error()
            return "ok"

        result = await retry_with_backoff(flaky, FAST_CONFIG, "test")
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_exception_breaks_immediately(self):
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            await retry_with_backoff(always_fail, FAST_CONFIG, "test")

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_raises(self):
        config = RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.05, jitter=False)
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise _make_openai_rate_limit_error()

        with pytest.raises(openai.RateLimitError):
            await retry_with_backoff(always_fail, config, "test")

        # 1 initial + 2 retries = 3 total
        assert call_count == 3


# ---------------------------------------------------------------------------
# Retry-After header integration
# ---------------------------------------------------------------------------


class TestRetryAfterIntegration:
    @pytest.mark.asyncio
    async def test_retry_after_header_used_as_delay_floor(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _make_openai_rate_limit_error(retry_after="0.05")
            return "ok"

        config = RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.1, jitter=False)

        with patch("services.ai.utils.retry_handler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(flaky, config, "test")

        assert result == "ok"
        assert call_count == 2
        # Sleep was called at least once, and the delay should be >= 0.05 (Retry-After floor)
        mock_sleep.assert_called_once()
        actual_delay = mock_sleep.call_args[0][0]
        assert actual_delay >= 0.05


# ---------------------------------------------------------------------------
# Concurrency semaphore
# ---------------------------------------------------------------------------


class TestConcurrencySemaphore:
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """With semaphore=2, at most 2 tasks should run concurrently."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def track_concurrency():
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.05)
            async with lock:
                current_concurrent -= 1
            return "done"

        config = RetryConfig(max_retries=0, base_delay=0.01, max_delay=0.01)

        with patch("services.ai.utils.retry_handler.get_llm_semaphore") as mock_sem:
            mock_sem.return_value = asyncio.Semaphore(2)
            tasks = [retry_with_backoff(track_concurrency, config, f"task-{i}") for i in range(5)]
            results = await asyncio.gather(*tasks)

        assert all(r == "done" for r in results)
        assert max_concurrent <= 2


# ---------------------------------------------------------------------------
# RetryConfig.calculate_delay
# ---------------------------------------------------------------------------


class TestCalculateDelay:
    def test_exponential_growth(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=100.0, jitter=False)
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0

    def test_max_delay_cap(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False)
        assert config.calculate_delay(10) == 5.0

    def test_jitter_adds_variance(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=100.0, jitter=True)
        delays = [config.calculate_delay(2) for _ in range(20)]
        # Jitter should cause some variance
        assert len(set(delays)) > 1
        # All should be close to 4.0
        assert all(3.5 <= d <= 4.5 for d in delays)


# ---------------------------------------------------------------------------
# Semaphore event-loop safety (simulates Celery asyncio.run() pattern)
# ---------------------------------------------------------------------------


class TestSemaphoreLoopSafety:
    def test_semaphore_works_across_separate_event_loops(self):
        """Simulates Celery reusing a worker process for two consecutive tasks.

        Each ``asyncio.run()`` creates a new event loop.  The semaphore must
        work in both — a stale global singleton would crash on the second run.
        """
        from services.ai.utils.concurrency import _llm_semaphores, get_llm_semaphore

        async def use_semaphore():
            sem = get_llm_semaphore()
            async with sem:
                return "ok"

        result_1 = asyncio.run(use_semaphore())
        assert result_1 == "ok"

        # Second asyncio.run() — new loop; old semaphore must not be reused
        result_2 = asyncio.run(use_semaphore())
        assert result_2 == "ok"

        # Only the latest loop's semaphore should remain cached
        assert len(_llm_semaphores) == 1
