"""Resilience patterns: retry with exponential backoff and circuit breaker."""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Set, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerException(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.

    Tracks consecutive failures and opens the circuit after a threshold.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: Optional[str] = None,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening.
            recovery_timeout: Seconds to wait before attempting to close.
            name: Optional name for logging.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name or "CircuitBreaker"
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.is_open = False

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func execution.

        Raises:
            CircuitBreakerException: If circuit is open.
        """
        # Check if we should attempt recovery
        if self.is_open:
            if self._should_attempt_recovery():
                logger.info("CircuitBreaker %s: attempting recovery", self.name)
                self.is_open = False
                self.failure_count = 0
            else:
                raise CircuitBreakerException(f"CircuitBreaker {self.name} is open")

        try:
            result = func(*args, **kwargs)
            # Success - reset failures
            if self.failure_count > 0:
                logger.info("CircuitBreaker %s: resetting after success", self.name)
            self.failure_count = 0
            self.last_failure_time = None
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                logger.warning(
                    "CircuitBreaker %s: opening circuit after %d failures",
                    self.name,
                    self.failure_count,
                )

            raise

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return False

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout


# Global circuit breakers registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    name: Optional[str] = None,
    exceptions: Optional[Set[Type[Exception]]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add circuit breaker pattern to a function.

    Args:
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to wait before attempting recovery.
        name: Optional name for circuit breaker (defaults to function name).
        exceptions: Set of exception types to catch (defaults to Exception).

    Returns:
        Decorated function with circuit breaker.
    """
    if exceptions is None:
        exceptions = {Exception}

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker_name = name or f"{func.__module__}.{func.__name__}"

        if breaker_name not in _circuit_breakers:
            _circuit_breakers[breaker_name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                name=breaker_name,
            )

        breaker = _circuit_breakers[breaker_name]

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerException:
                raise
            except tuple(exceptions) as e:
                raise
            except Exception:
                # Re-raise non-matching exceptions without going through circuit breaker
                raise

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 32.0,
    backoff_factor: float = 2.0,
    exceptions: Optional[Set[Type[Exception]]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add exponential backoff retry logic to a function.

    Args:
        max_attempts: Maximum number of attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        backoff_factor: Multiplier for delay between attempts.
        exceptions: Set of exception types to retry on (defaults to Exception).

    Returns:
        Decorated function with retry logic.

    Example:
        @retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0)
        def fetch_data():
            return api.call()
    """
    if exceptions is None:
        exceptions = {Exception}

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            delay = base_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(
                        "Attempting %s (attempt %d/%d)",
                        func.__name__,
                        attempt,
                        max_attempts,
                    )
                    return func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    if attempt < max_attempts:
                        # Calculate delay with exponential backoff
                        delay = min(delay * backoff_factor, max_delay)
                        logger.warning(
                            "Attempt %d/%d failed for %s: %s. Retrying in %.1f seconds...",
                            attempt,
                            max_attempts,
                            func.__name__,
                            str(e),
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All %d attempts failed for %s",
                            max_attempts,
                            func.__name__,
                        )

            if last_exception:
                raise last_exception
            raise RuntimeError(f"Unexpected error in retry decorator for {func.__name__}")

        return wrapper

    return decorator
