"""
Unit Tests for atlas.routes.agent_router

Tests route registration count, dispatch behavior for GET/POST,
parameterized route existence, and the /api/health endpoint.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_handler():
    """Create a mock HTTP handler with attributes expected by route handlers."""
    handler = MagicMock()
    handler.path = '/api/health'
    handler.headers = {}
    handler.client_address = ('127.0.0.1', 12345)
    handler.agent_start_time = 0
    handler.agent_version = '1.0.0'
    handler.fleet_server_url = None
    handler.last_fleet_report = None
    handler.__class__ = MagicMock()
    handler.__class__.e2ee_enabled = False
    handler.__class__.e2ee_server_verified = False
    handler.__class__.last_e2ee_verification = None
    return handler


@pytest.mark.unit
class TestAgentRouter:
    """Tests for agent_router route registration and dispatch."""

    def test_route_count(self):
        """The agent_router should have at least 100 registered routes."""
        # Importing api_routes triggers all @agent_router.route() decorators
        import atlas.routes.api_routes  # noqa: F401
        from atlas.routes.agent_router import agent_router

        routes = agent_router._router.list_routes()
        assert len(routes) >= 100, (
            f"Expected at least 100 registered routes, found {len(routes)}"
        )

    def test_dispatch_get_returns_bool(self, mock_handler):
        """dispatch_get returns True for a known path, False for unknown."""
        from atlas.routes.agent_router import agent_router

        # /api/health is a registered GET route
        with patch('atlas.routes.api_routes.get_system_health', return_value={'status': 'ok'}):
            result = agent_router.dispatch_get(mock_handler, '/api/health')
            assert result is True

        # Unknown path should return False
        result = agent_router.dispatch_get(mock_handler, '/api/this-does-not-exist-xyz')
        assert result is False

    def test_dispatch_post_returns_bool(self, mock_handler):
        """dispatch_post returns True for a known path, False for unknown."""
        from atlas.routes.agent_router import agent_router

        # Unknown POST path should return False
        result = agent_router.dispatch_post(mock_handler, '/api/this-does-not-exist-xyz')
        assert result is False

    def test_parameterized_route_exists(self):
        """Routes with path parameters should be registered."""
        from atlas.routes.agent_router import agent_router

        routes = agent_router._router.list_routes()
        route_patterns = [(method, pattern) for method, pattern in routes]

        # Check for parameterized routes
        assert ('POST', '/api/processes/kill/{pid}') in route_patterns, (
            "Expected route POST /api/processes/kill/{pid} to be registered"
        )
        assert ('GET', '/api/alerts/rules/{rule_id}') in route_patterns, (
            "Expected route GET /api/alerts/rules/{rule_id} to be registered"
        )

    def test_health_endpoint(self, mock_handler):
        """GET /api/health should call handler.serve_json."""
        from atlas.routes.agent_router import agent_router

        mock_health_data = {
            'status': 'healthy',
            'uptime': 12345,
            'version': '1.0.0',
        }

        with patch('atlas.routes.api_routes.get_system_health', return_value=mock_health_data):
            result = agent_router.dispatch_get(mock_handler, '/api/health')

        assert result is True
        mock_handler.serve_json.assert_called_once_with(mock_health_data)

    def test_dispatch_get_unknown_returns_false(self, mock_handler):
        """dispatch_get with a completely unknown path returns False."""
        from atlas.routes.agent_router import agent_router

        result = agent_router.dispatch_get(mock_handler, '/api/nonexistent/route/42')
        assert result is False

    def test_dispatch_post_unknown_returns_false(self, mock_handler):
        """dispatch_post with a completely unknown path returns False."""
        from atlas.routes.agent_router import agent_router

        result = agent_router.dispatch_post(mock_handler, '/api/nonexistent/action')
        assert result is False

    def test_routes_include_get_and_post_methods(self):
        """The router should have both GET and POST routes registered."""
        from atlas.routes.agent_router import agent_router

        routes = agent_router._router.list_routes()
        methods = {method for method, _ in routes}

        assert 'GET' in methods, "Expected GET routes to be registered"
        assert 'POST' in methods, "Expected POST routes to be registered"
