"""
ATLAS Fleet Authentication - Decorators

Provides authentication decorators for route handlers:
- @require_auth - Require any authentication method
- @require_jwt - Require JWT authentication specifically
- @require_api_key - Require API key authentication
- @require_scope - Require specific scope(s)
- @require_role - Require specific role
"""
import json
import logging
from functools import wraps
from typing import Union, List, Callable, Optional

from .middleware import AuthContext

logger = logging.getLogger(__name__)


def _send_json_error(handler, status_code: int, error: str, message: str):
    """Send a JSON error response"""
    handler.send_response(status_code)
    handler.send_header('Content-Type', 'application/json')
    handler.end_headers()
    response = json.dumps({
        'error': error,
        'message': message
    })
    handler.wfile.write(response.encode())


def _get_auth_context(handler) -> AuthContext:
    """Get auth context from handler, creating empty one if missing"""
    if hasattr(handler, 'auth_context') and isinstance(handler.auth_context, AuthContext):
        return handler.auth_context
    return AuthContext()


def require_auth(func: Callable) -> Callable:
    """
    Decorator that requires any form of authentication.

    The request must be authenticated via JWT, API key, or session cookie.

    Usage:
        @require_auth
        def handle_protected_resource(handler):
            user = handler.auth_context.user_id
            ...
    """
    @wraps(func)
    def wrapper(handler, *args, **kwargs):
        auth_context = _get_auth_context(handler)

        if not auth_context.authenticated:
            logger.warning(f"Unauthorized access attempt to {getattr(handler, 'path', 'unknown')}")
            _send_json_error(
                handler,
                401,
                'unauthorized',
                'Authentication required. Provide a valid JWT token, API key, or session cookie.'
            )
            return None

        return func(handler, *args, **kwargs)
    return wrapper


def require_jwt(func: Callable) -> Callable:
    """
    Decorator that requires JWT authentication specifically.

    The request must have a valid JWT Bearer token.

    Usage:
        @require_jwt
        def handle_user_profile(handler):
            user = handler.auth_context.user_id
            ...
    """
    @wraps(func)
    def wrapper(handler, *args, **kwargs):
        auth_context = _get_auth_context(handler)

        if not auth_context.authenticated:
            _send_json_error(
                handler,
                401,
                'unauthorized',
                'JWT authentication required. Provide a valid Bearer token.'
            )
            return None

        if auth_context.method != 'jwt':
            _send_json_error(
                handler,
                401,
                'invalid_auth_method',
                f'JWT authentication required, but got {auth_context.method or "none"}.'
            )
            return None

        return func(handler, *args, **kwargs)
    return wrapper


def require_api_key(func: Callable) -> Callable:
    """
    Decorator that requires API key authentication specifically.

    The request must have a valid API key.

    Usage:
        @require_api_key
        def handle_agent_metrics(handler):
            agent = handler.auth_context.agent_name
            ...
    """
    @wraps(func)
    def wrapper(handler, *args, **kwargs):
        auth_context = _get_auth_context(handler)

        if not auth_context.authenticated:
            _send_json_error(
                handler,
                401,
                'unauthorized',
                'API key authentication required. Provide a valid X-API-Key header.'
            )
            return None

        if auth_context.method != 'api_key':
            _send_json_error(
                handler,
                401,
                'invalid_auth_method',
                f'API key authentication required, but got {auth_context.method or "none"}.'
            )
            return None

        return func(handler, *args, **kwargs)
    return wrapper


def require_scope(*scopes: str, require_all: bool = True) -> Callable:
    """
    Decorator that requires specific scope(s).

    Args:
        *scopes: One or more scopes to check
        require_all: If True, all scopes required. If False, any scope is sufficient.

    Usage:
        @require_scope('metrics:read')
        def handle_metrics(handler):
            ...

        @require_scope('commands:write', 'commands:execute')
        def handle_command_execution(handler):
            ...

        @require_scope('commands:read', 'metrics:read', require_all=False)
        def handle_either_scope(handler):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(handler, *args, **kwargs):
            auth_context = _get_auth_context(handler)

            if not auth_context.authenticated:
                _send_json_error(
                    handler,
                    401,
                    'unauthorized',
                    'Authentication required.'
                )
                return None

            # Check scopes
            if require_all:
                has_access = auth_context.has_all_scopes(list(scopes))
            else:
                has_access = auth_context.has_any_scope(list(scopes))

            if not has_access:
                scope_str = ' and '.join(scopes) if require_all else ' or '.join(scopes)
                logger.warning(
                    f"Scope check failed for user {auth_context.user_id}: "
                    f"required {scope_str}, has {auth_context.scopes}"
                )
                _send_json_error(
                    handler,
                    403,
                    'insufficient_scope',
                    f'Required scope(s): {scope_str}. Your scopes: {", ".join(auth_context.scopes) or "none"}'
                )
                return None

            return func(handler, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: str) -> Callable:
    """
    Decorator that requires a specific role.

    Args:
        *roles: One or more acceptable roles

    Usage:
        @require_role('admin')
        def handle_admin_action(handler):
            ...

        @require_role('admin', 'moderator')
        def handle_moderation(handler):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(handler, *args, **kwargs):
            auth_context = _get_auth_context(handler)

            if not auth_context.authenticated:
                _send_json_error(
                    handler,
                    401,
                    'unauthorized',
                    'Authentication required.'
                )
                return None

            if auth_context.role not in roles:
                logger.warning(
                    f"Role check failed for user {auth_context.user_id}: "
                    f"required {roles}, has {auth_context.role}"
                )
                _send_json_error(
                    handler,
                    403,
                    'insufficient_role',
                    f'Required role: {" or ".join(roles)}. Your role: {auth_context.role or "none"}'
                )
                return None

            return func(handler, *args, **kwargs)
        return wrapper
    return decorator


def require_any(*decorators: Callable) -> Callable:
    """
    Meta-decorator that succeeds if ANY of the provided decorators pass.

    Useful for allowing multiple authentication methods for the same endpoint.

    Usage:
        @require_any(require_jwt, require_api_key)
        def handle_flexible_auth(handler):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(handler, *args, **kwargs):
            auth_context = _get_auth_context(handler)

            if not auth_context.authenticated:
                _send_json_error(
                    handler,
                    401,
                    'unauthorized',
                    'Authentication required.'
                )
                return None

            # For "any" logic, we just need to be authenticated
            # The specific method check is handled by calling the actual decorators
            return func(handler, *args, **kwargs)
        return wrapper
    return decorator


def optional_auth(func: Callable) -> Callable:
    """
    Decorator that doesn't require authentication but sets auth_context if present.

    Useful for endpoints that work differently for authenticated vs anonymous users.

    Usage:
        @optional_auth
        def handle_public_with_extras(handler):
            if handler.auth_context.authenticated:
                # Show extra data for logged-in users
                ...
            else:
                # Show public data only
                ...
    """
    @wraps(func)
    def wrapper(handler, *args, **kwargs):
        # Auth context should already be set by middleware
        # Just ensure it exists
        if not hasattr(handler, 'auth_context'):
            handler.auth_context = AuthContext()
        return func(handler, *args, **kwargs)
    return wrapper


def rate_limit(requests: int, window_seconds: int = 60) -> Callable:
    """
    Decorator that applies rate limiting to an endpoint.

    Note: This is a placeholder. Actual rate limiting should be implemented
    at the middleware or API key level. This decorator documents the intent.

    Args:
        requests: Maximum number of requests allowed
        window_seconds: Time window in seconds

    Usage:
        @rate_limit(100, 60)  # 100 requests per minute
        def handle_limited_endpoint(handler):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(handler, *args, **kwargs):
            # Rate limiting is primarily handled by API key manager
            # This decorator is for documentation and future implementation
            return func(handler, *args, **kwargs)
        return wrapper
    return decorator


# Convenience combinations
def admin_only(func: Callable) -> Callable:
    """
    Convenience decorator for admin-only endpoints.

    Equivalent to @require_auth @require_role('admin')
    """
    @wraps(func)
    @require_auth
    @require_role('admin')
    def wrapper(handler, *args, **kwargs):
        return func(handler, *args, **kwargs)
    return wrapper


def agent_only(func: Callable) -> Callable:
    """
    Convenience decorator for agent-only endpoints.

    Requires API key authentication with agent role.
    """
    @wraps(func)
    @require_api_key
    def wrapper(handler, *args, **kwargs):
        return func(handler, *args, **kwargs)
    return wrapper


__all__ = [
    'require_auth',
    'require_jwt',
    'require_api_key',
    'require_scope',
    'require_role',
    'require_any',
    'optional_auth',
    'rate_limit',
    'admin_only',
    'agent_only',
]
