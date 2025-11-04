"""
Retry handler with exponential backoff for API calls.

Handles OpenAI API errors with intelligent retry logic:
- RateLimitError: Exponential backoff
- TimeoutError: Immediate retry (max 2)
- APIError: Log and escalate
"""

import time
import asyncio
from typing import Callable, Any, TypeVar, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def calculate_backoff(attempt: int, config: RetryConfig) -> float:
    """
    Calculate exponential backoff with jitter.

    Args:
        attempt: Current retry attempt (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    delay = min(
        config.initial_delay * (config.exponential_base**attempt), config.max_delay
    )

    # Add jitter to prevent thundering herd
    if config.jitter:
        import random

        delay = delay * (0.5 + random.random() * 0.5)

    return delay


def with_retry(
    config: Optional[RetryConfig] = None,
    retry_on: tuple = (Exception,),
    log_retries: bool = True,
):
    """
    Decorator for adding retry logic to async functions.

    Args:
        config: Retry configuration
        retry_on: Tuple of exceptions to retry on
        log_retries: Whether to log retry attempts

    Example:
        @with_retry(config=RetryConfig(max_retries=3))
        async def call_api():
            return await client.chat.completions.create(...)
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except retry_on as e:
                    last_exception = e

                    if attempt >= config.max_retries:
                        if log_retries:
                            logger.error(
                                f"{func.__name__} failed after {config.max_retries} retries: {e}"
                            )
                        raise

                    # Calculate backoff
                    delay = calculate_backoff(attempt, config)

                    if log_retries:
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )

                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class OpenAIRetryHandler:
    """
    Specialized retry handler for OpenAI API calls.

    Handles different error types with appropriate strategies:
    - RateLimitError: Exponential backoff with long delays
    - Timeout: Quick retry
    - APIError: Log and fail fast
    - Other errors: Standard retry
    """

    def __init__(self):
        self.rate_limit_config = RetryConfig(
            max_retries=5, initial_delay=2.0, max_delay=120.0, exponential_base=2.0
        )

        self.timeout_config = RetryConfig(
            max_retries=2, initial_delay=0.5, max_delay=2.0, exponential_base=1.5
        )

        self.standard_config = RetryConfig(
            max_retries=3, initial_delay=1.0, max_delay=30.0, exponential_base=2.0
        )

    async def call_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with intelligent retry based on error type.

        Detects error type and applies appropriate retry strategy.
        """
        last_exception = None
        config = self.standard_config

        for attempt in range(config.max_retries + 1):
            try:
                return await func(*args, **kwargs)

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                # Determine retry strategy based on error type
                if "RateLimitError" in error_type:
                    config = self.rate_limit_config
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}). " f"Backing off..."
                    )

                elif "Timeout" in error_type:
                    config = self.timeout_config
                    logger.warning(
                        f"Timeout (attempt {attempt + 1}). " f"Quick retry..."
                    )

                elif "APIError" in error_type or "APIConnectionError" in error_type:
                    # API errors usually mean something is wrong with the request
                    # Don't retry as aggressively
                    logger.error(f"API error: {e}")
                    if attempt >= 1:  # Only retry once for API errors
                        raise

                else:
                    # Unknown error - use standard retry
                    logger.warning(f"Unknown error type: {error_type}: {e}")

                # Check if we've exhausted retries for this config
                if attempt >= config.max_retries:
                    logger.error(
                        f"Function failed after {config.max_retries} retries: {e}"
                    )
                    raise

                # Calculate and apply backoff
                delay = calculate_backoff(attempt, config)
                logger.info(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

        # Should never reach here
        if last_exception:
            raise last_exception


# Global retry handler instance
openai_retry_handler = OpenAIRetryHandler()


async def call_openai_with_retry(func: Callable, *args, **kwargs) -> Any:
    """
    Convenience function for calling OpenAI API with retry.

    Example:
        response = await call_openai_with_retry(
            client.chat.completions.create,
            model="gpt-5",
            messages=[...]
        )
    """
    return await openai_retry_handler.call_with_retry(func, *args, **kwargs)
