#!/usr/bin/env python3
"""
Test Phase 4 Stage 2: FleetAuthManager Extraction

This tests that the extracted FleetAuthManager works correctly.
"""
import sys
import logging
from unittest.mock import Mock, MagicMock, patch
from http.server import BaseHTTPRequestHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("PHASE 4 STAGE 2: FLEETAUTHMANAGER EXTRACTION TEST")
print("=" * 80)
print()


def test_auth_manager_import():
    """Test importing FleetAuthManager"""
    print("TEST 1: Import FleetAuthManager")
    print("-" * 80)

    try:
        from atlas.fleet.server.auth import FleetAuthManager, require_web_auth, require_api_key

        # Test instantiation
        auth_mgr = FleetAuthManager(api_key='test123')
        assert auth_mgr is not None
        assert auth_mgr.api_key == 'test123'
        print(f"FleetAuthManager imported and instantiated")
        print(f"API key set: {auth_mgr.api_key}")

        # Test without API key
        auth_mgr_no_key = FleetAuthManager()
        assert auth_mgr_no_key.api_key is None
        print(f"FleetAuthManager works without API key")

        # Check decorators
        assert callable(require_web_auth)
        assert callable(require_api_key)
        print(f"Decorators available: require_web_auth, require_api_key")

        print("TEST 1 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 1 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_get_session_token():
    """Test session token extraction"""
    print("TEST 2: Session Token Extraction")
    print("-" * 80)

    try:
        from atlas.fleet.server.auth import FleetAuthManager

        # Create mock handler with cookie
        handler = Mock(spec=BaseHTTPRequestHandler)
        handler.headers = {'Cookie': 'fleet_session=abc123; other=value'}

        token = FleetAuthManager.get_session_token(handler)
        assert token == 'abc123'
        print(f"Token extracted from cookie: {token}")

        # Test without cookie
        handler.headers = {}
        token = FleetAuthManager.get_session_token(handler)
        assert token is None
        print(f"Returns None when no cookie")

        # Test with wrong cookie
        handler.headers = {'Cookie': 'other=value'}
        token = FleetAuthManager.get_session_token(handler)
        assert token is None
        print(f"Returns None when session cookie missing")

        print("TEST 2 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_api_key_validation():
    """Test API key validation"""
    print("TEST 3: API Key Validation")
    print("-" * 80)

    try:
        from atlas.fleet.server.auth import FleetAuthManager

        # Create auth manager with API key
        auth_mgr = FleetAuthManager(api_key='secret123')

        # Test valid API key
        handler = Mock(spec=BaseHTTPRequestHandler)
        handler.headers = {'X-API-Key': 'secret123'}
        assert auth_mgr.check_api_key(handler) is True
        print(f"Valid API key accepted")

        # Test invalid API key
        handler.headers = {'X-API-Key': 'wrong'}
        assert auth_mgr.check_api_key(handler) is False
        print(f"Invalid API key rejected")

        # Test missing API key
        handler.headers = {}
        assert auth_mgr.check_api_key(handler) is False
        print(f"Missing API key rejected")

        # Test with no API key configured (should allow)
        auth_mgr_no_key = FleetAuthManager()
        handler.headers = {}
        assert auth_mgr_no_key.check_api_key(handler) is True
        print(f"No API key configured: allows all requests")

        print("TEST 3 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_auth_responses():
    """Test authentication response methods"""
    print("TEST 4: Authentication Responses")
    print("-" * 80)

    try:
        from atlas.fleet.server.auth import FleetAuthManager

        # Test send_auth_required
        handler = Mock(spec=BaseHTTPRequestHandler)
        handler.wfile = Mock()
        handler.wfile.write = Mock()

        FleetAuthManager.send_auth_required(handler)

        handler.send_response.assert_called_with(401)
        handler.send_header.assert_any_call('WWW-Authenticate', 'Basic realm="Fleet Dashboard"')
        handler.send_header.assert_any_call('Content-type', 'text/html')
        handler.end_headers.assert_called_once()
        assert handler.wfile.write.called
        print(f"send_auth_required() sends proper 401 response")

        # Test send_redirect_to_login
        handler = Mock(spec=BaseHTTPRequestHandler)

        FleetAuthManager.send_redirect_to_login(handler)

        handler.send_response.assert_called_with(302)
        handler.send_header.assert_called_with('Location', '/login')
        handler.end_headers.assert_called_once()
        print(f"send_redirect_to_login() sends 302 redirect")

        print("TEST 4 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 4 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_fleet_server_integration():
    """Test that fleet_server.py uses FleetAuthManager"""
    print("TEST 5: Fleet Server Integration")
    print("-" * 80)

    try:
        from atlas.fleet_server import FleetAuthManager

        # Should be able to import from fleet_server
        auth_mgr = FleetAuthManager(api_key='test')
        assert auth_mgr is not None
        print(f"FleetAuthManager imported from fleet_server")

        # Verify it's the refactored version
        from atlas.fleet.server.auth import FleetAuthManager as RefactoredAuth
        assert type(auth_mgr) == RefactoredAuth
        print(f"Confirmed: fleet_server uses refactored FleetAuthManager")

        print("TEST 5 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 5 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_decorators():
    """Test authentication decorators"""
    print("TEST 6: Authentication Decorators")
    print("-" * 80)

    try:
        from atlas.fleet.server.auth import require_web_auth, require_api_key, FleetAuthManager

        # Test require_web_auth decorator
        @require_web_auth
        def protected_method(handler):
            return f"Hello {handler.authenticated_user}"

        # Mock handler with authentication failure
        handler = Mock()
        handler.headers = {}

        with patch('atlas.fleet.server.auth.FleetAuthManager.check_web_auth', return_value=(False, None)):
            with patch('atlas.fleet.server.auth.FleetAuthManager.send_redirect_to_login') as mock_redirect:
                protected_method(handler)
                mock_redirect.assert_called_once()
        print(f"require_web_auth redirects when not authenticated")

        # Test require_api_key decorator
        auth_mgr = FleetAuthManager(api_key='test123')

        @require_api_key(auth_mgr)
        def api_method(handler):
            return "API response"

        # Mock handler with invalid API key
        handler = Mock()
        handler.headers = {'X-API-Key': 'wrong'}

        with patch('atlas.fleet.server.auth.FleetAuthManager.send_auth_required') as mock_auth_req:
            api_method(handler)
            mock_auth_req.assert_called_once()
        print(f"require_api_key sends 401 when API key invalid")

        print("TEST 6 PASSED\n")
        return True

    except Exception as e:
        print(f"TEST 6 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all FleetAuthManager tests"""
    print("Starting FleetAuthManager extraction tests...\n")

    results = []

    # Run all tests
    results.append(("Import FleetAuthManager", test_auth_manager_import()))
    results.append(("Session Token Extraction", test_get_session_token()))
    results.append(("API Key Validation", test_api_key_validation()))
    results.append(("Authentication Responses", test_auth_responses()))
    results.append(("Fleet Server Integration", test_fleet_server_integration()))
    results.append(("Authentication Decorators", test_decorators()))

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
        print("ALL FLEETAUTHMANAGER TESTS PASSED!")
        print()
        print("Phase 4 Stage 2 Progress:")
        print("  - FleetAuthManager extracted to fleet/server/auth.py")
        print("  - fleet_server.py reduced from 3,947 → 3,916 lines (31 lines saved)")
        print("  - Authentication logic centralized")
        print("  - Decorators created for easy authentication")
        print("  - Backward compatibility maintained")
        print()
        print("Cumulative Phase 4 Impact:")
        print("  - Stage 1 (FleetDataStore): 158 lines saved")
        print("  - Stage 2 (FleetAuthManager): 31 lines saved")
        print("  - Total saved so far: 189 lines (4.6% of original 4,105 lines)")
        print("  - fleet_server.py: 4,105 → 3,916 lines")
        print()
        print("Next Steps:")
        print("  1. Continue with router system creation (Stage 3)")
        print("  2. Extract route modules (Stage 4)")
        print("  3. Extract HTML templates (Stage 5)")
        return 0
    else:
        print(" Some FleetAuthManager tests failed!")
        print("Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
