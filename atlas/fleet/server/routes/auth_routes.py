"""
ATLAS Fleet Authentication - API Routes

Provides REST API endpoints for authentication:
- /api/auth/login - User login, returns JWT tokens
- /api/auth/login/touchid - TouchID login (macOS only)
- /api/auth/touchid/available - Check TouchID availability
- /api/auth/refresh - Refresh access token
- /api/auth/logout - Revoke tokens
- /api/auth/me - Current user info
- /api/auth/api-keys - API key management
- /api/auth/oauth/* - OAuth2 endpoints
- /api/auth/sessions - Active sessions
- /api/auth/scopes - Available scopes
"""
import json
import logging
from typing import Optional, Dict, Any
from urllib.parse import parse_qs, urlencode

logger = logging.getLogger(__name__)

# Import TouchID functions from dashboard_auth
try:
    from atlas.dashboard_auth import check_touchid_available, authenticate_with_touchid
    TOUCHID_AVAILABLE = True
except ImportError:
    TOUCHID_AVAILABLE = False
    def check_touchid_available():
        return False
    def authenticate_with_touchid(reason=""):
        return False, "TouchID not available"


class AuthRoutes:
    """
    Authentication API route handlers.

    These handlers are designed to work with the ATLAS router system.
    Each method handles a specific endpoint and auth operation.
    """

    def __init__(
        self,
        jwt_manager=None,
        api_key_manager=None,
        oauth2_manager=None,
        user_manager=None,
        scope_validator=None,
        db_path: str = "~/.fleet-data/users.db"
    ):
        """
        Initialize auth routes.

        Args:
            jwt_manager: JWTManager instance
            api_key_manager: APIKeyManager instance
            oauth2_manager: OAuth2Manager instance
            user_manager: FleetUserManager instance
            scope_validator: ScopeValidator instance
            db_path: Path to the database
        """
        self.jwt_manager = jwt_manager
        self.api_key_manager = api_key_manager
        self.oauth2_manager = oauth2_manager
        self.user_manager = user_manager
        self.scope_validator = scope_validator
        self.db_path = db_path
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialize managers if not provided"""
        if self._initialized:
            return

        from pathlib import Path
        db_path = str(Path(self.db_path).expanduser())

        if self.jwt_manager is None:
            try:
                from ..auth.jwt_manager import get_jwt_manager
                self.jwt_manager = get_jwt_manager(db_path)
            except ImportError as e:
                logger.warning(f"JWT manager not available: {e}")

        if self.api_key_manager is None:
            try:
                from ..auth.api_key_manager import get_api_key_manager
                self.api_key_manager = get_api_key_manager(db_path)
            except ImportError as e:
                logger.warning(f"API key manager not available: {e}")

        if self.oauth2_manager is None:
            try:
                from ..auth.oauth2_manager import get_oauth2_manager
                self.oauth2_manager = get_oauth2_manager(db_path, self.jwt_manager)
            except ImportError as e:
                logger.warning(f"OAuth2 manager not available: {e}")

        if self.scope_validator is None:
            try:
                from ..auth.scopes import get_scope_validator
                self.scope_validator = get_scope_validator(db_path)
            except ImportError as e:
                logger.warning(f"Scope validator not available: {e}")

        self._initialized = True

    def _send_json(self, handler, data: Dict, status_code: int = 200):
        """Send JSON response"""
        handler.send_response(status_code)
        handler.send_header('Content-Type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps(data).encode())

    def _send_error(self, handler, error: str, message: str, status_code: int = 400):
        """Send JSON error response"""
        self._send_json(handler, {'error': error, 'message': message}, status_code)

    def _get_json_body(self, handler) -> Optional[Dict]:
        """Parse JSON request body"""
        try:
            content_length = int(handler.headers.get('Content-Length', 0))
            if content_length == 0:
                return {}
            body = handler.rfile.read(content_length)
            return json.loads(body.decode())
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON body: {e}")
            return None

    def _get_client_ip(self, handler) -> str:
        """Get client IP address"""
        forwarded = handler.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        real_ip = handler.headers.get('X-Real-IP', '')
        if real_ip:
            return real_ip.strip()
        if hasattr(handler, 'client_address') and handler.client_address:
            return handler.client_address[0]
        return 'unknown'

    # User Authentication Endpoints

    def handle_login(self, handler):
        """
        POST /api/auth/login
        Authenticate user and return JWT tokens.

        Request body:
        {
            "username": "string",
            "password": "string",
            "device_name": "string" (optional)
        }

        Response:
        {
            "access_token": "string",
            "refresh_token": "string",
            "token_type": "Bearer",
            "expires_in": 900,
            "user": {...}
        }
        """
        self._ensure_initialized()

        body = self._get_json_body(handler)
        if body is None:
            return self._send_error(handler, 'invalid_request', 'Invalid JSON body')

        username = body.get('username', '').strip()
        password = body.get('password', '')
        device_name = body.get('device_name', 'unknown')

        if not username or not password:
            return self._send_error(handler, 'invalid_request', 'Username and password required')

        # Verify credentials
        if not self.user_manager:
            return self._send_error(handler, 'server_error', 'User manager not available', 500)

        user = self.user_manager.verify_password(username, password)
        if not user:
            logger.warning(f"Login failed for user: {username}")
            return self._send_error(handler, 'invalid_credentials', 'Invalid username or password', 401)

        # Generate tokens
        if not self.jwt_manager:
            return self._send_error(handler, 'server_error', 'JWT manager not available', 500)

        role = user.get('role', 'viewer')
        scopes = self.scope_validator.get_scopes_for_role(role) if self.scope_validator else []
        ip_address = self._get_client_ip(handler)

        token_pair = self.jwt_manager.create_token_pair(
            user_id=username,
            role=role,
            scopes=scopes,
            device_name=device_name,
            ip_address=ip_address
        )

        if not token_pair:
            return self._send_error(handler, 'server_error', 'Failed to generate tokens', 500)

        logger.info(f"Login successful for user: {username}")
        self._send_json(handler, {
            'access_token': token_pair.access_token,
            'refresh_token': token_pair.refresh_token,
            'token_type': 'Bearer',
            'expires_in': 900,
            'user': {
                'username': username,
                'role': role,
                'scopes': scopes
            }
        })

    def handle_touchid_available(self, handler):
        """
        GET /api/auth/touchid/available
        Check if TouchID is available on this system.

        Response:
        {
            "available": true/false,
            "message": "string"
        }
        """
        available = check_touchid_available()
        self._send_json(handler, {
            'available': available,
            'message': 'TouchID is available' if available else 'TouchID not available on this system'
        })

    def handle_touchid_login(self, handler):
        """
        POST /api/auth/login/touchid
        Authenticate using TouchID (macOS only).
        Requires a pre-authenticated user context (username provided in body).

        Request body:
        {
            "username": "string",  // Optional: Use for user-specific session
            "device_name": "string" (optional)
        }

        Response:
        {
            "access_token": "string",
            "refresh_token": "string",
            "token_type": "Bearer",
            "expires_in": 900,
            "user": {...}
        }
        """
        self._ensure_initialized()

        # Check if TouchID is available
        if not check_touchid_available():
            return self._send_error(handler, 'touchid_unavailable', 'TouchID is not available on this system', 400)

        body = self._get_json_body(handler) or {}
        username = body.get('username', '').strip()
        device_name = body.get('device_name', 'TouchID Device')

        # Perform TouchID authentication
        success, message = authenticate_with_touchid("authenticate to ATLAS Fleet Dashboard")

        if not success:
            logger.warning(f"TouchID authentication failed: {message}")
            return self._send_error(handler, 'touchid_failed', message, 401)

        # If username is provided and we have a user manager, verify user exists
        if username and self.user_manager:
            user = self.user_manager.get_user(username)
            if not user:
                return self._send_error(handler, 'invalid_user', 'User not found', 401)
            role = user.get('role', 'viewer')
        else:
            # Default to admin role for TouchID without specific user
            username = 'touchid_user'
            role = 'admin'

        # Generate tokens
        if not self.jwt_manager:
            return self._send_error(handler, 'server_error', 'JWT manager not available', 500)

        scopes = self.scope_validator.get_scopes_for_role(role) if self.scope_validator else []
        ip_address = self._get_client_ip(handler)

        token_pair = self.jwt_manager.create_token_pair(
            user_id=username,
            role=role,
            scopes=scopes,
            device_name=device_name,
            ip_address=ip_address
        )

        if not token_pair:
            return self._send_error(handler, 'server_error', 'Failed to generate tokens', 500)

        logger.info(f"TouchID login successful for user: {username}")
        self._send_json(handler, {
            'access_token': token_pair.access_token,
            'refresh_token': token_pair.refresh_token,
            'token_type': 'Bearer',
            'expires_in': 900,
            'user': {
                'username': username,
                'role': role,
                'scopes': scopes,
                'auth_method': 'touchid'
            }
        })

    def handle_refresh(self, handler):
        """
        POST /api/auth/refresh
        Refresh access token using refresh token.

        Request body:
        {
            "refresh_token": "string"
        }

        Response:
        {
            "access_token": "string",
            "refresh_token": "string",
            "token_type": "Bearer",
            "expires_in": 900
        }
        """
        self._ensure_initialized()

        body = self._get_json_body(handler)
        if body is None:
            return self._send_error(handler, 'invalid_request', 'Invalid JSON body')

        refresh_token = body.get('refresh_token', '').strip()
        if not refresh_token:
            return self._send_error(handler, 'invalid_request', 'Refresh token required')

        if not self.jwt_manager:
            return self._send_error(handler, 'server_error', 'JWT manager not available', 500)

        ip_address = self._get_client_ip(handler)
        token_pair = self.jwt_manager.refresh_access_token(refresh_token, ip_address)

        if not token_pair:
            return self._send_error(handler, 'invalid_token', 'Invalid or expired refresh token', 401)

        logger.debug(f"Token refreshed for user: {token_pair.access_token[:20]}...")
        self._send_json(handler, {
            'access_token': token_pair.access_token,
            'refresh_token': token_pair.refresh_token,
            'token_type': 'Bearer',
            'expires_in': 900
        })

    def handle_logout(self, handler):
        """
        POST /api/auth/logout
        Revoke current tokens.

        Request body (optional):
        {
            "refresh_token": "string",
            "all_devices": false
        }
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        body = self._get_json_body(handler) or {}
        all_devices = body.get('all_devices', False)

        if not self.jwt_manager:
            return self._send_error(handler, 'server_error', 'JWT manager not available', 500)

        if all_devices:
            # Revoke all user tokens
            count = self.jwt_manager.revoke_all_user_tokens(auth_context.user_id, 'logout_all')
            logger.info(f"Revoked {count} tokens for user: {auth_context.user_id}")
        else:
            # Just blacklist the current token
            if auth_context.token_jti:
                self.jwt_manager.blacklist_token(auth_context.token_jti, auth_context.user_id, 'logout')

        self._send_json(handler, {'success': True, 'message': 'Logged out successfully'})

    def handle_me(self, handler):
        """
        GET /api/auth/me
        Get current authenticated user info.

        Response:
        {
            "user_id": "string",
            "role": "string",
            "scopes": ["string"],
            "auth_method": "jwt|api_key|session"
        }
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        response = {
            'user_id': auth_context.user_id,
            'role': auth_context.role,
            'scopes': auth_context.scopes,
            'auth_method': auth_context.method
        }

        if auth_context.method == 'api_key':
            response['agent_id'] = auth_context.agent_id
            response['agent_name'] = auth_context.agent_name

        self._send_json(handler, response)

    # API Key Endpoints

    def handle_list_api_keys(self, handler):
        """
        GET /api/auth/api-keys
        List all API keys (admin only).
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        if not auth_context.has_scope('api_keys:read'):
            return self._send_error(handler, 'forbidden', 'Requires api_keys:read scope', 403)

        if not self.api_key_manager:
            return self._send_error(handler, 'server_error', 'API key manager not available', 500)

        keys = self.api_key_manager.list_keys()
        self._send_json(handler, {'api_keys': keys})

    def handle_create_api_key(self, handler):
        """
        POST /api/auth/api-keys
        Create a new API key.

        Request body:
        {
            "agent_name": "string",
            "scopes": ["string"],
            "expires_in_days": 365 (optional),
            "rate_limit_requests": 1000 (optional),
            "rate_limit_window": 3600 (optional)
        }
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        if not auth_context.has_scope('api_keys:write'):
            return self._send_error(handler, 'forbidden', 'Requires api_keys:write scope', 403)

        body = self._get_json_body(handler)
        if body is None:
            return self._send_error(handler, 'invalid_request', 'Invalid JSON body')

        agent_name = body.get('agent_name', '').strip()
        scopes = body.get('scopes', [])
        expires_in_days = body.get('expires_in_days', 365)

        if not agent_name:
            return self._send_error(handler, 'invalid_request', 'Agent name required')

        if not scopes:
            return self._send_error(handler, 'invalid_request', 'At least one scope required')

        if not self.api_key_manager:
            return self._send_error(handler, 'server_error', 'API key manager not available', 500)

        # Validate scopes
        if self.scope_validator:
            invalid_scopes = self.scope_validator.validate_scopes(scopes)
            if invalid_scopes:
                return self._send_error(handler, 'invalid_scopes', f'Invalid scopes: {invalid_scopes}')

        result = self.api_key_manager.create_key(
            agent_name=agent_name,
            scopes=scopes,
            created_by=auth_context.user_id,
            expires_in_days=expires_in_days,
            rate_limit_requests=body.get('rate_limit_requests', 1000),
            rate_limit_window=body.get('rate_limit_window', 3600)
        )

        logger.info(f"API key created for agent '{agent_name}' by {auth_context.user_id}")
        self._send_json(handler, result, 201)

    def handle_revoke_api_key(self, handler, key_id: str):
        """
        DELETE /api/auth/api-keys/{key_id}
        Revoke an API key.
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        if not auth_context.has_scope('api_keys:write'):
            return self._send_error(handler, 'forbidden', 'Requires api_keys:write scope', 403)

        if not self.api_key_manager:
            return self._send_error(handler, 'server_error', 'API key manager not available', 500)

        body = self._get_json_body(handler) or {}
        reason = body.get('reason', 'Admin revocation')

        success = self.api_key_manager.revoke_key(key_id, auth_context.user_id, reason)
        if not success:
            return self._send_error(handler, 'not_found', 'API key not found', 404)

        logger.info(f"API key {key_id} revoked by {auth_context.user_id}")
        self._send_json(handler, {'success': True, 'message': 'API key revoked'})

    def handle_rotate_api_key(self, handler, key_id: str):
        """
        POST /api/auth/api-keys/{key_id}/rotate
        Rotate an API key.
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        if not auth_context.has_scope('api_keys:write'):
            return self._send_error(handler, 'forbidden', 'Requires api_keys:write scope', 403)

        if not self.api_key_manager:
            return self._send_error(handler, 'server_error', 'API key manager not available', 500)

        result = self.api_key_manager.rotate_key(key_id, auth_context.user_id)
        if not result:
            return self._send_error(handler, 'not_found', 'API key not found or already revoked', 404)

        logger.info(f"API key {key_id} rotated by {auth_context.user_id}")
        self._send_json(handler, result)

    # OAuth2 Endpoints

    def handle_oauth_authorize(self, handler):
        """
        GET /api/auth/oauth/authorize
        OAuth2 authorization endpoint.

        Query params:
        - response_type: must be "code"
        - client_id: OAuth client ID
        - redirect_uri: Where to redirect
        - scope: Space-separated scopes
        - state: Client state (recommended)
        - code_challenge: PKCE challenge (required for public clients)
        - code_challenge_method: "plain" or "S256"
        """
        self._ensure_initialized()

        # Parse query string
        path = handler.path
        if '?' in path:
            query_string = path.split('?', 1)[1]
            params = {k: v[0] for k, v in parse_qs(query_string).items()}
        else:
            params = {}

        response_type = params.get('response_type')
        client_id = params.get('client_id')
        redirect_uri = params.get('redirect_uri')
        scope = params.get('scope', '')
        state = params.get('state', '')
        code_challenge = params.get('code_challenge')
        code_challenge_method = params.get('code_challenge_method', 'S256')

        if response_type != 'code':
            return self._send_error(handler, 'unsupported_response_type', 'Only "code" response type supported')

        if not client_id or not redirect_uri:
            return self._send_error(handler, 'invalid_request', 'client_id and redirect_uri required')

        # Check if user is authenticated
        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            # In a real implementation, redirect to login page
            return self._send_error(handler, 'login_required', 'User authentication required', 401)

        if not self.oauth2_manager:
            return self._send_error(handler, 'server_error', 'OAuth2 manager not available', 500)

        scopes = scope.split() if scope else []

        code = self.oauth2_manager.create_authorization_code(
            client_id=client_id,
            user_id=auth_context.user_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )

        if not code:
            return self._send_error(handler, 'invalid_request', 'Invalid client or redirect URI')

        # Redirect with authorization code
        redirect_params = {'code': code}
        if state:
            redirect_params['state'] = state

        redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"

        handler.send_response(302)
        handler.send_header('Location', redirect_url)
        handler.end_headers()

    def handle_oauth_token(self, handler):
        """
        POST /api/auth/oauth/token
        OAuth2 token endpoint.

        Request body (form or JSON):
        - grant_type: "authorization_code" or "client_credentials"
        - code: Authorization code (for auth code grant)
        - redirect_uri: Must match authorization request
        - client_id: OAuth client ID
        - client_secret: Client secret (for confidential clients)
        - code_verifier: PKCE verifier (for public clients)
        - scope: Requested scopes (for client credentials)
        """
        self._ensure_initialized()

        body = self._get_json_body(handler)
        if body is None:
            return self._send_error(handler, 'invalid_request', 'Invalid request body')

        grant_type = body.get('grant_type')

        if not self.oauth2_manager:
            return self._send_error(handler, 'server_error', 'OAuth2 manager not available', 500)

        if grant_type == 'authorization_code':
            code = body.get('code')
            redirect_uri = body.get('redirect_uri')
            client_id = body.get('client_id')
            client_secret = body.get('client_secret')
            code_verifier = body.get('code_verifier')

            if not code or not redirect_uri or not client_id:
                return self._send_error(handler, 'invalid_request', 'Missing required parameters')

            result = self.oauth2_manager.exchange_code(
                code=code,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier
            )

            if not result:
                return self._send_error(handler, 'invalid_grant', 'Invalid or expired authorization code')

            self._send_json(handler, result)

        elif grant_type == 'client_credentials':
            client_id = body.get('client_id')
            client_secret = body.get('client_secret')
            scope = body.get('scope', '')

            if not client_id or not client_secret:
                return self._send_error(handler, 'invalid_request', 'client_id and client_secret required')

            scopes = scope.split() if scope else []
            result = self.oauth2_manager.client_credentials_grant(client_id, client_secret, scopes)

            if not result:
                return self._send_error(handler, 'invalid_client', 'Invalid client credentials')

            self._send_json(handler, result)

        else:
            return self._send_error(handler, 'unsupported_grant_type', 'Unsupported grant type')

    def handle_oauth_introspect(self, handler):
        """
        POST /api/auth/oauth/introspect
        OAuth2 token introspection (RFC 7662).
        """
        self._ensure_initialized()

        body = self._get_json_body(handler)
        if body is None:
            return self._send_error(handler, 'invalid_request', 'Invalid request body')

        token = body.get('token')
        client_id = body.get('client_id')
        client_secret = body.get('client_secret')

        if not token or not client_id:
            return self._send_error(handler, 'invalid_request', 'token and client_id required')

        if not self.oauth2_manager:
            return self._send_error(handler, 'server_error', 'OAuth2 manager not available', 500)

        result = self.oauth2_manager.introspect_token(token, client_id, client_secret)
        self._send_json(handler, result)

    # OAuth2 Client Management

    def handle_list_oauth_clients(self, handler):
        """
        GET /api/auth/oauth/clients
        List OAuth2 clients (admin only).
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        if not auth_context.has_scope('oauth:read'):
            return self._send_error(handler, 'forbidden', 'Requires oauth:read scope', 403)

        if not self.oauth2_manager:
            return self._send_error(handler, 'server_error', 'OAuth2 manager not available', 500)

        clients = self.oauth2_manager.list_clients()
        self._send_json(handler, {'clients': clients})

    def handle_create_oauth_client(self, handler):
        """
        POST /api/auth/oauth/clients
        Register a new OAuth2 client.
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        if not auth_context.has_scope('oauth:write'):
            return self._send_error(handler, 'forbidden', 'Requires oauth:write scope', 403)

        body = self._get_json_body(handler)
        if body is None:
            return self._send_error(handler, 'invalid_request', 'Invalid JSON body')

        client_name = body.get('client_name', '').strip()
        client_type = body.get('client_type', 'confidential')
        redirect_uris = body.get('redirect_uris', [])
        allowed_scopes = body.get('allowed_scopes', [])

        if not client_name:
            return self._send_error(handler, 'invalid_request', 'Client name required')

        if not redirect_uris:
            return self._send_error(handler, 'invalid_request', 'At least one redirect URI required')

        if client_type not in ('confidential', 'public'):
            return self._send_error(handler, 'invalid_request', 'client_type must be "confidential" or "public"')

        if not self.oauth2_manager:
            return self._send_error(handler, 'server_error', 'OAuth2 manager not available', 500)

        result = self.oauth2_manager.register_client(
            client_name=client_name,
            client_type=client_type,
            redirect_uris=redirect_uris,
            allowed_scopes=allowed_scopes,
            created_by=auth_context.user_id
        )

        logger.info(f"OAuth2 client '{client_name}' created by {auth_context.user_id}")
        self._send_json(handler, result, 201)

    # Scope and Session Endpoints

    def handle_list_scopes(self, handler):
        """
        GET /api/auth/scopes
        List all available scopes.
        """
        self._ensure_initialized()

        if not self.scope_validator:
            return self._send_error(handler, 'server_error', 'Scope validator not available', 500)

        scopes = self.scope_validator.get_all_scopes()
        self._send_json(handler, {'scopes': scopes})

    def handle_list_sessions(self, handler):
        """
        GET /api/auth/sessions
        List active sessions for the current user.
        """
        self._ensure_initialized()

        auth_context = getattr(handler, 'auth_context', None)
        if not auth_context or not auth_context.authenticated:
            return self._send_error(handler, 'unauthorized', 'Authentication required', 401)

        if not self.jwt_manager:
            return self._send_error(handler, 'server_error', 'JWT manager not available', 500)

        sessions = self.jwt_manager.get_user_refresh_tokens(auth_context.user_id)
        self._send_json(handler, {'sessions': sessions})


# Route registration helper
def register_auth_routes(router, auth_routes: AuthRoutes):
    """
    Register all auth routes with the router.

    Args:
        router: The ATLAS router instance
        auth_routes: AuthRoutes instance
    """
    # User authentication
    router.add_route('POST', '/api/auth/login', auth_routes.handle_login)
    router.add_route('POST', '/api/auth/refresh', auth_routes.handle_refresh)
    router.add_route('POST', '/api/auth/logout', auth_routes.handle_logout)
    router.add_route('GET', '/api/auth/me', auth_routes.handle_me)

    # TouchID authentication (macOS)
    router.add_route('GET', '/api/auth/touchid/available', auth_routes.handle_touchid_available)
    router.add_route('POST', '/api/auth/login/touchid', auth_routes.handle_touchid_login)

    # API keys
    router.add_route('GET', '/api/auth/api-keys', auth_routes.handle_list_api_keys)
    router.add_route('POST', '/api/auth/api-keys', auth_routes.handle_create_api_key)
    # Note: Routes with path params need pattern matching support in router
    # router.add_route('DELETE', '/api/auth/api-keys/:id', auth_routes.handle_revoke_api_key)
    # router.add_route('POST', '/api/auth/api-keys/:id/rotate', auth_routes.handle_rotate_api_key)

    # OAuth2
    router.add_route('GET', '/api/auth/oauth/authorize', auth_routes.handle_oauth_authorize)
    router.add_route('POST', '/api/auth/oauth/token', auth_routes.handle_oauth_token)
    router.add_route('POST', '/api/auth/oauth/introspect', auth_routes.handle_oauth_introspect)
    router.add_route('GET', '/api/auth/oauth/clients', auth_routes.handle_list_oauth_clients)
    router.add_route('POST', '/api/auth/oauth/clients', auth_routes.handle_create_oauth_client)

    # Scopes and sessions
    router.add_route('GET', '/api/auth/scopes', auth_routes.handle_list_scopes)
    router.add_route('GET', '/api/auth/sessions', auth_routes.handle_list_sessions)

    logger.info("Auth routes registered")


__all__ = [
    'AuthRoutes',
    'register_auth_routes',
]
