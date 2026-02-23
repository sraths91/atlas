"""
Fleet Data Store - In-memory data store for fleet metrics

Extracted from fleet_server.py (Phase 4: Fleet Server Decomposition)
This module provides thread-safe storage for machine metrics and fleet data.

Migration completed: December 31, 2025
"""
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class FleetDataStore:
    """In-memory data store for fleet metrics

    Thread-safe storage for machine metrics, history, and fleet-wide data.
    Supports dynamic status updates based on last-seen timestamps.

    When a new agent connects for the first time, the dashboard page is
    automatically available at /machine/{serial_number}/dashboard
    """

    def __init__(self, history_size: int = 1000, on_new_agent=None):
        """Initialize the data store

        Args:
            history_size: Maximum number of metric entries to keep per machine
            on_new_agent: Optional callback function called when new agent registers.
                          Signature: on_new_agent(machine_id, machine_info, dashboard_url)
        """
        self.machines = {}  # machine_id -> machine data
        self.metrics_history = defaultdict(lambda: deque(maxlen=history_size))
        self.agent_db_keys = {}  # machine_id -> Fernet key (b64 str)
        self.export_logs = []  # permanent export log entries
        self.lock = threading.Lock()
        self.history_size = history_size
        self.on_new_agent = on_new_agent  # Callback for new agent registration

    def update_machine(self, machine_id: str, machine_info: Dict[str, Any], metrics: Dict[str, Any]):
        """Update machine data and metrics

        Args:
            machine_id: Unique machine identifier
            machine_info: Machine information (hostname, OS, etc.)
            metrics: Current metrics (CPU, memory, disk, etc.)

        When a new agent connects for the first time:
        - Creates the machine entry with first_seen timestamp
        - Logs the registration with dashboard URL
        - Calls on_new_agent callback if configured
        - Dashboard page is immediately available at /machine/{sn}/dashboard
        """
        is_new_agent = False

        with self.lock:
            now = datetime.now()

            # Update or create machine entry
            if machine_id not in self.machines:
                is_new_agent = True
                self.machines[machine_id] = {
                    'machine_id': machine_id,
                    'info': machine_info,
                    'first_seen': now.isoformat(),
                    'last_seen': now.isoformat(),
                    'status': 'online',
                    'latest_metrics': metrics
                }
            else:
                self.machines[machine_id]['last_seen'] = now.isoformat()
                self.machines[machine_id]['status'] = 'online'
                self.machines[machine_id]['latest_metrics'] = metrics
                # Update info if changed
                if machine_info:
                    self.machines[machine_id]['info'].update(machine_info)

            # Store metrics in history
            self.metrics_history[machine_id].append({
                'timestamp': now.isoformat(),
                'metrics': metrics
            })

        # Handle new agent registration (outside lock to avoid blocking)
        if is_new_agent:
            serial_number = machine_info.get('serial_number', machine_id)
            computer_name = machine_info.get('computer_name', machine_info.get('hostname', machine_id))
            local_ip = machine_info.get('local_ip', 'unknown')
            dashboard_url = f"/machine/{serial_number}/dashboard"

            # Log new agent registration
            logger.info(f"═══════════════════════════════════════════════════════════════")
            logger.info(f"🆕 NEW AGENT REGISTERED: {computer_name}")
            logger.info(f"   Serial Number: {serial_number}")
            logger.info(f"   Machine ID:    {machine_id}")
            logger.info(f"   Local IP:      {local_ip}")
            logger.info(f"   Dashboard URL: {dashboard_url}")
            logger.info(f"   First Seen:    {now.isoformat()}")
            logger.info(f"═══════════════════════════════════════════════════════════════")

            # Call callback if configured
            if self.on_new_agent:
                try:
                    self.on_new_agent(machine_id, machine_info, dashboard_url)
                except Exception as e:
                    logger.error(f"Error in on_new_agent callback: {e}")

    def store_agent_db_key(self, machine_id: str, key_b64: str):
        """Store an agent's local DB Fernet key."""
        with self.lock:
            self.agent_db_keys[machine_id] = key_b64

    def get_agent_db_key(self, machine_id: str) -> Optional[str]:
        """Get an agent's local DB Fernet key."""
        with self.lock:
            return self.agent_db_keys.get(machine_id)

    def store_export_log(self, machine_id: str, log_data: Dict[str, Any]):
        """Store an export log entry permanently (in-memory)."""
        with self.lock:
            self.export_logs.append({
                'machine_id': machine_id,
                'timestamp': log_data.get('timestamp', datetime.now().isoformat()),
                'local_user': log_data.get('local_user', 'unknown'),
                'export_type': log_data.get('export_type', 'unknown'),
                'format': log_data.get('format', 'unknown'),
                'encrypted': bool(log_data.get('encrypted')),
                'mode': log_data.get('mode', 'none'),
                'filename': log_data.get('filename', ''),
                'data': log_data,
            })

    def get_export_logs(self, machine_id: Optional[str] = None,
                        limit: int = 200) -> List[Dict[str, Any]]:
        """Get export logs, newest first."""
        with self.lock:
            logs = self.export_logs
            if machine_id:
                logs = [l for l in logs if l['machine_id'] == machine_id]
            return list(reversed(logs))[:limit]

    def get_machine(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Get machine data

        Args:
            machine_id: Machine identifier

        Returns:
            Machine data dict or None if not found
        """
        with self.lock:
            return self.machines.get(machine_id)

    def get_all_machines(self) -> List[Dict[str, Any]]:
        """Get all machines with updated status

        Status is automatically updated based on last_seen timestamp:
        - online: seen in last 30 seconds
        - warning: seen 30-60 seconds ago
        - offline: not seen in 60+ seconds

        Returns:
            List of all machine data dicts
        """
        with self.lock:
            # Update status based on last_seen
            now = datetime.now()
            for machine in self.machines.values():
                last_seen = datetime.fromisoformat(machine['last_seen'])
                if (now - last_seen).total_seconds() > 60:
                    machine['status'] = 'offline'
                elif (now - last_seen).total_seconds() > 30:
                    machine['status'] = 'warning'

            return list(self.machines.values())

    def get_registered_agents(self) -> List[Dict[str, Any]]:
        """Get list of all registered agents with their dashboard URLs

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
        with self.lock:
            agents = []
            now = datetime.now()

            for machine in self.machines.values():
                info = machine.get('info', {})
                serial_number = info.get('serial_number', machine['machine_id'])

                # Update status
                last_seen = datetime.fromisoformat(machine['last_seen'])
                if (now - last_seen).total_seconds() > 60:
                    status = 'offline'
                elif (now - last_seen).total_seconds() > 30:
                    status = 'warning'
                else:
                    status = 'online'

                agents.append({
                    'machine_id': machine['machine_id'],
                    'serial_number': serial_number,
                    'computer_name': info.get('computer_name', info.get('hostname', machine['machine_id'])),
                    'local_ip': info.get('local_ip', 'unknown'),
                    'dashboard_url': f"/machine/{serial_number}/dashboard",
                    'first_seen': machine.get('first_seen'),
                    'last_seen': machine.get('last_seen'),
                    'status': status
                })

            return agents

    def get_machine_history(self, machine_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get metrics history for a machine

        Args:
            machine_id: Machine identifier
            limit: Maximum number of entries to return (most recent)

        Returns:
            List of metric history entries
        """
        with self.lock:
            history = list(self.metrics_history.get(machine_id, []))
            return history[-limit:]

    def get_fleet_summary(self) -> Dict[str, Any]:
        """Get fleet-wide summary statistics

        Calculates aggregated metrics and identifies machines with issues.

        Returns:
            Dict containing:
            - total_machines: Total machine count
            - online/warning/offline: Count by status
            - avg_cpu/memory/disk: Average metrics for online machines
            - alerts: List of machines with critical resource usage
            - timestamp: When summary was generated
        """
        with self.lock:
            machines = list(self.machines.values())

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
        """Update machine health check status (server-to-device check)

        This tracks the result of active health checks from server to agent.

        Args:
            machine_id: Machine identifier
            status: Health status ('reachable', 'unreachable', 'timeout', 'unhealthy', 'error')
            health_data: Health data from agent endpoint
            latency_ms: Round-trip latency in milliseconds
            error: Error message if check failed
        """
        with self.lock:
            now = datetime.now()

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
                    self.machines[machine_id]['health_check']['data'] = health_data
                    self.machines[machine_id]['health_check']['agent_version'] = health_data.get('agent_version')
                    self.machines[machine_id]['health_check']['uptime_seconds'] = health_data.get('uptime_seconds')
                    self.machines[machine_id]['health_check']['agent_responsive'] = health_data.get('responsive', True)

    def store_network_test_metrics(self, machine_id: str, test_type: str, metrics: Dict[str, Any]):
        """Store network test metrics from agent (CyPerf-inspired tests)

        Args:
            machine_id: Machine identifier
            test_type: Type of test ('udp_quality', 'connection_rate', 'throughput', 'mos')
            metrics: Test results including measurements and quality scores
        """
        with self.lock:
            now = datetime.now()

            # Initialize network_tests storage if not exists
            if machine_id not in self.machines:
                logger.warning(f"Received network test metrics for unknown machine: {machine_id}")
                return

            if 'network_tests' not in self.machines[machine_id]:
                self.machines[machine_id]['network_tests'] = {
                    'udp_quality': deque(maxlen=100),
                    'connection_rate': deque(maxlen=100),
                    'throughput': deque(maxlen=100),
                    'mos': deque(maxlen=100)
                }

            # Add timestamp to metrics
            metrics['timestamp'] = now.isoformat()
            metrics['machine_id'] = machine_id

            # Store in appropriate queue
            if test_type in self.machines[machine_id]['network_tests']:
                self.machines[machine_id]['network_tests'][test_type].append(metrics)
                logger.info(f"Stored {test_type} metrics for machine {machine_id}")
            else:
                logger.warning(f"Unknown test type: {test_type}")

    def get_network_test_metrics(self, machine_id: str, test_type: str = None, limit: int = 50) -> Dict[str, Any]:
        """Get network test metrics for a machine

        Args:
            machine_id: Machine identifier
            test_type: Optional specific test type, or None for all types
            limit: Maximum number of results per type

        Returns:
            Dict with test metrics by type
        """
        with self.lock:
            if machine_id not in self.machines:
                return {'error': 'Machine not found'}

            network_tests = self.machines[machine_id].get('network_tests', {})

            if test_type:
                # Return specific test type
                tests = list(network_tests.get(test_type, []))
                return {test_type: tests[-limit:]}
            else:
                # Return all test types
                result = {}
                for t_type, tests in network_tests.items():
                    result[t_type] = list(tests)[-limit:]
                return result

    def get_fleet_network_test_summary(self, test_type: str = None, hours: int = 24) -> Dict[str, Any]:
        """Get fleet-wide network test summary

        Args:
            test_type: Optional specific test type
            hours: Time window in hours

        Returns:
            Aggregated network test statistics across fleet
        """
        from datetime import timedelta

        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            summary = {
                'total_tests': 0,
                'machines_tested': 0,
                'by_machine': {},
                'aggregated': {}
            }

            test_types = [test_type] if test_type else ['udp_quality', 'connection_rate', 'throughput', 'mos']

            for machine_id, machine in self.machines.items():
                network_tests = machine.get('network_tests', {})
                machine_has_tests = False

                for t_type in test_types:
                    tests = list(network_tests.get(t_type, []))
                    # Filter by time
                    recent_tests = [
                        t for t in tests
                        if datetime.fromisoformat(t.get('timestamp', '2000-01-01')) > cutoff
                    ]

                    if recent_tests:
                        machine_has_tests = True
                        summary['total_tests'] += len(recent_tests)

                        if machine_id not in summary['by_machine']:
                            summary['by_machine'][machine_id] = {}
                        summary['by_machine'][machine_id][t_type] = {
                            'count': len(recent_tests),
                            'latest': recent_tests[-1] if recent_tests else None
                        }

                        # Aggregate metrics based on test type
                        if t_type not in summary['aggregated']:
                            summary['aggregated'][t_type] = {'values': [], 'count': 0}

                        summary['aggregated'][t_type]['count'] += len(recent_tests)

                        # Extract key metrics for aggregation
                        if t_type == 'mos':
                            summary['aggregated'][t_type]['values'].extend(
                                [t.get('mos_score', 0) for t in recent_tests]
                            )
                        elif t_type == 'udp_quality':
                            summary['aggregated'][t_type]['values'].extend(
                                [t.get('quality_score', 0) for t in recent_tests]
                            )
                        elif t_type == 'throughput':
                            summary['aggregated'][t_type]['values'].extend(
                                [t.get('download_mbps', 0) for t in recent_tests]
                            )
                        elif t_type == 'connection_rate':
                            summary['aggregated'][t_type]['values'].extend(
                                [t.get('cps', 0) for t in recent_tests]
                            )

                if machine_has_tests:
                    summary['machines_tested'] += 1

            # Calculate averages
            for t_type, data in summary['aggregated'].items():
                values = data.get('values', [])
                if values:
                    data['avg'] = sum(values) / len(values)
                    data['min'] = min(values)
                    data['max'] = max(values)
                del data['values']  # Remove raw values from response

            summary['time_window_hours'] = hours
            summary['timestamp'] = datetime.now().isoformat()

            return summary


# Export for backward compatibility
__all__ = ['FleetDataStore']
