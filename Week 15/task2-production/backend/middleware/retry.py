"""
Retry Handler Module.

Implements exponential backoff retry logic for handling transient
failures when calling LLM providers and external services.
"""

import asyncio
import logging
import random
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Retry handler with exponential backoff and jitter.

    Handles transient failures by automatically retrying failed operations
    with configurable delay strategies.
    """

    # Exceptions that are considered retryable
    RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        OSError,
    )

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay cap in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.last_attempt_count = 0

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Full jitter: uniform random between 0 and calculated delay
            delay = random.uniform(0, delay)

        return delay

    def _is_retryable(self, exception: Exception) -> bool:
        """Check if an exception is retryable."""
        # Check against known retryable exceptions
        if isinstance(exception, self.RETRYABLE_EXCEPTIONS):
            return True

        # Check for HTTP-related retryable errors
        error_str = str(exception).lower()
        retryable_patterns = [
            "rate limit",
            "429",
            "500",
            "502",
            "503",
            "504",
            "timeout",
            "connection",
            "temporarily unavailable",
            "server error",
            "overloaded",
        ]
        return any(pattern in error_str for pattern in retryable_patterns)

    async def execute(
        self,
        func: Callable,
        *args,
        on_retry: Optional[Callable] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            on_retry: Optional callback called on each retry (attempt, exception)
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the successful function call.

        Raises:
            The last exception if all retries are exhausted.
        """
        last_exception = None
        self.last_attempt_count = 0

        for attempt in range(self.max_retries + 1):
            try:
                self.last_attempt_count = attempt
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_exception = e

                if attempt >= self.max_retries:
                    logger.error(
                        f"All {self.max_retries + 1} attempts failed. "
                        f"Last error: {e}"
                    )
                    raise

                if not self._is_retryable(e):
                    logger.error(f"Non-retryable error: {e}")
                    raise

                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                if on_retry:
                    on_retry(attempt + 1, e)

                await asyncio.sleep(delay)

        raise last_exception
