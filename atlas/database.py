"""Database module for storing historical system metrics."""
import sqlite3
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    import secrets
    import platform
    import subprocess
    import uuid
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


class MetricsDatabase:
    """SQLite database for storing system metrics history.

    When the cryptography package is available, metrics are automatically
    encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256) with a
    machine-bound key derived via PBKDF2.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the database connection."""
        if db_path is None:
            db_dir = Path.home() / '.atlas'
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / 'metrics.db')

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Initialize encryption
        self.fernet = None
        self._encryption_key_b64: Optional[str] = None
        if ENCRYPTION_AVAILABLE:
            key = self._derive_key()
            if key:
                self.fernet = Fernet(key)
                self._encryption_key_b64 = key.decode('ascii')
        self.encrypted = self.fernet is not None

        self._create_tables()

    @property
    def encryption_key_b64(self) -> Optional[str]:
        """Base64-url-safe Fernet key for fleet sharing. None if unencrypted."""
        return self._encryption_key_b64

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create a new random one."""
        salt_path = Path(self.db_path + '.salt')
        if salt_path.exists():
            try:
                return salt_path.read_bytes()
            except Exception as e:
                logger.warning(f"Could not load salt file, generating new one: {e}")

        salt = secrets.token_bytes(32)
        try:
            salt_path.parent.mkdir(parents=True, exist_ok=True)
            salt_path.write_bytes(salt)
            salt_path.chmod(0o600)
            logger.info(f"Generated new encryption salt: {salt_path}")
        except Exception as e:
            logger.error(f"Could not save salt file: {e}")

        return salt

    def _derive_key(self) -> Optional[bytes]:
        """Derive a machine-bound encryption key using stable hardware identifiers."""
        try:
            hardware_uuid = None
            try:
                if platform.system() == 'Darwin':
                    result = subprocess.run(
                        ['system_profiler', 'SPHardwareDataType'],
                        capture_output=True, text=True, timeout=5
                    )
                    for line in result.stdout.split('\n'):
                        if 'Hardware UUID' in line:
                            hardware_uuid = line.split(':')[1].strip()
                            break
            except Exception:
                pass

            machine_data = (
                (hardware_uuid or str(uuid.getnode())) +
                platform.machine() +
                platform.system()
            )

            salt = self._get_or_create_salt()

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=600000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(machine_data.encode()))
            return key
        except Exception as e:
            logger.error(f"Failed to derive encryption key: {e}")
            return None

    def _encrypt(self, data: str) -> str:
        """Encrypt a string using Fernet."""
        return self.fernet.encrypt(data.encode()).decode('utf-8')

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt a Fernet-encrypted string."""
        if not encrypted_data:
            return "{}"
        return self.fernet.decrypt(encrypted_data.encode()).decode('utf-8')

    def _create_tables(self):
        """Create database tables, handling schema migration."""
        cursor = self.conn.cursor()

        # Check current schema version
        cursor.execute('PRAGMA user_version')
        schema_version = cursor.fetchone()[0]

        if self.encrypted:
            # Encrypted schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    encrypted_data TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_v2_ts
                ON metrics_v2(timestamp)
            ''')

            # Migrate legacy data if it exists
            if schema_version < 2:
                self._migrate_to_encrypted(cursor)
                cursor.execute('PRAGMA user_version = 2')
        else:
            # Legacy plaintext schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cpu_usage REAL,
                    gpu_usage REAL,
                    memory_usage REAL,
                    memory_used INTEGER,
                    memory_total INTEGER,
                    disk_usage REAL,
                    disk_used INTEGER,
                    disk_total INTEGER,
                    network_up REAL,
                    network_down REAL,
                    battery_percent REAL,
                    battery_plugged INTEGER,
                    temperature REAL
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON metrics(timestamp)
            ''')

        # Alerts table (plaintext - not sensitive)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                alert_type TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                message TEXT
            )
        ''')

        self.conn.commit()

    def _migrate_to_encrypted(self, cursor):
        """Migrate legacy plaintext metrics to encrypted format."""
        try:
            # Check if legacy table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'"
            )
            if not cursor.fetchone():
                return

            cursor.execute('SELECT * FROM metrics')
            rows = cursor.fetchall()

            if rows:
                logger.info(f"Migrating {len(rows)} metrics rows to encrypted format...")
                metric_keys = [
                    'cpu_usage', 'gpu_usage', 'memory_usage', 'memory_used',
                    'memory_total', 'disk_usage', 'disk_used', 'disk_total',
                    'network_up', 'network_down', 'battery_percent',
                    'battery_plugged', 'temperature'
                ]

                for row in rows:
                    row_dict = dict(row)
                    payload = {k: row_dict.get(k, 0) for k in metric_keys}
                    encrypted = self._encrypt(json.dumps(payload))
                    cursor.execute(
                        'INSERT INTO metrics_v2 (timestamp, encrypted_data) VALUES (?, ?)',
                        (row_dict['timestamp'], encrypted)
                    )

                logger.info("Migration complete")

            cursor.execute('DROP TABLE IF EXISTS metrics')
            cursor.execute('DROP INDEX IF EXISTS idx_timestamp')
        except Exception as e:
            logger.error(f"Migration failed: {e}")

    def insert_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Insert a metrics snapshot into the database."""
        try:
            cursor = self.conn.cursor()
            timestamp = metrics.get('timestamp', datetime.now().timestamp())

            if self.encrypted:
                payload = {
                    'cpu_usage': metrics.get('cpu', 0),
                    'gpu_usage': metrics.get('gpu', 0),
                    'memory_usage': metrics.get('memory', 0),
                    'memory_used': metrics.get('memory_used', 0),
                    'memory_total': metrics.get('memory_total', 0),
                    'disk_usage': metrics.get('disk', 0),
                    'disk_used': metrics.get('disk_used', 0),
                    'disk_total': metrics.get('disk_total', 0),
                    'network_up': metrics.get('network_up', 0),
                    'network_down': metrics.get('network_down', 0),
                    'battery_percent': metrics.get('battery', 0),
                    'battery_plugged': metrics.get('battery_plugged', 0),
                    'temperature': metrics.get('temperature', 0),
                }
                encrypted_data = self._encrypt(json.dumps(payload))
                cursor.execute(
                    'INSERT INTO metrics_v2 (timestamp, encrypted_data) VALUES (?, ?)',
                    (timestamp, encrypted_data)
                )
            else:
                cursor.execute('''
                    INSERT INTO metrics (
                        timestamp, cpu_usage, gpu_usage, memory_usage,
                        memory_used, memory_total, disk_usage, disk_used,
                        disk_total, network_up, network_down, battery_percent,
                        battery_plugged, temperature
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp,
                    metrics.get('cpu', 0),
                    metrics.get('gpu', 0),
                    metrics.get('memory', 0),
                    metrics.get('memory_used', 0),
                    metrics.get('memory_total', 0),
                    metrics.get('disk', 0),
                    metrics.get('disk_used', 0),
                    metrics.get('disk_total', 0),
                    metrics.get('network_up', 0),
                    metrics.get('network_down', 0),
                    metrics.get('battery', 0),
                    metrics.get('battery_plugged', 0),
                    metrics.get('temperature', 0)
                ))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert metrics: {e}")
            return False

    def get_metrics(self, hours: int = 24, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get metrics from the last N hours."""
        try:
            cursor = self.conn.cursor()
            cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()

            if self.encrypted:
                query = '''
                    SELECT id, timestamp, encrypted_data FROM metrics_v2
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                '''
                if limit:
                    query += f' LIMIT {limit}'

                cursor.execute(query, (cutoff_time,))
                rows = cursor.fetchall()

                result = []
                for row in rows:
                    decrypted = json.loads(self._decrypt(row['encrypted_data']))
                    decrypted['id'] = row['id']
                    decrypted['timestamp'] = row['timestamp']
                    result.append(decrypted)
                return result
            else:
                query = '''
                    SELECT * FROM metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                '''
                if limit:
                    query += f' LIMIT {limit}'

                cursor.execute(query, (cutoff_time,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []

    def get_aggregated_metrics(self, hours: int = 24, interval_minutes: int = 5) -> Dict[str, List[Tuple[float, float]]]:
        """Get aggregated metrics with averages over intervals."""
        try:
            cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()
            interval_seconds = interval_minutes * 60

            if self.encrypted:
                # Decrypt all rows and aggregate in Python
                cursor = self.conn.cursor()
                cursor.execute(
                    'SELECT timestamp, encrypted_data FROM metrics_v2 WHERE timestamp >= ? ORDER BY timestamp',
                    (cutoff_time,)
                )
                rows = cursor.fetchall()

                buckets = defaultdict(lambda: defaultdict(list))
                for row in rows:
                    ts = row['timestamp']
                    bucket_key = int(ts / interval_seconds) * interval_seconds
                    decrypted = json.loads(self._decrypt(row['encrypted_data']))
                    for key in ('cpu_usage', 'gpu_usage', 'memory_usage', 'temperature', 'network_up', 'network_down'):
                        buckets[bucket_key][key].append(decrypted.get(key, 0) or 0)

                result = {
                    'cpu': [], 'gpu': [], 'memory': [],
                    'temperature': [], 'network_up': [], 'network_down': []
                }
                key_map = {
                    'cpu': 'cpu_usage', 'gpu': 'gpu_usage', 'memory': 'memory_usage',
                    'temperature': 'temperature', 'network_up': 'network_up', 'network_down': 'network_down'
                }

                for bucket_ts in sorted(buckets.keys()):
                    bucket = buckets[bucket_ts]
                    for result_key, db_key in key_map.items():
                        values = bucket.get(db_key, [0])
                        avg = sum(values) / len(values) if values else 0
                        result[result_key].append((bucket_ts, avg))

                return result
            else:
                cursor = self.conn.cursor()
                query = '''
                    SELECT
                        CAST(timestamp / ? AS INTEGER) * ? as time_bucket,
                        AVG(cpu_usage) as avg_cpu,
                        AVG(gpu_usage) as avg_gpu,
                        AVG(memory_usage) as avg_memory,
                        AVG(temperature) as avg_temp,
                        AVG(network_up) as avg_up,
                        AVG(network_down) as avg_down
                    FROM metrics
                    WHERE timestamp >= ?
                    GROUP BY time_bucket
                    ORDER BY time_bucket
                '''

                cursor.execute(query, (interval_seconds, interval_seconds, cutoff_time))
                rows = cursor.fetchall()

                result = {
                    'cpu': [], 'gpu': [], 'memory': [],
                    'temperature': [], 'network_up': [], 'network_down': []
                }

                for row in rows:
                    timestamp = row['time_bucket']
                    result['cpu'].append((timestamp, row['avg_cpu'] or 0))
                    result['gpu'].append((timestamp, row['avg_gpu'] or 0))
                    result['memory'].append((timestamp, row['avg_memory'] or 0))
                    result['temperature'].append((timestamp, row['avg_temp'] or 0))
                    result['network_up'].append((timestamp, row['avg_up'] or 0))
                    result['network_down'].append((timestamp, row['avg_down'] or 0))

                return result
        except Exception as e:
            logger.error(f"Failed to get aggregated metrics: {e}")
            return {}

    def insert_alert(self, alert: Dict[str, Any]) -> bool:
        """Insert an alert into the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO alerts (timestamp, alert_type, value, threshold, message)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                alert.get('timestamp', datetime.now().timestamp()),
                alert.get('type', ''),
                alert.get('value', 0),
                alert.get('threshold', 0),
                alert.get('message', '')
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert alert: {e}")
            return False

    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts from the last N hours."""
        try:
            cursor = self.conn.cursor()
            cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()

            cursor.execute('''
                SELECT * FROM alerts
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (cutoff_time,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

    def cleanup_old_data(self, days: int = 7):
        """Remove data older than N days."""
        try:
            cursor = self.conn.cursor()
            cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()

            if self.encrypted:
                cursor.execute('DELETE FROM metrics_v2 WHERE timestamp < ?', (cutoff_time,))
            else:
                cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff_time,))
            cursor.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff_time,))

            self.conn.commit()
            logger.info(f"Cleaned up data older than {days} days")
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    def export_to_csv(self, output_path: str, hours: int = 24) -> bool:
        """Export metrics to CSV file."""
        try:
            import csv

            metrics = self.get_metrics(hours=hours)
            if not metrics:
                return False

            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = metrics[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(metrics)

            logger.info(f"Exported {len(metrics)} records to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False

    def export_to_json(self, output_path: str, hours: int = 24) -> bool:
        """Export metrics to JSON file."""
        try:
            metrics = self.get_metrics(hours=hours)
            if not metrics:
                return False

            with open(output_path, 'w') as jsonfile:
                json.dump(metrics, jsonfile, indent=2)

            logger.info(f"Exported {len(metrics)} records to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return False

    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get statistical summary of metrics."""
        try:
            if self.encrypted:
                metrics = self.get_metrics(hours=hours)
                if not metrics:
                    return {}

                count = len(metrics)
                cpu_vals = [m.get('cpu_usage', 0) or 0 for m in metrics]
                gpu_vals = [m.get('gpu_usage', 0) or 0 for m in metrics]
                mem_vals = [m.get('memory_usage', 0) or 0 for m in metrics]
                temp_vals = [m.get('temperature', 0) or 0 for m in metrics]

                return {
                    'count': count,
                    'avg_cpu': sum(cpu_vals) / count if count else 0,
                    'max_cpu': max(cpu_vals) if cpu_vals else 0,
                    'avg_gpu': sum(gpu_vals) / count if count else 0,
                    'max_gpu': max(gpu_vals) if gpu_vals else 0,
                    'avg_memory': sum(mem_vals) / count if count else 0,
                    'max_memory': max(mem_vals) if mem_vals else 0,
                    'avg_temp': sum(temp_vals) / count if count else 0,
                    'max_temp': max(temp_vals) if temp_vals else 0,
                }
            else:
                cursor = self.conn.cursor()
                cutoff_time = (datetime.now() - timedelta(hours=hours)).timestamp()

                cursor.execute('''
                    SELECT
                        COUNT(*) as count,
                        AVG(cpu_usage) as avg_cpu,
                        MAX(cpu_usage) as max_cpu,
                        AVG(gpu_usage) as avg_gpu,
                        MAX(gpu_usage) as max_gpu,
                        AVG(memory_usage) as avg_memory,
                        MAX(memory_usage) as max_memory,
                        AVG(temperature) as avg_temp,
                        MAX(temperature) as max_temp
                    FROM metrics
                    WHERE timestamp >= ?
                ''', (cutoff_time,))

                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

# Singleton instance
_db_instance = None
_db_lock = threading.Lock()


def get_database() -> MetricsDatabase:
    """Get the singleton database instance (thread-safe)."""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = MetricsDatabase()
    return _db_instance
