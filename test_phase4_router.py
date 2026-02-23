#!/usr/bin/env python3
"""
Test Phase 4 Stage 3: FleetRouter Creation

This tests that the new FleetRouter system works correctly.
"""
import sys
import logging
from unittest.mock import Mock, MagicMock
from http.server import BaseHTTPRequestHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("PHASE 4 STAGE 3: FLEETROUTER CREATION TEST")
print("=" * 80)
print()


def test_router_import():
    """Test importing FleetRouter"""
    print("TEST 1: Import FleetRouter")
    print("-" * 80)

    try:
        from atlas.fleet.server.router import FleetRouter, Route

        # Test instantiation
        router = FleetRouter()
        assert router is not None
        assert router.routes == []
        assert router.global_middleware == []
        print(f"FleetRouter imported and instantiated")
        print(f"Initial state: {len(router.routes)} routes, {len(router.global_middleware)} middleware")

        # Test Route class
        route = Route('GET', '/test', lambda h: None)
        assert route.method == 'GET'
        assert route.pattern == '/test'
        print(f"Route class works")

        print("TEST 1 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 1 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_route_registration():
    """Test route registration"""
    print("TEST 2: Route Registration")
    print("-" * 80)

    try:
        from atlas.fleet.server.router import FleetRouter

        router = FleetRouter()

        # Define simple handlers
        def handle_home(handler):
            handler.send_response(200)
            handler.end_headers()

        def handle_api(handler):
            handler.send_response(200)
            handler.end_headers()

        # Register routes
        router.register('GET', '/', handle_home)
        router.register('GET', '/api/test', handle_api)

        assert len(router.routes) == 2
        print(f"Registered 2 routes")

        # Test convenience methods
        router.get('/api/get', handle_api)
        router.post('/api/post', handle_api)
        router.put('/api/put', handle_api)
        router.delete('/api/delete', handle_api)

        assert len(router.routes) == 6
        print(f"Convenience methods work (get, post, put, delete)")
        print(f"Total routes: {len(router.routes)}")

        # Test list_routes
        routes_list = router.list_routes()
        assert len(routes_list) == 6
        assert ('GET', '/') in routes_list
        assert ('POST', '/api/post') in routes_list
        print(f"list_routes() returns: {routes_list}")

        print("TEST 2 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_matching():
    """Test route pattern matching"""
    print("TEST 3: Pattern Matching")
    print("-" * 80)

    try:
        from atlas.fleet.server.router import Route

        # Simple pattern
        route = Route('GET', '/api/test', lambda h: None)
        matches, params = route.matches('GET', '/api/test')
        assert matches is True
        assert params == {}
        print(f"Simple pattern matches: /api/test")

        # Pattern with parameter
        route = Route('GET', '/api/machine/{id}', lambda h, id: None)
        matches, params = route.matches('GET', '/api/machine/abc123')
        assert matches is True
        assert params == {'id': 'abc123'}
        print(f"Parameterized pattern matches: /api/machine/{{id}} → {params}")

        # Multiple parameters
        route = Route('GET', '/api/{resource}/{id}', lambda h, resource, id: None)
        matches, params = route.matches('GET', '/api/machines/xyz789')
        assert matches is True
        assert params == {'resource': 'machines', 'id': 'xyz789'}
        print(f"Multiple parameters: /api/{{resource}}/{{id}} → {params}")

        # Method mismatch
        matches, params = route.matches('POST', '/api/machines/xyz789')
        assert matches is False
        print(f"Method mismatch rejected")

        # Path mismatch
        matches, params = route.matches('GET', '/wrong/path')
        assert matches is False
        print(f"Path mismatch rejected")

        print("TEST 3 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_route_dispatch():
    """Test route dispatching"""
    print("TEST 4: Route Dispatch")
    print("-" * 80)

    try:
        from atlas.fleet.server.router import FleetRouter

        router = FleetRouter()
        called_routes = []

        # Define handlers that track calls
        def handle_home(handler):
            called_routes.append('home')
            handler.send_response(200)
            handler.end_headers()
            handler.wfile.write(b'Home')

        def handle_machine(handler, id):
            called_routes.append(f'machine-{id}')
            handler.send_response(200)
            handler.end_headers()
            handler.wfile.write(f'Machine {id}'.encode())

        # Register routes
        router.get('/', handle_home)
        router.get('/api/machine/{id}', handle_machine)

        # Create mock handler
        handler = Mock(spec=BaseHTTPRequestHandler)
        handler.wfile = Mock()
        handler.wfile.write = Mock()

        # Dispatch to home
        handled = router.dispatch(handler, 'GET', '/')
        assert handled is True
        assert 'home' in called_routes
        print(f"Dispatched to home route")

        # Dispatch to machine
        handled = router.dispatch(handler, 'GET', '/api/machine/abc123')
        assert handled is True
        assert 'machine-abc123' in called_routes
        print(f"Dispatched to parameterized route with id=abc123")

        # Dispatch to non-existent route
        called_routes.clear()
        handled = router.dispatch(handler, 'GET', '/nonexistent')
        assert handled is False
        assert len(called_routes) == 0
        print(f"Non-existent route returns False")

        print("TEST 4 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 4 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_middleware():
    """Test middleware functionality"""
    print("TEST 5: Middleware")
    print("-" * 80)

    try:
        from atlas.fleet.server.router import FleetRouter

        router = FleetRouter()
        middleware_calls = []

        # Define middleware
        def global_middleware(handler):
            middleware_calls.append('global')
            return None  # Continue to route

        def route_middleware(handler):
            middleware_calls.append('route')
            return None  # Continue to handler

        def blocking_middleware(handler):
            middleware_calls.append('blocking')
            handler.send_response(403)
            handler.end_headers()
            return True  # Block further processing

        # Define handler
        def handle_test(handler):
            middleware_calls.append('handler')
            handler.send_response(200)
            handler.end_headers()

        # Add global middleware
        router.add_global_middleware(global_middleware)

        # Register route with route-specific middleware
        router.get('/test', handle_test, middleware=[route_middleware])

        # Create mock handler
        handler = Mock(spec=BaseHTTPRequestHandler)

        # Dispatch - should run global, then route, then handler
        middleware_calls.clear()
        router.dispatch(handler, 'GET', '/test')
        assert middleware_calls == ['global', 'route', 'handler']
        print(f"Middleware chain executed: {middleware_calls}")

        # Test blocking middleware
        router2 = FleetRouter()
        router2.add_global_middleware(blocking_middleware)
        router2.get('/test', handle_test)

        middleware_calls.clear()
        router2.dispatch(handler, 'GET', '/test')
        assert middleware_calls == ['blocking']
        assert 'handler' not in middleware_calls
        print(f"Blocking middleware prevents handler execution")

        print("TEST 5 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 5 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_full_request_handling():
    """Test complete request handling with 404"""
    print("TEST 6: Full Request Handling")
    print("-" * 80)

    try:
        from atlas.fleet.server.router import FleetRouter

        router = FleetRouter()

        def handle_api(handler):
            handler.send_response(200)
            handler.send_header('Content-type', 'application/json')
            handler.end_headers()
            handler.wfile.write(b'{"status": "ok"}')

        router.get('/api/status', handle_api)

        # Create mock handler
        handler = Mock(spec=BaseHTTPRequestHandler)
        handler.wfile = Mock()
        handler.wfile.write = Mock()

        # Test successful request
        router.handle_request(handler, 'GET', '/api/status')
        handler.send_response.assert_called_with(200)
        print(f"Successful request handled")

        # Test 404
        handler.reset_mock()
        router.handle_request(handler, 'GET', '/nonexistent')
        handler.send_response.assert_called_with(404)
        print(f"404 sent for non-existent route")

        # Test send_404 directly
        handler.reset_mock()
        router.send_404(handler)
        handler.send_response.assert_called_with(404)
        assert handler.wfile.write.called
        print(f"send_404() works directly")

        print("TEST 6 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 6 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_fleet_server_integration():
    """Test that fleet_server.py can use FleetRouter"""
    print("TEST 7: Fleet Server Integration")
    print("-" * 80)

    try:
        from atlas.fleet_server import FleetRouter

        # Should be able to import from fleet_server
        router = FleetRouter()
        assert router is not None
        print(f"FleetRouter imported from fleet_server")

        # Verify it's the refactored version
        from atlas.fleet.server.router import FleetRouter as RefactoredRouter
        assert type(router) == RefactoredRouter
        print(f"Confirmed: fleet_server uses refactored FleetRouter")

        print("TEST 7 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 7 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all FleetRouter tests"""
    print("Starting FleetRouter creation tests...\n")

    results = []

    # Run all tests
    results.append(("Import FleetRouter", test_router_import()))
    results.append(("Route Registration", test_route_registration()))
    results.append(("Pattern Matching", test_pattern_matching()))
    results.append(("Route Dispatch", test_route_dispatch()))
    results.append(("Middleware", test_middleware()))
    results.append(("Full Request Handling", test_full_request_handling()))
    results.append(("Fleet Server Integration", test_fleet_server_integration()))

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
        print("ALL FLEETROUTER TESTS PASSED!")
        print()
        print("Phase 4 Stage 3 Progress:")
        print("  - FleetRouter created in fleet/server/router.py")
        print("  - Clean route registration system")
        print("  - Pattern matching with parameters (e.g., /machine/{id})")
        print("  - Middleware support (global and route-specific)")
        print("  - Automatic 404 handling")
        print("  - Ready to replace if/elif chains in fleet_server.py")
        print()
        print("Cumulative Phase 4 Impact:")
        print("  - Stage 1 (FleetDataStore): 158 lines saved")
        print("  - Stage 2 (FleetAuthManager): 31 lines saved")
        print("  - Stage 3 (FleetRouter): Infrastructure created (ready for use)")
        print("  - Total: New modular architecture foundation complete")
        print()
        print("Next Steps:")
        print("  1. Update fleet_server.py to use FleetRouter")
        print("  2. Extract route modules (Stage 4)")
        print("  3. Extract HTML templates (Stage 5)")
        return 0
    else:
        print(" Some FleetRouter tests failed!")
        print("Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
