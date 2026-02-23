#!/usr/bin/env python3
"""
Test script for enhanced metrics implementation

This script verifies that all new monitors can be imported and initialized.
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all new monitors can be imported"""
    print("=" * 60)
    print("TESTING ENHANCED METRICS IMPLEMENTATION")
    print("=" * 60)
    print()

    tests_passed = 0
    tests_failed = 0

    # Test VPN Monitor
    try:
        from atlas.network.monitors.vpn_monitor import get_vpn_monitor
        monitor = get_vpn_monitor()
        status = monitor.get_current_status()
        print("✅ VPN Monitor: PASS")
        print(f"   - Connected: {status.get('connected')}")
        print(f"   - VPN Client: {status.get('vpn_client') or 'None detected'}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ VPN Monitor: FAIL - {e}")
        tests_failed += 1

    print()

    # Test SaaS Endpoint Monitor
    try:
        from atlas.network.monitors.saas_endpoint_monitor import get_saas_endpoint_monitor
        monitor = get_saas_endpoint_monitor()
        summary = monitor.get_category_summary()
        print("✅ SaaS Endpoint Monitor: PASS")
        print(f"   - Categories monitored: {len(summary)}")
        print(f"   - Endpoints configured: {len(monitor.endpoints)}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ SaaS Endpoint Monitor: FAIL - {e}")
        tests_failed += 1

    print()

    # Test Network Quality Monitor
    try:
        from atlas.network.monitors.network_quality_monitor import get_network_quality_monitor
        monitor = get_network_quality_monitor()
        summary = monitor.get_quality_summary()
        print("✅ Network Quality Monitor: PASS")
        print(f"   - TCP stats available: {bool(summary.get('tcp'))}")
        print(f"   - DNS stats available: {bool(summary.get('dns'))}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Network Quality Monitor: FAIL - {e}")
        tests_failed += 1

    print()

    # Test WiFi Roaming Monitor
    try:
        from atlas.network.monitors.wifi_roaming_monitor import get_wifi_roaming_monitor
        monitor = get_wifi_roaming_monitor()
        summary = monitor.get_roaming_summary()
        print("✅ WiFi Roaming Monitor: PASS")
        print(f"   - Roaming events: {summary.get('total_roaming_events', 0)}")
        print(f"   - Sticky client incidents: {summary.get('sticky_client_incidents', 0)}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ WiFi Roaming Monitor: FAIL - {e}")
        tests_failed += 1

    print()

    # Test Security Monitor
    try:
        from atlas.security_monitor import get_security_monitor
        monitor = get_security_monitor()
        status = monitor.get_current_security_status()
        print("✅ Security Monitor: PASS")
        if status:
            print(f"   - Security Score: {status.get('security_score', 'Calculating...')}/100")
            print(f"   - Firewall: {'✓' if status.get('firewall_enabled') else '✗'}")
            print(f"   - FileVault: {'✓' if status.get('filevault_enabled') else '✗'}")
        else:
            print("   - Still collecting initial data...")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Security Monitor: FAIL - {e}")
        tests_failed += 1

    print()
    print("=" * 60)
    print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)

    if tests_failed == 0:
        print()
        print("🎉 ALL TESTS PASSED! Enhanced metrics implementation is working!")
        print()
        print("Next steps:")
        print("1. Let monitors collect data for a few minutes")
        print("2. Check CSV log files in your home directory:")
        print("   - ~/vpn_*.csv")
        print("   - ~/saas_*.csv")
        print("   - ~/network_*.csv")
        print("   - ~/wifi_roaming_*.csv")
        print("   - ~/security_*.csv")
        print("3. Verify data in fleet database")
        return 0
    else:
        print()
        print("⚠️  Some tests failed. Check error messages above.")
        return 1

if __name__ == '__main__':
    sys.exit(test_imports())
