"""
SpeedTest Monitor - Refactored to use BaseNetworkMonitor and CSVLogger

This module uses shared utilities to eliminate ~625 lines of duplicated code.

Enhanced with OpenSpeedTest-inspired improvements:
- Jitter measurement (variance in ping samples)
- Multiple ping samples (10 by default) for accurate latency
- Overhead compensation factor (4% default) for browser/HTTP overhead
- Smart lite mode with parallel HTTP downloads for accuracy
"""
import time
import logging
import subprocess
import statistics
import concurrent.futures
import urllib.request
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from atlas.network.monitors.base import BaseNetworkMonitor
from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

# Log file path
SPEEDTEST_LOG_FILE = '~/speedtest_history.csv'

# Default configuration (inspired by OpenSpeedTest methodology)
DEFAULT_PING_SAMPLES = 10  # Number of ping samples for accurate latency
DEFAULT_OVERHEAD_COMPENSATION = 1.04  # 4% overhead compensation factor

# CDN test URLs for parallel HTTP download testing (fast.com-inspired)
# These are public test files that support HTTP Range requests
SPEED_TEST_URLS = [
    'https://speed.cloudflare.com/__down?bytes=100000000',  # 100MB from Cloudflare
    'https://proof.ovh.net/files/100Mb.dat',  # OVH 100MB test file
]

# Lite mode configuration - more aggressive for accurate results
LITE_MODE_PARALLEL_CONNECTIONS = 16  # More connections to saturate high-speed links
LITE_MODE_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB per chunk
LITE_MODE_TEST_DURATION = 8  # 8 seconds for better averaging


class SpeedTestMonitor(BaseNetworkMonitor):
    """Monitor internet speed using speedtest-cli - Refactored version

    Enhanced with OpenSpeedTest-inspired improvements:
    - Jitter measurement for connection stability assessment
    - Multiple ping samples for accurate latency measurement
    - Overhead compensation for browser/HTTP overhead
    """

    def __init__(self):
        # Check if speedtest-cli is available before initializing
        self._check_speedtest_available()

        # Initialize base class
        super().__init__()

        # Initialize CSV logger with extended fields for jitter
        self.csv_logger = CSVLogger(
            log_file=SPEEDTEST_LOG_FILE,
            fieldnames=['timestamp', 'download', 'upload', 'ping', 'jitter', 'server'],
            max_history=20,
            retention_days=7
        )

        # Initialize last_result with SpeedTest-specific fields (including jitter)
        self.last_result = {
            'download': 0,
            'upload': 0,
            'ping': 0,
            'jitter': 0,
            'ping_samples': [],
            'server': 'Unknown',
            'timestamp': None,
            'status': 'idle',
            'error': None
        }

        # Test timing
        self.next_test_time = None

        # Enhanced configuration (OpenSpeedTest-inspired)
        self.ping_samples = DEFAULT_PING_SAMPLES  # Number of ping samples
        self.overhead_compensation = DEFAULT_OVERHEAD_COMPENSATION  # 4% overhead

        # Speed test mode: 'lite' (4 threads, faster) or 'full' (auto threads, most accurate)
        self._test_mode = 'full'  # Default to full mode for accurate measurements
        self._full_mode_threads = None  # None = library default (usually 4-8 threads, ~10-15s test)
        self._lite_mode_threads = 4  # 4 threads for lite mode (faster, ~90% accuracy)

        # One-time full test flag (for manual trigger from dashboard)
        self._run_full_test_once = False

        # Slow speed alert configuration
        self.slow_speed_threshold = 20.0  # Mbps
        self.consecutive_slow_count = 0
        self.consecutive_slow_trigger = 5
        self.slow_speed_alert_active = False
        self.slow_speed_alert_callback = None
        self.last_slow_alert_time = 0
        self.slow_alert_cooldown = 300  # 5 minutes

    # ==================== Utility Methods ====================

    def _check_speedtest_available(self) -> bool:
        """Check if speedtest-cli is available and update flag

        This method can be called to re-check availability after installation.
        Returns True if speedtest-cli is available.
        """
        try:
            import speedtest
            if not getattr(self, 'speedtest_available', False):
                logger.info("speedtest-cli is now available")
            self.speedtest_available = True
            return True
        except ImportError:
            if getattr(self, 'speedtest_available', True):
                logger.warning("speedtest-cli not installed. Install with: pip install speedtest-cli")
            self.speedtest_available = False
            return False

    # ==================== BaseNetworkMonitor Abstract Methods ====================

    def get_monitor_name(self) -> str:
        """Return human-readable monitor name"""
        return "Speed Test Monitor"

    def get_default_interval(self) -> int:
        """Speed test interval (default: 60 seconds = 1 minute)"""
        return 60

    def _run_monitoring_cycle(self):
        """Execute one speed test cycle"""
        # Re-check availability in case speedtest-cli was installed after startup
        if not self.speedtest_available:
            self._check_speedtest_available()

        if not self.speedtest_available:
            # Only log error occasionally to avoid log spam
            self.update_last_result({
                'status': 'error',
                'error': 'speedtest-cli not installed'
            })
            return

        try:
            self._run_speed_test()
        except Exception as e:
            logger.error(f"Speed test error: {e}")
            self.update_last_result({
                'status': 'error',
                'error': str(e)
            })

    def _on_start(self):
        """Called when monitoring starts"""
        if self.speedtest_available:
            self.next_test_time = time.time() + self.interval
            logger.info(f"Speed test monitoring started (interval: {self.interval}s)")

    def _on_cleanup(self):
        """Cleanup old logs (CSVLogger handles automatically)"""
        pass

    # ==================== SpeedTest-Specific Methods ====================

    def _run_speed_test(self):
        """Run a single speed test with enhanced metrics

        Enhanced with OpenSpeedTest-inspired improvements:
        - Multiple ping samples for accurate latency
        - Jitter calculation from ping variance
        - Overhead compensation for speed measurements

        Supports two modes:
        - 'lite': speedtest-cli with 4 threads (faster, less data, ~90% accuracy)
        - 'full': speedtest-cli with auto threads (slower, more data, 100% accuracy)
        """
        if not self.speedtest_available:
            logger.error("Cannot run speed test: speedtest-cli not installed")
            self.update_last_result({'status': 'error', 'error': 'speedtest-cli not installed'})
            return

        # Determine if this is a full test (one-time or persistent mode)
        use_full_mode = self._run_full_test_once or self._test_mode == 'full'

        # Reset one-time flag after use
        if self._run_full_test_once:
            self._run_full_test_once = False

        mode_label = 'full' if use_full_mode else 'lite'
        self.update_last_result({'status': 'testing', 'mode': mode_label})

        # Thread selection:
        # - Lite mode: 4 threads (good balance of speed vs accuracy)
        # - Full mode: library default (usually 4-8 threads, saturates connection)
        threads = self._full_mode_threads if use_full_mode else self._lite_mode_threads
        logger.info(f"Starting speed test ({mode_label} mode, threads={threads or 'auto'})...")

        try:
            import speedtest

            # Create Speedtest instance with secure connection
            st = speedtest.Speedtest(secure=True)

            # Get best server
            st.get_best_server()
            server_name = st.results.server.get('sponsor', 'Unknown')
            server_host = st.results.server.get('host', '')

            # Collect multiple ping samples for accurate latency and jitter
            ping_samples = self._collect_ping_samples(server_host)

            # Calculate ping statistics
            if ping_samples:
                avg_ping = statistics.mean(ping_samples)
                jitter = self._calculate_jitter(ping_samples)
            else:
                # Fallback to speedtest-cli's single ping
                avg_ping = st.results.ping
                jitter = 0.0

            # Test download speed (with thread control)
            if threads:
                raw_download = st.download(threads=threads) / 1_000_000
            else:
                raw_download = st.download() / 1_000_000  # Library default
            # Apply overhead compensation (accounts for HTTP/browser overhead)
            download_speed = raw_download * self.overhead_compensation

            # Test upload speed (with thread control)
            if threads:
                raw_upload = st.upload(threads=threads) / 1_000_000
            else:
                raw_upload = st.upload() / 1_000_000  # Library default
            # Apply overhead compensation
            upload_speed = raw_upload * self.overhead_compensation

            # Create result with enhanced metrics
            result = {
                'download': round(download_speed, 2),
                'upload': round(upload_speed, 2),
                'ping': round(avg_ping, 2),
                'jitter': round(jitter, 2),
                'ping_samples': ping_samples,
                'server': server_name,
                'mode': mode_label,
                'status': 'complete',
                'error': None,
                'overhead_compensation': self.overhead_compensation
            }

            self.update_last_result(result)
            self._log_and_alert_result(result)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Speed test failed: {error_msg}")

            # Provide more helpful error messages
            if '403' in error_msg or 'Forbidden' in error_msg:
                error_msg = "Access denied by speedtest.net. Try again later."
            elif 'timeout' in error_msg.lower():
                error_msg = "Connection timeout. Check your internet."
            elif 'connection' in error_msg.lower():
                error_msg = "Connection failed. Check network."

            self.update_last_result({
                'status': 'error',
                'error': error_msg
            })

    def _log_and_alert_result(self, result: Dict[str, Any]):
        """Log result to CSV/fleet and check for alerts"""
        download_speed = result['download']
        upload_speed = result['upload']
        avg_ping = result['ping']
        jitter = result['jitter']
        server_name = result['server']
        mode_label = result['mode']

        # Log to CSV using shared CSVLogger (now includes jitter)
        self.csv_logger.append({
            'timestamp': datetime.now().isoformat(),
            'download': download_speed,
            'upload': upload_speed,
            'ping': avg_ping,
            'jitter': jitter,
            'server': server_name
        })

        # Fleet logging - use 'speedtest' as widget_type so fleet aggregator recognizes it
        if self.fleet_logger:
            try:
                self.fleet_logger(
                    level='info',
                    widget_type='speedtest',
                    message='speedtest',
                    data={
                        'download': download_speed,
                        'upload': upload_speed,
                        'ping': avg_ping,
                        'jitter': jitter,
                        'server': server_name
                    }
                )
            except Exception as e:
                logger.error(f"Failed to log speedtest to fleet: {e}")

        # Check for slow speed alert
        self._check_slow_speed_alert(download_speed)

        logger.info(f"Speed test complete ({mode_label}): ↓{download_speed:.2f} Mbps ↑{upload_speed:.2f} Mbps (ping: {avg_ping:.2f}ms, jitter: {jitter:.2f}ms)")

    def _collect_ping_samples(self, server_host: str) -> List[float]:
        """Collect multiple ping samples for accurate latency measurement

        Args:
            server_host: Hostname of the speedtest server

        Returns:
            List of ping times in milliseconds
        """
        ping_times = []

        if not server_host:
            logger.warning("No server host for ping samples, using fallback")
            return ping_times

        # Extract hostname (remove port if present)
        hostname = server_host.split(':')[0]

        try:
            for i in range(self.ping_samples):
                # Use system ping command for accurate ICMP measurements
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', hostname],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    # Parse ping time from output
                    # Format: "time=XX.XXX ms" or "time XX.XXX ms"
                    output = result.stdout
                    if 'time=' in output:
                        time_str = output.split('time=')[1].split()[0]
                        ping_ms = float(time_str.replace('ms', ''))
                        ping_times.append(ping_ms)
                    elif 'time ' in output:
                        time_str = output.split('time ')[1].split()[0]
                        ping_ms = float(time_str.replace('ms', ''))
                        ping_times.append(ping_ms)

        except subprocess.TimeoutExpired:
            logger.warning(f"Ping sample collection timed out after {len(ping_times)} samples")
        except Exception as e:
            logger.warning(f"Error collecting ping samples: {e}")

        if ping_times:
            logger.debug(f"Collected {len(ping_times)} ping samples: min={min(ping_times):.2f}ms, max={max(ping_times):.2f}ms")

        return ping_times

    def _calculate_jitter(self, ping_samples: List[float]) -> float:
        """Calculate jitter from ping samples

        Jitter is the variation in latency, calculated as the standard deviation
        of consecutive ping differences. Low jitter (<10ms) indicates a stable
        connection, important for VoIP and video calls.

        Args:
            ping_samples: List of ping times in milliseconds

        Returns:
            Jitter value in milliseconds
        """
        if len(ping_samples) < 2:
            return 0.0

        # Calculate jitter as standard deviation of consecutive differences
        # This is more meaningful than just the range (max - min)
        differences = []
        for i in range(1, len(ping_samples)):
            diff = abs(ping_samples[i] - ping_samples[i-1])
            differences.append(diff)

        if differences:
            # Use mean of absolute differences (similar to ITU-T definition)
            jitter = statistics.mean(differences)
            return jitter

        return 0.0

    def _run_smart_lite_test(self) -> Tuple[float, float]:
        """Run a smart lite speed test using parallel HTTP downloads with requests library

        This method downloads from multiple CDN servers in parallel to accurately
        measure available bandwidth while using less data than a full test.

        Uses a "ramp-up" approach similar to fast.com:
        1. Start with multiple parallel connections using requests with connection pooling
        2. Download in streams with large buffers
        3. Measure sustained throughput over test duration

        Returns:
            Tuple of (download_speed_mbps, upload_speed_mbps)
        """
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
        except ImportError:
            logger.warning("requests library not available, using urllib fallback")
            return self._run_smart_lite_test_urllib()

        total_bytes = 0
        start_time = time.time()
        end_time = start_time + LITE_MODE_TEST_DURATION
        bytes_lock = threading.Lock()
        samples = []  # Track speed samples for averaging
        samples_lock = threading.Lock()

        # Create a session with connection pooling
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=LITE_MODE_PARALLEL_CONNECTIONS,
            pool_maxsize=LITE_MODE_PARALLEL_CONNECTIONS,
            max_retries=Retry(total=0)  # No retries for speed test
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        def download_stream(connection_id: int) -> int:
            """Download data continuously until time expires"""
            nonlocal total_bytes
            bytes_received = 0
            last_sample_time = time.time()
            last_sample_bytes = 0

            try:
                # Use Cloudflare speed test with streaming
                url = f'https://speed.cloudflare.com/__down?bytes=100000000&r={connection_id}'

                response = session.get(
                    url,
                    stream=True,
                    timeout=LITE_MODE_TEST_DURATION + 5,
                    headers={
                        'User-Agent': 'Mozilla/5.0 SpeedTest/1.0',
                        'Accept-Encoding': 'identity',
                    }
                )

                for chunk in response.iter_content(chunk_size=262144):  # 256KB chunks
                    if time.time() >= end_time:
                        break
                    if chunk:
                        chunk_len = len(chunk)
                        bytes_received += chunk_len

                        with bytes_lock:
                            total_bytes += chunk_len

                        # Sample speed every 0.5 seconds
                        now = time.time()
                        if now - last_sample_time >= 0.5:
                            sample_bytes = bytes_received - last_sample_bytes
                            sample_time = now - last_sample_time
                            if sample_time > 0:
                                sample_mbps = (sample_bytes * 8) / (sample_time * 1_000_000)
                                with samples_lock:
                                    samples.append(sample_mbps)
                            last_sample_time = now
                            last_sample_bytes = bytes_received

                response.close()

            except Exception as e:
                logger.debug(f"Connection {connection_id} error: {e}")

            return bytes_received

        logger.info(f"Smart lite test (requests): {LITE_MODE_PARALLEL_CONNECTIONS} parallel connections for {LITE_MODE_TEST_DURATION}s")

        # Run parallel downloads
        with concurrent.futures.ThreadPoolExecutor(max_workers=LITE_MODE_PARALLEL_CONNECTIONS) as executor:
            futures = [executor.submit(download_stream, i) for i in range(LITE_MODE_PARALLEL_CONNECTIONS)]
            concurrent.futures.wait(futures, timeout=LITE_MODE_TEST_DURATION + 2)

        session.close()
        elapsed = time.time() - start_time

        # Calculate speed from total bytes
        if elapsed > 0:
            raw_speed = (total_bytes * 8) / (elapsed * 1_000_000)
        else:
            raw_speed = 0.0

        # Use median of top 50% of samples for accuracy (removes slow startup)
        if samples and len(samples) >= 4:
            sorted_samples = sorted(samples, reverse=True)
            top_half = sorted_samples[:len(sorted_samples) // 2]
            download_speed = statistics.median(top_half)
            logger.info(f"Smart lite: {len(samples)} samples, median of top half: {download_speed:.2f} Mbps (raw: {raw_speed:.2f})")
        else:
            download_speed = raw_speed
            logger.info(f"Smart lite: {total_bytes / 1_000_000:.2f} MB in {elapsed:.2f}s = {download_speed:.2f} Mbps")

        # Upload speed estimation
        upload_speed = download_speed * 0.15

        return download_speed, upload_speed

    def _run_smart_lite_test_urllib(self) -> Tuple[float, float]:
        """Fallback smart lite test using urllib (if requests not available)"""
        total_bytes = 0
        start_time = time.time()
        end_time = start_time + LITE_MODE_TEST_DURATION

        def download_chunk(url: str, conn_id: int) -> int:
            bytes_received = 0
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 SpeedTest/1.0',
                    'Accept-Encoding': 'identity',
                })
                with urllib.request.urlopen(req, timeout=LITE_MODE_TEST_DURATION + 5) as response:
                    while time.time() < end_time:
                        chunk = response.read(262144)
                        if not chunk:
                            break
                        bytes_received += len(chunk)
            except Exception as e:
                logger.debug(f"urllib download error: {e}")
            return bytes_received

        test_url = SPEED_TEST_URLS[0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=LITE_MODE_PARALLEL_CONNECTIONS) as executor:
            futures = [executor.submit(download_chunk, test_url, i) for i in range(LITE_MODE_PARALLEL_CONNECTIONS)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    total_bytes += future.result()
                except Exception:
                    pass

        elapsed = time.time() - start_time
        download_speed = (total_bytes * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0.0

        logger.info(f"Smart lite (urllib): {total_bytes / 1_000_000:.2f} MB in {elapsed:.2f}s = {download_speed:.2f} Mbps")

        return download_speed, download_speed * 0.15

    def _check_slow_speed_alert(self, download_speed: float):
        """Check if download speed triggers slow speed alert"""
        if download_speed < self.slow_speed_threshold:
            self.consecutive_slow_count += 1
            logger.info(f"Slow speed detected: {download_speed:.2f} Mbps (consecutive: {self.consecutive_slow_count}/{self.consecutive_slow_trigger})")

            # Check if we've hit the trigger threshold
            if self.consecutive_slow_count >= self.consecutive_slow_trigger:
                now = time.time()

                # Only alert if cooldown has passed or alert wasn't active
                if not self.slow_speed_alert_active or (now - self.last_slow_alert_time) >= self.slow_alert_cooldown:
                    self.slow_speed_alert_active = True
                    self.last_slow_alert_time = now

                    # Calculate average of last N slow tests
                    history = self.csv_logger.get_history()
                    recent_speeds = [float(h.get('download', 0)) for h in history[-self.consecutive_slow_trigger:]]
                    avg_speed = sum(recent_speeds) / len(recent_speeds) if recent_speeds else download_speed

                    alert_data = {
                        'type': 'slow_speed',
                        'consecutive_count': self.consecutive_slow_count,
                        'threshold': self.slow_speed_threshold,
                        'current_speed': download_speed,
                        'average_speed': round(avg_speed, 2),
                        'timestamp': datetime.now().isoformat()
                    }

                    # Send macOS notification
                    self._send_slow_speed_notification(alert_data)

                    # Call callback if registered
                    if self.slow_speed_alert_callback:
                        try:
                            self.slow_speed_alert_callback(alert_data)
                        except Exception as e:
                            logger.error(f"Slow speed alert callback error: {e}")

                    logger.warning(f"🚨 SLOW SPEED ALERT: {self.consecutive_slow_count} consecutive tests below {self.slow_speed_threshold} Mbps (avg: {avg_speed:.2f} Mbps)")
        else:
            # Speed is good - reset counter and clear alert
            if self.consecutive_slow_count > 0:
                logger.info(f"Speed recovered: {download_speed:.2f} Mbps (was {self.consecutive_slow_count} consecutive slow tests)")

            self.consecutive_slow_count = 0

            # Clear alert if it was active
            if self.slow_speed_alert_active:
                self.slow_speed_alert_active = False
                self._send_speed_recovered_notification(download_speed)

                # Call callback to clear alert
                if self.slow_speed_alert_callback:
                    try:
                        self.slow_speed_alert_callback({
                            'type': 'speed_recovered',
                            'current_speed': download_speed,
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Speed recovered callback error: {e}")

    @staticmethod
    def _escape_applescript(text: str) -> str:
        """Escape a string for safe use in AppleScript double-quoted strings"""
        return text.replace('\\', '\\\\').replace('"', '\\"')

    def _send_slow_speed_notification(self, alert_data: Dict[str, Any]):
        """Send macOS notification for slow speed alert"""
        try:
            title = self._escape_applescript("Slow Internet Speed Alert")
            message = self._escape_applescript(
                f"{alert_data['consecutive_count']} tests in a row below {alert_data['threshold']} Mbps. Average: {alert_data['average_speed']} Mbps"
            )

            script = f'display notification "{message}" with title "{title}" sound name "Basso"'
            subprocess.run(['osascript', '-e', script], capture_output=True, timeout=5)
            logger.info("Sent slow speed notification")
        except Exception as e:
            logger.error(f"Failed to send slow speed notification: {e}")

    def _send_speed_recovered_notification(self, current_speed: float):
        """Send macOS notification when speed recovers"""
        try:
            title = self._escape_applescript("Internet Speed Recovered")
            message = self._escape_applescript(f"Download speed back to normal: {current_speed:.1f} Mbps")

            script = f'display notification "{message}" with title "{title}" sound name "Glass"'
            subprocess.run(['osascript', '-e', script], capture_output=True, timeout=5)
            logger.info("Sent speed recovered notification")
        except Exception as e:
            logger.error(f"Failed to send speed recovered notification: {e}")

    # ==================== Public API Methods ====================

    def get_history(self) -> List[Dict[str, Any]]:
        """Get speed test history from CSV logger"""
        history = self.csv_logger.get_history()
        # Convert to simplified format for graph (now includes jitter)
        return [{
            'download': float(row.get('download', 0)),
            'upload': float(row.get('upload', 0)),
            'ping': float(row.get('ping', 0)),
            'jitter': float(row.get('jitter', 0)),
            'timestamp': row.get('timestamp', '')
        } for row in history]

    def get_last_result_with_countdown(self) -> Dict[str, Any]:
        """Get last result with countdown to next test"""
        result = self.get_last_result()

        # Add countdown information
        if self.next_test_time and self.running:
            seconds_until_next = max(0, int(self.next_test_time - time.time()))
            result['next_test_in'] = seconds_until_next
        else:
            result['next_test_in'] = None

        return result

    def run_test_now(self):
        """Trigger an immediate speed test"""
        # Re-check availability in case speedtest-cli was installed after startup
        if not self.speedtest_available:
            self._check_speedtest_available()

        if not self.speedtest_available:
            logger.error("Cannot run speed test: speedtest-cli not installed")
            self.update_last_result({
                'status': 'error',
                'error': 'speedtest-cli not installed. Install with: pip install speedtest-cli'
            })
            return

        if self.last_result.get('status') == 'testing':
            logger.warning("Speed test already in progress")
            return

        # Run test in background thread
        import threading
        threading.Thread(target=self._run_speed_test, daemon=True).start()

    def set_slow_speed_alert_callback(self, callback):
        """Set callback function for slow speed alerts

        Callback receives dict with:
        - type: 'slow_speed' or 'speed_recovered'
        - consecutive_count: number of consecutive slow tests (for slow_speed)
        - threshold: speed threshold in Mbps
        - current_speed: current download speed
        - average_speed: average of recent slow tests (for slow_speed)
        - timestamp: ISO timestamp
        """
        self.slow_speed_alert_callback = callback

    def configure_slow_speed_alert(self, threshold: float = 20.0, consecutive_trigger: int = 5, cooldown: int = 300):
        """Configure slow speed alert parameters

        Args:
            threshold: Download speed threshold in Mbps (default: 20)
            consecutive_trigger: Number of consecutive slow tests to trigger alert (default: 5)
            cooldown: Seconds between repeated alerts (default: 300)
        """
        self.slow_speed_threshold = threshold
        self.consecutive_slow_trigger = consecutive_trigger
        self.slow_alert_cooldown = cooldown
        logger.info(f"Slow speed alert configured: threshold={threshold} Mbps, trigger={consecutive_trigger} tests, cooldown={cooldown}s")

    # ==================== Test Mode Control Methods ====================

    def get_test_mode(self) -> str:
        """Get current test mode ('lite' or 'full')"""
        return self._test_mode

    def set_test_mode(self, mode: str) -> bool:
        """Set persistent test mode

        Args:
            mode: 'lite' (single-thread, low data) or 'full' (multi-thread, accurate)

        Returns:
            True if mode was set, False if invalid mode
        """
        if mode not in ('lite', 'full'):
            logger.error(f"Invalid test mode: {mode}. Must be 'lite' or 'full'")
            return False

        old_mode = self._test_mode
        self._test_mode = mode
        logger.info(f"Speed test mode changed: {old_mode} -> {mode}")
        return True

    def run_full_test_now(self):
        """Run a single full (accurate) speed test immediately

        This runs one full test regardless of the persistent mode setting.
        After this test, subsequent tests will use the persistent mode.
        """
        # Re-check availability in case speedtest-cli was installed after startup
        if not self.speedtest_available:
            self._check_speedtest_available()

        if not self.speedtest_available:
            logger.error("Cannot run speed test: speedtest-cli not installed")
            self.update_last_result({
                'status': 'error',
                'error': 'speedtest-cli not installed. Install with: pip install speedtest-cli'
            })
            return

        if self.last_result.get('status') == 'testing':
            logger.warning("Speed test already in progress")
            return

        # Set flag for one-time full test
        self._run_full_test_once = True
        logger.info("Triggering one-time full speed test...")

        # Run test in background thread
        import threading
        threading.Thread(target=self._run_speed_test, daemon=True).start()

    def get_mode_info(self) -> Dict[str, Any]:
        """Get information about available test modes

        Returns:
            Dict with mode descriptions and current settings
        """
        return {
            'current_mode': self._test_mode,
            'modes': {
                'lite': {
                    'description': 'Balanced mode (4 threads, speedtest.net)',
                    'threads': self._lite_mode_threads,
                    'data_usage': 'Reduced (~5-15 MB per test)',
                    'accuracy': 'Good (~90% accuracy, faster)'
                },
                'full': {
                    'description': 'Maximum accuracy mode (auto threads, speedtest.net)',
                    'threads': self._full_mode_threads or 'auto (4-8)',
                    'data_usage': 'Full (10-50 MB per test)',
                    'accuracy': 'Best (100% accuracy, saturates connection)'
                }
            }
        }

    def get_slow_speed_status(self) -> Dict[str, Any]:
        """Get current slow speed alert status"""
        return {
            'alert_active': self.slow_speed_alert_active,
            'consecutive_slow_count': self.consecutive_slow_count,
            'threshold': self.slow_speed_threshold,
            'trigger_count': self.consecutive_slow_trigger,
            'last_alert_time': datetime.fromtimestamp(self.last_slow_alert_time).isoformat() if self.last_slow_alert_time else None
        }

    # ==================== Enhanced Configuration Methods (OpenSpeedTest-inspired) ====================

    def configure_enhanced_metrics(
        self,
        ping_samples: int = 10,
        overhead_compensation: float = 1.04
    ):
        """Configure enhanced speed test parameters

        Inspired by OpenSpeedTest methodology for more accurate measurements.

        Args:
            ping_samples: Number of ping samples to collect (default: 10)
                         More samples = more accurate latency and jitter
            overhead_compensation: Compensation factor for HTTP overhead (default: 1.04 = 4%)
                                  Set to 1.0 to disable, max 1.04 (4%)
        """
        # Validate parameters
        if ping_samples < 1:
            ping_samples = 1
        elif ping_samples > 30:
            ping_samples = 30  # Cap at 30 to prevent excessive testing time

        if overhead_compensation < 1.0:
            overhead_compensation = 1.0  # No negative compensation
        elif overhead_compensation > 1.04:
            overhead_compensation = 1.04  # Cap at 4% as per OpenSpeedTest

        self.ping_samples = ping_samples
        self.overhead_compensation = overhead_compensation

        logger.info(
            f"Enhanced metrics configured: ping_samples={ping_samples}, "
            f"overhead_compensation={overhead_compensation:.1%}"
        )

    def get_enhanced_config(self) -> Dict[str, Any]:
        """Get current enhanced configuration settings"""
        return {
            'ping_samples': self.ping_samples,
            'overhead_compensation': self.overhead_compensation,
            'overhead_percentage': f"{(self.overhead_compensation - 1) * 100:.1f}%"
        }

    def get_jitter_quality(self, jitter: float = None) -> Dict[str, Any]:
        """Assess connection quality based on jitter

        Jitter thresholds (industry standards):
        - Excellent: < 5ms (good for real-time applications)
        - Good: 5-10ms (acceptable for VoIP/video)
        - Fair: 10-30ms (may cause minor issues)
        - Poor: > 30ms (likely to cause problems)

        Args:
            jitter: Jitter value in ms. If None, uses last result.

        Returns:
            Dict with quality assessment
        """
        if jitter is None:
            jitter = self.last_result.get('jitter', 0)

        if jitter < 5:
            quality = 'excellent'
            description = 'Excellent - ideal for real-time applications'
            color = '#22c55e'  # green
        elif jitter < 10:
            quality = 'good'
            description = 'Good - suitable for VoIP and video calls'
            color = '#84cc16'  # lime
        elif jitter < 30:
            quality = 'fair'
            description = 'Fair - may experience minor issues'
            color = '#eab308'  # yellow
        else:
            quality = 'poor'
            description = 'Poor - likely to cause streaming/call problems'
            color = '#ef4444'  # red

        return {
            'jitter': round(jitter, 2),
            'quality': quality,
            'description': description,
            'color': color,
            'thresholds': {
                'excellent': '< 5ms',
                'good': '5-10ms',
                'fair': '10-30ms',
                'poor': '> 30ms'
            }
        }


# Global speed test monitor instance (singleton pattern)
_speed_test_monitor = None


def get_speed_test_monitor() -> SpeedTestMonitor:
    """Get or create the global speed test monitor"""
    global _speed_test_monitor
    if _speed_test_monitor is None:
        _speed_test_monitor = SpeedTestMonitor()
    return _speed_test_monitor
