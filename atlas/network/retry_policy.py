"""
Retry Policy and Circuit Breaker for Fleet Agent

Phase 7: Thread Safety and Concurrency Improvements

This module provides intelligent retry logic with:
- Exponential backoff with jitter
- Circuit breaker pattern
- Retry budget tracking
- Request-specific retry strategies

Prevents:
- Retry storms
- Cascading failures
- Resource exhaustion
"""
import time
import random
import logging
import threading
from enum import Enum
from typing import Callable, Optional, Any, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Too many failures, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_backoff: float = 1.0  # seconds
    max_backoff: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retry_on_exceptions: tuple = (ConnectionError, TimeoutError)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes in half-open to close circuit
    timeout: float = 60.0  # Seconds before trying half-open
    half_open_max_calls: int = 3  # Max concurrent calls in half-open state


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation.

    Prevents cascading failures by:
    1. CLOSED: Normal operation
    2. OPEN: After threshold failures, block all requests
    3. HALF_OPEN: After timeout, allow limited requests to test recovery
    4. Back to CLOSED: If test requests succeed
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker

        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    def call(self, func: Callable[[], T]) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function raises exception
        """
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info("Circuit breaker: Transitioning from OPEN to HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is OPEN - too many failures")

            # Check if we're in HALF_OPEN and at max concurrent calls
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError("Circuit breaker is HALF_OPEN - max concurrent calls reached")
                self._half_open_calls += 1

        # Execute function
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
        finally:
            # Decrement half-open calls counter
            if self._state == CircuitState.HALF_OPEN:
                with self._lock:
                    self._half_open_calls -= 1

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self._last_failure_time is None:
            return True
        elapsed = datetime.now() - self._last_failure_time
        return elapsed.total_seconds() >= self.config.timeout

    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(f"Circuit breaker: Success in HALF_OPEN state ({self._success_count}/{self.config.success_threshold})")

                if self._success_count >= self.config.success_threshold:
                    logger.info("Circuit breaker: Transitioning from HALF_OPEN to CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0

            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success in CLOSED state
                if self._failure_count > 0:
                    self._failure_count = 0

    def _on_failure(self, exception: Exception):
        """Handle failed call"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker: Failure in HALF_OPEN state - returning to OPEN")
                self._state = CircuitState.OPEN
                self._success_count = 0

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    logger.error(f"Circuit breaker: Failure threshold reached ({self._failure_count}) - transitioning to OPEN")
                    self._state = CircuitState.OPEN
                else:
                    logger.warning(f"Circuit breaker: Failure {self._failure_count}/{self.config.failure_threshold}")

    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        with self._lock:
            logger.info("Circuit breaker: Manual reset to CLOSED state")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class RetryPolicy:
    """
    Intelligent retry policy with exponential backoff and jitter.

    Features:
    - Exponential backoff: delay *= multiplier each retry
    - Jitter: Randomize delay to prevent retry storms
    - Max backoff: Cap maximum delay
    - Selective retries: Only retry specific exceptions
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry policy

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()

    def execute(self, func: Callable[[], T]) -> T:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute (no arguments)

        Returns:
            Function result

        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        delay = self.config.initial_backoff

        for attempt in range(self.config.max_attempts):
            try:
                result = func()
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt + 1}/{self.config.max_attempts}")
                return result

            except Exception as e:
                last_exception = e

                # Check if exception is retryable
                if not self._should_retry(e):
                    logger.warning(f"Non-retryable exception: {type(e).__name__}: {e}")
                    raise

                # Check if we have retries left
                if attempt >= self.config.max_attempts - 1:
                    logger.error(f"All {self.config.max_attempts} retry attempts exhausted")
                    raise

                # Calculate backoff delay
                actual_delay = self._calculate_backoff(delay, attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{self.config.max_attempts} failed: {type(e).__name__}: {str(e)[:100]}"
                    f" - Retrying in {actual_delay:.2f}s"
                )

                # Wait before retry
                time.sleep(actual_delay)

                # Increase delay for next retry
                delay = min(delay * self.config.backoff_multiplier, self.config.max_backoff)

        # Should not reach here, but raise last exception if we do
        if last_exception:
            raise last_exception

    def _should_retry(self, exception: Exception) -> bool:
        """Check if exception should trigger retry"""
        return isinstance(exception, self.config.retry_on_exceptions)

    def _calculate_backoff(self, base_delay: float, attempt: int) -> float:
        """Calculate backoff delay with optional jitter"""
        if self.config.jitter:
            # Add random jitter: ±25% of delay
            jitter_factor = 1.0 + (random.random() - 0.5) * 0.5
            return base_delay * jitter_factor
        return base_delay


class RetryBudget:
    """
    Track retry budget to prevent retry storms.

    Limits the percentage of requests that can be retries over a time window.
    If retry budget is exhausted, fail fast instead of retrying.
    """

    def __init__(self, window_seconds: int = 60, max_retry_ratio: float = 0.3):
        """Initialize retry budget

        Args:
            window_seconds: Time window for tracking retries
            max_retry_ratio: Maximum ratio of retries to total requests (0.0-1.0)
        """
        self.window_seconds = window_seconds
        self.max_retry_ratio = max_retry_ratio
        self._requests: list = []  # (timestamp, is_retry)
        self._lock = threading.Lock()

    def can_retry(self) -> bool:
        """Check if retry budget allows another retry"""
        with self._lock:
            self._cleanup_old_entries()

            if not self._requests:
                return True

            # Count retries vs total requests
            retries = sum(1 for _, is_retry in self._requests if is_retry)
            total = len(self._requests)

            retry_ratio = retries / total if total > 0 else 0
            can_retry = retry_ratio < self.max_retry_ratio

            if not can_retry:
                logger.warning(
                    f"Retry budget exhausted: {retries}/{total} requests are retries "
                    f"({retry_ratio:.1%} >= {self.max_retry_ratio:.1%})"
                )

            return can_retry

    def record_request(self, is_retry: bool = False):
        """Record a request in the budget"""
        with self._lock:
            self._requests.append((time.time(), is_retry))
            self._cleanup_old_entries()

    def _cleanup_old_entries(self):
        """Remove entries outside the time window"""
        cutoff = time.time() - self.window_seconds
        self._requests = [(ts, is_retry) for ts, is_retry in self._requests if ts >= cutoff]


# Convenience function for simple retry
def with_retry(func: Callable[[], T],
               max_attempts: int = 3,
               backoff: float = 1.0,
               exceptions: tuple = (ConnectionError, TimeoutError)) -> T:
    """
    Simple retry wrapper function.

    Args:
        func: Function to execute
        max_attempts: Maximum retry attempts
        backoff: Initial backoff delay in seconds
        exceptions: Tuple of exception types to retry

    Returns:
        Function result

    Example:
        >>> result = with_retry(lambda: risky_operation(), max_attempts=5)
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_backoff=backoff,
        retry_on_exceptions=exceptions
    )
    policy = RetryPolicy(config)
    return policy.execute(func)


# Export public API
__all__ = [
    'RetryPolicy',
    'RetryConfig',
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitState',
    'CircuitBreakerOpenError',
    'RetryBudget',
    'with_retry',
]
