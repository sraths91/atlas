"""
Pytest Configuration and Fixtures

Phase 8: Testing Infrastructure

Provides shared fixtures and configuration for all tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_machine_info() -> Dict[str, Any]:
    """Sample machine information for testing"""
    return {
        'hostname': 'test-machine',
        'os': 'Darwin',
        'os_version': '14.1.0',
        'architecture': 'arm64',
        'processor': 'Apple M1',
        'cpu_count': 8,
        'cpu_threads': 8,
        'total_memory': 17179869184,  # 16 GB
        'local_ip': '192.168.1.100'
    }


@pytest.fixture
def sample_metrics() -> Dict[str, Any]:
    """Sample system metrics for testing"""
    return {
        'cpu': {
            'percent': 45.2,
            'per_core': [40.0, 50.0, 45.0, 48.0, 42.0, 46.0, 44.0, 49.0]
        },
        'memory': {
            'total': 17179869184,
            'available': 8589934592,
            'percent': 50.0,
            'used': 8589934592
        },
        'disk': {
            'total': 1000000000000,  # 1 TB
            'used': 500000000000,    # 500 GB
            'free': 500000000000,
            'percent': 50.0
        },
        'network': {
            'bytes_sent': 1000000,
            'bytes_recv': 2000000,
            'packets_sent': 1000,
            'packets_recv': 2000
        }
    }


@pytest.fixture
def fleet_data_store():
    """Create a FleetDataStore instance for testing"""
    from atlas.fleet.server.data_store import FleetDataStore
    return FleetDataStore(history_size=100)


@pytest.fixture
def improved_data_store():
    """Create an ImprovedFleetDataStore instance for testing"""
    from atlas.fleet.server.improved_data_store import ImprovedFleetDataStore
    return ImprovedFleetDataStore(history_size=100)


@pytest.fixture
def retry_config():
    """Default retry configuration for testing"""
    from atlas.network.retry_policy import RetryConfig
    return RetryConfig(
        max_attempts=3,
        initial_backoff=0.1,
        max_backoff=1.0,
        backoff_multiplier=2.0,
        jitter=False,  # Disable for deterministic tests
        retry_on_exceptions=(ConnectionError, TimeoutError)
    )


@pytest.fixture
def circuit_breaker_config():
    """Default circuit breaker configuration for testing"""
    from atlas.network.retry_policy import CircuitBreakerConfig
    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=0.5,
        half_open_max_calls=2
    )


# Test markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, multiple components)"
    )
    config.addinivalue_line(
        "markers", "security: Security tests (vulnerability scanning)"
    )
    config.addinivalue_line(
        "markers", "performance: Performance benchmarks"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full workflows)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (skip with -m 'not slow')"
    )
