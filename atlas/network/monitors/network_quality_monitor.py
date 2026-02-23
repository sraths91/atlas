"""
Network Quality Monitor - Advanced network quality metrics

Monitors:
- TCP retransmission rates
- Packet reordering
- DNS query latency (multiple resolvers)
- TLS handshake latency
- HTTP/HTTPS response times
- MTU path discovery issues
"""

import logging
import subprocess
import re
import time
import threading
import socket
import ssl
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import statistics

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

class NetworkQualityMonitor:
    """Monitor advanced network quality metrics"""

    # DNS resolvers to test
    DNS_RESOLVERS = {
        'cloudflare_primary': '1.1.1.1',
        'cloudflare_secondary': '1.0.0.1',
        'google_primary': '8.8.8.8',
        'google_secondary': '8.8.4.4',
        'quad9': '9.9.9.9',
    }

    # Test domains for DNS queries
    TEST_DOMAINS = [
        'google.com',
        'cloudflare.com',
        'amazon.com',
        'microsoft.com'
    ]

    # Test endpoints for HTTP/TLS checks
    TEST_HTTPS_ENDPOINTS = [
        'https://www.google.com',
        'https://www.cloudflare.com',
        'https://www.amazon.com'
    ]

    def __init__(self, sample_interval: int = 60):
        """
        Initialize network quality monitor

        Args:
            sample_interval: Seconds between samples (default: 60)
        """
        self.sample_interval = sample_interval
        self._running = False
        self._thread = None

        # CSV Loggers
        log_dir = Path.home()
        self.tcp_stats_logger = CSVLogger(
            str(log_dir / 'network_tcp_stats.csv'),
            fieldnames=['timestamp', 'retransmit_segs', 'out_of_order_segs',
                    'failed_connection_attempts', 'connection_resets',
                    'retransmit_rate_percent'],
            retention_days=7,
            max_history=1000
        )

        self.dns_logger = CSVLogger(
            str(log_dir / 'network_dns_quality.csv'),
            fieldnames=['timestamp', 'resolver_name', 'resolver_ip', 'test_domain',
                    'query_time_ms', 'success', 'error'],
            retention_days=7,
            max_history=2000
        )

        self.tls_logger = CSVLogger(
            str(log_dir / 'network_tls_quality.csv'),
            fieldnames=['timestamp', 'endpoint', 'handshake_time_ms',
                    'tls_version', 'cipher', 'success', 'error'],
            retention_days=7,
            max_history=1000
        )

        self.http_logger = CSVLogger(
            str(log_dir / 'network_http_quality.csv'),
            fieldnames=['timestamp', 'endpoint', 'response_time_ms',
                    'status_code', 'success', 'error'],
            retention_days=7,
            max_history=1000
        )

        # Previous TCP stats for calculating rates
        self._prev_tcp_stats = None

    def start(self):
        """Start monitoring network quality"""
        if self._running:
            logger.warning("Network quality monitor already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Network quality monitor started with {self.sample_interval}s interval")

    def stop(self):
        """Stop monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Network quality monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                current_time = datetime.now()

                # Collect TCP statistics
                self._collect_tcp_stats(current_time)

                # Test DNS resolvers (sample 2 domains per cycle)
                self._test_dns_resolvers(current_time)

                # Test TLS handshakes (sample 1 endpoint per cycle)
                self._test_tls_handshake(current_time)

                # Test HTTP response times (sample 1 endpoint per cycle)
                self._test_http_response(current_time)

            except Exception as e:
                logger.error(f"Error in network quality monitoring loop: {e}")

            time.sleep(self.sample_interval)

    def _collect_tcp_stats(self, current_time: datetime):
        """Collect TCP statistics from netstat"""
        try:
            result = subprocess.run(['netstat', '-s', '-p', 'tcp'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return

            stats = self._parse_tcp_stats(result.stdout)
            if not stats:
                return

            # Calculate retransmission rate
            retransmit_rate = 0
            if self._prev_tcp_stats:
                prev_retrans = self._prev_tcp_stats.get('retransmit_segs', 0)
                prev_total = self._prev_tcp_stats.get('data_packets_sent', 0)
                curr_retrans = stats.get('retransmit_segs', 0)
                curr_total = stats.get('data_packets_sent', 0)

                delta_retrans = curr_retrans - prev_retrans
                delta_total = curr_total - prev_total

                if delta_total > 0:
                    retransmit_rate = (delta_retrans / delta_total) * 100

            self.tcp_stats_logger.append({
                'timestamp': current_time.isoformat(),
                'retransmit_segs': stats.get('retransmit_segs', 0),
                'out_of_order_segs': stats.get('out_of_order_segs', 0),
                'failed_connection_attempts': stats.get('failed_connection_attempts', 0),
                'connection_resets': stats.get('connection_resets', 0),
                'retransmit_rate_percent': round(retransmit_rate, 4)
            })

            self._prev_tcp_stats = stats

        except Exception as e:
            logger.error(f"Error collecting TCP stats: {e}")

    def _parse_tcp_stats(self, netstat_output: str) -> dict:
        """Parse TCP statistics from netstat output"""
        stats = {}

        patterns = {
            'data_packets_sent': r'(\d+) data packets sent',
            'retransmit_segs': r'(\d+) data packets? retransmitted',
            'out_of_order_segs': r'(\d+) out-of-order packets? received',
            'failed_connection_attempts': r'(\d+) connection requests?',
            'connection_resets': r'(\d+) connections? reset',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, netstat_output)
            if match:
                stats[key] = int(match.group(1))

        return stats

    def _test_dns_resolvers(self, current_time: datetime):
        """Test DNS query latency for all configured resolvers"""
        # Sample 2 random domains per cycle to reduce load
        import random
        test_domains = random.sample(self.TEST_DOMAINS, min(2, len(self.TEST_DOMAINS)))

        for resolver_name, resolver_ip in self.DNS_RESOLVERS.items():
            for domain in test_domains:
                try:
                    result = self._query_dns(domain, resolver_ip)

                    self.dns_logger.append({
                        'timestamp': current_time.isoformat(),
                        'resolver_name': resolver_name,
                        'resolver_ip': resolver_ip,
                        'test_domain': domain,
                        'query_time_ms': result.get('query_time_ms', 0),
                        'success': result.get('success', False),
                        'error': result.get('error', '')
                    })

                except Exception as e:
                    logger.error(f"Error testing DNS resolver {resolver_name}: {e}")

    def _query_dns(self, domain: str, resolver: str, timeout: int = 3) -> dict:
        """Query DNS resolver and measure response time"""
        result = {
            'success': False,
            'query_time_ms': 0,
            'error': ''
        }

        try:
            start_time = time.time()

            # Use dig command for accurate DNS timing
            cmd = ['dig', f'@{resolver}', domain, '+time=3', '+tries=1']
            proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            query_time = (time.time() - start_time) * 1000
            result['query_time_ms'] = round(query_time, 2)

            if proc_result.returncode == 0 and 'ANSWER:' in proc_result.stdout:
                result['success'] = True
            else:
                result['error'] = 'Query failed or no answer'

        except subprocess.TimeoutExpired:
            result['error'] = 'DNS query timeout'
        except Exception as e:
            result['error'] = str(e)

        return result

    def _test_tls_handshake(self, current_time: datetime):
        """Test TLS handshake performance"""
        # Sample 1 endpoint per cycle
        import random
        endpoint = random.choice(self.TEST_HTTPS_ENDPOINTS)

        try:
            result = self._measure_tls_handshake(endpoint)

            self.tls_logger.append({
                'timestamp': current_time.isoformat(),
                'endpoint': endpoint,
                'handshake_time_ms': result.get('handshake_time_ms', 0),
                'tls_version': result.get('tls_version', ''),
                'cipher': result.get('cipher', ''),
                'success': result.get('success', False),
                'error': result.get('error', '')
            })

        except Exception as e:
            logger.error(f"Error testing TLS handshake for {endpoint}: {e}")

    def _measure_tls_handshake(self, url: str, timeout: int = 5) -> dict:
        """Measure TLS handshake time"""
        result = {
            'success': False,
            'handshake_time_ms': 0,
            'tls_version': '',
            'cipher': '',
            'error': ''
        }

        try:
            # Parse URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or 443

            # Create socket and wrap with SSL
            start_time = time.time()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            context = ssl.create_default_context()
            wrapped_sock = context.wrap_socket(sock, server_hostname=hostname)

            try:
                wrapped_sock.connect((hostname, port))
                handshake_time = (time.time() - start_time) * 1000

                result['handshake_time_ms'] = round(handshake_time, 2)
                result['tls_version'] = wrapped_sock.version() or 'Unknown'
                result['cipher'] = wrapped_sock.cipher()[0] if wrapped_sock.cipher() else 'Unknown'
                result['success'] = True

            finally:
                wrapped_sock.close()

        except socket.timeout:
            result['error'] = 'TLS handshake timeout'
        except Exception as e:
            result['error'] = str(e)

        return result

    def _test_http_response(self, current_time: datetime):
        """Test HTTP response time"""
        # Sample 1 endpoint per cycle
        import random
        endpoint = random.choice(self.TEST_HTTPS_ENDPOINTS)

        try:
            result = self._measure_http_response(endpoint)

            self.http_logger.append({
                'timestamp': current_time.isoformat(),
                'endpoint': endpoint,
                'response_time_ms': result.get('response_time_ms', 0),
                'status_code': result.get('status_code', 0),
                'success': result.get('success', False),
                'error': result.get('error', '')
            })

        except Exception as e:
            logger.error(f"Error testing HTTP response for {endpoint}: {e}")

    def _measure_http_response(self, url: str, timeout: int = 10) -> dict:
        """Measure HTTP response time using curl"""
        result = {
            'success': False,
            'response_time_ms': 0,
            'status_code': 0,
            'error': ''
        }

        try:
            # Use curl for accurate timing
            cmd = [
                'curl', '-s', '-o', '/dev/null', '-w',
                '%{http_code},%{time_total}',
                '--max-time', str(timeout),
                url
            ]

            proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)

            if proc_result.returncode == 0:
                parts = proc_result.stdout.strip().split(',')
                if len(parts) == 2:
                    result['status_code'] = int(parts[0])
                    result['response_time_ms'] = round(float(parts[1]) * 1000, 2)
                    result['success'] = 200 <= result['status_code'] < 400
            else:
                result['error'] = 'HTTP request failed'

        except subprocess.TimeoutExpired:
            result['error'] = 'HTTP request timeout'
        except Exception as e:
            result['error'] = str(e)

        return result

    def get_quality_summary(self) -> dict:
        """Get network quality summary statistics"""
        summary = {
            'tcp': self._get_tcp_summary(),
            'dns': self._get_dns_summary(),
            'tls': self._get_tls_summary(),
            'http': self._get_http_summary()
        }
        return summary

    def _get_tcp_summary(self) -> dict:
        """Get TCP quality summary"""
        recent = self.tcp_stats_logger.get_history()
        if not recent:
            return {}

        rates = [float(e.get('retransmit_rate_percent', 0)) for e in recent if e.get('retransmit_rate_percent')]

        if rates:
            return {
                'avg_retransmit_rate_percent': round(statistics.mean(rates), 4),
                'max_retransmit_rate_percent': round(max(rates), 4),
                'sample_count': len(rates)
            }
        return {}

    def _get_dns_summary(self) -> dict:
        """Get DNS quality summary"""
        recent = self.dns_logger.get_history()
        if not recent:
            return {}

        successful = [e for e in recent if e.get('success')]
        if not successful:
            return {'availability_percent': 0}

        times = [float(e.get('query_time_ms', 0)) for e in successful]

        # Per-resolver breakdown
        resolver_data = {}
        for entry in recent:
            name = entry.get('resolver_name', 'Unknown')
            if name not in resolver_data:
                resolver_data[name] = {'total': 0, 'success': 0, 'times': []}
            resolver_data[name]['total'] += 1
            if entry.get('success'):
                resolver_data[name]['success'] += 1
                resolver_data[name]['times'].append(float(entry.get('query_time_ms', 0)))

        resolvers = []
        for name, data in resolver_data.items():
            avg_latency = round(statistics.mean(data['times']), 2) if data['times'] else 0
            availability = round(data['success'] / data['total'] * 100, 1) if data['total'] > 0 else 0
            resolvers.append({
                'name': name,
                'latency': avg_latency,
                'availability': availability
            })

        return {
            'availability_percent': round(len(successful) / len(recent) * 100, 2),
            'avg_query_time_ms': round(statistics.mean(times), 2) if times else 0,
            'max_query_time_ms': round(max(times), 2) if times else 0,
            'sample_count': len(recent),
            'resolvers': resolvers
        }

    def _get_tls_summary(self) -> dict:
        """Get TLS handshake summary"""
        recent = self.tls_logger.get_history()
        if not recent:
            return {}

        successful = [e for e in recent if e.get('success')]
        if not successful:
            return {'success_rate_percent': 0}

        times = [float(e.get('handshake_time_ms', 0)) for e in successful]

        return {
            'success_rate_percent': round(len(successful) / len(recent) * 100, 2),
            'avg_handshake_time_ms': round(statistics.mean(times), 2) if times else 0,
            'max_handshake_time_ms': round(max(times), 2) if times else 0,
            'sample_count': len(recent)
        }

    def _get_http_summary(self) -> dict:
        """Get HTTP response time summary"""
        recent = self.http_logger.get_history()
        if not recent:
            return {}

        successful = [e for e in recent if e.get('success')]
        if not successful:
            return {'success_rate_percent': 0}

        times = [float(e.get('response_time_ms', 0)) for e in successful]

        return {
            'success_rate_percent': round(len(successful) / len(recent) * 100, 2),
            'avg_response_time_ms': round(statistics.mean(times), 2) if times else 0,
            'max_response_time_ms': round(max(times), 2) if times else 0,
            'sample_count': len(recent)
        }


# Singleton instance
_network_quality_monitor_instance = None
_monitor_lock = threading.Lock()

def get_network_quality_monitor(sample_interval: int = 60) -> NetworkQualityMonitor:
    """Get or create singleton network quality monitor instance"""
    global _network_quality_monitor_instance

    with _monitor_lock:
        if _network_quality_monitor_instance is None:
            _network_quality_monitor_instance = NetworkQualityMonitor(sample_interval=sample_interval)
            _network_quality_monitor_instance.start()

        return _network_quality_monitor_instance
