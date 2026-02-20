"""
Retry logic with exponential backoff for AWS operations.

This module provides decorators and utilities for retrying failed
operations with configurable backoff strategies.
"""

import asyncio
import functools
import logging
import random
from dataclasses import dataclass, field
from typing import Callable, Optional, Set, Type, TypeVar, Union

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: Set[str] = field(default_factory=lambda: {
        "ThrottlingException",
        "ServiceUnavailableException",
        "InternalServerException",
        "RequestTimeout",
        "ProvisionedThroughputExceededException",
    })
    retryable_exceptions: tuple = field(default_factory=lambda: (
        ConnectionError,
        TimeoutError,
    ))


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """
    Calculate delay for the next retry attempt.
    
    Uses exponential backoff with optional jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        
    Returns:
        Delay in seconds before next attempt
    """
    delay = min(
        config.base_delay * (config.exponential_base ** attempt),
        config.max_delay
    )
    
    if config.jitter:
        # Add random jitter between 0 and delay
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay


def is_retryable(
    error: Exception,
    config: RetryConfig,
) -> bool:
    """
    Check if an error is retryable.
    
    Args:
        error: The exception that occurred
        config: Retry configuration
        
    Returns:
        True if the error should be retried
    """
    # Check for retryable exception types
    if isinstance(error, config.retryable_exceptions):
        return True
    
    # Check for AWS ClientError with retryable error codes
    if isinstance(error, ClientError):
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in config.retryable_errors
    
    return False


def with_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """
    Decorator for adding retry logic to synchronous functions.
    
    Args:
        config: Retry configuration (uses defaults if not provided)
        on_retry: Optional callback called before each retry
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @with_retry(RetryConfig(max_attempts=5))
        def query_knowledge_base(query: str) -> str:
            # ... implementation
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error: Optional[Exception] = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    if not is_retryable(e, config):
                        logger.warning(
                            f"Non-retryable error in {func.__name__}: {e}"
                        )
                        raise
                    
                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"Retryable error in {func.__name__} "
                            f"(attempt {attempt + 1}/{config.max_attempts}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        
                        if on_retry:
                            on_retry(e, attempt)
                        
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Max retries exceeded for {func.__name__}: {e}"
                        )
            
            raise last_error
        
        return wrapper
    return decorator


def with_async_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """
    Decorator for adding retry logic to async functions.
    
    Args:
        config: Retry configuration (uses defaults if not provided)
        on_retry: Optional callback called before each retry
        
    Returns:
        Decorated async function with retry logic
        
    Example:
        @with_async_retry(RetryConfig(max_attempts=5))
        async def async_query(query: str) -> str:
            # ... implementation
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error: Optional[Exception] = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    if not is_retryable(e, config):
                        logger.warning(
                            f"Non-retryable error in {func.__name__}: {e}"
                        )
                        raise
                    
                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"Retryable error in {func.__name__} "
                            f"(attempt {attempt + 1}/{config.max_attempts}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        
                        if on_retry:
                            on_retry(e, attempt)
                        
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Max retries exceeded for {func.__name__}: {e}"
                        )
            
            raise last_error
        
        return wrapper
    return decorator
