"""
Network monitor implementations

Core Monitors:
- WiFiMonitor: WiFi signal quality and roaming
- SpeedTestMonitor: Public speedtest.net bandwidth testing
- PingMonitor: ICMP latency monitoring

Advanced Monitors (CyPerf-inspired):
- UDPQualityMonitor: UDP packet loss and jitter for VoIP/video
- TCPConnectionTester: Connection rate testing (CPS)
- ThroughputTester: Private server bandwidth testing
- NetworkQualityMonitor: TCP retransmit, DNS, TLS, HTTP quality

Quality Metrics:
- MOSCalculator: ITU-T E-Model MOS score calculation
"""

from .base import BaseNetworkMonitor
from .wifi import WiFiMonitor, get_wifi_monitor
from .speedtest import SpeedTestMonitor, get_speed_test_monitor
from .ping import PingMonitor, get_ping_monitor

# Advanced monitors
from .udp_quality_monitor import UDPQualityMonitor, UDPEchoServer, get_udp_quality_monitor
from .tcp_connection_tester import TCPConnectionTester, ConnectionTestServer, get_tcp_connection_tester
from .throughput_tester import ThroughputTester, ThroughputServer, get_throughput_tester
from .network_quality_monitor import NetworkQualityMonitor, get_network_quality_monitor
from .osi_diagnostic_monitor import OSIDiagnosticMonitor, get_osi_diagnostic_monitor

# Quality metrics
from .mos_calculator import (
    MOSCalculator,
    MOSResult,
    NetworkMetrics,
    CodecType,
    calculate_network_mos,
    estimate_mos_simple,
    get_mos_color,
    get_mos_emoji
)

__all__ = [
    # Base class
    'BaseNetworkMonitor',

    # Core monitors
    'WiFiMonitor', 'get_wifi_monitor',
    'SpeedTestMonitor', 'get_speed_test_monitor',
    'PingMonitor', 'get_ping_monitor',

    # Advanced monitors
    'UDPQualityMonitor', 'UDPEchoServer', 'get_udp_quality_monitor',
    'TCPConnectionTester', 'ConnectionTestServer', 'get_tcp_connection_tester',
    'ThroughputTester', 'ThroughputServer', 'get_throughput_tester',
    'NetworkQualityMonitor', 'get_network_quality_monitor',
    'OSIDiagnosticMonitor', 'get_osi_diagnostic_monitor',

    # Quality metrics
    'MOSCalculator', 'MOSResult', 'NetworkMetrics', 'CodecType',
    'calculate_network_mos', 'estimate_mos_simple',
    'get_mos_color', 'get_mos_emoji'
]
