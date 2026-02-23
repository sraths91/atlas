#!/usr/bin/env python3
"""
Test script for Security Dashboard Widget - Phase 3
Tests both the widget HTML generation and the API endpoint
"""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_widget_html():
    """Test that the widget HTML generation works"""
    print("=" * 70)
    print("TEST 1: Security Dashboard Widget HTML Generation")
    print("=" * 70)

    try:
        from atlas.security_dashboard_widget import get_security_dashboard_widget_html

        html = get_security_dashboard_widget_html()

        # Basic checks
        assert html, "Widget HTML is empty"
        assert '<!DOCTYPE html>' in html, "Missing DOCTYPE"
        assert 'Security Dashboard' in html, "Missing title"
        assert '/api/security/status' in html, "Missing API endpoint reference"
        assert 'scoreValue' in html, "Missing score value element"
        assert 'firewall' in html.lower(), "Missing firewall check"
        assert 'filevault' in html.lower(), "Missing FileVault check"
        assert 'gatekeeper' in html.lower(), "Missing Gatekeeper check"

        print("✓ Widget HTML generation: PASS")
        print(f"  - HTML length: {len(html)} bytes")
        print(f"  - Contains security checklist items")
        print(f"  - Contains API endpoint reference")
        print()
        return True

    except Exception as e:
        print(f"✗ Widget HTML generation: FAIL")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_security_monitor():
    """Test that the security monitor works"""
    print("=" * 70)
    print("TEST 2: Security Monitor Functionality")
    print("=" * 70)

    try:
        from atlas.security_monitor import get_security_monitor

        # Get monitor instance
        monitor = get_security_monitor()

        # Get current status
        status = monitor.get_current_security_status()

        # Check required fields
        assert 'security_score' in status, "Missing security_score"
        assert 'firewall' in status, "Missing firewall status"
        assert 'filevault' in status, "Missing filevault status"
        assert 'gatekeeper' in status, "Missing gatekeeper status"
        assert 'sip' in status, "Missing SIP status"
        assert 'screen_lock' in status, "Missing screen_lock status"
        assert 'updates' in status, "Missing updates status"

        print("✓ Security monitor: PASS")
        print(f"  - Security Score: {status['security_score']}")
        print(f"  - Firewall: {status['firewall'].get('enabled', 'unknown')}")
        print(f"  - FileVault: {status['filevault'].get('enabled', 'unknown')}")
        print(f"  - Gatekeeper: {status['gatekeeper'].get('enabled', 'unknown')}")
        print(f"  - SIP: {status['sip'].get('enabled', 'unknown')}")
        print()
        return True

    except Exception as e:
        print(f"✗ Security monitor: FAIL")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_routes():
    """Test that API routes are registered"""
    print("=" * 70)
    print("TEST 3: API Route Registration")
    print("=" * 70)

    try:
        from atlas.fleet.server.routes.security_routes import register_security_routes
        from atlas.fleet.server.router import FleetRouter

        # Create router
        router = FleetRouter()

        # Register security routes
        register_security_routes(router)

        # Get registered routes
        routes = router.list_routes()

        # Check for expected routes
        expected_routes = [
            ('GET', '/api/security/status'),
            ('GET', '/api/security/events'),
            ('GET', '/api/security/score'),
        ]

        found_routes = []
        for method, pattern in routes:
            route_tuple = (method, pattern)
            if route_tuple in expected_routes:
                found_routes.append(route_tuple)

        assert len(found_routes) == len(expected_routes), f"Expected {len(expected_routes)} routes, found {len(found_routes)}"

        print("✓ API routes: PASS")
        print(f"  - Total routes registered: {len(routes)}")
        print(f"  - Security routes found: {len(found_routes)}")
        for method, pattern in found_routes:
            print(f"    • {method} {pattern}")
        print()
        return True

    except Exception as e:
        print(f"✗ API routes: FAIL")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_widget_integration():
    """Test that widget is integrated into live_widgets"""
    print("=" * 70)
    print("TEST 4: Widget Integration in Live Widgets")
    print("=" * 70)

    try:
        # Check import
        from atlas import live_widgets

        # Check that the import is present
        assert hasattr(live_widgets, 'get_security_dashboard_widget_html') or \
               'security_dashboard_widget' in str(live_widgets.__dict__), \
               "Security dashboard widget not imported in live_widgets"

        # Read the file to check for route handler
        import inspect
        source = inspect.getsource(live_widgets)

        assert '/widget/security-dashboard' in source, "Missing widget route handler"
        assert 'get_security_dashboard_widget_html' in source, "Missing widget HTML generator call"

        print("✓ Widget integration: PASS")
        print(f"  - Import present in live_widgets.py")
        print(f"  - Route handler /widget/security-dashboard registered")
        print()
        return True

    except Exception as e:
        print(f"✗ Widget integration: FAIL")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Security Dashboard Widget Tests" + " " * 22 + "║")
    print("║" + " " * 68 + "║")
    print("║" + "  Phase 3: Visualization Widgets - Security Dashboard" + " " * 13 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    results = []

    # Run tests
    results.append(("Widget HTML Generation", test_widget_html()))
    results.append(("Security Monitor", test_security_monitor()))
    results.append(("API Routes", test_api_routes()))
    results.append(("Widget Integration", test_widget_integration()))

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status:8} - {name}")

    print()
    print(f"  Total: {passed}/{total} tests passed")
    print()

    if passed == total:
        print("🎉 All tests passed! Security Dashboard Widget is ready.")
        print()
        print("Next steps:")
        print("  1. Start the fleet agent:")
        print("     python -m atlas.menubar_agent")
        print()
        print("  2. Access the Security Dashboard widget at:")
        print("     http://localhost:8767/widget/security-dashboard")
        print()
        print("  3. The widget will fetch data from:")
        print("     http://localhost:8767/api/security/status")
        print()
        return 0
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
