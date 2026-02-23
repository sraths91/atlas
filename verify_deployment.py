#!/usr/bin/env python3
"""
ATLAS Agent - Deployment Verification Script

Verifies that all monitors, API endpoints, and components are properly
installed and functional.

Usage:
    python3 verify_deployment.py
"""

import sys
import os
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_status(item, status, details=""):
    """Print status line"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {item:<50} {details}")

def verify_monitors():
    """Verify all monitor files exist"""
    print_header("1. Verifying Monitor Files")

    monitors = {
        "VPN Monitor": "atlas/network/monitors/vpn_monitor.py",
        "SaaS Endpoint Monitor": "atlas/network/monitors/saas_endpoint_monitor.py",
        "Network Quality Monitor": "atlas/network/monitors/network_quality_monitor.py",
        "WiFi Roaming Monitor": "atlas/network/monitors/wifi_roaming_monitor.py",
        "Security Monitor": "atlas/security_monitor.py",
        "Application Monitor": "atlas/application_monitor.py",
        "Disk Health Monitor": "atlas/disk_health_monitor.py",
        "Software Inventory Monitor": "atlas/software_inventory_monitor.py",
        "Peripheral Monitor": "atlas/peripheral_monitor.py",
        "Power Monitor": "atlas/power_monitor.py",
        "Display Monitor": "atlas/display_monitor.py",
        "System Monitor": "atlas/system_monitor.py"
    }

    all_good = True
    for name, path in monitors.items():
        exists = Path(path).exists()
        print_status(name, exists, path if exists else "MISSING")
        if not exists:
            all_good = False

    return all_good

def verify_imports():
    """Verify all monitors can be imported"""
    print_header("2. Verifying Monitor Imports")

    imports = {
        "VPN Monitor": "from atlas.network.monitors.vpn_monitor import get_vpn_monitor",
        "SaaS Monitor": "from atlas.network.monitors.saas_endpoint_monitor import get_saas_endpoint_monitor",
        "Network Quality": "from atlas.network.monitors.network_quality_monitor import get_network_quality_monitor",
        "WiFi Roaming": "from atlas.network.monitors.wifi_roaming_monitor import get_wifi_roaming_monitor",
        "Security": "from atlas.security_monitor import get_security_monitor",
        "Application": "from atlas.application_monitor import get_app_monitor",
        "Disk Health": "from atlas.disk_health_monitor import get_disk_monitor",
        "Software Inventory": "from atlas.software_inventory_monitor import get_software_monitor",
        "Peripheral": "from atlas.peripheral_monitor import get_peripheral_monitor",
        "Power": "from atlas.power_monitor import get_power_monitor",
        "Display": "from atlas.display_monitor import get_display_monitor",
    }

    all_good = True
    for name, import_stmt in imports.items():
        try:
            exec(import_stmt)
            print_status(name, True, "Import successful")
        except ImportError as e:
            print_status(name, False, f"Import failed: {e}")
            all_good = False
        except Exception as e:
            print_status(name, False, f"Error: {e}")
            all_good = False

    return all_good

def verify_api_endpoints():
    """Verify API endpoints are registered"""
    print_header("3. Verifying API Endpoint Registration")

    security_routes = Path("atlas/fleet/server/routes/security_routes.py")

    if not security_routes.exists():
        print_status("security_routes.py", False, "File not found")
        return False

    content = security_routes.read_text()

    endpoints = {
        "Security Status": "'/api/security/status'",
        "VPN Status": "'/api/vpn/status'",
        "SaaS Health": "'/api/saas/health'",
        "Network Quality": "'/api/network/quality'",
        "WiFi Roaming": "'/api/wifi/roaming'",
        "App Crashes": "'/api/applications/crashes'",
        "Disk Health": "'/api/disk/health'",
        "Software Inventory": "'/api/software/inventory'",
        "Peripheral Devices": "'/api/peripherals/devices'",
        "Power Status": "'/api/power/status'",
        "Display Status": "'/api/display/status'"
    }

    all_good = True
    for name, endpoint in endpoints.items():
        found = endpoint in content
        print_status(name, found, endpoint if found else "NOT REGISTERED")
        if not found:
            all_good = False

    return all_good

def verify_csv_logging():
    """Verify CSV logging infrastructure"""
    print_header("4. Verifying CSV Logging")

    from atlas.core.logging import CSVLogger
    import tempfile
    import time

    try:
        # Test CSV logger
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            test_file = f.name

        logger = CSVLogger(
            log_file=test_file,
            fieldnames=['timestamp', 'test_value'],
            max_history=10
        )

        # Write test data
        logger.append({'timestamp': '2026-01-11T00:00:00', 'test_value': 'test'})

        # Read back
        history = logger.get_history()

        # Cleanup
        os.unlink(test_file)

        if len(history) == 1 and history[0]['test_value'] == 'test':
            print_status("CSVLogger", True, "Write/Read test passed")
            return True
        else:
            print_status("CSVLogger", False, "Write/Read test failed")
            return False

    except Exception as e:
        print_status("CSVLogger", False, f"Error: {e}")
        return False

def verify_widgets():
    """Verify widget files"""
    print_header("5. Verifying Visualization Widgets")

    widgets = {
        "Security Dashboard": "atlas/security_dashboard_widget.py",
        "VPN Status": "atlas/vpn_status_widget.py",
        "SaaS Health": "atlas/saas_health_widget.py",
        "Network Quality": "atlas/network_quality_widget.py",
        "WiFi Roaming": "atlas/wifi_roaming_widget.py"
    }

    all_good = True
    for name, path in widgets.items():
        exists = Path(path).exists()
        print_status(name, exists, path if exists else "MISSING")
        if not exists:
            all_good = False

    return all_good

def verify_documentation():
    """Verify documentation files"""
    print_header("6. Verifying Documentation")

    docs = {
        "Executive Summary": "EXECUTIVE_SUMMARY.md",
        "Implementation Matrix": "IMPLEMENTATION_MATRIX.md",
        "Phase 3 Complete": "PHASE3_COMPLETE.md",
        "Phase 4 APM": "PHASE4_APM_COMPLETE.md",
        "Phase 4 Extended": "PHASE4_EXTENDED_COMPLETE.md",
        "APM Enhancement": "APM_ENHANCEMENT_COMPLETE.md",
        "Display Monitor Complete": "DISPLAY_MONITOR_COMPLETE.md",
        "Quick Reference": "QUICK_REFERENCE.md",
        "Final Status": "IMPLEMENTATION_STATUS_FINAL.md"
    }

    all_good = True
    for name, path in docs.items():
        exists = Path(path).exists()
        print_status(name, exists, path if exists else "MISSING")
        if not exists:
            all_good = False

    return all_good

def main():
    """Run all verification checks"""
    print("\n" + "="*70)
    print("  ATLAS Agent - Deployment Verification")
    print("  Date: 2026-01-11")
    print("="*70)

    results = {
        "Monitor Files": verify_monitors(),
        "Monitor Imports": verify_imports(),
        "API Endpoints": verify_api_endpoints(),
        "CSV Logging": verify_csv_logging(),
        "Widgets": verify_widgets(),
        "Documentation": verify_documentation()
    }

    # Summary
    print_header("Verification Summary")

    all_passed = all(results.values())

    for check, passed in results.items():
        print_status(check, passed)

    print("\n" + "="*70)
    if all_passed:
        print("  ✅ ALL CHECKS PASSED - DEPLOYMENT READY")
        print("="*70 + "\n")
        return 0
    else:
        print("  ❌ SOME CHECKS FAILED - REVIEW ERRORS ABOVE")
        print("="*70 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
