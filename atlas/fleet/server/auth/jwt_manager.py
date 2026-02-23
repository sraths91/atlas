"""
ATLAS Fleet Authentication - JWT Token Manager

Handles JWT access and refresh token lifecycle:
- Access tokens: Short-lived (15 min), stateless validation
- Refresh tokens: Long-lived (7 days), stored in database for revocation
- Token rotation on refresh
- Blacklist for immediate access token revocation
"""
import os
import json
import sqlite3
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import PyJWT
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not installed. Install with: pip install PyJWT")


@dataclass
class TokenPair:
    """Access and refresh token pair"""
    access_token: str
    refresh_token: str
    access_expires_in: int  # seconds
    refresh_expires_in: int  # seconds
    token_type: str = "Bearer"


@dataclass
class TokenClaims:
    """Parsed JWT claims"""
    user_id: str
    role: str
    scopes: List[str]
    jti: str
    exp: datetime
    iat: datetime
    token_type: str  # 'access' or 'refresh'


class JWTManager:
    """
    Manages JWT token creation, validation, and refresh.

    Uses HS256 (symmetric) signing by default for simplicity.
    Access tokens are stateless; refresh tokens are tracked in database.
    """

    DEFAULT_ACCESS_TTL = 900  # 15 minutes
    DEFAULT_REFRESH_TTL = 604800  # 7 days

    def __init__(
        self,
        db_path: str = "~/.fleet-data/users.db",
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_ttl: int = DEFAULT_ACCESS_TTL,
        refresh_ttl: int = DEFAULT_REFRESH_TTL,
        issuer: str = "atlas-fleet-server",
        audience: str = "atlas-fleet-api",
    ):
        if not JWT_AVAILABLE:
            raise ImportError("PyJWT required: pip install PyJWT")

        self.db_path = str(Path(db_path).expanduser())
        self.algorithm = algorithm
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
        self.issuer = issuer
        self.audience = audience

        # Key management
        if secret_key:
            self.secret_key = secret_key
        else:
            self.secret_key = self._load_or_generate_key()

        self._init_db()

    def _load_or_generate_key(self) -> str:
        """Load existing key or generate new one"""
        key_path = Path.home() / '.fleet-data' / '.jwt_secret'
        key_path.parent.mkdir(parents=True, exist_ok=True)

        if key_path.exists():
            return key_path.read_text().strip()
        else:
            key = secrets.token_urlsafe(64)
            key_path.write_text(key)
            key_path.chmod(0o600)  # Secure permissions
            logger.info("Generated new JWT signing key")
            return key

    def _init_db(self):
        """Initialize database tables for token management"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            # Refresh tokens table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    device_name TEXT,
                    device_fingerprint TEXT,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_used_at TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_revoked INTEGER DEFAULT 0,
                    revoked_at TEXT,
                    revoked_reason TEXT
                )
            """)

            # Token blacklist table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS token_blacklist (
                    jti TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    blacklisted_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    reason TEXT
                )
            """)

            # Indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user
                ON refresh_tokens(user_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires
                ON refresh_tokens(expires_at)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash
                ON refresh_tokens(token_hash)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_blacklist_expires
                ON token_blacklist(expires_at)
            """)

            conn.commit()
            logger.debug("JWT database tables initialized")
        finally:
            conn.close()

    def create_token_pair(
        self,
        user_id: str,
        role: str,
        scopes: List[str],
        device_name: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        """
        Create a new access/refresh token pair for a user.

        Args:
            user_id: Username
            role: User role (admin, viewer)
            scopes: List of granted scopes
            device_name: Optional device identifier
            device_fingerprint: Optional device fingerprint
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            TokenPair with access and refresh tokens
        """
        now = datetime.utcnow()
        access_jti = secrets.token_urlsafe(16)
        refresh_jti = secrets.token_urlsafe(32)

        # Access token (short-lived, stateless)
        access_exp = now + timedelta(seconds=self.access_ttl)
        access_claims = {
            'sub': user_id,
            'role': role,
            'scopes': scopes,
            'type': 'access',
            'jti': access_jti,
            'iat': int(now.timestamp()),
            'exp': int(access_exp.timestamp()),
            'iss': self.issuer,
            'aud': self.audience,
        }
        access_token = jwt.encode(access_claims, self.secret_key, algorithm=self.algorithm)

        # Refresh token (long-lived, stored in DB)
        refresh_exp = now + timedelta(seconds=self.refresh_ttl)
        refresh_claims = {
            'sub': user_id,
            'type': 'refresh',
            'jti': refresh_jti,
            'iat': int(now.timestamp()),
            'exp': int(refresh_exp.timestamp()),
            'iss': self.issuer,
        }
        refresh_token = jwt.encode(refresh_claims, self.secret_key, algorithm=self.algorithm)

        # Store refresh token in database
        self._store_refresh_token(
            jti=refresh_jti,
            user_id=user_id,
            token=refresh_token,
            device_name=device_name,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=refresh_exp,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_in=self.access_ttl,
            refresh_expires_in=self.refresh_ttl,
        )

    def validate_access_token(self, token: str) -> Optional[TokenClaims]:
        """
        Validate an access token and return claims.

        Returns:
            TokenClaims if valid, None if invalid/expired/blacklisted
        """
        try:
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
            )

            # Check token type
            if claims.get('type') != 'access':
                logger.warning("Token type mismatch: expected 'access'")
                return None

            # Check blacklist
            if self._is_blacklisted(claims['jti']):
                logger.warning(f"Token {claims['jti'][:8]}... is blacklisted")
                return None

            return TokenClaims(
                user_id=claims['sub'],
                role=claims['role'],
                scopes=claims.get('scopes', []),
                jti=claims['jti'],
                exp=datetime.fromtimestamp(claims['exp']),
                iat=datetime.fromtimestamp(claims['iat']),
                token_type='access',
            )

        except jwt.ExpiredSignatureError:
            logger.debug("Access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[TokenPair]:
        """
        Use a refresh token to get a new access token.

        Implements refresh token rotation: the old refresh token
        is invalidated and a new one is issued.

        Returns:
            New TokenPair if refresh token valid, None otherwise
        """
        try:
            claims = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
            )

            if claims.get('type') != 'refresh':
                logger.warning("Token type mismatch: expected 'refresh'")
                return None

            # Verify refresh token exists and is valid in DB
            user_data = self._validate_refresh_token(claims['jti'], refresh_token)
            if not user_data:
                return None

            # Revoke old refresh token (rotation)
            self._revoke_refresh_token(claims['jti'], reason='rotated')

            # Get user info for new tokens
            user_id = claims['sub']
            user_info = self._get_user_info(user_id)
            if not user_info:
                logger.warning(f"User not found or inactive: {user_id}")
                return None

            # Get scopes for role
            from .scopes import get_scope_validator
            scope_validator = get_scope_validator(self.db_path)
            scopes = scope_validator.get_scopes_for_role(user_info['role'])

            # Issue new token pair
            return self.create_token_pair(
                user_id=user_id,
                role=user_info['role'],
                scopes=scopes,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        except jwt.ExpiredSignatureError:
            logger.debug("Refresh token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None

    def revoke_token(self, access_token: str, reason: str = "logout") -> bool:
        """
        Revoke a specific access token by adding to blacklist.

        Args:
            access_token: The access token to revoke
            reason: Reason for revocation

        Returns:
            True if revoked successfully
        """
        try:
            # Decode without verification to get claims
            claims = jwt.decode(
                access_token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )

            jti = claims.get('jti')
            user_id = claims.get('sub')
            exp = datetime.fromtimestamp(claims.get('exp', 0))

            if not jti or not user_id:
                return False

            # Add to blacklist
            self._add_to_blacklist(jti, user_id, exp, reason)
            return True

        except jwt.InvalidTokenError:
            return False

    def revoke_all_user_tokens(self, user_id: str, reason: str = "user_logout"):
        """Revoke all tokens for a user (logout everywhere)"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()

            # Revoke all refresh tokens
            cur.execute("""
                UPDATE refresh_tokens
                SET is_revoked = 1, revoked_at = ?, revoked_reason = ?
                WHERE user_id = ? AND is_revoked = 0
            """, (now, reason, user_id))

            revoked_count = cur.rowcount
            conn.commit()
            logger.info(f"Revoked {revoked_count} refresh tokens for user {user_id}: {reason}")
        finally:
            conn.close()

    def revoke_refresh_token_by_id(self, token_id: str, reason: str = "admin_revocation") -> bool:
        """Revoke a specific refresh token by its ID"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()

            cur.execute("""
                UPDATE refresh_tokens
                SET is_revoked = 1, revoked_at = ?, revoked_reason = ?
                WHERE id = ? AND is_revoked = 0
            """, (now, reason, token_id))

            success = cur.rowcount > 0
            conn.commit()
            return success
        finally:
            conn.close()

    def list_active_sessions(self, user_id: Optional[str] = None) -> List[Dict]:
        """List active refresh tokens (sessions)"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if user_id:
                cur.execute("""
                    SELECT id, user_id, device_name, issued_at, expires_at,
                           last_used_at, ip_address, user_agent
                    FROM refresh_tokens
                    WHERE user_id = ? AND is_revoked = 0
                      AND datetime(expires_at) > datetime('now')
                    ORDER BY last_used_at DESC
                """, (user_id,))
            else:
                cur.execute("""
                    SELECT id, user_id, device_name, issued_at, expires_at,
                           last_used_at, ip_address, user_agent
                    FROM refresh_tokens
                    WHERE is_revoked = 0
                      AND datetime(expires_at) > datetime('now')
                    ORDER BY last_used_at DESC
                """)

            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from database

        Returns:
            Total number of deleted entries
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()

            # Clean refresh tokens
            cur.execute("""
                DELETE FROM refresh_tokens
                WHERE datetime(expires_at) < datetime(?)
            """, (now,))
            refresh_deleted = cur.rowcount

            # Clean blacklist
            cur.execute("""
                DELETE FROM token_blacklist
                WHERE datetime(expires_at) < datetime(?)
            """, (now,))
            blacklist_deleted = cur.rowcount

            conn.commit()

            total_deleted = refresh_deleted + blacklist_deleted
            if total_deleted > 0:
                logger.info(f"Cleaned up {refresh_deleted} expired refresh tokens, "
                           f"{blacklist_deleted} blacklist entries")
            return total_deleted
        finally:
            conn.close()

    def cleanup_expired(self) -> int:
        """Alias for cleanup_expired_tokens()"""
        return self.cleanup_expired_tokens()

    def _store_refresh_token(
        self,
        jti: str,
        user_id: str,
        token: str,
        device_name: Optional[str],
        device_fingerprint: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        expires_at: datetime,
    ):
        """Store refresh token in database"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            now = datetime.utcnow().isoformat()

            cur.execute("""
                INSERT INTO refresh_tokens
                (id, user_id, token_hash, device_name, device_fingerprint,
                 issued_at, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (jti, user_id, token_hash, device_name, device_fingerprint,
                  now, expires_at.isoformat(), ip_address, user_agent))

            conn.commit()
        finally:
            conn.close()

    def _validate_refresh_token(self, jti: str, token: str) -> Optional[Dict]:
        """Validate refresh token exists and is not revoked"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            cur.execute("""
                SELECT user_id, is_revoked, expires_at
                FROM refresh_tokens
                WHERE id = ? AND token_hash = ?
            """, (jti, token_hash))

            row = cur.fetchone()
            if not row:
                logger.warning(f"Refresh token not found: {jti[:8]}...")
                return None

            user_id, is_revoked, expires_at = row

            if is_revoked:
                logger.warning(f"Refresh token revoked: {jti[:8]}...")
                return None

            if datetime.fromisoformat(expires_at) < datetime.utcnow():
                logger.warning(f"Refresh token expired: {jti[:8]}...")
                return None

            # Update last used
            cur.execute("""
                UPDATE refresh_tokens
                SET last_used_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), jti))
            conn.commit()

            return {'user_id': user_id}
        finally:
            conn.close()

    def _revoke_refresh_token(self, jti: str, reason: str):
        """Revoke a specific refresh token"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE refresh_tokens
                SET is_revoked = 1, revoked_at = ?, revoked_reason = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), reason, jti))
            conn.commit()
        finally:
            conn.close()

    def _add_to_blacklist(self, jti: str, user_id: str, expires_at: datetime, reason: str):
        """Add access token to blacklist"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO token_blacklist
                (jti, user_id, blacklisted_at, expires_at, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (jti, user_id, datetime.utcnow().isoformat(),
                  expires_at.isoformat(), reason))
            conn.commit()
        finally:
            conn.close()

    def _is_blacklisted(self, jti: str) -> bool:
        """Check if access token JTI is blacklisted"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM token_blacklist WHERE jti = ?", (jti,))
            return cur.fetchone() is not None
        finally:
            conn.close()

    def _get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user info from database"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT role, is_active FROM users WHERE username = ?", (user_id,))
            row = cur.fetchone()
            if row and row[1]:  # is_active
                return {'role': row[0]}
            return None
        finally:
            conn.close()


# Singleton instance
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager(db_path: str = "~/.fleet-data/users.db") -> Optional[JWTManager]:
    """Get or create the JWT manager singleton

    Returns:
        JWTManager instance, or None if PyJWT is not available
    """
    global _jwt_manager

    if not JWT_AVAILABLE:
        logger.warning("JWT manager unavailable - PyJWT not installed")
        return None

    if _jwt_manager is None:
        try:
            _jwt_manager = JWTManager(db_path)
        except ImportError as e:
            logger.error(f"Failed to initialize JWT manager: {e}")
            return None
    return _jwt_manager


__all__ = [
    'JWTManager',
    'TokenPair',
    'TokenClaims',
    'get_jwt_manager',
]
