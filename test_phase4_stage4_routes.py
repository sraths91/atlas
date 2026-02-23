"""
Test Suite for Phase 4 Stage 4: Route Modules Extraction

Tests the extracted route modules integrated with FleetRouter.
Demonstrates proof-of-concept for route extraction strategy.

Created: December 31, 2025
"""
import sys
import json
from io import BytesIO
from http.server import BaseHTTPRequestHandler

# Add parent directory to path
sys.path.insert(0, '/Users/samraths/CascadeProjects/windsurf-project-2-refactored')

def test_1_import_route_modules():
    """Test 1: Import route modules"""
    print("\n" + "="*60)
    print("TEST 1: Import Route Modules")
    print("="*60)

    try:
        from atlas.fleet.server.routes.agent_routes import register_agent_routes
        from atlas.fleet.server.routes.dashboard_routes import register_dashboard_routes
        from atlas.fleet.server.routes.machine_routes import register_machine_routes
        print("Successfully imported agent_routes")
        print("Successfully imported dashboard_routes")
        print("Successfully imported machine_routes")
        print(f"   - register_agent_routes: {register_agent_routes}")
        print(f"   - register_dashboard_routes: {register_dashboard_routes}")
        print(f"   - register_machine_routes: {register_machine_routes}")
        return True
    except Exception as e:
        print(f"Failed to import route modules: {e}")
        return False


def test_2_register_agent_routes():
    """Test 2: Register agent routes with FleetRouter"""
    print("\n" + "="*60)
    print("TEST 2: Register Agent Routes")
    print("="*60)

    try:
        from atlas.fleet.server.router import FleetRouter
        from atlas.fleet.server.routes.agent_routes import register_agent_routes
        from atlas.fleet.server.data_store import FleetDataStore
        from atlas.fleet.server.auth import FleetAuthManager

        # Create instances
        router = FleetRouter()
        data_store = FleetDataStore()
        auth_manager = FleetAuthManager(api_key='test-key')

        # Register agent routes
        register_agent_routes(router, data_store, encryption=None, auth_manager=auth_manager)

        # Check registered routes
        routes = router.list_routes()
        print(f"Registered {len(routes)} agent routes:")
        for method, pattern in routes:
            print(f"   - {method} {pattern}")

        # Expected routes:
        # POST /api/fleet/report
        # GET /api/fleet/commands/{machine_id}
        # POST /api/fleet/command/{machine_id}/ack
        # POST /api/fleet/widget-logs

        assert len(routes) == 4, f"Expected 4 routes, got {len(routes)}"
        return True
    except Exception as e:
        print(f"Failed to register agent routes: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_register_dashboard_routes():
    """Test 3: Register dashboard routes with FleetRouter"""
    print("\n" + "="*60)
    print("TEST 3: Register Dashboard Routes")
    print("="*60)

    try:
        from atlas.fleet.server.router import FleetRouter
        from atlas.fleet.server.routes.dashboard_routes import register_dashboard_routes
        from atlas.fleet.server.data_store import FleetDataStore
        from atlas.fleet.server.auth import FleetAuthManager

        # Create instances
        router = FleetRouter()
        data_store = FleetDataStore()
        auth_manager = FleetAuthManager()

        # Register dashboard routes
        register_dashboard_routes(router, data_store, auth_manager)

        # Check registered routes
        routes = router.list_routes()
        print(f"Registered {len(routes)} dashboard routes:")
        for method, pattern in routes:
            print(f"   - {method} {pattern}")

        # Expected routes:
        # GET /api/fleet/machines
        # GET /api/fleet/summary
        # GET /api/fleet/server-resources
        # GET /api/fleet/storage

        assert len(routes) == 4, f"Expected 4 routes, got {len(routes)}"
        return True
    except Exception as e:
        print(f"Failed to register dashboard routes: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_route_dispatch():
    """Test 4: Test route dispatch with mock handler"""
    print("\n" + "="*60)
    print("TEST 4: Route Dispatch")
    print("="*60)

    try:
        from atlas.fleet.server.router import FleetRouter
        from atlas.fleet.server.routes.agent_routes import register_agent_routes
        from atlas.fleet.server.data_store import FleetDataStore
        from atlas.fleet.server.auth import FleetAuthManager

        # Create instances
        router = FleetRouter()
        data_store = FleetDataStore()
        auth_manager = FleetAuthManager(api_key='test-key-123')

        # Register agent routes
        register_agent_routes(router, data_store, encryption=None, auth_manager=auth_manager)

        # Create mock handler
        class MockHandler(BaseHTTPRequestHandler):
            def __init__(self):
                # Don't call super().__init__() to avoid socket setup
                self.headers = {}
                self.wfile = BytesIO()
                self.response_code = None
                self.response_headers = {}

            def send_response(self, code):
                self.response_code = code

            def send_header(self, key, value):
                self.response_headers[key] = value

            def end_headers(self):
                pass

        handler = MockHandler()
        handler.headers = {'X-API-Key': 'test-key-123'}

        # Test dispatching to /api/fleet/commands/mac-001
        print("\nTesting dispatch to /api/fleet/commands/mac-001...")
        result = router.dispatch(handler, 'GET', '/api/fleet/commands/mac-001')

        if result:
            print("Route dispatched successfully")
            print(f"   - Response code: {handler.response_code}")
            response = handler.wfile.getvalue().decode()
            if response:
                print(f"   - Response: {response}")
        else:
            print("Route dispatch failed")
            return False

        return True
    except Exception as e:
        print(f"Failed route dispatch test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_register_machine_routes():
    """Test 5: Register machine routes with FleetRouter"""
    print("\n" + "="*60)
    print("TEST 5: Register Machine Routes")
    print("="*60)

    try:
        from atlas.fleet.server.router import FleetRouter
        from atlas.fleet.server.routes.machine_routes import register_machine_routes
        from atlas.fleet.server.data_store import FleetDataStore
        from atlas.fleet.server.auth import FleetAuthManager

        # Create instances
        router = FleetRouter()
        data_store = FleetDataStore()
        auth_manager = FleetAuthManager()

        # Register machine routes
        register_machine_routes(router, data_store, auth_manager)

        # Check registered routes
        routes = router.list_routes()
        print(f"Registered {len(routes)} machine routes:")
        for method, pattern in routes:
            print(f"   - {method} {pattern}")

        # Expected routes:
        # GET /api/fleet/machine/{identifier}
        # GET /api/fleet/history/{identifier}
        # GET /api/fleet/recent-commands/{identifier}

        assert len(routes) == 3, f"Expected 3 routes, got {len(routes)}"
        return True
    except Exception as e:
        print(f"Failed to register machine routes: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_combined_registration():
    """Test 6: Register all route modules together"""
    print("\n" + "="*60)
    print("TEST 6: Combined Route Registration")
    print("="*60)

    try:
        from atlas.fleet.server.router import FleetRouter
        from atlas.fleet.server.routes.agent_routes import register_agent_routes
        from atlas.fleet.server.routes.dashboard_routes import register_dashboard_routes
        from atlas.fleet.server.routes.machine_routes import register_machine_routes
        from atlas.fleet.server.data_store import FleetDataStore
        from atlas.fleet.server.auth import FleetAuthManager

        # Create instances
        router = FleetRouter()
        data_store = FleetDataStore()
        auth_manager = FleetAuthManager(api_key='test-key')

        # Register all route sets
        register_agent_routes(router, data_store, encryption=None, auth_manager=auth_manager)
        register_dashboard_routes(router, data_store, auth_manager)
        register_machine_routes(router, data_store, auth_manager)

        # Check total registered routes
        routes = router.list_routes()
        print(f"Total registered routes: {len(routes)}")

        # Categorize routes (order matters - check more specific patterns first)
        machine_routes = [(method, pattern) for method, pattern in routes if 'machine/{' in pattern or 'history/{' in pattern or 'recent-commands/{' in pattern]
        dashboard_routes = [(method, pattern) for method, pattern in routes if 'machines' in pattern or 'summary' in pattern or 'storage' in pattern or 'server-resources' in pattern]
        # Agent routes - exclude recent-commands which is in machine_routes
        agent_routes = [(method, pattern) for method, pattern in routes
                       if (pattern.startswith('/api/fleet/commands/{') or
                           pattern.startswith('/api/fleet/command/{') or
                           'report' in pattern or
                           'widget' in pattern)]

        print(f"\n   Agent routes: {len(agent_routes)}")
        for method, pattern in agent_routes:
            print(f"      {method} {pattern}")

        print(f"\n   Dashboard routes: {len(dashboard_routes)}")
        for method, pattern in dashboard_routes:
            print(f"      {method} {pattern}")

        print(f"\n   Machine routes: {len(machine_routes)}")
        for method, pattern in machine_routes:
            print(f"      {method} {pattern}")

        assert len(routes) == 11, f"Expected 11 total routes, got {len(routes)}"
        assert len(agent_routes) == 4, f"Expected 4 agent routes, got {len(agent_routes)}"
        assert len(dashboard_routes) == 4, f"Expected 4 dashboard routes, got {len(dashboard_routes)}"
        assert len(machine_routes) == 3, f"Expected 3 machine routes, got {len(machine_routes)}"

        return True
    except Exception as e:
        print(f"Failed combined registration test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PHASE 4 STAGE 4: ROUTE MODULES EXTRACTION - TEST SUITE")
    print("=" * 60)

    tests = [
        test_1_import_route_modules,
        test_2_register_agent_routes,
        test_3_register_dashboard_routes,
        test_4_route_dispatch,
        test_5_register_machine_routes,
        test_6_combined_registration,
    ]

    results = []
    for test in tests:
        results.append(test())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({100*passed//total}%)")

    if passed == total:
        print("\nALL ROUTE MODULE TESTS PASSED!")
        print("\nPhase 4 Stage 4 Progress:")
        print("  - Agent routes extracted and tested (4 routes)")
        print("  - Dashboard routes extracted and tested (4 routes)")
        print("  - Machine routes extracted and tested (3 routes)")
        print("  - Total routes extracted: 11/61 (18%)")
        print("  - Routes integrate with FleetRouter")
        print("  - Pattern matching works correctly")
        print("  - 🔜 Next: Extract cluster routes (4 routes)")
        print("  - 🔜 Next: Extract remaining routes (46 more routes)")
        print("  - 🔜 Next: Integrate router into fleet_server.py")
    else:
        print(f"\n{total - passed} test(s) failed")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
