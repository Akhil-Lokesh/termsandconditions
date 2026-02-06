"""
Retry handler with exponential backoff for API calls.
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
