"""
ATLAS Fleet Authentication - Middleware

Provides authentication middleware for the router that validates:
1. JWT Bearer tokens (highest priority)
2. API Keys (for agents)
3. Session cookies (legacy web sessions)

Sets handler.auth_context with authentication details.
"""
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class AuthContext:
    """Authentication context attached to request handlers"""
    authenticated: bool = False
    method: Optional[str] = None  # 'jwt', 'api_key', 'session', None
    user_id: Optional[str] = None
    role: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    agent_id: Optional[str] = None  # For API key auth
    agent_name: Optional[str] = None  # For API key auth
    key_id: Optional[str] = None  # For API key auth
    token_jti: Optional[str] = None  # For JWT auth
    session_id: Optional[str] = None  # For session auth
    ip_address: Optional[str] = None

    def has_scope(self, scope: str) -> bool:
        """Check if context has a specific scope"""
        if 'admin:all' in self.scopes:
            return True
        return scope in self.scopes

    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if context has any of the specified scopes"""
        if 'admin:all' in self.scopes:
            return True
        return any(s in self.scopes for s in scopes)

    def has_all_scopes(self, scopes: List[str]) -> bool:
        """Check if context has all specified scopes"""
        if 'admin:all' in self.scopes:
            return True
        return all(s in self.scopes for s in scopes)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'authenticated': self.authenticated,
            'method': self.method,
            'user_id': self.user_id,
            'role': self.role,
            'scopes': self.scopes,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
        }


class AuthMiddleware:
    """
    Authentication middleware for the ATLAS router.

    Validates authentication credentials in the following priority:
    1. JWT Bearer token in Authorization header
    2. API Key in X-API-Key header or Authorization header
    3. Session cookie

    Usage:
        middleware = AuthMiddleware(jwt_manager, api_key_manager, user_manager)
        router.use(middleware)
    """

    def __init__(
        self,
        jwt_manager=None,
        api_key_manager=None,
        user_manager=None,
        db_path: str = "~/.fleet-data/users.db"
    ):
        """
        Initialize the auth middleware.

        Args:
            jwt_manager: JWTManager instance for JWT validation
            api_key_manager: APIKeyManager instance for API key validation
            user_manager: FleetUserManager instance for session validation
            db_path: Path to the user database
        """
        self.jwt_manager = jwt_manager
        self.api_key_manager = api_key_manager
        self.user_manager = user_manager
        self.db_path = db_path

        # Lazy initialization
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialize managers if not provided"""
        if self._initialized:
            return

        if self.jwt_manager is None:
            try:
                from .jwt_manager import get_jwt_manager
                self.jwt_manager = get_jwt_manager(self.db_path)
            except ImportError:
                logger.warning("JWT manager not available")

        if self.api_key_manager is None:
            try:
                from .api_key_manager import get_api_key_manager
                self.api_key_manager = get_api_key_manager(self.db_path)
            except ImportError:
                logger.warning("API key manager not available")

        self._initialized = True

    def _get_client_ip(self, handler) -> str:
        """Extract client IP from request"""
        # Check X-Forwarded-For header first (for proxied requests)
        forwarded = handler.headers.get('X-Forwarded-For', '')
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(',')[0].strip()

        # Check X-Real-IP header
        real_ip = handler.headers.get('X-Real-IP', '')
        if real_ip:
            return real_ip.strip()

        # Fall back to client address
        if hasattr(handler, 'client_address') and handler.client_address:
            return handler.client_address[0]

        return 'unknown'

    def _extract_bearer_token(self, handler) -> Optional[str]:
        """Extract Bearer token from Authorization header"""
        auth_header = handler.headers.get('Authorization', '')
        if auth_header.lower().startswith('bearer '):
            return auth_header[7:].strip()
        return None

    def _extract_api_key(self, handler) -> Optional[str]:
        """Extract API key from headers"""
        # Check X-API-Key header first
        api_key = handler.headers.get('X-API-Key', '')
        if api_key:
            return api_key.strip()

        # Check Authorization header with ApiKey scheme
        auth_header = handler.headers.get('Authorization', '')
        if auth_header.lower().startswith('apikey '):
            return auth_header[7:].strip()

        return None

    def _extract_session_cookie(self, handler) -> Optional[str]:
        """Extract session ID from cookies"""
        cookie_header = handler.headers.get('Cookie', '')
        if not cookie_header:
            return None

        # Parse cookies
        cookies = {}
        for item in cookie_header.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                cookies[name.strip()] = value.strip()

        return cookies.get('session_id')

    def _validate_jwt(self, token: str, ip_address: str) -> Optional[AuthContext]:
        """Validate JWT and return auth context"""
        if not self.jwt_manager:
            return None

        claims = self.jwt_manager.validate_access_token(token)
        if not claims:
            return None

        return AuthContext(
            authenticated=True,
            method='jwt',
            user_id=claims.sub,
            role=claims.role,
            scopes=claims.scopes,
            token_jti=claims.jti,
            ip_address=ip_address
        )

    def _validate_api_key(self, api_key: str, ip_address: str, handler) -> Optional[AuthContext]:
        """Validate API key and return auth context"""
        if not self.api_key_manager:
            return None

        # Get request path and method for rate limiting
        path = getattr(handler, 'path', '/')
        method = getattr(handler, 'command', 'GET')

        result = self.api_key_manager.validate_key(api_key, ip_address, path, method)
        if not result:
            return None

        return AuthContext(
            authenticated=True,
            method='api_key',
            user_id=result.get('created_by'),
            role='agent',  # API keys are typically for agents
            scopes=result.get('scopes', []),
            agent_id=result.get('agent_id'),
            agent_name=result.get('agent_name'),
            key_id=result.get('id'),
            ip_address=ip_address
        )

    def _validate_session(self, session_id: str, ip_address: str) -> Optional[AuthContext]:
        """Validate session cookie and return auth context"""
        if not self.user_manager:
            return None

        # Get session info from user manager
        session = self.user_manager.get_session(session_id) if hasattr(self.user_manager, 'get_session') else None
        if not session:
            return None

        # Check if session is valid
        if not session.get('is_valid', False):
            return None

        return AuthContext(
            authenticated=True,
            method='session',
            user_id=session.get('username'),
            role=session.get('role', 'viewer'),
            scopes=self._get_scopes_for_role(session.get('role', 'viewer')),
            session_id=session_id,
            ip_address=ip_address
        )

    def _get_scopes_for_role(self, role: str) -> List[str]:
        """Get default scopes for a role"""
        from .scopes import ROLE_SCOPES
        return ROLE_SCOPES.get(role, ['metrics:read'])

    def __call__(self, handler) -> AuthContext:
        """
        Process authentication for a request.

        This method is called by the router before handling the request.
        It sets handler.auth_context with the authentication result.

        Args:
            handler: The request handler

        Returns:
            AuthContext with authentication details
        """
        self._ensure_initialized()

        ip_address = self._get_client_ip(handler)
        auth_context = AuthContext(ip_address=ip_address)

        # Priority 1: JWT Bearer token
        bearer_token = self._extract_bearer_token(handler)
        if bearer_token:
            jwt_context = self._validate_jwt(bearer_token, ip_address)
            if jwt_context:
                auth_context = jwt_context
                logger.debug(f"JWT auth successful for user: {auth_context.user_id}")
            else:
                logger.debug("JWT validation failed")

        # Priority 2: API Key (only if JWT not authenticated)
        if not auth_context.authenticated:
            api_key = self._extract_api_key(handler)
            if api_key:
                key_context = self._validate_api_key(api_key, ip_address, handler)
                if key_context:
                    auth_context = key_context
                    logger.debug(f"API key auth successful for agent: {auth_context.agent_name}")
                else:
                    logger.debug("API key validation failed")

        # Priority 3: Session cookie (only if neither JWT nor API key authenticated)
        if not auth_context.authenticated:
            session_id = self._extract_session_cookie(handler)
            if session_id:
                session_context = self._validate_session(session_id, ip_address)
                if session_context:
                    auth_context = session_context
                    logger.debug(f"Session auth successful for user: {auth_context.user_id}")
                else:
                    logger.debug("Session validation failed")

        # Attach context to handler
        handler.auth_context = auth_context

        # Return None so the router continues to the route handler
        # (returning non-None would short-circuit the request)
        return None


def create_auth_middleware(
    jwt_manager=None,
    api_key_manager=None,
    user_manager=None,
    db_path: str = "~/.fleet-data/users.db"
) -> AuthMiddleware:
    """
    Factory function to create an AuthMiddleware instance.

    Args:
        jwt_manager: Optional JWTManager instance
        api_key_manager: Optional APIKeyManager instance
        user_manager: Optional FleetUserManager instance
        db_path: Path to the user database

    Returns:
        Configured AuthMiddleware instance
    """
    return AuthMiddleware(
        jwt_manager=jwt_manager,
        api_key_manager=api_key_manager,
        user_manager=user_manager,
        db_path=db_path
    )


# Singleton instance
_auth_middleware: Optional[AuthMiddleware] = None


def get_auth_middleware(db_path: str = "~/.fleet-data/users.db") -> AuthMiddleware:
    """Get or create the auth middleware singleton"""
    global _auth_middleware
    if _auth_middleware is None:
        _auth_middleware = AuthMiddleware(db_path=db_path)
    return _auth_middleware


__all__ = [
    'AuthContext',
    'AuthMiddleware',
    'create_auth_middleware',
    'get_auth_middleware',
]
