"""
Network Log Correlation Analyzer
Automatically analyzes logs to identify potential causes of network slowdowns
by correlating speed tests with WiFi quality, network diagnostics, and events.
"""

import csv
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Log file paths
SPEEDTEST_LOG_FILE = Path.home() / 'speedtest_history.csv'
PING_LOG_FILE = Path.home() / 'ping_history.csv'
WIFI_LOG_FILE = Path.home() / 'wifi_quality.csv'
WIFI_EVENTS_FILE = Path.home() / 'wifi_events.csv'
NETWORK_DIAG_FILE = Path.home() / 'network_diagnostics.csv'


class SeverityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CorrelatedFactor:
    """A factor that may have contributed to a network issue"""
    category: str  # wifi_signal, interference, congestion, gateway, internet, event
    description: str
    severity: SeverityLevel
    timestamp: str
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricChange:
    """Represents a change in a metric before vs during a slowdown"""
    metric_name: str
    category: str
    before_value: float
    during_value: float
    change_amount: float
    change_percent: float
    direction: str  # "increased", "decreased", "stable"
    is_significant: bool
    description: str


@dataclass
class AccessPointInfo:
    """Information about the WiFi access point during an incident"""
    ssid: str
    bssid: str  # Access point MAC address
    channel: int
    avg_rssi: float
    avg_snr: float
    tx_rate: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ssid': self.ssid,
            'bssid': self.bssid,
            'channel': self.channel,
            'avg_rssi': self.avg_rssi,
            'avg_snr': self.avg_snr,
            'tx_rate': self.tx_rate
        }


@dataclass
class TracerouteSnapshot:
    """Traceroute data captured during an incident"""
    target: str
    timestamp: str
    hop_count: int
    hops: List[Dict[str, Any]]
    problem_hops: List[Dict[str, Any]]
    avg_latency_ms: float
    max_latency_ms: float
    method: str  # "native" or "mtr"
    total_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'target': self.target,
            'timestamp': self.timestamp,
            'hop_count': self.hop_count,
            'hops': self.hops,
            'problem_hops': self.problem_hops,
            'avg_latency_ms': self.avg_latency_ms,
            'max_latency_ms': self.max_latency_ms,
            'method': self.method,
            'total_time_ms': self.total_time_ms
        }


@dataclass
class SlowdownIncident:
    """Represents a detected network slowdown incident"""
    start_time: datetime
    end_time: datetime
    speed_tests: List[Dict[str, Any]]
    avg_download: float
    avg_upload: float
    avg_ping: float
    connection_type: str = "wifi"  # "wifi", "ethernet", or "unknown"
    access_point: Optional[AccessPointInfo] = None  # WiFi AP info during incident
    factors: List[CorrelatedFactor] = field(default_factory=list)
    metric_changes: List[MetricChange] = field(default_factory=list)  # Delta analysis
    trigger_factors: List[str] = field(default_factory=list)  # Likely triggers
    traceroute_snapshots: List[TracerouteSnapshot] = field(default_factory=list)  # Network path data
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class NetworkAnalyzer:
    """
    Analyzes network logs to identify and explain network slowdowns.
    Correlates speed test results with WiFi quality, diagnostics, and events.
    """
    
    # Thresholds for detecting issues
    SLOW_DOWNLOAD_THRESHOLD = 20.0  # Mbps
    SLOW_UPLOAD_THRESHOLD = 5.0  # Mbps
    HIGH_PING_THRESHOLD = 100.0  # ms
    CONSECUTIVE_SLOW_COUNT = 3  # Number of consecutive slow tests to trigger analysis
    
    # WiFi quality thresholds
    WEAK_SIGNAL_RSSI = -70  # dBm (weak signal)
    VERY_WEAK_SIGNAL_RSSI = -80  # dBm (very weak)
    LOW_SNR_THRESHOLD = 20  # dB (poor signal-to-noise)
    LOW_QUALITY_SCORE = 50  # Quality score percentage
    
    # Network diagnostic thresholds
    HIGH_GATEWAY_LATENCY = 20  # ms
    HIGH_INTERNET_LATENCY = 100  # ms
    PACKET_LOSS_THRESHOLD = 5  # percentage
    
    def __init__(self,
                 slow_download_threshold: float = None,
                 consecutive_slow_count: int = None,
                 enable_notifications: bool = True):
        """Initialize the analyzer with optional custom thresholds"""
        # Load settings from file (if available)
        try:
            from .network_analysis_settings import get_settings
            settings = get_settings()
            self.SLOW_DOWNLOAD_THRESHOLD = settings.get('slow_download_threshold', self.SLOW_DOWNLOAD_THRESHOLD)
            self.SLOW_UPLOAD_THRESHOLD = settings.get('slow_upload_threshold', self.SLOW_UPLOAD_THRESHOLD)
            self.HIGH_PING_THRESHOLD = settings.get('high_ping_threshold', self.HIGH_PING_THRESHOLD)
            self.CONSECUTIVE_SLOW_COUNT = settings.get('consecutive_slow_count', self.CONSECUTIVE_SLOW_COUNT)
            logger.info(f"Loaded thresholds: download={self.SLOW_DOWNLOAD_THRESHOLD}, count={self.CONSECUTIVE_SLOW_COUNT}")
        except Exception as e:
            logger.debug(f"Using default thresholds: {e}")

        # Allow constructor parameters to override loaded settings
        if slow_download_threshold:
            self.SLOW_DOWNLOAD_THRESHOLD = slow_download_threshold
        if consecutive_slow_count:
            self.CONSECUTIVE_SLOW_COUNT = consecutive_slow_count

        # Initialize notification manager
        self.notifications_enabled = enable_notifications
        self._notification_manager = None
        if enable_notifications:
            try:
                from .notification_manager import get_notification_manager
                self._notification_manager = get_notification_manager()
                logger.info("Notification system initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize notifications: {e}")
                self._notification_manager = None

        self._speedtest_data = []
        self._wifi_data = []
        self._wifi_events = []
        self._network_diag = []
        self._ping_data = []
        self._last_notified_incident = None  # Track last incident we notified about
        
    def load_all_logs(self, hours: int = 24) -> None:
        """Load all log files for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        self._speedtest_data = self._load_csv(SPEEDTEST_LOG_FILE, cutoff_time)
        self._wifi_data = self._load_csv(WIFI_LOG_FILE, cutoff_time)
        self._wifi_events = self._load_csv(WIFI_EVENTS_FILE, cutoff_time)
        self._network_diag = self._load_csv(NETWORK_DIAG_FILE, cutoff_time)
        self._ping_data = self._load_csv(PING_LOG_FILE, cutoff_time)
        
        logger.info(f"Loaded logs: {len(self._speedtest_data)} speed tests, "
                   f"{len(self._wifi_data)} wifi samples, "
                   f"{len(self._wifi_events)} wifi events, "
                   f"{len(self._network_diag)} diagnostics, "
                   f"{len(self._ping_data)} pings")
    
    def _load_csv(self, filepath: Path, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Load CSV file and filter by time"""
        data = []
        try:
            if not filepath.exists():
                return data

            with open(filepath, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        timestamp_str = row.get('timestamp', '')
                        if not timestamp_str:
                            continue
                        
                        # Parse timestamp (handle different formats)
                        timestamp = self._parse_timestamp(timestamp_str)
                        if timestamp and timestamp >= cutoff_time:
                            row['_parsed_time'] = timestamp
                            data.append(row)
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
        
        return data
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse various timestamp formats"""
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str[:26], fmt)
            except ValueError:
                continue
        return None
    
    def detect_slowdown_incidents(self) -> List[SlowdownIncident]:
        """
        Detect periods of network slowdown based on consecutive slow speed tests.
        Returns a list of incidents with correlated factors.
        """
        incidents = []
        
        if not self._speedtest_data:
            return incidents
        
        # Sort by timestamp
        sorted_tests = sorted(self._speedtest_data, 
                             key=lambda x: x.get('_parsed_time', datetime.min))
        
        # Find consecutive slow tests
        slow_streak = []
        
        for test in sorted_tests:
            try:
                download = float(test.get('download', 0))
                
                if download < self.SLOW_DOWNLOAD_THRESHOLD:
                    slow_streak.append(test)
                else:
                    # End of slow streak
                    if len(slow_streak) >= self.CONSECUTIVE_SLOW_COUNT:
                        incident = self._create_incident(slow_streak)
                        incidents.append(incident)
                    slow_streak = []
            except (ValueError, TypeError):
                continue
        
        # Check final streak
        if len(slow_streak) >= self.CONSECUTIVE_SLOW_COUNT:
            incident = self._create_incident(slow_streak)
            incidents.append(incident)
        
        # Analyze each incident
        for incident in incidents:
            self._analyze_incident(incident)
        
        logger.info(f"Detected {len(incidents)} slowdown incidents")
        return incidents
    
    def _create_incident(self, slow_tests: List[Dict]) -> SlowdownIncident:
        """Create a SlowdownIncident from a list of slow speed tests"""
        downloads = []
        uploads = []
        pings = []
        
        for test in slow_tests:
            try:
                downloads.append(float(test.get('download', 0)))
                uploads.append(float(test.get('upload', 0)))
                pings.append(float(test.get('ping', 0)))
            except (ValueError, TypeError):
                continue
        
        start_time = slow_tests[0].get('_parsed_time', datetime.now())
        end_time = slow_tests[-1].get('_parsed_time', datetime.now())
        
        # Detect connection type and extract access point info
        connection_type = self._detect_connection_type(start_time, end_time)
        access_point = None
        if connection_type == "wifi":
            access_point = self._extract_access_point_info(start_time, end_time)
        
        return SlowdownIncident(
            start_time=start_time,
            end_time=end_time,
            speed_tests=slow_tests,
            avg_download=sum(downloads) / len(downloads) if downloads else 0,
            avg_upload=sum(uploads) / len(uploads) if uploads else 0,
            avg_ping=sum(pings) / len(pings) if pings else 0,
            connection_type=connection_type,
            access_point=access_point
        )
    
    def _detect_connection_type(self, start_time: datetime, end_time: datetime) -> str:
        """Detect whether the connection was WiFi or Ethernet during the incident"""
        # Get WiFi data during the incident
        incident_wifi = [
            d for d in self._wifi_data
            if d.get('_parsed_time') and start_time <= d['_parsed_time'] <= end_time
        ]
        
        if not incident_wifi:
            # No WiFi data - likely Ethernet or unknown
            return "ethernet"
        
        # Check if any samples indicate Ethernet
        for sample in incident_wifi:
            ssid = sample.get('ssid', '')
            # Check for Ethernet indicators
            if 'ethernet' in ssid.lower() or ssid.startswith('Ethernet'):
                return "ethernet"
            # Check for valid WiFi data (negative RSSI indicates WiFi)
            rssi = int(sample.get('rssi', 0))
            if rssi < 0:
                return "wifi"
        
        # Default to unknown if we can't determine
        return "unknown"
    
    def _extract_access_point_info(self, start_time: datetime, end_time: datetime) -> Optional[AccessPointInfo]:
        """Extract access point information during the incident period"""
        # Get WiFi data during the incident
        incident_wifi = [
            d for d in self._wifi_data
            if d.get('_parsed_time') and start_time <= d['_parsed_time'] <= end_time
        ]
        
        if not incident_wifi:
            return None
        
        # Get the most common SSID and BSSID during the incident
        ssids = [d.get('ssid', '') for d in incident_wifi if d.get('ssid')]
        bssids = [d.get('bssid', '') for d in incident_wifi if d.get('bssid')]
        channels = [int(d.get('channel', 0)) for d in incident_wifi if d.get('channel')]
        rssis = [int(d.get('rssi', 0)) for d in incident_wifi if int(d.get('rssi', 0)) < 0]
        snrs = [float(d.get('snr', 0)) for d in incident_wifi if float(d.get('snr', 0)) > 0]
        tx_rates = [int(d.get('tx_rate', 0)) for d in incident_wifi if int(d.get('tx_rate', 0)) > 0]
        
        if not ssids:
            return None
        
        # Use most frequent values (in case of AP roaming during incident)
        from collections import Counter
        ssid = Counter(ssids).most_common(1)[0][0] if ssids else ''
        bssid = Counter(bssids).most_common(1)[0][0] if bssids else ''
        channel = Counter(channels).most_common(1)[0][0] if channels else 0
        
        return AccessPointInfo(
            ssid=ssid,
            bssid=bssid,
            channel=channel,
            avg_rssi=round(sum(rssis) / len(rssis), 1) if rssis else 0,
            avg_snr=round(sum(snrs) / len(snrs), 1) if snrs else 0,
            tx_rate=int(sum(tx_rates) / len(tx_rates)) if tx_rates else 0
        )
    
    def _analyze_incident(self, incident: SlowdownIncident) -> None:
        """Analyze an incident and identify correlated factors"""
        # Expand time window slightly for correlation
        window_start = incident.start_time - timedelta(minutes=5)
        window_end = incident.end_time + timedelta(minutes=5)

        # Only analyze WiFi-specific factors if using WiFi
        if incident.connection_type == "wifi":
            # Analyze WiFi signal quality
            self._analyze_wifi_quality(incident, window_start, window_end)

            # Analyze WiFi events (disconnections, roaming, etc.)
            self._analyze_wifi_events(incident, window_start, window_end)

        # These apply to both WiFi and Ethernet
        # Analyze network diagnostics (router, ISP issues)
        self._analyze_network_diagnostics(incident, window_start, window_end)

        # Analyze ping data for packet loss/latency
        self._analyze_ping_data(incident, window_start, window_end)

        # Run traceroute to capture network path during slowdown
        self._capture_traceroute(incident)

        # Delta analysis - compare before vs during to find what changed
        self._analyze_metric_changes(incident)

        # Generate summary and recommendations (connection-type aware)
        self._generate_summary(incident)

    def _capture_traceroute(self, incident: SlowdownIncident) -> None:
        """
        Run traceroute to common targets to capture network path data.
        This helps identify where in the network path issues are occurring.
        Uses a thread with timeout to avoid blocking the API response.
        """
        # Only capture traceroute for recent/active incidents (within last hour)
        # to avoid running traceroutes for historical incidents
        time_since_end = datetime.now() - incident.end_time
        if time_since_end.total_seconds() > 3600:  # More than 1 hour ago
            logger.debug(f"Skipping traceroute for old incident ({time_since_end} ago)")
            return

        import threading

        def _run_traces():
            try:
                from .enhanced_traceroute import get_tracer
                tracer = get_tracer()

                # Single target to keep it fast
                target = '8.8.8.8'
                try:
                    logger.info(f"Running traceroute to {target} for incident analysis")
                    result = tracer.quick_trace(target)

                    if result and result.get('completed'):
                        hops = result.get('hops', [])
                        valid_latencies = [h.get('avg_ms', 0) for h in hops if h.get('avg_ms', 0) > 0]
                        avg_lat = sum(valid_latencies) / len(valid_latencies) if valid_latencies else 0
                        max_lat = max([h.get('max_ms', 0) for h in hops]) if hops else 0

                        snapshot = TracerouteSnapshot(
                            target=target,
                            timestamp=datetime.now().isoformat(),
                            hop_count=result.get('hop_count', 0),
                            hops=result.get('hops', []),
                            problem_hops=result.get('problem_hops', []),
                            avg_latency_ms=round(avg_lat, 2),
                            max_latency_ms=round(max_lat, 2),
                            method=result.get('method', 'native'),
                            total_time_ms=result.get('total_time_ms', 0)
                        )
                        incident.traceroute_snapshots.append(snapshot)
                        self._analyze_traceroute_problems(incident, snapshot)

                except Exception as e:
                    logger.warning(f"Failed to trace {target}: {e}")

            except ImportError:
                logger.debug("Enhanced traceroute module not available")
            except Exception as e:
                logger.error(f"Error capturing traceroute: {e}")

        trace_thread = threading.Thread(target=_run_traces, daemon=True)
        trace_thread.start()
        trace_thread.join(timeout=10)  # Wait at most 10 seconds
        if trace_thread.is_alive():
            logger.warning("Traceroute timed out after 10s, skipping for this incident")

    def _analyze_traceroute_problems(self, incident: SlowdownIncident,
                                      snapshot: TracerouteSnapshot) -> None:
        """Analyze traceroute results and add relevant factors"""
        problem_hops = snapshot.problem_hops

        if not problem_hops:
            return

        # Categorize problems by hop position
        early_problems = []  # Hops 1-3 (local network)
        mid_problems = []    # Hops 4-8 (ISP)
        late_problems = []   # Hops 9+ (internet backbone)

        for p in problem_hops:
            hop_num = p.get('hop', 0)
            if hop_num <= 3:
                early_problems.append(p)
            elif hop_num <= 8:
                mid_problems.append(p)
            else:
                late_problems.append(p)

        # Add factors based on where problems occur
        if early_problems:
            issues_str = '; '.join([f"Hop {p['hop']}: {', '.join(p['issues'])}" for p in early_problems])
            incident.factors.append(CorrelatedFactor(
                category="gateway",
                description=f"Network path issues detected near your local network (hops 1-3). "
                           f"This indicates problems between your device and ISP. Issues: {issues_str}",
                severity=SeverityLevel.WARNING if len(early_problems) == 1 else SeverityLevel.CRITICAL,
                timestamp=snapshot.timestamp,
                metrics={
                    'target': snapshot.target,
                    'problem_hop_count': len(early_problems),
                    'affected_hops': [p['hop'] for p in early_problems]
                }
            ))

        if mid_problems:
            issues_str = '; '.join([f"Hop {p['hop']}: {', '.join(p['issues'])}" for p in mid_problems])
            incident.factors.append(CorrelatedFactor(
                category="internet",
                description=f"Network path issues detected in ISP network (hops 4-8). "
                           f"This suggests problems with your Internet Service Provider. Issues: {issues_str}",
                severity=SeverityLevel.WARNING,
                timestamp=snapshot.timestamp,
                metrics={
                    'target': snapshot.target,
                    'problem_hop_count': len(mid_problems),
                    'affected_hops': [p['hop'] for p in mid_problems]
                }
            ))

        if late_problems:
            issues_str = '; '.join([f"Hop {p['hop']}: {', '.join(p['issues'])}" for p in late_problems])
            incident.factors.append(CorrelatedFactor(
                category="internet",
                description=f"Network path issues detected on internet backbone (hops 9+). "
                           f"This may indicate broader internet congestion. Issues: {issues_str}",
                severity=SeverityLevel.INFO,
                timestamp=snapshot.timestamp,
                metrics={
                    'target': snapshot.target,
                    'problem_hop_count': len(late_problems),
                    'affected_hops': [p['hop'] for p in late_problems]
                }
            ))

        # Check for high overall latency
        if snapshot.avg_latency_ms > 100:
            incident.factors.append(CorrelatedFactor(
                category="internet",
                description=f"High average path latency to {snapshot.target}: {snapshot.avg_latency_ms:.0f}ms "
                           f"across {snapshot.hop_count} hops. This contributes to slow response times.",
                severity=SeverityLevel.WARNING if snapshot.avg_latency_ms < 200 else SeverityLevel.CRITICAL,
                timestamp=snapshot.timestamp,
                metrics={
                    'target': snapshot.target,
                    'avg_latency_ms': snapshot.avg_latency_ms,
                    'max_latency_ms': snapshot.max_latency_ms,
                    'hop_count': snapshot.hop_count
                }
            ))
    
    def _analyze_metric_changes(self, incident: SlowdownIncident) -> None:
        """
        Compare metrics BEFORE the slowdown vs DURING the slowdown
        to identify what changed right before the speed drop.
        """
        # Define time windows
        # "Before" = 15 minutes before the incident started
        # "During" = the incident period itself
        before_start = incident.start_time - timedelta(minutes=15)
        before_end = incident.start_time - timedelta(minutes=1)
        during_start = incident.start_time
        during_end = incident.end_time
        
        # Analyze WiFi metric changes
        self._compare_wifi_metrics(incident, before_start, before_end, during_start, during_end)
        
        # Analyze network diagnostic changes
        self._compare_network_metrics(incident, before_start, before_end, during_start, during_end)
        
        # Analyze ping metric changes
        self._compare_ping_metrics(incident, before_start, before_end, during_start, during_end)
        
        # Identify likely trigger factors (significant changes that happened right before)
        self._identify_triggers(incident)
    
    def _compare_wifi_metrics(self, incident: SlowdownIncident,
                               before_start: datetime, before_end: datetime,
                               during_start: datetime, during_end: datetime) -> None:
        """Compare WiFi metrics before vs during the slowdown"""
        # Get samples for each period
        before_samples = [
            d for d in self._wifi_data
            if d.get('_parsed_time') and before_start <= d['_parsed_time'] <= before_end
        ]
        during_samples = [
            d for d in self._wifi_data
            if d.get('_parsed_time') and during_start <= d['_parsed_time'] <= during_end
        ]
        
        if not before_samples or not during_samples:
            return
        
        # Compare RSSI (signal strength)
        before_rssi = [int(s.get('rssi', 0)) for s in before_samples if int(s.get('rssi', 0)) < 0]
        during_rssi = [int(s.get('rssi', 0)) for s in during_samples if int(s.get('rssi', 0)) < 0]
        
        if before_rssi and during_rssi:
            before_avg = sum(before_rssi) / len(before_rssi)
            during_avg = sum(during_rssi) / len(during_rssi)
            change = during_avg - before_avg
            change_pct = (change / abs(before_avg)) * 100 if before_avg != 0 else 0
            
            # Negative change in RSSI means weaker signal (RSSI is negative, so more negative = worse)
            is_significant = change < -5  # 5 dBm drop is significant
            direction = "decreased" if change < -2 else ("increased" if change > 2 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="WiFi Signal (RSSI)",
                category="wifi_signal",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"Signal {'dropped' if change < 0 else 'improved'} from {before_avg:.0f} to {during_avg:.0f} dBm"
            ))
        
        # Compare SNR (signal-to-noise ratio)
        before_snr = [float(s.get('snr', 0)) for s in before_samples if float(s.get('snr', 0)) > 0]
        during_snr = [float(s.get('snr', 0)) for s in during_samples if float(s.get('snr', 0)) > 0]
        
        if before_snr and during_snr:
            before_avg = sum(before_snr) / len(before_snr)
            during_avg = sum(during_snr) / len(during_snr)
            change = during_avg - before_avg
            change_pct = (change / before_avg) * 100 if before_avg != 0 else 0
            
            is_significant = change < -5  # 5 dB drop in SNR is significant
            direction = "decreased" if change < -2 else ("increased" if change > 2 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="Signal-to-Noise Ratio",
                category="interference",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"SNR {'dropped' if change < 0 else 'improved'} from {before_avg:.0f} to {during_avg:.0f} dB" + 
                           (" (interference increased)" if change < -5 else "")
            ))
        
        # Compare quality score
        before_quality = [float(s.get('quality_score', 0)) for s in before_samples if float(s.get('quality_score', 0)) > 0]
        during_quality = [float(s.get('quality_score', 0)) for s in during_samples if float(s.get('quality_score', 0)) > 0]
        
        if before_quality and during_quality:
            before_avg = sum(before_quality) / len(before_quality)
            during_avg = sum(during_quality) / len(during_quality)
            change = during_avg - before_avg
            change_pct = (change / before_avg) * 100 if before_avg != 0 else 0
            
            is_significant = change < -15  # 15% drop in quality is significant
            direction = "decreased" if change < -5 else ("increased" if change > 5 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="WiFi Quality Score",
                category="wifi_signal",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"Quality {'dropped' if change < 0 else 'improved'} from {before_avg:.0f}% to {during_avg:.0f}%"
            ))
    
    def _compare_network_metrics(self, incident: SlowdownIncident,
                                  before_start: datetime, before_end: datetime,
                                  during_start: datetime, during_end: datetime) -> None:
        """Compare network diagnostic metrics before vs during"""
        before_diags = [
            d for d in self._network_diag
            if d.get('_parsed_time') and before_start <= d['_parsed_time'] <= before_end
        ]
        during_diags = [
            d for d in self._network_diag
            if d.get('_parsed_time') and during_start <= d['_parsed_time'] <= during_end
        ]
        
        if not before_diags or not during_diags:
            return
        
        # Compare gateway latency
        def safe_float(val, default=0):
            try:
                return float(val) if val not in (None, '') else default
            except (ValueError, TypeError):
                return default
        
        before_gw_lat = [safe_float(d.get('gateway_latency', 0)) for d in before_diags if safe_float(d.get('gateway_latency', 0)) > 0]
        during_gw_lat = [safe_float(d.get('gateway_latency', 0)) for d in during_diags if safe_float(d.get('gateway_latency', 0)) > 0]
        
        if before_gw_lat and during_gw_lat:
            before_avg = sum(before_gw_lat) / len(before_gw_lat)
            during_avg = sum(during_gw_lat) / len(during_gw_lat)
            change = during_avg - before_avg
            change_pct = (change / before_avg) * 100 if before_avg != 0 else 0
            
            is_significant = change > 20 or change_pct > 100  # 20ms increase or 100% increase
            direction = "increased" if change > 5 else ("decreased" if change < -5 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="Gateway Latency",
                category="gateway",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"Router latency {'spiked' if change > 20 else 'changed'} from {before_avg:.0f}ms to {during_avg:.0f}ms"
            ))
        
        # Compare internet latency
        before_inet_lat = [safe_float(d.get('internet_latency', 0)) for d in before_diags if safe_float(d.get('internet_latency', 0)) > 0]
        during_inet_lat = [safe_float(d.get('internet_latency', 0)) for d in during_diags if safe_float(d.get('internet_latency', 0)) > 0]
        
        if before_inet_lat and during_inet_lat:
            before_avg = sum(before_inet_lat) / len(before_inet_lat)
            during_avg = sum(during_inet_lat) / len(during_inet_lat)
            change = during_avg - before_avg
            change_pct = (change / before_avg) * 100 if before_avg != 0 else 0
            
            is_significant = change > 50 or change_pct > 100
            direction = "increased" if change > 10 else ("decreased" if change < -10 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="Internet Latency",
                category="internet",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"Internet latency {'spiked' if change > 50 else 'changed'} from {before_avg:.0f}ms to {during_avg:.0f}ms"
            ))
        
        # Compare packet loss
        before_loss = [safe_float(d.get('gateway_loss', 0)) + safe_float(d.get('internet_loss', 0)) for d in before_diags]
        during_loss = [safe_float(d.get('gateway_loss', 0)) + safe_float(d.get('internet_loss', 0)) for d in during_diags]
        
        if before_loss and during_loss:
            before_avg = sum(before_loss) / len(before_loss)
            during_avg = sum(during_loss) / len(during_loss)
            change = during_avg - before_avg
            
            is_significant = during_avg > 5 and change > 3  # Loss went above 5% with 3%+ increase
            direction = "increased" if change > 1 else ("decreased" if change < -1 else "stable")
            
            if change != 0 or during_avg > 0:
                incident.metric_changes.append(MetricChange(
                    metric_name="Packet Loss",
                    category="congestion",
                    before_value=round(before_avg, 1),
                    during_value=round(during_avg, 1),
                    change_amount=round(change, 1),
                    change_percent=round((change / max(before_avg, 0.1)) * 100, 1),
                    direction=direction,
                    is_significant=is_significant,
                    description=f"Packet loss {'appeared' if before_avg < 1 and during_avg > 3 else 'changed'} from {before_avg:.1f}% to {during_avg:.1f}%"
                ))
    
    def _compare_ping_metrics(self, incident: SlowdownIncident,
                               before_start: datetime, before_end: datetime,
                               during_start: datetime, during_end: datetime) -> None:
        """Compare ping metrics before vs during"""
        before_pings = [
            p for p in self._ping_data
            if p.get('_parsed_time') and before_start <= p['_parsed_time'] <= before_end
        ]
        during_pings = [
            p for p in self._ping_data
            if p.get('_parsed_time') and during_start <= p['_parsed_time'] <= during_end
        ]
        
        if not before_pings or not during_pings:
            return
        
        # Compare ping latency
        before_lat = [float(p.get('latency', 0)) for p in before_pings 
                      if float(p.get('latency', 0)) > 0 and 'fail' not in p.get('status', '').lower()]
        during_lat = [float(p.get('latency', 0)) for p in during_pings 
                      if float(p.get('latency', 0)) > 0 and 'fail' not in p.get('status', '').lower()]
        
        if before_lat and during_lat:
            before_avg = sum(before_lat) / len(before_lat)
            during_avg = sum(during_lat) / len(during_lat)
            change = during_avg - before_avg
            change_pct = (change / before_avg) * 100 if before_avg != 0 else 0
            
            is_significant = change > 30 or change_pct > 50
            direction = "increased" if change > 10 else ("decreased" if change < -10 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="Ping Latency",
                category="congestion",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"Ping latency {'spiked' if change > 30 else 'changed'} from {before_avg:.0f}ms to {during_avg:.0f}ms"
            ))
        
        # Compare ping failure rate
        before_fails = len([p for p in before_pings if 'fail' in p.get('status', '').lower() or 'timeout' in p.get('status', '').lower()])
        during_fails = len([p for p in during_pings if 'fail' in p.get('status', '').lower() or 'timeout' in p.get('status', '').lower()])
        
        before_rate = (before_fails / len(before_pings)) * 100 if before_pings else 0
        during_rate = (during_fails / len(during_pings)) * 100 if during_pings else 0
        change = during_rate - before_rate
        
        if during_rate > 0 or before_rate > 0:
            is_significant = during_rate > 10 and change > 5
            direction = "increased" if change > 2 else ("decreased" if change < -2 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="Ping Failure Rate",
                category="congestion",
                before_value=round(before_rate, 1),
                during_value=round(during_rate, 1),
                change_amount=round(change, 1),
                change_percent=round((change / max(before_rate, 0.1)) * 100, 1) if before_rate > 0 else (100 if during_rate > 0 else 0),
                direction=direction,
                is_significant=is_significant,
                description=f"Ping failures {'appeared' if before_rate < 1 and during_rate > 5 else 'changed'} from {before_rate:.1f}% to {during_rate:.1f}%"
            ))
    
    def _identify_triggers(self, incident: SlowdownIncident) -> None:
        """Identify the most likely trigger factors based on metric changes"""
        triggers = []
        
        # Sort changes by significance and magnitude
        significant_changes = [mc for mc in incident.metric_changes if mc.is_significant]
        
        for mc in significant_changes:
            if mc.direction in ["increased", "decreased"]:
                # Determine if this change is likely a trigger
                trigger_desc = None
                
                if mc.category == "wifi_signal" and mc.direction == "decreased":
                    trigger_desc = f"📶 WiFi signal degraded ({mc.description})"
                elif mc.category == "interference" and mc.direction == "decreased":
                    trigger_desc = f"Wireless interference increased ({mc.description})"
                elif mc.category == "gateway" and mc.direction == "increased":
                    trigger_desc = f"Router/gateway issues detected ({mc.description})"
                elif mc.category == "internet" and mc.direction == "increased":
                    trigger_desc = f"ISP/internet path degraded ({mc.description})"
                elif mc.category == "congestion" and mc.direction == "increased":
                    trigger_desc = f"Network congestion detected ({mc.description})"
                
                if trigger_desc:
                    triggers.append(trigger_desc)
        
        # Also check for WiFi events that happened right before
        event_window_start = incident.start_time - timedelta(minutes=2)
        event_window_end = incident.start_time + timedelta(minutes=1)
        
        recent_events = [
            e for e in self._wifi_events
            if e.get('_parsed_time') and event_window_start <= e['_parsed_time'] <= event_window_end
        ]
        
        for event in recent_events:
            event_type = event.get('event_type', '').lower()
            if 'disconnect' in event_type:
                triggers.insert(0, f"WiFi disconnection right before slowdown")
            elif 'roam' in event_type:
                triggers.append(f"WiFi roaming event detected")
        
        incident.trigger_factors = triggers[:5]  # Top 5 triggers
    
    def _analyze_wifi_quality(self, incident: SlowdownIncident, 
                              start: datetime, end: datetime) -> None:
        """Analyze WiFi quality during the incident window"""
        relevant_samples = [
            d for d in self._wifi_data
            if d.get('_parsed_time') and start <= d['_parsed_time'] <= end
        ]
        
        if not relevant_samples:
            return
        
        # Analyze signal strength (RSSI)
        rssi_values = []
        snr_values = []
        quality_scores = []
        
        for sample in relevant_samples:
            try:
                rssi = int(sample.get('rssi', 0))
                if rssi < 0:  # Valid RSSI values are negative
                    rssi_values.append(rssi)
                
                snr = float(sample.get('snr', 0))
                if snr > 0:
                    snr_values.append(snr)
                
                quality = float(sample.get('quality_score', 0))
                if quality > 0:
                    quality_scores.append(quality)
            except (ValueError, TypeError):
                continue
        
        if rssi_values:
            avg_rssi = sum(rssi_values) / len(rssi_values)
            min_rssi = min(rssi_values)
            
            if min_rssi <= self.VERY_WEAK_SIGNAL_RSSI:
                incident.factors.append(CorrelatedFactor(
                    category="wifi_signal",
                    description=f"Very weak WiFi signal detected (min: {min_rssi} dBm, avg: {avg_rssi:.0f} dBm). "
                               f"Signal dropped below -80 dBm indicating potential distance from router or obstruction.",
                    severity=SeverityLevel.CRITICAL,
                    timestamp=relevant_samples[0].get('timestamp', ''),
                    metrics={'avg_rssi': avg_rssi, 'min_rssi': min_rssi, 'samples': len(rssi_values)}
                ))
            elif min_rssi <= self.WEAK_SIGNAL_RSSI:
                incident.factors.append(CorrelatedFactor(
                    category="wifi_signal",
                    description=f"Weak WiFi signal detected (min: {min_rssi} dBm, avg: {avg_rssi:.0f} dBm). "
                               f"Consider moving closer to the router or reducing obstructions.",
                    severity=SeverityLevel.WARNING,
                    timestamp=relevant_samples[0].get('timestamp', ''),
                    metrics={'avg_rssi': avg_rssi, 'min_rssi': min_rssi, 'samples': len(rssi_values)}
                ))
        
        if snr_values:
            avg_snr = sum(snr_values) / len(snr_values)
            min_snr = min(snr_values)
            
            if min_snr < self.LOW_SNR_THRESHOLD:
                incident.factors.append(CorrelatedFactor(
                    category="interference",
                    description=f"Poor signal-to-noise ratio detected (min: {min_snr:.0f} dB, avg: {avg_snr:.0f} dB). "
                               f"This indicates wireless interference from other devices or networks.",
                    severity=SeverityLevel.WARNING if min_snr > 15 else SeverityLevel.CRITICAL,
                    timestamp=relevant_samples[0].get('timestamp', ''),
                    metrics={'avg_snr': avg_snr, 'min_snr': min_snr}
                ))
        
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            min_quality = min(quality_scores)
            
            if min_quality < self.LOW_QUALITY_SCORE:
                incident.factors.append(CorrelatedFactor(
                    category="wifi_signal",
                    description=f"Low WiFi quality score (min: {min_quality:.0f}%, avg: {avg_quality:.0f}%). "
                               f"Overall connection quality was degraded during this period.",
                    severity=SeverityLevel.WARNING,
                    timestamp=relevant_samples[0].get('timestamp', ''),
                    metrics={'avg_quality': avg_quality, 'min_quality': min_quality}
                ))
    
    def _analyze_wifi_events(self, incident: SlowdownIncident,
                             start: datetime, end: datetime) -> None:
        """Analyze WiFi events (disconnections, roaming) during incident"""
        relevant_events = [
            e for e in self._wifi_events
            if e.get('_parsed_time') and start <= e['_parsed_time'] <= end
        ]
        
        disconnect_count = 0
        roam_count = 0
        
        for event in relevant_events:
            event_type = event.get('event_type', '').lower()
            
            if 'disconnect' in event_type or 'lost' in event_type:
                disconnect_count += 1
            elif 'roam' in event_type or 'switch' in event_type:
                roam_count += 1
        
        if disconnect_count > 0:
            incident.factors.append(CorrelatedFactor(
                category="event",
                description=f"WiFi disconnection(s) detected: {disconnect_count} disconnect event(s) "
                           f"occurred during this slowdown period. Connection instability likely caused speed issues.",
                severity=SeverityLevel.CRITICAL,
                timestamp=relevant_events[0].get('timestamp', '') if relevant_events else '',
                metrics={'disconnect_count': disconnect_count}
            ))
        
        if roam_count > 0:
            incident.factors.append(CorrelatedFactor(
                category="event",
                description=f"WiFi roaming detected: {roam_count} roaming event(s). "
                           f"Device switched between access points which can cause temporary slowdowns.",
                severity=SeverityLevel.INFO,
                timestamp=relevant_events[0].get('timestamp', '') if relevant_events else '',
                metrics={'roam_count': roam_count}
            ))
    
    def _analyze_network_diagnostics(self, incident: SlowdownIncident,
                                     start: datetime, end: datetime) -> None:
        """Analyze network diagnostics during incident"""
        relevant_diags = [
            d for d in self._network_diag
            if d.get('_parsed_time') and start <= d['_parsed_time'] <= end
        ]
        
        if not relevant_diags:
            return
        
        gateway_latencies = []
        internet_latencies = []
        gateway_losses = []
        internet_losses = []
        
        for diag in relevant_diags:
            try:
                gw_lat = float(diag.get('gateway_latency', 0))
                if gw_lat > 0:
                    gateway_latencies.append(gw_lat)
                
                inet_lat = float(diag.get('internet_latency', 0))
                if inet_lat > 0:
                    internet_latencies.append(inet_lat)
                
                gw_loss = float(diag.get('gateway_loss', 0))
                gateway_losses.append(gw_loss)
                
                inet_loss = float(diag.get('internet_loss', 0))
                internet_losses.append(inet_loss)
            except (ValueError, TypeError):
                continue
        
        # Analyze gateway issues (local network)
        if gateway_latencies:
            avg_gw_lat = sum(gateway_latencies) / len(gateway_latencies)
            max_gw_lat = max(gateway_latencies)
            
            if max_gw_lat > self.HIGH_GATEWAY_LATENCY:
                incident.factors.append(CorrelatedFactor(
                    category="gateway",
                    description=f"High gateway/router latency detected (max: {max_gw_lat:.0f}ms, avg: {avg_gw_lat:.0f}ms). "
                               f"This indicates local network congestion or router issues.",
                    severity=SeverityLevel.WARNING if max_gw_lat < 50 else SeverityLevel.CRITICAL,
                    timestamp=relevant_diags[0].get('timestamp', ''),
                    metrics={'avg_latency': avg_gw_lat, 'max_latency': max_gw_lat}
                ))
        
        if gateway_losses:
            avg_gw_loss = sum(gateway_losses) / len(gateway_losses)
            max_gw_loss = max(gateway_losses)
            
            if max_gw_loss > self.PACKET_LOSS_THRESHOLD:
                incident.factors.append(CorrelatedFactor(
                    category="gateway",
                    description=f"Packet loss to gateway detected (max: {max_gw_loss:.1f}%, avg: {avg_gw_loss:.1f}%). "
                               f"Packets are being lost between your device and router.",
                    severity=SeverityLevel.CRITICAL,
                    timestamp=relevant_diags[0].get('timestamp', ''),
                    metrics={'avg_loss': avg_gw_loss, 'max_loss': max_gw_loss}
                ))
        
        # Analyze internet issues (ISP/external)
        if internet_latencies:
            avg_inet_lat = sum(internet_latencies) / len(internet_latencies)
            max_inet_lat = max(internet_latencies)
            
            if max_inet_lat > self.HIGH_INTERNET_LATENCY:
                incident.factors.append(CorrelatedFactor(
                    category="internet",
                    description=f"High internet latency detected (max: {max_inet_lat:.0f}ms, avg: {avg_inet_lat:.0f}ms). "
                               f"This may indicate ISP congestion or routing issues.",
                    severity=SeverityLevel.WARNING,
                    timestamp=relevant_diags[0].get('timestamp', ''),
                    metrics={'avg_latency': avg_inet_lat, 'max_latency': max_inet_lat}
                ))
        
        if internet_losses:
            avg_inet_loss = sum(internet_losses) / len(internet_losses)
            max_inet_loss = max(internet_losses)
            
            if max_inet_loss > self.PACKET_LOSS_THRESHOLD:
                incident.factors.append(CorrelatedFactor(
                    category="internet",
                    description=f"Internet packet loss detected (max: {max_inet_loss:.1f}%, avg: {avg_inet_loss:.1f}%). "
                               f"Packets are being lost on the internet path - likely ISP issue.",
                    severity=SeverityLevel.CRITICAL,
                    timestamp=relevant_diags[0].get('timestamp', ''),
                    metrics={'avg_loss': avg_inet_loss, 'max_loss': max_inet_loss}
                ))
    
    def _analyze_ping_data(self, incident: SlowdownIncident,
                           start: datetime, end: datetime) -> None:
        """Analyze ping data for latency spikes and packet loss"""
        relevant_pings = [
            p for p in self._ping_data
            if p.get('_parsed_time') and start <= p['_parsed_time'] <= end
        ]
        
        if not relevant_pings:
            return
        
        latencies = []
        losses = []
        failed_count = 0
        
        for ping in relevant_pings:
            try:
                status = ping.get('status', '').lower()
                if 'fail' in status or 'timeout' in status:
                    failed_count += 1
                    continue
                
                latency = float(ping.get('latency', 0))
                if latency > 0:
                    latencies.append(latency)
                
                loss = float(ping.get('packet_loss', 0))
                losses.append(loss)
            except (ValueError, TypeError):
                continue
        
        if failed_count > 0:
            fail_rate = (failed_count / len(relevant_pings)) * 100
            if fail_rate > 10:
                incident.factors.append(CorrelatedFactor(
                    category="congestion",
                    description=f"High ping failure rate: {failed_count} of {len(relevant_pings)} pings failed "
                               f"({fail_rate:.1f}%). Network connectivity was intermittent.",
                    severity=SeverityLevel.CRITICAL,
                    timestamp=relevant_pings[0].get('timestamp', ''),
                    metrics={'failed_count': failed_count, 'total': len(relevant_pings), 'fail_rate': fail_rate}
                ))
        
        if latencies:
            avg_lat = sum(latencies) / len(latencies)
            max_lat = max(latencies)
            
            # Check for latency spikes (values much higher than average)
            spikes = [l for l in latencies if l > avg_lat * 3 and l > 50]
            if spikes:
                incident.factors.append(CorrelatedFactor(
                    category="congestion",
                    description=f"Latency spikes detected: {len(spikes)} ping(s) with unusually high latency "
                               f"(max: {max_lat:.0f}ms, avg: {avg_lat:.0f}ms). Network congestion likely.",
                    severity=SeverityLevel.WARNING,
                    timestamp=relevant_pings[0].get('timestamp', ''),
                    metrics={'spike_count': len(spikes), 'max_latency': max_lat, 'avg_latency': avg_lat}
                ))
    
    def _generate_summary(self, incident: SlowdownIncident) -> None:
        """Generate a human-readable summary and recommendations (connection-type aware)"""
        duration = incident.end_time - incident.start_time
        duration_mins = duration.total_seconds() / 60
        
        # Connection type label
        conn_type_label = {
            "wifi": "WiFi",
            "ethernet": "Ethernet (wired)",
            "unknown": "Network"
        }.get(incident.connection_type, "Network")
        
        # Build summary
        summary_parts = [
            f"{conn_type_label} slowdown detected from {incident.start_time.strftime('%Y-%m-%d %H:%M')} "
            f"to {incident.end_time.strftime('%H:%M')} ({duration_mins:.0f} minutes).",
            f"Average speeds: {incident.avg_download:.1f} Mbps down, {incident.avg_upload:.1f} Mbps up, "
            f"{incident.avg_ping:.0f}ms ping.",
            f"{len(incident.speed_tests)} consecutive slow speed tests recorded."
        ]
        
        if incident.factors:
            summary_parts.append(f"\nIdentified {len(incident.factors)} potential contributing factor(s):")
            
            # Group by severity
            critical = [f for f in incident.factors if f.severity == SeverityLevel.CRITICAL]
            warnings = [f for f in incident.factors if f.severity == SeverityLevel.WARNING]
            
            if critical:
                summary_parts.append(f"  • {len(critical)} critical issue(s)")
            if warnings:
                summary_parts.append(f"  • {len(warnings)} warning(s)")
        else:
            if incident.connection_type == "ethernet":
                summary_parts.append("\nNo local factors identified on wired connection - likely ISP or router issue.")
            else:
                summary_parts.append("\nNo obvious local factors identified - issue may be ISP-related.")
        
        incident.summary = "\n".join(summary_parts)
        
        # Generate recommendations based on factors AND connection type
        recommendations = set()
        
        for factor in incident.factors:
            if factor.category == "wifi_signal":
                recommendations.add("Move closer to your WiFi router or access point")
                recommendations.add("Check for physical obstructions between device and router")
                recommendations.add("Consider using a WiFi extender or mesh system")
            
            elif factor.category == "interference":
                recommendations.add("Change WiFi channel to reduce interference (try channels 1, 6, or 11 for 2.4GHz)")
                recommendations.add("Move away from other electronic devices that may cause interference")
                recommendations.add("Consider switching to 5GHz band if available")
            
            elif factor.category == "gateway":
                recommendations.add("Restart your router/gateway")
                recommendations.add("Check if other devices are consuming bandwidth")
                recommendations.add("Consider upgrading your router if it's older")
            
            elif factor.category == "internet":
                recommendations.add("Contact your ISP if issues persist")
                recommendations.add("Check ISP status page for known outages")
                recommendations.add("Try using a different DNS server (e.g., 8.8.8.8 or 1.1.1.1)")
            
            elif factor.category == "event":
                recommendations.add("Check WiFi router logs for issues")
                recommendations.add("Ensure router firmware is up to date")
            
            elif factor.category == "congestion":
                recommendations.add("Reduce number of connected devices")
                recommendations.add("Schedule bandwidth-heavy tasks for off-peak hours")
        
        # Add connection-type specific recommendations
        if incident.connection_type == "ethernet":
            if not incident.factors:
                recommendations.add("Check Ethernet cable for damage or loose connections")
                recommendations.add("Try a different Ethernet port on your router")
                recommendations.add("Test with a different Ethernet cable")
            recommendations.add("Check router/switch for issues - restart if needed")
        elif incident.connection_type == "wifi" and not any(f.category in ["wifi_signal", "interference"] for f in incident.factors):
            recommendations.add("Consider using a wired Ethernet connection for more stable performance")
        
        incident.recommendations = list(recommendations)
    
    def get_analysis_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Run full analysis and return a comprehensive report.
        This is the main entry point for the analyzer.
        """
        self.load_all_logs(hours=hours)
        incidents = self.detect_slowdown_incidents()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_period_hours': hours,
            'thresholds': {
                'slow_download_mbps': self.SLOW_DOWNLOAD_THRESHOLD,
                'consecutive_tests_required': self.CONSECUTIVE_SLOW_COUNT,
                'weak_signal_rssi': self.WEAK_SIGNAL_RSSI,
                'high_ping_ms': self.HIGH_PING_THRESHOLD
            },
            'data_summary': {
                'speed_tests_analyzed': len(self._speedtest_data),
                'wifi_samples_analyzed': len(self._wifi_data),
                'wifi_events_analyzed': len(self._wifi_events),
                'network_diagnostics_analyzed': len(self._network_diag),
                'ping_samples_analyzed': len(self._ping_data)
            },
            'incidents_detected': len(incidents),
            'incidents': []
        }
        
        for incident in incidents:
            incident_data = {
                'start_time': incident.start_time.isoformat(),
                'end_time': incident.end_time.isoformat(),
                'duration_minutes': (incident.end_time - incident.start_time).total_seconds() / 60,
                'speed_test_count': len(incident.speed_tests),
                'connection_type': incident.connection_type,  # "wifi", "ethernet", or "unknown"
                'avg_download_mbps': round(incident.avg_download, 2),
                'avg_upload_mbps': round(incident.avg_upload, 2),
                'avg_ping_ms': round(incident.avg_ping, 1),
                'access_point': incident.access_point.to_dict() if incident.access_point else None,
                'summary': incident.summary,
                'factors': [
                    {
                        'category': f.category,
                        'severity': f.severity.value,
                        'description': f.description,
                        'timestamp': f.timestamp,
                        'metrics': f.metrics
                    }
                    for f in incident.factors
                ],
                'metric_changes': [
                    {
                        'metric_name': mc.metric_name,
                        'category': mc.category,
                        'before_value': mc.before_value,
                        'during_value': mc.during_value,
                        'change_amount': mc.change_amount,
                        'change_percent': mc.change_percent,
                        'direction': mc.direction,
                        'is_significant': mc.is_significant,
                        'description': mc.description
                    }
                    for mc in incident.metric_changes
                ],
                'trigger_factors': incident.trigger_factors,
                'traceroute_snapshots': [
                    snapshot.to_dict() for snapshot in incident.traceroute_snapshots
                ],
                'recommendations': incident.recommendations
            }
            report['incidents'].append(incident_data)
        
        # Add overall health assessment
        # Check if any incident is "active" (ended within last 30 minutes)
        active_threshold = datetime.now() - timedelta(minutes=30)
        active_incidents = [inc for inc in incidents if inc.end_time >= active_threshold]
        past_incidents = [inc for inc in incidents if inc.end_time < active_threshold]
        
        if active_incidents:
            # There's an active/recent issue
            report['overall_status'] = 'degraded'
            report['overall_message'] = f"Active slowdown detected! {len(active_incidents)} ongoing issue(s)."
            report['is_active'] = True

            # Send notification for the most recent active incident
            if self._notification_manager and active_incidents:
                latest_incident = active_incidents[-1]

                # Only notify if this is a new incident (not the same one we notified about before)
                incident_id = f"{latest_incident.start_time}_{latest_incident.end_time}"
                if self._last_notified_incident != incident_id:
                    # Extract primary cause from factors
                    primary_cause = None
                    if latest_incident.factors:
                        # Get the most critical factor
                        critical_factors = [f for f in latest_incident.factors if f.severity == SeverityLevel.CRITICAL]
                        if critical_factors:
                            primary_cause = critical_factors[0].description
                        elif latest_incident.factors:
                            primary_cause = latest_incident.factors[0].description

                    duration_minutes = int((latest_incident.end_time - latest_incident.start_time).total_seconds() / 60)

                    # Send the notification
                    try:
                        self._notification_manager.send_slowdown_notification(
                            download_speed=latest_incident.avg_download,
                            upload_speed=latest_incident.avg_upload,
                            duration_minutes=duration_minutes,
                            primary_cause=primary_cause
                        )
                        self._last_notified_incident = incident_id
                        logger.info(f"Sent notification for incident at {latest_incident.start_time}")
                    except Exception as e:
                        logger.error(f"Failed to send notification: {e}")
        elif past_incidents:
            # Only past issues - show counter
            report['overall_status'] = 'slowdowns'
            report['slowdown_count'] = len(past_incidents)
            report['overall_message'] = f"{len(past_incidents)} past slowdown(s) in the last {hours} hours."
            report['is_active'] = False
        else:
            report['overall_status'] = 'healthy'
            report['overall_message'] = f"No significant slowdowns detected in the past {hours} hours."
            report['is_active'] = False
            report['slowdown_count'] = 0
        
        return report
    
    def get_latest_analysis(self) -> Optional[Dict[str, Any]]:
        """Get analysis of just the most recent slowdown incident if any"""
        report = self.get_analysis_report(hours=24)
        
        if report['incidents']:
            return {
                'has_recent_incident': True,
                'latest_incident': report['incidents'][-1],
                'overall_status': report['overall_status']
            }
        return {
            'has_recent_incident': False,
            'overall_status': 'healthy',
            'message': 'No recent slowdown incidents detected'
        }


# Singleton instance
_analyzer_instance = None


def get_network_analyzer() -> NetworkAnalyzer:
    """Get or create the singleton NetworkAnalyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = NetworkAnalyzer()
    return _analyzer_instance


if __name__ == '__main__':
    # Test the analyzer
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    analyzer = NetworkAnalyzer()
    report = analyzer.get_analysis_report(hours=168)  # Last week
    
    print(json.dumps(report, indent=2))
