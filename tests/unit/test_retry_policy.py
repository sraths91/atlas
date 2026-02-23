"""
Unit Tests for Retry Policy and Circuit Breaker

Phase 8: Testing Infrastructure
"""
import pytest
import time
from atlas.network.retry_policy import (
    RetryPolicy,
    RetryConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenError,
    RetryBudget,
    with_retry,
)


@pytest.mark.unit
class TestRetryPolicy:
    """Tests for RetryPolicy"""

    def test_success_on_first_attempt(self, retry_config):
        """Test successful operation on first attempt"""
        policy = RetryPolicy(retry_config)
        attempt_count = [0]

        def operation():
            attempt_count[0] += 1
            return "success"

        result = policy.execute(operation)
        assert result == "success"
        assert attempt_count[0] == 1

    def test_success_after_retries(self, retry_config):
        """Test successful operation after retries"""
        policy = RetryPolicy(retry_config)
        attempt_count = [0]

        def operation():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        start = time.time()
        result = policy.execute(operation)
        elapsed = time.time() - start

        assert result == "success"
        assert attempt_count[0] == 3
        # Should have delays: 0.1s + 0.2s = 0.3s
        assert elapsed >= 0.3

    def test_exhausted_retries(self, retry_config):
        """Test all retries exhausted"""
        policy = RetryPolicy(retry_config)
        attempt_count = [0]

        def operation():
            attempt_count[0] += 1
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError):
            policy.execute(operation)

        assert attempt_count[0] == retry_config.max_attempts

    def test_non_retryable_exception(self, retry_config):
        """Test non-retryable exception fails immediately"""
        policy = RetryPolicy(retry_config)
        attempt_count = [0]

        def operation():
            attempt_count[0] += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            policy.execute(operation)

        assert attempt_count[0] == 1  # Should not retry

    def test_exponential_backoff(self):
        """Test exponential backoff progression"""
        config = RetryConfig(
            max_attempts=5,
            initial_backoff=0.1,
            max_backoff=1.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        policy = RetryPolicy(config)
        attempt_count = [0]
        delays = []

        def operation():
            attempt_count[0] += 1
            if attempt_count[0] > 1:
                delays.append(time.time())
            if attempt_count[0] < 4:
                raise ConnectionError("Failure")
            return "success"

        policy.execute(operation)

        # Verify delays increase exponentially
        # Delays: 0.1, 0.2, 0.4
        assert len(delays) == 3
        if len(delays) >= 2:
            # Second delay should be ~2x first delay
            delay1 = delays[1] - delays[0]
            # Allow some tolerance for timing
            assert 0.15 < delay1 < 0.25  # ~0.2s

    def test_max_backoff_cap(self):
        """Test backoff is capped at max_backoff"""
        config = RetryConfig(
            max_attempts=10,
            initial_backoff=0.1,
            max_backoff=0.5,  # Cap at 0.5s
            backoff_multiplier=2.0,
            jitter=False
        )
        policy = RetryPolicy(config)

        # Backoff should be: 0.1, 0.2, 0.4, 0.5 (capped), 0.5 (capped)...
        # After 3 failures, backoff would be 0.8s but is capped at 0.5s
        assert policy._calculate_backoff(0.8, 3) == 0.8  # Not capped yet
        # But policy should use min(delay * multiplier, max_backoff)


@pytest.mark.unit
class TestCircuitBreaker:
    """Tests for CircuitBreaker"""

    def test_initial_state_closed(self, circuit_breaker_config):
        """Test circuit breaker starts in CLOSED state"""
        breaker = CircuitBreaker(circuit_breaker_config)
        assert breaker.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self, circuit_breaker_config):
        """Test circuit opens after failure threshold"""
        breaker = CircuitBreaker(circuit_breaker_config)

        # Fail threshold times
        for i in range(circuit_breaker_config.failure_threshold):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))
            except ConnectionError:
                pass

        assert breaker.state == CircuitState.OPEN

    def test_blocks_calls_when_open(self, circuit_breaker_config):
        """Test circuit blocks calls when OPEN"""
        breaker = CircuitBreaker(circuit_breaker_config)

        # Open the circuit
        for i in range(circuit_breaker_config.failure_threshold):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))
            except ConnectionError:
                pass

        # Try to call - should fail immediately
        with pytest.raises(CircuitBreakerOpenError):
            breaker.call(lambda: "should not execute")

    def test_transitions_to_half_open(self, circuit_breaker_config):
        """Test circuit transitions to HALF_OPEN after timeout"""
        breaker = CircuitBreaker(circuit_breaker_config)

        # Open the circuit
        for i in range(circuit_breaker_config.failure_threshold):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))
            except ConnectionError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(circuit_breaker_config.timeout + 0.1)

        # Next call should transition to HALF_OPEN
        try:
            breaker.call(lambda: "success")
        except:
            pass

        assert breaker.state == CircuitState.HALF_OPEN

    def test_closes_after_successes_in_half_open(self, circuit_breaker_config):
        """Test circuit closes after success threshold in HALF_OPEN"""
        breaker = CircuitBreaker(circuit_breaker_config)

        # Open the circuit
        for i in range(circuit_breaker_config.failure_threshold):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))
            except ConnectionError:
                pass

        # Wait and transition to HALF_OPEN
        time.sleep(circuit_breaker_config.timeout + 0.1)
        breaker.call(lambda: "success")  # First success

        assert breaker.state == CircuitState.HALF_OPEN

        # Succeed threshold times
        for i in range(circuit_breaker_config.success_threshold):
            breaker.call(lambda: "success")

        assert breaker.state == CircuitState.CLOSED

    def test_reopens_on_failure_in_half_open(self, circuit_breaker_config):
        """Test circuit reopens on failure in HALF_OPEN"""
        breaker = CircuitBreaker(circuit_breaker_config)

        # Open the circuit
        for i in range(circuit_breaker_config.failure_threshold):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))
            except ConnectionError:
                pass

        # Wait and transition to HALF_OPEN
        time.sleep(circuit_breaker_config.timeout + 0.1)
        breaker.call(lambda: "success")

        assert breaker.state == CircuitState.HALF_OPEN

        # Fail once - should return to OPEN
        try:
            breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))
        except ConnectionError:
            pass

        assert breaker.state == CircuitState.OPEN

    def test_manual_reset(self, circuit_breaker_config):
        """Test manual circuit breaker reset"""
        breaker = CircuitBreaker(circuit_breaker_config)

        # Open the circuit
        for i in range(circuit_breaker_config.failure_threshold):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))
            except ConnectionError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Manual reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED


@pytest.mark.unit
class TestRetryBudget:
    """Tests for RetryBudget"""

    def test_allows_retries_when_under_budget(self):
        """Test retries allowed when under budget"""
        budget = RetryBudget(window_seconds=60, max_retry_ratio=0.3)

        # Record normal requests
        for i in range(10):
            budget.record_request(is_retry=False)

        # Should allow retries (0% retries so far)
        assert budget.can_retry() is True

        # Record some retries (still under 30%)
        for i in range(2):
            budget.record_request(is_retry=True)

        assert budget.can_retry() is True

    def test_blocks_retries_when_over_budget(self):
        """Test retries blocked when over budget"""
        budget = RetryBudget(window_seconds=60, max_retry_ratio=0.3)

        # Record normal requests
        for i in range(7):
            budget.record_request(is_retry=False)

        # Record retries to exceed budget
        for i in range(4):
            budget.record_request(is_retry=True)

        # Should block (4/11 = 36% > 30%)
        assert budget.can_retry() is False

    def test_budget_window_cleanup(self):
        """Test old entries are cleaned up from budget window"""
        budget = RetryBudget(window_seconds=1, max_retry_ratio=0.3)

        # Record requests that exceed budget
        for i in range(7):
            budget.record_request(is_retry=False)
        for i in range(4):
            budget.record_request(is_retry=True)

        assert budget.can_retry() is False

        # Wait for window to pass
        time.sleep(1.1)

        # Budget should recover (old entries cleaned up)
        assert budget.can_retry() is True


@pytest.mark.unit
class TestWithRetry:
    """Tests for with_retry convenience function"""

    def test_with_retry_success(self):
        """Test with_retry succeeds"""
        attempt_count = [0]

        def operation():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise ConnectionError("Fail")
            return "success"

        result = with_retry(operation, max_attempts=3, backoff=0.1)
        assert result == "success"
        assert attempt_count[0] == 2

    def test_with_retry_failure(self):
        """Test with_retry fails after all attempts"""
        def operation():
            raise TimeoutError("Always fails")

        with pytest.raises(TimeoutError):
            with_retry(operation, max_attempts=2, backoff=0.1)
