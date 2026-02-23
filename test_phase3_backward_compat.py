#!/usr/bin/env python3
"""
Test Phase 3: Backward Compatibility

This tests that the old widget imports still work after migration to refactored monitors.
"""
import sys
import warnings
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("PHASE 3: BACKWARD COMPATIBILITY TEST")
print("=" * 80)
print()

# Capture deprecation warnings
warnings.simplefilter('always', DeprecationWarning)

def test_wifi_widget_backward_compat():
    """Test that old WiFi widget imports still work"""
    print("TEST 1: WiFi Widget Backward Compatibility")
    print("-" * 80)

    try:
        # This should work but show a deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from atlas.wifi_widget import (
                WiFiMonitor,
                get_wifi_monitor,
                get_wifi_widget_html,
                NetworkDiagnostics
            )

            # Check that deprecation warning was issued
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            print(f"Deprecation warning issued: {w[0].message}")

        # Test that the classes/functions work
        monitor = get_wifi_monitor()
        assert monitor is not None
        assert isinstance(monitor, WiFiMonitor)
        print(f"get_wifi_monitor() works: {type(monitor).__name__}")

        # Test HTML function
        html = get_wifi_widget_html()
        assert html is not None
        assert len(html) > 0
        assert "WiFi" in html
        print(f"get_wifi_widget_html() works ({len(html)} chars)")

        # Test NetworkDiagnostics
        assert NetworkDiagnostics is not None
        print(f"NetworkDiagnostics class available")

        print("TEST 1 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 1 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_speedtest_widget_backward_compat():
    """Test that old SpeedTest widget imports still work"""
    print("TEST 2: SpeedTest Widget Backward Compatibility")
    print("-" * 80)

    try:
        # This should work but show a deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from atlas.speedtest_widget import (
                SpeedTestMonitor,
                get_speed_test_monitor,
                get_speedtest_widget_html,
                get_speedtest_history_widget_html
            )

            # Check that deprecation warning was issued
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            print(f"Deprecation warning issued: {w[0].message}")

        # Test that the classes/functions work
        monitor = get_speed_test_monitor()
        assert monitor is not None
        assert isinstance(monitor, SpeedTestMonitor)
        print(f"get_speed_test_monitor() works: {type(monitor).__name__}")

        # Test HTML functions
        html = get_speedtest_widget_html()
        assert html is not None
        assert len(html) > 0
        assert "Speed Test" in html
        print(f"get_speedtest_widget_html() works ({len(html)} chars)")

        history_html = get_speedtest_history_widget_html()
        assert history_html is not None
        assert len(history_html) > 0
        assert "Speed History" in history_html
        print(f"get_speedtest_history_widget_html() works ({len(history_html)} chars)")

        print("TEST 2 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_ping_widget_backward_compat():
    """Test that old Ping widget imports still work"""
    print("TEST 3: Ping Widget Backward Compatibility")
    print("-" * 80)

    try:
        # This should work but show a deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from atlas.ping_widget import (
                PingMonitor,
                get_ping_monitor,
                get_ping_widget_html,
                get_local_ip
            )

            # Check that deprecation warning was issued
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            print(f"Deprecation warning issued: {w[0].message}")

        # Test that the classes/functions work
        monitor = get_ping_monitor()
        assert monitor is not None
        assert isinstance(monitor, PingMonitor)
        print(f"get_ping_monitor() works: {type(monitor).__name__}")

        # Test HTML function
        html = get_ping_widget_html()
        assert html is not None
        assert len(html) > 0
        assert "Ping" in html
        print(f"get_ping_widget_html() works ({len(html)} chars)")

        # Test get_local_ip function
        local_ip = get_local_ip()
        assert local_ip is not None
        print(f"get_local_ip() works: {local_ip}")

        print("TEST 3 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_live_widgets_integration():
    """Test that live_widgets.py still works with the wrapper imports"""
    print("TEST 4: Live Widgets Integration")
    print("-" * 80)

    try:
        # This tests that live_widgets.py can still import from the old locations
        from atlas.live_widgets import (
            get_speed_test_monitor,
            get_ping_monitor,
            get_wifi_monitor
        )

        # Test that all monitors can be created
        speed_monitor = get_speed_test_monitor()
        ping_monitor = get_ping_monitor()
        wifi_monitor = get_wifi_monitor()

        assert speed_monitor is not None
        assert ping_monitor is not None
        assert wifi_monitor is not None

        print(f"get_speed_test_monitor() from live_widgets: {type(speed_monitor).__name__}")
        print(f"get_ping_monitor() from live_widgets: {type(ping_monitor).__name__}")
        print(f"get_wifi_monitor() from live_widgets: {type(wifi_monitor).__name__}")

        print("TEST 4 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 4 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all backward compatibility tests"""
    print("Starting backward compatibility tests for Phase 3 migration...\n")

    results = []

    # Run all tests
    results.append(("WiFi Widget", test_wifi_widget_backward_compat()))
    results.append(("SpeedTest Widget", test_speedtest_widget_backward_compat()))
    results.append(("Ping Widget", test_ping_widget_backward_compat()))
    results.append(("Live Widgets Integration", test_live_widgets_integration()))

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{status}: {name}")

    print()
    print(f"Total: {passed}/{total} tests passed")
    print()

    if passed == total:
        print("ALL BACKWARD COMPATIBILITY TESTS PASSED!")
        print()
        print("Migration Status:")
        print("  - Old widget files now act as thin wrappers")
        print("  - All imports redirected to refactored monitors")
        print("  - Deprecation warnings issued to encourage migration")
        print("  - Existing code (like live_widgets.py) works without changes")
        print()
        print("Next Steps:")
        print("  1. Test the live widget server")
        print("  2. Update documentation")
        print("  3. Create migration guide for future updates")
        return 0
    else:
        print(" Some backward compatibility tests failed!")
        print("Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
