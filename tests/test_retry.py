"""
Tests for retry logic.
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from shared.retry import (
    RetryConfig,
    calculate_delay,
    is_retryable,
    with_retry,
)


class TestRetryConfig:
    """Tests for RetryConfig."""
    
    def test_default_values(self):
        """Default configuration should have sensible defaults."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.jitter is True
        assert "ThrottlingException" in config.retryable_errors


class TestCalculateDelay:
    """Tests for calculate_delay function."""
    
    def test_exponential_backoff(self):
        """Delay should increase exponentially."""
        config = RetryConfig(jitter=False, base_delay=1.0, exponential_base=2.0)
        
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0
        assert calculate_delay(3, config) == 8.0
    
    def test_max_delay_cap(self):
        """Delay should be capped at max_delay."""
        config = RetryConfig(jitter=False, base_delay=1.0, max_delay=5.0)
        
        assert calculate_delay(10, config) == 5.0
    
    def test_jitter_adds_randomness(self):
        """Jitter should add randomness to delay."""
        config = RetryConfig(jitter=True, base_delay=1.0)
        
        # Run multiple times and check for variation
        delays = [calculate_delay(0, config) for _ in range(10)]
        assert len(set(delays)) > 1  # Should have variation


class TestIsRetryable:
    """Tests for is_retryable function."""
    
    def test_throttling_exception_is_retryable(self):
        """ThrottlingException should be retryable."""
        config = RetryConfig()
        error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "TestOperation",
        )
        assert is_retryable(error, config) is True
    
    def test_access_denied_not_retryable(self):
        """AccessDeniedException should not be retryable."""
        config = RetryConfig()
        error = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "TestOperation",
        )
        assert is_retryable(error, config) is False
    
    def test_connection_error_is_retryable(self):
        """ConnectionError should be retryable."""
        config = RetryConfig()
        error = ConnectionError("Connection failed")
        assert is_retryable(error, config) is True
    
    def test_timeout_error_is_retryable(self):
        """TimeoutError should be retryable."""
        config = RetryConfig()
        error = TimeoutError("Request timed out")
        assert is_retryable(error, config) is True
    
    def test_value_error_not_retryable(self):
        """ValueError should not be retryable."""
        config = RetryConfig()
        error = ValueError("Invalid value")
        assert is_retryable(error, config) is False


class TestWithRetry:
    """Tests for with_retry decorator."""
    
    def test_success_on_first_attempt(self):
        """Function should return immediately on success."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3))
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_retryable_error(self):
        """Function should retry on retryable errors."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert call_count == 3
    
    def test_no_retry_on_non_retryable_error(self):
        """Function should not retry on non-retryable errors."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3))
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid value")
        
        with pytest.raises(ValueError):
            failing_func()
        
        assert call_count == 1
    
    def test_max_retries_exceeded(self):
        """Function should raise after max retries."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            always_fails()
        
        assert call_count == 3
    
    def test_on_retry_callback(self):
        """on_retry callback should be called before each retry."""
        retry_calls = []
        
        def on_retry(error, attempt):
            retry_calls.append((str(error), attempt))
        
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01), on_retry=on_retry)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert len(retry_calls) == 2
        assert retry_calls[0][1] == 0  # First retry attempt
        assert retry_calls[1][1] == 1  # Second retry attempt
