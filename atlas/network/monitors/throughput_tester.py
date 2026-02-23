"""
Private Server Throughput Tester - Enterprise Bandwidth Testing

Measures TCP/UDP throughput between endpoints using a custom
protocol that doesn't rely on public speedtest servers.

Use cases:
- Internal network bandwidth assessment
- WAN link capacity testing
- SD-WAN path quality verification
- Datacenter interconnect testing
- VPN tunnel throughput measurement

Inspired by iperf3 and Keysight CyPerf throughput testing.
"""

import socket
import struct
import threading
import time
import logging
import statistics
import ssl
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import hashlib
import os

from atlas.network.monitors.base import BaseNetworkMonitor
from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

# Protocol constants
THROUGHPUT_PORT = 5007
CONTROL_PORT = 5008
MAGIC_NUMBER = 0x54485055  # "THPU" in hex
PROTOCOL_VERSION = 1

# Packet types
class PacketType(Enum):
    HANDSHAKE = 1
    DATA = 2
    ACK = 3
    COMPLETE = 4
    ERROR = 5
    STATS = 6


@dataclass
class ThroughputResult:
    """Result of a throughput test"""
    direction: str  # 'download', 'upload', 'bidirectional'
    bytes_transferred: int
    duration_seconds: float
    throughput_mbps: float
    packets_sent: int
    packets_received: int
    packet_loss_percent: float
    avg_latency_ms: float
    jitter_ms: float


class ThroughputTester(BaseNetworkMonitor):
    """
    Measure throughput to private servers.

    Features:
    - Configurable test duration and buffer sizes
    - Download, upload, and bidirectional testing
    - TCP and UDP modes
    - Real-time throughput reporting
    - Integration with fleet server
    """

    # Default test parameters
    DEFAULT_DURATION = 10  # seconds
    DEFAULT_BUFFER_SIZE = 128 * 1024  # 128KB
    DEFAULT_PARALLEL_STREAMS = 1

    def __init__(
        self,
        server_host: str = None,
        server_port: int = THROUGHPUT_PORT,
        test_duration: int = DEFAULT_DURATION,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        parallel_streams: int = DEFAULT_PARALLEL_STREAMS,
        use_tcp: bool = True
    ):
        """
        Initialize Throughput Tester.

        Args:
            server_host: Throughput server hostname/IP
            server_port: Server port
            test_duration: Duration of each test in seconds
            buffer_size: Buffer size for data transfer
            parallel_streams: Number of parallel connections
            use_tcp: True for TCP, False for UDP
        """
        self.server_host = server_host
        self.server_port = server_port
        self.test_duration = test_duration
        self.buffer_size = buffer_size
        self.parallel_streams = parallel_streams
        self.use_tcp = use_tcp

        # Test data buffer (random data for realistic testing)
        self._test_data = os.urandom(buffer_size)

        # Results tracking
        self.test_history: List[Dict[str, Any]] = []
        self.max_history = 100

        # Initialize base class
        super().__init__()

        # Initialize CSV logger
        log_dir = Path.home()
        self.csv_logger = CSVLogger(
            log_file=str(log_dir / 'throughput_test.csv'),
            fieldnames=[
                'timestamp', 'server', 'direction', 'protocol',
                'duration_seconds', 'bytes_transferred',
                'throughput_mbps', 'avg_throughput_mbps',
                'packets_sent', 'packets_received',
                'packet_loss_percent', 'jitter_ms'
            ],
            max_history=500,
            retention_days=7
        )

        # Initialize last_result
        self.last_result = {
            'status': 'idle',
            'timestamp': None,
            'download_mbps': 0,
            'upload_mbps': 0,
            'quality_rating': 'unknown'
        }

    def get_monitor_name(self) -> str:
        return "Throughput Tester"

    def get_default_interval(self) -> int:
        """Default interval: 30 minutes between tests"""
        return 1800

    def _run_monitoring_cycle(self):
        """Execute throughput test cycle"""
        if not self.server_host:
            logger.warning("No throughput server configured")
            self.update_last_result({
                'status': 'unconfigured',
                'error': 'No server host configured',
                'timestamp': datetime.now().isoformat()
            })
            return

        try:
            result = self.run_full_test()
            self.update_last_result(result)

            # Log to fleet
            self.log_to_fleet('throughput_test', result)

            logger.info(
                f"Throughput Test to {self.server_host}: "
                f"Download={result.get('download_mbps', 0):.2f} Mbps, "
                f"Upload={result.get('upload_mbps', 0):.2f} Mbps"
            )

        except Exception as e:
            logger.error(f"Throughput test failed: {e}")
            self.update_last_result({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    def run_full_test(self) -> Dict[str, Any]:
        """
        Run a complete throughput test (download + upload).

        Returns:
            Dictionary with test results
        """
        results = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'server': f"{self.server_host}:{self.server_port}",
            'protocol': 'TCP' if self.use_tcp else 'UDP',
            'test_duration': self.test_duration
        }

        # Run download test
        try:
            download_result = self._run_download_test()
            results['download_mbps'] = download_result.throughput_mbps
            results['download_bytes'] = download_result.bytes_transferred
            results['download_duration'] = download_result.duration_seconds

            self._log_result('download', download_result)

        except Exception as e:
            logger.error(f"Download test failed: {e}")
            results['download_mbps'] = 0
            results['download_error'] = str(e)

        # Brief pause between tests
        time.sleep(1)

        # Run upload test
        try:
            upload_result = self._run_upload_test()
            results['upload_mbps'] = upload_result.throughput_mbps
            results['upload_bytes'] = upload_result.bytes_transferred
            results['upload_duration'] = upload_result.duration_seconds

            self._log_result('upload', upload_result)

        except Exception as e:
            logger.error(f"Upload test failed: {e}")
            results['upload_mbps'] = 0
            results['upload_error'] = str(e)

        # Calculate overall quality
        results['quality_rating'] = self._get_quality_rating(
            results.get('download_mbps', 0),
            results.get('upload_mbps', 0)
        )

        # Add to history
        self.test_history.append(results)
        if len(self.test_history) > self.max_history:
            self.test_history = self.test_history[-self.max_history:]

        return results

    def _run_download_test(self) -> ThroughputResult:
        """
        Run download (server -> client) throughput test.

        Returns:
            ThroughputResult with download metrics
        """
        if self.use_tcp:
            return self._tcp_download_test()
        else:
            return self._udp_download_test()

    def _run_upload_test(self) -> ThroughputResult:
        """
        Run upload (client -> server) throughput test.

        Returns:
            ThroughputResult with upload metrics
        """
        if self.use_tcp:
            return self._tcp_upload_test()
        else:
            return self._udp_upload_test()

    def _tcp_download_test(self) -> ThroughputResult:
        """TCP download test implementation"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.test_duration + 5)

        try:
            sock.connect((self.server_host, self.server_port))

            # Send download request
            request = struct.pack('!IBI', MAGIC_NUMBER, PacketType.HANDSHAKE.value, self.test_duration)
            sock.sendall(request)

            # Receive data for duration
            bytes_received = 0
            start_time = time.time()
            end_time = start_time + self.test_duration

            # Track throughput samples
            samples = []
            sample_start = start_time
            sample_bytes = 0

            while time.time() < end_time:
                try:
                    data = sock.recv(self.buffer_size)
                    if not data:
                        break

                    bytes_received += len(data)
                    sample_bytes += len(data)

                    # Calculate per-second samples
                    now = time.time()
                    if now - sample_start >= 1.0:
                        mbps = (sample_bytes * 8) / ((now - sample_start) * 1_000_000)
                        samples.append(mbps)
                        sample_start = now
                        sample_bytes = 0

                except socket.timeout:
                    break

            duration = time.time() - start_time
            throughput_mbps = (bytes_received * 8) / (duration * 1_000_000) if duration > 0 else 0

            return ThroughputResult(
                direction='download',
                bytes_transferred=bytes_received,
                duration_seconds=duration,
                throughput_mbps=round(throughput_mbps, 2),
                packets_sent=0,
                packets_received=bytes_received // self.buffer_size,
                packet_loss_percent=0,
                avg_latency_ms=0,
                jitter_ms=statistics.stdev(samples) if len(samples) > 1 else 0
            )

        finally:
            sock.close()

    def _tcp_upload_test(self) -> ThroughputResult:
        """TCP upload test implementation"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.test_duration + 5)

        try:
            sock.connect((self.server_host, self.server_port))

            # Send upload request
            request = struct.pack('!IBI', MAGIC_NUMBER, PacketType.DATA.value, self.test_duration)
            sock.sendall(request)

            # Send data for duration
            bytes_sent = 0
            start_time = time.time()
            end_time = start_time + self.test_duration

            # Track throughput samples
            samples = []
            sample_start = start_time
            sample_bytes = 0

            while time.time() < end_time:
                try:
                    sent = sock.send(self._test_data)
                    bytes_sent += sent
                    sample_bytes += sent

                    # Calculate per-second samples
                    now = time.time()
                    if now - sample_start >= 1.0:
                        mbps = (sample_bytes * 8) / ((now - sample_start) * 1_000_000)
                        samples.append(mbps)
                        sample_start = now
                        sample_bytes = 0

                except socket.timeout:
                    break
                except BrokenPipeError:
                    break

            duration = time.time() - start_time
            throughput_mbps = (bytes_sent * 8) / (duration * 1_000_000) if duration > 0 else 0

            return ThroughputResult(
                direction='upload',
                bytes_transferred=bytes_sent,
                duration_seconds=duration,
                throughput_mbps=round(throughput_mbps, 2),
                packets_sent=bytes_sent // self.buffer_size,
                packets_received=0,
                packet_loss_percent=0,
                avg_latency_ms=0,
                jitter_ms=statistics.stdev(samples) if len(samples) > 1 else 0
            )

        finally:
            sock.close()

    def _udp_download_test(self) -> ThroughputResult:
        """UDP download test - uses packet loss tracking"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)

        try:
            # Send download request to server
            request = struct.pack('!IBI', MAGIC_NUMBER, PacketType.HANDSHAKE.value, self.test_duration)
            sock.sendto(request, (self.server_host, self.server_port))

            # Receive packets
            bytes_received = 0
            packets_received = 0
            expected_seq = 0
            lost_packets = 0
            latencies = []

            start_time = time.time()
            end_time = start_time + self.test_duration

            while time.time() < end_time:
                try:
                    data, addr = sock.recvfrom(65535)
                    receive_time = time.time()

                    if len(data) >= 12:
                        seq, timestamp = struct.unpack('!Id', data[:12])

                        # Track packet loss
                        if seq > expected_seq:
                            lost_packets += (seq - expected_seq)
                        expected_seq = seq + 1

                        # Track latency
                        latency = (receive_time - timestamp) * 1000
                        if latency > 0 and latency < 10000:  # Sanity check
                            latencies.append(latency)

                    bytes_received += len(data)
                    packets_received += 1

                except socket.timeout:
                    continue

            duration = time.time() - start_time
            throughput_mbps = (bytes_received * 8) / (duration * 1_000_000) if duration > 0 else 0

            total_expected = packets_received + lost_packets
            packet_loss = (lost_packets / total_expected * 100) if total_expected > 0 else 0

            return ThroughputResult(
                direction='download',
                bytes_transferred=bytes_received,
                duration_seconds=duration,
                throughput_mbps=round(throughput_mbps, 2),
                packets_sent=0,
                packets_received=packets_received,
                packet_loss_percent=round(packet_loss, 2),
                avg_latency_ms=round(statistics.mean(latencies), 2) if latencies else 0,
                jitter_ms=round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0
            )

        finally:
            sock.close()

    def _udp_upload_test(self) -> ThroughputResult:
        """UDP upload test"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            bytes_sent = 0
            packets_sent = 0
            seq = 0

            start_time = time.time()
            end_time = start_time + self.test_duration

            # Create packet with sequence and timestamp
            packet_size = min(1400, self.buffer_size)  # MTU safe
            payload_size = packet_size - 12  # Header size

            while time.time() < end_time:
                timestamp = time.time()
                header = struct.pack('!Id', seq, timestamp)
                packet = header + os.urandom(payload_size)

                try:
                    sock.sendto(packet, (self.server_host, self.server_port))
                    bytes_sent += len(packet)
                    packets_sent += 1
                    seq += 1

                    # Small delay to avoid overwhelming the network
                    time.sleep(0.0001)

                except Exception:
                    continue

            duration = time.time() - start_time
            throughput_mbps = (bytes_sent * 8) / (duration * 1_000_000) if duration > 0 else 0

            return ThroughputResult(
                direction='upload',
                bytes_transferred=bytes_sent,
                duration_seconds=duration,
                throughput_mbps=round(throughput_mbps, 2),
                packets_sent=packets_sent,
                packets_received=0,
                packet_loss_percent=0,  # Would need server feedback
                avg_latency_ms=0,
                jitter_ms=0
            )

        finally:
            sock.close()

    def _log_result(self, direction: str, result: ThroughputResult):
        """Log test result to CSV"""
        self.csv_logger.append({
            'timestamp': datetime.now().isoformat(),
            'server': f"{self.server_host}:{self.server_port}",
            'direction': direction,
            'protocol': 'TCP' if self.use_tcp else 'UDP',
            'duration_seconds': result.duration_seconds,
            'bytes_transferred': result.bytes_transferred,
            'throughput_mbps': result.throughput_mbps,
            'avg_throughput_mbps': result.throughput_mbps,
            'packets_sent': result.packets_sent,
            'packets_received': result.packets_received,
            'packet_loss_percent': result.packet_loss_percent,
            'jitter_ms': result.jitter_ms
        })

    def _get_quality_rating(self, download_mbps: float, upload_mbps: float) -> str:
        """Determine quality rating based on throughput"""
        # Use the lower of the two for rating
        min_speed = min(download_mbps, upload_mbps)

        if min_speed >= 100:
            return 'excellent'
        elif min_speed >= 50:
            return 'good'
        elif min_speed >= 25:
            return 'acceptable'
        elif min_speed >= 10:
            return 'fair'
        elif min_speed >= 1:
            return 'poor'
        else:
            return 'bad'

    # ==================== Public API Methods ====================

    def set_server(self, host: str, port: int = THROUGHPUT_PORT):
        """Set the throughput test server"""
        self.server_host = host
        self.server_port = port
        logger.info(f"Throughput server set to {host}:{port}")

    def get_history(self) -> List[Dict[str, Any]]:
        """Get test history"""
        return list(self.test_history)

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics from history"""
        if not self.test_history:
            return {
                'total_tests': 0,
                'avg_download_mbps': 0,
                'avg_upload_mbps': 0
            }

        downloads = [t.get('download_mbps', 0) for t in self.test_history if t.get('download_mbps')]
        uploads = [t.get('upload_mbps', 0) for t in self.test_history if t.get('upload_mbps')]

        return {
            'total_tests': len(self.test_history),
            'avg_download_mbps': round(statistics.mean(downloads), 2) if downloads else 0,
            'max_download_mbps': round(max(downloads), 2) if downloads else 0,
            'avg_upload_mbps': round(statistics.mean(uploads), 2) if uploads else 0,
            'max_upload_mbps': round(max(uploads), 2) if uploads else 0
        }

    def run_quick_test(self, duration: int = 5) -> Dict[str, Any]:
        """Run a quick throughput test with shorter duration"""
        original_duration = self.test_duration
        self.test_duration = duration

        try:
            return self.run_full_test()
        finally:
            self.test_duration = original_duration


# ==================== Throughput Test Server ====================

class ThroughputServer:
    """
    Throughput test server for enterprise bandwidth testing.

    Deploy on fleet server to allow agents to measure throughput
    to internal infrastructure.
    """

    def __init__(
        self,
        host: str = '0.0.0.0',
        tcp_port: int = THROUGHPUT_PORT,
        buffer_size: int = 128 * 1024
    ):
        self.host = host
        self.tcp_port = tcp_port
        self.buffer_size = buffer_size
        self._running = False
        self._tcp_thread: Optional[threading.Thread] = None
        self._tcp_socket: Optional[socket.socket] = None
        self._test_data = os.urandom(buffer_size)

        # Statistics
        self._stats = {
            'total_tests': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0
        }

    def start(self):
        """Start the throughput server"""
        if self._running:
            return

        self._running = True

        # Start TCP server
        self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_socket.bind((self.host, self.tcp_port))
        self._tcp_socket.listen(10)
        self._tcp_socket.settimeout(1.0)

        self._tcp_thread = threading.Thread(target=self._tcp_serve_loop, daemon=True)
        self._tcp_thread.start()

        logger.info(f"Throughput Server started on TCP {self.host}:{self.tcp_port}")

    def stop(self):
        """Stop the throughput server"""
        self._running = False

        if self._tcp_thread:
            self._tcp_thread.join(timeout=2)
        if self._tcp_socket:
            self._tcp_socket.close()

        logger.info("Throughput Server stopped")

    def _tcp_serve_loop(self):
        """TCP server main loop"""
        while self._running:
            try:
                conn, addr = self._tcp_socket.accept()
                # Handle each connection in a new thread
                threading.Thread(
                    target=self._handle_tcp_client,
                    args=(conn, addr),
                    daemon=True
                ).start()

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.error(f"TCP server error: {e}")

    def _handle_tcp_client(self, conn: socket.socket, addr: Tuple[str, int]):
        """Handle a single TCP client connection"""
        conn.settimeout(60)

        try:
            # Read request header
            header = conn.recv(9)
            if len(header) < 9:
                return

            magic, packet_type, duration = struct.unpack('!IBI', header)

            if magic != MAGIC_NUMBER:
                logger.warning(f"Invalid magic number from {addr}")
                return

            if packet_type == PacketType.HANDSHAKE.value:
                # Download request - send data to client
                self._send_data_to_client(conn, duration)

            elif packet_type == PacketType.DATA.value:
                # Upload request - receive data from client
                self._receive_data_from_client(conn, duration)

            self._stats['total_tests'] += 1

        except Exception as e:
            logger.debug(f"Client handler error: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _send_data_to_client(self, conn: socket.socket, duration: int):
        """Send test data to client for download test"""
        start_time = time.time()
        end_time = start_time + duration
        bytes_sent = 0

        while time.time() < end_time:
            try:
                sent = conn.send(self._test_data)
                bytes_sent += sent
            except Exception:
                break

        self._stats['total_bytes_sent'] += bytes_sent

    def _receive_data_from_client(self, conn: socket.socket, duration: int):
        """Receive test data from client for upload test"""
        start_time = time.time()
        end_time = start_time + duration
        bytes_received = 0

        while time.time() < end_time:
            try:
                data = conn.recv(self.buffer_size)
                if not data:
                    break
                bytes_received += len(data)
            except Exception:
                break

        self._stats['total_bytes_received'] += bytes_received

    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return self._stats.copy()


# ==================== Singleton Access ====================

_throughput_tester: Optional[ThroughputTester] = None
_tester_lock = threading.Lock()


def get_throughput_tester(server_host: str = None) -> ThroughputTester:
    """Get or create singleton throughput tester instance"""
    global _throughput_tester

    with _tester_lock:
        if _throughput_tester is None:
            _throughput_tester = ThroughputTester(server_host=server_host)

    return _throughput_tester
