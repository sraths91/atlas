"""
WiFi Roaming History Tracker

Tracks WiFi roaming events including:
- Access point switches (detected via gateway MAC)
- Band switches (2.4GHz <-> 5GHz)
- Channel changes
- Signal quality transitions

Since macOS redacts BSSID, we use the gateway MAC from ARP table
as a proxy for AP identification.
"""
import subprocess
import threading
import time
import json
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import deque

logger = logging.getLogger(__name__)

# Data persistence
DATA_DIR = Path.home() / "Library" / "Application Support" / "Atlas"
ROAMING_HISTORY_FILE = DATA_DIR / "wifi_roaming_history.json"

# Event types
EVENT_TYPE_AP_SWITCH = "ap_switch"
EVENT_TYPE_BAND_SWITCH = "band_switch"
EVENT_TYPE_CHANNEL_CHANGE = "channel_change"
EVENT_TYPE_QUALITY_CHANGE = "quality_change"
EVENT_TYPE_DISCONNECT = "disconnect"
EVENT_TYPE_CONNECT = "connect"


class WiFiRoamingTracker:
    """Tracks WiFi roaming events over time"""

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
        self._data_lock = threading.RLock()  # Use RLock to allow reentrant calls

        # Current state
        self.current_state: Dict[str, Any] = {
            'gateway_mac': None,
            'channel': None,
            'band': None,
            'channel_width': None,
            'quality_rating': None,
            'rssi': None,
            'connected': False,
            'last_update': None
        }

        # Roaming events history (last 7 days max)
        self.events: List[Dict[str, Any]] = []
        self.max_events = 1000

        # Session tracking
        self.session_start: Optional[float] = None
        self.sessions: List[Dict[str, Any]] = []  # Track connection sessions

        # Monitoring
        self.running = False
        self.monitor_thread = None
        self.check_interval = 60  # Check every 60 seconds (reduced to avoid stressing WiFi driver)

        # Load history
        self._load_history()

    def _load_history(self):
        """Load roaming history from disk"""
        try:
            if ROAMING_HISTORY_FILE.exists():
                with open(ROAMING_HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.events = data.get('events', [])
                    self.sessions = data.get('sessions', [])

                    # Restore last known state
                    if data.get('last_state'):
                        self.current_state = data['last_state']

                    logger.info(f"Loaded {len(self.events)} roaming events")
        except Exception as e:
            logger.error(f"Error loading roaming history: {e}")
            self.events = []
            self.sessions = []

    def _save_history(self):
        """Save roaming history to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            # Prune old events (keep last 7 days)
            cutoff = datetime.now().timestamp() - (7 * 24 * 3600)
            self.events = [e for e in self.events if e.get('epoch', 0) > cutoff]
            self.sessions = [s for s in self.sessions if s.get('start_epoch', 0) > cutoff]

            with open(ROAMING_HISTORY_FILE, 'w') as f:
                json.dump({
                    'events': self.events[-self.max_events:],
                    'sessions': self.sessions[-100:],
                    'last_state': self.current_state,
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving roaming history: {e}")

    def _get_gateway_mac(self) -> Optional[str]:
        """Get the MAC address of the default gateway from ARP table"""
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
            match = re.search(r'at\s+([0-9a-f:]+)\s+on', result.stdout, re.IGNORECASE)
            if match:
                return match.group(1).lower()

            return None
        except Exception as e:
            logger.error(f"Error getting gateway MAC: {e}")
            return None

    def _get_wifi_state(self) -> Dict[str, Any]:
        """Get current WiFi state from the WiFi monitor (avoids duplicate system_profiler calls)"""
        state = {
            'connected': False,
            'channel': None,
            'band': None,
            'channel_width': None,
            'rssi': None,
            'noise': None,
            'snr': None,
            'quality_rating': None,
            'phy_mode': None,
            'ssid': None
        }

        try:
            # Use the WiFi monitor's data instead of making our own system_profiler calls
            # This avoids potential kernel panics from concurrent WiFi driver access
            import atlas.network.monitors.wifi as wifi_module
            logger.info(f"Roaming tracker: wifi module id={id(wifi_module)}, _wifi_monitor global={id(wifi_module._wifi_monitor) if wifi_module._wifi_monitor else 'None'}")

            wifi_monitor = wifi_module.get_wifi_monitor()
            wifi_data = wifi_monitor.last_result

            logger.info(f"Roaming tracker got wifi_data from monitor {id(wifi_monitor)}: status={wifi_data.get('status')}, rssi={wifi_data.get('rssi')}, channel={wifi_data.get('channel')}, is_running={wifi_monitor._running if hasattr(wifi_monitor, '_running') else 'N/A'}")

            if not wifi_data:
                logger.info("Roaming tracker: wifi_data is empty")
                return state

            # Check if connected
            status = wifi_data.get('status', '')
            if status == 'connected' or wifi_data.get('rssi', 0) != 0:
                state['connected'] = True
                logger.info(f"Roaming tracker: detected connected (status={status}, rssi={wifi_data.get('rssi')})")
            else:
                logger.info(f"Roaming tracker: detected disconnected (status={status}, rssi={wifi_data.get('rssi')})")
                return state

            # Get WiFi metrics from monitor
            state['ssid'] = wifi_data.get('ssid')
            state['rssi'] = wifi_data.get('rssi')
            state['noise'] = wifi_data.get('noise')
            state['snr'] = wifi_data.get('snr')

            channel = wifi_data.get('channel', 0)
            if channel:
                state['channel'] = channel
                # Determine band from channel number
                if channel <= 14:
                    state['band'] = '2.4GHz'
                elif channel <= 177:
                    state['band'] = '5GHz'
                else:
                    state['band'] = '6GHz'

            # Calculate quality rating from SNR
            snr = state.get('snr') or 0
            if snr >= 40:
                state['quality_rating'] = 'excellent'
            elif snr >= 25:
                state['quality_rating'] = 'good'
            elif snr >= 15:
                state['quality_rating'] = 'fair'
            elif snr > 0:
                state['quality_rating'] = 'poor'

        except ImportError:
            logger.warning("WiFi monitor not available")
        except Exception as e:
            logger.error(f"Error getting WiFi state: {e}")

        return state

    def _record_event(self, event_type: str, details: Dict[str, Any]):
        """Record a roaming event"""
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'epoch': datetime.now().timestamp(),
            **details
        }

        with self._data_lock:
            self.events.append(event)
            self._save_history()

        logger.info(f"Roaming event: {event_type} - {details}")

    def _check_for_changes(self):
        """Check for WiFi changes and record events"""
        new_state = self._get_wifi_state()
        gateway_mac = self._get_gateway_mac() if new_state['connected'] else None

        now = datetime.now()

        with self._data_lock:
            old_state = self.current_state.copy()
            old_gateway = old_state.get('gateway_mac')

            # Check for disconnect
            if old_state.get('connected') and not new_state['connected']:
                self._record_event(EVENT_TYPE_DISCONNECT, {
                    'previous_channel': old_state.get('channel'),
                    'previous_band': old_state.get('band'),
                    'previous_gateway': old_gateway
                })

                # End current session
                if self.session_start:
                    session_duration = now.timestamp() - self.session_start
                    self.sessions.append({
                        'start_epoch': self.session_start,
                        'end_epoch': now.timestamp(),
                        'duration_seconds': session_duration,
                        'gateway_mac': old_gateway,
                        'band': old_state.get('band'),
                        'channel': old_state.get('channel')
                    })
                    self.session_start = None

            # Check for connect
            elif not old_state.get('connected') and new_state['connected']:
                self._record_event(EVENT_TYPE_CONNECT, {
                    'channel': new_state.get('channel'),
                    'band': new_state.get('band'),
                    'gateway_mac': gateway_mac,
                    'rssi': new_state.get('rssi'),
                    'quality_rating': new_state.get('quality_rating')
                })
                self.session_start = now.timestamp()

            # Check for changes while connected
            elif old_state.get('connected') and new_state['connected']:

                # AP switch (gateway MAC changed)
                if old_gateway and gateway_mac and old_gateway != gateway_mac:
                    self._record_event(EVENT_TYPE_AP_SWITCH, {
                        'from_gateway': old_gateway,
                        'to_gateway': gateway_mac,
                        'from_channel': old_state.get('channel'),
                        'to_channel': new_state.get('channel'),
                        'from_band': old_state.get('band'),
                        'to_band': new_state.get('band'),
                        'rssi': new_state.get('rssi')
                    })

                    # End old session, start new one
                    if self.session_start:
                        session_duration = now.timestamp() - self.session_start
                        self.sessions.append({
                            'start_epoch': self.session_start,
                            'end_epoch': now.timestamp(),
                            'duration_seconds': session_duration,
                            'gateway_mac': old_gateway,
                            'band': old_state.get('band'),
                            'channel': old_state.get('channel')
                        })
                    self.session_start = now.timestamp()

                # Band switch
                elif old_state.get('band') and new_state.get('band') and \
                     old_state.get('band') != new_state.get('band'):
                    self._record_event(EVENT_TYPE_BAND_SWITCH, {
                        'from_band': old_state.get('band'),
                        'to_band': new_state.get('band'),
                        'from_channel': old_state.get('channel'),
                        'to_channel': new_state.get('channel'),
                        'rssi_before': old_state.get('rssi'),
                        'rssi_after': new_state.get('rssi')
                    })

                # Channel change (within same band)
                elif old_state.get('channel') and new_state.get('channel') and \
                     old_state.get('channel') != new_state.get('channel'):
                    self._record_event(EVENT_TYPE_CHANNEL_CHANGE, {
                        'from_channel': old_state.get('channel'),
                        'to_channel': new_state.get('channel'),
                        'band': new_state.get('band'),
                        'rssi': new_state.get('rssi')
                    })

                # Quality change (significant)
                elif old_state.get('quality_rating') and new_state.get('quality_rating') and \
                     old_state.get('quality_rating') != new_state.get('quality_rating'):
                    self._record_event(EVENT_TYPE_QUALITY_CHANGE, {
                        'from_quality': old_state.get('quality_rating'),
                        'to_quality': new_state.get('quality_rating'),
                        'from_rssi': old_state.get('rssi'),
                        'to_rssi': new_state.get('rssi'),
                        'channel': new_state.get('channel'),
                        'band': new_state.get('band')
                    })

            # Update current state
            self.current_state = {
                'gateway_mac': gateway_mac,
                'channel': new_state.get('channel'),
                'band': new_state.get('band'),
                'channel_width': new_state.get('channel_width'),
                'quality_rating': new_state.get('quality_rating'),
                'rssi': new_state.get('rssi'),
                'snr': new_state.get('snr'),
                'connected': new_state['connected'],
                'last_update': now.isoformat()
            }

    def _monitor_loop(self):
        """Background monitoring loop"""
        # Wait for WiFi monitor to collect initial data before first check
        # This avoids race conditions during startup
        time.sleep(15)

        while self.running:
            try:
                self._check_for_changes()
            except Exception as e:
                logger.error(f"Error in roaming monitor: {e}")

            time.sleep(self.check_interval)

    def start(self):
        """Start the roaming monitor"""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        # Delay initial state check to allow WiFi monitor to collect data first
        # The monitor loop will do the first check after check_interval seconds
        # This avoids race conditions during startup
        logger.info("WiFi roaming tracker started")

    def stop(self):
        """Stop the roaming monitor"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self._save_history()
        logger.info("WiFi roaming tracker stopped")

    def get_events(self, hours: int = 24, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get roaming events within the specified time period"""
        cutoff = datetime.now().timestamp() - (hours * 3600)

        with self._data_lock:
            events = [e for e in self.events if e.get('epoch', 0) > cutoff]

            if event_type:
                events = [e for e in events if e.get('type') == event_type]

            return sorted(events, key=lambda x: x.get('epoch', 0), reverse=True)

    def get_sessions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get connection sessions within the specified time period"""
        cutoff = datetime.now().timestamp() - (hours * 3600)

        with self._data_lock:
            return [s for s in self.sessions if s.get('start_epoch', 0) > cutoff]

    def get_current_state(self) -> Dict[str, Any]:
        """Get current WiFi state"""
        with self._data_lock:
            return self.current_state.copy()

    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get roaming statistics"""
        events = self.get_events(hours)
        sessions = self.get_sessions(hours)

        # Count events by type
        event_counts = {}
        for e in events:
            t = e.get('type', 'unknown')
            event_counts[t] = event_counts.get(t, 0) + 1

        # Calculate session stats
        session_durations = [s.get('duration_seconds', 0) for s in sessions if s.get('duration_seconds')]

        # Band usage
        band_time = {'2.4GHz': 0, '5GHz': 0, '6GHz': 0}
        for s in sessions:
            band = s.get('band', '')
            duration = s.get('duration_seconds', 0)
            if band in band_time:
                band_time[band] += duration

        # Unique APs
        unique_aps = set()
        for e in events:
            if e.get('gateway_mac'):
                unique_aps.add(e.get('gateway_mac'))
            if e.get('from_gateway'):
                unique_aps.add(e.get('from_gateway'))
            if e.get('to_gateway'):
                unique_aps.add(e.get('to_gateway'))
        for s in sessions:
            if s.get('gateway_mac'):
                unique_aps.add(s.get('gateway_mac'))

        return {
            'hours_analyzed': hours,
            'total_events': len(events),
            'event_counts': event_counts,
            'total_sessions': len(sessions),
            'unique_access_points': len(unique_aps),
            'session_stats': {
                'avg_duration_seconds': sum(session_durations) / len(session_durations) if session_durations else 0,
                'min_duration_seconds': min(session_durations) if session_durations else 0,
                'max_duration_seconds': max(session_durations) if session_durations else 0,
                'total_duration_seconds': sum(session_durations)
            },
            'band_usage': band_time,
            'current_state': self.get_current_state()
        }

    def get_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get a timeline view of events and sessions"""
        events = self.get_events(hours)
        sessions = self.get_sessions(hours)

        timeline = []

        # Add events
        for e in events:
            timeline.append({
                'type': 'event',
                'event_type': e.get('type'),
                'timestamp': e.get('timestamp'),
                'epoch': e.get('epoch'),
                'details': e
            })

        # Add session starts/ends
        for s in sessions:
            timeline.append({
                'type': 'session_start',
                'timestamp': datetime.fromtimestamp(s.get('start_epoch', 0)).isoformat(),
                'epoch': s.get('start_epoch'),
                'details': s
            })

        # Sort by time
        timeline.sort(key=lambda x: x.get('epoch', 0), reverse=True)

        return timeline


# Singleton instance
_tracker = None


def get_wifi_roaming_tracker(auto_start: bool = True) -> WiFiRoamingTracker:
    """Get or create the WiFi roaming tracker singleton

    Args:
        auto_start: If True, start the tracker if not already running
    """
    global _tracker
    if _tracker is None:
        _tracker = WiFiRoamingTracker()
    if auto_start and not _tracker.running:
        # Start in background to avoid blocking API calls
        threading.Thread(target=_tracker.start, daemon=True).start()
    return _tracker
