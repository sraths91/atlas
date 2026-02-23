"""
ATLAS Fleet Authentication - OAuth2 Manager

Implements OAuth2 Authorization Code flow with PKCE support
for third-party integrations.

Supports:
- Authorization Code Grant (with PKCE for public clients)
- Client Credentials Grant (for server-to-server)
- Token introspection
- Token revocation
"""
import sqlite3
import secrets
import hashlib
import base64
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OAuth2Client:
    """Represents an OAuth2 client application"""
    client_id: str
    client_name: str
    client_type: str  # 'confidential' or 'public'
    redirect_uris: List[str]
    allowed_scopes: List[str]
    created_by: str
    created_at: str
    is_active: bool = True


@dataclass
class AuthorizationCode:
    """Represents an OAuth2 authorization code"""
    code: str
    client_id: str
    user_id: str
    redirect_uri: str
    scopes: List[str]
    code_challenge: Optional[str]
    code_challenge_method: Optional[str]
    issued_at: str
    expires_at: str
    is_used: bool = False


class OAuth2Manager:
    """
    Manages OAuth2 clients, authorization codes, and token exchange.

    Supports:
    - Client registration and management
    - Authorization code generation and validation
    - PKCE (Proof Key for Code Exchange) for public clients
    - Token exchange
    """

    AUTH_CODE_TTL = 600  # 10 minutes

    def __init__(self, db_path: str = "~/.fleet-data/users.db", jwt_manager=None):
        """
        Initialize the OAuth2 manager.

        Args:
            db_path: Path to the SQLite database
            jwt_manager: JWTManager instance for token generation
        """
        self.db_path = str(Path(db_path).expanduser())
        self.jwt_manager = jwt_manager
        self._init_db()

    def _init_db(self):
        """Initialize OAuth2 tables in database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            # OAuth2 clients table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS oauth2_clients (
                    client_id TEXT PRIMARY KEY,
                    client_secret_hash TEXT,
                    client_name TEXT NOT NULL,
                    client_type TEXT NOT NULL,
                    redirect_uris TEXT NOT NULL,
                    allowed_scopes TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # Authorization codes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS oauth2_auth_codes (
                    code TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    code_challenge TEXT,
                    code_challenge_method TEXT,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    FOREIGN KEY (client_id) REFERENCES oauth2_clients(client_id)
                )
            """)

            # OAuth2 access tokens (for tracking/revocation)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS oauth2_access_tokens (
                    token_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_revoked INTEGER DEFAULT 0,
                    FOREIGN KEY (client_id) REFERENCES oauth2_clients(client_id)
                )
            """)

            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_oauth2_codes_client ON oauth2_auth_codes(client_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_oauth2_codes_user ON oauth2_auth_codes(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_oauth2_tokens_client ON oauth2_access_tokens(client_id)")

            conn.commit()
            logger.debug("OAuth2 tables initialized")
        finally:
            conn.close()

    def _hash_secret(self, secret: str) -> str:
        """Hash a client secret"""
        return hashlib.sha256(secret.encode()).hexdigest()

    def _generate_code(self) -> str:
        """Generate a secure authorization code"""
        return secrets.token_urlsafe(32)

    def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str) -> bool:
        """Verify PKCE code challenge"""
        if method == 'plain':
            return code_verifier == code_challenge
        elif method == 'S256':
            # SHA256 hash of verifier, base64url encoded
            verifier_hash = hashlib.sha256(code_verifier.encode()).digest()
            computed_challenge = base64.urlsafe_b64encode(verifier_hash).rstrip(b'=').decode()
            return computed_challenge == code_challenge
        return False

    # Client Management

    def register_client(
        self,
        client_name: str,
        client_type: str,
        redirect_uris: List[str],
        allowed_scopes: List[str],
        created_by: str
    ) -> Dict:
        """
        Register a new OAuth2 client.

        Args:
            client_name: Human-readable name for the client
            client_type: 'confidential' (has secret) or 'public' (no secret, requires PKCE)
            redirect_uris: List of allowed redirect URIs
            allowed_scopes: List of scopes this client can request
            created_by: Username of the admin creating the client

        Returns:
            Dict with client_id and client_secret (if confidential)
        """
        client_id = f"atlas_{secrets.token_urlsafe(16)}"
        client_secret = None
        client_secret_hash = None

        if client_type == 'confidential':
            client_secret = secrets.token_urlsafe(32)
            client_secret_hash = self._hash_secret(client_secret)

        now = datetime.utcnow().isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO oauth2_clients
                (client_id, client_secret_hash, client_name, client_type,
                 redirect_uris, allowed_scopes, created_by, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                client_id, client_secret_hash, client_name, client_type,
                json.dumps(redirect_uris), json.dumps(allowed_scopes),
                created_by, now
            ))
            conn.commit()

            logger.info(f"OAuth2 client registered: {client_name} ({client_id}) by {created_by}")

            result = {
                'client_id': client_id,
                'client_name': client_name,
                'client_type': client_type,
                'redirect_uris': redirect_uris,
                'allowed_scopes': allowed_scopes,
                'created_at': now
            }

            if client_secret:
                result['client_secret'] = client_secret

            return result
        finally:
            conn.close()

    def get_client(self, client_id: str) -> Optional[Dict]:
        """Get client info by client_id"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT client_id, client_name, client_type, redirect_uris,
                       allowed_scopes, created_by, created_at, is_active
                FROM oauth2_clients
                WHERE client_id = ?
            """, (client_id,))
            row = cur.fetchone()
            if not row:
                return None

            return {
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'client_type': row['client_type'],
                'redirect_uris': json.loads(row['redirect_uris']),
                'allowed_scopes': json.loads(row['allowed_scopes']),
                'created_by': row['created_by'],
                'created_at': row['created_at'],
                'is_active': bool(row['is_active'])
            }
        finally:
            conn.close()

    def validate_client(self, client_id: str, client_secret: Optional[str] = None) -> Optional[Dict]:
        """
        Validate a client and optionally its secret.

        Args:
            client_id: The client ID
            client_secret: The client secret (required for confidential clients)

        Returns:
            Client info dict if valid, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT client_id, client_secret_hash, client_name, client_type,
                       redirect_uris, allowed_scopes, is_active
                FROM oauth2_clients
                WHERE client_id = ? AND is_active = 1
            """, (client_id,))
            row = cur.fetchone()

            if not row:
                return None

            # For confidential clients, verify secret
            if row['client_type'] == 'confidential':
                if not client_secret:
                    logger.warning(f"Missing client secret for confidential client: {client_id}")
                    return None
                if self._hash_secret(client_secret) != row['client_secret_hash']:
                    logger.warning(f"Invalid client secret for: {client_id}")
                    return None

            return {
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'client_type': row['client_type'],
                'redirect_uris': json.loads(row['redirect_uris']),
                'allowed_scopes': json.loads(row['allowed_scopes'])
            }
        finally:
            conn.close()

    def list_clients(self, include_inactive: bool = False) -> List[Dict]:
        """List all OAuth2 clients"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if include_inactive:
                cur.execute("""
                    SELECT client_id, client_name, client_type, redirect_uris,
                           allowed_scopes, created_by, created_at, is_active
                    FROM oauth2_clients
                    ORDER BY created_at DESC
                """)
            else:
                cur.execute("""
                    SELECT client_id, client_name, client_type, redirect_uris,
                           allowed_scopes, created_by, created_at, is_active
                    FROM oauth2_clients
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                """)

            return [{
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'client_type': row['client_type'],
                'redirect_uris': json.loads(row['redirect_uris']),
                'allowed_scopes': json.loads(row['allowed_scopes']),
                'created_by': row['created_by'],
                'created_at': row['created_at'],
                'is_active': bool(row['is_active'])
            } for row in cur.fetchall()]
        finally:
            conn.close()

    def deactivate_client(self, client_id: str) -> bool:
        """Deactivate an OAuth2 client"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE oauth2_clients
                SET is_active = 0
                WHERE client_id = ?
            """, (client_id,))
            conn.commit()

            if cur.rowcount > 0:
                logger.info(f"OAuth2 client deactivated: {client_id}")
                return True
            return False
        finally:
            conn.close()

    # Authorization Code Flow

    def create_authorization_code(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scopes: List[str],
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> Optional[str]:
        """
        Create an authorization code for the OAuth2 flow.

        Args:
            client_id: The client requesting authorization
            user_id: The user authorizing access
            redirect_uri: Where to redirect after authorization
            scopes: Requested scopes
            code_challenge: PKCE code challenge (required for public clients)
            code_challenge_method: PKCE method ('plain' or 'S256')

        Returns:
            Authorization code if successful, None otherwise
        """
        # Validate client
        client = self.get_client(client_id)
        if not client or not client['is_active']:
            logger.warning(f"Invalid or inactive client: {client_id}")
            return None

        # Validate redirect URI
        if redirect_uri not in client['redirect_uris']:
            logger.warning(f"Invalid redirect URI for client {client_id}: {redirect_uri}")
            return None

        # For public clients, PKCE is required
        if client['client_type'] == 'public':
            if not code_challenge or not code_challenge_method:
                logger.warning(f"PKCE required for public client: {client_id}")
                return None

        # Validate scopes
        invalid_scopes = [s for s in scopes if s not in client['allowed_scopes']]
        if invalid_scopes:
            logger.warning(f"Invalid scopes for client {client_id}: {invalid_scopes}")
            return None

        # Generate code
        code = self._generate_code()
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.AUTH_CODE_TTL)

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO oauth2_auth_codes
                (code, client_id, user_id, redirect_uri, scopes,
                 code_challenge, code_challenge_method, issued_at, expires_at, is_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                code, client_id, user_id, redirect_uri, json.dumps(scopes),
                code_challenge, code_challenge_method,
                now.isoformat(), expires_at.isoformat()
            ))
            conn.commit()

            logger.info(f"Authorization code created for client {client_id}, user {user_id}")
            return code
        finally:
            conn.close()

    def exchange_code(
        self,
        code: str,
        client_id: str,
        client_secret: Optional[str],
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Exchange an authorization code for tokens.

        Args:
            code: The authorization code
            client_id: The client ID
            client_secret: Client secret (for confidential clients)
            redirect_uri: Must match the one used in authorization
            code_verifier: PKCE code verifier (for public clients)

        Returns:
            Dict with access_token, refresh_token, etc. or None if invalid
        """
        # Validate client
        client = self.validate_client(client_id, client_secret)
        if not client:
            # For public clients, secret is not required
            client = self.get_client(client_id)
            if not client or client['client_type'] != 'public':
                logger.warning(f"Client validation failed: {client_id}")
                return None

        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Get and validate the code
            cur.execute("""
                SELECT code, client_id, user_id, redirect_uri, scopes,
                       code_challenge, code_challenge_method, expires_at, is_used
                FROM oauth2_auth_codes
                WHERE code = ? AND client_id = ?
            """, (code, client_id))
            row = cur.fetchone()

            if not row:
                logger.warning(f"Authorization code not found: {code[:8]}...")
                return None

            # Check if already used
            if row['is_used']:
                logger.warning(f"Authorization code already used: {code[:8]}...")
                return None

            # Check expiration
            expires_at = datetime.fromisoformat(row['expires_at'])
            if datetime.utcnow() > expires_at:
                logger.warning(f"Authorization code expired: {code[:8]}...")
                return None

            # Check redirect URI
            if row['redirect_uri'] != redirect_uri:
                logger.warning(f"Redirect URI mismatch for code: {code[:8]}...")
                return None

            # Verify PKCE if present
            if row['code_challenge']:
                if not code_verifier:
                    logger.warning(f"PKCE verifier required but not provided: {code[:8]}...")
                    return None
                if not self._verify_pkce(code_verifier, row['code_challenge'], row['code_challenge_method']):
                    logger.warning(f"PKCE verification failed: {code[:8]}...")
                    return None

            # Mark code as used
            cur.execute("""
                UPDATE oauth2_auth_codes
                SET is_used = 1
                WHERE code = ?
            """, (code,))
            conn.commit()

            # Generate tokens
            scopes = json.loads(row['scopes'])
            user_id = row['user_id']

            if self.jwt_manager:
                token_pair = self.jwt_manager.create_token_pair(
                    user_id=user_id,
                    role='oauth_user',
                    scopes=scopes,
                    device_name=f'oauth2:{client_id}'
                )

                if token_pair:
                    logger.info(f"Token exchange successful for client {client_id}, user {user_id}")
                    return {
                        'access_token': token_pair.access_token,
                        'token_type': 'Bearer',
                        'expires_in': 900,  # 15 minutes
                        'refresh_token': token_pair.refresh_token,
                        'scope': ' '.join(scopes)
                    }

            # Fallback if no JWT manager
            logger.warning("No JWT manager available for token generation")
            return None
        finally:
            conn.close()

    # Client Credentials Flow

    def client_credentials_grant(self, client_id: str, client_secret: str, scopes: List[str]) -> Optional[Dict]:
        """
        Client credentials grant for server-to-server authentication.

        Args:
            client_id: The client ID
            client_secret: The client secret
            scopes: Requested scopes

        Returns:
            Dict with access_token or None if invalid
        """
        # Validate client (must be confidential)
        client = self.validate_client(client_id, client_secret)
        if not client:
            return None

        if client['client_type'] != 'confidential':
            logger.warning(f"Client credentials grant requires confidential client: {client_id}")
            return None

        # Validate scopes
        invalid_scopes = [s for s in scopes if s not in client['allowed_scopes']]
        if invalid_scopes:
            logger.warning(f"Invalid scopes for client {client_id}: {invalid_scopes}")
            return None

        if self.jwt_manager:
            token_pair = self.jwt_manager.create_token_pair(
                user_id=f"client:{client_id}",
                role='service',
                scopes=scopes,
                device_name=f'client_credentials:{client_id}'
            )

            if token_pair:
                logger.info(f"Client credentials grant successful for {client_id}")
                return {
                    'access_token': token_pair.access_token,
                    'token_type': 'Bearer',
                    'expires_in': 900,
                    'scope': ' '.join(scopes)
                }

        return None

    # Token Introspection

    def introspect_token(self, token: str, client_id: str, client_secret: Optional[str] = None) -> Dict:
        """
        Introspect a token (RFC 7662).

        Args:
            token: The token to introspect
            client_id: The requesting client
            client_secret: Client secret (optional)

        Returns:
            Dict with 'active' bool and token details if active
        """
        # Validate requesting client
        client = self.validate_client(client_id, client_secret)
        if not client and client_secret:
            return {'active': False}

        # Validate the token
        if self.jwt_manager:
            claims = self.jwt_manager.validate_access_token(token)
            if claims:
                return {
                    'active': True,
                    'scope': ' '.join(claims.scopes),
                    'client_id': client_id,
                    'username': claims.sub,
                    'token_type': 'Bearer',
                    'exp': int(claims.exp.timestamp()) if claims.exp else None,
                    'iat': int(claims.iat.timestamp()) if claims.iat else None,
                    'sub': claims.sub,
                    'jti': claims.jti
                }

        return {'active': False}

    # Cleanup

    def cleanup_expired(self) -> int:
        """Remove expired authorization codes"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()

            cur.execute("""
                DELETE FROM oauth2_auth_codes
                WHERE expires_at < ? OR is_used = 1
            """, (now,))
            deleted = cur.rowcount
            conn.commit()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired/used authorization codes")
            return deleted
        finally:
            conn.close()


# Singleton instance
_oauth2_manager: Optional[OAuth2Manager] = None


def get_oauth2_manager(db_path: str = "~/.fleet-data/users.db", jwt_manager=None) -> OAuth2Manager:
    """Get or create the OAuth2 manager singleton"""
    global _oauth2_manager
    if _oauth2_manager is None:
        _oauth2_manager = OAuth2Manager(db_path, jwt_manager)
    return _oauth2_manager


__all__ = [
    'OAuth2Client',
    'AuthorizationCode',
    'OAuth2Manager',
    'get_oauth2_manager',
]
