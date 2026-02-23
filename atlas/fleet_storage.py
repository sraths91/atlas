"""Persistent storage for fleet metrics using SQLite.

This module provides a PersistentFleetDataStore that mirrors the in-memory
FleetDataStore API but stores data on disk so metrics and history survive
server restarts.
"""

import json
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


class PersistentFleetDataStore:
    """SQLite-backed data store for fleet metrics.

    Tables:
      - machines(machine_id TEXT PRIMARY KEY,
                 info_json TEXT,
                 first_seen TEXT,
                 last_seen TEXT,
                 status TEXT,
                 latest_metrics_json TEXT)
      - metrics_history(id INTEGER PRIMARY KEY AUTOINCREMENT,
                        machine_id TEXT,
                        timestamp TEXT,
                        metrics_json TEXT)
      - commands(id TEXT PRIMARY KEY,
                 machine_id TEXT,
                 action TEXT,
                 params_json TEXT,
                 status TEXT,
                 created_at TEXT,
                 executed_at TEXT,
                 result_json TEXT)
    """

    def __init__(self, db_path: str, history_size: int = 1000, history_retention_days: Optional[int] = None):
        db_path_obj = Path(db_path).expanduser()
        self.db_path = str(db_path_obj)
        self.history_size = history_size
        self.history_retention_days = history_retention_days
        self.lock = threading.Lock()
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS machines (
                    machine_id TEXT PRIMARY KEY,
                    info_json TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    status TEXT,
                    latest_metrics_json TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT,
                    timestamp TEXT,
                    metrics_json TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS commands (
                    id TEXT PRIMARY KEY,
                    machine_id TEXT,
                    action TEXT,
                    params_json TEXT,
                    status TEXT,
                    created_at TEXT,
                    executed_at TEXT,
                    result_json TEXT
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
                    message TEXT,
                    data_json TEXT
                )
                """
            )
            
            # Create indexes for faster log queries and cleanup
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

            # Enhanced metrics tables (Phase 1 & 2)

            # VPN Status table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS vpn_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    connected BOOLEAN,
                    vpn_client TEXT,
                    interface_count INTEGER,
                    interfaces TEXT,
                    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
                )
                """
            )

            # SaaS Endpoint Availability table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS saas_availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    category TEXT,
                    availability_percent REAL,
                    avg_latency_ms REAL,
                    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
                )
                """
            )

            # Network Quality table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS network_quality (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tcp_retransmit_rate REAL,
                    dns_avg_latency_ms REAL,
                    dns_availability REAL,
                    tls_avg_latency_ms REAL,
                    http_avg_latency_ms REAL,
                    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
                )
                """
            )

            # WiFi Roaming table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS wifi_roaming (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    roaming_events INTEGER,
                    sticky_client_incidents INTEGER,
                    avg_roaming_latency_ms REAL,
                    current_channel INTEGER,
                    channel_utilization REAL,
                    interfering_aps INTEGER,
                    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
                )
                """
            )

            # Enhanced Security Status table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS security_status_enhanced (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    security_score INTEGER,
                    firewall_enabled BOOLEAN,
                    filevault_enabled BOOLEAN,
                    gatekeeper_enabled BOOLEAN,
                    sip_enabled BOOLEAN,
                    screen_lock_enabled BOOLEAN,
                    auto_updates_enabled BOOLEAN,
                    pending_updates INTEGER,
                    critical_events_24h INTEGER,
                    high_events_24h INTEGER,
                    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
                )
                """
            )

            # Create indexes for enhanced metrics tables
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vpn_machine_time
                ON vpn_status(machine_id, timestamp)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_saas_machine_time
                ON saas_availability(machine_id, timestamp)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_netqual_machine_time
                ON network_quality(machine_id, timestamp)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_wifi_machine_time
                ON wifi_roaming(machine_id, timestamp)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_security_enh_machine_time
                ON security_status_enhanced(machine_id, timestamp)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_security_enh_score
                ON security_status_enhanced(security_score)
                """
            )

            conn.commit()
        finally:
            conn.close()

    # Public API mirrors FleetDataStore
    def update_machine(self, machine_id: str, machine_info: Dict[str, Any], metrics: Dict[str, Any]):
        """Update machine data and metrics, storing to SQLite.
        
        Includes duplicate prevention: if a device with the same serial number
        already exists under a different machine_id, the old entry is removed
        and consolidated into the new one.
        """
        now = datetime.now().isoformat()
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                
                # Check for duplicate serial numbers (duplicate prevention)
                serial_number = (machine_info or {}).get('serial_number')
                if serial_number:
                    # Find any existing machine with the same serial number but different machine_id
                    cur.execute(
                        """
                        SELECT machine_id, info_json, first_seen FROM machines 
                        WHERE machine_id != ? AND info_json LIKE ?
                        """,
                        (machine_id, f'%"serial_number": "{serial_number}"%')
                    )
                    duplicates = cur.fetchall()
                    
                    earliest_first_seen = now
                    for dup in duplicates:
                        dup_machine_id = dup["machine_id"]
                        dup_first_seen = dup["first_seen"]
                        
                        # Keep the earliest first_seen date
                        if dup_first_seen and dup_first_seen < earliest_first_seen:
                            earliest_first_seen = dup_first_seen
                        
                        logger.info(f"Removing duplicate machine '{dup_machine_id}' with same serial number '{serial_number}' - consolidating into '{machine_id}'")
                        
                        # Delete the duplicate machine entry
                        cur.execute("DELETE FROM machines WHERE machine_id = ?", (dup_machine_id,))
                        # Optionally migrate history to new machine_id
                        cur.execute(
                            "UPDATE metrics_history SET machine_id = ? WHERE machine_id = ?",
                            (machine_id, dup_machine_id)
                        )
                        # Update widget logs too
                        cur.execute(
                            "UPDATE widget_logs SET machine_id = ? WHERE machine_id = ?",
                            (machine_id, dup_machine_id)
                        )

                # Load existing info if present
                cur.execute("SELECT info_json, first_seen FROM machines WHERE machine_id = ?", (machine_id,))
                row = cur.fetchone()

                # Track if we found duplicates to preserve earliest first_seen
                found_duplicates = serial_number and 'earliest_first_seen' in locals() and earliest_first_seen != now

                # Track if this is a new agent
                is_new_agent = False

                if row is None:
                    # New machine
                    is_new_agent = True
                    info = machine_info or {}
                    # Use earliest_first_seen if we consolidated duplicates
                    first_seen = earliest_first_seen if found_duplicates else now
                else:
                    # Existing machine: merge info
                    existing_info = json.loads(row["info_json"]) if row["info_json"] else {}
                    info = existing_info
                    if machine_info:
                        info.update(machine_info)
                    first_seen = row["first_seen"] or now

                cur.execute(
                    """
                    INSERT INTO machines(machine_id, info_json, first_seen, last_seen, status, latest_metrics_json)
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(machine_id) DO UPDATE SET
                        info_json=excluded.info_json,
                        last_seen=excluded.last_seen,
                        status=excluded.status,
                        latest_metrics_json=excluded.latest_metrics_json
                    """,
                    (
                        machine_id,
                        json.dumps(info),
                        first_seen,
                        now,
                        "online",
                        json.dumps(metrics or {}),
                    ),
                )

                # Insert history row
                cur.execute(
                    """
                    INSERT INTO metrics_history(machine_id, timestamp, metrics_json)
                    VALUES(?, ?, ?)
                    """,
                    (machine_id, now, json.dumps(metrics or {})),
                )

                # Trim history per machine to history_size (count-based)
                if self.history_size and self.history_size > 0:
                    cur.execute(
                        """
                        DELETE FROM metrics_history
                        WHERE machine_id = ? AND id NOT IN (
                            SELECT id FROM metrics_history
                            WHERE machine_id = ?
                            ORDER BY id DESC
                            LIMIT ?
                        )
                        """,
                        (machine_id, machine_id, self.history_size),
                    )

                # Timestamp-based retention: delete rows older than history_retention_days
                if self.history_retention_days and self.history_retention_days > 0:
                    cutoff = (datetime.now() - timedelta(days=self.history_retention_days)).isoformat()
                    cur.execute(
                        """
                        DELETE FROM metrics_history
                        WHERE timestamp < ?
                        """,
                        (cutoff,),
                    )

                conn.commit()

                # Log new agent registration (inside the lock but after commit)
                if is_new_agent:
                    serial_number = info.get('serial_number', machine_id)
                    computer_name = info.get('computer_name', info.get('hostname', machine_id))
                    local_ip = info.get('local_ip', 'unknown')
                    dashboard_url = f"/machine/{serial_number}/dashboard"

                    logger.info("═══════════════════════════════════════════════════════════════")
                    logger.info(f"🆕 NEW AGENT REGISTERED: {computer_name}")
                    logger.info(f"   Serial Number: {serial_number}")
                    logger.info(f"   Machine ID:    {machine_id}")
                    logger.info(f"   Local IP:      {local_ip}")
                    logger.info(f"   Dashboard URL: {dashboard_url}")
                    logger.info(f"   First Seen:    {first_seen}")
                    logger.info("═══════════════════════════════════════════════════════════════")

            except Exception as e:
                logger.error("Error updating machine in persistent store: %s", e, exc_info=True)
            finally:
                conn.close()

    def get_machine(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Get machine data, computing status based on last_seen."""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM machines WHERE machine_id = ?", (machine_id,))
                row = cur.fetchone()
                if not row:
                    return None
                machine = self._row_to_machine(row)

                # Recompute status from last_seen (same logic as get_all_machines)
                try:
                    last_seen = datetime.fromisoformat(machine["last_seen"]) if machine.get("last_seen") else None
                except Exception:
                    last_seen = None
                if last_seen is not None:
                    delta = (datetime.now() - last_seen).total_seconds()
                    if delta > 60:
                        machine["status"] = "offline"
                    elif delta > 30:
                        machine["status"] = "warning"
                    else:
                        machine["status"] = "online"

                return machine
            finally:
                conn.close()

    def get_all_machines(self) -> List[Dict[str, Any]]:
        """Get all machines, computing status based on last_seen."""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM machines")
                rows = cur.fetchall()
                machines: List[Dict[str, Any]] = []
                now = datetime.now()
                for row in rows:
                    machine = self._row_to_machine(row)
                    # Recompute status from last_seen
                    try:
                        last_seen = datetime.fromisoformat(machine["last_seen"]) if machine.get("last_seen") else None
                    except Exception:
                        last_seen = None
                    if last_seen is not None:
                        delta = (now - last_seen).total_seconds()
                        if delta > 60:
                            machine["status"] = "offline"
                        elif delta > 30:
                            machine["status"] = "warning"
                        else:
                            machine["status"] = "online"
                    machines.append(machine)
                return machines
            finally:
                conn.close()

    def get_machine_history(self, machine_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get metrics history for a machine."""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT timestamp, metrics_json
                    FROM metrics_history
                    WHERE machine_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (machine_id, limit),
                )
                rows = cur.fetchall()
                history: List[Dict[str, Any]] = []
                for row in reversed(rows):  # reverse to oldest-first
                    history.append(
                        {
                            "timestamp": row["timestamp"],
                            "metrics": json.loads(row["metrics_json"]) if row["metrics_json"] else {},
                        }
                    )
                return history
            finally:
                conn.close()

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Get fleet-wide summary (mirrors in-memory implementation)."""
        machines = self.get_all_machines()
        total = len(machines)
        online = sum(1 for m in machines if m.get("status") == "online")
        warning = sum(1 for m in machines if m.get("status") == "warning")
        offline = sum(1 for m in machines if m.get("status") == "offline")

        if online > 0:
            avg_cpu = (
                sum(m.get("latest_metrics", {}).get("cpu", {}).get("percent", 0) for m in machines if m.get("status") == "online")
                / online
            )
            avg_memory = (
                sum(m.get("latest_metrics", {}).get("memory", {}).get("percent", 0) for m in machines if m.get("status") == "online")
                / online
            )
            avg_disk = (
                sum(m.get("latest_metrics", {}).get("disk", {}).get("percent", 0) for m in machines if m.get("status") == "online")
                / online
            )
        else:
            avg_cpu = avg_memory = avg_disk = 0

        alerts: List[Dict[str, Any]] = []
        for machine in machines:
            if machine.get("status") != "online":
                continue
            metrics = machine.get("latest_metrics", {})
            cpu = metrics.get("cpu", {}).get("percent", 0)
            memory = metrics.get("memory", {}).get("percent", 0)
            disk = metrics.get("disk", {}).get("percent", 0)

            if cpu > 90:
                alerts.append(
                    {
                        "machine_id": machine["machine_id"],
                        "type": "cpu",
                        "severity": "critical",
                        "message": f"CPU usage at {cpu:.1f}%",
                    }
                )
            if memory > 90:
                alerts.append(
                    {
                        "machine_id": machine["machine_id"],
                        "type": "memory",
                        "severity": "critical",
                        "message": f"Memory usage at {memory:.1f}%",
                    }
                )
            if disk > 90:
                alerts.append(
                    {
                        "machine_id": machine["machine_id"],
                        "type": "disk",
                        "severity": "critical",
                        "message": f"Disk usage at {disk:.1f}%",
                    }
                )

        return {
            "total_machines": total,
            "online": online,
            "warning": warning,
            "offline": offline,
            "avg_cpu": avg_cpu,
            "avg_memory": avg_memory,
            "avg_disk": avg_disk,
            "alerts": alerts,
            "timestamp": datetime.now().isoformat(),
        }

    def get_registered_agents(self) -> List[Dict[str, Any]]:
        """Get list of all registered agents with their dashboard URLs.

        Returns:
            List of dicts containing:
            - machine_id: Machine identifier
            - serial_number: Hardware serial number
            - computer_name: Friendly computer name
            - local_ip: Last known IP address
            - dashboard_url: URL to access the dashboard
            - first_seen: When agent first connected
            - last_seen: Last report time
            - status: Current status (online/warning/offline)
        """
        machines = self.get_all_machines()
        agents = []

        for machine in machines:
            info = machine.get('info', {})
            serial_number = info.get('serial_number', machine['machine_id'])

            agents.append({
                'machine_id': machine['machine_id'],
                'serial_number': serial_number,
                'computer_name': info.get('computer_name', info.get('hostname', machine['machine_id'])),
                'local_ip': info.get('local_ip', 'unknown'),
                'dashboard_url': f"/machine/{serial_number}/dashboard",
                'first_seen': machine.get('first_seen'),
                'last_seen': machine.get('last_seen'),
                'status': machine.get('status', 'unknown')
            })

        return agents

    def storage_info(self) -> Dict[str, Any]:
        """Return high-level information about the persistent storage.

        Includes counts and configuration details useful for inspection.
        """
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM machines")
                machine_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM metrics_history")
                history_count = cur.fetchone()[0]
            finally:
                conn.close()

        return {
            "backend": "sqlite",
            "db_path": self.db_path,
            "machines": machine_count,
            "history_rows": history_count,
            "history_size_per_machine": self.history_size,
            "history_retention_days": self.history_retention_days,
        }

    # Command management methods
    def create_command(self, machine_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Create a new command for a machine. Returns command ID."""
        import uuid
        command_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO commands(id, machine_id, action, params_json, status, created_at, executed_at, result_json)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (command_id, machine_id, action, json.dumps(params or {}), 'pending', now, None, None)
                )
                conn.commit()
            finally:
                conn.close()
        
        return command_id
    
    def get_pending_commands(self, machine_id: str) -> List[Dict[str, Any]]:
        """Get all pending commands for a machine."""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, action, params_json, created_at
                    FROM commands
                    WHERE machine_id = ? AND status = 'pending'
                    ORDER BY created_at ASC
                    """,
                    (machine_id,)
                )
                rows = cur.fetchall()
                commands = []
                for row in rows:
                    commands.append({
                        'id': row['id'],
                        'action': row['action'],
                        'params': json.loads(row['params_json']) if row['params_json'] else {},
                        'created_at': row['created_at']
                    })
                return commands
            finally:
                conn.close()
    
    def acknowledge_command(self, command_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Mark a command as executed with result."""
        now = datetime.now().isoformat()
        
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE commands
                    SET status = ?, executed_at = ?, result_json = ?
                    WHERE id = ?
                    """,
                    (status, now, json.dumps(result or {}), command_id)
                )
                conn.commit()
            finally:
                conn.close()
    
    def get_recent_commands(self, machine_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commands for a machine (for UI display)."""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, action, params_json, status, created_at, executed_at, result_json
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
                    commands.append({
                        'id': row['id'],
                        'action': row['action'],
                        'params': json.loads(row['params_json']) if row['params_json'] else {},
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'executed_at': row['executed_at'],
                        'result': json.loads(row['result_json']) if row['result_json'] else {}
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
                    cur.execute(
                        """
                        INSERT INTO widget_logs 
                        (machine_id, timestamp, log_level, widget_type, message, data_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            machine_id,
                            log.get('timestamp', datetime.now().isoformat()),
                            log.get('level', 'INFO'),
                            log.get('widget_type', 'unknown'),
                            log.get('message', ''),
                            json.dumps(log.get('data', {}))
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
                    SELECT id, machine_id, timestamp, log_level, widget_type, message, data_json
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
                    logs.append({
                        'id': row['id'],
                        'machine_id': row['machine_id'],
                        'timestamp': row['timestamp'],
                        'level': row['log_level'],
                        'widget_type': row['widget_type'],
                        'message': row['message'],
                        'data': json.loads(row['data_json']) if row['data_json'] else {}
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

    # Enhanced metrics storage (Phase 1 & 2)
    def store_enhanced_metrics(self, machine_id: str, metrics: Dict[str, Any]):
        """Store enhanced monitoring metrics (VPN, SaaS, network quality, WiFi, security)"""
        if not metrics:
            return

        timestamp = datetime.now().isoformat()

        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()

                # Store VPN metrics
                vpn = metrics.get('vpn')
                if vpn:
                    cur.execute(
                        """
                        INSERT INTO vpn_status
                        (machine_id, timestamp, connected, vpn_client, interface_count, interfaces)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (machine_id, timestamp, vpn.get('connected'), vpn.get('vpn_client'),
                         vpn.get('interface_count'), json.dumps(vpn.get('interfaces', [])))
                    )

                # Store SaaS endpoint metrics (one row per category)
                saas = metrics.get('saas_endpoints')
                if saas:
                    for category, stats in saas.items():
                        cur.execute(
                            """
                            INSERT INTO saas_availability
                            (machine_id, timestamp, category, availability_percent, avg_latency_ms)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (machine_id, timestamp, category,
                             stats.get('availability'), stats.get('avg_latency'))
                        )

                # Store network quality metrics
                netqual = metrics.get('network_quality')
                if netqual:
                    cur.execute(
                        """
                        INSERT INTO network_quality
                        (machine_id, timestamp, tcp_retransmit_rate, dns_avg_latency_ms,
                         dns_availability, tls_avg_latency_ms, http_avg_latency_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (machine_id, timestamp,
                         netqual.get('tcp_retransmit_rate'),
                         netqual.get('dns_avg_latency'),
                         netqual.get('dns_availability'),
                         netqual.get('tls_avg_latency'),
                         netqual.get('http_avg_latency'))
                    )

                # Store WiFi roaming metrics
                wifi = metrics.get('wifi_roaming')
                if wifi:
                    cur.execute(
                        """
                        INSERT INTO wifi_roaming
                        (machine_id, timestamp, roaming_events, sticky_client_incidents,
                         avg_roaming_latency_ms, current_channel, channel_utilization, interfering_aps)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (machine_id, timestamp,
                         wifi.get('roaming_events'),
                         wifi.get('sticky_client_incidents'),
                         wifi.get('avg_roaming_latency'),
                         wifi.get('current_channel'),
                         wifi.get('channel_utilization'),
                         wifi.get('interfering_aps'))
                    )

                # Store enhanced security metrics
                security = metrics.get('security_enhanced')
                if security:
                    cur.execute(
                        """
                        INSERT INTO security_status_enhanced
                        (machine_id, timestamp, security_score, firewall_enabled, filevault_enabled,
                         gatekeeper_enabled, sip_enabled, screen_lock_enabled, auto_updates_enabled,
                         pending_updates, critical_events_24h, high_events_24h)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (machine_id, timestamp,
                         security.get('security_score'),
                         security.get('firewall_enabled'),
                         security.get('filevault_enabled'),
                         security.get('gatekeeper_enabled'),
                         security.get('sip_enabled'),
                         security.get('screen_lock_enabled'),
                         security.get('auto_updates_enabled'),
                         security.get('pending_updates'),
                         security.get('critical_events_24h'),
                         security.get('high_events_24h'))
                    )

                conn.commit()
            except Exception as e:
                logger.error(f"Error storing enhanced metrics: {e}")
                conn.rollback()
            finally:
                conn.close()

    def get_vpn_status(self, machine_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get VPN connection status history"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                if machine_id:
                    cur.execute(
                        """
                        SELECT * FROM vpn_status
                        WHERE machine_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (machine_id, limit)
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM vpn_status
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (limit,)
                    )

                rows = cur.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def get_saas_availability(self, machine_id: Optional[str] = None,
                             category: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Get SaaS endpoint availability history"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()

                if machine_id and category:
                    cur.execute(
                        """
                        SELECT * FROM saas_availability
                        WHERE machine_id = ? AND category = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (machine_id, category, limit)
                    )
                elif machine_id:
                    cur.execute(
                        """
                        SELECT * FROM saas_availability
                        WHERE machine_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (machine_id, limit)
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM saas_availability
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (limit,)
                    )

                rows = cur.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def get_network_quality(self, machine_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get network quality metrics history"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                if machine_id:
                    cur.execute(
                        """
                        SELECT * FROM network_quality
                        WHERE machine_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (machine_id, limit)
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM network_quality
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (limit,)
                    )

                rows = cur.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def get_security_scores(self, threshold: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get security scores for all machines, optionally filtered by threshold"""
        with self.lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()

                # Get latest security score for each machine
                if threshold is not None:
                    cur.execute(
                        """
                        SELECT s.* FROM security_status_enhanced s
                        INNER JOIN (
                            SELECT machine_id, MAX(timestamp) as max_ts
                            FROM security_status_enhanced
                            GROUP BY machine_id
                        ) latest ON s.machine_id = latest.machine_id AND s.timestamp = latest.max_ts
                        WHERE s.security_score < ?
                        ORDER BY s.security_score ASC
                        """,
                        (threshold,)
                    )
                else:
                    cur.execute(
                        """
                        SELECT s.* FROM security_status_enhanced s
                        INNER JOIN (
                            SELECT machine_id, MAX(timestamp) as max_ts
                            FROM security_status_enhanced
                            GROUP BY machine_id
                        ) latest ON s.machine_id = latest.machine_id AND s.timestamp = latest.max_ts
                        ORDER BY s.security_score ASC
                        """
                    )

                rows = cur.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    # Helpers
    def _row_to_machine(self, row: sqlite3.Row) -> Dict[str, Any]:
        info = json.loads(row["info_json"]) if row["info_json"] else {}
        latest_metrics = json.loads(row["latest_metrics_json"]) if row["latest_metrics_json"] else {}
        return {
            "machine_id": row["machine_id"],
            "info": info,
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "status": row["status"] or "offline",
            "latest_metrics": latest_metrics,
        }
