"""
Fleet Server Router

Clean route registration and dispatch system to replace massive if/elif chains.
Extracted from fleet_server.py (Phase 4: Fleet Server Decomposition)

This module provides:
- Route registration by method and path
- Pattern matching for dynamic routes (e.g., /api/machine/{id})
- Middleware support for authentication, logging, etc.
- Automatic 404 handling
- Clean separation of routing from handler logic

Migration completed: December 31, 2025
"""
import re
import logging
from typing import Callable, Dict, List, Tuple, Optional, Any
from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


class Route:
    """Represents a single route with pattern matching"""

    def __init__(self, method: str, pattern: str, handler: Callable, middleware: Optional[List[Callable]] = None):
        """Initialize a route

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            pattern: URL pattern (e.g., '/api/fleet/machines' or '/api/machine/{id}')
            handler: Callable that handles the request
            middleware: Optional list of middleware functions to run before handler
        """
        self.method = method.upper()
        self.pattern = pattern
        self.handler = handler
        self.middleware = middleware or []

        # Convert pattern to regex for matching
        # Replace {param} with named capture groups
        regex_pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern)
        regex_pattern = f"^{regex_pattern}$"
        self.regex = re.compile(regex_pattern)

    def matches(self, method: str, path: str) -> Tuple[bool, Dict[str, str]]:
        """Check if this route matches the given method and path

        Args:
            method: HTTP method
            path: Request path

        Returns:
            Tuple of (matches: bool, params: Dict[str, str])
            params contains any captured path parameters
        """
        if self.method != method.upper():
            return False, {}

        match = self.regex.match(path)
        if match:
            return True, match.groupdict()

        return False, {}


class FleetRouter:
    """HTTP router for fleet server with clean route registration

    Replaces massive if/elif chains with a clean, maintainable route registry.
    Supports pattern matching, middleware, and automatic 404 handling.
    """

    def __init__(self):
        """Initialize the router"""
        self.routes: List[Route] = []
        self.global_middleware: List[Callable] = []

    def register(self, method: str, pattern: str, handler: Callable, middleware: Optional[List[Callable]] = None):
        """Register a route

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            pattern: URL pattern (supports {param} placeholders)
            handler: Handler function
            middleware: Optional middleware for this specific route

        Example:
            router.register('GET', '/api/fleet/machines', handle_machines_list)
            router.register('GET', '/api/machine/{id}', handle_machine_detail)
        """
        route = Route(method, pattern, handler, middleware)
        self.routes.append(route)
        logger.debug(f"Registered route: {method} {pattern}")

    def add_route(self, method: str, pattern: str, handler: Callable, middleware: Optional[List[Callable]] = None):
        """Alias for register() for compatibility with auth_routes"""
        self.register(method, pattern, handler, middleware)

    def get(self, pattern: str, handler: Callable, middleware: Optional[List[Callable]] = None):
        """Register a GET route (convenience method)"""
        self.register('GET', pattern, handler, middleware)

    def post(self, pattern: str, handler: Callable, middleware: Optional[List[Callable]] = None):
        """Register a POST route (convenience method)"""
        self.register('POST', pattern, handler, middleware)

    def put(self, pattern: str, handler: Callable, middleware: Optional[List[Callable]] = None):
        """Register a PUT route (convenience method)"""
        self.register('PUT', pattern, handler, middleware)

    def delete(self, pattern: str, handler: Callable, middleware: Optional[List[Callable]] = None):
        """Register a DELETE route (convenience method)"""
        self.register('DELETE', pattern, handler, middleware)

    def add_global_middleware(self, middleware: Callable):
        """Add middleware that runs before all routes

        Args:
            middleware: Middleware function

        Middleware should return None to continue, or a response to short-circuit.
        """
        self.global_middleware.append(middleware)

    def dispatch(self, handler: BaseHTTPRequestHandler, method: str, path: str) -> bool:
        """Dispatch request to appropriate route handler

        Args:
            handler: HTTP request handler instance
            method: HTTP method
            path: Request path

        Returns:
            True if route was found and handled, False if 404

        The handler instance is passed to route handlers so they can access
        request data and send responses.
        """
        # Strip query string from path for matching
        path_only = path.split('?')[0]

        # Run global middleware
        for middleware_func in self.global_middleware:
            result = middleware_func(handler)
            if result is not None:
                # Middleware returned a response, short-circuit
                return True

        # Find matching route
        for route in self.routes:
            matches, params = route.matches(method, path_only)

            if matches:
                # Run route-specific middleware
                for middleware_func in route.middleware:
                    result = middleware_func(handler)
                    if result is not None:
                        # Middleware returned a response, short-circuit
                        return True

                # Call the handler with params
                try:
                    if params:
                        # Pass path params to handler
                        route.handler(handler, **params)
                    else:
                        route.handler(handler)
                    return True

                except Exception as e:
                    logger.error(f"Error handling route {method} {path}: {e}")
                    import traceback
                    traceback.print_exc()

                    # Send 500 - JSON for API routes, HTML for page routes
                    if path_only.startswith('/api/'):
                        send_error(handler, 'Internal server error')
                    else:
                        handler.send_response(500)
                        handler.send_header('Content-type', 'text/html')
                        handler.end_headers()
                        handler.wfile.write(
                            b'<html><body><h1>500 Internal Server Error</h1>'
                            b'<p>An error occurred processing your request.</p></body></html>'
                        )
                    return True

        # No route matched
        return False

    def send_404(self, handler: BaseHTTPRequestHandler, path: str = ''):
        """Send 404 Not Found response

        Args:
            handler: HTTP request handler
            path: Request path (used to determine JSON vs HTML response)
        """
        if path.startswith('/api/'):
            send_error(handler, 'Not found', status=404)
        else:
            handler.send_response(404)
            handler.send_header('Content-type', 'text/html')
            handler.end_headers()
            handler.wfile.write(
                b'<html><body><h1>404 Not Found</h1>'
                b'<p>The requested resource was not found.</p></body></html>'
            )

    def handle_request(self, handler: BaseHTTPRequestHandler, method: str, path: str):
        """Handle request with automatic 404 fallback

        Args:
            handler: HTTP request handler instance
            method: HTTP method
            path: Request path

        This is the main entry point for routing. It dispatches to a route
        handler or sends a 404 if no route matches.
        """
        handled = self.dispatch(handler, method, path)

        if not handled:
            self.send_404(handler, path)

    def list_routes(self) -> List[Tuple[str, str]]:
        """List all registered routes

        Returns:
            List of (method, pattern) tuples
        """
        return [(route.method, route.pattern) for route in self.routes]


MAX_REQUEST_BODY = 10 * 1024 * 1024  # 10 MB default


# --- API Response Helpers ---
# Reduce boilerplate and ensure consistent JSON responses across all routes.

def send_json(handler, data, status=200, cache=False):
    """Send a JSON response with standard headers.

    Args:
        handler: HTTP request handler instance
        data: Dictionary to serialize as JSON
        status: HTTP status code (default 200)
        cache: If False (default), adds no-cache headers
    """
    import json
    handler.send_response(status)
    handler.send_header('Content-type', 'application/json')
    if not cache:
        handler.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode())


def send_error(handler, message, status=500, extra=None):
    """Send a JSON error response.

    Args:
        handler: HTTP request handler instance
        message: Error message string
        status: HTTP status code (default 500)
        extra: Optional dict of additional fields to include in response
    """
    data = {'error': message}
    if extra:
        data.update(extra)
    send_json(handler, data, status=status)


def send_unauthorized(handler):
    """Send a 401 Unauthorized JSON response."""
    send_error(handler, 'Unauthorized', status=401)


def validate_required_fields(data, fields):
    """Validate that required fields are present in request data.

    Args:
        data: Parsed request data dict
        fields: List of required field names

    Returns:
        List of missing field names (empty if all present)
    """
    return [f for f in fields if not data.get(f)]


def read_request_body(handler, max_size=MAX_REQUEST_BODY):
    """Read and validate request body size.

    Args:
        handler: HTTP request handler instance
        max_size: Maximum allowed body size in bytes

    Returns:
        bytes: The request body, or None if rejected (response already sent)
    """
    content_length = int(handler.headers.get('Content-Length', 0))

    if content_length < 0:
        handler.send_response(400)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(b'{"error": "Invalid Content-Length"}')
        return None

    if content_length > max_size:
        handler.send_response(413)
        handler.send_header('Content-type', 'application/json')
        handler.end_headers()
        handler.wfile.write(b'{"error": "Request body too large"}')
        logger.warning(
            f"Rejected request with body size {content_length} bytes "
            f"(max {max_size}) from {handler.client_address[0]}"
        )
        return None

    if content_length == 0:
        return b''

    return handler.rfile.read(content_length)


# Export for easy import
__all__ = [
    'FleetRouter', 'Route', 'read_request_body', 'MAX_REQUEST_BODY',
    'send_json', 'send_error', 'send_unauthorized', 'validate_required_fields',
]
