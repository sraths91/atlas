"""
OSI Layers Network Diagnostic Monitor

Tests each of the 7 OSI layers to identify which layer is causing
network issues. Displays pass/warning/fail status per layer with
a waterfall effect (lower-layer failures block higher layers).

Layer 1 - Physical:    Interface status, WiFi signal, link speed
Layer 2 - Data Link:   ARP resolution, interface errors, MAC address
Layer 3 - Network:     IP config, gateway ping, external ping
Layer 4 - Transport:   TCP connection tests, connection timing
Layer 5 - Session:     HTTP keep-alive, persistent connection test
Layer 6 - Presentation: TLS handshake, certificate validation
Layer 7 - Application: DNS resolution, HTTP request, status check
"""

import logging
import platform
import re
import socket
import ssl
import struct
import subprocess
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from atlas.network.monitors.base import BaseNetworkMonitor

logger = logging.getLogger(__name__)


# ==================== Data Structures ====================

class LayerStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    BLOCKED = "blocked"
    TESTING = "testing"
    UNKNOWN = "unknown"


@dataclass
class LayerTestResult:
    """Result of a single sub-test within an OSI layer."""
    name: str
    status: str  # LayerStatus value
    value: Optional[str] = None
    latency_ms: Optional[float] = None
    detail: str = ""
    error: Optional[str] = None


@dataclass
class LayerResult:
    """Result for one OSI layer (aggregates sub-tests)."""
    layer_number: int
    layer_name: str
    status: str = "unknown"
    tests: List[dict] = field(default_factory=list)
    summary: str = ""
    latency_ms: Optional[float] = None


@dataclass
class OSIDiagnosticResult:
    """Complete result for all 7 layers."""
    timestamp: str = ""
    overall_status: str = "unknown"
    health_score: int = 0
    layers: List[dict] = field(default_factory=list)
    duration_ms: float = 0.0
    blocked_above: Optional[int] = None
    qoe: dict = field(default_factory=dict)
    cloudflare_trace: dict = field(default_factory=dict)


# ==================== Health Score Weights ====================

LAYER_WEIGHTS = {1: 20, 2: 15, 3: 20, 4: 15, 5: 5, 6: 10, 7: 15}

# ==================== Thresholds ====================

RSSI_GOOD = -60
RSSI_WARN = -75
GATEWAY_PING_WARN_MS = 50
EXTERNAL_PING_WARN_MS = 100
TCP_CONNECT_WARN_MS = 300
TLS_HANDSHAKE_WARN_MS = 500
DNS_RESOLVE_WARN_MS = 200
HTTP_RESPONSE_WARN_MS = 1000

# Captive portal check URLs
CAPTIVE_PORTAL_CHECKS = [
    {'name': 'Apple', 'url': 'http://captive.apple.com/hotspot-detect.html',
     'expect_body': 'Success'},
    {'name': 'Google', 'url': 'http://www.gstatic.com/generate_204',
     'expect_status': 204},
    {'name': 'Microsoft', 'url': 'http://www.msftconnecttest.com/connecttest.txt',
     'expect_body': 'Microsoft Connect Test'},
]

# SaaS endpoints to test
SAAS_ENDPOINTS = [
    {'name': 'Slack', 'url': 'https://slack.com/api/api.test'},
    {'name': 'Google', 'url': 'https://www.googleapis.com/discovery/v1/apis'},
    {'name': 'GitHub', 'url': 'https://api.github.com/'},
]

# Commonly blocked ports for firewall detection
FIREWALL_TEST_PORTS = [
    {'name': 'SSH', 'host': 'github.com', 'port': 22},
    {'name': 'SMTP', 'host': 'smtp.gmail.com', 'port': 25},
    {'name': 'STUN', 'host': 'stun.l.google.com', 'port': 3478},
]

# Video conferencing requirements (published minimums for HD group calls)
VIDEO_CONF_REQUIREMENTS = {
    'zoom': {'latency_ms': 150, 'jitter_ms': 40},
    'teams': {'latency_ms': 100, 'jitter_ms': 30},
    'meet': {'latency_ms': 100, 'jitter_ms': 30},
}

# MTU binary search
MTU_TEST_TARGET = '8.8.8.8'


class OSIDiagnosticMonitor(BaseNetworkMonitor):
    """Monitor that tests all 7 OSI layers for network diagnostics."""

    def __init__(self):
        super().__init__()
        self._diagnostic_lock = threading.Lock()
        logger.info("OSI Diagnostic Monitor initialized")

    def get_monitor_name(self) -> str:
        return "OSI Diagnostic Monitor"

    def get_default_interval(self) -> int:
        return 300  # 5 minutes

    def _run_monitoring_cycle(self):
        """Execute one full OSI diagnostic cycle."""
        result = self.run_diagnostic()
        self.update_last_result(asdict(result))

    def run_diagnostic(self) -> OSIDiagnosticResult:
        """Run full 7-layer diagnostic. Thread-safe for on-demand calls."""
        with self._diagnostic_lock:
            start = time.time()

            layers = []
            layers.append(self._test_layer1_physical())
            layers.append(self._test_layer2_data_link())
            layers.append(self._test_layer3_network())
            layers.append(self._test_layer4_transport())
            layers.append(self._test_layer5_session())
            layers.append(self._test_layer6_presentation())
            layers.append(self._test_layer7_application())

            # Convert LayerResult objects to dicts
            layer_dicts = [asdict(l) for l in layers]

            # Apply waterfall: lower-layer failure blocks higher layers
            blocked_above = self._apply_waterfall(layer_dicts)

            health_score = self._calculate_health_score(layer_dicts)

            # Determine overall status
            statuses = [l['status'] for l in layer_dicts]
            if LayerStatus.FAIL.value in statuses:
                overall = LayerStatus.FAIL.value
            elif LayerStatus.WARNING.value in statuses:
                overall = LayerStatus.WARNING.value
            else:
                overall = LayerStatus.PASS.value

            # QoE summary and Cloudflare trace
            qoe = self._compute_qoe_summary(layer_dicts)
            cf_trace = self._fetch_cloudflare_trace()

            duration = round((time.time() - start) * 1000, 1)

            return OSIDiagnosticResult(
                timestamp=datetime.now().isoformat(),
                overall_status=overall,
                health_score=health_score,
                layers=layer_dicts,
                duration_ms=duration,
                blocked_above=blocked_above,
                qoe=qoe,
                cloudflare_trace=cf_trace
            )

    # ==================== Waterfall & Scoring ====================

    def _apply_waterfall(self, layers: List[dict]) -> Optional[int]:
        """If a lower layer fails, mark all higher layers as BLOCKED."""
        sorted_layers = sorted(layers, key=lambda l: l['layer_number'])
        lowest_fail = None

        for layer in sorted_layers:
            if layer['status'] == LayerStatus.FAIL.value:
                lowest_fail = layer['layer_number']
                break

        if lowest_fail is not None:
            for layer in layers:
                if layer['layer_number'] > lowest_fail:
                    layer['status'] = LayerStatus.BLOCKED.value
                    layer['summary'] = f"Blocked by Layer {lowest_fail} failure"

        return lowest_fail

    def _calculate_health_score(self, layers: List[dict]) -> int:
        """Calculate 0-100 health score based on layer results."""
        score = 0
        for layer in layers:
            weight = LAYER_WEIGHTS.get(layer['layer_number'], 10)
            status = layer['status']
            if status == LayerStatus.PASS.value:
                score += weight
            elif status == LayerStatus.WARNING.value:
                score += weight * 0.6
        return round(score)

    # ==================== Layer 1: Physical ====================

    def _test_layer1_physical(self) -> LayerResult:
        """Test physical layer: interface status, signal strength, link speed."""
        tests = []
        layer = LayerResult(layer_number=1, layer_name="Physical")

        # Test 1: Interface status
        tests.append(self._test_interface_status())

        # Test 2: WiFi signal strength (reuse WiFi monitor if available)
        tests.append(self._test_wifi_signal())

        # Test 3: Link speed
        tests.append(self._test_link_speed())

        layer.tests = [asdict(t) for t in tests]
        layer.status = self._aggregate_status(tests)
        layer.summary = self._build_summary(tests)
        return layer

    def _test_interface_status(self) -> LayerTestResult:
        """Check if the primary network interface is up and active."""
        try:
            result = subprocess.run(
                ['ifconfig'], capture_output=True, text=True, timeout=5
            )
            # Find active interfaces
            active_ifaces = []
            current_iface = None
            for line in result.stdout.split('\n'):
                if not line.startswith('\t') and ':' in line:
                    current_iface = line.split(':')[0]
                if current_iface and 'status: active' in line:
                    if current_iface.startswith('en'):
                        active_ifaces.append(current_iface)

            if active_ifaces:
                iface = active_ifaces[0]
                conn_type = "Ethernet" if iface == "en0" else "WiFi"
                # On modern Macs, en0 is usually WiFi
                if platform.system() == 'Darwin':
                    conn_type = "WiFi" if iface == "en0" else "Ethernet"
                return LayerTestResult(
                    name="Interface Status",
                    status=LayerStatus.PASS.value,
                    value=f"{iface} active",
                    detail=f"{conn_type} interface is up and active"
                )
            else:
                return LayerTestResult(
                    name="Interface Status",
                    status=LayerStatus.FAIL.value,
                    value="No active interface",
                    detail="No active network interface found",
                    error="All interfaces are down"
                )
        except Exception as e:
            return LayerTestResult(
                name="Interface Status",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    def _test_wifi_signal(self) -> LayerTestResult:
        """Check WiFi signal strength, reusing WiFi monitor data if fresh."""
        try:
            # Try reusing WiFi monitor data
            rssi = None
            try:
                from atlas.network.monitors.wifi import get_wifi_monitor
                wifi = get_wifi_monitor()
                data = wifi.get_last_result()
                ts = data.get('timestamp')
                if ts and (time.time() - _parse_timestamp(ts)) < 300:
                    rssi = data.get('rssi')
                    ssid = data.get('ssid', 'Unknown')
                    if rssi is not None:
                        quality = "Excellent" if rssi >= -50 else \
                                  "Good" if rssi >= RSSI_GOOD else \
                                  "Fair" if rssi >= RSSI_WARN else "Poor"
                        status = LayerStatus.PASS.value if rssi >= RSSI_GOOD else \
                                 LayerStatus.WARNING.value if rssi >= RSSI_WARN else \
                                 LayerStatus.FAIL.value
                        return LayerTestResult(
                            name="Signal Strength",
                            status=status,
                            value=f"{rssi} dBm",
                            detail=f"RSSI {rssi} dBm on {ssid} ({quality})"
                        )
            except (ImportError, Exception):
                pass

            # Fallback: try airport CLI then system_profiler
            if platform.system() == 'Darwin':
                airport_path = ('/System/Library/PrivateFrameworks/'
                                'Apple80211.framework/Versions/Current/'
                                'Resources/airport')
                try:
                    result = subprocess.run(
                        [airport_path, '-I'],
                        capture_output=True, text=True, timeout=5
                    )
                    for line in result.stdout.split('\n'):
                        if 'agrCtlRSSI' in line:
                            rssi = int(line.split(':')[1].strip())
                            break
                except FileNotFoundError:
                    pass

                # macOS 14+ removed airport — use system_profiler
                if rssi is None:
                    result = subprocess.run(
                        ['system_profiler', 'SPAirPortDataType'],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.split('\n'):
                        if 'Signal / Noise' in line:
                            import re
                            m = re.search(r'(-\d+)\s*/\s*(-?\d+)', line)
                            if m:
                                rssi = int(m.group(1))
                            break

                if rssi is not None:
                    status = LayerStatus.PASS.value if rssi >= RSSI_GOOD else \
                             LayerStatus.WARNING.value if rssi >= RSSI_WARN else \
                             LayerStatus.FAIL.value
                    quality = "Excellent" if rssi >= -50 else \
                              "Good" if rssi >= RSSI_GOOD else \
                              "Fair" if rssi >= RSSI_WARN else "Poor"
                    return LayerTestResult(
                        name="Signal Strength",
                        status=status,
                        value=f"{rssi} dBm",
                        detail=f"RSSI {rssi} dBm ({quality})"
                    )

            # Not WiFi or can't read signal
            return LayerTestResult(
                name="Signal Strength",
                status=LayerStatus.PASS.value,
                value="N/A (wired)",
                detail="Wired connection — signal strength not applicable"
            )
        except Exception as e:
            return LayerTestResult(
                name="Signal Strength",
                status=LayerStatus.WARNING.value,
                value="Unknown",
                detail=f"Could not determine signal strength: {e}",
                error=str(e)
            )

    def _test_link_speed(self) -> LayerTestResult:
        """Check the negotiated link speed."""
        try:
            # Try WiFi monitor data first
            try:
                from atlas.network.monitors.wifi import get_wifi_monitor
                wifi = get_wifi_monitor()
                data = wifi.get_last_result()
                tx_rate = data.get('tx_rate')
                if tx_rate:
                    speed_mbps = float(str(tx_rate).replace(' Mbps', '').replace('Mbps', ''))
                    status = LayerStatus.PASS.value if speed_mbps >= 100 else \
                             LayerStatus.WARNING.value if speed_mbps >= 10 else \
                             LayerStatus.FAIL.value
                    return LayerTestResult(
                        name="Link Speed",
                        status=status,
                        value=f"{int(speed_mbps)} Mbps",
                        detail=f"Negotiated link speed: {int(speed_mbps)} Mbps"
                    )
            except (ImportError, ValueError, Exception):
                pass

            # Fallback: parse ifconfig for media speed
            if platform.system() == 'Darwin':
                result = subprocess.run(
                    ['ifconfig', 'en0'], capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'media:' in line.lower():
                        return LayerTestResult(
                            name="Link Speed",
                            status=LayerStatus.PASS.value,
                            value="Connected",
                            detail=f"Media: {line.strip()}"
                        )

            return LayerTestResult(
                name="Link Speed",
                status=LayerStatus.PASS.value,
                value="Unknown",
                detail="Could not determine link speed"
            )
        except Exception as e:
            return LayerTestResult(
                name="Link Speed",
                status=LayerStatus.WARNING.value,
                error=str(e)
            )

    # ==================== Layer 2: Data Link ====================

    def _test_layer2_data_link(self) -> LayerResult:
        """Test data link layer: ARP, errors, MAC address."""
        tests = []
        layer = LayerResult(layer_number=2, layer_name="Data Link")

        tests.append(self._test_arp_resolution())
        tests.append(self._test_interface_errors())
        tests.append(self._test_mac_address())

        layer.tests = [asdict(t) for t in tests]
        layer.status = self._aggregate_status(tests)
        layer.summary = self._build_summary(tests)
        return layer

    def _test_arp_resolution(self) -> LayerTestResult:
        """Test if gateway MAC can be resolved via ARP."""
        try:
            from atlas.network.monitors.wifi import NetworkDiagnostics
            gateway = NetworkDiagnostics.get_default_gateway()

            if not gateway:
                return LayerTestResult(
                    name="ARP Resolution",
                    status=LayerStatus.FAIL.value,
                    value="No gateway",
                    detail="Cannot find default gateway",
                    error="No default gateway configured"
                )

            result = subprocess.run(
                ['arp', '-n', gateway],
                capture_output=True, text=True, timeout=5
            )

            # Parse ARP output for MAC address
            mac_match = re.search(
                r'([0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2}:'
                r'[0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2}:[0-9a-fA-F]{1,2})',
                result.stdout
            )

            if mac_match and 'incomplete' not in result.stdout.lower():
                mac = mac_match.group(1)
                return LayerTestResult(
                    name="ARP Resolution",
                    status=LayerStatus.PASS.value,
                    value=mac,
                    detail=f"Gateway {gateway} resolved to {mac}"
                )
            else:
                return LayerTestResult(
                    name="ARP Resolution",
                    status=LayerStatus.FAIL.value,
                    value="Incomplete",
                    detail=f"ARP for gateway {gateway} is incomplete",
                    error="Cannot resolve gateway MAC address"
                )
        except Exception as e:
            return LayerTestResult(
                name="ARP Resolution",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    def _test_interface_errors(self) -> LayerTestResult:
        """Check for interface errors and collisions."""
        try:
            result = subprocess.run(
                ['netstat', '-i'], capture_output=True, text=True, timeout=5
            )

            # Parse netstat output for en0 errors
            for line in result.stdout.split('\n'):
                parts = line.split()
                if len(parts) >= 7 and parts[0].startswith('en'):
                    iface = parts[0]
                    try:
                        # netstat -i columns: Name Mtu Network Address Ipkts Ierrs Opkts Oerrs Coll
                        ierrs = int(parts[5]) if parts[5].isdigit() else 0
                        oerrs = int(parts[7]) if len(parts) > 7 and parts[7].isdigit() else 0
                        total_errors = ierrs + oerrs

                        if total_errors == 0:
                            return LayerTestResult(
                                name="Interface Errors",
                                status=LayerStatus.PASS.value,
                                value="0 errors",
                                detail=f"{iface}: no input/output errors"
                            )
                        elif total_errors < 100:
                            return LayerTestResult(
                                name="Interface Errors",
                                status=LayerStatus.WARNING.value,
                                value=f"{total_errors} errors",
                                detail=f"{iface}: {ierrs} input, {oerrs} output errors"
                            )
                        else:
                            return LayerTestResult(
                                name="Interface Errors",
                                status=LayerStatus.FAIL.value,
                                value=f"{total_errors} errors",
                                detail=f"{iface}: {ierrs} input, {oerrs} output errors (high)",
                                error="High error count on interface"
                            )
                    except (ValueError, IndexError):
                        continue

            return LayerTestResult(
                name="Interface Errors",
                status=LayerStatus.PASS.value,
                value="OK",
                detail="No error data available (likely clean)"
            )
        except Exception as e:
            return LayerTestResult(
                name="Interface Errors",
                status=LayerStatus.WARNING.value,
                error=str(e)
            )

    def _test_mac_address(self) -> LayerTestResult:
        """Verify the interface has a valid MAC address."""
        try:
            result = subprocess.run(
                ['ifconfig', 'en0'], capture_output=True, text=True, timeout=5
            )
            mac_match = re.search(
                r'ether\s+([0-9a-fA-F:]{17})', result.stdout
            )
            if mac_match:
                mac = mac_match.group(1)
                # Check for all-zeros (invalid)
                if mac == '00:00:00:00:00:00':
                    return LayerTestResult(
                        name="MAC Address",
                        status=LayerStatus.FAIL.value,
                        value=mac,
                        detail="All-zero MAC address (invalid)",
                        error="Invalid MAC address"
                    )
                return LayerTestResult(
                    name="MAC Address",
                    status=LayerStatus.PASS.value,
                    value=mac,
                    detail="Valid MAC address present"
                )
            return LayerTestResult(
                name="MAC Address",
                status=LayerStatus.WARNING.value,
                value="Not found",
                detail="Could not read MAC address from en0"
            )
        except Exception as e:
            return LayerTestResult(
                name="MAC Address",
                status=LayerStatus.WARNING.value,
                error=str(e)
            )

    # ==================== Layer 3: Network ====================

    def _test_layer3_network(self) -> LayerResult:
        """Test network layer: IP config, gateway ping, external ping."""
        tests = []
        layer = LayerResult(layer_number=3, layer_name="Network")

        tests.append(self._test_ip_configuration())
        tests.append(self._test_ping_gateway())
        tests.append(self._test_ping_external())
        tests.append(self._test_ipv6_connectivity())
        tests.append(self._test_mtu_path_discovery())

        layer.tests = [asdict(t) for t in tests]
        layer.status = self._aggregate_status(tests)
        layer.summary = self._build_summary(tests)
        # Use external ping latency as the layer latency
        for t in tests:
            if t.latency_ms and t.name == "External Ping":
                layer.latency_ms = t.latency_ms
        return layer

    def _test_ip_configuration(self) -> LayerTestResult:
        """Check if IP, subnet, and gateway are properly configured."""
        try:
            result = subprocess.run(
                ['ifconfig', 'en0'], capture_output=True, text=True, timeout=5
            )

            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
            mask_match = re.search(r'netmask\s+(0x[0-9a-f]+)', result.stdout)

            from atlas.network.monitors.wifi import NetworkDiagnostics
            gateway = NetworkDiagnostics.get_default_gateway()

            if ip_match and gateway:
                ip_addr = ip_match.group(1)
                return LayerTestResult(
                    name="IP Configuration",
                    status=LayerStatus.PASS.value,
                    value=ip_addr,
                    detail=f"IP {ip_addr}, gateway {gateway}"
                )
            elif ip_match:
                return LayerTestResult(
                    name="IP Configuration",
                    status=LayerStatus.WARNING.value,
                    value=ip_match.group(1),
                    detail="IP assigned but no default gateway"
                )
            else:
                return LayerTestResult(
                    name="IP Configuration",
                    status=LayerStatus.FAIL.value,
                    value="No IP",
                    detail="No IP address assigned to en0",
                    error="DHCP may have failed"
                )
        except Exception as e:
            return LayerTestResult(
                name="IP Configuration",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    def _test_ping_gateway(self) -> LayerTestResult:
        """Ping the default gateway."""
        try:
            from atlas.network.monitors.wifi import NetworkDiagnostics
            gateway = NetworkDiagnostics.get_default_gateway()

            if not gateway:
                return LayerTestResult(
                    name="Gateway Ping",
                    status=LayerStatus.FAIL.value,
                    value="No gateway",
                    error="No default gateway to ping"
                )

            ping_result = NetworkDiagnostics.ping_host(gateway, count=3, timeout=2)

            if ping_result['reachable']:
                latency = ping_result.get('avg_latency')
                status = LayerStatus.PASS.value if (latency and latency < GATEWAY_PING_WARN_MS) else \
                         LayerStatus.WARNING.value
                return LayerTestResult(
                    name="Gateway Ping",
                    status=status,
                    value=f"{latency:.1f} ms" if latency else "OK",
                    latency_ms=latency,
                    detail=f"Gateway {gateway} reachable, {ping_result['packet_loss']}% loss"
                )
            else:
                return LayerTestResult(
                    name="Gateway Ping",
                    status=LayerStatus.FAIL.value,
                    value="Unreachable",
                    detail=f"Gateway {gateway} is not responding",
                    error="Gateway unreachable"
                )
        except Exception as e:
            return LayerTestResult(
                name="Gateway Ping",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    def _test_ping_external(self) -> LayerTestResult:
        """Ping external host (8.8.8.8). Reuse Ping monitor if fresh."""
        try:
            # Try reusing ping monitor data
            latency = None
            try:
                from atlas.network.monitors.ping import get_ping_monitor
                ping_mon = get_ping_monitor()
                data = ping_mon.get_last_result()
                ts = data.get('timestamp')
                if ts and (time.time() - _parse_timestamp(ts)) < 15:
                    if data.get('status') == 'success':
                        latency = data.get('latency')
                        if latency is not None:
                            status = LayerStatus.PASS.value if latency < EXTERNAL_PING_WARN_MS else \
                                     LayerStatus.WARNING.value
                            return LayerTestResult(
                                name="External Ping",
                                status=status,
                                value=f"{latency:.1f} ms",
                                latency_ms=round(latency, 1),
                                detail=f"8.8.8.8 reachable in {latency:.1f}ms (cached)"
                            )
            except (ImportError, Exception):
                pass

            # Fallback: run our own ping
            from atlas.network.monitors.wifi import NetworkDiagnostics
            ping_result = NetworkDiagnostics.ping_host('8.8.8.8', count=3, timeout=2)

            if ping_result['reachable']:
                latency = ping_result.get('avg_latency')
                status = LayerStatus.PASS.value if (latency and latency < EXTERNAL_PING_WARN_MS) else \
                         LayerStatus.WARNING.value
                return LayerTestResult(
                    name="External Ping",
                    status=status,
                    value=f"{latency:.1f} ms" if latency else "OK",
                    latency_ms=round(latency, 1) if latency else None,
                    detail=f"8.8.8.8 reachable, {ping_result['packet_loss']}% loss"
                )
            else:
                return LayerTestResult(
                    name="External Ping",
                    status=LayerStatus.FAIL.value,
                    value="Unreachable",
                    detail="8.8.8.8 is not responding — internet may be down",
                    error="External host unreachable"
                )
        except Exception as e:
            return LayerTestResult(
                name="External Ping",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    # ==================== Layer 4: Transport ====================

    def _test_layer4_transport(self) -> LayerResult:
        """Test transport layer: TCP connections."""
        tests = []
        layer = LayerResult(layer_number=4, layer_name="Transport")

        tests.append(self._test_tcp_connect('8.8.8.8', 443))
        tests.append(self._test_tcp_connect('1.1.1.1', 443))
        tests.append(self._test_port_blocking())

        layer.tests = [asdict(t) for t in tests]
        layer.status = self._aggregate_status(tests)
        layer.summary = self._build_summary(tests)
        # Use the first successful latency
        for t in tests:
            if t.latency_ms:
                layer.latency_ms = t.latency_ms
                break
        return layer

    def _test_tcp_connect(self, host: str, port: int) -> LayerTestResult:
        """Test TCP connection to a specific host:port."""
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            elapsed_ms = round((time.time() - start) * 1000, 1)
            sock.close()

            status = LayerStatus.PASS.value if elapsed_ms < TCP_CONNECT_WARN_MS else \
                     LayerStatus.WARNING.value
            return LayerTestResult(
                name=f"TCP to {host}:{port}",
                status=status,
                value="Connected",
                latency_ms=elapsed_ms,
                detail=f"TCP established in {elapsed_ms}ms"
            )
        except socket.timeout:
            return LayerTestResult(
                name=f"TCP to {host}:{port}",
                status=LayerStatus.FAIL.value,
                value="Timeout",
                detail=f"TCP connection to {host}:{port} timed out",
                error="Connection timed out"
            )
        except ConnectionRefusedError:
            return LayerTestResult(
                name=f"TCP to {host}:{port}",
                status=LayerStatus.FAIL.value,
                value="Refused",
                detail=f"TCP connection to {host}:{port} refused",
                error="Connection refused"
            )
        except Exception as e:
            return LayerTestResult(
                name=f"TCP to {host}:{port}",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    # ==================== Layer 5: Session ====================

    def _test_layer5_session(self) -> LayerResult:
        """Test session layer: HTTP keep-alive, persistent connections."""
        tests = []
        layer = LayerResult(layer_number=5, layer_name="Session")

        tests.append(self._test_http_keepalive())

        layer.tests = [asdict(t) for t in tests]
        layer.status = self._aggregate_status(tests)
        layer.summary = self._build_summary(tests)
        for t in tests:
            if t.latency_ms:
                layer.latency_ms = t.latency_ms
        return layer

    def _test_http_keepalive(self) -> LayerTestResult:
        """Test HTTP keep-alive by sending two requests on one connection."""
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('www.google.com', 80))

            # First request
            request1 = (
                b"HEAD / HTTP/1.1\r\n"
                b"Host: www.google.com\r\n"
                b"Connection: keep-alive\r\n\r\n"
            )
            sock.sendall(request1)
            response1 = sock.recv(4096)

            if b'HTTP/' not in response1:
                sock.close()
                return LayerTestResult(
                    name="HTTP Keep-Alive",
                    status=LayerStatus.FAIL.value,
                    value="No response",
                    detail="First request got no HTTP response",
                    error="Invalid HTTP response"
                )

            # Second request on same connection (tests keep-alive)
            request2 = (
                b"HEAD / HTTP/1.1\r\n"
                b"Host: www.google.com\r\n"
                b"Connection: close\r\n\r\n"
            )
            sock.sendall(request2)
            response2 = sock.recv(4096)
            elapsed_ms = round((time.time() - start) * 1000, 1)
            sock.close()

            if b'HTTP/' in response2:
                return LayerTestResult(
                    name="HTTP Keep-Alive",
                    status=LayerStatus.PASS.value,
                    value="Keep-Alive OK",
                    latency_ms=elapsed_ms,
                    detail=f"2 requests on single connection in {elapsed_ms}ms"
                )
            else:
                return LayerTestResult(
                    name="HTTP Keep-Alive",
                    status=LayerStatus.WARNING.value,
                    value="Partial",
                    latency_ms=elapsed_ms,
                    detail="First request OK, keep-alive may not be supported"
                )
        except Exception as e:
            return LayerTestResult(
                name="HTTP Keep-Alive",
                status=LayerStatus.FAIL.value,
                detail=f"Keep-alive test failed: {e}",
                error=str(e)
            )

    # ==================== Layer 6: Presentation ====================

    def _test_layer6_presentation(self) -> LayerResult:
        """Test presentation layer: TLS handshake, certificate validation."""
        tests = []
        layer = LayerResult(layer_number=6, layer_name="Presentation")

        tests.append(self._test_tls_handshake())
        tests.append(self._test_certificate_validation())
        tests.append(self._test_dns_over_https())

        layer.tests = [asdict(t) for t in tests]
        layer.status = self._aggregate_status(tests)
        layer.summary = self._build_summary(tests)
        for t in tests:
            if t.latency_ms:
                layer.latency_ms = t.latency_ms
                break
        return layer

    def _test_tls_handshake(self) -> LayerTestResult:
        """Test TLS handshake to google.com:443."""
        try:
            context = ssl.create_default_context()
            start = time.time()
            with socket.create_connection(('www.google.com', 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname='www.google.com') as ssock:
                    elapsed_ms = round((time.time() - start) * 1000, 1)
                    tls_version = ssock.version()
                    cipher = ssock.cipher()
                    cipher_name = cipher[0] if cipher else "Unknown"

            status = LayerStatus.PASS.value if elapsed_ms < TLS_HANDSHAKE_WARN_MS else \
                     LayerStatus.WARNING.value
            return LayerTestResult(
                name="TLS Handshake",
                status=status,
                value=tls_version or "TLS",
                latency_ms=elapsed_ms,
                detail=f"{tls_version} with {cipher_name} in {elapsed_ms}ms"
            )
        except ssl.SSLCertVerificationError as e:
            return LayerTestResult(
                name="TLS Handshake",
                status=LayerStatus.FAIL.value,
                value="Cert Error",
                detail="Certificate verification failed",
                error=str(e)
            )
        except Exception as e:
            return LayerTestResult(
                name="TLS Handshake",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    def _test_certificate_validation(self) -> LayerTestResult:
        """Validate the certificate chain and check expiry."""
        try:
            context = ssl.create_default_context()
            with socket.create_connection(('www.google.com', 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname='www.google.com') as ssock:
                    cert = ssock.getpeercert()

            if not cert:
                return LayerTestResult(
                    name="Certificate Validation",
                    status=LayerStatus.FAIL.value,
                    value="No cert",
                    error="No certificate received"
                )

            # Check expiry
            not_after = cert.get('notAfter', '')
            if not_after:
                # Parse SSL date format: 'Mar  1 12:00:00 2026 GMT'
                try:
                    expiry = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                    days_left = (expiry - datetime.utcnow()).days
                    expiry_str = expiry.strftime('%Y-%m-%d')

                    if days_left < 0:
                        return LayerTestResult(
                            name="Certificate Validation",
                            status=LayerStatus.FAIL.value,
                            value="Expired",
                            detail=f"Certificate expired on {expiry_str}",
                            error="Expired certificate"
                        )
                    elif days_left < 30:
                        return LayerTestResult(
                            name="Certificate Validation",
                            status=LayerStatus.WARNING.value,
                            value=f"Expires in {days_left}d",
                            detail=f"Certificate expires {expiry_str} ({days_left} days)"
                        )
                    else:
                        return LayerTestResult(
                            name="Certificate Validation",
                            status=LayerStatus.PASS.value,
                            value="Valid",
                            detail=f"Chain verified, expires {expiry_str}"
                        )
                except ValueError:
                    pass

            return LayerTestResult(
                name="Certificate Validation",
                status=LayerStatus.PASS.value,
                value="Valid",
                detail="Certificate chain verified"
            )
        except ssl.SSLCertVerificationError as e:
            return LayerTestResult(
                name="Certificate Validation",
                status=LayerStatus.FAIL.value,
                value="Invalid",
                detail="Certificate chain verification failed",
                error=str(e)
            )
        except Exception as e:
            return LayerTestResult(
                name="Certificate Validation",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    # ==================== Layer 7: Application ====================

    def _test_layer7_application(self) -> LayerResult:
        """Test application layer: DNS, HTTP request, status code."""
        tests = []
        layer = LayerResult(layer_number=7, layer_name="Application")

        tests.append(self._test_dns_resolution())
        tests.append(self._test_http_request())
        tests.append(self._test_captive_portal())
        tests.append(self._test_saas_endpoints())

        layer.tests = [asdict(t) for t in tests]
        layer.status = self._aggregate_status(tests)
        layer.summary = self._build_summary(tests)
        # Use HTTP latency as layer latency
        for t in tests:
            if t.name == "HTTP Request" and t.latency_ms:
                layer.latency_ms = t.latency_ms
        return layer

    def _test_dns_resolution(self) -> LayerTestResult:
        """Test DNS resolution for google.com."""
        try:
            from atlas.network.monitors.wifi import NetworkDiagnostics
            result = NetworkDiagnostics.test_dns_resolution('google.com', timeout=3)

            if result.get('resolved'):
                latency = result.get('resolve_time_ms', 0)
                status = LayerStatus.PASS.value if latency < DNS_RESOLVE_WARN_MS else \
                         LayerStatus.WARNING.value
                return LayerTestResult(
                    name="DNS Resolution",
                    status=status,
                    value=f"google.com -> {result['ip']}",
                    latency_ms=round(latency, 1),
                    detail=f"Resolved in {latency:.0f}ms"
                )
            else:
                return LayerTestResult(
                    name="DNS Resolution",
                    status=LayerStatus.FAIL.value,
                    value="Failed",
                    detail="Could not resolve google.com",
                    error=result.get('error', 'DNS resolution failed')
                )
        except Exception as e:
            return LayerTestResult(
                name="DNS Resolution",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    def _test_http_request(self) -> LayerTestResult:
        """Test a full HTTP GET request."""
        try:
            import urllib.request

            start = time.time()
            req = urllib.request.Request(
                'https://www.google.com',
                headers={'User-Agent': 'ATLAS-OSI-Diagnostic/1.0'}
            )
            response = urllib.request.urlopen(req, timeout=5)
            elapsed_ms = round((time.time() - start) * 1000, 1)
            status_code = response.getcode()
            response.close()

            if 200 <= status_code < 400:
                status = LayerStatus.PASS.value if elapsed_ms < HTTP_RESPONSE_WARN_MS else \
                         LayerStatus.WARNING.value
                return LayerTestResult(
                    name="HTTP Request",
                    status=status,
                    value=f"{status_code} OK",
                    latency_ms=elapsed_ms,
                    detail=f"GET https://www.google.com -> {status_code} in {elapsed_ms}ms"
                )
            else:
                return LayerTestResult(
                    name="HTTP Request",
                    status=LayerStatus.WARNING.value,
                    value=f"{status_code}",
                    latency_ms=elapsed_ms,
                    detail=f"Unexpected status code: {status_code}"
                )
        except urllib.error.URLError as e:
            return LayerTestResult(
                name="HTTP Request",
                status=LayerStatus.FAIL.value,
                value="Failed",
                detail=f"HTTP request failed: {e.reason}",
                error=str(e.reason)
            )
        except Exception as e:
            return LayerTestResult(
                name="HTTP Request",
                status=LayerStatus.FAIL.value,
                error=str(e)
            )

    # ==================== New Enhanced Tests ====================

    def _test_ipv6_connectivity(self) -> LayerTestResult:
        """Test IPv6 connectivity to Google DNS IPv6."""
        try:
            if not socket.has_ipv6:
                return LayerTestResult(
                    name="IPv6 Connectivity",
                    status=LayerStatus.PASS.value,
                    value="Not available",
                    detail="System does not support IPv6 (normal for many networks)"
                )

            start = time.time()
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect(('2001:4860:4860::8888', 443))
            elapsed_ms = round((time.time() - start) * 1000, 1)
            sock.close()

            return LayerTestResult(
                name="IPv6 Connectivity",
                status=LayerStatus.PASS.value,
                value=f"Connected ({elapsed_ms}ms)",
                latency_ms=elapsed_ms,
                detail=f"IPv6 to Google DNS in {elapsed_ms}ms (dual-stack OK)"
            )
        except (socket.timeout, OSError):
            return LayerTestResult(
                name="IPv6 Connectivity",
                status=LayerStatus.WARNING.value,
                value="No IPv6",
                detail="IPv6 supported but connectivity failed (IPv4-only network)"
            )
        except Exception as e:
            return LayerTestResult(
                name="IPv6 Connectivity",
                status=LayerStatus.WARNING.value,
                value="Error",
                error=str(e)
            )

    def _test_mtu_path_discovery(self) -> LayerTestResult:
        """Discover effective path MTU using binary search with ping -D."""
        try:
            if platform.system() != 'Darwin':
                return LayerTestResult(
                    name="Path MTU",
                    status=LayerStatus.PASS.value,
                    value="Skipped",
                    detail="MTU test only supported on macOS"
                )

            low, high = 68, 1472  # 1500 - 28 (IP+ICMP headers)
            best = low
            for _ in range(8):
                if low > high:
                    break
                mid = (low + high) // 2
                result = subprocess.run(
                    ['ping', '-D', '-s', str(mid), '-c', '1', '-W', '1000',
                     MTU_TEST_TARGET],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    best = mid
                    low = mid + 1
                else:
                    high = mid - 1

            effective_mtu = best + 28
            status = LayerStatus.PASS.value if effective_mtu >= 1400 else \
                     LayerStatus.WARNING.value
            return LayerTestResult(
                name="Path MTU",
                status=status,
                value=f"{effective_mtu} bytes",
                detail=f"Effective path MTU to {MTU_TEST_TARGET}: {effective_mtu} bytes"
            )
        except Exception as e:
            return LayerTestResult(
                name="Path MTU",
                status=LayerStatus.WARNING.value,
                value="Unknown",
                error=str(e)
            )

    def _test_port_blocking(self) -> LayerTestResult:
        """Test commonly blocked ports to detect corporate firewall restrictions."""
        try:
            blocked = []
            open_ports = []
            for entry in FIREWALL_TEST_PORTS:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1.5)
                    sock.connect((entry['host'], entry['port']))
                    sock.close()
                    open_ports.append(entry['name'])
                except (socket.timeout, ConnectionRefusedError, OSError):
                    blocked.append(f"{entry['name']}:{entry['port']}")

            total = len(FIREWALL_TEST_PORTS)
            open_count = len(open_ports)

            if not blocked:
                return LayerTestResult(
                    name="Port Blocking",
                    status=LayerStatus.PASS.value,
                    value=f"All {total} open",
                    detail=f"Tested {total} common ports — no firewall blocking detected"
                )
            else:
                blocked_str = ', '.join(blocked)
                return LayerTestResult(
                    name="Port Blocking",
                    status=LayerStatus.WARNING.value,
                    value=f"Blocked: {blocked_str}",
                    detail=f"Open: {', '.join(open_ports) if open_ports else 'none'}. Blocked: {blocked_str} (ISP/firewall)"
                )
        except Exception as e:
            return LayerTestResult(
                name="Port Blocking",
                status=LayerStatus.WARNING.value,
                value="Error",
                error=str(e)
            )

    def _test_dns_over_https(self) -> LayerTestResult:
        """Test DNS-over-HTTPS to Cloudflare using wire-format query."""
        try:
            # Build minimal DNS query for example.com A record
            header = struct.pack('!HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
            qname = b'\x07example\x03com\x00'
            question = qname + struct.pack('!HH', 1, 1)
            dns_query = header + question

            start = time.time()
            req = urllib.request.Request(
                'https://cloudflare-dns.com/dns-query',
                data=dns_query,
                headers={
                    'Content-Type': 'application/dns-message',
                    'Accept': 'application/dns-message',
                },
                method='POST'
            )
            response = urllib.request.urlopen(req, timeout=5)
            elapsed_ms = round((time.time() - start) * 1000, 1)
            status_code = response.getcode()
            body = response.read()
            response.close()

            if status_code == 200 and len(body) > 12:
                return LayerTestResult(
                    name="DNS-over-HTTPS",
                    status=LayerStatus.PASS.value,
                    value=f"{elapsed_ms}ms",
                    latency_ms=elapsed_ms,
                    detail=f"DoH query to Cloudflare resolved in {elapsed_ms}ms"
                )
            else:
                return LayerTestResult(
                    name="DNS-over-HTTPS",
                    status=LayerStatus.WARNING.value,
                    value="Unexpected response",
                    latency_ms=elapsed_ms,
                    detail=f"DoH returned status {status_code}, body {len(body)} bytes"
                )
        except Exception as e:
            return LayerTestResult(
                name="DNS-over-HTTPS",
                status=LayerStatus.WARNING.value,
                value="Failed",
                detail=f"DoH test failed: {e}",
                error=str(e)
            )

    def _test_captive_portal(self) -> LayerTestResult:
        """Detect captive portals using Apple/Google/Microsoft connectivity checks."""
        try:
            detected = False
            detail_parts = []
            for check in CAPTIVE_PORTAL_CHECKS:
                try:
                    req = urllib.request.Request(
                        check['url'],
                        headers={'User-Agent': 'ATLAS-OSI-Diagnostic/1.0'}
                    )
                    response = urllib.request.urlopen(req, timeout=3)
                    status_code = response.getcode()
                    body = response.read(512).decode('utf-8', errors='ignore')
                    response.close()

                    if 'expect_status' in check:
                        if status_code != check['expect_status']:
                            detected = True
                            detail_parts.append(f"{check['name']}: got {status_code}")
                    elif 'expect_body' in check:
                        if check['expect_body'] not in body:
                            detected = True
                            detail_parts.append(f"{check['name']}: unexpected body")
                except Exception:
                    detected = True
                    detail_parts.append(f"{check['name']}: unreachable")

            if detected:
                return LayerTestResult(
                    name="Captive Portal",
                    status=LayerStatus.FAIL.value,
                    value="Detected",
                    detail=f"Captive portal likely active: {'; '.join(detail_parts)}",
                    error="Captive portal intercepting traffic"
                )
            return LayerTestResult(
                name="Captive Portal",
                status=LayerStatus.PASS.value,
                value="None detected",
                detail="Apple/Google/Microsoft checks all passed"
            )
        except Exception as e:
            return LayerTestResult(
                name="Captive Portal",
                status=LayerStatus.WARNING.value,
                value="Unknown",
                error=str(e)
            )

    def _test_saas_endpoints(self) -> LayerTestResult:
        """Test reachability and latency of key SaaS endpoints."""
        try:
            reachable = []
            unreachable = []
            latencies = []

            for ep in SAAS_ENDPOINTS:
                try:
                    req = urllib.request.Request(ep['url'], headers={
                        'User-Agent': 'ATLAS-OSI-Diagnostic/1.0'
                    })
                    start = time.time()
                    response = urllib.request.urlopen(req, timeout=3)
                    elapsed = round((time.time() - start) * 1000, 1)
                    response.close()
                    reachable.append(ep['name'])
                    latencies.append(elapsed)
                except Exception:
                    unreachable.append(ep['name'])

            total = len(SAAS_ENDPOINTS)
            ok_count = len(reachable)
            avg_lat = round(sum(latencies) / len(latencies), 0) if latencies else 0

            if ok_count == total:
                return LayerTestResult(
                    name="SaaS Endpoints",
                    status=LayerStatus.PASS.value,
                    value=f"{ok_count}/{total} OK",
                    latency_ms=avg_lat,
                    detail=f"All reachable (avg {avg_lat}ms): {', '.join(reachable)}"
                )
            elif ok_count > 0:
                return LayerTestResult(
                    name="SaaS Endpoints",
                    status=LayerStatus.WARNING.value,
                    value=f"{ok_count}/{total} OK",
                    latency_ms=avg_lat if avg_lat else None,
                    detail=f"Unreachable: {', '.join(unreachable)}"
                )
            else:
                return LayerTestResult(
                    name="SaaS Endpoints",
                    status=LayerStatus.FAIL.value,
                    value="0/{} OK".format(total),
                    detail="All SaaS endpoints unreachable",
                    error="No SaaS endpoints reachable"
                )
        except Exception as e:
            return LayerTestResult(
                name="SaaS Endpoints",
                status=LayerStatus.WARNING.value,
                error=str(e)
            )

    # ==================== QoE & Cloudflare Trace ====================

    def _compute_qoe_summary(self, layers: List[dict]) -> dict:
        """Compute Quality of Experience summary from layer results."""
        qoe: Dict[str, Any] = {}

        # --- MOS Score from Layer 3 ping data ---
        latency = 0.0
        jitter = 0.0
        try:
            from atlas.network.monitors.mos_calculator import (
                estimate_mos_simple, get_mos_color
            )
            l3 = next((l for l in layers if l['layer_number'] == 3), None)
            if l3:
                gateway_lat = 0.0
                external_lat = 0.0
                for t in l3.get('tests', []):
                    if t.get('name') == 'Gateway Ping' and t.get('latency_ms'):
                        gateway_lat = t['latency_ms']
                    if t.get('name') == 'External Ping' and t.get('latency_ms'):
                        external_lat = t['latency_ms']
                latency = external_lat or gateway_lat
                jitter = abs(external_lat - gateway_lat) / 2 \
                    if gateway_lat and external_lat else 0.0
                mos, rating = estimate_mos_simple(latency, jitter, 0.0)
                qoe['mos'] = round(mos, 1)
                qoe['mos_rating'] = rating
                qoe['mos_color'] = get_mos_color(mos)
        except Exception as e:
            logger.debug(f"QoE MOS failed: {e}")
            qoe['mos'] = None
            qoe['mos_rating'] = 'unknown'
            qoe['mos_color'] = '#666'

        # --- Video Conferencing Readiness ---
        try:
            vc_grades = {}
            for service, reqs in VIDEO_CONF_REQUIREMENTS.items():
                lat_ok = latency <= reqs['latency_ms']
                jit_ok = jitter <= reqs['jitter_ms']
                if lat_ok and jit_ok:
                    vc_grades[service] = 'good'
                elif latency <= reqs['latency_ms'] * 1.5:
                    vc_grades[service] = 'fair'
                else:
                    vc_grades[service] = 'poor'
            qoe['video_conf'] = vc_grades
        except Exception as e:
            logger.debug(f"QoE video conf failed: {e}")
            qoe['video_conf'] = {}

        # --- VPN Detection ---
        try:
            from atlas.network.monitors.vpn_monitor import get_vpn_monitor
            vpn = get_vpn_monitor()
            vpn_status = vpn.get_current_status()
            qoe['vpn'] = {
                'connected': vpn_status.get('connected', False),
                'client': vpn_status.get('vpn_client'),
                'interface_count': vpn_status.get('connection_count', 0),
            }
        except Exception as e:
            logger.debug(f"QoE VPN detection failed: {e}")
            qoe['vpn'] = {'connected': False, 'client': None}

        # --- Captive Portal (from Layer 7 test results) ---
        try:
            l7 = next((l for l in layers if l['layer_number'] == 7), None)
            if l7:
                for t in l7.get('tests', []):
                    if t.get('name') == 'Captive Portal':
                        qoe['captive_portal'] = t.get('status') == 'fail'
                        break
            if 'captive_portal' not in qoe:
                qoe['captive_portal'] = False
        except Exception:
            qoe['captive_portal'] = False

        # --- Bufferbloat (placeholder; needs networkQuality data) ---
        qoe['bufferbloat'] = {
            'grade': 'N/A',
            'detail': 'Run networkQuality for bufferbloat assessment'
        }

        return qoe

    def _fetch_cloudflare_trace(self) -> dict:
        """Fetch Cloudflare trace data for network path info."""
        try:
            req = urllib.request.Request(
                'https://1.1.1.1/cdn-cgi/trace',
                headers={'User-Agent': 'ATLAS-OSI-Diagnostic/1.0'}
            )
            response = urllib.request.urlopen(req, timeout=3)
            body = response.read().decode('utf-8', errors='ignore')
            response.close()

            trace: Dict[str, str] = {}
            for line in body.strip().split('\n'):
                if '=' in line:
                    key, _, val = line.partition('=')
                    trace[key.strip()] = val.strip()
            return trace
        except Exception as e:
            logger.debug(f"Cloudflare trace failed: {e}")
            return {}

    # ==================== Custom Scan ====================

    def run_custom_scan(self, options: dict) -> dict:
        """Run a custom one-time scan with user-specified targets.

        Args:
            options: Dict with optional keys:
                ports: list of {"host": str, "port": int, "label": str?}
                ping_targets: list of IP/hostname strings
                dns_hostnames: list of hostname strings
                http_urls: list of URL strings
                tls_targets: list of {"host": str, "port": int?}

        Returns:
            Dict with 'tests' list and metadata.
        """
        start = time.time()
        tests: List[LayerTestResult] = []

        # --- Custom Port Scan (Layer 4) ---
        for entry in options.get('ports', []):
            host = entry.get('host', '').strip()
            port = entry.get('port', 0)
            label = entry.get('label', f'{host}:{port}')
            if not host or not port:
                continue
            try:
                port = int(port)
                if port < 1 or port > 65535:
                    tests.append(LayerTestResult(
                        name=f"Port {label}",
                        status=LayerStatus.FAIL.value,
                        value="Invalid port",
                        error=f"Port {port} out of range"
                    ))
                    continue
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                t0 = time.time()
                s.connect((host, port))
                elapsed = round((time.time() - t0) * 1000, 1)
                s.close()
                tests.append(LayerTestResult(
                    name=f"Port {label}",
                    status=LayerStatus.PASS.value,
                    value=f"Open ({elapsed}ms)",
                    latency_ms=elapsed,
                    detail=f"TCP to {host}:{port} connected in {elapsed}ms"
                ))
            except (socket.timeout, ConnectionRefusedError, OSError) as e:
                tests.append(LayerTestResult(
                    name=f"Port {label}",
                    status=LayerStatus.FAIL.value,
                    value="Closed/Blocked",
                    detail=f"TCP to {host}:{port} failed: {e}"
                ))
            except (ValueError, TypeError):
                tests.append(LayerTestResult(
                    name=f"Port {label}",
                    status=LayerStatus.FAIL.value,
                    value="Invalid",
                    error=f"Invalid port: {port}"
                ))

        # --- Custom Ping Targets (Layer 3) ---
        for target in options.get('ping_targets', []):
            target = str(target).strip()
            if not target:
                continue
            try:
                from atlas.network.monitors.wifi import NetworkDiagnostics
                ping_result = NetworkDiagnostics.ping_host(target, count=3, timeout=2)
                if ping_result['reachable']:
                    lat = ping_result.get('avg_latency')
                    tests.append(LayerTestResult(
                        name=f"Ping {target}",
                        status=LayerStatus.PASS.value,
                        value=f"{lat:.1f} ms" if lat else "OK",
                        latency_ms=round(lat, 1) if lat else None,
                        detail=f"{target} reachable, {ping_result['packet_loss']}% loss"
                    ))
                else:
                    tests.append(LayerTestResult(
                        name=f"Ping {target}",
                        status=LayerStatus.FAIL.value,
                        value="Unreachable",
                        detail=f"{target} did not respond to ping"
                    ))
            except Exception as e:
                tests.append(LayerTestResult(
                    name=f"Ping {target}",
                    status=LayerStatus.FAIL.value,
                    error=str(e)
                ))

        # --- Custom DNS Resolution (Layer 7) ---
        for hostname in options.get('dns_hostnames', []):
            hostname = str(hostname).strip()
            if not hostname:
                continue
            try:
                t0 = time.time()
                ip = socket.gethostbyname(hostname)
                elapsed = round((time.time() - t0) * 1000, 1)
                tests.append(LayerTestResult(
                    name=f"DNS {hostname}",
                    status=LayerStatus.PASS.value,
                    value=f"{hostname} -> {ip}",
                    latency_ms=elapsed,
                    detail=f"Resolved in {elapsed}ms"
                ))
            except socket.gaierror as e:
                tests.append(LayerTestResult(
                    name=f"DNS {hostname}",
                    status=LayerStatus.FAIL.value,
                    value="Failed",
                    detail=f"Could not resolve {hostname}",
                    error=str(e)
                ))
            except Exception as e:
                tests.append(LayerTestResult(
                    name=f"DNS {hostname}",
                    status=LayerStatus.FAIL.value,
                    error=str(e)
                ))

        # --- Custom HTTP URLs (Layer 7) ---
        for url in options.get('http_urls', []):
            url = str(url).strip()
            if not url:
                continue
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'ATLAS-OSI-CustomScan/1.0'
                })
                t0 = time.time()
                response = urllib.request.urlopen(req, timeout=5)
                elapsed = round((time.time() - t0) * 1000, 1)
                status_code = response.getcode()
                response.close()

                status = LayerStatus.PASS.value if 200 <= status_code < 400 else \
                         LayerStatus.WARNING.value
                # Truncate URL for display
                display_url = url if len(url) <= 40 else url[:37] + '...'
                tests.append(LayerTestResult(
                    name=f"HTTP {display_url}",
                    status=status,
                    value=f"{status_code} ({elapsed}ms)",
                    latency_ms=elapsed,
                    detail=f"GET {url} -> {status_code} in {elapsed}ms"
                ))
            except urllib.error.URLError as e:
                display_url = url if len(url) <= 40 else url[:37] + '...'
                tests.append(LayerTestResult(
                    name=f"HTTP {display_url}",
                    status=LayerStatus.FAIL.value,
                    value="Failed",
                    detail=f"Request to {url} failed: {e.reason}",
                    error=str(e.reason)
                ))
            except Exception as e:
                display_url = url if len(url) <= 40 else url[:37] + '...'
                tests.append(LayerTestResult(
                    name=f"HTTP {display_url}",
                    status=LayerStatus.FAIL.value,
                    error=str(e)
                ))

        # --- Custom TLS Targets (Layer 6) ---
        for entry in options.get('tls_targets', []):
            host = entry.get('host', '').strip() if isinstance(entry, dict) else str(entry).strip()
            port = entry.get('port', 443) if isinstance(entry, dict) else 443
            if not host:
                continue
            try:
                port = int(port)
                context = ssl.create_default_context()
                t0 = time.time()
                with socket.create_connection((host, port), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=host) as ssock:
                        elapsed = round((time.time() - t0) * 1000, 1)
                        tls_ver = ssock.version()
                        cipher = ssock.cipher()
                        cipher_name = cipher[0] if cipher else "Unknown"

                tests.append(LayerTestResult(
                    name=f"TLS {host}:{port}",
                    status=LayerStatus.PASS.value,
                    value=f"{tls_ver} ({elapsed}ms)",
                    latency_ms=elapsed,
                    detail=f"{tls_ver} with {cipher_name} in {elapsed}ms"
                ))
            except ssl.SSLCertVerificationError as e:
                tests.append(LayerTestResult(
                    name=f"TLS {host}:{port}",
                    status=LayerStatus.FAIL.value,
                    value="Cert Error",
                    detail=f"Certificate verification failed for {host}",
                    error=str(e)
                ))
            except Exception as e:
                tests.append(LayerTestResult(
                    name=f"TLS {host}:{port}",
                    status=LayerStatus.FAIL.value,
                    value="Failed",
                    error=str(e)
                ))

        duration = round((time.time() - start) * 1000, 1)

        # Aggregate
        test_dicts = [asdict(t) for t in tests]
        pass_count = sum(1 for t in test_dicts if t['status'] == LayerStatus.PASS.value)
        warn_count = sum(1 for t in test_dicts if t['status'] == LayerStatus.WARNING.value)
        fail_count = sum(1 for t in test_dicts if t['status'] == LayerStatus.FAIL.value)
        total = len(test_dicts)

        if fail_count > 0:
            overall = 'fail'
        elif warn_count > 0:
            overall = 'warning'
        else:
            overall = 'pass'

        return {
            'timestamp': datetime.now().isoformat(),
            'scan_type': 'custom',
            'overall_status': overall,
            'tests': test_dicts,
            'summary': {
                'total': total,
                'pass': pass_count,
                'warning': warn_count,
                'fail': fail_count,
            },
            'duration_ms': duration,
        }

    # ==================== Helpers ====================

    def _aggregate_status(self, tests: List[LayerTestResult]) -> str:
        """Aggregate test results into a single layer status."""
        statuses = [t.status for t in tests]
        if LayerStatus.FAIL.value in statuses:
            return LayerStatus.FAIL.value
        if LayerStatus.WARNING.value in statuses:
            return LayerStatus.WARNING.value
        if all(s == LayerStatus.PASS.value for s in statuses):
            return LayerStatus.PASS.value
        return LayerStatus.UNKNOWN.value

    def _build_summary(self, tests: List[LayerTestResult]) -> str:
        """Build a one-line summary from test results."""
        parts = []
        for t in tests:
            if t.value and t.status != LayerStatus.FAIL.value:
                if t.latency_ms:
                    parts.append(f"{t.name.split()[0]} {t.latency_ms:.0f}ms")
                else:
                    parts.append(f"{t.name.split()[0]} {t.value}")
            elif t.status == LayerStatus.FAIL.value:
                parts.append(f"{t.name.split()[0]} FAIL")
        return ", ".join(parts[:3])


# ==================== Utility ====================

def _parse_timestamp(ts: str) -> float:
    """Parse ISO timestamp to epoch seconds."""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0


# ==================== Singleton ====================

_osi_diagnostic_monitor: Optional[OSIDiagnosticMonitor] = None
_osi_lock = threading.Lock()


def get_osi_diagnostic_monitor() -> OSIDiagnosticMonitor:
    """Get or create singleton OSI Diagnostic Monitor instance."""
    global _osi_diagnostic_monitor
    with _osi_lock:
        if _osi_diagnostic_monitor is None:
            _osi_diagnostic_monitor = OSIDiagnosticMonitor()
    return _osi_diagnostic_monitor
