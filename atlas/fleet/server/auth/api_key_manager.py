"""
ATLAS Fleet Authentication - API Key Manager

Handles per-agent API key lifecycle:
- Create unique keys per agent
- Scoped access control
- Key expiration and revocation
- Rate limiting per key
- Usage tracking and auditing
"""
import json
import sqlite3
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Key prefix for identification
KEY_PREFIX = "atls_"


class APIKeyManager:
    """
    Manages per-agent API keys with scopes, expiration, and rate limiting.

    Each agent gets a unique API key instead of sharing a global key.
    Keys are stored hashed; the plain key is only shown once at creation.
    """

    def __init__(self, db_path: str = "~/.fleet-data/users.db"):
        self.db_path = str(Path(db_path).expanduser())
        self._init_db()

    def _init_db(self):
        """Initialize API key tables in database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            # API keys table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_api_keys (
                    id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
                    key_prefix TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    agent_id TEXT,
                    scopes TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    last_used_at TEXT,
                    last_used_ip TEXT,
                    use_count INTEGER DEFAULT 0,
                    is_revoked INTEGER DEFAULT 0,
                    revoked_at TEXT,
                    revoked_by TEXT,
                    revoked_reason TEXT,
                    rate_limit_requests INTEGER DEFAULT 1000,
                    rate_limit_window INTEGER DEFAULT 3600,
                    metadata TEXT
                )
            """)

            # API key usage log
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_key_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    response_status INTEGER
                )
            """)

            # Indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_prefix
                ON agent_api_keys(key_prefix)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_agent
                ON agent_api_keys(agent_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_hash
                ON agent_api_keys(key_hash)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_created_by
                ON agent_api_keys(created_by)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_key_usage_timestamp
                ON api_key_usage(timestamp)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_key_usage_key
                ON api_key_usage(key_id, timestamp)
            """)

            conn.commit()
            logger.debug("API key database tables initialized")
        finally:
            conn.close()

    def create_key(
        self,
        agent_name: str,
        scopes: List[str],
        created_by: str,
        agent_id: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_requests: int = 1000,
        rate_limit_window: int = 3600,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new API key for an agent.

        Args:
            agent_name: Human-readable name for the agent
            scopes: List of granted scopes
            created_by: Username of creator
            agent_id: Optional machine_id to link
            expires_in_days: Days until expiration (None = never)
            rate_limit_requests: Max requests per window
            rate_limit_window: Rate limit window in seconds
            metadata: Additional metadata dict

        Returns:
            Dict with key info including plain_key (only shown once!)
        """
        # Generate unique key
        key_id = secrets.token_urlsafe(16)
        key_random = secrets.token_urlsafe(32)
        plain_key = f"{KEY_PREFIX}{key_random}"
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        key_prefix = plain_key[:12]  # First 12 chars for identification

        now = datetime.utcnow()
        expires_at = None
        if expires_in_days:
            expires_at = (now + timedelta(days=expires_in_days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO agent_api_keys
                (id, key_hash, key_prefix, agent_name, agent_id, scopes,
                 created_by, created_at, expires_at, rate_limit_requests,
                 rate_limit_window, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key_id, key_hash, key_prefix, agent_name, agent_id,
                json.dumps(scopes), created_by, now.isoformat(),
                expires_at, rate_limit_requests, rate_limit_window,
                json.dumps(metadata) if metadata else None
            ))
            conn.commit()

            logger.info(f"Created API key {key_prefix}... for agent '{agent_name}' "
                       f"by {created_by}")

            return {
                'id': key_id,
                'plain_key': plain_key,  # Only returned once!
                'key_prefix': key_prefix,
                'agent_name': agent_name,
                'agent_id': agent_id,
                'scopes': scopes,
                'created_at': now.isoformat(),
                'expires_at': expires_at,
            }
        finally:
            conn.close()

    def validate_key(
        self,
        api_key: str,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Validate an API key and return its data if valid.

        Args:
            api_key: The API key to validate
            ip_address: Client IP for logging
            endpoint: API endpoint being called
            method: HTTP method

        Returns:
            Dict with key data if valid, None if invalid
        """
        if not api_key or not api_key.startswith(KEY_PREFIX):
            return None

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT id, agent_name, agent_id, scopes, expires_at,
                       is_revoked, rate_limit_requests, rate_limit_window,
                       use_count, metadata
                FROM agent_api_keys
                WHERE key_hash = ?
            """, (key_hash,))

            row = cur.fetchone()
            if not row:
                logger.warning(f"API key not found: {api_key[:12]}...")
                return None

            key_data = dict(row)

            # Check revocation
            if key_data['is_revoked']:
                logger.warning(f"API key revoked: {api_key[:12]}...")
                return None

            # Check expiration
            if key_data['expires_at']:
                if datetime.fromisoformat(key_data['expires_at']) < datetime.utcnow():
                    logger.warning(f"API key expired: {api_key[:12]}...")
                    return None

            # Check rate limit
            if not self._check_rate_limit(
                key_data['id'],
                key_data['rate_limit_requests'],
                key_data['rate_limit_window']
            ):
                logger.warning(f"API key rate limited: {api_key[:12]}...")
                return None

            # Update usage stats
            now = datetime.utcnow().isoformat()
            cur.execute("""
                UPDATE agent_api_keys
                SET last_used_at = ?, last_used_ip = ?, use_count = use_count + 1
                WHERE id = ?
            """, (now, ip_address, key_data['id']))

            # Log usage
            if endpoint:
                cur.execute("""
                    INSERT INTO api_key_usage
                    (key_id, timestamp, endpoint, method, ip_address)
                    VALUES (?, ?, ?, ?, ?)
                """, (key_data['id'], now, endpoint, method or 'GET', ip_address))

            conn.commit()

            # Parse JSON fields
            key_data['scopes'] = json.loads(key_data['scopes'])
            if key_data['metadata']:
                key_data['metadata'] = json.loads(key_data['metadata'])

            return key_data
        finally:
            conn.close()

    def revoke_key(
        self,
        key_id: str,
        revoked_by: str,
        reason: str = "admin_revocation",
    ) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: ID of the key to revoke
            revoked_by: Username performing revocation
            reason: Reason for revocation

        Returns:
            True if revoked successfully
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()

            cur.execute("""
                UPDATE agent_api_keys
                SET is_revoked = 1, revoked_at = ?, revoked_by = ?, revoked_reason = ?
                WHERE id = ? AND is_revoked = 0
            """, (now, revoked_by, reason, key_id))

            success = cur.rowcount > 0
            conn.commit()

            if success:
                logger.info(f"API key {key_id} revoked by {revoked_by}: {reason}")

            return success
        finally:
            conn.close()

    def rotate_key(
        self,
        key_id: str,
        rotated_by: str,
    ) -> Optional[Dict]:
        """
        Rotate an API key (revoke old, create new with same settings).

        Args:
            key_id: ID of the key to rotate
            rotated_by: Username performing rotation

        Returns:
            New key data if successful, None if key not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Get current key settings
            cur.execute("""
                SELECT agent_name, agent_id, scopes, rate_limit_requests,
                       rate_limit_window, metadata, expires_at
                FROM agent_api_keys
                WHERE id = ? AND is_revoked = 0
            """, (key_id,))

            row = cur.fetchone()
            if not row:
                return None

            old_data = dict(row)

            # Revoke old key
            self.revoke_key(key_id, rotated_by, "key_rotation")

            # Calculate remaining expiration
            expires_in_days = None
            if old_data['expires_at']:
                remaining = datetime.fromisoformat(old_data['expires_at']) - datetime.utcnow()
                if remaining.days > 0:
                    expires_in_days = remaining.days

            # Create new key with same settings
            return self.create_key(
                agent_name=old_data['agent_name'],
                scopes=json.loads(old_data['scopes']),
                created_by=rotated_by,
                agent_id=old_data['agent_id'],
                expires_in_days=expires_in_days,
                rate_limit_requests=old_data['rate_limit_requests'],
                rate_limit_window=old_data['rate_limit_window'],
                metadata=json.loads(old_data['metadata']) if old_data['metadata'] else None,
            )
        finally:
            conn.close()

    def list_keys(
        self,
        include_revoked: bool = False,
        created_by: Optional[str] = None,
    ) -> List[Dict]:
        """
        List all API keys (without revealing the actual keys).

        Args:
            include_revoked: Include revoked keys in list
            created_by: Filter by creator

        Returns:
            List of key metadata dicts
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            query = """
                SELECT id, key_prefix, agent_name, agent_id, scopes,
                       created_by, created_at, expires_at, last_used_at,
                       use_count, is_revoked, revoked_at, revoked_reason,
                       rate_limit_requests, rate_limit_window
                FROM agent_api_keys
            """
            params = []
            conditions = []

            if not include_revoked:
                conditions.append("is_revoked = 0")
            if created_by:
                conditions.append("created_by = ?")
                params.append(created_by)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC"

            cur.execute(query, params)

            keys = []
            for row in cur.fetchall():
                key_data = dict(row)
                key_data['scopes'] = json.loads(key_data['scopes'])
                key_data['is_revoked'] = bool(key_data['is_revoked'])
                keys.append(key_data)

            return keys
        finally:
            conn.close()

    def get_key_by_id(self, key_id: str) -> Optional[Dict]:
        """Get key metadata by ID"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT id, key_prefix, agent_name, agent_id, scopes,
                       created_by, created_at, expires_at, last_used_at,
                       use_count, is_revoked, revoked_at, revoked_reason,
                       rate_limit_requests, rate_limit_window, metadata
                FROM agent_api_keys
                WHERE id = ?
            """, (key_id,))

            row = cur.fetchone()
            if not row:
                return None

            key_data = dict(row)
            key_data['scopes'] = json.loads(key_data['scopes'])
            key_data['is_revoked'] = bool(key_data['is_revoked'])
            if key_data['metadata']:
                key_data['metadata'] = json.loads(key_data['metadata'])

            return key_data
        finally:
            conn.close()

    def get_key_usage(
        self,
        key_id: str,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[Dict]:
        """Get usage log for a key"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if since:
                cur.execute("""
                    SELECT timestamp, endpoint, method, ip_address, response_status
                    FROM api_key_usage
                    WHERE key_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (key_id, since.isoformat(), limit))
            else:
                cur.execute("""
                    SELECT timestamp, endpoint, method, ip_address, response_status
                    FROM api_key_usage
                    WHERE key_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (key_id, limit))

            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update_key_scopes(
        self,
        key_id: str,
        scopes: List[str],
        updated_by: str,
    ) -> bool:
        """Update the scopes for an API key"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE agent_api_keys
                SET scopes = ?
                WHERE id = ? AND is_revoked = 0
            """, (json.dumps(scopes), key_id))

            success = cur.rowcount > 0
            conn.commit()

            if success:
                logger.info(f"API key {key_id} scopes updated by {updated_by}")

            return success
        finally:
            conn.close()

    def validate_scopes(self, scopes: List[str]) -> bool:
        """Validate that all scopes are valid"""
        from .scopes import get_scope_validator
        validator = get_scope_validator(self.db_path)
        invalid = validator.validate_scopes(scopes)
        return len(invalid) == 0

    def _check_rate_limit(
        self,
        key_id: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        """Check if key is within rate limit"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            window_start = (datetime.utcnow() - timedelta(seconds=window_seconds)).isoformat()

            cur.execute("""
                SELECT COUNT(*) FROM api_key_usage
                WHERE key_id = ? AND timestamp >= ?
            """, (key_id, window_start))

            count = cur.fetchone()[0]
            return count < max_requests
        finally:
            conn.close()

    def cleanup_old_usage_logs(self, days: int = 30):
        """Remove usage logs older than specified days"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

            cur.execute("""
                DELETE FROM api_key_usage
                WHERE timestamp < ?
            """, (cutoff,))

            deleted = cur.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted} old API key usage logs")
        finally:
            conn.close()


# Singleton instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager(db_path: str = "~/.fleet-data/users.db") -> APIKeyManager:
    """Get or create the API key manager singleton"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(db_path)
    return _api_key_manager


__all__ = [
    'APIKeyManager',
    'get_api_key_manager',
    'KEY_PREFIX',
]
