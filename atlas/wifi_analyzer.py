"""
WiFi Analyzer - Advanced WiFi Analysis Features
Inspired by WiFi Explorer functionality

Features:
- Signal strength history with configurable periods
- Nearby networks scanner with channel analysis
- Channel spectrum visualization data
- SNR-based quality ratings
- Network capability detection
"""
import subprocess
import threading
import time
import logging
import json
import re
from pathlib import Path
from datetime import datetime
from collections import deque
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Data persistence file path
DATA_DIR = Path.home() / "Library" / "Application Support" / "Atlas"
WIFI_HISTORY_FILE = DATA_DIR / "wifi_signal_history.json"
NEARBY_NETWORKS_FILE = DATA_DIR / "nearby_networks.json"
NETWORK_ALIASES_FILE = DATA_DIR / "network_aliases.json"

# Quality thresholds based on SNR
SNR_THRESHOLDS = {
    'excellent': 40,  # >40 dB
    'good': 25,       # 25-40 dB
    'fair': 15,       # 15-25 dB
    'poor': 0         # <15 dB
}

# RSSI thresholds
RSSI_THRESHOLDS = {
    'excellent': -50,  # >-50 dBm
    'good': -60,       # -50 to -60 dBm
    'fair': -70,       # -60 to -70 dBm
    'poor': -80,       # -70 to -80 dBm
    'unusable': -90    # <-80 dBm
}

# Channel information
CHANNELS_2_4GHZ = list(range(1, 15))  # Channels 1-14 (14 only in Japan)
CHANNELS_5GHZ = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112,
                 116, 120, 124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165]

# Channel width overlap patterns
CHANNEL_WIDTHS = {
    20: 1,   # 20 MHz = 1 channel
    40: 2,   # 40 MHz = 2 channels
    80: 4,   # 80 MHz = 4 channels
    160: 8   # 160 MHz = 8 channels
}


class WiFiSignalLogger:
    """Logs WiFi signal metrics over time with configurable retention"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._data_lock = threading.Lock()

        # Sample every 30 seconds (increased from 10s to reduce WiFi driver stress)
        self.sample_interval = 30

        # Store samples with different granularities:
        # - Last 10 min: every 30 sec = 20 samples
        # - Last hour: every 1 min = 60 samples
        # - Last 24 hours: every 5 min = 288 samples
        # - Last 7 days: every 15 min = 672 samples
        self.samples_10sec = deque(maxlen=20)  # 10 min at 30s intervals
        self.samples_1min = deque(maxlen=60)
        self.samples_5min = deque(maxlen=288)
        self.samples_15min = deque(maxlen=672)

        # Track connection events (disconnects, SSID changes, quality drops)
        self.events = deque(maxlen=500)

        # Aggregation buffers
        self._minute_buffer = []
        self._five_min_buffer = []
        self._fifteen_min_buffer = []
        self._last_minute_mark = None
        self._last_five_min_mark = None
        self._last_fifteen_min_mark = None

        # Running stats
        self.is_running = False
        self._thread = None
        self._last_save_time = 0
        self._save_interval = 60

        # Track last values for event detection
        self._last_ssid = None
        self._last_quality_rating = None

        # Load persisted data
        self._load_from_disk()

    def start(self):
        """Start the WiFi logging thread"""
        if self.is_running:
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._logging_loop, daemon=True)
        self._thread.start()
        logger.info("WiFi signal logger started")

    def stop(self):
        """Stop the WiFi logging thread"""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._save_to_disk()
        logger.info("WiFi signal logger stopped")

    def _save_to_disk(self):
        """Save current data to disk for persistence"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            with self._data_lock:
                data = {
                    'saved_at': datetime.now().isoformat(),
                    'samples_10sec': list(self.samples_10sec),
                    'samples_1min': list(self.samples_1min),
                    'samples_5min': list(self.samples_5min),
                    'samples_15min': list(self.samples_15min),
                    'events': list(self.events)
                }

            temp_file = WIFI_HISTORY_FILE.with_suffix('.json.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f)
            temp_file.replace(WIFI_HISTORY_FILE)

            logger.debug(f"Saved WiFi signal data: {len(data['samples_5min'])} 5-min samples")

        except Exception as e:
            logger.error(f"Failed to save WiFi signal data: {e}")

    def _load_from_disk(self):
        """Load persisted data from disk"""
        try:
            if not WIFI_HISTORY_FILE.exists():
                logger.info("No WiFi signal history found, starting fresh")
                return

            with open(WIFI_HISTORY_FILE, 'r') as f:
                data = json.load(f)

            now = time.time()
            seven_days = 7 * 24 * 60 * 60

            with self._data_lock:
                for sample in data.get('samples_10sec', []):
                    self.samples_10sec.append(sample)

                for sample in data.get('samples_1min', []):
                    self.samples_1min.append(sample)

                for sample in data.get('samples_5min', []):
                    if sample.get('epoch', 0) > now - seven_days:
                        self.samples_5min.append(sample)

                for sample in data.get('samples_15min', []):
                    if sample.get('epoch', 0) > now - seven_days:
                        self.samples_15min.append(sample)

                for event in data.get('events', []):
                    if event.get('epoch', 0) > now - seven_days:
                        self.events.append(event)

            logger.info(f"Loaded WiFi signal history: {len(self.samples_5min)} 5-min samples")

        except Exception as e:
            logger.error(f"Failed to load WiFi signal data: {e}")

    def _get_current_wifi_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current WiFi metrics from system"""
        try:
            # Get WiFi info using system_profiler
            result = subprocess.run(
                ['system_profiler', 'SPAirPortDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            # Parse the output
            output = result.stdout
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'epoch': time.time(),
                'ssid': None,
                'bssid': None,
                'rssi': -100,
                'noise': -100,
                'snr': 0,
                'channel': 0,
                'channel_width': 20,
                'band': None,
                'tx_rate': 0,
                'phy_mode': None,
                'security': None,
                'status': 'disconnected',
                'quality_rating': 'poor',
                'quality_score': 0
            }

            # Check connection status
            if 'Status: Connected' not in output and 'status: connected' not in output.lower():
                return metrics

            metrics['status'] = 'connected'

            # Parse current network information
            in_current_network = False

            for line in output.split('\n'):
                line_stripped = line.strip()

                if 'Current Network Information' in line:
                    in_current_network = True
                    continue

                if 'Other Local Wi-Fi Networks' in line:
                    in_current_network = False
                    continue

                # Extract SSID
                if in_current_network and not metrics['ssid']:
                    if line_stripped.endswith(':') and ':' not in line_stripped[:-1]:
                        potential_ssid = line_stripped[:-1].strip()
                        known_keys = ['phy mode', 'channel', 'country code', 'network type',
                                     'security', 'signal / noise', 'transmit rate', 'mcs index', 'bssid']
                        if potential_ssid.lower() not in known_keys and len(potential_ssid) > 0:
                            metrics['ssid'] = potential_ssid

                # Parse metrics
                if ':' in line_stripped and in_current_network:
                    # Handle "Signal / Noise: -48 dBm / -90 dBm"
                    if 'signal / noise' in line_stripped.lower():
                        match = re.search(r'(-?\d+)\s*dBm\s*/\s*(-?\d+)\s*dBm', line_stripped)
                        if match:
                            metrics['rssi'] = int(match.group(1))
                            metrics['noise'] = int(match.group(2))
                            metrics['snr'] = metrics['rssi'] - metrics['noise']
                        continue

                    key, value = line_stripped.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if 'channel' in key and '(' in value:
                        # Parse "149 (5GHz, 80MHz)"
                        ch_match = re.search(r'(\d+)', value)
                        if ch_match:
                            metrics['channel'] = int(ch_match.group(1))

                        if '5ghz' in value.lower():
                            metrics['band'] = '5GHz'
                        elif '2.4ghz' in value.lower() or '2ghz' in value.lower():
                            metrics['band'] = '2.4GHz'
                        elif '6ghz' in value.lower():
                            metrics['band'] = '6GHz'

                        # Channel width
                        width_match = re.search(r'(\d+)MHz', value)
                        if width_match:
                            metrics['channel_width'] = int(width_match.group(1))

                    elif 'phy mode' in key:
                        metrics['phy_mode'] = value
                        # Determine WiFi standard
                        if 'ax' in value.lower():
                            metrics['wifi_standard'] = 'WiFi 6 (802.11ax)'
                        elif 'ac' in value.lower():
                            metrics['wifi_standard'] = 'WiFi 5 (802.11ac)'
                        elif 'n' in value.lower():
                            metrics['wifi_standard'] = 'WiFi 4 (802.11n)'
                        elif 'g' in value.lower():
                            metrics['wifi_standard'] = '802.11g'
                        elif 'a' in value.lower():
                            metrics['wifi_standard'] = '802.11a'

                    elif 'transmit rate' in key:
                        rate_match = re.search(r'(\d+)', value)
                        if rate_match:
                            metrics['tx_rate'] = int(rate_match.group(1))

                    elif 'bssid' in key:
                        metrics['bssid'] = value

                    elif 'security' in key:
                        metrics['security'] = value

            # Calculate quality rating based on SNR
            snr = metrics['snr']
            if snr >= SNR_THRESHOLDS['excellent']:
                metrics['quality_rating'] = 'excellent'
                metrics['quality_score'] = 100
            elif snr >= SNR_THRESHOLDS['good']:
                metrics['quality_rating'] = 'good'
                metrics['quality_score'] = 75
            elif snr >= SNR_THRESHOLDS['fair']:
                metrics['quality_rating'] = 'fair'
                metrics['quality_score'] = 50
            else:
                metrics['quality_rating'] = 'poor'
                metrics['quality_score'] = 25

            # Refine quality score based on RSSI
            rssi = metrics['rssi']
            if rssi >= RSSI_THRESHOLDS['excellent']:
                metrics['quality_score'] = min(100, metrics['quality_score'] + 10)
            elif rssi <= RSSI_THRESHOLDS['poor']:
                metrics['quality_score'] = max(0, metrics['quality_score'] - 20)

            return metrics

        except Exception as e:
            logger.error(f"Error getting WiFi metrics: {e}")
            return None

    def _check_events(self, metrics: Dict[str, Any]):
        """Check for significant WiFi events"""
        events_to_log = []

        # SSID change
        if self._last_ssid and metrics.get('ssid') and self._last_ssid != metrics['ssid']:
            events_to_log.append({
                'type': 'ssid_change',
                'severity': 'info',
                'description': f"Network changed: {self._last_ssid} → {metrics['ssid']}"
            })

        # Quality degradation
        if self._last_quality_rating and metrics.get('quality_rating'):
            rating_order = ['excellent', 'good', 'fair', 'poor']
            last_idx = rating_order.index(self._last_quality_rating) if self._last_quality_rating in rating_order else -1
            curr_idx = rating_order.index(metrics['quality_rating']) if metrics['quality_rating'] in rating_order else -1

            if curr_idx > last_idx + 1:  # Dropped more than one level
                events_to_log.append({
                    'type': 'quality_drop',
                    'severity': 'warning',
                    'description': f"Signal quality dropped: {self._last_quality_rating} → {metrics['quality_rating']}"
                })

        # Disconnection
        if metrics.get('status') == 'disconnected' and self._last_ssid:
            events_to_log.append({
                'type': 'disconnect',
                'severity': 'warning',
                'description': f"Disconnected from {self._last_ssid}"
            })

        # Log events
        for event in events_to_log:
            event['timestamp'] = metrics['timestamp']
            event['epoch'] = metrics['epoch']
            event['ssid'] = metrics.get('ssid')
            event['rssi'] = metrics.get('rssi')
            event['snr'] = metrics.get('snr')

            with self._data_lock:
                self.events.append(event)

        # Update last values
        self._last_ssid = metrics.get('ssid')
        self._last_quality_rating = metrics.get('quality_rating')

    def _aggregate_samples(self, samples: List[Dict]) -> Optional[Dict[str, Any]]:
        """Aggregate multiple samples into one summary"""
        if not samples:
            return None

        rssi_values = [s['rssi'] for s in samples if s.get('rssi')]
        snr_values = [s['snr'] for s in samples if s.get('snr')]
        noise_values = [s['noise'] for s in samples if s.get('noise')]
        quality_values = [s['quality_score'] for s in samples if s.get('quality_score')]

        if not rssi_values:
            return None

        return {
            'timestamp': samples[-1]['timestamp'],
            'epoch': samples[-1]['epoch'],
            'ssid': samples[-1].get('ssid'),
            'rssi': round(sum(rssi_values) / len(rssi_values), 1),
            'rssi_max': max(rssi_values),
            'rssi_min': min(rssi_values),
            'noise': round(sum(noise_values) / len(noise_values), 1) if noise_values else -100,
            'snr': round(sum(snr_values) / len(snr_values), 1) if snr_values else 0,
            'snr_max': max(snr_values) if snr_values else 0,
            'snr_min': min(snr_values) if snr_values else 0,
            'quality_score': round(sum(quality_values) / len(quality_values), 1) if quality_values else 0,
            'channel': samples[-1].get('channel'),
            'band': samples[-1].get('band'),
            'samples': len(samples)
        }

    def _logging_loop(self):
        """Main logging loop"""
        while self.is_running:
            try:
                metrics = self._get_current_wifi_metrics()
                if metrics:
                    now = datetime.now()

                    with self._data_lock:
                        # Store 10-second sample
                        self.samples_10sec.append(metrics)

                        # Add to minute buffer
                        self._minute_buffer.append(metrics)

                        # Check for minute boundary
                        current_minute = now.replace(second=0, microsecond=0)
                        if self._last_minute_mark is None:
                            self._last_minute_mark = current_minute
                        elif current_minute > self._last_minute_mark:
                            if self._minute_buffer:
                                aggregated = self._aggregate_samples(self._minute_buffer)
                                if aggregated:
                                    self.samples_1min.append(aggregated)
                                    self._five_min_buffer.append(aggregated)
                            self._minute_buffer = []
                            self._last_minute_mark = current_minute

                        # Check for 5-minute boundary
                        current_five_min = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)
                        if self._last_five_min_mark is None:
                            self._last_five_min_mark = current_five_min
                        elif current_five_min > self._last_five_min_mark:
                            if self._five_min_buffer:
                                aggregated = self._aggregate_samples(self._five_min_buffer)
                                if aggregated:
                                    self.samples_5min.append(aggregated)
                                    self._fifteen_min_buffer.append(aggregated)
                            self._five_min_buffer = []
                            self._last_five_min_mark = current_five_min

                        # Check for 15-minute boundary
                        current_fifteen_min = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
                        if self._last_fifteen_min_mark is None:
                            self._last_fifteen_min_mark = current_fifteen_min
                        elif current_fifteen_min > self._last_fifteen_min_mark:
                            if self._fifteen_min_buffer:
                                aggregated = self._aggregate_samples(self._fifteen_min_buffer)
                                if aggregated:
                                    self.samples_15min.append(aggregated)
                            self._fifteen_min_buffer = []
                            self._last_fifteen_min_mark = current_fifteen_min

                    # Check for events
                    self._check_events(metrics)

                    # Periodic save
                    current_time = time.time()
                    if current_time - self._last_save_time >= self._save_interval:
                        self._save_to_disk()
                        self._last_save_time = current_time

                # Sleep in small intervals to allow graceful shutdown
                for _ in range(self.sample_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in WiFi logging loop: {e}")
                for _ in range(self.sample_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)

    def get_history(self, period: str = '10m') -> Dict[str, Any]:
        """Get WiFi signal history for a given period"""
        now = time.time()

        with self._data_lock:
            if period == '10m':
                samples = list(self.samples_10sec)
            elif period == '1h':
                samples = list(self.samples_1min)
            elif period == '24h':
                cutoff = now - 86400
                samples = [s for s in self.samples_5min if s.get('epoch', 0) >= cutoff]
            elif period == '7d':
                samples = list(self.samples_15min)
            else:
                samples = list(self.samples_10sec)

            # Get events in range
            if samples:
                oldest_epoch = samples[0].get('epoch', 0)
                events_in_range = [e for e in self.events if e.get('epoch', 0) >= oldest_epoch]
            else:
                events_in_range = []

        if not samples:
            return {
                'period': period,
                'samples': [],
                'stats': None,
                'events': events_in_range
            }

        # Calculate stats
        rssi_values = [s['rssi'] for s in samples if s.get('rssi')]
        snr_values = [s['snr'] for s in samples if s.get('snr')]
        quality_values = [s['quality_score'] for s in samples if s.get('quality_score')]

        stats = {
            'rssi_avg': round(sum(rssi_values) / len(rssi_values), 1) if rssi_values else 0,
            'rssi_max': max(rssi_values) if rssi_values else 0,
            'rssi_min': min(rssi_values) if rssi_values else 0,
            'snr_avg': round(sum(snr_values) / len(snr_values), 1) if snr_values else 0,
            'snr_max': max(snr_values) if snr_values else 0,
            'snr_min': min(snr_values) if snr_values else 0,
            'quality_avg': round(sum(quality_values) / len(quality_values), 1) if quality_values else 0,
            'sample_count': len(samples),
            'event_count': len(events_in_range)
        }

        # Time span info
        time_span = {
            'start_time': samples[0].get('timestamp', ''),
            'end_time': samples[-1].get('timestamp', ''),
            'duration_seconds': samples[-1].get('epoch', 0) - samples[0].get('epoch', 0),
            'sample_count': len(samples)
        }

        return {
            'period': period,
            'time_span': time_span,
            'samples': samples,
            'stats': stats,
            'events': events_in_range
        }

    def get_current(self) -> Dict[str, Any]:
        """Get current WiFi metrics"""
        return self._get_current_wifi_metrics() or {
            'status': 'disconnected',
            'quality_rating': 'unknown'
        }


class NearbyNetworksScanner:
    """Scans for nearby WiFi networks and analyzes channel usage"""

    def __init__(self):
        self._last_scan_time = 0
        self._scan_cache = []
        self._scan_interval = 30  # Minimum seconds between scans

    def scan_networks(self, force: bool = False) -> List[Dict[str, Any]]:
        """
        Scan for nearby WiFi networks

        Uses system_profiler to get nearby networks info.
        Results are cached for 30 seconds to avoid excessive scanning.
        """
        now = time.time()

        # Return cached results if recent enough
        if not force and (now - self._last_scan_time) < self._scan_interval:
            return self._scan_cache

        try:
            # Use system_profiler to get network information
            result = subprocess.run(
                ['system_profiler', 'SPAirPortDataType'],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                logger.error("Failed to run system_profiler")
                return self._scan_cache

            networks = self._parse_networks(result.stdout)

            self._scan_cache = networks
            self._last_scan_time = now

            # Save to disk for analysis
            self._save_scan_results(networks)

            return networks

        except subprocess.TimeoutExpired:
            logger.error("system_profiler timed out")
            return self._scan_cache
        except Exception as e:
            logger.error(f"Network scan failed: {e}")
            return self._scan_cache

    def _parse_networks(self, output: str) -> List[Dict[str, Any]]:
        """Parse system_profiler output for network information"""
        networks = []
        current_network = None
        in_other_networks = False
        in_current_network = False

        lines = output.split('\n')

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            if 'Current Network Information' in line:
                in_current_network = True
                in_other_networks = False
                continue

            if 'Other Local Wi-Fi Networks' in line:
                in_other_networks = True
                in_current_network = False
                continue

            # New network entry (SSID line ends with : and is indented)
            if (in_other_networks or in_current_network):
                # Detect new network entry
                if line_stripped.endswith(':') and ':' not in line_stripped[:-1]:
                    if current_network and current_network.get('ssid'):
                        networks.append(current_network)

                    ssid = line_stripped[:-1].strip()
                    # Skip known metadata keys
                    known_keys = ['phy mode', 'channel', 'country code', 'network type',
                                 'security', 'signal / noise', 'transmit rate', 'mcs index',
                                 'bssid', 'supported phy modes', 'supported channels']
                    if ssid.lower() not in known_keys and len(ssid) > 0:
                        current_network = {
                            'ssid': ssid,
                            'bssid': None,
                            'rssi': -100,
                            'noise': -100,
                            'snr': 0,
                            'channel': 0,
                            'channel_width': 20,
                            'band': None,
                            'security': None,
                            'phy_mode': None,
                            'is_current': in_current_network
                        }
                    continue

                # Parse network properties
                if current_network and ':' in line_stripped:
                    if 'signal / noise' in line_stripped.lower():
                        match = re.search(r'(-?\d+)\s*dBm\s*/\s*(-?\d+)\s*dBm', line_stripped)
                        if match:
                            current_network['rssi'] = int(match.group(1))
                            current_network['noise'] = int(match.group(2))
                            current_network['snr'] = current_network['rssi'] - current_network['noise']
                        continue

                    parts = line_stripped.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()

                        if 'channel' in key and '(' in value:
                            ch_match = re.search(r'(\d+)', value)
                            if ch_match:
                                current_network['channel'] = int(ch_match.group(1))

                            if '5ghz' in value.lower():
                                current_network['band'] = '5GHz'
                            elif '2.4ghz' in value.lower() or '2ghz' in value.lower():
                                current_network['band'] = '2.4GHz'
                            elif '6ghz' in value.lower():
                                current_network['band'] = '6GHz'

                            width_match = re.search(r'(\d+)MHz', value)
                            if width_match:
                                current_network['channel_width'] = int(width_match.group(1))

                        elif 'bssid' in key:
                            current_network['bssid'] = value

                        elif 'security' in key:
                            current_network['security'] = value

                        elif 'phy mode' in key:
                            current_network['phy_mode'] = value

        # Don't forget the last network
        if current_network and current_network.get('ssid'):
            networks.append(current_network)

        # Add vendor info based on BSSID (first 3 octets are OUI)
        for network in networks:
            if network.get('bssid'):
                network['vendor'] = self._lookup_vendor(network['bssid'])

            # Calculate quality rating
            snr = network.get('snr', 0)
            if snr >= SNR_THRESHOLDS['excellent']:
                network['quality_rating'] = 'excellent'
            elif snr >= SNR_THRESHOLDS['good']:
                network['quality_rating'] = 'good'
            elif snr >= SNR_THRESHOLDS['fair']:
                network['quality_rating'] = 'fair'
            else:
                network['quality_rating'] = 'poor'

        # Sort by signal strength (strongest first)
        networks.sort(key=lambda x: x.get('rssi', -100), reverse=True)

        return networks

    def _lookup_vendor(self, bssid: str) -> str:
        """Look up vendor from BSSID OUI (simplified mapping)"""
        if not bssid:
            return 'Unknown'

        # Common OUI prefixes (first 3 bytes)
        oui = bssid.upper().replace(':', '')[:6]

        # Simplified vendor mapping (most common)
        oui_vendors = {
            '00005E': 'Cisco',
            '000C29': 'VMware',
            '001A2B': 'Cisco-Linksys',
            '002275': 'TP-Link',
            '0022CE': 'Samsung',
            '0025BC': 'Apple',
            '002590': 'Apple',
            '003676': 'Apple',
            '00CDFe': 'Apple',
            '0050F2': 'Microsoft',
            '0080C2': 'IEEE',
            '00E04C': 'Realtek',
            '18E829': 'Amazon',
            '244CE3': 'Amazon',
            '28F076': 'Amazon',
            '34E12D': 'Aruba',
            '3C37C6': 'Samsung',
            '48E1E9': 'Huawei',
            '4CEFC0': 'Netgear',
            '54271E': 'Aruba',
            '5C5B35': 'Huawei',
            '64DBA0': 'Apple',
            '704D7B': 'Apple',
            '7CD1C3': 'Apple',
            '8418F5': 'Samsung',
            '88E9FE': 'Apple',
            '9C20B4': 'Apple',
            'A4E975': 'TP-Link',
            'A860B6': 'Apple',
            'AC3743': 'Huawei',
            'AC84C6': 'TP-Link',
            'ACF10F': 'Google',
            'B4A9FC': 'Ubiquiti',
            'B827EB': 'Raspberry Pi',
            'BC307D': 'Google',
            'C0A53E': 'Google',
            'CC2D21': 'Samsung',
            'D0034B': 'Apple',
            'D0C5F3': 'Apple',
            'DC2C26': 'Aruba',
            'E847D2': 'Google',
            'E8B470': 'Samsung',
            'F09FC2': 'Ubiquiti',
            'F0DEF1': 'Apple',
            'F4F26D': 'TP-Link',
        }

        return oui_vendors.get(oui, 'Unknown')

    def _save_scan_results(self, networks: List[Dict[str, Any]]):
        """Save scan results to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            data = {
                'scanned_at': datetime.now().isoformat(),
                'network_count': len(networks),
                'networks': networks
            }

            with open(NEARBY_NETWORKS_FILE, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save scan results: {e}")

    def get_channel_analysis(self) -> Dict[str, Any]:
        """Analyze channel usage and congestion"""
        networks = self.scan_networks()

        # Separate by band
        networks_2_4 = [n for n in networks if n.get('band') == '2.4GHz']
        networks_5 = [n for n in networks if n.get('band') == '5GHz']
        networks_6 = [n for n in networks if n.get('band') == '6GHz']

        # Count networks per channel
        channel_counts_2_4 = {}
        channel_counts_5 = {}

        for n in networks_2_4:
            ch = n.get('channel', 0)
            if ch > 0:
                channel_counts_2_4[ch] = channel_counts_2_4.get(ch, 0) + 1

        for n in networks_5:
            ch = n.get('channel', 0)
            if ch > 0:
                channel_counts_5[ch] = channel_counts_5.get(ch, 0) + 1

        # Find current network
        current_network = next((n for n in networks if n.get('is_current')), None)

        # Calculate overlapping networks for current channel
        overlapping_networks = []
        if current_network:
            current_ch = current_network.get('channel', 0)
            current_width = current_network.get('channel_width', 20)
            current_band = current_network.get('band')

            # Calculate channel range
            if current_band == '2.4GHz':
                # In 2.4GHz, each channel is 5MHz apart, but 20MHz wide
                # Channels 1, 6, 11 are non-overlapping
                for n in networks_2_4:
                    if n.get('is_current'):
                        continue
                    n_ch = n.get('channel', 0)
                    # Channels within 4 of each other overlap in 2.4GHz
                    if abs(n_ch - current_ch) < 5:
                        overlapping_networks.append(n)
            else:
                # In 5GHz, calculate based on channel width
                channels_used = current_width // 20
                for n in networks_5:
                    if n.get('is_current'):
                        continue
                    n_ch = n.get('channel', 0)
                    n_width = n.get('channel_width', 20)
                    n_channels_used = n_width // 20

                    # Check for overlap
                    if abs(n_ch - current_ch) < (channels_used + n_channels_used) * 4:
                        overlapping_networks.append(n)

        # Find recommended channels (least congested)
        recommended_2_4 = self._find_best_channel(channel_counts_2_4, CHANNELS_2_4GHZ[:11])
        recommended_5 = self._find_best_channel(channel_counts_5, CHANNELS_5GHZ)

        return {
            'scanned_at': datetime.now().isoformat(),
            'total_networks': len(networks),
            'networks_2_4ghz': len(networks_2_4),
            'networks_5ghz': len(networks_5),
            'networks_6ghz': len(networks_6),
            'channel_counts_2_4ghz': channel_counts_2_4,
            'channel_counts_5ghz': channel_counts_5,
            'current_network': current_network,
            'overlapping_networks': overlapping_networks,
            'overlap_count': len(overlapping_networks),
            'recommended_channel_2_4ghz': recommended_2_4,
            'recommended_channel_5ghz': recommended_5,
            'congestion_level': self._calculate_congestion(current_network, overlapping_networks)
        }

    def _find_best_channel(self, channel_counts: Dict[int, int], available_channels: List[int]) -> int:
        """Find the least congested channel"""
        if not available_channels:
            return 0

        # For channels not in counts, they have 0 networks
        best_channel = available_channels[0]
        min_count = channel_counts.get(best_channel, 0)

        for ch in available_channels:
            count = channel_counts.get(ch, 0)
            if count < min_count:
                min_count = count
                best_channel = ch

        return best_channel

    def _calculate_congestion(self, current: Optional[Dict], overlapping: List[Dict]) -> str:
        """Calculate congestion level"""
        if not current:
            return 'unknown'

        overlap_count = len(overlapping)

        if overlap_count == 0:
            return 'none'
        elif overlap_count <= 2:
            return 'low'
        elif overlap_count <= 5:
            return 'moderate'
        else:
            return 'high'

    def get_spectrum_data(self) -> Dict[str, Any]:
        """Get data for channel spectrum visualization"""
        networks = self.scan_networks()

        # Prepare spectrum data for visualization
        spectrum_2_4 = []
        spectrum_5 = []

        for network in networks:
            band = network.get('band')
            channel = network.get('channel', 0)
            width = network.get('channel_width', 20)
            rssi = network.get('rssi', -100)
            ssid = network.get('ssid', 'Unknown')
            is_current = network.get('is_current', False)

            entry = {
                'ssid': ssid,
                'channel': channel,
                'width': width,
                'rssi': rssi,
                'is_current': is_current,
                'quality_rating': network.get('quality_rating', 'unknown')
            }

            if band == '2.4GHz' and channel > 0:
                spectrum_2_4.append(entry)
            elif band == '5GHz' and channel > 0:
                spectrum_5.append(entry)

        return {
            'spectrum_2_4ghz': spectrum_2_4,
            'spectrum_5ghz': spectrum_5,
            'channels_2_4ghz': CHANNELS_2_4GHZ[:11],  # US channels only
            'channels_5ghz': CHANNELS_5GHZ
        }


# Singleton instances
_wifi_signal_logger = None
_nearby_scanner = None
_network_alias_manager = None


class NetworkAliasManager:
    """
    Manages user-defined network aliases for WiFi networks.
    Since macOS redacts SSID/BSSID, we create a fingerprint from available data
    and let users assign friendly names to networks.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._data_lock = threading.Lock()
        self.aliases: Dict[str, Dict[str, Any]] = {}
        self._load_aliases()

    def _load_aliases(self):
        """Load network aliases from disk"""
        try:
            if NETWORK_ALIASES_FILE.exists():
                with open(NETWORK_ALIASES_FILE, 'r') as f:
                    data = json.load(f)
                    self.aliases = data.get('aliases', {})
                    logger.info(f"Loaded {len(self.aliases)} network aliases")
        except Exception as e:
            logger.error(f"Error loading network aliases: {e}")
            self.aliases = {}

    def _save_aliases(self):
        """Save network aliases to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(NETWORK_ALIASES_FILE, 'w') as f:
                json.dump({
                    'aliases': self.aliases,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving network aliases: {e}")

    def _get_gateway_mac(self) -> Optional[str]:
        """Get the MAC address of the default gateway (router) from ARP table"""
        try:
            # Get default gateway IP
            result = subprocess.run(
                ['route', '-n', 'get', 'default'],
                capture_output=True, text=True, timeout=5
            )
            gateway_ip = None
            for line in result.stdout.split('\n'):
                if 'gateway:' in line:
                    gateway_ip = line.split(':')[1].strip()
                    break

            if not gateway_ip:
                return None

            # Look up MAC in ARP table
            result = subprocess.run(
                ['arp', '-n', gateway_ip],
                capture_output=True, text=True, timeout=5
            )
            # Parse: "? (192.168.50.1) at a0:36:bc:e9:28:c0 on en0"
            match = re.search(r'at\s+([0-9a-f:]+)\s+on', result.stdout, re.IGNORECASE)
            if match:
                return match.group(1).lower()

            return None
        except Exception as e:
            logger.error(f"Error getting gateway MAC: {e}")
            return None

    def generate_fingerprint(self, network_info: Dict[str, Any]) -> str:
        """
        Generate a fingerprint for a network.
        Primary: Uses router's MAC address from ARP table (unique per network)
        Fallback: Uses channel, band, phy_mode, security (less unique)
        """
        # Try to get router MAC address - this is the most reliable identifier
        gateway_mac = self._get_gateway_mac()

        if gateway_mac:
            # Use MAC address as fingerprint (normalized)
            return gateway_mac.replace(':', '').lower()

        # Fallback to network characteristics if MAC unavailable
        channel = network_info.get('channel', 0)
        channel_width = network_info.get('channel_width', 20)
        band = network_info.get('band', 'unknown')
        phy_mode = network_info.get('phy_mode', 'unknown')
        security = network_info.get('security', 'unknown')

        fingerprint_str = f"{channel}:{channel_width}:{band}:{phy_mode}:{security}"

        import hashlib
        hash_obj = hashlib.md5(fingerprint_str.encode())
        return hash_obj.hexdigest()[:12]

    def get_current_fingerprint(self) -> Optional[str]:
        """Get fingerprint for the currently connected network"""
        gateway_mac = self._get_gateway_mac()
        if gateway_mac:
            return gateway_mac.replace(':', '').lower()
        return None

    def set_alias(self, fingerprint: str, alias: str, network_info: Optional[Dict[str, Any]] = None) -> bool:
        """Set a user-defined alias for a network fingerprint"""
        with self._data_lock:
            self.aliases[fingerprint] = {
                'alias': alias,
                'created': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'network_info': network_info or {}
            }
            self._save_aliases()
            logger.info(f"Set alias '{alias}' for fingerprint {fingerprint}")
            return True

    def get_alias(self, fingerprint: str) -> Optional[str]:
        """Get the alias for a network fingerprint"""
        with self._data_lock:
            if fingerprint in self.aliases:
                # Update last seen
                self.aliases[fingerprint]['last_seen'] = datetime.now().isoformat()
                self._save_aliases()
                return self.aliases[fingerprint].get('alias')
            return None

    def get_alias_for_network(self, network_info: Dict[str, Any]) -> Optional[str]:
        """Get alias for a network based on its info"""
        fingerprint = self.generate_fingerprint(network_info)
        return self.get_alias(fingerprint)

    def remove_alias(self, fingerprint: str) -> bool:
        """Remove an alias"""
        with self._data_lock:
            if fingerprint in self.aliases:
                del self.aliases[fingerprint]
                self._save_aliases()
                return True
            return False

    def get_all_aliases(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored aliases"""
        with self._data_lock:
            return self.aliases.copy()

    def resolve_network_name(self, network_info: Dict[str, Any]) -> str:
        """
        Resolve the display name for a network.
        Returns user alias if set, otherwise the SSID (or redacted message).
        """
        # First check for user alias
        alias = self.get_alias_for_network(network_info)
        if alias:
            return alias

        # Fall back to SSID
        ssid = network_info.get('ssid', '')
        if ssid and ssid != '<redacted>' and 'hidden by macOS' not in ssid:
            return ssid

        # Generate a descriptive fallback
        channel = network_info.get('channel', '?')
        band = network_info.get('band', '')
        return f"Network on Ch.{channel} ({band})"


def get_wifi_signal_logger() -> WiFiSignalLogger:
    """Get or create the WiFi signal logger singleton"""
    global _wifi_signal_logger
    if _wifi_signal_logger is None:
        _wifi_signal_logger = WiFiSignalLogger()
        _wifi_signal_logger.start()
    return _wifi_signal_logger


def get_nearby_scanner() -> NearbyNetworksScanner:
    """Get or create the nearby networks scanner singleton"""
    global _nearby_scanner
    if _nearby_scanner is None:
        _nearby_scanner = NearbyNetworksScanner()
    return _nearby_scanner


def get_network_alias_manager() -> NetworkAliasManager:
    """Get or create the network alias manager singleton"""
    global _network_alias_manager
    if _network_alias_manager is None:
        _network_alias_manager = NetworkAliasManager()
    return _network_alias_manager
