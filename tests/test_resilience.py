"""Tests for resilience patterns (retry and circuit breaker)."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cloud_resource_inefficiency.core.resilience import (
    CircuitBreaker,
    CircuitBreakerException,
    circuit_breaker,
    retry,
)


class TestRetryDecorator:
    """Tests for @retry decorator."""

    def test_retry_succeeds_on_first_attempt(self) -> None:
        """Retry should succeed on first attempt without delay."""
        mock_func = MagicMock(return_value="success")

        @retry(max_attempts=3)
        def test_func() -> str:
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_succeeds_after_failure(self) -> None:
        """Retry should succeed after retrying failed attempts."""
        mock_func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

        @retry(max_attempts=3, base_delay=0.01)
        def test_func() -> str:
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_exhausts_attempts(self) -> None:
        """Retry should raise exception after exhausting attempts."""
        mock_func = MagicMock(side_effect=ValueError("always fails"))

        @retry(max_attempts=2, base_delay=0.01)
        def test_func() -> None:
            return mock_func()

        with pytest.raises(ValueError, match="always fails"):
            test_func()

        assert mock_func.call_count == 2

    def test_retry_exponential_backoff(self) -> None:
        """Retry should use exponential backoff between attempts."""
        mock_func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

        start_time = time.time()

        @retry(max_attempts=3, base_delay=0.05, backoff_factor=2.0)
        def test_func() -> str:
            return mock_func()

        result = test_func()
        elapsed = time.time() - start_time

        assert result == "success"
        # Should have ~0.05 + ~0.1 = 0.15 seconds of delay minimum
        assert elapsed >= 0.13

    def test_retry_with_specific_exceptions(self) -> None:
        """Retry should only retry on specified exceptions."""
        mock_func = MagicMock(side_effect=RuntimeError("not retryable"))

        @retry(max_attempts=3, exceptions={ValueError})
        def test_func() -> None:
            return mock_func()

        with pytest.raises(RuntimeError):
            test_func()

        # Should only be called once since RuntimeError is not in exceptions set
        assert mock_func.call_count == 1

    def test_retry_max_delay_capped(self) -> None:
        """Retry backoff delay should not exceed max_delay."""
        call_times = []

        @retry(max_attempts=5, base_delay=1.0, max_delay=2.0, backoff_factor=2.0)
        def test_func() -> None:
            call_times.append(time.time())
            if len(call_times) < 5:
                raise ValueError("retry me")

        test_func()

        # Check that delays don't exceed max_delay
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i - 1]
            assert delay <= 2.5  # Some tolerance for execution time


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_circuit_breaker_succeeds_initially(self) -> None:
        """Circuit breaker should allow calls when closed."""
        breaker = CircuitBreaker(failure_threshold=3)
        func = MagicMock(return_value="ok")

        result = breaker.call(func)
        assert result == "ok"
        assert not breaker.is_open

    def test_circuit_breaker_opens_after_failures(self) -> None:
        """Circuit breaker should open after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=2)
        func = MagicMock(side_effect=ValueError("fail"))

        # First failure
        with pytest.raises(ValueError):
            breaker.call(func)
        assert not breaker.is_open

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            breaker.call(func)
        assert breaker.is_open

    def test_circuit_breaker_raises_when_open(self) -> None:
        """Circuit breaker should raise CircuitBreakerException when open."""
        breaker = CircuitBreaker(failure_threshold=1)
        func = MagicMock(side_effect=ValueError("fail"))

        # Open the circuit
        with pytest.raises(ValueError):
            breaker.call(func)

        # Next call should raise CircuitBreakerException
        with pytest.raises(CircuitBreakerException):
            breaker.call(func)

    def test_circuit_breaker_resets_on_success(self) -> None:
        """Circuit breaker should reset failure count on success."""
        breaker = CircuitBreaker(failure_threshold=3)
        func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok", "ok"])

        with pytest.raises(ValueError):
            breaker.call(func)
        assert breaker.failure_count == 1

        with pytest.raises(ValueError):
            breaker.call(func)
        assert breaker.failure_count == 2

        result = breaker.call(func)
        assert result == "ok"
        assert breaker.failure_count == 0  # Reset

    def test_circuit_breaker_recovery_timeout(self) -> None:
        """Circuit breaker should attempt recovery after timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        func = MagicMock(side_effect=[ValueError("fail"), "ok"])

        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(func)
        assert breaker.is_open

        # Try immediately - should still raise CircuitBreakerException
        with pytest.raises(CircuitBreakerException):
            breaker.call(func)

        # Wait for recovery timeout
        time.sleep(0.1)

        # Should attempt recovery and succeed
        result = breaker.call(func)
        assert result == "ok"
        assert not breaker.is_open


class TestCircuitBreakerDecorator:
    """Tests for @circuit_breaker decorator."""

    def test_circuit_breaker_decorator_works(self) -> None:
        """Circuit breaker decorator should protect functions."""
        call_count = {"value": 0}

        @circuit_breaker(failure_threshold=2, name="test_breaker")
        def failing_func() -> None:
            call_count["value"] += 1
            raise ValueError("fail")

        # First two failures
        with pytest.raises(ValueError):
            failing_func()
        with pytest.raises(ValueError):
            failing_func()

        # Circuit should now be open
        with pytest.raises(CircuitBreakerException):
            failing_func()

    def test_circuit_breaker_decorator_with_success(self) -> None:
        """Circuit breaker decorator should allow successful calls."""
        @circuit_breaker(failure_threshold=3)
        def test_func() -> str:
            return "success"

        result = test_func()
        assert result == "success"

    def test_circuit_breaker_decorator_multiple_instances(self) -> None:
        """Each decorated function should have its own circuit breaker."""
        @circuit_breaker(failure_threshold=1, name="breaker1")
        def func1() -> None:
            raise ValueError("fail")

        @circuit_breaker(failure_threshold=1, name="breaker2")
        def func2() -> str:
            return "ok"

        # Open breaker for func1
        with pytest.raises(ValueError):
            func1()

        # func2 should still work
        result = func2()
        assert result == "ok"


class TestRetryWithCircuitBreaker:
    """Tests for combining retry and circuit breaker."""

    def test_retry_then_circuit_breaker(self) -> None:
        """Retry decorator followed by circuit breaker."""
        call_count = {"value": 0}

        @circuit_breaker(failure_threshold=2, name="retry_cb_test")
        @retry(max_attempts=2, base_delay=0.01)
        def test_func() -> None:
            call_count["value"] += 1
            raise ValueError("always fails")

        # First invocation triggers retry (2 attempts), both fail
        with pytest.raises(ValueError):
            test_func()
        assert call_count["value"] == 2

        # Second invocation triggers retry (2 more attempts), both fail
        # This reaches the circuit breaker threshold
        with pytest.raises(ValueError):
            test_func()
        assert call_count["value"] == 4

        # Third invocation should hit open circuit breaker
        with pytest.raises(CircuitBreakerException):
            test_func()
        assert call_count["value"] == 4  # No new attempt


class TestCircuitBreakerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_circuit_breaker_with_custom_name(self) -> None:
        """Circuit breaker should accept custom name."""
        breaker = CircuitBreaker(name="custom_name")
        assert breaker.name == "custom_name"

    def test_circuit_breaker_last_failure_time_tracking(self) -> None:
        """Circuit breaker should track last failure time."""
        breaker = CircuitBreaker(failure_threshold=1)
        func = MagicMock(side_effect=ValueError("fail"))

        assert breaker.last_failure_time is None

        with pytest.raises(ValueError):
            breaker.call(func)

        assert breaker.last_failure_time is not None

    def test_retry_preserves_function_name(self) -> None:
        """Retry decorator should preserve original function name."""
        @retry(max_attempts=1)
        def my_function() -> str:
            return "test"

        assert my_function.__name__ == "my_function"

    def test_circuit_breaker_preserves_function_name(self) -> None:
        """Circuit breaker decorator should preserve original function name."""
        @circuit_breaker()
        def my_function() -> str:
            return "test"

        assert my_function.__name__ == "my_function"
