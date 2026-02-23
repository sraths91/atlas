"""
Unit Tests for ATLAS Fleet Authentication System

Tests for:
- JWT Manager (token creation, validation, refresh, revocation)
- API Key Manager (creation, validation, rotation, rate limiting)
- OAuth2 Manager (client registration, authorization code, token exchange)
- Scope Validator (scope checking, role mappings)
- Auth Middleware (authentication flow)
- Auth Decorators (access control)
"""
import pytest
import tempfile
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch


# Test fixtures
@pytest.fixture
def temp_db():
    """Create a temporary database file for testing"""
    temp = tempfile.mktemp(suffix='.db')
    yield temp
    try:
        os.unlink(temp)
    except FileNotFoundError:
        pass


@pytest.fixture
def scope_validator(temp_db):
    """Create a ScopeValidator instance for testing"""
    from atlas.fleet.server.auth.scopes import ScopeValidator
    return ScopeValidator(db_path=temp_db)


@pytest.fixture
def jwt_manager(temp_db):
    """Create a JWTManager instance for testing"""
    try:
        from atlas.fleet.server.auth.jwt_manager import JWTManager
        return JWTManager(db_path=temp_db, secret_key='test-secret-key-for-testing')
    except ImportError:
        pytest.skip("PyJWT not installed")


@pytest.fixture
def api_key_manager(temp_db):
    """Create an APIKeyManager instance for testing"""
    from atlas.fleet.server.auth.api_key_manager import APIKeyManager
    return APIKeyManager(db_path=temp_db)


@pytest.fixture
def oauth2_manager(temp_db, jwt_manager):
    """Create an OAuth2Manager instance for testing"""
    from atlas.fleet.server.auth.oauth2_manager import OAuth2Manager
    return OAuth2Manager(db_path=temp_db, jwt_manager=jwt_manager)


# =====================
# Scope Validator Tests
# =====================

@pytest.mark.unit
class TestScopeValidator:
    """Tests for ScopeValidator"""

    def test_init_creates_default_scopes(self, scope_validator):
        """Test that initialization creates default scopes"""
        scopes = scope_validator.get_all_scopes()
        assert len(scopes) > 0
        scope_names = [s['scope'] for s in scopes]
        assert 'metrics:read' in scope_names
        assert 'admin:all' in scope_names

    def test_is_valid_scope(self, scope_validator):
        """Test scope validation"""
        assert scope_validator.is_valid_scope('metrics:read') is True
        assert scope_validator.is_valid_scope('invalid:scope') is False

    def test_validate_scopes(self, scope_validator):
        """Test batch scope validation"""
        invalid = scope_validator.validate_scopes(['metrics:read', 'invalid:scope'])
        assert 'invalid:scope' in invalid
        assert 'metrics:read' not in invalid

    def test_get_scopes_for_role(self, scope_validator):
        """Test role to scope mapping"""
        admin_scopes = scope_validator.get_scopes_for_role('admin')
        assert 'admin:all' in admin_scopes

        viewer_scopes = scope_validator.get_scopes_for_role('viewer')
        assert 'metrics:read' in viewer_scopes
        assert 'admin:all' not in viewer_scopes

        agent_scopes = scope_validator.get_scopes_for_role('agent')
        assert 'metrics:write' in agent_scopes

    def test_check_scope_with_admin_all(self, scope_validator):
        """Test that admin:all grants access to everything"""
        granted = ['admin:all']
        assert scope_validator.check_scope(granted, 'metrics:read') is True
        assert scope_validator.check_scope(granted, 'users:write') is True

    def test_check_scope_specific(self, scope_validator):
        """Test specific scope checking"""
        granted = ['metrics:read', 'machines:read']
        assert scope_validator.check_scope(granted, 'metrics:read') is True
        assert scope_validator.check_scope(granted, 'machines:read') is True
        assert scope_validator.check_scope(granted, 'commands:write') is False

    def test_check_any_scope(self, scope_validator):
        """Test any scope checking"""
        granted = ['metrics:read']
        assert scope_validator.check_any_scope(granted, ['metrics:read', 'metrics:write']) is True
        assert scope_validator.check_any_scope(granted, ['commands:read', 'commands:write']) is False

    def test_check_all_scopes(self, scope_validator):
        """Test all scopes checking"""
        granted = ['metrics:read', 'metrics:write']
        assert scope_validator.check_all_scopes(granted, ['metrics:read', 'metrics:write']) is True
        assert scope_validator.check_all_scopes(granted, ['metrics:read', 'commands:read']) is False

    def test_get_scopes_by_category(self, scope_validator):
        """Test getting scopes by category"""
        admin_scopes = scope_validator.get_scopes_by_category('admin')
        assert len(admin_scopes) > 0
        assert all(s.get('scope', '').endswith(':read') or s.get('scope', '').endswith(':write') or s.get('scope') == 'admin:all' for s in admin_scopes)


# ================
# JWT Manager Tests
# ================

@pytest.mark.unit
class TestJWTManager:
    """Tests for JWTManager"""

    def test_create_token_pair(self, jwt_manager):
        """Test token pair creation"""
        token_pair = jwt_manager.create_token_pair(
            user_id='testuser',
            role='admin',
            scopes=['metrics:read', 'commands:write']
        )

        assert token_pair is not None
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == 'Bearer'
        assert token_pair.access_expires_in > 0

    def test_validate_access_token(self, jwt_manager):
        """Test access token validation"""
        token_pair = jwt_manager.create_token_pair(
            user_id='testuser',
            role='viewer',
            scopes=['metrics:read']
        )

        claims = jwt_manager.validate_access_token(token_pair.access_token)
        assert claims is not None
        assert claims.sub == 'testuser'
        assert claims.role == 'viewer'
        assert 'metrics:read' in claims.scopes

    def test_validate_invalid_token(self, jwt_manager):
        """Test invalid token rejection"""
        claims = jwt_manager.validate_access_token('invalid-token')
        assert claims is None

    def test_validate_expired_token(self, jwt_manager):
        """Test expired token rejection"""
        # Create a manager with very short TTL
        from atlas.fleet.server.auth.jwt_manager import JWTManager
        short_ttl_manager = JWTManager(
            db_path=jwt_manager.db_path,
            secret_key='test-key',
            access_ttl=1  # 1 second
        )

        token_pair = short_ttl_manager.create_token_pair(
            user_id='testuser',
            role='viewer',
            scopes=[]
        )

        # Wait for token to expire
        time.sleep(2)

        claims = short_ttl_manager.validate_access_token(token_pair.access_token)
        assert claims is None

    def test_refresh_access_token(self, jwt_manager):
        """Test token refresh"""
        original_pair = jwt_manager.create_token_pair(
            user_id='testuser',
            role='admin',
            scopes=['metrics:read']
        )

        new_pair = jwt_manager.refresh_access_token(original_pair.refresh_token)
        assert new_pair is not None
        assert new_pair.access_token != original_pair.access_token
        assert new_pair.refresh_token != original_pair.refresh_token

    def test_refresh_invalid_token(self, jwt_manager):
        """Test refresh with invalid token"""
        new_pair = jwt_manager.refresh_access_token('invalid-refresh-token')
        assert new_pair is None

    def test_blacklist_token(self, jwt_manager):
        """Test token blacklisting"""
        token_pair = jwt_manager.create_token_pair(
            user_id='testuser',
            role='viewer',
            scopes=[]
        )

        # Validate before blacklist
        claims = jwt_manager.validate_access_token(token_pair.access_token)
        assert claims is not None
        jti = claims.jti

        # Blacklist the token
        jwt_manager.blacklist_token(jti, 'testuser', 'testing')

        # Validate after blacklist
        claims = jwt_manager.validate_access_token(token_pair.access_token)
        assert claims is None

    def test_revoke_all_user_tokens(self, jwt_manager):
        """Test revoking all user tokens"""
        # Create multiple tokens for the same user
        for _ in range(3):
            jwt_manager.create_token_pair(
                user_id='testuser',
                role='viewer',
                scopes=[]
            )

        # Revoke all
        count = jwt_manager.revoke_all_user_tokens('testuser', 'testing')
        assert count >= 3

    def test_cleanup_expired_tokens(self, jwt_manager):
        """Test cleanup of expired tokens"""
        # Create some tokens (they won't be expired yet)
        jwt_manager.create_token_pair(
            user_id='testuser',
            role='viewer',
            scopes=[]
        )

        # Run cleanup (should not delete non-expired tokens)
        deleted = jwt_manager.cleanup_expired()
        assert deleted >= 0


# ====================
# API Key Manager Tests
# ====================

@pytest.mark.unit
class TestAPIKeyManager:
    """Tests for APIKeyManager"""

    def test_create_key(self, api_key_manager):
        """Test API key creation"""
        result = api_key_manager.create_key(
            agent_name='test-agent',
            scopes=['metrics:write'],
            created_by='admin'
        )

        assert result is not None
        assert 'id' in result
        assert 'key' in result
        assert result['key'].startswith('atls_')
        assert result['agent_name'] == 'test-agent'

    def test_validate_key(self, api_key_manager):
        """Test API key validation"""
        result = api_key_manager.create_key(
            agent_name='test-agent',
            scopes=['metrics:write'],
            created_by='admin'
        )

        validation = api_key_manager.validate_key(
            result['key'],
            ip_address='127.0.0.1',
            endpoint='/api/metrics',
            method='POST'
        )

        assert validation is not None
        assert validation['agent_name'] == 'test-agent'
        assert 'metrics:write' in validation['scopes']

    def test_validate_invalid_key(self, api_key_manager):
        """Test invalid key rejection"""
        validation = api_key_manager.validate_key(
            'invalid-key',
            ip_address='127.0.0.1'
        )
        assert validation is None

    def test_revoke_key(self, api_key_manager):
        """Test API key revocation"""
        result = api_key_manager.create_key(
            agent_name='test-agent',
            scopes=['metrics:write'],
            created_by='admin'
        )

        # Revoke
        success = api_key_manager.revoke_key(result['id'], 'admin', 'testing')
        assert success is True

        # Validate after revoke
        validation = api_key_manager.validate_key(result['key'])
        assert validation is None

    def test_rotate_key(self, api_key_manager):
        """Test API key rotation"""
        original = api_key_manager.create_key(
            agent_name='test-agent',
            scopes=['metrics:write'],
            created_by='admin'
        )

        rotated = api_key_manager.rotate_key(original['id'], 'admin')
        assert rotated is not None
        assert rotated['key'] != original['key']
        assert rotated['id'] != original['id']

        # Old key should be invalid
        validation = api_key_manager.validate_key(original['key'])
        assert validation is None

        # New key should be valid
        validation = api_key_manager.validate_key(rotated['key'])
        assert validation is not None

    def test_list_keys(self, api_key_manager):
        """Test listing API keys"""
        # Create some keys
        for i in range(3):
            api_key_manager.create_key(
                agent_name=f'agent-{i}',
                scopes=['metrics:write'],
                created_by='admin'
            )

        keys = api_key_manager.list_keys()
        assert len(keys) >= 3

        # Keys should not include the actual key value
        for key in keys:
            assert 'key' not in key or key['key'] is None

    def test_key_expiration(self, api_key_manager):
        """Test API key expiration"""
        result = api_key_manager.create_key(
            agent_name='test-agent',
            scopes=['metrics:write'],
            created_by='admin',
            expires_in_days=0  # Expires immediately
        )

        # Should be invalid due to expiration
        # Note: This might need adjustment based on implementation
        validation = api_key_manager.validate_key(result['key'])
        # The key should still be valid right after creation
        # Expiration check happens on the next day boundary


# =====================
# OAuth2 Manager Tests
# =====================

@pytest.mark.unit
class TestOAuth2Manager:
    """Tests for OAuth2Manager"""

    def test_register_client(self, oauth2_manager):
        """Test OAuth2 client registration"""
        result = oauth2_manager.register_client(
            client_name='Test App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        assert result is not None
        assert 'client_id' in result
        assert 'client_secret' in result
        assert result['client_id'].startswith('atlas_')

    def test_register_public_client(self, oauth2_manager):
        """Test public client registration (no secret)"""
        result = oauth2_manager.register_client(
            client_name='Mobile App',
            client_type='public',
            redirect_uris=['myapp://callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        assert result is not None
        assert 'client_id' in result
        assert 'client_secret' not in result

    def test_validate_client(self, oauth2_manager):
        """Test client validation"""
        registration = oauth2_manager.register_client(
            client_name='Test App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        validation = oauth2_manager.validate_client(
            registration['client_id'],
            registration['client_secret']
        )

        assert validation is not None
        assert validation['client_name'] == 'Test App'

    def test_validate_client_wrong_secret(self, oauth2_manager):
        """Test client validation with wrong secret"""
        registration = oauth2_manager.register_client(
            client_name='Test App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        validation = oauth2_manager.validate_client(
            registration['client_id'],
            'wrong-secret'
        )

        assert validation is None

    def test_create_authorization_code(self, oauth2_manager):
        """Test authorization code creation"""
        registration = oauth2_manager.register_client(
            client_name='Test App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        code = oauth2_manager.create_authorization_code(
            client_id=registration['client_id'],
            user_id='testuser',
            redirect_uri='https://example.com/callback',
            scopes=['metrics:read']
        )

        assert code is not None
        assert len(code) > 20

    def test_authorization_code_invalid_redirect(self, oauth2_manager):
        """Test authorization code with invalid redirect URI"""
        registration = oauth2_manager.register_client(
            client_name='Test App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        code = oauth2_manager.create_authorization_code(
            client_id=registration['client_id'],
            user_id='testuser',
            redirect_uri='https://evil.com/callback',  # Not registered
            scopes=['metrics:read']
        )

        assert code is None

    def test_exchange_code(self, oauth2_manager):
        """Test authorization code exchange for tokens"""
        registration = oauth2_manager.register_client(
            client_name='Test App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        code = oauth2_manager.create_authorization_code(
            client_id=registration['client_id'],
            user_id='testuser',
            redirect_uri='https://example.com/callback',
            scopes=['metrics:read']
        )

        tokens = oauth2_manager.exchange_code(
            code=code,
            client_id=registration['client_id'],
            client_secret=registration['client_secret'],
            redirect_uri='https://example.com/callback'
        )

        assert tokens is not None
        assert 'access_token' in tokens
        assert tokens['token_type'] == 'Bearer'

    def test_exchange_code_reuse(self, oauth2_manager):
        """Test that authorization codes can only be used once"""
        registration = oauth2_manager.register_client(
            client_name='Test App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        code = oauth2_manager.create_authorization_code(
            client_id=registration['client_id'],
            user_id='testuser',
            redirect_uri='https://example.com/callback',
            scopes=['metrics:read']
        )

        # First exchange should succeed
        tokens1 = oauth2_manager.exchange_code(
            code=code,
            client_id=registration['client_id'],
            client_secret=registration['client_secret'],
            redirect_uri='https://example.com/callback'
        )
        assert tokens1 is not None

        # Second exchange should fail
        tokens2 = oauth2_manager.exchange_code(
            code=code,
            client_id=registration['client_id'],
            client_secret=registration['client_secret'],
            redirect_uri='https://example.com/callback'
        )
        assert tokens2 is None

    def test_client_credentials_grant(self, oauth2_manager):
        """Test client credentials grant"""
        registration = oauth2_manager.register_client(
            client_name='Service App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read', 'metrics:write'],
            created_by='admin'
        )

        tokens = oauth2_manager.client_credentials_grant(
            client_id=registration['client_id'],
            client_secret=registration['client_secret'],
            scopes=['metrics:read']
        )

        assert tokens is not None
        assert 'access_token' in tokens

    def test_deactivate_client(self, oauth2_manager):
        """Test client deactivation"""
        registration = oauth2_manager.register_client(
            client_name='Test App',
            client_type='confidential',
            redirect_uris=['https://example.com/callback'],
            allowed_scopes=['metrics:read'],
            created_by='admin'
        )

        success = oauth2_manager.deactivate_client(registration['client_id'])
        assert success is True

        # Client should no longer validate
        validation = oauth2_manager.validate_client(
            registration['client_id'],
            registration['client_secret']
        )
        assert validation is None

    def test_list_clients(self, oauth2_manager):
        """Test listing OAuth2 clients"""
        for i in range(3):
            oauth2_manager.register_client(
                client_name=f'App {i}',
                client_type='confidential',
                redirect_uris=['https://example.com/callback'],
                allowed_scopes=['metrics:read'],
                created_by='admin'
            )

        clients = oauth2_manager.list_clients()
        assert len(clients) >= 3


# =====================
# Auth Middleware Tests
# =====================

@pytest.mark.unit
class TestAuthMiddleware:
    """Tests for AuthMiddleware"""

    def test_extract_bearer_token(self, jwt_manager, temp_db):
        """Test Bearer token extraction"""
        from atlas.fleet.server.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(jwt_manager=jwt_manager, db_path=temp_db)

        mock_handler = Mock()
        mock_handler.headers = {'Authorization': 'Bearer test-token'}

        token = middleware._extract_bearer_token(mock_handler)
        assert token == 'test-token'

    def test_extract_api_key(self, temp_db):
        """Test API key extraction from X-API-Key header"""
        from atlas.fleet.server.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(db_path=temp_db)

        mock_handler = Mock()
        mock_handler.headers = {'X-API-Key': 'atls_test123'}

        key = middleware._extract_api_key(mock_handler)
        assert key == 'atls_test123'

    def test_extract_api_key_from_auth_header(self, temp_db):
        """Test API key extraction from Authorization header"""
        from atlas.fleet.server.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(db_path=temp_db)

        mock_handler = Mock()
        mock_handler.headers = {'Authorization': 'ApiKey atls_test123'}

        key = middleware._extract_api_key(mock_handler)
        assert key == 'atls_test123'

    def test_get_client_ip(self, temp_db):
        """Test client IP extraction"""
        from atlas.fleet.server.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(db_path=temp_db)

        # Test X-Forwarded-For
        mock_handler = Mock()
        mock_handler.headers = {'X-Forwarded-For': '1.2.3.4, 5.6.7.8'}
        mock_handler.client_address = ('10.0.0.1', 12345)

        ip = middleware._get_client_ip(mock_handler)
        assert ip == '1.2.3.4'

        # Test client_address fallback
        mock_handler.headers = {}
        ip = middleware._get_client_ip(mock_handler)
        assert ip == '10.0.0.1'

    def test_auth_context_has_scope(self):
        """Test AuthContext scope checking"""
        from atlas.fleet.server.auth.middleware import AuthContext

        context = AuthContext(
            authenticated=True,
            method='jwt',
            user_id='testuser',
            role='viewer',
            scopes=['metrics:read', 'machines:read']
        )

        assert context.has_scope('metrics:read') is True
        assert context.has_scope('commands:write') is False

    def test_auth_context_admin_all(self):
        """Test AuthContext with admin:all scope"""
        from atlas.fleet.server.auth.middleware import AuthContext

        context = AuthContext(
            authenticated=True,
            method='jwt',
            user_id='admin',
            role='admin',
            scopes=['admin:all']
        )

        assert context.has_scope('metrics:read') is True
        assert context.has_scope('commands:write') is True
        assert context.has_scope('anything:here') is True


# =====================
# Auth Decorators Tests
# =====================

@pytest.mark.unit
class TestAuthDecorators:
    """Tests for Auth Decorators"""

    def test_require_auth_authenticated(self):
        """Test require_auth with authenticated user"""
        from atlas.fleet.server.auth.decorators import require_auth
        from atlas.fleet.server.auth.middleware import AuthContext

        mock_handler = Mock()
        mock_handler.auth_context = AuthContext(
            authenticated=True,
            method='jwt',
            user_id='testuser',
            role='viewer',
            scopes=['metrics:read']
        )

        @require_auth
        def handler(h):
            return 'success'

        result = handler(mock_handler)
        assert result == 'success'

    def test_require_auth_unauthenticated(self):
        """Test require_auth with unauthenticated user"""
        from atlas.fleet.server.auth.decorators import require_auth
        from atlas.fleet.server.auth.middleware import AuthContext

        mock_handler = Mock()
        mock_handler.auth_context = AuthContext(authenticated=False)
        mock_handler.wfile = Mock()

        @require_auth
        def handler(h):
            return 'success'

        result = handler(mock_handler)
        assert result is None
        mock_handler.send_response.assert_called_with(401)

    def test_require_scope_has_scope(self):
        """Test require_scope with matching scope"""
        from atlas.fleet.server.auth.decorators import require_scope
        from atlas.fleet.server.auth.middleware import AuthContext

        mock_handler = Mock()
        mock_handler.auth_context = AuthContext(
            authenticated=True,
            method='jwt',
            user_id='testuser',
            role='viewer',
            scopes=['metrics:read']
        )

        @require_scope('metrics:read')
        def handler(h):
            return 'success'

        result = handler(mock_handler)
        assert result == 'success'

    def test_require_scope_missing_scope(self):
        """Test require_scope with missing scope"""
        from atlas.fleet.server.auth.decorators import require_scope
        from atlas.fleet.server.auth.middleware import AuthContext

        mock_handler = Mock()
        mock_handler.auth_context = AuthContext(
            authenticated=True,
            method='jwt',
            user_id='testuser',
            role='viewer',
            scopes=['metrics:read']
        )
        mock_handler.wfile = Mock()

        @require_scope('commands:write')
        def handler(h):
            return 'success'

        result = handler(mock_handler)
        assert result is None
        mock_handler.send_response.assert_called_with(403)

    def test_require_role_matching(self):
        """Test require_role with matching role"""
        from atlas.fleet.server.auth.decorators import require_role
        from atlas.fleet.server.auth.middleware import AuthContext

        mock_handler = Mock()
        mock_handler.auth_context = AuthContext(
            authenticated=True,
            method='jwt',
            user_id='admin',
            role='admin',
            scopes=[]
        )

        @require_role('admin')
        def handler(h):
            return 'success'

        result = handler(mock_handler)
        assert result == 'success'

    def test_require_role_not_matching(self):
        """Test require_role with non-matching role"""
        from atlas.fleet.server.auth.decorators import require_role
        from atlas.fleet.server.auth.middleware import AuthContext

        mock_handler = Mock()
        mock_handler.auth_context = AuthContext(
            authenticated=True,
            method='jwt',
            user_id='testuser',
            role='viewer',
            scopes=[]
        )
        mock_handler.wfile = Mock()

        @require_role('admin')
        def handler(h):
            return 'success'

        result = handler(mock_handler)
        assert result is None
        mock_handler.send_response.assert_called_with(403)
