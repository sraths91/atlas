"""
Custom Alert Rules Manager with Database Persistence

Provides a comprehensive alert rules system with:
- Database-backed rule persistence (SQLite)
- Severity levels (info, warning, critical)
- Webhook notification support
- Email notification support
- CRUD operations for rules
- Rule validation and testing
"""

import json
import logging
import sqlite3
import threading
import time
import hashlib
import smtplib
import ssl
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import subprocess
import os

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MetricType(Enum):
    """Supported metric types for alerting"""
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    DISK = "disk"
    TEMPERATURE = "temperature"
    BATTERY = "battery"
    NETWORK_UP = "network_up"
    NETWORK_DOWN = "network_down"
    DOWNLOAD_SPEED = "download_speed"
    UPLOAD_SPEED = "upload_speed"
    PING = "ping"
    PACKET_LOSS = "packet_loss"


class Condition(Enum):
    """Comparison conditions for alert rules"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUALS = "=="
    NOT_EQUALS = "!="


class NotificationType(Enum):
    """Notification delivery methods"""
    SYSTEM = "system"  # macOS/Linux native notifications
    WEBHOOK = "webhook"
    EMAIL = "email"


@dataclass
class AlertRule:
    """A custom alert rule definition"""
    id: str
    name: str
    description: str
    metric_type: str  # MetricType value
    condition: str  # Condition value
    threshold: float
    severity: str = "warning"  # AlertSeverity value
    cooldown_seconds: int = 300  # Time between repeated alerts
    enabled: bool = True
    notification_types: List[str] = field(default_factory=lambda: ["system"])
    webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    message_template: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_triggered_at: Optional[str] = None
    trigger_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'metric_type': self.metric_type,
            'condition': self.condition,
            'threshold': self.threshold,
            'severity': self.severity,
            'cooldown_seconds': self.cooldown_seconds,
            'enabled': self.enabled,
            'notification_types': self.notification_types,
            'webhook_url': self.webhook_url,
            'email_recipients': self.email_recipients,
            'message_template': self.message_template,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_triggered_at': self.last_triggered_at,
            'trigger_count': self.trigger_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertRule':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            metric_type=data['metric_type'],
            condition=data['condition'],
            threshold=float(data['threshold']),
            severity=data.get('severity', 'warning'),
            cooldown_seconds=int(data.get('cooldown_seconds', 300)),
            enabled=bool(data.get('enabled', True)),
            notification_types=data.get('notification_types', ['system']),
            webhook_url=data.get('webhook_url'),
            email_recipients=data.get('email_recipients', []),
            message_template=data.get('message_template', ''),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            last_triggered_at=data.get('last_triggered_at'),
            trigger_count=int(data.get('trigger_count', 0)),
        )


@dataclass
class AlertEvent:
    """A triggered alert event"""
    id: str
    rule_id: str
    rule_name: str
    metric_type: str
    metric_value: float
    threshold: float
    condition: str
    severity: str
    message: str
    triggered_at: str
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EmailConfig:
    """Email notification configuration"""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_address: str = ""
    enabled: bool = False


class AlertRulesManager:
    """
    Manages custom alert rules with database persistence.

    Features:
    - Create, read, update, delete alert rules
    - Persist rules to SQLite database
    - Evaluate metrics against rules
    - Send notifications via system, webhook, or email
    - Track alert history and statistics
    """

    # Default rules provided out of the box
    DEFAULT_RULES = [
        {
            'id': 'default_cpu_high',
            'name': 'High CPU Usage',
            'description': 'Alert when CPU usage exceeds 90%',
            'metric_type': 'cpu',
            'condition': '>',
            'threshold': 90.0,
            'severity': 'warning',
            'cooldown_seconds': 300,
            'message_template': 'High CPU usage detected: {value:.1f}%',
        },
        {
            'id': 'default_memory_high',
            'name': 'High Memory Usage',
            'description': 'Alert when memory usage exceeds 90%',
            'metric_type': 'memory',
            'condition': '>',
            'threshold': 90.0,
            'severity': 'warning',
            'cooldown_seconds': 300,
            'message_template': 'High memory usage: {value:.1f}%',
        },
        {
            'id': 'default_temp_high',
            'name': 'High Temperature',
            'description': 'Alert when temperature exceeds 80°C',
            'metric_type': 'temperature',
            'condition': '>',
            'threshold': 80.0,
            'severity': 'critical',
            'cooldown_seconds': 300,
            'message_template': 'High temperature: {value:.1f}°C',
        },
        {
            'id': 'default_battery_low',
            'name': 'Low Battery',
            'description': 'Alert when battery drops below 20%',
            'metric_type': 'battery',
            'condition': '<',
            'threshold': 20.0,
            'severity': 'warning',
            'cooldown_seconds': 600,
            'message_template': 'Low battery: {value:.1f}% remaining',
        },
        {
            'id': 'default_battery_critical',
            'name': 'Critical Battery',
            'description': 'Alert when battery drops below 10%',
            'metric_type': 'battery',
            'condition': '<',
            'threshold': 10.0,
            'severity': 'critical',
            'cooldown_seconds': 300,
            'message_template': 'Critical battery: {value:.1f}% remaining',
        },
        {
            'id': 'default_disk_high',
            'name': 'High Disk Usage',
            'description': 'Alert when disk usage exceeds 90%',
            'metric_type': 'disk',
            'condition': '>',
            'threshold': 90.0,
            'severity': 'warning',
            'cooldown_seconds': 3600,
            'message_template': 'Disk space running low: {value:.1f}% used',
        },
        {
            'id': 'default_slow_download',
            'name': 'Slow Download Speed',
            'description': 'Alert when download speed drops below 20 Mbps',
            'metric_type': 'download_speed',
            'condition': '<',
            'threshold': 20.0,
            'severity': 'info',
            'cooldown_seconds': 600,
            'message_template': 'Slow download speed: {value:.1f} Mbps',
        },
        {
            'id': 'default_high_ping',
            'name': 'High Latency',
            'description': 'Alert when ping exceeds 100ms',
            'metric_type': 'ping',
            'condition': '>',
            'threshold': 100.0,
            'severity': 'warning',
            'cooldown_seconds': 300,
            'message_template': 'High latency detected: {value:.1f}ms',
        },
    ]

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the Alert Rules Manager.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.atlas/alert_rules.db
        """
        if db_path is None:
            db_dir = Path.home() / '.atlas'
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / 'alert_rules.db')

        self.db_path = db_path
        self._lock = threading.Lock()
        self._last_trigger_times: Dict[str, float] = {}
        self._email_config: Optional[EmailConfig] = None

        self._init_database()
        self._load_email_config()

    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    metric_type TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    severity TEXT DEFAULT 'warning',
                    cooldown_seconds INTEGER DEFAULT 300,
                    enabled INTEGER DEFAULT 1,
                    notification_types TEXT DEFAULT '["system"]',
                    webhook_url TEXT,
                    email_recipients TEXT DEFAULT '[]',
                    message_template TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_triggered_at TEXT,
                    trigger_count INTEGER DEFAULT 0,
                    is_default INTEGER DEFAULT 0
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS alert_events (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    condition TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    triggered_at TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0,
                    acknowledged_at TEXT,
                    acknowledged_by TEXT,
                    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
                )
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_rule_id
                ON alert_events(rule_id)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_triggered_at
                ON alert_events(triggered_at)
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    smtp_host TEXT DEFAULT 'smtp.gmail.com',
                    smtp_port INTEGER DEFAULT 587,
                    use_tls INTEGER DEFAULT 1,
                    username TEXT,
                    password_encrypted TEXT,
                    from_address TEXT,
                    enabled INTEGER DEFAULT 0
                )
            ''')

            conn.commit()

            # Initialize default rules if none exist
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM alert_rules')
            if cur.fetchone()[0] == 0:
                self._seed_default_rules(conn)

    def _seed_default_rules(self, conn: sqlite3.Connection):
        """Seed the database with default rules"""
        now = datetime.now().isoformat()
        for rule_data in self.DEFAULT_RULES:
            conn.execute('''
                INSERT INTO alert_rules (
                    id, name, description, metric_type, condition, threshold,
                    severity, cooldown_seconds, enabled, notification_types,
                    message_template, created_at, updated_at, is_default
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (
                rule_data['id'],
                rule_data['name'],
                rule_data.get('description', ''),
                rule_data['metric_type'],
                rule_data['condition'],
                rule_data['threshold'],
                rule_data.get('severity', 'warning'),
                rule_data.get('cooldown_seconds', 300),
                1,  # enabled
                json.dumps(['system']),
                rule_data.get('message_template', ''),
                now,
                now,
            ))
        conn.commit()
        logger.info(f"Seeded {len(self.DEFAULT_RULES)} default alert rules")

    def _load_email_config(self):
        """Load email configuration from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT * FROM email_config WHERE id = 1')
            row = cur.fetchone()
            if row:
                self._email_config = EmailConfig(
                    smtp_host=row['smtp_host'] or 'smtp.gmail.com',
                    smtp_port=row['smtp_port'] or 587,
                    use_tls=bool(row['use_tls']),
                    username=row['username'] or '',
                    password=row['password_encrypted'] or '',  # In production, decrypt this
                    from_address=row['from_address'] or '',
                    enabled=bool(row['enabled']),
                )

    # ==================== RULE CRUD OPERATIONS ====================

    def create_rule(self, rule_data: Dict[str, Any]) -> Tuple[bool, str, Optional[AlertRule]]:
        """
        Create a new alert rule.

        Args:
            rule_data: Dictionary containing rule properties

        Returns:
            Tuple of (success, message, rule)
        """
        # Validate required fields
        required = ['name', 'metric_type', 'condition', 'threshold']
        for field in required:
            if field not in rule_data:
                return False, f"Missing required field: {field}", None

        # Validate metric type
        valid_metrics = [m.value for m in MetricType]
        if rule_data['metric_type'] not in valid_metrics:
            return False, f"Invalid metric_type. Must be one of: {valid_metrics}", None

        # Validate condition
        valid_conditions = [c.value for c in Condition]
        if rule_data['condition'] not in valid_conditions:
            return False, f"Invalid condition. Must be one of: {valid_conditions}", None

        # Validate severity
        valid_severities = [s.value for s in AlertSeverity]
        severity = rule_data.get('severity', 'warning')
        if severity not in valid_severities:
            return False, f"Invalid severity. Must be one of: {valid_severities}", None

        # Generate ID
        rule_id = rule_data.get('id') or self._generate_rule_id(rule_data['name'])

        now = datetime.now().isoformat()
        rule = AlertRule(
            id=rule_id,
            name=rule_data['name'],
            description=rule_data.get('description', ''),
            metric_type=rule_data['metric_type'],
            condition=rule_data['condition'],
            threshold=float(rule_data['threshold']),
            severity=severity,
            cooldown_seconds=int(rule_data.get('cooldown_seconds', 300)),
            enabled=rule_data.get('enabled', True),
            notification_types=rule_data.get('notification_types', ['system']),
            webhook_url=rule_data.get('webhook_url'),
            email_recipients=rule_data.get('email_recipients', []),
            message_template=rule_data.get('message_template', ''),
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT INTO alert_rules (
                            id, name, description, metric_type, condition, threshold,
                            severity, cooldown_seconds, enabled, notification_types,
                            webhook_url, email_recipients, message_template,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        rule.id, rule.name, rule.description, rule.metric_type,
                        rule.condition, rule.threshold, rule.severity,
                        rule.cooldown_seconds, int(rule.enabled),
                        json.dumps(rule.notification_types), rule.webhook_url,
                        json.dumps(rule.email_recipients), rule.message_template,
                        rule.created_at, rule.updated_at,
                    ))
                    conn.commit()
                logger.info(f"Created alert rule: {rule.name} ({rule.id})")
                return True, "Rule created successfully", rule
            except sqlite3.IntegrityError:
                return False, f"Rule with ID '{rule_id}' already exists", None
            except Exception as e:
                logger.error(f"Failed to create rule: {e}")
                return False, str(e), None

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get a single rule by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT * FROM alert_rules WHERE id = ?', (rule_id,))
            row = cur.fetchone()
            if row:
                return self._row_to_rule(row)
        return None

    def list_rules(self, include_disabled: bool = True) -> List[AlertRule]:
        """Get all alert rules"""
        rules = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if include_disabled:
                cur.execute('SELECT * FROM alert_rules ORDER BY created_at DESC')
            else:
                cur.execute('SELECT * FROM alert_rules WHERE enabled = 1 ORDER BY created_at DESC')
            for row in cur.fetchall():
                rules.append(self._row_to_rule(row))
        return rules

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update an existing rule.

        Args:
            rule_id: ID of rule to update
            updates: Dictionary of fields to update

        Returns:
            Tuple of (success, message)
        """
        # Validate updates
        if 'metric_type' in updates:
            valid_metrics = [m.value for m in MetricType]
            if updates['metric_type'] not in valid_metrics:
                return False, f"Invalid metric_type. Must be one of: {valid_metrics}"

        if 'condition' in updates:
            valid_conditions = [c.value for c in Condition]
            if updates['condition'] not in valid_conditions:
                return False, f"Invalid condition. Must be one of: {valid_conditions}"

        if 'severity' in updates:
            valid_severities = [s.value for s in AlertSeverity]
            if updates['severity'] not in valid_severities:
                return False, f"Invalid severity. Must be one of: {valid_severities}"

        with self._lock:
            existing = self.get_rule(rule_id)
            if not existing:
                return False, f"Rule not found: {rule_id}"

            # Build update query
            allowed_fields = [
                'name', 'description', 'metric_type', 'condition', 'threshold',
                'severity', 'cooldown_seconds', 'enabled', 'notification_types',
                'webhook_url', 'email_recipients', 'message_template'
            ]

            set_clauses = []
            values = []

            for field in allowed_fields:
                if field in updates:
                    value = updates[field]
                    if field in ('notification_types', 'email_recipients'):
                        value = json.dumps(value)
                    elif field == 'enabled':
                        value = int(value)
                    set_clauses.append(f"{field} = ?")
                    values.append(value)

            if not set_clauses:
                return False, "No valid fields to update"

            set_clauses.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(rule_id)

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        f"UPDATE alert_rules SET {', '.join(set_clauses)} WHERE id = ?",
                        values
                    )
                    conn.commit()
                logger.info(f"Updated alert rule: {rule_id}")
                return True, "Rule updated successfully"
            except Exception as e:
                logger.error(f"Failed to update rule: {e}")
                return False, str(e)

    def delete_rule(self, rule_id: str) -> Tuple[bool, str]:
        """Delete an alert rule"""
        with self._lock:
            existing = self.get_rule(rule_id)
            if not existing:
                return False, f"Rule not found: {rule_id}"

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM alert_rules WHERE id = ?', (rule_id,))
                    conn.commit()
                logger.info(f"Deleted alert rule: {rule_id}")
                return True, "Rule deleted successfully"
            except Exception as e:
                logger.error(f"Failed to delete rule: {e}")
                return False, str(e)

    def toggle_rule(self, rule_id: str, enabled: bool) -> Tuple[bool, str]:
        """Enable or disable a rule"""
        return self.update_rule(rule_id, {'enabled': enabled})

    def reset_to_defaults(self) -> Tuple[bool, str]:
        """Reset all rules to defaults"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM alert_rules')
                    self._seed_default_rules(conn)
                logger.info("Reset alert rules to defaults")
                return True, "Rules reset to defaults"
            except Exception as e:
                logger.error(f"Failed to reset rules: {e}")
                return False, str(e)

    # ==================== RULE EVALUATION ====================

    def evaluate_metrics(self, metrics: Dict[str, float]) -> List[AlertEvent]:
        """
        Evaluate current metrics against all enabled rules.

        Args:
            metrics: Dictionary of metric_type -> value

        Returns:
            List of triggered AlertEvents
        """
        triggered_events = []
        rules = self.list_rules(include_disabled=False)
        now = time.time()

        for rule in rules:
            metric_value = metrics.get(rule.metric_type)
            if metric_value is None:
                continue

            # Check cooldown
            last_trigger = self._last_trigger_times.get(rule.id, 0)
            if now - last_trigger < rule.cooldown_seconds:
                continue

            # Evaluate condition
            if self._evaluate_condition(metric_value, rule.condition, rule.threshold):
                event = self._create_alert_event(rule, metric_value)
                triggered_events.append(event)
                self._last_trigger_times[rule.id] = now

                # Update rule statistics
                self._update_rule_trigger_stats(rule.id)

                # Save event to database
                self._save_alert_event(event)

                # Send notifications
                self._send_notifications(rule, event)

        return triggered_events

    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate a condition"""
        conditions = {
            '>': value > threshold,
            '<': value < threshold,
            '>=': value >= threshold,
            '<=': value <= threshold,
            '==': value == threshold,
            '!=': value != threshold,
        }
        return conditions.get(condition, False)

    def _create_alert_event(self, rule: AlertRule, metric_value: float) -> AlertEvent:
        """Create an alert event from a triggered rule"""
        message = rule.message_template or f"{rule.name}: {metric_value}"
        if '{value' in message:
            message = message.format(value=metric_value)

        return AlertEvent(
            id=self._generate_event_id(),
            rule_id=rule.id,
            rule_name=rule.name,
            metric_type=rule.metric_type,
            metric_value=metric_value,
            threshold=rule.threshold,
            condition=rule.condition,
            severity=rule.severity,
            message=message,
            triggered_at=datetime.now().isoformat(),
        )

    def _update_rule_trigger_stats(self, rule_id: str):
        """Update trigger statistics for a rule"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE alert_rules
                SET trigger_count = trigger_count + 1,
                    last_triggered_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), rule_id))
            conn.commit()

    def _save_alert_event(self, event: AlertEvent):
        """Save alert event to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO alert_events (
                    id, rule_id, rule_name, metric_type, metric_value,
                    threshold, condition, severity, message, triggered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.id, event.rule_id, event.rule_name, event.metric_type,
                event.metric_value, event.threshold, event.condition,
                event.severity, event.message, event.triggered_at,
            ))
            conn.commit()

    # ==================== NOTIFICATIONS ====================

    def _send_notifications(self, rule: AlertRule, event: AlertEvent):
        """Send notifications for a triggered alert"""
        for notification_type in rule.notification_types:
            try:
                if notification_type == 'system':
                    self._send_system_notification(event)
                elif notification_type == 'webhook' and rule.webhook_url:
                    self._send_webhook_notification(rule.webhook_url, event)
                elif notification_type == 'email' and rule.email_recipients:
                    self._send_email_notification(rule.email_recipients, event)
            except Exception as e:
                logger.error(f"Failed to send {notification_type} notification: {e}")

    def _send_system_notification(self, event: AlertEvent):
        """Send native system notification"""
        title = self._escape_applescript(f"ATLAS Alert: {event.rule_name}")
        message = self._escape_applescript(event.message)

        severity_sounds = {
            'info': 'Pop',
            'warning': 'Submarine',
            'critical': 'Basso',
        }
        sound = severity_sounds.get(event.severity, 'Submarine')

        try:
            if os.uname().sysname == 'Darwin':
                script = f'display notification "{message}" with title "{title}" sound name "{sound}"'
                subprocess.run(['osascript', '-e', script], capture_output=True, timeout=5)
            else:
                urgency = 'critical' if event.severity == 'critical' else 'normal'
                subprocess.run([
                    'notify-send', '-u', urgency, title, message
                ], timeout=5)
        except Exception as e:
            logger.warning(f"Failed to send system notification: {e}")

    @staticmethod
    def _escape_applescript(text: str) -> str:
        """Escape text for AppleScript"""
        return text.replace('\\', '\\\\').replace('"', '\\"')

    def _send_webhook_notification(self, webhook_url: str, event: AlertEvent):
        """Send webhook notification"""
        payload = {
            'event_type': 'atlas_alert',
            'alert': event.to_dict(),
            'timestamp': datetime.now().isoformat(),
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            request = Request(
                webhook_url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'ATLAS-Alert-System/1.0',
                }
            )
            with urlopen(request, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"Webhook notification sent successfully to {webhook_url}")
                else:
                    logger.warning(f"Webhook returned status {response.status}")
        except (URLError, HTTPError) as e:
            logger.error(f"Failed to send webhook notification: {e}")

    def _send_email_notification(self, recipients: List[str], event: AlertEvent):
        """Send email notification"""
        if not self._email_config or not self._email_config.enabled:
            logger.warning("Email notifications not configured")
            return

        severity_colors = {
            'info': '#2196F3',
            'warning': '#FF9800',
            'critical': '#F44336',
        }
        color = severity_colors.get(event.severity, '#FF9800')

        subject = f"[ATLAS {event.severity.upper()}] {event.rule_name}"
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="border-left: 4px solid {color}; padding: 10px 20px; margin: 10px 0;">
                <h2 style="color: {color}; margin: 0 0 10px 0;">ATLAS Alert: {event.rule_name}</h2>
                <p><strong>Severity:</strong> {event.severity.upper()}</p>
                <p><strong>Message:</strong> {event.message}</p>
                <p><strong>Metric:</strong> {event.metric_type}</p>
                <p><strong>Value:</strong> {event.metric_value:.2f}</p>
                <p><strong>Threshold:</strong> {event.condition} {event.threshold}</p>
                <p><strong>Time:</strong> {event.triggered_at}</p>
            </div>
            <p style="color: #666; font-size: 12px;">
                This is an automated alert from ATLAS System Monitor.
            </p>
        </body>
        </html>
        """

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self._email_config.from_address
            msg['To'] = ', '.join(recipients)
            msg.attach(MIMEText(html_body, 'html'))

            context = ssl.create_default_context()
            with smtplib.SMTP(self._email_config.smtp_host, self._email_config.smtp_port) as server:
                if self._email_config.use_tls:
                    server.starttls(context=context)
                server.login(self._email_config.username, self._email_config.password)
                server.sendmail(
                    self._email_config.from_address,
                    recipients,
                    msg.as_string()
                )
            logger.info(f"Email notification sent to {recipients}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    # ==================== EMAIL CONFIGURATION ====================

    def configure_email(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Configure email notifications.

        Args:
            config: Dictionary with smtp_host, smtp_port, use_tls, username, password, from_address
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO email_config (
                        id, smtp_host, smtp_port, use_tls, username,
                        password_encrypted, from_address, enabled
                    ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    config.get('smtp_host', 'smtp.gmail.com'),
                    config.get('smtp_port', 587),
                    int(config.get('use_tls', True)),
                    config.get('username', ''),
                    config.get('password', ''),  # In production, encrypt this
                    config.get('from_address', ''),
                    int(config.get('enabled', False)),
                ))
                conn.commit()

            self._load_email_config()
            logger.info("Email configuration updated")
            return True, "Email configuration saved"
        except Exception as e:
            logger.error(f"Failed to configure email: {e}")
            return False, str(e)

    def get_email_config(self) -> Optional[Dict[str, Any]]:
        """Get email configuration (without password)"""
        if self._email_config:
            return {
                'smtp_host': self._email_config.smtp_host,
                'smtp_port': self._email_config.smtp_port,
                'use_tls': self._email_config.use_tls,
                'username': self._email_config.username,
                'from_address': self._email_config.from_address,
                'enabled': self._email_config.enabled,
            }
        return None

    def test_email(self, recipient: str) -> Tuple[bool, str]:
        """Send a test email"""
        if not self._email_config or not self._email_config.enabled:
            return False, "Email notifications not configured"

        test_event = AlertEvent(
            id='test',
            rule_id='test',
            rule_name='Test Alert',
            metric_type='cpu',
            metric_value=50.0,
            threshold=90.0,
            condition='>',
            severity='info',
            message='This is a test notification from ATLAS',
            triggered_at=datetime.now().isoformat(),
        )

        try:
            self._send_email_notification([recipient], test_event)
            return True, f"Test email sent to {recipient}"
        except Exception as e:
            return False, str(e)

    # ==================== ALERT HISTORY ====================

    def get_alert_events(
        self,
        rule_id: Optional[str] = None,
        severity: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[AlertEvent]:
        """Get historical alert events"""
        events = []
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            query = 'SELECT * FROM alert_events WHERE triggered_at >= ?'
            params = [cutoff]

            if rule_id:
                query += ' AND rule_id = ?'
                params.append(rule_id)

            if severity:
                query += ' AND severity = ?'
                params.append(severity)

            query += ' ORDER BY triggered_at DESC LIMIT ?'
            params.append(limit)

            cur.execute(query, params)
            for row in cur.fetchall():
                events.append(AlertEvent(
                    id=row['id'],
                    rule_id=row['rule_id'],
                    rule_name=row['rule_name'],
                    metric_type=row['metric_type'],
                    metric_value=row['metric_value'],
                    threshold=row['threshold'],
                    condition=row['condition'],
                    severity=row['severity'],
                    message=row['message'],
                    triggered_at=row['triggered_at'],
                    acknowledged=bool(row['acknowledged']),
                    acknowledged_at=row['acknowledged_at'],
                    acknowledged_by=row['acknowledged_by'],
                ))

        return events

    def acknowledge_event(self, event_id: str, acknowledged_by: str) -> Tuple[bool, str]:
        """Acknowledge an alert event"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE alert_events
                    SET acknowledged = 1,
                        acknowledged_at = ?,
                        acknowledged_by = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), acknowledged_by, event_id))
                if conn.total_changes == 0:
                    return False, "Event not found"
                conn.commit()
            return True, "Event acknowledged"
        except Exception as e:
            return False, str(e)

    def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            # Total events
            cur.execute(
                'SELECT COUNT(*) FROM alert_events WHERE triggered_at >= ?',
                (cutoff,)
            )
            total_events = cur.fetchone()[0]

            # By severity
            cur.execute('''
                SELECT severity, COUNT(*)
                FROM alert_events
                WHERE triggered_at >= ?
                GROUP BY severity
            ''', (cutoff,))
            by_severity = dict(cur.fetchall())

            # By rule
            cur.execute('''
                SELECT rule_name, COUNT(*)
                FROM alert_events
                WHERE triggered_at >= ?
                GROUP BY rule_id
                ORDER BY COUNT(*) DESC
                LIMIT 10
            ''', (cutoff,))
            by_rule = [{'rule': r[0], 'count': r[1]} for r in cur.fetchall()]

            # Unacknowledged
            cur.execute(
                'SELECT COUNT(*) FROM alert_events WHERE acknowledged = 0 AND triggered_at >= ?',
                (cutoff,)
            )
            unacknowledged = cur.fetchone()[0]

        return {
            'period_hours': hours,
            'total_events': total_events,
            'unacknowledged': unacknowledged,
            'by_severity': by_severity,
            'top_rules': by_rule,
        }

    def cleanup_old_events(self, days: int = 30) -> int:
        """Remove events older than N days"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM alert_events WHERE triggered_at < ?', (cutoff,))
            deleted = cur.rowcount
            conn.commit()
        logger.info(f"Cleaned up {deleted} old alert events")
        return deleted

    # ==================== HELPER METHODS ====================

    def _row_to_rule(self, row: sqlite3.Row) -> AlertRule:
        """Convert database row to AlertRule"""
        return AlertRule(
            id=row['id'],
            name=row['name'],
            description=row['description'] or '',
            metric_type=row['metric_type'],
            condition=row['condition'],
            threshold=row['threshold'],
            severity=row['severity'],
            cooldown_seconds=row['cooldown_seconds'],
            enabled=bool(row['enabled']),
            notification_types=json.loads(row['notification_types'] or '["system"]'),
            webhook_url=row['webhook_url'],
            email_recipients=json.loads(row['email_recipients'] or '[]'),
            message_template=row['message_template'] or '',
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_triggered_at=row['last_triggered_at'],
            trigger_count=row['trigger_count'],
        )

    def _generate_rule_id(self, name: str) -> str:
        """Generate a unique rule ID"""
        base = name.lower().replace(' ', '_')[:20]
        suffix = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:6]
        return f"{base}_{suffix}"

    def _generate_event_id(self) -> str:
        """Generate a unique event ID"""
        return hashlib.md5(f"event_{time.time()}".encode()).hexdigest()[:16]


# ==================== SINGLETON INSTANCE ====================

_manager_instance: Optional[AlertRulesManager] = None
_manager_lock = threading.Lock()


def get_alert_rules_manager(db_path: Optional[str] = None) -> AlertRulesManager:
    """Get the singleton AlertRulesManager instance (thread-safe)"""
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = AlertRulesManager(db_path)
    return _manager_instance
