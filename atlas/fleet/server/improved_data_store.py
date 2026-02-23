"""
Improved Fleet Data Store - Enhanced Thread Safety and Performance

Phase 7: Thread Safety and Concurrency Improvements

This module provides an improved version of FleetDataStore with:
- Per-resource locking (finer granularity)
- Read/write lock differentiation
- No I/O operations while holding locks
- Better scalability for high-load scenarios

Migration: Can be used as drop-in replacement for FleetDataStore
"""
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ReadWriteLock:
    """
    Read-Write Lock implementation for better concurrency.

    Allows:
    - Multiple concurrent readers (no blocking)
    - Single exclusive writer (blocks all readers and writers)
    - Writer priority (pending writers block new readers)
    """

    def __init__(self):
        self._readers = 0
        self._writers = 0
        self._waiting_writers = 0
        self._lock = threading.Lock()
        self._read_ok = threading.Condition(self._lock)
        self._write_ok = threading.Condition(self._lock)

    @contextmanager
    def read_lock(self):
        """Acquire read lock (shared)"""
        self._acquire_read()
        try:
            yield
        finally:
            self._release_read()

    @contextmanager
    def write_lock(self):
        """Acquire write lock (exclusive)"""
        self._acquire_write()
        try:
            yield
        finally:
            self._release_write()

    def _acquire_read(self):
        """Acquire read lock (allows multiple readers)"""
        with self._lock:
            # Wait if there are writers or waiting writers
            while self._writers > 0 or self._waiting_writers > 0:
                self._read_ok.wait()
            self._readers += 1

    def _release_read(self):
        """Release read lock"""
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                # Last reader, notify waiting writers
                self._write_ok.notify()

    def _acquire_write(self):
        """Acquire write lock (exclusive)"""
        with self._lock:
            self._waiting_writers += 1
            # Wait for all readers and writers to finish
            while self._readers > 0 or self._writers > 0:
                self._write_ok.wait()
            self._waiting_writers -= 1
            self._writers += 1

    def _release_write(self):
        """Release write lock"""
        with self._lock:
            self._writers -= 1
            # Notify all waiting readers and one waiting writer
            self._write_ok.notify()
            self._read_ok.notify_all()


class ImprovedFleetDataStore:
    """
    Improved in-memory data store with fine-grained locking.

    Improvements over FleetDataStore:
    1. Per-resource locks (machines, history, commands)
    2. Read/write lock differentiation
    3. No I/O operations while holding locks
    4. Better scalability for concurrent access
    """

    def __init__(self, history_size: int = 1000):
        """Initialize the improved data store

        Args:
            history_size: Maximum number of metric entries to keep per machine
        """
        # Data structures (protected by separate locks)
        self.machines: Dict[str, Dict[str, Any]] = {}
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.command_queues: Dict[str, deque] = defaultdict(deque)

        # Per-resource locks (finer granularity)
        self._machines_lock = ReadWriteLock()
        self._history_lock = ReadWriteLock()
        self._commands_lock = ReadWriteLock()

        self.history_size = history_size

        logger.info(f"ImprovedFleetDataStore initialized (history_size={history_size})")

    def update_machine(self, machine_id: str, machine_info: Dict[str, Any], metrics: Dict[str, Any]):
        """
        Update machine data and metrics.

        Uses fine-grained locking:
        - Machines lock for updating machine record
        - History lock for appending metrics
        - No I/O operations while holding locks

        Args:
            machine_id: Unique machine identifier
            machine_info: Machine information (hostname, OS, etc.)
            metrics: Current metrics (CPU, memory, disk, etc.)
        """
        now = datetime.now()
        timestamp_iso = now.isoformat()

        # Prepare data outside of locks (no expensive operations in critical section)
        new_machine = machine_id not in self.machines

        # Update machine record (write lock)
        with self._machines_lock.write_lock():
            if new_machine:
                self.machines[machine_id] = {
                    'machine_id': machine_id,
                    'info': machine_info.copy() if machine_info else {},
                    'first_seen': timestamp_iso,
                    'last_seen': timestamp_iso,
                    'status': 'online',
                    'latest_metrics': metrics.copy() if metrics else {}
                }
            else:
                self.machines[machine_id]['last_seen'] = timestamp_iso
                self.machines[machine_id]['status'] = 'online'
                self.machines[machine_id]['latest_metrics'] = metrics.copy() if metrics else {}

                # Update info if changed (merge, don't replace)
                if machine_info:
                    self.machines[machine_id]['info'].update(machine_info)

        # Append to history (separate lock, no contention with machine updates)
        with self._history_lock.write_lock():
            self.metrics_history[machine_id].append({
                'timestamp': timestamp_iso,
                'metrics': metrics.copy() if metrics else {}
            })

    def get_machine(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """
        Get machine data (read-only).

        Uses read lock (allows concurrent reads, no blocking).

        Args:
            machine_id: Machine identifier

        Returns:
            Machine data dict (copy) or None if not found
        """
        with self._machines_lock.read_lock():
            machine = self.machines.get(machine_id)
            # Return deep copy to prevent external mutation
            return self._deep_copy_dict(machine) if machine else None

    def get_all_machines(self) -> List[Dict[str, Any]]:
        """
        Get all machines with updated status.

        Status is automatically updated based on last_seen timestamp:
        - online: seen in last 30 seconds
        - warning: seen 30-60 seconds ago
        - offline: not seen in 60+ seconds

        Returns:
            List of all machine data dicts (copies)
        """
        now = datetime.now()

        # Read machines with status updates
        with self._machines_lock.write_lock():  # Write lock needed for status updates
            for machine in self.machines.values():
                last_seen = datetime.fromisoformat(machine['last_seen'])
                delta_seconds = (now - last_seen).total_seconds()

                if delta_seconds > 60:
                    machine['status'] = 'offline'
                elif delta_seconds > 30:
                    machine['status'] = 'warning'
                # else: status is already 'online'

            # Return deep copies
            return [self._deep_copy_dict(m) for m in self.machines.values()]

    def get_machine_history(self, machine_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get metrics history for a machine.

        Uses read lock (allows concurrent history reads).

        Args:
            machine_id: Machine identifier
            limit: Maximum number of entries to return (most recent)

        Returns:
            List of metric history entries (copies)
        """
        with self._history_lock.read_lock():
            history = self.metrics_history.get(machine_id, deque())
            # Return slice as list (most recent entries)
            history_list = list(history)[-limit:]
            return [self._deep_copy_dict(entry) for entry in history_list]

    def get_fleet_summary(self) -> Dict[str, Any]:
        """
        Get fleet-wide summary statistics.

        Calculates aggregated metrics and identifies machines with issues.
        Uses read lock for safe concurrent access.

        Returns:
            Dict containing:
            - total_machines: Total machine count
            - online/warning/offline: Count by status
            - avg_cpu/memory/disk: Average metrics for online machines
            - alerts: List of machines with critical resource usage
            - timestamp: When summary was generated
        """
        # Read machines snapshot
        with self._machines_lock.read_lock():
            machines = [self._deep_copy_dict(m) for m in self.machines.values()]

        # Perform expensive calculations outside of lock
        total = len(machines)
        online = sum(1 for m in machines if m['status'] == 'online')
        warning = sum(1 for m in machines if m['status'] == 'warning')
        offline = sum(1 for m in machines if m['status'] == 'offline')

        # Aggregate metrics
        if online > 0:
            avg_cpu = sum(m['latest_metrics'].get('cpu', {}).get('percent', 0)
                        for m in machines if m['status'] == 'online') / online
            avg_memory = sum(m['latest_metrics'].get('memory', {}).get('percent', 0)
                           for m in machines if m['status'] == 'online') / online
            avg_disk = sum(m['latest_metrics'].get('disk', {}).get('percent', 0)
                         for m in machines if m['status'] == 'online') / online
        else:
            avg_cpu = avg_memory = avg_disk = 0

        # Find machines with issues
        alerts = []
        for machine in machines:
            if machine['status'] != 'online':
                continue

            metrics = machine['latest_metrics']
            cpu = metrics.get('cpu', {}).get('percent', 0)
            memory = metrics.get('memory', {}).get('percent', 0)
            disk = metrics.get('disk', {}).get('percent', 0)

            if cpu > 90:
                alerts.append({
                    'machine_id': machine['machine_id'],
                    'type': 'cpu',
                    'severity': 'critical',
                    'message': f"CPU usage at {cpu:.1f}%"
                })
            if memory > 90:
                alerts.append({
                    'machine_id': machine['machine_id'],
                    'type': 'memory',
                    'severity': 'critical',
                    'message': f"Memory usage at {memory:.1f}%"
                })
            if disk > 90:
                alerts.append({
                    'machine_id': machine['machine_id'],
                    'type': 'disk',
                    'severity': 'critical',
                    'message': f"Disk usage at {disk:.1f}%"
                })

        return {
            'total_machines': total,
            'online': online,
            'warning': warning,
            'offline': offline,
            'avg_cpu': avg_cpu,
            'avg_memory': avg_memory,
            'avg_disk': avg_disk,
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        }

    def update_health_check(self, machine_id: str, status: str, health_data: Optional[Dict[str, Any]] = None,
                           latency_ms: Optional[int] = None, error: Optional[str] = None):
        """
        Update machine health check status (server-to-device check).

        Args:
            machine_id: Machine identifier
            status: Health status ('reachable', 'unreachable', 'timeout', 'unhealthy', 'error')
            health_data: Health data from agent endpoint
            latency_ms: Round-trip latency in milliseconds
            error: Error message if check failed
        """
        now = datetime.now()

        with self._machines_lock.write_lock():
            if machine_id in self.machines:
                # Initialize health_check if not exists
                if 'health_check' not in self.machines[machine_id]:
                    self.machines[machine_id]['health_check'] = {}

                self.machines[machine_id]['health_check'] = {
                    'status': status,
                    'last_check': now.isoformat(),
                    'latency_ms': latency_ms,
                    'error': error
                }

                # Store detailed health data if provided
                if health_data:
                    self.machines[machine_id]['health_check']['data'] = health_data.copy()
                    self.machines[machine_id]['health_check']['agent_version'] = health_data.get('agent_version')
                    self.machines[machine_id]['health_check']['uptime_seconds'] = health_data.get('uptime_seconds')
                    self.machines[machine_id]['health_check']['agent_responsive'] = health_data.get('responsive', True)

    def add_command(self, machine_id: str, command: Dict[str, Any]):
        """
        Add command to machine's command queue.

        Uses separate command lock (no contention with machine updates).

        Args:
            machine_id: Target machine identifier
            command: Command dict (must include 'id', 'type', 'created_at')
        """
        with self._commands_lock.write_lock():
            self.command_queues[machine_id].append(command.copy())

    def get_pending_commands(self, machine_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending commands for a machine.

        Args:
            machine_id: Machine identifier
            limit: Maximum number of commands to return

        Returns:
            List of command dicts (copies)
        """
        with self._commands_lock.read_lock():
            commands = list(self.command_queues.get(machine_id, deque()))[:limit]
            return [self._deep_copy_dict(cmd) for cmd in commands]

    def remove_command(self, machine_id: str, command_id: str) -> bool:
        """
        Remove command from machine's queue (after acknowledgment).

        Args:
            machine_id: Machine identifier
            command_id: Command ID to remove

        Returns:
            True if command was found and removed, False otherwise
        """
        with self._commands_lock.write_lock():
            queue = self.command_queues.get(machine_id)
            if not queue:
                return False

            # Find and remove command
            for i, cmd in enumerate(queue):
                if cmd.get('id') == command_id:
                    del queue[i]
                    return True

            return False

    @staticmethod
    def _deep_copy_dict(d: Optional[Dict]) -> Optional[Dict]:
        """
        Deep copy a dictionary (prevents external mutation).

        Note: Only copies dicts, lists, and primitive types.
        Does not handle custom objects.

        Args:
            d: Dictionary to copy

        Returns:
            Deep copy of dictionary
        """
        if d is None:
            return None

        def copy_value(v):
            if isinstance(v, dict):
                return {k: copy_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [copy_value(item) for item in v]
            elif isinstance(v, (str, int, float, bool, type(None))):
                return v
            else:
                # For unknown types, try to convert to string (safe fallback)
                return str(v)

        return {k: copy_value(v) for k, v in d.items()}


# Export for use in fleet server
__all__ = ['ImprovedFleetDataStore', 'ReadWriteLock']
