"""
ATLAS Fleet Authentication - Audit Logging

Provides comprehensive audit logging for authentication events:
- Login attempts (success/failure)
- Token creation and revocation
- API key operations
- OAuth2 flows
- Permission changes
- Security events

All events are stored in a dedicated SQLite table for analysis and compliance.
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    # Authentication events
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILURE = 'login_failure'
    LOGOUT = 'logout'
    SESSION_EXPIRED = 'session_expired'

    # Token events
    TOKEN_CREATED = 'token_created'
    TOKEN_REFRESHED = 'token_refreshed'
    TOKEN_REVOKED = 'token_revoked'
    TOKEN_EXPIRED = 'token_expired'
    TOKEN_BLACKLISTED = 'token_blacklisted'

    # API Key events
    API_KEY_CREATED = 'api_key_created'
    API_KEY_USED = 'api_key_used'
    API_KEY_REVOKED = 'api_key_revoked'
    API_KEY_ROTATED = 'api_key_rotated'
    API_KEY_RATE_LIMITED = 'api_key_rate_limited'

    # OAuth2 events
    OAUTH_CLIENT_REGISTERED = 'oauth_client_registered'
    OAUTH_CLIENT_DEACTIVATED = 'oauth_client_deactivated'
    OAUTH_CODE_CREATED = 'oauth_code_created'
    OAUTH_CODE_EXCHANGED = 'oauth_code_exchanged'
    OAUTH_TOKEN_INTROSPECTED = 'oauth_token_introspected'

    # User management events
    USER_CREATED = 'user_created'
    USER_DELETED = 'user_deleted'
    PASSWORD_CHANGED = 'password_changed'
    PASSWORD_RESET = 'password_reset'
    ROLE_CHANGED = 'role_changed'

    # Security events
    BRUTE_FORCE_DETECTED = 'brute_force_detected'
    ACCOUNT_LOCKED = 'account_locked'
    ACCOUNT_UNLOCKED = 'account_unlocked'
    SUSPICIOUS_ACTIVITY = 'suspicious_activity'
    INVALID_TOKEN = 'invalid_token'
    UNAUTHORIZED_ACCESS = 'unauthorized_access'


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


@dataclass
class AuditEvent:
    """Represents an audit log entry"""
    event_type: str
    severity: str
    timestamp: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    details: Optional[Dict] = None
    request_id: Optional[str] = None


class AuditLogger:
    """
    Audit logging system for authentication events.

    Stores all auth-related events in a dedicated SQLite table
    for security monitoring, compliance, and forensic analysis.
    """

    def __init__(self, db_path: str = "~/.fleet-data/users.db"):
        """Initialize the audit logger"""
        self.db_path = str(Path(db_path).expanduser())
        self._init_db()

    def _init_db(self):
        """Initialize audit log table"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            # Main audit log table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    resource TEXT,
                    action TEXT,
                    status TEXT,
                    details TEXT,
                    request_id TEXT
                )
            """)

            # Indexes for common queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON auth_audit_log(timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON auth_audit_log(event_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON auth_audit_log(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_ip_address ON auth_audit_log(ip_address)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_severity ON auth_audit_log(severity)")

            conn.commit()
            logger.debug("Audit log table initialized")
        finally:
            conn.close()

    def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        details: Optional[Dict] = None,
        request_id: Optional[str] = None
    ):
        """
        Log an audit event.

        Args:
            event_type: Type of event (from AuditEventType enum)
            severity: Event severity level
            user_id: User or agent ID involved
            ip_address: Client IP address
            user_agent: Client user agent string
            resource: Resource being accessed (e.g., '/api/auth/login')
            action: Specific action taken
            status: Result status (e.g., 'success', 'failure')
            details: Additional event details as dict
            request_id: Request correlation ID
        """
        timestamp = datetime.utcnow().isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO auth_audit_log
                (event_type, severity, timestamp, user_id, ip_address, user_agent,
                 resource, action, status, details, request_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_type.value if isinstance(event_type, AuditEventType) else event_type,
                severity.value if isinstance(severity, AuditSeverity) else severity,
                timestamp,
                user_id,
                ip_address,
                user_agent,
                resource,
                action,
                status,
                json.dumps(details) if details else None,
                request_id
            ))
            conn.commit()

            # Also log to standard logger for real-time monitoring
            log_msg = f"[AUDIT] {event_type.value if isinstance(event_type, AuditEventType) else event_type}: " \
                     f"user={user_id}, ip={ip_address}, status={status}"
            if severity == AuditSeverity.CRITICAL:
                logger.critical(log_msg)
            elif severity == AuditSeverity.ERROR:
                logger.error(log_msg)
            elif severity == AuditSeverity.WARNING:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
        finally:
            conn.close()

    # Convenience methods for common events

    def log_login_success(self, user_id: str, ip_address: str, user_agent: str = None):
        """Log successful login"""
        self.log(
            AuditEventType.LOGIN_SUCCESS,
            AuditSeverity.INFO,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource='/api/auth/login',
            action='authenticate',
            status='success'
        )

    def log_login_failure(self, user_id: str, ip_address: str, reason: str, user_agent: str = None):
        """Log failed login attempt"""
        self.log(
            AuditEventType.LOGIN_FAILURE,
            AuditSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource='/api/auth/login',
            action='authenticate',
            status='failure',
            details={'reason': reason}
        )

    def log_token_created(self, user_id: str, token_type: str, scopes: List[str], ip_address: str = None):
        """Log token creation"""
        self.log(
            AuditEventType.TOKEN_CREATED,
            AuditSeverity.INFO,
            user_id=user_id,
            ip_address=ip_address,
            action='create_token',
            status='success',
            details={'token_type': token_type, 'scopes': scopes}
        )

    def log_token_revoked(self, user_id: str, revoked_by: str, reason: str):
        """Log token revocation"""
        self.log(
            AuditEventType.TOKEN_REVOKED,
            AuditSeverity.INFO,
            user_id=user_id,
            action='revoke_token',
            status='success',
            details={'revoked_by': revoked_by, 'reason': reason}
        )

    def log_api_key_created(self, agent_name: str, created_by: str, scopes: List[str]):
        """Log API key creation"""
        self.log(
            AuditEventType.API_KEY_CREATED,
            AuditSeverity.INFO,
            user_id=created_by,
            action='create_api_key',
            status='success',
            details={'agent_name': agent_name, 'scopes': scopes}
        )

    def log_api_key_used(self, agent_name: str, ip_address: str, endpoint: str):
        """Log API key usage"""
        self.log(
            AuditEventType.API_KEY_USED,
            AuditSeverity.INFO,
            user_id=agent_name,
            ip_address=ip_address,
            resource=endpoint,
            action='api_request',
            status='success'
        )

    def log_api_key_rate_limited(self, agent_name: str, ip_address: str, endpoint: str):
        """Log API key rate limit hit"""
        self.log(
            AuditEventType.API_KEY_RATE_LIMITED,
            AuditSeverity.WARNING,
            user_id=agent_name,
            ip_address=ip_address,
            resource=endpoint,
            action='api_request',
            status='rate_limited'
        )

    def log_brute_force_detected(self, user_id: str, ip_address: str, attempts: int):
        """Log brute force detection"""
        self.log(
            AuditEventType.BRUTE_FORCE_DETECTED,
            AuditSeverity.CRITICAL,
            user_id=user_id,
            ip_address=ip_address,
            action='brute_force_detection',
            status='detected',
            details={'attempts': attempts}
        )

    def log_account_locked(self, user_id: str, ip_address: str, duration_seconds: int):
        """Log account lockout"""
        self.log(
            AuditEventType.ACCOUNT_LOCKED,
            AuditSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            action='lock_account',
            status='locked',
            details={'duration_seconds': duration_seconds}
        )

    def log_unauthorized_access(self, user_id: str, ip_address: str, resource: str, required_scope: str):
        """Log unauthorized access attempt"""
        self.log(
            AuditEventType.UNAUTHORIZED_ACCESS,
            AuditSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action='access_denied',
            status='unauthorized',
            details={'required_scope': required_scope}
        )

    # Query methods

    def get_events(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Query audit events with filters.

        Returns list of matching audit events.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            query = "SELECT * FROM auth_audit_log WHERE 1=1"
            params = []

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if ip_address:
                query += " AND ip_address = ?"
                params.append(ip_address)

            if severity:
                query += " AND severity = ?"
                params.append(severity)

            if start_time:
                query += " AND datetime(timestamp) >= datetime(?)"
                params.append(start_time.isoformat())

            if end_time:
                query += " AND datetime(timestamp) <= datetime(?)"
                params.append(end_time.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cur.execute(query, params)

            events = []
            for row in cur.fetchall():
                event = dict(row)
                if event.get('details'):
                    event['details'] = json.loads(event['details'])
                events.append(event)

            return events
        finally:
            conn.close()

    def get_security_alerts(self, hours: int = 24) -> List[Dict]:
        """Get security-related events from the last N hours"""
        start_time = datetime.utcnow() - timedelta(hours=hours)

        security_events = [
            AuditEventType.LOGIN_FAILURE.value,
            AuditEventType.BRUTE_FORCE_DETECTED.value,
            AuditEventType.ACCOUNT_LOCKED.value,
            AuditEventType.UNAUTHORIZED_ACCESS.value,
            AuditEventType.INVALID_TOKEN.value,
            AuditEventType.SUSPICIOUS_ACTIVITY.value
        ]

        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            placeholders = ','.join('?' * len(security_events))
            cur.execute(f"""
                SELECT * FROM auth_audit_log
                WHERE event_type IN ({placeholders})
                AND datetime(timestamp) >= datetime(?)
                ORDER BY timestamp DESC
            """, security_events + [start_time.isoformat()])

            events = []
            for row in cur.fetchall():
                event = dict(row)
                if event.get('details'):
                    event['details'] = json.loads(event['details'])
                events.append(event)

            return events
        finally:
            conn.close()

    def get_user_activity(self, user_id: str, days: int = 7) -> List[Dict]:
        """Get all activity for a specific user"""
        start_time = datetime.utcnow() - timedelta(days=days)
        return self.get_events(user_id=user_id, start_time=start_time, limit=500)

    def get_ip_activity(self, ip_address: str, hours: int = 24) -> List[Dict]:
        """Get all activity from a specific IP address"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return self.get_events(ip_address=ip_address, start_time=start_time, limit=500)

    def get_failed_logins(self, hours: int = 24) -> List[Dict]:
        """Get failed login attempts from the last N hours"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return self.get_events(
            event_type=AuditEventType.LOGIN_FAILURE.value,
            start_time=start_time,
            limit=500
        )

    def get_statistics(self, hours: int = 24) -> Dict:
        """Get audit log statistics"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            start_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

            # Total events
            cur.execute("""
                SELECT COUNT(*) FROM auth_audit_log
                WHERE datetime(timestamp) >= datetime(?)
            """, (start_time,))
            total_events = cur.fetchone()[0]

            # Events by type
            cur.execute("""
                SELECT event_type, COUNT(*) as count
                FROM auth_audit_log
                WHERE datetime(timestamp) >= datetime(?)
                GROUP BY event_type
                ORDER BY count DESC
            """, (start_time,))
            by_type = {row[0]: row[1] for row in cur.fetchall()}

            # Events by severity
            cur.execute("""
                SELECT severity, COUNT(*) as count
                FROM auth_audit_log
                WHERE datetime(timestamp) >= datetime(?)
                GROUP BY severity
            """, (start_time,))
            by_severity = {row[0]: row[1] for row in cur.fetchall()}

            # Top IPs with failed logins
            cur.execute("""
                SELECT ip_address, COUNT(*) as count
                FROM auth_audit_log
                WHERE event_type = 'login_failure'
                AND datetime(timestamp) >= datetime(?)
                GROUP BY ip_address
                ORDER BY count DESC
                LIMIT 10
            """, (start_time,))
            failed_login_ips = {row[0]: row[1] for row in cur.fetchall()}

            return {
                'period_hours': hours,
                'total_events': total_events,
                'by_event_type': by_type,
                'by_severity': by_severity,
                'failed_login_ips': failed_login_ips
            }
        finally:
            conn.close()

    def cleanup_old_events(self, days: int = 90) -> int:
        """Remove audit events older than N days"""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

            cur.execute("""
                DELETE FROM auth_audit_log
                WHERE datetime(timestamp) < datetime(?)
            """, (cutoff,))

            deleted = cur.rowcount
            conn.commit()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} audit events older than {days} days")

            return deleted
        finally:
            conn.close()


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db_path: str = "~/.fleet-data/users.db") -> AuditLogger:
    """Get or create the audit logger singleton"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(db_path)
    return _audit_logger


__all__ = [
    'AuditEventType',
    'AuditSeverity',
    'AuditEvent',
    'AuditLogger',
    'get_audit_logger',
]
