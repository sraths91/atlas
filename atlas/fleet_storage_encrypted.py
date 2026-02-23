"""
Encrypted Fleet Storage - SQLite storage with encryption support
"""
import json
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet


class EncryptedFleetDataStore:
    """
    Encrypted persistent data store for fleet metrics using SQLite with field-level encryption.
    
    This implementation encrypts sensitive data fields (machine info, metrics, command params)
    while keeping metadata (IDs, timestamps, status) in plain text for querying.
    
    Tables:
      - machines(machine_id TEXT PRIMARY KEY,
                 info_json_encrypted TEXT,
                 first_seen TEXT,
                 last_seen TEXT,
                 status TEXT,
                 latest_metrics_json_encrypted TEXT)
      - metrics_history(id INTEGER PRIMARY KEY AUTOINCREMENT,
                        machine_id TEXT,
                        timestamp TEXT,
                        metrics_json_encrypted TEXT)
      - commands(id TEXT PRIMARY KEY,
                 machine_id TEXT,
                 action TEXT,
                 params_json_encrypted TEXT,
                 status TEXT,
                 created_at TEXT,
                 executed_at TEXT,
                 result_json_encrypted TEXT)
    """

    def __init__(self, db_path: str, encryption_key: str, history_size: int = 1000, 
                 history_retention_days: Optional[int] = None):
        """
        Initialize encrypted data store
        
        Args:
            db_path: Path to SQLite database file
            encryption_key: Base64-encoded Fernet encryption key
            history_size: Maximum number of history records per machine
            history_retention_days: Optional time-based retention (days)
        """
        self.db_path = str(Path(db_path).expanduser())
        self.history_size = history_size
        self.history_retention_days = history_retention_days
        self.lock = threading.Lock()
        
        # Initialize encryption
        self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        
        self._init_db()

    def _get_conn(self):
        """Get a database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            
            # Machines table with encrypted fields
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS machines (
                    machine_id TEXT PRIMARY KEY,
                    info_json_encrypted TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    status TEXT,
                    latest_metrics_json_encrypted TEXT
                )
                """
            )
            
            # Metrics history with encrypted data
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT,
                    timestamp TEXT,
                    metrics_json_encrypted TEXT
                )
                """
            )
            
            # Commands with encrypted params and results
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS commands (
                    id TEXT PRIMARY KEY,
                    machine_id TEXT,
                    action TEXT,
                    params_json_encrypted TEXT,
                    status TEXT,
                    created_at TEXT,
                    executed_at TEXT,
                    result_json_encrypted TEXT
                )
                """
            )
            
            # Widget logs table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS widget_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT,
                    timestamp TEXT,
                    log_level TEXT,
                    widget_type TEXT,
                    message_encrypted TEXT,
                    data_encrypted TEXT
                )
                """
            )
            
            # Create index for faster log queries and cleanup
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_widget_logs_timestamp 
                ON widget_logs(timestamp)
                """
            )
            
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_widget_logs_machine 
                ON widget_logs(machine_id, timestamp)
                """
            )
            
            # Agent DB keys table (stores agent-side Fernet keys encrypted with fleet key)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_db_keys (
                    machine_id TEXT PRIMARY KEY,
                    key_encrypted TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            # Export logs table (permanent — never auto-cleaned)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS export_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT,
                    timestamp TEXT,
                    local_user TEXT,
                    export_type TEXT,
                    export_format TEXT,
                    encrypted INTEGER DEFAULT 0,
                    encryption_mode TEXT,
                    filename TEXT,
                    data_encrypted TEXT
                )
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_export_logs_timestamp
                ON export_logs(timestamp)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_export_logs_machine
                ON export_logs(machine_id, timestamp)
                """
            )

            conn.commit()
        finally:
            conn.close()

    def _encrypt(self, data: str) -> str:
        """Encrypt a string"""
        return self.fernet.encrypt(data.encode()).decode('utf-8')
    
    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string"""
        if not encrypted_data:
            return ""
        return self.fernet.decrypt(encrypted_data.encode()).decode('utf-8')

    # Public API mirrors FleetDataStore
    def update_machine(self, machine_id: str, machine_info: Dict[str, Any], metrics: Dict[str, Any]):
        """Update machine data and metrics, storing encrypted to SQLite."""
        now = datetime.now().isoformat()
        
        # Encrypt sensitive data
        info_encrypted = self._encrypt(json.dumps(machine_info))
        metrics_encrypted = self._encrypt(json.dumps(metrics))
        
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                
                # Check if machine exists
                cur.execute("SELECT machine_id, first_seen FROM machines WHERE machine_id = ?", (machine_id,))
                row = cur.fetchone()
                
                if row:
                    # Update existing
                    first_seen = row['first_seen']
                    cur.execute(
                        """
                        UPDATE machines
                        SET info_json_encrypted = ?, last_seen = ?, status = ?, latest_metrics_json_encrypted = ?
                        WHERE machine_id = ?
                        """,
                        (info_encrypted, now, 'online', metrics_encrypted, machine_id)
                    )
                else:
                    # Insert new
                    first_seen = now
                    cur.execute(
                        """
                        INSERT INTO machines(machine_id, info_json_encrypted, first_seen, last_seen, status, latest_metrics_json_encrypted)
                        VALUES(?, ?, ?, ?, ?, ?)
                        """,
                        (machine_id, info_encrypted, first_seen, now, 'online', metrics_encrypted)
                    )
                
                # Insert into history
                cur.execute(
                    """
                    INSERT INTO metrics_history(machine_id, timestamp, metrics_json_encrypted)
                    VALUES(?, ?, ?)
                    """,
                    (machine_id, now, metrics_encrypted)
                )
                
                # Trim history by count
                cur.execute(
                    """
                    DELETE FROM metrics_history
                    WHERE machine_id = ? AND id NOT IN (
                        SELECT id FROM metrics_history
                        WHERE machine_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    )
                    """,
                    (machine_id, machine_id, self.history_size)
                )
                
                # Trim history by time if configured
                if self.history_retention_days:
                    cutoff = (datetime.now() - timedelta(days=self.history_retention_days)).isoformat()
                    cur.execute(
                        """
                        DELETE FROM metrics_history
                        WHERE machine_id = ? AND timestamp < ?
                        """,
                        (machine_id, cutoff)
                    )
                
                conn.commit()
            finally:
                conn.close()

    def get_all_machines(self) -> List[Dict[str, Any]]:
        """Get all machines with decrypted data"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM machines")
                rows = cur.fetchall()
                return [self._row_to_machine(row) for row in rows]
            finally:
                conn.close()

    def get_machine(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Get specific machine with decrypted data"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM machines WHERE machine_id = ?", (machine_id,))
                row = cur.fetchone()
                return self._row_to_machine(row) if row else None
            finally:
                conn.close()

    def get_machine_history(self, machine_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get machine metrics history with decrypted data"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT timestamp, metrics_json_encrypted
                    FROM metrics_history
                    WHERE machine_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (machine_id, limit)
                )
                rows = cur.fetchall()
                history = []
                for row in rows:
                    metrics = json.loads(self._decrypt(row['metrics_json_encrypted']))
                    history.append({
                        'timestamp': row['timestamp'],
                        'metrics': metrics
                    })
                return history
            finally:
                conn.close()

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Get fleet summary (uses plain text fields, no decryption needed for counts)"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                
                # Get all machines (without re-acquiring lock)
                cur.execute("SELECT * FROM machines")
                rows = cur.fetchall()
                machines = [self._row_to_machine(row) for row in rows]
                
                total = len(machines)
                online = sum(1 for m in machines if m['status'] == 'online')
                warning = sum(1 for m in machines if m['status'] == 'warning')
                offline = sum(1 for m in machines if m['status'] == 'offline')
                
                # Calculate averages
                avg_cpu = sum(m.get('latest_metrics', {}).get('cpu', {}).get('percent', 0) for m in machines) / total if total > 0 else 0
                avg_memory = sum(m.get('latest_metrics', {}).get('memory', {}).get('percent', 0) for m in machines) / total if total > 0 else 0
                avg_disk = sum(m.get('latest_metrics', {}).get('disk', {}).get('percent', 0) for m in machines) / total if total > 0 else 0
                
                return {
                    'total_machines': total,
                    'online': online,
                    'warning': warning,
                    'offline': offline,
                    'avg_cpu': round(avg_cpu, 1),
                    'avg_memory': round(avg_memory, 1),
                    'avg_disk': round(avg_disk, 1),
                    'alerts': [],
                    'timestamp': datetime.now().isoformat()
                }
            finally:
                conn.close()

    def storage_info(self) -> Dict[str, Any]:
        """Get storage backend information"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) as count FROM machines")
                machine_count = cur.fetchone()['count']
                cur.execute("SELECT COUNT(*) as count FROM metrics_history")
                history_count = cur.fetchone()['count']
                
                return {
                    "backend": "sqlite_encrypted",
                    "encryption": "Fernet (AES-128)",
                    "db_path": self.db_path,
                    "machines": machine_count,
                    "history_rows": history_count,
                    "history_size_per_machine": self.history_size,
                    "history_retention_days": self.history_retention_days,
                }
            finally:
                conn.close()

    # Command management methods (with encryption)
    def create_command(self, machine_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Create a new command for a machine with encrypted params"""
        import uuid
        command_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        params_encrypted = self._encrypt(json.dumps(params or {}))
        
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO commands(id, machine_id, action, params_json_encrypted, status, created_at, executed_at, result_json_encrypted)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (command_id, machine_id, action, params_encrypted, 'pending', now, None, None)
                )
                conn.commit()
            finally:
                conn.close()
        
        return command_id
    
    def get_pending_commands(self, machine_id: str) -> List[Dict[str, Any]]:
        """Get all pending commands for a machine with decrypted params"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, action, params_json_encrypted, created_at
                    FROM commands
                    WHERE machine_id = ? AND status = 'pending'
                    ORDER BY created_at ASC
                    """,
                    (machine_id,)
                )
                rows = cur.fetchall()
                commands = []
                for row in rows:
                    params = json.loads(self._decrypt(row['params_json_encrypted']))
                    commands.append({
                        'id': row['id'],
                        'action': row['action'],
                        'params': params,
                        'created_at': row['created_at']
                    })
                return commands
            finally:
                conn.close()
    
    def acknowledge_command(self, command_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Mark a command as executed with encrypted result"""
        now = datetime.now().isoformat()
        result_encrypted = self._encrypt(json.dumps(result or {}))
        
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE commands
                    SET status = ?, executed_at = ?, result_json_encrypted = ?
                    WHERE id = ?
                    """,
                    (status, now, result_encrypted, command_id)
                )
                conn.commit()
            finally:
                conn.close()
    
    def get_recent_commands(self, machine_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commands for a machine with decrypted data"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, action, params_json_encrypted, status, created_at, executed_at, result_json_encrypted
                    FROM commands
                    WHERE machine_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (machine_id, limit)
                )
                rows = cur.fetchall()
                commands = []
                for row in rows:
                    params = json.loads(self._decrypt(row['params_json_encrypted']))
                    result = json.loads(self._decrypt(row['result_json_encrypted'])) if row['result_json_encrypted'] else {}
                    commands.append({
                        'id': row['id'],
                        'action': row['action'],
                        'params': params,
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'executed_at': row['executed_at'],
                        'result': result
                    })
                return commands
            finally:
                conn.close()

    def store_widget_logs(self, machine_id: str, logs: List[Dict[str, Any]]):
        """Store widget logs from a machine"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                for log in logs:
                    # Encrypt sensitive data
                    message_encrypted = self._encrypt(log.get('message', ''))
                    data_encrypted = self._encrypt(json.dumps(log.get('data', {})))
                    
                    cur.execute(
                        """
                        INSERT INTO widget_logs 
                        (machine_id, timestamp, log_level, widget_type, message_encrypted, data_encrypted)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            machine_id,
                            log.get('timestamp', datetime.now().isoformat()),
                            log.get('level', 'INFO'),
                            log.get('widget_type', 'unknown'),
                            message_encrypted,
                            data_encrypted
                        )
                    )
                conn.commit()
            finally:
                conn.close()
    
    def get_widget_logs(self, machine_id: Optional[str] = None, limit: int = 100, 
                        widget_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get widget logs with optional filtering"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                
                query = """
                    SELECT id, machine_id, timestamp, log_level, widget_type, 
                           message_encrypted, data_encrypted
                    FROM widget_logs
                    WHERE 1=1
                """
                params = []
                
                if machine_id:
                    query += " AND machine_id = ?"
                    params.append(machine_id)
                
                if widget_type:
                    query += " AND widget_type = ?"
                    params.append(widget_type)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                logs = []
                for row in rows:
                    message = self._decrypt(row['message_encrypted'])
                    data = json.loads(self._decrypt(row['data_encrypted'])) if row['data_encrypted'] else {}
                    logs.append({
                        'id': row['id'],
                        'machine_id': row['machine_id'],
                        'timestamp': row['timestamp'],
                        'level': row['log_level'],
                        'widget_type': row['widget_type'],
                        'message': message,
                        'data': data
                    })
                return logs
            finally:
                conn.close()
    
    def cleanup_old_widget_logs(self, days: int = 7):
        """Delete widget logs older than specified days"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM widget_logs WHERE timestamp < ?",
                    (cutoff_date,)
                )
                deleted_count = cur.rowcount
                conn.commit()
                return deleted_count
            finally:
                conn.close()

    # Export log management (permanent storage — never auto-cleaned)
    def store_export_log(self, machine_id: str, log_data: Dict[str, Any]):
        """Store a single export log entry permanently.

        Args:
            machine_id: Machine that performed the export
            log_data: Dict with keys: local_user, export_type, format, encrypted, mode, filename
        """
        now = log_data.get('timestamp', datetime.now().isoformat())
        extra_encrypted = self._encrypt(json.dumps(log_data))

        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO export_logs
                    (machine_id, timestamp, local_user, export_type, export_format,
                     encrypted, encryption_mode, filename, data_encrypted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        machine_id,
                        now,
                        log_data.get('local_user', 'unknown'),
                        log_data.get('export_type', 'unknown'),
                        log_data.get('format', 'unknown'),
                        1 if log_data.get('encrypted') else 0,
                        log_data.get('mode', 'none'),
                        log_data.get('filename', ''),
                        extra_encrypted,
                    )
                )
                conn.commit()
            finally:
                conn.close()

    def get_export_logs(self, machine_id: Optional[str] = None,
                        limit: int = 200) -> List[Dict[str, Any]]:
        """Get export logs with optional machine filtering.

        Args:
            machine_id: Optional machine ID filter
            limit: Maximum number of records to return

        Returns:
            List of export log dicts, newest first
        """
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()

                query = """
                    SELECT id, machine_id, timestamp, local_user, export_type,
                           export_format, encrypted, encryption_mode, filename,
                           data_encrypted
                    FROM export_logs
                    WHERE 1=1
                """
                params: list = []

                if machine_id:
                    query += " AND machine_id = ?"
                    params.append(machine_id)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cur.execute(query, params)
                rows = cur.fetchall()

                logs = []
                for row in rows:
                    data = json.loads(self._decrypt(row['data_encrypted'])) if row['data_encrypted'] else {}
                    logs.append({
                        'id': row['id'],
                        'machine_id': row['machine_id'],
                        'timestamp': row['timestamp'],
                        'local_user': row['local_user'],
                        'export_type': row['export_type'],
                        'format': row['export_format'],
                        'encrypted': bool(row['encrypted']),
                        'mode': row['encryption_mode'],
                        'filename': row['filename'],
                        'data': data,
                    })
                return logs
            finally:
                conn.close()

    # Agent DB key management
    def store_agent_db_key(self, machine_id: str, key_b64: str):
        """Store agent's Fernet key, encrypted with fleet's own key."""
        now = datetime.now().isoformat()
        key_encrypted = self._encrypt(key_b64)
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO agent_db_keys (machine_id, key_encrypted, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(machine_id) DO UPDATE SET
                        key_encrypted = excluded.key_encrypted,
                        updated_at = excluded.updated_at
                """, (machine_id, key_encrypted, now))
                conn.commit()
            finally:
                conn.close()

    def get_agent_db_key(self, machine_id: str) -> Optional[str]:
        """Retrieve agent's Fernet key (decrypted from fleet storage)."""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT key_encrypted FROM agent_db_keys WHERE machine_id = ?",
                    (machine_id,)
                )
                row = cur.fetchone()
                if row and row['key_encrypted']:
                    return self._decrypt(row['key_encrypted'])
                return None
            finally:
                conn.close()

    def decrypt_agent_data(self, machine_id: str, encrypted_data: str) -> Optional[str]:
        """Decrypt Fernet ciphertext from an agent's local DB."""
        key_b64 = self.get_agent_db_key(machine_id)
        if not key_b64:
            return None
        agent_fernet = Fernet(key_b64.encode('ascii'))
        return agent_fernet.decrypt(encrypted_data.encode()).decode('utf-8')

    # Helper
    def _row_to_machine(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to machine dict with decryption"""
        info = json.loads(self._decrypt(row["info_json_encrypted"])) if row["info_json_encrypted"] else {}
        latest_metrics = json.loads(self._decrypt(row["latest_metrics_json_encrypted"])) if row["latest_metrics_json_encrypted"] else {}
        return {
            "machine_id": row["machine_id"],
            "info": info,
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "status": row["status"] or "offline",
            "latest_metrics": latest_metrics
        }
