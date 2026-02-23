"""
ATLAS Fleet Authentication - Scope Definitions

Defines available scopes for fine-grained access control.
Scopes follow the pattern: resource:action (e.g., metrics:read, commands:write)
"""
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Scope:
    """Represents an authentication scope"""
    scope: str
    display_name: str
    description: str
    category: str
    is_sensitive: bool = False


# Default scope definitions
DEFAULT_SCOPES = [
    # Metrics
    Scope('metrics:read', 'Read Metrics', 'View machine metrics and health data', 'metrics', False),
    Scope('metrics:write', 'Write Metrics', 'Submit machine metrics (agent use)', 'metrics', False),

    # Commands
    Scope('commands:read', 'Read Commands', 'View pending commands', 'commands', False),
    Scope('commands:write', 'Write Commands', 'Issue commands to machines', 'commands', True),
    Scope('commands:execute', 'Execute Commands', 'Execute commands on machines', 'commands', True),

    # Machines
    Scope('machines:read', 'Read Machines', 'View machine list and details', 'machines', False),
    Scope('machines:write', 'Manage Machines', 'Add, update, remove machines', 'machines', True),

    # Users
    Scope('users:read', 'Read Users', 'View user list', 'admin', True),
    Scope('users:write', 'Manage Users', 'Create, update, delete users', 'admin', True),

    # API Keys
    Scope('api_keys:read', 'Read API Keys', 'View API key list (metadata only)', 'admin', True),
    Scope('api_keys:write', 'Manage API Keys', 'Create, revoke API keys', 'admin', True),

    # OAuth
    Scope('oauth:read', 'Read OAuth Clients', 'View OAuth client list', 'admin', True),
    Scope('oauth:write', 'Manage OAuth Clients', 'Create, update OAuth clients', 'admin', True),

    # Admin
    Scope('admin:all', 'Full Admin Access', 'Complete administrative access', 'admin', True),

    # Widget Logs
    Scope('widget_logs:read', 'Read Widget Logs', 'View widget log data', 'logs', False),
    Scope('widget_logs:write', 'Write Widget Logs', 'Submit widget logs (agent use)', 'logs', False),

    # Analysis
    Scope('analysis:read', 'Read Analysis', 'View network analysis results', 'analysis', False),
    Scope('analysis:write', 'Run Analysis', 'Trigger network analysis', 'analysis', False),
]

# Role to scope mappings
ROLE_SCOPES = {
    'admin': [
        'admin:all', 'metrics:read', 'metrics:write', 'commands:read', 'commands:write',
        'commands:execute', 'machines:read', 'machines:write', 'users:read', 'users:write',
        'api_keys:read', 'api_keys:write', 'oauth:read', 'oauth:write',
        'widget_logs:read', 'widget_logs:write', 'analysis:read', 'analysis:write'
    ],
    'viewer': [
        'metrics:read', 'machines:read', 'widget_logs:read', 'analysis:read'
    ],
    'agent': [
        'metrics:write', 'commands:read', 'widget_logs:write'
    ],
}


class ScopeValidator:
    """Validates and manages authentication scopes"""

    def __init__(self, db_path: str = "~/.fleet-data/users.db"):
        self.db_path = str(Path(db_path).expanduser())
        self._init_db()
        self._valid_scopes: Optional[Set[str]] = None

    def _init_db(self):
        """Initialize scopes table in database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            # Create scopes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_scopes (
                    scope TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    is_sensitive INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            # Insert default scopes
            now = datetime.utcnow().isoformat()
            for scope in DEFAULT_SCOPES:
                cur.execute("""
                    INSERT OR IGNORE INTO auth_scopes
                    (scope, display_name, description, category, is_sensitive, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (scope.scope, scope.display_name, scope.description,
                      scope.category, 1 if scope.is_sensitive else 0, now))

            conn.commit()
            logger.debug("Auth scopes table initialized")
        finally:
            conn.close()

    def _load_valid_scopes(self) -> Set[str]:
        """Load valid scopes from database"""
        if self._valid_scopes is not None:
            return self._valid_scopes

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT scope FROM auth_scopes")
            self._valid_scopes = {row[0] for row in cur.fetchall()}
            return self._valid_scopes
        finally:
            conn.close()

    def is_valid_scope(self, scope: str) -> bool:
        """Check if a scope is valid"""
        return scope in self._load_valid_scopes()

    def validate_scopes(self, scopes: List[str]) -> List[str]:
        """
        Validate a list of scopes.

        Returns:
            List of invalid scopes (empty if all valid)
        """
        valid = self._load_valid_scopes()
        return [s for s in scopes if s not in valid]

    def get_scopes_for_role(self, role: str) -> List[str]:
        """Get default scopes for a role"""
        return ROLE_SCOPES.get(role, ['metrics:read'])

    def get_all_scopes(self) -> List[Dict]:
        """Get all available scopes with metadata"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT scope, display_name, description, category, is_sensitive
                FROM auth_scopes
                ORDER BY category, scope
            """)
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_scopes_by_category(self, category: str) -> List[Dict]:
        """Get scopes in a specific category"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT scope, display_name, description, is_sensitive
                FROM auth_scopes
                WHERE category = ?
                ORDER BY scope
            """, (category,))
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def check_scope(self, granted_scopes: List[str], required_scope: str) -> bool:
        """
        Check if granted scopes satisfy a required scope.

        Args:
            granted_scopes: List of scopes the user/agent has
            required_scope: The scope required for the action

        Returns:
            True if access should be granted
        """
        # admin:all grants access to everything
        if 'admin:all' in granted_scopes:
            return True

        return required_scope in granted_scopes

    def check_any_scope(self, granted_scopes: List[str], required_scopes: List[str]) -> bool:
        """Check if any of the required scopes are granted"""
        if 'admin:all' in granted_scopes:
            return True
        return any(s in granted_scopes for s in required_scopes)

    def check_all_scopes(self, granted_scopes: List[str], required_scopes: List[str]) -> bool:
        """Check if all required scopes are granted"""
        if 'admin:all' in granted_scopes:
            return True
        return all(s in granted_scopes for s in required_scopes)

    def filter_sensitive_scopes(self, scopes: List[str]) -> List[str]:
        """Filter out sensitive scopes from a list"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT scope FROM auth_scopes
                WHERE is_sensitive = 1
            """)
            sensitive = {row[0] for row in cur.fetchall()}
            return [s for s in scopes if s not in sensitive]
        finally:
            conn.close()


# Singleton instance
_scope_validator: Optional[ScopeValidator] = None


def get_scope_validator(db_path: str = "~/.fleet-data/users.db") -> ScopeValidator:
    """Get or create the scope validator singleton"""
    global _scope_validator
    if _scope_validator is None:
        _scope_validator = ScopeValidator(db_path)
    return _scope_validator


__all__ = [
    'Scope',
    'ScopeValidator',
    'get_scope_validator',
    'DEFAULT_SCOPES',
    'ROLE_SCOPES',
]
