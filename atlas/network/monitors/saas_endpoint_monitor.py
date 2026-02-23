"""
SaaS Endpoint Monitor - Track connectivity and performance to critical business services

Monitors reachability and latency to:
- Office 365 / Microsoft 365
- Google Workspace
- Salesforce
- AWS services
- Zoom / Microsoft Teams / Google Meet
- Slack
- Custom enterprise endpoints
"""

import logging
import socket
import time
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import statistics

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

class SaaSEndpointMonitor:
    """Monitor SaaS endpoint reachability and performance"""

    # Critical SaaS endpoints to monitor
    DEFAULT_ENDPOINTS = {
        # Microsoft 365
        'office365_portal': {'host': 'portal.office.com', 'port': 443, 'category': 'Office365'},
        'office365_api': {'host': 'graph.microsoft.com', 'port': 443, 'category': 'Office365'},
        'outlook': {'host': 'outlook.office365.com', 'port': 443, 'category': 'Office365'},
        'teams': {'host': 'teams.microsoft.com', 'port': 443, 'category': 'Teams'},
        'onedrive': {'host': 'onedrive.live.com', 'port': 443, 'category': 'Office365'},

        # Google Workspace
        'gmail': {'host': 'mail.google.com', 'port': 443, 'category': 'GoogleWorkspace'},
        'gdrive': {'host': 'drive.google.com', 'port': 443, 'category': 'GoogleWorkspace'},
        'gcal': {'host': 'calendar.google.com', 'port': 443, 'category': 'GoogleWorkspace'},
        'meet': {'host': 'meet.google.com', 'port': 443, 'category': 'GoogleMeet'},

        # Zoom
        'zoom_web': {'host': 'zoom.us', 'port': 443, 'category': 'Zoom'},
        'zoom_api': {'host': 'api.zoom.us', 'port': 443, 'category': 'Zoom'},

        # Salesforce
        'salesforce': {'host': 'login.salesforce.com', 'port': 443, 'category': 'Salesforce'},

        # AWS
        'aws_console': {'host': 'console.aws.amazon.com', 'port': 443, 'category': 'AWS'},
        'aws_s3': {'host': 's3.amazonaws.com', 'port': 443, 'category': 'AWS'},

        # Slack
        'slack': {'host': 'slack.com', 'port': 443, 'category': 'Slack'},
        'slack_api': {'host': 'api.slack.com', 'port': 443, 'category': 'Slack'},

        # Common CDNs
        'cloudflare': {'host': 'cloudflare.com', 'port': 443, 'category': 'CDN'},
        'akamai': {'host': 'akamai.com', 'port': 443, 'category': 'CDN'},
    }

    def __init__(self, sample_interval: int = 60, custom_endpoints: Optional[Dict] = None):
        """
        Initialize SaaS endpoint monitor

        Args:
            sample_interval: Seconds between checks (default: 60)
            custom_endpoints: Additional custom endpoints to monitor
        """
        self.sample_interval = sample_interval
        self._running = False
        self._thread = None

        # Merge default and custom endpoints
        self.endpoints = self.DEFAULT_ENDPOINTS.copy()
        if custom_endpoints:
            self.endpoints.update(custom_endpoints)

        # CSV Loggers
        log_dir = Path.home()
        self.reachability_logger = CSVLogger(
            str(log_dir / 'saas_reachability.csv'),
            fieldnames=['timestamp', 'endpoint_name', 'host', 'category', 'reachable',
                    'latency_ms', 'dns_time_ms', 'connect_time_ms', 'error'],
            retention_days=7,
            max_history=1000
        )

        self.incidents_logger = CSVLogger(
            str(log_dir / 'saas_incidents.csv'),
            fieldnames=['timestamp', 'endpoint_name', 'category', 'incident_type',
                    'duration_seconds', 'details'],
            retention_days=30,
            max_history=500
        )

        # State tracking
        self._last_status: Dict[str, bool] = {}
        self._incident_start_times: Dict[str, datetime] = {}

    def start(self):
        """Start monitoring SaaS endpoints"""
        if self._running:
            logger.warning("SaaS endpoint monitor already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"SaaS endpoint monitor started with {self.sample_interval}s interval")

    def stop(self):
        """Stop monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("SaaS endpoint monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._check_all_endpoints()
            except Exception as e:
                logger.error(f"Error in SaaS monitoring loop: {e}")

            time.sleep(self.sample_interval)

    def _check_all_endpoints(self):
        """Check all configured endpoints"""
        current_time = datetime.now()

        for endpoint_name, endpoint_config in self.endpoints.items():
            try:
                result = self._check_endpoint(
                    endpoint_config['host'],
                    endpoint_config.get('port', 443)
                )

                # Log reachability
                self.reachability_logger.append({
                    'timestamp': current_time.isoformat(),
                    'endpoint_name': endpoint_name,
                    'host': endpoint_config['host'],
                    'category': endpoint_config.get('category', 'Custom'),
                    'reachable': result['reachable'],
                    'latency_ms': result.get('latency_ms', 0),
                    'dns_time_ms': result.get('dns_time_ms', 0),
                    'connect_time_ms': result.get('connect_time_ms', 0),
                    'error': result.get('error', '')
                })

                # Track incidents (outages)
                self._track_incidents(endpoint_name, endpoint_config, result, current_time)

            except Exception as e:
                logger.error(f"Error checking endpoint {endpoint_name}: {e}")

    def _check_endpoint(self, host: str, port: int = 443, timeout: int = 5) -> dict:
        """
        Check endpoint reachability and measure latency

        Returns dict with: reachable, latency_ms, dns_time_ms, connect_time_ms, error
        """
        result = {
            'reachable': False,
            'latency_ms': 0,
            'dns_time_ms': 0,
            'connect_time_ms': 0,
            'error': ''
        }

        try:
            # DNS resolution
            dns_start = time.time()
            ip = socket.gethostbyname(host)
            dns_time = (time.time() - dns_start) * 1000
            result['dns_time_ms'] = round(dns_time, 2)

            # TCP connection
            connect_start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            try:
                sock.connect((ip, port))
                connect_time = (time.time() - connect_start) * 1000
                result['connect_time_ms'] = round(connect_time, 2)
                result['latency_ms'] = round(dns_time + connect_time, 2)
                result['reachable'] = True
            finally:
                sock.close()

        except socket.gaierror as e:
            result['error'] = f"DNS resolution failed: {e}"
        except socket.timeout:
            result['error'] = "Connection timeout"
        except ConnectionRefusedError:
            result['error'] = "Connection refused"
        except Exception as e:
            result['error'] = str(e)

        return result

    def _track_incidents(self, endpoint_name: str, endpoint_config: dict,
                        result: dict, current_time: datetime):
        """Track endpoint outages and recoveries"""
        is_reachable = result['reachable']
        was_reachable = self._last_status.get(endpoint_name, True)

        # New outage
        if was_reachable and not is_reachable:
            self._incident_start_times[endpoint_name] = current_time
            logger.warning(f"SaaS endpoint {endpoint_name} became unreachable: {result.get('error')}")

        # Recovery
        elif not was_reachable and is_reachable:
            if endpoint_name in self._incident_start_times:
                duration = (current_time - self._incident_start_times[endpoint_name]).total_seconds()
                self.incidents_logger.append({
                    'timestamp': current_time.isoformat(),
                    'endpoint_name': endpoint_name,
                    'category': endpoint_config.get('category', 'Custom'),
                    'incident_type': 'outage_recovered',
                    'duration_seconds': duration,
                    'details': f"Endpoint recovered after {duration:.0f}s outage"
                })
                del self._incident_start_times[endpoint_name]
                logger.info(f"SaaS endpoint {endpoint_name} recovered after {duration:.0f}s")

        # High latency incident
        elif is_reachable and result['latency_ms'] > 1000:  # >1s latency
            self.incidents_logger.append({
                'timestamp': current_time.isoformat(),
                'endpoint_name': endpoint_name,
                'category': endpoint_config.get('category', 'Custom'),
                'incident_type': 'high_latency',
                'duration_seconds': 0,
                'details': f"High latency: {result['latency_ms']:.0f}ms"
            })

        self._last_status[endpoint_name] = is_reachable

    def get_current_status(self) -> Dict[str, dict]:
        """Get current status of all endpoints"""
        status = {}
        recent_entries = self.reachability_logger.get_history()

        # Get most recent entry for each endpoint
        for entry in reversed(recent_entries):
            endpoint_name = entry.get('endpoint_name')
            if endpoint_name and endpoint_name not in status:
                status[endpoint_name] = entry

        return status

    def get_category_summary(self) -> Dict[str, dict]:
        """Get summary statistics by category"""
        recent_entries = self.reachability_logger.get_history()
        categories = {}

        for entry in recent_entries:
            category = entry.get('category', 'Unknown')
            if category not in categories:
                categories[category] = {
                    'total_checks': 0,
                    'successful_checks': 0,
                    'latencies': []
                }

            categories[category]['total_checks'] += 1
            if entry.get('reachable'):
                categories[category]['successful_checks'] += 1
                if entry.get('latency_ms'):
                    categories[category]['latencies'].append(float(entry['latency_ms']))

        # Calculate statistics
        summary = {}
        for category, data in categories.items():
            availability = 0
            if data['total_checks'] > 0:
                availability = (data['successful_checks'] / data['total_checks']) * 100

            avg_latency = 0
            if data['latencies']:
                avg_latency = statistics.mean(data['latencies'])

            summary[category] = {
                'availability_percent': round(availability, 2),
                'avg_latency_ms': round(avg_latency, 2),
                'total_checks': data['total_checks']
            }

        return summary

    def add_custom_endpoint(self, name: str, host: str, port: int = 443, category: str = 'Custom'):
        """Add a custom endpoint to monitor"""
        self.endpoints[name] = {
            'host': host,
            'port': port,
            'category': category
        }
        logger.info(f"Added custom endpoint: {name} ({host}:{port})")


# Singleton instance
_saas_monitor_instance = None
_monitor_lock = threading.Lock()

def get_saas_endpoint_monitor(sample_interval: int = 60,
                               custom_endpoints: Optional[Dict] = None) -> SaaSEndpointMonitor:
    """Get or create singleton SaaS endpoint monitor instance"""
    global _saas_monitor_instance

    with _monitor_lock:
        if _saas_monitor_instance is None:
            _saas_monitor_instance = SaaSEndpointMonitor(
                sample_interval=sample_interval,
                custom_endpoints=custom_endpoints
            )
            _saas_monitor_instance.start()

        return _saas_monitor_instance
