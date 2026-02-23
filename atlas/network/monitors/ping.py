"""
Ping Monitor - Refactored to use BaseNetworkMonitor and CSVLogger

This module uses shared utilities to eliminate ~338 lines of duplicated code
"""
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, List

from atlas.network.monitors.base import BaseNetworkMonitor
from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

# Log file path
PING_LOG_FILE = '~/ping_history.csv'


class PingMonitor(BaseNetworkMonitor):
    """Monitor network latency by pinging 8.8.8.8 - Refactored version"""

    def __init__(self, target: str = "8.8.8.8"):
        """
        Initialize Ping Monitor

        Args:
            target: IP address or hostname to ping (default: 8.8.8.8 - Google DNS)
        """
        self.target = target
        self.consecutive_failures = 0
        self.network_lost_threshold = 3  # Consider network lost after 3 consecutive failures

        # Initialize base class
        super().__init__()

        # Initialize CSV logger (eliminates ~50 lines of CSV code)
        self.csv_logger = CSVLogger(
            log_file=PING_LOG_FILE,
            fieldnames=['timestamp', 'latency', 'packet_loss', 'status'],
            max_history=60,
            retention_days=7
        )

        # Initialize last_result with Ping-specific fields
        self.last_result = {
            'latency': 0,
            'status': 'idle',
            'timestamp': None,
            'packet_loss': 0,
            'error': None,
            'network_lost': False
        }

    # ==================== BaseNetworkMonitor Abstract Methods ====================

    def get_monitor_name(self) -> str:
        """Return human-readable monitor name"""
        return "Ping Monitor"

    def get_default_interval(self) -> int:
        """Ping interval (default: 10 seconds, reduced from 5s to limit kernel network stress)"""
        return 10

    def _run_monitoring_cycle(self):
        """Execute one ping test cycle"""
        try:
            self._run_ping()
        except Exception as e:
            logger.error(f"Ping error: {e}")
            self.update_last_result({
                'status': 'error',
                'error': str(e)
            })

    def _on_cleanup(self):
        """Cleanup old logs (CSVLogger handles automatically)"""
        pass

    # ==================== Ping-Specific Methods ====================

    def _run_ping(self):
        """Run a single ping test"""
        try:
            # Run ping command (1 packet, 2 second timeout)
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2000', self.target],
                capture_output=True,
                text=True,
                timeout=3
            )

            if result.returncode == 0:
                # Parse latency from output
                # Example: "time=14.2 ms"
                output = result.stdout
                latency = 0

                for line in output.split('\n'):
                    if 'time=' in line:
                        try:
                            time_str = line.split('time=')[1].split()[0]
                            latency = float(time_str)
                            break
                        except (IndexError, ValueError):
                            pass

                # Reset consecutive failures on success
                self.consecutive_failures = 0

                ping_result = {
                    'latency': round(latency, 2),
                    'status': 'success',
                    'packet_loss': 0,
                    'error': None,
                    'network_lost': False
                }

                # Update last result (thread-safe via base class)
                self.update_last_result(ping_result)

                # Log to CSV using shared CSVLogger
                self.csv_logger.append({
                    'timestamp': datetime.now().isoformat(),
                    'latency': ping_result['latency'],
                    'packet_loss': 0,
                    'status': 'success'
                })

                # Fleet logging (using base class integration)
                # Sample every 12th ping (~1 per minute at 5s interval)
                if len(self.csv_logger.get_history()) % 12 == 0:
                    self.log_to_fleet('ping', {
                        'latency': round(latency, 2),
                        'packet_loss': 0,
                        'target': self.target
                    })

                logger.debug(f"Ping successful: {latency:.2f}ms")

            else:
                # Ping failed
                self.consecutive_failures += 1
                network_lost = self.consecutive_failures >= self.network_lost_threshold

                self.update_last_result({
                    'latency': 0,
                    'status': 'timeout',
                    'packet_loss': 100,
                    'error': 'Request timeout',
                    'network_lost': network_lost
                })

        except subprocess.TimeoutExpired:
            self.consecutive_failures += 1
            network_lost = self.consecutive_failures >= self.network_lost_threshold

            self.update_last_result({
                'latency': 0,
                'status': 'timeout',
                'packet_loss': 100,
                'error': 'Request timeout',
                'network_lost': network_lost
            })

        except Exception as e:
            logger.error(f"Ping failed: {e}")
            self.consecutive_failures += 1
            network_lost = self.consecutive_failures >= self.network_lost_threshold

            self.update_last_result({
                'latency': 0,
                'status': 'error',
                'packet_loss': 100,
                'error': str(e),
                'network_lost': network_lost
            })

    # ==================== Public API Methods ====================

    def get_history(self) -> List[Dict[str, Any]]:
        """Get ping history from CSV logger"""
        history = self.csv_logger.get_history()
        # Convert to simplified format for graph
        return [{
            'latency': float(row.get('latency', 0)),
            'timestamp': row.get('timestamp', ''),
            'status': row.get('status', 'unknown')
        } for row in history]

    def get_stats(self) -> Dict[str, Any]:
        """Get ping statistics from history"""
        history = self.get_history()

        if not history:
            return {
                'avg_latency': 0,
                'min_latency': 0,
                'max_latency': 0,
                'success_rate': 0,
                'total_pings': 0
            }

        successful_pings = [h for h in history if h['status'] == 'success']

        if successful_pings:
            latencies = [h['latency'] for h in successful_pings]
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
        else:
            avg_latency = min_latency = max_latency = 0

        success_rate = (len(successful_pings) / len(history)) * 100 if history else 0

        return {
            'avg_latency': round(avg_latency, 2),
            'min_latency': round(min_latency, 2),
            'max_latency': round(max_latency, 2),
            'success_rate': round(success_rate, 1),
            'total_pings': len(history)
        }

    def set_target(self, target: str):
        """Change the ping target

        Args:
            target: IP address or hostname to ping
        """
        self.target = target
        logger.info(f"Ping target changed to: {target}")

    def get_target(self) -> str:
        """Get current ping target"""
        return self.target


# Global ping monitor instance (singleton pattern)
_ping_monitor = None


def get_ping_monitor(target: str = "8.8.8.8") -> PingMonitor:
    """Get or create the global ping monitor

    Args:
        target: IP address or hostname to ping (default: 8.8.8.8)
    """
    global _ping_monitor
    if _ping_monitor is None:
        _ping_monitor = PingMonitor(target=target)
    return _ping_monitor
