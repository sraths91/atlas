"""
VPN Monitor - Track VPN connections and performance

Monitors:
- Active VPN connections and tunnels
- VPN interface metrics (throughput, latency)
- VPN reconnection events
- Split tunnel detection
- Common VPN clients (Cisco AnyConnect, GlobalProtect, OpenVPN, etc.)
"""

import logging
import subprocess
import re
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

class VPNMonitor:
    """Monitor VPN connections and performance"""

    # Common VPN interface patterns
    VPN_INTERFACE_PATTERNS = [
        'utun',  # macOS VPN interfaces
        'ppp',   # PPP-based VPNs
        'ipsec', # IPsec VPNs
        'tun',   # Generic tunnel interfaces
        'tap',   # TAP interfaces
    ]

    # Known VPN client processes
    VPN_PROCESSES = {
        'Cisco AnyConnect': ['vpnagentd', 'acwebsecagent'],
        'GlobalProtect': ['PanGPS', 'PanGPA'],
        'OpenVPN': ['openvpn'],
        'Tunnelblick': ['tunnelblick'],
        'Viscosity': ['viscosity'],
        'FortiClient': ['FortiClient'],
        'NordVPN': ['nordvpn'],
        'ExpressVPN': ['expressvpn'],
    }

    def __init__(self, sample_interval: int = 30):
        """
        Initialize VPN monitor

        Args:
            sample_interval: Seconds between samples (default: 30)
        """
        self.sample_interval = sample_interval
        self._running = False
        self._thread = None

        # CSV Loggers
        log_dir = Path.home()
        self.connections_logger = CSVLogger(
            str(log_dir / 'vpn_connections.csv'),
            fieldnames=['timestamp', 'vpn_client', 'interface', 'status', 'local_ip',
                    'remote_ip', 'duration_seconds'],
            retention_days=7,
            max_history=100
        )

        self.metrics_logger = CSVLogger(
            str(log_dir / 'vpn_metrics.csv'),
            fieldnames=['timestamp', 'interface', 'bytes_sent', 'bytes_received',
                    'packets_sent', 'packets_received', 'errors_in', 'errors_out'],
            retention_days=7,
            max_history=1000
        )

        self.events_logger = CSVLogger(
            str(log_dir / 'vpn_events.csv'),
            fieldnames=['timestamp', 'event_type', 'vpn_client', 'interface', 'details'],
            retention_days=30,
            max_history=500
        )

        # State tracking
        self._last_connections: Dict[str, dict] = {}
        self._connection_start_times: Dict[str, datetime] = {}

    def start(self):
        """Start monitoring VPN connections"""
        if self._running:
            logger.warning("VPN monitor already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"VPN monitor started with {self.sample_interval}s interval")

    def stop(self):
        """Stop monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("VPN monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._collect_vpn_data()
            except Exception as e:
                logger.error(f"Error in VPN monitoring loop: {e}")

            time.sleep(self.sample_interval)

    def _collect_vpn_data(self):
        """Collect VPN connection and metrics data"""
        current_time = datetime.now()

        # Detect active VPN connections
        vpn_interfaces = self._get_vpn_interfaces()
        active_vpn_client = self._detect_vpn_client()

        # Track new connections and disconnections
        current_interfaces = set(vpn_interfaces.keys())
        previous_interfaces = set(self._last_connections.keys())

        # New connections
        new_connections = current_interfaces - previous_interfaces
        for interface in new_connections:
            self._log_connection_event('connect', interface, active_vpn_client)
            self._connection_start_times[interface] = current_time

        # Disconnections
        disconnections = previous_interfaces - current_interfaces
        for interface in disconnections:
            self._log_connection_event('disconnect', interface,
                                       self._last_connections[interface].get('vpn_client'))
            if interface in self._connection_start_times:
                del self._connection_start_times[interface]

        # Collect metrics for active VPN interfaces
        for interface, info in vpn_interfaces.items():
            # Log connection status
            duration = 0
            if interface in self._connection_start_times:
                duration = (current_time - self._connection_start_times[interface]).total_seconds()

            self.connections_logger.append({
                'timestamp': current_time.isoformat(),
                'vpn_client': active_vpn_client or 'Unknown',
                'interface': interface,
                'status': 'connected',
                'local_ip': info.get('local_ip', ''),
                'remote_ip': info.get('remote_ip', ''),
                'duration_seconds': duration
            })

            # Log interface metrics
            stats = self._get_interface_stats(interface)
            if stats:
                self.metrics_logger.append({
                    'timestamp': current_time.isoformat(),
                    'interface': interface,
                    'bytes_sent': stats.get('bytes_sent', 0),
                    'bytes_received': stats.get('bytes_received', 0),
                    'packets_sent': stats.get('packets_sent', 0),
                    'packets_received': stats.get('packets_received', 0),
                    'errors_in': stats.get('errors_in', 0),
                    'errors_out': stats.get('errors_out', 0)
                })

            # Check for split tunnel
            if self._detect_split_tunnel(interface):
                self._log_event('split_tunnel_detected', interface, active_vpn_client,
                              'Split tunnel configuration detected')

        self._last_connections = vpn_interfaces

    def _get_vpn_interfaces(self) -> Dict[str, dict]:
        """Get active VPN interfaces and their info"""
        vpn_interfaces = {}

        try:
            # Get all network interfaces
            result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return vpn_interfaces

            current_interface = None
            interface_data = {}

            for line in result.stdout.split('\n'):
                # New interface
                if line and not line.startswith('\t') and not line.startswith(' '):
                    # Save previous interface if it was a VPN interface
                    if current_interface and self._is_vpn_interface(current_interface):
                        vpn_interfaces[current_interface] = interface_data.copy()

                    # Start new interface
                    current_interface = line.split(':')[0]
                    interface_data = {'interface': current_interface}

                # Parse interface details
                elif current_interface:
                    if 'inet ' in line:
                        match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                        if match:
                            interface_data['local_ip'] = match.group(1)
                    elif '->' in line and 'inet' in line:
                        # Point-to-point interface (typical for VPN)
                        match = re.search(r'--> (\d+\.\d+\.\d+\.\d+)', line)
                        if match:
                            interface_data['remote_ip'] = match.group(1)
                    elif 'status: active' in line:
                        interface_data['status'] = 'active'

            # Don't forget the last interface
            if current_interface and self._is_vpn_interface(current_interface):
                vpn_interfaces[current_interface] = interface_data

        except Exception as e:
            logger.error(f"Error getting VPN interfaces: {e}")

        return vpn_interfaces

    def _is_vpn_interface(self, interface: str) -> bool:
        """Check if interface name matches VPN patterns"""
        for pattern in self.VPN_INTERFACE_PATTERNS:
            if interface.startswith(pattern):
                return True
        return False

    def _detect_vpn_client(self) -> Optional[str]:
        """Detect which VPN client is running"""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None

            processes = result.stdout.lower()

            for client_name, process_names in self.VPN_PROCESSES.items():
                for process in process_names:
                    if process.lower() in processes:
                        return client_name

        except Exception as e:
            logger.error(f"Error detecting VPN client: {e}")

        return None

    def _get_interface_stats(self, interface: str) -> Optional[dict]:
        """Get network statistics for an interface"""
        try:
            result = subprocess.run(['netstat', '-ibn'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None

            for line in result.stdout.split('\n'):
                if line.startswith(interface):
                    parts = line.split()
                    if len(parts) >= 10:
                        return {
                            'bytes_received': int(parts[6]),
                            'packets_received': int(parts[4]),
                            'errors_in': int(parts[5]),
                            'bytes_sent': int(parts[9]),
                            'packets_sent': int(parts[7]),
                            'errors_out': int(parts[8])
                        }

        except Exception as e:
            logger.error(f"Error getting interface stats: {e}")

        return None

    def _detect_split_tunnel(self, interface: str) -> bool:
        """Detect if VPN is using split tunnel configuration"""
        try:
            # Check routing table - if default route doesn't go through VPN, it's split tunnel
            result = subprocess.run(['netstat', '-rn'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return False

            # Look for default route (0.0.0.0 or default)
            for line in result.stdout.split('\n'):
                if 'default' in line or '0.0.0.0' in line:
                    # If default route goes through VPN interface, not split tunnel
                    if interface in line:
                        return False

            # If we have a VPN interface but it's not the default route, it's split tunnel
            return True

        except Exception as e:
            logger.error(f"Error detecting split tunnel: {e}")
            return False

    def _log_connection_event(self, event_type: str, interface: str, vpn_client: Optional[str]):
        """Log VPN connection event"""
        self._log_event(event_type, interface, vpn_client,
                       f"VPN {event_type} on interface {interface}")

    def _log_event(self, event_type: str, interface: str, vpn_client: Optional[str], details: str):
        """Log VPN event"""
        self.events_logger.append({
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'vpn_client': vpn_client or 'Unknown',
            'interface': interface,
            'details': details
        })
        logger.info(f"VPN event: {event_type} - {details}")

    def get_current_status(self) -> dict:
        """Get current VPN status"""
        vpn_interfaces = self._get_vpn_interfaces()
        vpn_client = self._detect_vpn_client()

        return {
            'connected': len(vpn_interfaces) > 0,
            'vpn_client': vpn_client,
            'interfaces': vpn_interfaces,
            'connection_count': len(vpn_interfaces)
        }

    def get_connection_history(self, hours: int = 24) -> List[dict]:
        """Get VPN connection history"""
        return self.connections_logger.get_history()

    def get_events(self, hours: int = 24) -> List[dict]:
        """Get VPN events"""
        return self.events_logger.get_history()


# Singleton instance
_vpn_monitor_instance = None
_monitor_lock = threading.Lock()

def get_vpn_monitor(sample_interval: int = 30) -> VPNMonitor:
    """Get or create singleton VPN monitor instance"""
    global _vpn_monitor_instance

    with _monitor_lock:
        if _vpn_monitor_instance is None:
            _vpn_monitor_instance = VPNMonitor(sample_interval=sample_interval)
            _vpn_monitor_instance.start()

        return _vpn_monitor_instance
