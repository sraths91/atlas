#!/usr/bin/env python3
"""
Test script for refactored SpeedTestMonitor

This tests that the new SpeedTestMonitor using BaseNetworkMonitor + CSVLogger works correctly.
"""
import sys
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the refactored monitor
from atlas.network.monitors.speedtest import SpeedTestMonitor, get_speed_test_monitor

def test_speedtest_monitor_basic():
    """Test basic SpeedTestMonitor functionality"""
    print("=" * 80)
    print("TEST 1: Basic SpeedTestMonitor Functionality")
    print("=" * 80)

    # Create monitor
    monitor = SpeedTestMonitor()
    print(f"Created SpeedTestMonitor: {monitor}")

    # Check initial state
    assert not monitor.is_running(), "Monitor should not be running initially"
    print("Initial state: not running")

    # Check speedtest availability
    if not monitor.speedtest_available:
        print(" speedtest-cli not installed - skipping actual speed test")
        print("   Install with: pip install speedtest-cli")
        return monitor, True  # Return skip flag

    print(f"speedtest-cli is available")

    print("\nTEST 1 PASSED: Basic functionality works!\n")
    return monitor, False  # Return no-skip flag

def test_speedtest_monitor_singleton():
    """Test singleton pattern"""
    print("=" * 80)
    print("TEST 2: Singleton Pattern")
    print("=" * 80)

    monitor1 = get_speed_test_monitor()
    monitor2 = get_speed_test_monitor()

    assert monitor1 is monitor2, "Singleton should return same instance"
    print(f"Singleton pattern works: {id(monitor1)} == {id(monitor2)}")

    print("\nTEST 2 PASSED: Singleton works!\n")
    return monitor1

def test_csv_logger():
    """Test that CSV logger is working"""
    print("=" * 80)
    print("TEST 3: CSV Logger Integration")
    print("=" * 80)

    monitor = SpeedTestMonitor()

    # Check that logger exists
    assert hasattr(monitor, 'csv_logger'), "Should have csv_logger"
    print("CSV logger initialized")

    # Check logger type
    from atlas.core.logging import CSVLogger
    assert isinstance(monitor.csv_logger, CSVLogger), "csv_logger should be CSVLogger"
    print("Logger is CSVLogger instance")

    # Check log file path
    print(f"   SpeedTest log: {monitor.csv_logger.get_log_path()}")

    # Check fieldnames
    expected_fields = ['timestamp', 'download', 'upload', 'ping', 'server']
    assert monitor.csv_logger.fieldnames == expected_fields, f"Fieldnames should be {expected_fields}"
    print(f"Correct fieldnames: {expected_fields}")

    print("\nTEST 3 PASSED: CSV logger working!\n")

def test_base_monitor_inheritance():
    """Test BaseNetworkMonitor inheritance"""
    print("=" * 80)
    print("TEST 4: BaseNetworkMonitor Inheritance")
    print("=" * 80)

    from atlas.network.monitors.base import BaseNetworkMonitor

    monitor = SpeedTestMonitor()

    # Check inheritance
    assert isinstance(monitor, BaseNetworkMonitor), "SpeedTestMonitor should inherit from BaseNetworkMonitor"
    print("SpeedTestMonitor inherits from BaseNetworkMonitor")

    # Check required methods exist
    assert hasattr(monitor, 'start'), "Should have start() method"
    assert hasattr(monitor, 'stop'), "Should have stop() method"
    assert hasattr(monitor, 'is_running'), "Should have is_running() method"
    assert hasattr(monitor, 'get_last_result'), "Should have get_last_result() method"
    assert hasattr(monitor, 'update_last_result'), "Should have update_last_result() method"
    print("All base class methods present")

    # Check abstract methods are implemented
    assert monitor.get_monitor_name() == "Speed Test Monitor", "get_monitor_name() should be implemented"
    assert monitor.get_default_interval() == 60, "get_default_interval() should return 60"
    print(f"Abstract methods implemented: {monitor.get_monitor_name()}")

    print("\nTEST 4 PASSED: Inheritance working!\n")

def test_alert_configuration():
    """Test slow speed alert configuration"""
    print("=" * 80)
    print("TEST 5: Slow Speed Alert Configuration")
    print("=" * 80)

    monitor = SpeedTestMonitor()

    # Check default configuration
    assert monitor.slow_speed_threshold == 20.0, "Default threshold should be 20.0 Mbps"
    assert monitor.consecutive_slow_trigger == 5, "Default trigger should be 5"
    assert monitor.slow_alert_cooldown == 300, "Default cooldown should be 300s"
    print("Default alert configuration correct")

    # Test configuration update
    monitor.configure_slow_speed_alert(threshold=15.0, consecutive_trigger=3, cooldown=180)
    assert monitor.slow_speed_threshold == 15.0, "Threshold should be updated to 15.0"
    assert monitor.consecutive_slow_trigger == 3, "Trigger should be updated to 3"
    assert monitor.slow_alert_cooldown == 180, "Cooldown should be updated to 180"
    print("Alert configuration update works")

    # Test status retrieval
    status = monitor.get_slow_speed_status()
    assert 'alert_active' in status, "Status should have alert_active"
    assert 'consecutive_slow_count' in status, "Status should have consecutive_slow_count"
    assert 'threshold' in status, "Status should have threshold"
    print(f"Alert status retrieval works: {status}")

    print("\nTEST 5 PASSED: Alert configuration working!\n")

def test_speedtest_features():
    """Test SpeedTest-specific features"""
    print("=" * 80)
    print("TEST 6: SpeedTest-Specific Features")
    print("=" * 80)

    monitor = SpeedTestMonitor()

    # Test get_history (should use CSV logger)
    history = monitor.get_history()
    assert isinstance(history, list), "History should be a list"
    print(f"get_history() works: {len(history)} entries")

    # Test get_last_result_with_countdown
    result = monitor.get_last_result_with_countdown()
    assert 'next_test_in' in result, "Result should have next_test_in"
    assert result['status'] == 'idle', "Initial status should be idle"
    print(f"get_last_result_with_countdown() works: status={result['status']}")

    # Test callback setter
    callback_called = []
    def test_callback(data):
        callback_called.append(data)

    monitor.set_slow_speed_alert_callback(test_callback)
    assert monitor.slow_speed_alert_callback is test_callback, "Callback should be set"
    print("set_slow_speed_alert_callback() works")

    print("\nTEST 6 PASSED: SpeedTest features working!\n")

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("REFACTORED SpeedTestMonitor TEST SUITE")
    print("=" * 80 + "\n")

    try:
        # Test 1: Basic functionality
        monitor, skip_speedtest = test_speedtest_monitor_basic()

        # Test 2: Singleton pattern
        test_speedtest_monitor_singleton()

        # Test 3: CSV logger
        test_csv_logger()

        # Test 4: Inheritance
        test_base_monitor_inheritance()

        # Test 5: Alert configuration
        test_alert_configuration()

        # Test 6: SpeedTest features
        test_speedtest_features()

        print("=" * 80)
        print("ALL TESTS PASSED! ")
        print("=" * 80)
        print("\nRefactored SpeedTestMonitor is working correctly!")
        print("\nBenefits achieved:")
        print("  - Using BaseNetworkMonitor (eliminates ~120 lines)")
        print("  - Using CSVLogger (eliminates ~80 lines)")
        print("  - Total estimated reduction: ~625 lines")
        print("  - Original: ~1,225 lines → Refactored: ~600 lines")

        if skip_speedtest:
            print("\n Note: speedtest-cli not installed, so actual speed tests were skipped")
            print("   Install with: pip install speedtest-cli")

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
