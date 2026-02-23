"""
WiFi Monitor - Refactored to use BaseNetworkMonitor and CSVLogger

This module uses shared utilities to eliminate ~850 lines of duplicated code
"""
import subprocess
import time
import logging
import re
import socket
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import deque

from atlas.network.monitors.base import BaseNetworkMonitor
from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

# Log file paths
WIFI_LOG_FILE = str(Path.home() / 'wifi_quality.csv')
WIFI_EVENTS_FILE = str(Path.home() / 'wifi_events.csv')
NETWORK_DIAG_FILE = str(Path.home() / 'network_diagnostics.csv')

# External test targets (for backward compatibility)
EXTERNAL_PING_TARGETS = [
    ('8.8.8.8', 'Google DNS'),
    ('1.1.1.1', 'Cloudflare DNS'),
]
DNS_TEST_DOMAINS = ['google.com', 'cloudflare.com', 'apple.com']


class NetworkDiagnostics:
    """Network diagnostic tools to identify connection issues"""

    @staticmethod
    def get_default_gateway() -> Optional[str]:
        """Get the default gateway IP address"""
        try:
            result = subprocess.run(
                ['netstat', '-rn'],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if line.startswith('default') or line.startswith('0.0.0.0'):
                    parts = line.split()
                    if len(parts) >= 2:
                        gateway = parts[1]
                        # Validate it's an IP
                        if re.match(r'\d+\.\d+\.\d+\.\d+', gateway):
                            return gateway
            return None
        except Exception as e:
            logger.error(f"Failed to get default gateway: {e}")
            return None

    @staticmethod
    def ping_host(host: str, count: int = 3, timeout: int = 2) -> Dict[str, Any]:
        """Ping a host and return latency statistics"""
        try:
            result = subprocess.run(
                ['ping', '-c', str(count), '-W', str(timeout * 1000), host],
                capture_output=True,
                text=True,
                timeout=timeout * count + 5
            )

            if result.returncode != 0:
                return {
                    'host': host,
                    'reachable': False,
                    'packet_loss': 100,
                    'avg_latency': None,
                    'min_latency': None,
                    'max_latency': None
                }

            # Parse ping output
            packet_loss = 100
            avg_latency = None
            min_latency = None
            max_latency = None

            for line in result.stdout.split('\n'):
                # Parse packet loss
                if 'packet loss' in line:
                    match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*packet loss', line)
                    if match:
                        packet_loss = float(match.group(1))

                # Parse round-trip times
                if 'round-trip' in line or 'rtt' in line:
                    match = re.search(r'(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)', line)
                    if match:
                        min_latency = float(match.group(1))
                        avg_latency = float(match.group(2))
                        max_latency = float(match.group(3))

            return {
                'host': host,
                'reachable': packet_loss < 100,
                'packet_loss': packet_loss,
                'avg_latency': avg_latency,
                'min_latency': min_latency,
                'max_latency': max_latency
            }
        except subprocess.TimeoutExpired:
            return {
                'host': host,
                'reachable': False,
                'packet_loss': 100,
                'avg_latency': None,
                'min_latency': None,
                'max_latency': None
            }
        except Exception as e:
            logger.error(f"Ping failed for {host}: {e}")
            return {
                'host': host,
                'reachable': False,
                'packet_loss': 100,
                'avg_latency': None,
                'min_latency': None,
                'max_latency': None
            }

    @staticmethod
    def test_dns_resolution(domain: str, timeout: int = 3) -> Dict[str, Any]:
        """Test DNS resolution for a domain"""
        try:
            start_time = time.time()
            socket.setdefaulttimeout(timeout)
            ip = socket.gethostbyname(domain)
            resolve_time = (time.time() - start_time) * 1000  # Convert to ms

            return {
                'domain': domain,
                'resolved': True,
                'ip': ip,
                'resolve_time_ms': round(resolve_time, 2)
            }
        except socket.gaierror:
            return {
                'domain': domain,
                'resolved': False,
                'ip': None,
                'resolve_time_ms': None,
                'error': 'DNS resolution failed'
            }
        except socket.timeout:
            return {
                'domain': domain,
                'resolved': False,
                'ip': None,
                'resolve_time_ms': None,
                'error': 'DNS timeout'
            }
        except Exception as e:
            return {
                'domain': domain,
                'resolved': False,
                'ip': None,
                'resolve_time_ms': None,
                'error': str(e)
            }

    @staticmethod
    def diagnose_network_issue(
        wifi_quality: int,
        gateway_ping: Dict[str, Any],
        external_ping: Dict[str, Any],
        dns_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Diagnose network issues based on test results.

        Returns a diagnosis with:
        - issue_type: 'none', 'wifi', 'router', 'isp', 'dns', 'multiple'
        - severity: 'none', 'minor', 'moderate', 'severe'
        - description: Human-readable description
        - recommendation: Suggested action
        """
        issues = []

        # Check WiFi signal quality
        wifi_ok = wifi_quality >= 50
        if not wifi_ok:
            issues.append({
                'type': 'wifi',
                'severity': 'severe' if wifi_quality < 30 else 'moderate',
                'detail': f'Weak WiFi signal ({wifi_quality}%)'
            })

        # Check gateway (router) connectivity
        gateway_ok = gateway_ping.get('reachable', False) and gateway_ping.get('packet_loss', 100) < 10
        gateway_latency_ok = gateway_ping.get('avg_latency') and gateway_ping.get('avg_latency') < 50

        if not gateway_ok:
            issues.append({
                'type': 'router',
                'severity': 'severe',
                'detail': f"Can't reach router ({gateway_ping.get('packet_loss', 100):.0f}% packet loss)"
            })
        elif not gateway_latency_ok and gateway_ping.get('avg_latency'):
            issues.append({
                'type': 'router',
                'severity': 'moderate',
                'detail': f"High router latency ({gateway_ping.get('avg_latency'):.0f}ms)"
            })

        # Check external connectivity (ISP)
        external_ok = external_ping.get('reachable', False) and external_ping.get('packet_loss', 100) < 10
        external_latency_ok = external_ping.get('avg_latency') and external_ping.get('avg_latency') < 100

        if gateway_ok and not external_ok:
            issues.append({
                'type': 'isp',
                'severity': 'severe',
                'detail': f"Can't reach internet ({external_ping.get('packet_loss', 100):.0f}% packet loss)"
            })
        elif gateway_ok and external_ok and not external_latency_ok and external_ping.get('avg_latency'):
            issues.append({
                'type': 'isp',
                'severity': 'moderate',
                'detail': f"High internet latency ({external_ping.get('avg_latency'):.0f}ms)"
            })

        # Check DNS
        dns_ok = dns_result.get('resolved', False)
        if external_ok and not dns_ok:
            issues.append({
                'type': 'dns',
                'severity': 'moderate',
                'detail': f"DNS not working ({dns_result.get('error', 'unknown error')})"
            })

        # Determine overall diagnosis
        if not issues:
            return {
                'issue_type': 'none',
                'severity': 'none',
                'status': 'healthy',
                'description': 'Network connection is healthy',
                'recommendation': 'No action needed',
                'details': {
                    'wifi_quality': wifi_quality,
                    'gateway_latency': gateway_ping.get('avg_latency'),
                    'internet_latency': external_ping.get('avg_latency'),
                    'dns_time': dns_result.get('resolve_time_ms')
                }
            }

        # Single issue
        if len(issues) == 1:
            issue = issues[0]
            recommendations = {
                'wifi': 'Move closer to your WiFi router or reduce interference from other devices',
                'router': 'Restart your router. If issue persists, check router settings or contact support',
                'isp': 'Contact your Internet Service Provider - the issue is beyond your local network',
                'dns': 'Try changing DNS servers to 8.8.8.8 (Google) or 1.1.1.1 (Cloudflare)'
            }

            return {
                'issue_type': issue['type'],
                'severity': issue['severity'],
                'status': 'degraded' if issue['severity'] == 'moderate' else 'poor',
                'description': issue['detail'],
                'recommendation': recommendations.get(issue['type'], 'Check your network settings'),
                'details': {
                    'wifi_quality': wifi_quality,
                    'gateway_latency': gateway_ping.get('avg_latency'),
                    'gateway_loss': gateway_ping.get('packet_loss'),
                    'internet_latency': external_ping.get('avg_latency'),
                    'internet_loss': external_ping.get('packet_loss'),
                    'dns_working': dns_ok
                }
            }

        # Multiple issues - find the root cause
        issue_types = [i['type'] for i in issues]
        max_severity = max(i['severity'] for i in issues)

        # WiFi issue usually causes downstream problems
        if 'wifi' in issue_types:
            primary_issue = 'wifi'
            description = 'Weak WiFi signal is likely causing network problems'
            recommendation = 'Fix WiFi signal first - move closer to router or reduce interference'
        elif 'router' in issue_types:
            primary_issue = 'router'
            description = 'Router connectivity issues detected'
            recommendation = 'Restart your router and check connections'
        else:
            primary_issue = 'multiple'
            description = 'Multiple network issues detected: ' + ', '.join(i['detail'] for i in issues)
            recommendation = 'Start by restarting your router, then contact ISP if issues persist'

        return {
            'issue_type': primary_issue,
            'severity': max_severity,
            'status': 'poor',
            'description': description,
            'recommendation': recommendation,
            'all_issues': issues,
            'details': {
                'wifi_quality': wifi_quality,
                'gateway_latency': gateway_ping.get('avg_latency'),
                'gateway_loss': gateway_ping.get('packet_loss'),
                'internet_latency': external_ping.get('avg_latency'),
                'internet_loss': external_ping.get('packet_loss'),
                'dns_working': dns_ok
            }
        }


class WiFiMonitor(BaseNetworkMonitor):
    """Monitor WiFi connection quality and events - Refactored version"""

    def __init__(self):
        # Initialize tracking variables before calling super().__init__()
        self.last_ssid = None
        self.last_diagnosis = None
        self.diagnosis_interval = 120  # Run diagnostics every 2 minutes
        self.last_diagnosis_time = 0

        # Network diagnostics helper
        self.diagnostics = NetworkDiagnostics()

        # Initialize base class
        super().__init__()

        # Initialize CSV loggers (eliminates ~200 lines of duplicated code)
        self.quality_logger = CSVLogger(
            log_file=WIFI_LOG_FILE,
            fieldnames=['timestamp', 'ssid', 'bssid', 'rssi', 'noise', 'snr',
                       'channel', 'tx_rate', 'auth_type', 'quality_score'],
            max_history=60,
            retention_days=7
        )

        self.events_logger = CSVLogger(
            log_file=WIFI_EVENTS_FILE,
            fieldnames=['timestamp', 'event_type', 'ssid', 'bssid', 'details'],
            max_history=100,
            retention_days=7
        )

        self.diag_logger = CSVLogger(
            log_file=NETWORK_DIAG_FILE,
            fieldnames=['timestamp', 'wifi_quality', 'gateway_ip', 'gateway_latency',
                       'gateway_loss', 'internet_latency', 'internet_loss',
                       'dns_working', 'issue_type', 'severity', 'description'],
            max_history=100,
            retention_days=7
        )

        # Initialize last_result with WiFi-specific fields
        self.last_result = {
            'ssid': None,
            'bssid': None,
            'rssi': 0,
            'noise': 0,
            'snr': 0,
            'channel': 0,
            'tx_rate': 0,
            'auth_type': None,
            'status': 'disconnected',
            'quality_score': 0,
            'timestamp': None
        }

    # ==================== BaseNetworkMonitor Abstract Methods ====================

    def get_monitor_name(self) -> str:
        """Return human-readable monitor name"""
        return "WiFi Quality Monitor"

    def get_default_interval(self) -> int:
        """WiFi monitoring interval (increased to 60s to reduce WiFi driver stress)"""
        return 60

    def _run_monitoring_cycle(self):
        """Execute one WiFi monitoring cycle"""
        try:
            self._get_wifi_info()

            # Run network diagnostics periodically
            if time.time() - self.last_diagnosis_time >= self.diagnosis_interval:
                self._run_network_diagnostics()
                self.last_diagnosis_time = time.time()

        except Exception as e:
            logger.error(f"WiFi monitoring error: {e}")
            self._set_disconnected()

    def _on_cleanup(self):
        """Cleanup old logs (called by base class every 24 hours)"""
        # CSVLogger handles its own cleanup automatically
        pass

    # ==================== WiFi-Specific Methods ====================

    def _get_wifi_info(self):
        """Get current WiFi information using system_profiler with caching"""
        try:
            import time as _time

            # Cache system_profiler SPAirPortDataType output to reduce IOKit stress
            # WiFi metrics don't change faster than our 60s polling interval
            now = _time.time()
            cache_ttl = 55  # Just under the 60s monitor interval
            if not hasattr(self, '_sp_wifi_cache'):
                self._sp_wifi_cache = None
                self._sp_wifi_cache_time = 0

            if self._sp_wifi_cache and (now - self._sp_wifi_cache_time) < cache_ttl:
                result_stdout = self._sp_wifi_cache
            else:
                result = subprocess.run(
                    ['system_profiler', 'SPAirPortDataType'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0 or not result.stdout.strip():
                    self._set_disconnected()
                    return
                result_stdout = result.stdout
                self._sp_wifi_cache = result_stdout
                self._sp_wifi_cache_time = now

            # Parse system_profiler output
            bssid = ''
            rssi = -70  # Default moderate signal
            noise = -90  # Default noise floor
            channel = 0
            tx_rate = 0
            auth_type = 'WPA2'
            ssid = None
            is_connected = False

            # Check if connected
            if 'Status: Connected' in result_stdout or 'status: connected' in result_stdout.lower():
                is_connected = True

            if not is_connected:
                self._set_disconnected()
                return

            # Parse current network information
            in_current_network = False

            for line in result_stdout.split('\n'):
                line_stripped = line.strip()

                if 'Current Network Information' in line:
                    in_current_network = True
                    continue

                if 'Other Local Wi-Fi Networks' in line:
                    in_current_network = False
                    continue

                # Extract SSID from system_profiler
                if in_current_network and not ssid:
                    if line_stripped.endswith(':') and ':' not in line_stripped[:-1]:
                        potential_ssid = line_stripped[:-1].strip()
                        known_keys = ['phy mode', 'channel', 'country code', 'network type',
                                     'security', 'signal / noise', 'transmit rate', 'mcs index', 'bssid']
                        if potential_ssid.lower() not in known_keys and len(potential_ssid) > 0:
                            ssid = potential_ssid

                # Parse WiFi metrics
                if ':' in line_stripped:
                    # Handle "Signal / Noise: -48 dBm / -90 dBm"
                    if 'signal / noise' in line_stripped.lower():
                        match = re.search(r'(-?\d+)\s*dBm\s*/\s*(-?\d+)\s*dBm', line_stripped)
                        if match and in_current_network:
                            rssi = int(match.group(1))
                            noise = int(match.group(2))
                        continue

                    key, value = line_stripped.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if in_current_network:
                        if 'channel' in key and '(' in value:
                            try:
                                channel = int(re.search(r'\d+', value).group())
                            except (ValueError, AttributeError):
                                pass
                        elif 'phy mode' in key:
                            if 'ax' in value.lower():
                                tx_rate = 1200  # WiFi 6
                            elif 'ac' in value.lower():
                                tx_rate = 866  # WiFi 5
                            elif 'n' in value.lower():
                                tx_rate = 300  # WiFi 4
                        elif 'transmit rate' in key:
                            try:
                                tx_rate = int(re.search(r'\d+', value).group())
                            except (ValueError, AttributeError):
                                pass
                        elif 'bssid' in key:
                            bssid = value
                        elif 'security' in key or 'network type' in key:
                            if value:
                                auth_type = value

            # Calculate SNR
            snr = rssi - noise if noise != 0 else 0

            # Calculate quality score
            quality_score = self._calculate_quality_score(rssi, snr, noise)

            # macOS privacy feature redacts SSIDs in system_profiler output
            if ssid == '<redacted>':
                ssid = 'WiFi Connected (SSID hidden by macOS)'

            if not ssid:
                ssid = 'WiFi Connected'

            # Check for SSID change (roaming event)
            if self.last_ssid and self.last_ssid != ssid:
                self._log_event('ssid_change', ssid, bssid, f"Changed from {self.last_ssid}")
            elif not self.last_ssid and ssid:
                self._log_event('connect', ssid, bssid, "Connected to network")

            self.last_ssid = ssid

            # Update last result (thread-safe via base class)
            result_data = {
                'ssid': ssid,
                'bssid': bssid,
                'rssi': rssi,
                'noise': noise,
                'snr': snr,
                'channel': channel,
                'tx_rate': tx_rate,
                'auth_type': auth_type,
                'status': 'connected',
                'quality_score': quality_score
            }
            self.update_last_result(result_data)

            # Log to CSV (using shared CSVLogger)
            self.quality_logger.append({
                'timestamp': datetime.now().isoformat(),
                'ssid': ssid,
                'bssid': bssid,
                'rssi': rssi,
                'noise': noise,
                'snr': snr,
                'channel': channel,
                'tx_rate': tx_rate,
                'auth_type': auth_type,
                'quality_score': quality_score
            })

            # Fleet logging (using base class integration)
            if len(self.quality_logger.get_history()) % 6 == 0:
                self.log_to_fleet('wifi_quality', {
                    'signal_strength': quality_score,
                    'noise': noise,
                    'rssi': rssi,
                    'channel': channel,
                    'ssid': ssid,
                    'bssid': bssid,
                    'snr': snr,
                    'tx_rate': tx_rate,
                    'quality_score': quality_score
                })

        except subprocess.TimeoutExpired:
            self._set_disconnected()
        except Exception as e:
            logger.error(f"Failed to get WiFi info: {e}")
            self._set_disconnected()

    def _calculate_quality_score(self, rssi: int, snr: int, noise: int) -> int:
        """Calculate WiFi quality score (0-100)"""
        score = 100

        # RSSI scoring
        if rssi >= -50:
            score = 100
        elif rssi >= -60:
            score = 90
        elif rssi >= -67:
            score = 75
        elif rssi >= -70:
            score = 60
        elif rssi >= -80:
            score = 40
        else:
            score = 20

        # SNR adjustment
        if snr >= 40:
            score = min(100, score + 10)
        elif snr < 20:
            score = max(0, score - 20)

        return int(score)

    def _set_disconnected(self):
        """Set status to disconnected or show Ethernet if available"""
        if self.last_result.get('status') == 'connected':
            # Log disconnect event
            self._log_event('disconnect', self.last_result.get('ssid'),
                          self.last_result.get('bssid'), 'Connection lost')
            self.last_ssid = None

        # Check if using Ethernet
        ethernet_info = self._check_ethernet_connection()

        if ethernet_info:
            self.update_last_result({
                'ssid': f"Ethernet ({ethernet_info['interface']})",
                'bssid': None,
                'rssi': 0,
                'noise': 0,
                'snr': 0,
                'channel': 0,
                'tx_rate': 0,
                'auth_type': None,
                'status': 'ethernet',
                'quality_score': 100,
                'connection_type': 'ethernet',
                'ethernet_ip': ethernet_info['ip_address'],
                'ethernet_speed': ethernet_info['speed']
            })
        else:
            self.update_last_result({
                'ssid': 'Not Connected',
                'bssid': None,
                'rssi': 0,
                'noise': 0,
                'snr': 0,
                'channel': 0,
                'tx_rate': 0,
                'auth_type': None,
                'status': 'disconnected',
                'quality_score': 0,
                'connection_type': 'none'
            })

    def _check_ethernet_connection(self) -> Optional[Dict[str, Any]]:
        """Check if there's an active Ethernet connection"""
        try:
            result = subprocess.run(
                ['networksetup', '-listallhardwareports'],
                capture_output=True,
                text=True,
                timeout=5
            )

            ethernet_interfaces = []
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if any(x in line for x in ['Ethernet', 'Thunderbolt', 'USB 10/100/1000 LAN', 'USB Ethernet']):
                    if i + 1 < len(lines):
                        device_line = lines[i + 1]
                        if 'Device:' in device_line:
                            interface = device_line.split('Device:')[1].strip()
                            ethernet_interfaces.append(interface)

            # Check each Ethernet interface
            for interface in ethernet_interfaces:
                try:
                    result = subprocess.run(
                        ['ifconfig', interface],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if 'status: active' in result.stdout and 'inet ' in result.stdout:
                        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                        ip_address = ip_match.group(1) if ip_match else 'Unknown'

                        speed = 'Unknown'
                        try:
                            speed_result = subprocess.run(
                                ['networksetup', '-getMedia', interface],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if speed_result.returncode == 0:
                                speed_match = re.search(r'(\d+)base', speed_result.stdout)
                                if speed_match:
                                    speed = f"{speed_match.group(1)} Mbps"
                        except (subprocess.SubprocessError, OSError, TimeoutError):
                            pass

                        return {
                            'interface': interface,
                            'ip_address': ip_address,
                            'speed': speed,
                            'type': 'ethernet'
                        }
                except (subprocess.SubprocessError, OSError, KeyError):
                    continue

            return None
        except Exception as e:
            logger.debug(f"Ethernet check failed: {e}")
            return None

    def _log_event(self, event_type: str, ssid: str, bssid: str, details: str):
        """Log WiFi events using shared CSVLogger"""
        try:
            self.events_logger.append({
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'ssid': ssid or '',
                'bssid': bssid or '',
                'details': details
            })
            logger.info(f"WiFi event: {event_type} - {details}")
        except Exception as e:
            logger.error(f"Failed to log event: {e}")

    def _run_network_diagnostics(self):
        """Run network diagnostics to identify connection issues"""
        try:
            wifi_quality = self.last_result.get('quality_score', 0)

            # Get default gateway
            gateway = NetworkDiagnostics.get_default_gateway()

            # Ping gateway (router)
            if gateway:
                gateway_ping = NetworkDiagnostics.ping_host(gateway, count=3, timeout=2)
            else:
                gateway_ping = {'reachable': False, 'packet_loss': 100, 'avg_latency': None}

            # Ping external (Google DNS)
            external_ping = NetworkDiagnostics.ping_host('8.8.8.8', count=3, timeout=2)

            # Test DNS
            dns_result = NetworkDiagnostics.test_dns_resolution('google.com', timeout=3)

            # Run diagnosis
            diagnosis = NetworkDiagnostics.diagnose_network_issue(
                wifi_quality=wifi_quality,
                gateway_ping=gateway_ping,
                external_ping=external_ping,
                dns_result=dns_result
            )

            # Add raw test results
            diagnosis['gateway_ip'] = gateway
            diagnosis['gateway_ping'] = gateway_ping
            diagnosis['external_ping'] = external_ping
            diagnosis['dns_result'] = dns_result
            diagnosis['timestamp'] = datetime.now().isoformat()

            # Store diagnosis
            self.last_diagnosis = diagnosis

            # Log issues
            if diagnosis['issue_type'] != 'none':
                logger.info(f"Network diagnosis: {diagnosis['issue_type']} - {diagnosis['description']}")
                self._log_event(
                    f"network_{diagnosis['issue_type']}",
                    self.last_result.get('ssid'),
                    self.last_result.get('bssid'),
                    diagnosis['description']
                )

            # Log to CSV using shared CSVLogger
            details = diagnosis.get('details', {})
            self.diag_logger.append({
                'timestamp': diagnosis.get('timestamp', datetime.now().isoformat()),
                'wifi_quality': details.get('wifi_quality', 0),
                'gateway_ip': gateway or '',
                'gateway_latency': details.get('gateway_latency') or '',
                'gateway_loss': details.get('gateway_loss') or '',
                'internet_latency': details.get('internet_latency') or '',
                'internet_loss': details.get('internet_loss') or '',
                'dns_working': details.get('dns_working', False),
                'issue_type': diagnosis.get('issue_type', 'unknown'),
                'severity': diagnosis.get('severity', 'unknown'),
                'description': diagnosis.get('description', '')
            })

        except Exception as e:
            logger.error(f"Network diagnostics failed: {e}")

    # ==================== Public API Methods ====================

    def get_history(self) -> List[Dict[str, Any]]:
        """Get WiFi quality history from CSV logger"""
        history = self.quality_logger.get_history()
        # Convert to simplified format for graph
        return [{
            'rssi': int(row.get('rssi', 0)),
            'quality_score': int(row.get('quality_score', 0)),
            'timestamp': row.get('timestamp', '')
        } for row in history]

    def run_diagnostics_now(self) -> Dict[str, Any]:
        """Run network diagnostics immediately and return results"""
        self._run_network_diagnostics()
        return self.last_diagnosis or {'error': 'No diagnosis available'}

    def get_last_diagnosis(self) -> Optional[Dict[str, Any]]:
        """Get the last network diagnosis result"""
        return self.last_diagnosis


# Global WiFi monitor instance (singleton pattern)
_wifi_monitor = None


def get_wifi_monitor() -> WiFiMonitor:
    """Get or create the global WiFi monitor"""
    global _wifi_monitor
    if _wifi_monitor is None:
        _wifi_monitor = WiFiMonitor()
    return _wifi_monitor
