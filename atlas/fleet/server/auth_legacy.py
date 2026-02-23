"""
Fleet Authentication Manager

Centralized authentication and session management for fleet server.
Extracted from fleet_server.py (Phase 4: Fleet Server Decomposition)

This module provides:
- Session token extraction from cookies
- Session validation via FleetUserManager
- API key validation
- Authentication decorators
- 401 response generation

Migration completed: December 31, 2025
"""
import logging
import http.cookies
from typing import Optional, Tuple, Callable, Any
from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


class FleetAuthManager:
    """Manages authentication for fleet server

    Provides session-based authentication for web UI and API key
    authentication for agent API calls.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize authentication manager

        Args:
            api_key: Optional API key for agent authentication
        """
        self.api_key = api_key

    @staticmethod
    def get_session_token(handler: BaseHTTPRequestHandler) -> Optional[str]:
        """Extract session token from HTTP cookie header

        Args:
            handler: HTTP request handler with headers

        Returns:
            Session token string or None if not found
        """
        cookie_header = handler.headers.get('Cookie')
        if not cookie_header:
            return None

        cookies = http.cookies.SimpleCookie()
        cookies.load(cookie_header)

        if 'fleet_session' in cookies:
            return cookies['fleet_session'].value
        return None

    @staticmethod
    def check_web_auth(handler: BaseHTTPRequestHandler) -> Tuple[bool, Optional[str]]:
        """Check session-based authentication for web UI

        Validates session token from cookie against FleetUserManager.

        Args:
            handler: HTTP request handler with cookie headers

        Returns:
            Tuple of (is_authenticated, username)
            - is_authenticated: True if valid session
            - username: Username if authenticated, None otherwise
        """
        try:
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            # Get session token from cookie
            session_token = FleetAuthManager.get_session_token(handler)

            if not session_token:
                logger.debug("No session token found")
                return False, None

            # Validate session
            is_valid, username = user_manager.validate_session(session_token)

            if not is_valid:
                logger.debug("Invalid or expired session")
                return False, None

            return True, username

        except Exception as e:
            logger.error(f"Error in session auth: {e}")
            return False, None

    def check_api_key(self, handler: BaseHTTPRequestHandler) -> bool:
        """Check API key authentication for agent API calls

        Validates X-API-Key header against configured API key.

        Args:
            handler: HTTP request handler with headers

        Returns:
            True if API key is valid or not required, False otherwise
        """
        if not self.api_key:
            return True  # No auth required

        provided_key = handler.headers.get('X-API-Key')
        return provided_key == self.api_key

    @staticmethod
    def send_auth_required(handler: BaseHTTPRequestHandler):
        """Send 401 Unauthorized response

        Sends HTTP 401 with WWW-Authenticate header for browser authentication.

        Args:
            handler: HTTP request handler to send response through
        """
        handler.send_response(401)
        handler.send_header('WWW-Authenticate', 'Basic realm="Fleet Dashboard"')
        handler.send_header('Content-type', 'text/html')
        handler.end_headers()
        handler.wfile.write(
            b'<html><body><h1>401 Unauthorized</h1>'
            b'<p>Authentication required.</p></body></html>'
        )

    @staticmethod
    def send_redirect_to_login(handler: BaseHTTPRequestHandler):
        """Send 302 redirect to login page

        Args:
            handler: HTTP request handler to send response through
        """
        handler.send_response(302)
        handler.send_header('Location', '/login')
        handler.end_headers()

    @staticmethod
    def clear_session_cookie(handler: BaseHTTPRequestHandler):
        """Clear session cookie and redirect to login

        Destroys session and sends redirect with cookie clearing header.

        Args:
            handler: HTTP request handler
        """
        try:
            from atlas.fleet_user_manager import FleetUserManager
            user_manager = FleetUserManager()

            # Get and destroy session
            session_token = FleetAuthManager.get_session_token(handler)
            if session_token:
                user_manager.destroy_session(session_token)

        except Exception as e:
            logger.error(f"Error clearing session: {e}")

        # Send redirect with cookie clearing
        handler.send_response(302)
        handler.send_header('Location', '/login')
        # SECURITY: Include Secure flag on cookie clearing
        handler.send_header(
            'Set-Cookie',
            'fleet_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict; Secure'
        )
        handler.end_headers()


def require_web_auth(handler_method: Callable) -> Callable:
    """Decorator to require web authentication for handler methods

    Checks session authentication and redirects to /login if not authenticated.

    Usage:
        @require_web_auth
        def do_GET(self):
            # Only called if authenticated
            ...

    Args:
        handler_method: Handler method to wrap

    Returns:
        Wrapped method that checks authentication first
    """
    def wrapper(handler: Any, *args, **kwargs):
        is_authenticated, username = FleetAuthManager.check_web_auth(handler)

        if not is_authenticated:
            FleetAuthManager.send_redirect_to_login(handler)
            return

        # Store username in handler for use in method
        handler.authenticated_user = username

        # Call original method
        return handler_method(handler, *args, **kwargs)

    return wrapper


def require_api_key(auth_manager: FleetAuthManager):
    """Decorator factory to require API key for handler methods

    Checks X-API-Key header and sends 401 if invalid.

    Usage:
        auth_mgr = FleetAuthManager(api_key='secret123')

        @require_api_key(auth_mgr)
        def handle_api_call(self):
            # Only called if API key valid
            ...

    Args:
        auth_manager: FleetAuthManager instance with API key

    Returns:
        Decorator function
    """
    def decorator(handler_method: Callable) -> Callable:
        def wrapper(handler: Any, *args, **kwargs):
            if not auth_manager.check_api_key(handler):
                FleetAuthManager.send_auth_required(handler)
                return

            # Call original method
            return handler_method(handler, *args, **kwargs)

        return wrapper

    return decorator


# Export for easy import
__all__ = [
    'FleetAuthManager',
    'require_web_auth',
    'require_api_key'
]
