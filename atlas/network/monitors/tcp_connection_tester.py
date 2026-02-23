"""
TCP Connection Rate Tester - Network Capacity Testing

Measures TCP connection establishment rate (connections per second - CPS)
to assess network and firewall capacity for handling new connections.

This is important for:
- Web server capacity planning
- Firewall/NAT performance assessment
- SD-WAN and proxy throughput evaluation
- Load balancer validation

Based on concepts from Keysight CyPerf's connection rate testing.
"""

import socket
import threading
import time
import logging
import statistics
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from atlas.network.monitors.base import BaseNetworkMonitor
from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

# Default test endpoints
DEFAULT_TEST_ENDPOINTS = [
    ('www.google.com', 443, True),      # HTTPS
    ('www.cloudflare.com', 443, True),  # HTTPS
    ('www.amazon.com', 443, True),      # HTTPS
]


@dataclass
class ConnectionResult:
    """Result of a single connection attempt"""
    success: bool
    connect_time_ms: float
    error: Optional[str] = None
    tls_time_ms: Optional[float] = None


class TCPConnectionTester(BaseNetworkMonitor):
    """
    Test TCP connection establishment rate.

    Features:
    - Concurrent connection testing
    - Connection latency measurement
    - TLS handshake timing
    - Configurable connection count and rate
    - Historical tracking and analysis
    """

    def __init__(
        self,
        test_endpoints: List[Tuple[str, int, bool]] = None,
        connections_per_test: int = 20,
        max_concurrent: int = 10,
        timeout_seconds: float = 5.0,
        include_tls: bool = True
    ):
        """
        Initialize TCP Connection Tester.

        Args:
            test_endpoints: List of (host, port, use_tls) tuples
            connections_per_test: Total connections per test cycle
            max_concurrent: Maximum concurrent connection attempts
            timeout_seconds: Connection timeout
            include_tls: Whether to measure TLS handshake time
        """
        self.test_endpoints = test_endpoints or DEFAULT_TEST_ENDPOINTS
        self.connections_per_test = connections_per_test
        self.max_concurrent = max_concurrent
        self.timeout = timeout_seconds
        self.include_tls = include_tls

        # Results tracking
        self.test_history: List[Dict[str, Any]] = []
        self.max_history = 100

        # Initialize base class
        super().__init__()

        # Initialize CSV logger
        log_dir = Path.home()
        self.csv_logger = CSVLogger(
            log_file=str(log_dir / 'tcp_connection_rate.csv'),
            fieldnames=[
                'timestamp', 'total_connections', 'successful', 'failed',
                'success_rate_percent', 'connections_per_second',
                'avg_connect_time_ms', 'min_connect_time_ms', 'max_connect_time_ms',
                'avg_tls_time_ms', 'p95_connect_time_ms'
            ],
            max_history=500,
            retention_days=7
        )

        # Initialize last_result
        self.last_result = {
            'status': 'idle',
            'timestamp': None,
            'connections_per_second': 0,
            'success_rate_percent': 0,
            'avg_connect_time_ms': 0,
            'quality_rating': 'unknown'
        }

    def get_monitor_name(self) -> str:
        return "TCP Connection Tester"

    def get_default_interval(self) -> int:
        """Default interval: 10 minutes between tests"""
        return 600

    def _run_monitoring_cycle(self):
        """Execute one TCP connection rate test cycle"""
        try:
            result = self._run_connection_test()
            self.update_last_result(result)

            # Log to CSV
            self.csv_logger.append({
                'timestamp': datetime.now().isoformat(),
                'total_connections': result.get('total_connections', 0),
                'successful': result.get('successful_connections', 0),
                'failed': result.get('failed_connections', 0),
                'success_rate_percent': result.get('success_rate_percent', 0),
                'connections_per_second': result.get('connections_per_second', 0),
                'avg_connect_time_ms': result.get('avg_connect_time_ms', 0),
                'min_connect_time_ms': result.get('min_connect_time_ms', 0),
                'max_connect_time_ms': result.get('max_connect_time_ms', 0),
                'avg_tls_time_ms': result.get('avg_tls_time_ms', 0),
                'p95_connect_time_ms': result.get('p95_connect_time_ms', 0)
            })

            # Add to history
            self.test_history.append(result)
            if len(self.test_history) > self.max_history:
                self.test_history = self.test_history[-self.max_history:]

            # Log to fleet
            self.log_to_fleet('tcp_connection_rate', result)

            logger.info(
                f"TCP Connection Test: {result['successful_connections']}/{result['total_connections']} "
                f"({result['connections_per_second']:.1f} CPS), "
                f"avg={result['avg_connect_time_ms']:.1f}ms"
            )

        except Exception as e:
            logger.error(f"TCP connection test failed: {e}")
            self.update_last_result({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    def _run_connection_test(self) -> Dict[str, Any]:
        """
        Run a complete TCP connection rate test.

        Establishes multiple connections concurrently and measures:
        - Connection success rate
        - Connection establishment time
        - TLS handshake time (if applicable)
        - Connections per second

        Returns:
            Dictionary with test results
        """
        results: List[ConnectionResult] = []
        start_time = time.time()

        # Distribute connections across endpoints
        connection_tasks = []
        for i in range(self.connections_per_test):
            endpoint = self.test_endpoints[i % len(self.test_endpoints)]
            connection_tasks.append(endpoint)

        # Run connections concurrently
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {
                executor.submit(
                    self._test_single_connection, host, port, use_tls
                ): (host, port)
                for host, port, use_tls in connection_tasks
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ConnectionResult(
                        success=False,
                        connect_time_ms=0,
                        error=str(e)
                    ))

        total_time = time.time() - start_time

        # Calculate metrics
        return self._calculate_metrics(results, total_time)

    def _test_single_connection(
        self,
        host: str,
        port: int,
        use_tls: bool
    ) -> ConnectionResult:
        """
        Test a single TCP connection.

        Args:
            host: Target hostname
            port: Target port
            use_tls: Whether to perform TLS handshake

        Returns:
            ConnectionResult with timing information
        """
        sock = None
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            # Measure TCP connection time
            connect_start = time.time()

            # Resolve and connect
            sock.connect((host, port))

            connect_time = (time.time() - connect_start) * 1000

            tls_time = None

            # TLS handshake if requested
            if use_tls and self.include_tls:
                tls_start = time.time()
                context = ssl.create_default_context()
                wrapped_sock = context.wrap_socket(sock, server_hostname=host)
                tls_time = (time.time() - tls_start) * 1000
                wrapped_sock.close()
                sock = None  # Already closed by wrapped_sock
            else:
                sock.close()
                sock = None

            return ConnectionResult(
                success=True,
                connect_time_ms=connect_time,
                tls_time_ms=tls_time
            )

        except socket.timeout:
            return ConnectionResult(
                success=False,
                connect_time_ms=self.timeout * 1000,
                error='Connection timeout'
            )
        except socket.gaierror as e:
            return ConnectionResult(
                success=False,
                connect_time_ms=0,
                error=f'DNS resolution failed: {e}'
            )
        except ConnectionRefusedError:
            return ConnectionResult(
                success=False,
                connect_time_ms=0,
                error='Connection refused'
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                connect_time_ms=0,
                error=str(e)
            )
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _calculate_metrics(
        self,
        results: List[ConnectionResult],
        total_time: float
    ) -> Dict[str, Any]:
        """
        Calculate test metrics from connection results.

        Args:
            results: List of ConnectionResult objects
            total_time: Total test duration in seconds

        Returns:
            Dictionary with calculated metrics
        """
        total = len(results)
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        # Connection times
        connect_times = [r.connect_time_ms for r in successful if r.connect_time_ms > 0]
        tls_times = [r.tls_time_ms for r in successful if r.tls_time_ms is not None]

        # Calculate statistics
        if connect_times:
            avg_connect = statistics.mean(connect_times)
            min_connect = min(connect_times)
            max_connect = max(connect_times)
            sorted_times = sorted(connect_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95_connect = sorted_times[min(p95_index, len(sorted_times) - 1)]
        else:
            avg_connect = min_connect = max_connect = p95_connect = 0

        if tls_times:
            avg_tls = statistics.mean(tls_times)
        else:
            avg_tls = 0

        # Connections per second
        if total_time > 0:
            cps = len(successful) / total_time
        else:
            cps = 0

        # Success rate
        success_rate = (len(successful) / total) * 100 if total > 0 else 0

        # Quality rating based on CPS and success rate
        quality_rating = self._get_quality_rating(cps, success_rate, avg_connect)

        # Error breakdown
        error_counts: Dict[str, int] = {}
        for r in failed:
            error = r.error or 'Unknown error'
            error_counts[error] = error_counts.get(error, 0) + 1

        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'total_connections': total,
            'successful_connections': len(successful),
            'failed_connections': len(failed),
            'success_rate_percent': round(success_rate, 2),
            'connections_per_second': round(cps, 2),
            'test_duration_seconds': round(total_time, 2),
            'avg_connect_time_ms': round(avg_connect, 2),
            'min_connect_time_ms': round(min_connect, 2),
            'max_connect_time_ms': round(max_connect, 2),
            'p95_connect_time_ms': round(p95_connect, 2),
            'avg_tls_time_ms': round(avg_tls, 2),
            'quality_rating': quality_rating,
            'error_breakdown': error_counts,
            'endpoints_tested': [f"{h}:{p}" for h, p, _ in self.test_endpoints]
        }

    def _get_quality_rating(
        self,
        cps: float,
        success_rate: float,
        avg_latency: float
    ) -> str:
        """
        Determine quality rating based on metrics.

        Args:
            cps: Connections per second
            success_rate: Success percentage
            avg_latency: Average connection time in ms

        Returns:
            Quality rating string
        """
        score = 100

        # Penalize low success rate heavily
        if success_rate < 90:
            score -= (100 - success_rate) * 2
        elif success_rate < 95:
            score -= (100 - success_rate)

        # Penalize high latency
        if avg_latency > 500:
            score -= 30
        elif avg_latency > 200:
            score -= 15
        elif avg_latency > 100:
            score -= 5

        # Bonus for high CPS
        if cps >= 10:
            score = min(100, score + 10)
        elif cps >= 5:
            score = min(100, score + 5)

        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'good'
        elif score >= 50:
            return 'acceptable'
        elif score >= 25:
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
                'avg_cps': 0,
                'avg_success_rate': 0
            }

        cps_values = [t.get('connections_per_second', 0) for t in self.test_history]
        success_rates = [t.get('success_rate_percent', 0) for t in self.test_history]
        connect_times = [t.get('avg_connect_time_ms', 0) for t in self.test_history]

        return {
            'total_tests': len(self.test_history),
            'avg_cps': round(statistics.mean(cps_values), 2),
            'max_cps': round(max(cps_values), 2),
            'avg_success_rate': round(statistics.mean(success_rates), 2),
            'avg_connect_time_ms': round(statistics.mean(connect_times), 2)
        }

    def add_endpoint(self, host: str, port: int, use_tls: bool = True):
        """Add a test endpoint"""
        self.test_endpoints.append((host, port, use_tls))
        logger.info(f"Added endpoint: {host}:{port} (TLS={use_tls})")

    def set_endpoints(self, endpoints: List[Tuple[str, int, bool]]):
        """Replace test endpoints"""
        self.test_endpoints = endpoints
        logger.info(f"Set {len(endpoints)} test endpoints")

    def run_single_test(self) -> Dict[str, Any]:
        """Run a single test immediately (outside monitoring loop)"""
        return self._run_connection_test()


# ==================== Connection Rate Test Server ====================

class ConnectionTestServer:
    """
    Simple TCP server for connection rate testing.

    Can be deployed on the fleet server to allow agents to measure
    connection rate to internal infrastructure.
    """

    def __init__(self, host: str = '0.0.0.0', port: int = 5006):
        self.host = host
        self.port = port
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None
        self._stats = {
            'total_connections': 0,
            'connections_per_second': 0,
            'last_minute_connections': 0
        }
        self._connection_times: List[float] = []

    def start(self):
        """Start the test server"""
        if self._running:
            return

        self._running = True
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.host, self.port))
        self._socket.listen(100)
        self._socket.settimeout(1.0)

        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()

        logger.info(f"TCP Connection Test Server started on {self.host}:{self.port}")

    def stop(self):
        """Stop the test server"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._socket:
            self._socket.close()
        logger.info("TCP Connection Test Server stopped")

    def _serve_loop(self):
        """Main server loop - accept and immediately close connections"""
        while self._running:
            try:
                conn, addr = self._socket.accept()
                conn.close()

                # Track statistics
                now = time.time()
                self._connection_times.append(now)
                self._stats['total_connections'] += 1

                # Clean old timestamps (keep last minute)
                cutoff = now - 60
                self._connection_times = [t for t in self._connection_times if t > cutoff]
                self._stats['last_minute_connections'] = len(self._connection_times)
                self._stats['connections_per_second'] = len(self._connection_times) / 60.0

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.debug(f"Connection Test Server error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return self._stats.copy()


# ==================== Singleton Access ====================

_tcp_connection_tester: Optional[TCPConnectionTester] = None
_tester_lock = threading.Lock()


def get_tcp_connection_tester() -> TCPConnectionTester:
    """Get or create singleton TCP connection tester instance"""
    global _tcp_connection_tester

    with _tester_lock:
        if _tcp_connection_tester is None:
            _tcp_connection_tester = TCPConnectionTester()

    return _tcp_connection_tester
