"""
UDP Quality Monitor - VoIP/Video Quality Testing

Measures UDP packet loss, jitter, and one-way delay variation for
assessing real-time communication quality (VoIP, video conferencing).

This monitor sends UDP probe packets between the agent and a server
to measure actual packet delivery characteristics that affect
voice/video quality.
"""

import socket
import struct
import time
import threading
import logging
import statistics
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from atlas.network.monitors.base import BaseNetworkMonitor
from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

# Default UDP test port
DEFAULT_UDP_PORT = 5005

# Packet structure: sequence_number (I), timestamp (d), padding
PACKET_FORMAT = '!Id'  # Network byte order: unsigned int + double
PACKET_HEADER_SIZE = struct.calcsize(PACKET_FORMAT)
DEFAULT_PACKET_SIZE = 172  # Similar to RTP voice packet size


class UDPQualityMonitor(BaseNetworkMonitor):
    """
    Monitor UDP packet loss and jitter for VoIP/Video quality assessment.

    Features:
    - Packet loss measurement
    - Jitter calculation (RFC 3550 algorithm)
    - One-way delay variation (OWDV)
    - Round-trip time measurement
    - Configurable packet rate and size
    - Quality scoring based on ITU-T standards

    Can operate in two modes:
    1. Client mode: Sends UDP probes to a server
    2. Server mode: Receives probes and sends responses
    """

    # Quality thresholds based on ITU-T G.114
    JITTER_THRESHOLDS = {
        'excellent': 10,   # < 10ms
        'good': 20,        # < 20ms
        'acceptable': 50,  # < 50ms
        'poor': 100        # > 50ms is poor
    }

    PACKET_LOSS_THRESHOLDS = {
        'excellent': 0.1,  # < 0.1%
        'good': 1.0,       # < 1%
        'acceptable': 3.0, # < 3%
        'poor': 5.0        # > 5% is poor
    }

    def __init__(
        self,
        target_host: str = "8.8.8.8",
        target_port: int = DEFAULT_UDP_PORT,
        packet_size: int = DEFAULT_PACKET_SIZE,
        packets_per_test: int = 50,
        packet_interval_ms: int = 20  # 50 packets/second
    ):
        """
        Initialize UDP Quality Monitor.

        Args:
            target_host: Target server IP/hostname
            target_port: Target UDP port
            packet_size: Size of each probe packet in bytes
            packets_per_test: Number of packets per test cycle
            packet_interval_ms: Interval between packets in milliseconds
        """
        self.target_host = target_host
        self.target_port = target_port
        self.packet_size = max(PACKET_HEADER_SIZE, packet_size)
        self.packets_per_test = packets_per_test
        self.packet_interval_ms = packet_interval_ms

        # Results history
        self.test_history: List[Dict[str, Any]] = []
        self.max_history = 100

        # Socket
        self._socket: Optional[socket.socket] = None

        # Initialize base class
        super().__init__()

        # Initialize CSV logger
        log_dir = Path.home()
        self.csv_logger = CSVLogger(
            log_file=str(log_dir / 'udp_quality.csv'),
            fieldnames=[
                'timestamp', 'target', 'packets_sent', 'packets_received',
                'packet_loss_percent', 'avg_rtt_ms', 'min_rtt_ms', 'max_rtt_ms',
                'jitter_ms', 'quality_score', 'quality_rating'
            ],
            max_history=500,
            retention_days=7
        )

        # Initialize last_result
        self.last_result = {
            'status': 'idle',
            'timestamp': None,
            'packets_sent': 0,
            'packets_received': 0,
            'packet_loss_percent': 0,
            'avg_rtt_ms': 0,
            'jitter_ms': 0,
            'quality_score': 0,
            'quality_rating': 'unknown'
        }

    def get_monitor_name(self) -> str:
        return "UDP Quality Monitor"

    def get_default_interval(self) -> int:
        """Default interval: 5 minutes between tests"""
        return 300

    def _on_start(self):
        """Create UDP socket on start"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.settimeout(2.0)  # 2 second timeout for responses
            logger.info(f"UDP Quality Monitor socket created for {self.target_host}:{self.target_port}")
        except Exception as e:
            logger.error(f"Failed to create UDP socket: {e}")

    def _on_stop(self):
        """Close socket on stop"""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def _run_monitoring_cycle(self):
        """Execute one UDP quality test cycle"""
        try:
            result = self._run_udp_test()
            self.update_last_result(result)

            # Log to CSV
            self.csv_logger.append({
                'timestamp': datetime.now().isoformat(),
                'target': f"{self.target_host}:{self.target_port}",
                'packets_sent': result.get('packets_sent', 0),
                'packets_received': result.get('packets_received', 0),
                'packet_loss_percent': result.get('packet_loss_percent', 0),
                'avg_rtt_ms': result.get('avg_rtt_ms', 0),
                'min_rtt_ms': result.get('min_rtt_ms', 0),
                'max_rtt_ms': result.get('max_rtt_ms', 0),
                'jitter_ms': result.get('jitter_ms', 0),
                'quality_score': result.get('quality_score', 0),
                'quality_rating': result.get('quality_rating', 'unknown')
            })

            # Add to history
            self.test_history.append(result)
            if len(self.test_history) > self.max_history:
                self.test_history = self.test_history[-self.max_history:]

            # Log to fleet
            self.log_to_fleet('udp_quality', result)

            logger.info(
                f"UDP Quality Test: {result['packets_received']}/{result['packets_sent']} packets, "
                f"loss={result['packet_loss_percent']:.2f}%, jitter={result['jitter_ms']:.2f}ms, "
                f"quality={result['quality_rating']}"
            )

        except Exception as e:
            logger.error(f"UDP quality test failed: {e}")
            self.update_last_result({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    def _run_udp_test(self) -> Dict[str, Any]:
        """
        Run a complete UDP quality test.

        Sends a burst of UDP packets and measures:
        - Packet loss
        - Round-trip time (if echo server available)
        - Jitter (variation in delay)

        Returns:
            Dictionary with test results
        """
        if not self._socket:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.settimeout(2.0)

        packets_sent = 0
        packets_received = 0
        rtts: List[float] = []
        receive_times: List[float] = []

        # Prepare padding to reach desired packet size
        padding_size = self.packet_size - PACKET_HEADER_SIZE
        padding = b'\x00' * padding_size

        # Send packets
        send_times: Dict[int, float] = {}

        for seq in range(self.packets_per_test):
            try:
                # Create packet with sequence number and timestamp
                send_time = time.time()
                packet = struct.pack(PACKET_FORMAT, seq, send_time) + padding

                self._socket.sendto(packet, (self.target_host, self.target_port))
                send_times[seq] = send_time
                packets_sent += 1

                # Wait between packets
                time.sleep(self.packet_interval_ms / 1000.0)

            except Exception as e:
                logger.debug(f"Failed to send packet {seq}: {e}")

        # Try to receive responses (for echo servers)
        # Set shorter timeout for receiving
        self._socket.settimeout(0.1)

        deadline = time.time() + 2.0  # Wait up to 2 seconds for all responses

        while time.time() < deadline:
            try:
                data, addr = self._socket.recvfrom(self.packet_size + 100)
                receive_time = time.time()

                if len(data) >= PACKET_HEADER_SIZE:
                    seq, send_timestamp = struct.unpack(PACKET_FORMAT, data[:PACKET_HEADER_SIZE])

                    if seq in send_times:
                        rtt = (receive_time - send_times[seq]) * 1000  # Convert to ms
                        rtts.append(rtt)
                        receive_times.append(receive_time)
                        packets_received += 1

            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"Error receiving packet: {e}")
                break

        # Reset socket timeout
        self._socket.settimeout(2.0)

        # Calculate metrics
        result = self._calculate_metrics(
            packets_sent, packets_received, rtts, receive_times
        )

        return result

    def _calculate_metrics(
        self,
        packets_sent: int,
        packets_received: int,
        rtts: List[float],
        receive_times: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate UDP quality metrics from test results.

        Args:
            packets_sent: Number of packets sent
            packets_received: Number of packets received
            rtts: List of round-trip times in ms
            receive_times: List of receive timestamps

        Returns:
            Dictionary with calculated metrics
        """
        # Packet loss
        if packets_sent > 0:
            packet_loss = ((packets_sent - packets_received) / packets_sent) * 100
        else:
            packet_loss = 100.0

        # RTT statistics
        if rtts:
            avg_rtt = statistics.mean(rtts)
            min_rtt = min(rtts)
            max_rtt = max(rtts)
        else:
            avg_rtt = min_rtt = max_rtt = 0

        # Jitter calculation (RFC 3550 algorithm)
        jitter = self._calculate_jitter(receive_times)

        # Calculate quality score (0-100)
        quality_score = self._calculate_quality_score(packet_loss, jitter, avg_rtt)
        quality_rating = self._get_quality_rating(quality_score)

        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'packets_sent': packets_sent,
            'packets_received': packets_received,
            'packet_loss_percent': round(packet_loss, 2),
            'avg_rtt_ms': round(avg_rtt, 2),
            'min_rtt_ms': round(min_rtt, 2),
            'max_rtt_ms': round(max_rtt, 2),
            'jitter_ms': round(jitter, 2),
            'quality_score': round(quality_score, 1),
            'quality_rating': quality_rating,
            'target': f"{self.target_host}:{self.target_port}"
        }

    def _calculate_jitter(self, receive_times: List[float]) -> float:
        """
        Calculate jitter using RFC 3550 algorithm.

        Jitter is the mean deviation of the difference in packet spacing
        at the receiver compared to the sender.

        Args:
            receive_times: List of packet receive timestamps

        Returns:
            Jitter in milliseconds
        """
        if len(receive_times) < 2:
            return 0.0

        # Calculate inter-arrival times
        inter_arrivals = []
        for i in range(1, len(receive_times)):
            delta = (receive_times[i] - receive_times[i-1]) * 1000  # Convert to ms
            inter_arrivals.append(delta)

        if not inter_arrivals:
            return 0.0

        # Expected interval
        expected_interval = self.packet_interval_ms

        # Calculate deviations from expected interval
        deviations = [abs(ia - expected_interval) for ia in inter_arrivals]

        # Jitter is the mean absolute deviation
        if deviations:
            return statistics.mean(deviations)

        return 0.0

    def _calculate_quality_score(
        self,
        packet_loss: float,
        jitter: float,
        latency: float
    ) -> float:
        """
        Calculate a quality score from 0-100 based on metrics.

        Based on ITU-T G.107 E-Model simplified approach:
        - Packet loss has highest impact
        - Jitter affects real-time applications
        - Latency adds delay but less impact for non-interactive

        Args:
            packet_loss: Packet loss percentage
            jitter: Jitter in milliseconds
            latency: Average latency in milliseconds

        Returns:
            Quality score 0-100
        """
        score = 100.0

        # Deduct for packet loss (most impactful)
        # 1% loss = -20 points, 5% loss = -50 points
        if packet_loss > 0:
            loss_penalty = min(50, packet_loss * 10)
            score -= loss_penalty

        # Deduct for jitter
        # 20ms jitter = -10 points, 50ms jitter = -25 points
        if jitter > 0:
            jitter_penalty = min(30, jitter * 0.5)
            score -= jitter_penalty

        # Deduct for high latency
        # 100ms = -5 points, 300ms = -15 points
        if latency > 50:
            latency_penalty = min(20, (latency - 50) * 0.05)
            score -= latency_penalty

        return max(0, score)

    def _get_quality_rating(self, score: float) -> str:
        """
        Convert quality score to rating.

        Args:
            score: Quality score 0-100

        Returns:
            Quality rating string
        """
        if score >= 90:
            return 'excellent'
        elif score >= 70:
            return 'good'
        elif score >= 50:
            return 'acceptable'
        elif score >= 30:
            return 'poor'
        else:
            return 'bad'

    # ==================== Public API Methods ====================

    def get_history(self) -> List[Dict[str, Any]]:
        """Get test history"""
        return list(self.test_history)

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics from history"""
        if not self.test_history:
            return {
                'total_tests': 0,
                'avg_packet_loss': 0,
                'avg_jitter': 0,
                'avg_quality_score': 0
            }

        losses = [t.get('packet_loss_percent', 0) for t in self.test_history]
        jitters = [t.get('jitter_ms', 0) for t in self.test_history]
        scores = [t.get('quality_score', 0) for t in self.test_history]

        return {
            'total_tests': len(self.test_history),
            'avg_packet_loss': round(statistics.mean(losses), 2),
            'max_packet_loss': round(max(losses), 2),
            'avg_jitter': round(statistics.mean(jitters), 2),
            'max_jitter': round(max(jitters), 2),
            'avg_quality_score': round(statistics.mean(scores), 1),
            'min_quality_score': round(min(scores), 1)
        }

    def set_target(self, host: str, port: int = DEFAULT_UDP_PORT):
        """Change the target server"""
        self.target_host = host
        self.target_port = port
        logger.info(f"UDP target changed to {host}:{port}")

    def run_single_test(self) -> Dict[str, Any]:
        """Run a single test immediately (outside monitoring loop)"""
        if not self._socket:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.settimeout(2.0)
        return self._run_udp_test()


# ==================== UDP Echo Server ====================

class UDPEchoServer:
    """
    Simple UDP echo server for quality testing.

    Can be run on the fleet server to allow agents to measure
    UDP quality to the server.
    """

    def __init__(self, host: str = '0.0.0.0', port: int = DEFAULT_UDP_PORT):
        self.host = host
        self.port = port
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None

    def start(self):
        """Start the echo server"""
        if self._running:
            return

        self._running = True
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.host, self.port))
        self._socket.settimeout(1.0)

        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()

        logger.info(f"UDP Echo Server started on {self.host}:{self.port}")

    def stop(self):
        """Stop the echo server"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._socket:
            self._socket.close()
        logger.info("UDP Echo Server stopped")

    def _serve_loop(self):
        """Main server loop - echo back received packets"""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(2048)
                # Echo the packet back immediately
                self._socket.sendto(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.debug(f"UDP Echo Server error: {e}")


# ==================== Singleton Access ====================

_udp_quality_monitor: Optional[UDPQualityMonitor] = None
_monitor_lock = threading.Lock()


def get_udp_quality_monitor(
    target_host: str = "8.8.8.8",
    target_port: int = DEFAULT_UDP_PORT
) -> UDPQualityMonitor:
    """Get or create singleton UDP quality monitor instance"""
    global _udp_quality_monitor

    with _monitor_lock:
        if _udp_quality_monitor is None:
            _udp_quality_monitor = UDPQualityMonitor(
                target_host=target_host,
                target_port=target_port
            )

    return _udp_quality_monitor
