"""
ATLAS Fleet Authentication Module

Comprehensive authentication system supporting:
- JWT Bearer Tokens for user authentication
- Per-Agent API Keys with scopes and rate limiting
- OAuth2 Authorization Code flow with PKCE
- Session cookie authentication (legacy)

Usage:
    from atlas.fleet.server.auth import (
        get_jwt_manager,
        get_api_key_manager,
        get_oauth2_manager,
        get_auth_middleware,
        require_auth,
        require_scope,
    )

    # Initialize managers
    jwt = get_jwt_manager()
    api_keys = get_api_key_manager()
    middleware = get_auth_middleware()

    # Use decorators on route handlers
    @require_auth
    def protected_handler(handler):
        user = handler.auth_context.user_id
        ...

    @require_scope('metrics:read')
    def metrics_handler(handler):
        ...
"""

# JWT Manager
from .jwt_manager import (
    JWTManager,
    TokenPair,
    TokenClaims,
    get_jwt_manager,
)

# API Key Manager
from .api_key_manager import (
    APIKeyManager,
    get_api_key_manager,
)

# OAuth2 Manager
from .oauth2_manager import (
    OAuth2Manager,
    OAuth2Client,
    AuthorizationCode,
    get_oauth2_manager,
)

# Middleware
from .middleware import (
    AuthContext,
    AuthMiddleware,
    create_auth_middleware,
    get_auth_middleware,
)

# Decorators
from .decorators import (
    require_auth,
    require_jwt,
    require_api_key,
    require_scope,
    require_role,
    require_any,
    optional_auth,
    rate_limit,
    admin_only,
    agent_only,
)

# Scopes
from .scopes import (
    Scope,
    ScopeValidator,
    get_scope_validator,
    DEFAULT_SCOPES,
    ROLE_SCOPES,
)

# Audit Logging
from .audit_log import (
    AuditEventType,
    AuditSeverity,
    AuditLogger,
    get_audit_logger,
)

__all__ = [
    # JWT
    'JWTManager',
    'TokenPair',
    'TokenClaims',
    'get_jwt_manager',

    # API Keys
    'APIKeyManager',
    'get_api_key_manager',

    # OAuth2
    'OAuth2Manager',
    'OAuth2Client',
    'AuthorizationCode',
    'get_oauth2_manager',

    # Middleware
    'AuthContext',
    'AuthMiddleware',
    'create_auth_middleware',
    'get_auth_middleware',

    # Decorators
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

    # Scopes
    'Scope',
    'ScopeValidator',
    'get_scope_validator',
    'DEFAULT_SCOPES',
    'ROLE_SCOPES',

    # Audit Logging
    'AuditEventType',
    'AuditSeverity',
    'AuditLogger',
    'get_audit_logger',

    # Legacy auth (FleetAuthManager)
    'FleetAuthManager',
    'require_web_auth',
]

# Legacy auth (FleetAuthManager, session-based auth from original fleet_server decomposition)
from ..auth_legacy import FleetAuthManager, require_web_auth
__version__ = '1.0.0'
