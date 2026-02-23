"""
WiFi Roaming Monitor - Track WiFi roaming behavior and AP transitions

Monitors:
- AP roaming events (switching between access points)
- Roaming latency (how long handoff takes)
- Sticky client detection (stuck on weak AP)
- Channel utilization
- 802.11 frame statistics
- Neighbor AP tracking over time
"""

import logging
import subprocess
import re
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import deque

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)

AIRPORT_BIN = '/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport'


class WiFiRoamingMonitor:
    """Monitor WiFi roaming behavior and AP transitions"""

    def __init__(self, sample_interval: int = 30):
        """
        Initialize WiFi roaming monitor

        Args:
            sample_interval: Seconds between samples (default: 30, increased from 5 to reduce kernel stress)
        """
        self.sample_interval = sample_interval
        self._running = False
        self._thread = None
        self._airport_available = Path(AIRPORT_BIN).exists()

        # CSV Loggers
        log_dir = Path.home()
        self.roaming_logger = CSVLogger(
            str(log_dir / 'wifi_roaming_events.csv'),
            fieldnames=['timestamp', 'event_type', 'old_bssid', 'new_bssid', 'old_rssi',
                    'new_rssi', 'old_channel', 'new_channel', 'roaming_latency_ms',
                    'reason'],
            retention_days=30,
            max_history=500
        )

        self.ap_tracking_logger = CSVLogger(
            str(log_dir / 'wifi_ap_tracking.csv'),
            fieldnames=['timestamp', 'ssid', 'bssid', 'rssi', 'channel', 'noise',
                    'tx_rate', 'is_connected'],
            retention_days=7,
            max_history=2000
        )

        self.channel_logger = CSVLogger(
            str(log_dir / 'wifi_channel_utilization.csv'),
            fieldnames=['timestamp', 'channel', 'utilization_percent', 'interfering_aps',
                    'strongest_interferer_rssi'],
            retention_days=7,
            max_history=1000
        )

        self.frame_stats_logger = CSVLogger(
            str(log_dir / 'wifi_frame_stats.csv'),
            fieldnames=['timestamp', 'tx_frames', 'tx_retries', 'tx_failures',
                    'rx_frames', 'rx_duplicates', 'retry_rate_percent'],
            retention_days=7,
            max_history=1000
        )

        # State tracking
        self._current_ap: Optional[Dict] = None
        self._roaming_start_time: Optional[datetime] = None
        self._nearby_aps_history: deque = deque(maxlen=100)  # Track nearby APs over time
        self._prev_frame_stats: Optional[Dict] = None

    def start(self):
        """Start monitoring WiFi roaming"""
        if self._running:
            logger.warning("WiFi roaming monitor already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"WiFi roaming monitor started with {self.sample_interval}s interval")

    def stop(self):
        """Stop monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("WiFi roaming monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._collect_roaming_data()
            except Exception as e:
                logger.error(f"Error in WiFi roaming monitoring loop: {e}")

            time.sleep(self.sample_interval)

    def _collect_roaming_data(self):
        """Collect WiFi roaming and AP data"""
        current_time = datetime.now()

        # Get current AP info
        current_ap = self._get_current_ap_info()

        # Get nearby APs
        nearby_aps = self._scan_nearby_aps()

        # Track all APs (current + nearby)
        if current_ap:
            self.ap_tracking_logger.append({
                'timestamp': current_time.isoformat(),
                'ssid': current_ap.get('ssid', ''),
                'bssid': current_ap.get('bssid', ''),
                'rssi': current_ap.get('rssi', 0),
                'channel': current_ap.get('channel', 0),
                'noise': current_ap.get('noise', 0),
                'tx_rate': current_ap.get('tx_rate', 0),
                'is_connected': True
            })

        for ap in nearby_aps:
            self.ap_tracking_logger.append({
                'timestamp': current_time.isoformat(),
                'ssid': ap.get('ssid', ''),
                'bssid': ap.get('bssid', ''),
                'rssi': ap.get('rssi', 0),
                'channel': ap.get('channel', 0),
                'noise': 0,  # Not available in scan
                'tx_rate': 0,  # Not available in scan
                'is_connected': False
            })

        # Detect roaming events
        if self._current_ap and current_ap:
            if self._current_ap.get('bssid') != current_ap.get('bssid'):
                self._log_roaming_event(self._current_ap, current_ap, current_time)

        # Check for sticky client issue
        if current_ap and nearby_aps:
            self._check_sticky_client(current_ap, nearby_aps)

        # Analyze channel utilization
        if current_ap:
            self._analyze_channel_utilization(current_ap, nearby_aps, current_time)

        # Collect frame statistics
        self._collect_frame_stats(current_time)

        self._current_ap = current_ap
        if nearby_aps:
            self._nearby_aps_history.append((current_time, nearby_aps))

    def _get_current_ap_info(self) -> Optional[Dict]:
        """Get info about currently connected AP"""
        if not self._airport_available:
            return None
        try:
            result = subprocess.run(
                [AIRPORT_BIN, '-I'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                return None

            ap_info = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()

                    if key == 'ssid':
                        ap_info['ssid'] = value
                    elif key == 'bssid':
                        ap_info['bssid'] = value
                    elif key == 'rssi':
                        ap_info['rssi'] = int(value)
                    elif key == 'channel':
                        # Extract channel number from "channel,band" format
                        ap_info['channel'] = int(value.split(',')[0])
                    elif key == 'noise':
                        ap_info['noise'] = int(value)
                    elif key == 'lastTxRate' or key == 'lasttxrate':
                        ap_info['tx_rate'] = int(value)

            return ap_info if ap_info else None

        except Exception as e:
            logger.error(f"Error getting current AP info: {e}")
            return None

    def _scan_nearby_aps(self) -> List[Dict]:
        """Scan for nearby access points"""
        if not self._airport_available:
            return []
        try:
            result = subprocess.run(
                [AIRPORT_BIN, '-s'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return []

            aps = []
            lines = result.stdout.split('\n')[1:]  # Skip header

            for line in lines:
                if not line.strip():
                    continue

                # Parse airport scan output
                # Format: SSID BSSID RSSI CHANNEL HT CC SECURITY
                parts = line.split()
                if len(parts) >= 4:
                    ap = {
                        'ssid': parts[0],
                        'bssid': parts[1],
                        'rssi': int(parts[2]),
                        'channel': int(parts[3].split(',')[0]) if ',' in parts[3] else int(parts[3])
                    }
                    aps.append(ap)

            return aps

        except Exception as e:
            logger.error(f"Error scanning nearby APs: {e}")
            return []

    def _log_roaming_event(self, old_ap: Dict, new_ap: Dict, current_time: datetime):
        """Log AP roaming event"""
        roaming_latency = 0
        if self._roaming_start_time:
            roaming_latency = (current_time - self._roaming_start_time).total_seconds() * 1000
            self._roaming_start_time = None

        # Determine roaming reason
        reason = 'unknown'
        old_rssi = old_ap.get('rssi', 0)
        new_rssi = new_ap.get('rssi', 0)

        if new_rssi > old_rssi + 10:
            reason = 'better_signal'
        elif old_rssi < -75:
            reason = 'poor_signal'
        elif old_ap.get('channel') != new_ap.get('channel'):
            reason = 'channel_change'

        self.roaming_logger.append({
            'timestamp': current_time.isoformat(),
            'event_type': 'ap_roaming',
            'old_bssid': old_ap.get('bssid', ''),
            'new_bssid': new_ap.get('bssid', ''),
            'old_rssi': old_rssi,
            'new_rssi': new_rssi,
            'old_channel': old_ap.get('channel', 0),
            'new_channel': new_ap.get('channel', 0),
            'roaming_latency_ms': roaming_latency,
            'reason': reason
        })

        logger.info(f"WiFi roamed from {old_ap.get('bssid')} to {new_ap.get('bssid')} "
                   f"(RSSI {old_rssi} -> {new_rssi}, latency {roaming_latency:.0f}ms, reason: {reason})")

    def _check_sticky_client(self, current_ap: Dict, nearby_aps: List[Dict]):
        """Check if client is stuck on weak AP when better one is available"""
        current_rssi = current_ap.get('rssi', 0)
        current_bssid = current_ap.get('bssid', '')
        current_ssid = current_ap.get('ssid', '')

        # Find better APs with same SSID
        better_aps = []
        for ap in nearby_aps:
            if (ap.get('ssid') == current_ssid and
                ap.get('bssid') != current_bssid and
                ap.get('rssi', -100) > current_rssi + 15):  # 15 dBm better
                better_aps.append(ap)

        # If stuck on weak signal with better AP available, log it
        if current_rssi < -70 and better_aps:
            best_ap = max(better_aps, key=lambda x: x.get('rssi', -100))
            self.roaming_logger.append({
                'timestamp': datetime.now().isoformat(),
                'event_type': 'sticky_client',
                'old_bssid': current_bssid,
                'new_bssid': best_ap.get('bssid', ''),
                'old_rssi': current_rssi,
                'new_rssi': best_ap.get('rssi', 0),
                'old_channel': current_ap.get('channel', 0),
                'new_channel': best_ap.get('channel', 0),
                'roaming_latency_ms': 0,
                'reason': 'sticky_client_detected'
            })

            logger.warning(f"Sticky client detected: Connected to {current_bssid} "
                         f"(RSSI {current_rssi}) but {best_ap.get('bssid')} has "
                         f"RSSI {best_ap.get('rssi')}")

    def _analyze_channel_utilization(self, current_ap: Dict, nearby_aps: List[Dict],
                                    current_time: datetime):
        """Analyze WiFi channel utilization and interference"""
        current_channel = current_ap.get('channel', 0)

        # Count APs on same channel and adjacent channels
        # 2.4GHz channels overlap (1-6-11 are non-overlapping)
        # 5GHz channels are non-overlapping
        same_channel_aps = []
        interfering_aps = []

        for ap in nearby_aps:
            ap_channel = ap.get('channel', 0)

            if ap_channel == current_channel:
                same_channel_aps.append(ap)
            elif abs(ap_channel - current_channel) <= 4:  # Adjacent/overlapping channels
                interfering_aps.append(ap)

        # Estimate channel utilization based on number of APs and their signal strength
        # Higher RSSI APs contribute more to interference
        utilization = min(100, len(same_channel_aps) * 10 + len(interfering_aps) * 5)

        strongest_interferer = -100
        if interfering_aps:
            strongest_interferer = max(ap.get('rssi', -100) for ap in interfering_aps)

        self.channel_logger.append({
            'timestamp': current_time.isoformat(),
            'channel': current_channel,
            'utilization_percent': utilization,
            'interfering_aps': len(same_channel_aps) + len(interfering_aps),
            'strongest_interferer_rssi': strongest_interferer
        })

    def _collect_frame_stats(self, current_time: datetime):
        """Collect 802.11 frame statistics"""
        if not self._airport_available:
            return
        try:
            # Get WiFi statistics using airport
            result = subprocess.run(
                [AIRPORT_BIN, '-I'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                return

            stats = {}
            for line in result.stdout.split('\n'):
                if 'lastTxRate' in line:
                    match = re.search(r'(\d+)', line)
                    if match:
                        stats['tx_rate'] = int(match.group(1))

            # Get interface stats using netstat for frame counts
            interface = 'en0'  # Primary WiFi interface
            result = subprocess.run(['netstat', '-ibn'], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith(interface):
                        parts = line.split()
                        if len(parts) >= 10:
                            stats['tx_frames'] = int(parts[7])
                            stats['tx_errors'] = int(parts[8])
                            stats['rx_frames'] = int(parts[4])
                            stats['rx_errors'] = int(parts[5])

            if not stats:
                return

            # Calculate retry rate
            retry_rate = 0
            if self._prev_frame_stats and 'tx_frames' in stats and 'tx_errors' in stats:
                prev_tx = self._prev_frame_stats.get('tx_frames', 0)
                prev_errors = self._prev_frame_stats.get('tx_errors', 0)
                curr_tx = stats['tx_frames']
                curr_errors = stats['tx_errors']

                delta_tx = curr_tx - prev_tx
                delta_errors = curr_errors - prev_errors

                if delta_tx > 0:
                    retry_rate = (delta_errors / delta_tx) * 100

            self.frame_stats_logger.append({
                'timestamp': current_time.isoformat(),
                'tx_frames': stats.get('tx_frames', 0),
                'tx_retries': stats.get('tx_errors', 0),
                'tx_failures': 0,  # Not easily accessible
                'rx_frames': stats.get('rx_frames', 0),
                'rx_duplicates': 0,  # Not easily accessible
                'retry_rate_percent': round(retry_rate, 2)
            })

            self._prev_frame_stats = stats

        except Exception as e:
            logger.error(f"Error collecting frame stats: {e}")

    def get_roaming_summary(self) -> dict:
        """Get summary of roaming behavior"""
        roaming_events = self.roaming_logger.get_history()

        actual_roams = [e for e in roaming_events if e.get('event_type') == 'ap_roaming']
        sticky_events = [e for e in roaming_events if e.get('event_type') == 'sticky_client']

        avg_latency = 0
        if actual_roams:
            latencies = [float(e.get('roaming_latency_ms', 0)) for e in actual_roams
                        if e.get('roaming_latency_ms')]
            if latencies:
                avg_latency = sum(latencies) / len(latencies)

        return {
            'total_roaming_events': len(actual_roams),
            'sticky_client_incidents': len(sticky_events),
            'avg_roaming_latency_ms': round(avg_latency, 2)
        }

    def get_current_channel_quality(self) -> dict:
        """Get current channel quality metrics"""
        recent = self.channel_logger.get_history()
        if not recent:
            return {}

        latest = recent[-1]
        return {
            'channel': latest.get('channel'),
            'utilization_percent': latest.get('utilization_percent'),
            'interfering_aps': latest.get('interfering_aps')
        }


# Singleton instance
_wifi_roaming_monitor_instance = None
_monitor_lock = threading.Lock()

def get_wifi_roaming_monitor(sample_interval: int = 30) -> WiFiRoamingMonitor:
    """Get or create singleton WiFi roaming monitor instance"""
    global _wifi_roaming_monitor_instance

    with _monitor_lock:
        if _wifi_roaming_monitor_instance is None:
            _wifi_roaming_monitor_instance = WiFiRoamingMonitor(sample_interval=sample_interval)
            _wifi_roaming_monitor_instance.start()

        return _wifi_roaming_monitor_instance
