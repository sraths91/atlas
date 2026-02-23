"""
Fleet Network Analyzer
Server-side analysis of network logs received from endpoint agents.
Processes widget logs stored in the fleet database to detect slowdowns
and correlate them with WiFi quality, ping data, and other metrics.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CorrelatedFactor:
    """A factor that may have contributed to a network issue"""
    category: str
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
class SlowdownIncident:
    """Represents a detected network slowdown incident"""
    machine_id: str
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
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class FleetNetworkAnalyzer:
    """
    Analyzes network logs from fleet agents to identify network issues.
    Works with widget logs stored in the fleet database.
    """
    
    # Thresholds for detecting issues (aligned with endpoint agent)
    SLOW_DOWNLOAD_THRESHOLD = 20.0  # Mbps
    SLOW_UPLOAD_THRESHOLD = 5.0  # Mbps
    HIGH_PING_THRESHOLD = 100.0  # ms
    CONSECUTIVE_SLOW_COUNT = 3  # Number of consecutive slow tests to trigger analysis
    
    # WiFi quality thresholds (using RSSI like endpoint agent)
    WEAK_SIGNAL_RSSI = -70  # dBm (weak signal)
    VERY_WEAK_SIGNAL_RSSI = -80  # dBm (very weak)
    LOW_SNR_THRESHOLD = 20  # dB (poor signal-to-noise)
    LOW_QUALITY_SCORE = 50  # Quality score percentage
    WEAK_SIGNAL_PERCENT = 60  # % (fallback for percentage-based signals)
    
    # Network diagnostic thresholds
    HIGH_GATEWAY_LATENCY = 20  # ms
    HIGH_INTERNET_LATENCY = 100  # ms
    PACKET_LOSS_THRESHOLD = 5  # percentage
    
    # Correlation window
    CORRELATION_WINDOW_MINUTES = 5  # minutes before/after incident
    
    def __init__(self, data_store):
        """
        Initialize with fleet data store
        
        Args:
            data_store: Fleet data store instance with widget logs
        """
        self.data_store = data_store
    
    def analyze_machine(self, machine_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze network logs for a specific machine
        
        Args:
            machine_id: Machine identifier
            hours: Number of hours to analyze
            
        Returns:
            Analysis report dictionary
        """
        # Get widget logs for this machine
        logs = self._get_machine_logs(machine_id, hours)
        
        if not logs:
            return {
                'machine_id': machine_id,
                'status': 'no_data',
                'message': 'No log data available for analysis',
                'incidents': [],
                'overall_status': 'unknown'
            }
        
        # Parse logs by type
        speed_tests = self._extract_speed_tests(logs)
        wifi_logs = self._extract_wifi_logs(logs)
        ping_logs = self._extract_ping_logs(logs)
        
        # Detect slowdown incidents
        incidents = self._detect_slowdowns(speed_tests, wifi_logs, ping_logs, machine_id)
        
        # Generate overall status
        overall_status = self._determine_status(incidents, speed_tests)
        
        return {
            'machine_id': machine_id,
            'analysis_time': datetime.now().isoformat(),
            'period_hours': hours,
            'total_logs': len(logs),
            'speed_tests_analyzed': len(speed_tests),
            'incidents_detected': len(incidents),
            'incidents': [self._incident_to_dict(i) for i in incidents],
            'overall_status': overall_status['status'],
            'overall_message': overall_status['message'],
            'avg_download': overall_status.get('avg_download', 0),
            'avg_upload': overall_status.get('avg_upload', 0),
            'avg_ping': overall_status.get('avg_ping', 0)
        }
    
    def analyze_fleet(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze network logs across all machines in the fleet
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Fleet-wide analysis report
        """
        machines = self.data_store.get_all_machines()
        
        fleet_report = {
            'analysis_time': datetime.now().isoformat(),
            'period_hours': hours,
            'total_machines': len(machines),
            'machines_analyzed': 0,
            'machines_with_issues': 0,
            'total_incidents': 0,
            'machine_reports': [],
            'fleet_summary': {}
        }
        
        all_downloads = []
        all_uploads = []
        all_pings = []
        
        for machine in machines:
            machine_id = machine.get('machine_id')
            if not machine_id:
                continue
            
            report = self.analyze_machine(machine_id, hours)
            fleet_report['machine_reports'].append(report)
            
            if report.get('status') != 'no_data':
                fleet_report['machines_analyzed'] += 1
                
                if report.get('incidents_detected', 0) > 0:
                    fleet_report['machines_with_issues'] += 1
                    fleet_report['total_incidents'] += report['incidents_detected']
                
                if report.get('avg_download'):
                    all_downloads.append(report['avg_download'])
                if report.get('avg_upload'):
                    all_uploads.append(report['avg_upload'])
                if report.get('avg_ping'):
                    all_pings.append(report['avg_ping'])
        
        # Calculate fleet averages
        fleet_report['fleet_summary'] = {
            'avg_download': sum(all_downloads) / len(all_downloads) if all_downloads else 0,
            'avg_upload': sum(all_uploads) / len(all_uploads) if all_uploads else 0,
            'avg_ping': sum(all_pings) / len(all_pings) if all_pings else 0,
            'health_score': self._calculate_fleet_health(fleet_report)
        }
        
        return fleet_report
    
    def _get_machine_logs(self, machine_id: str, hours: int) -> List[Dict[str, Any]]:
        """Get widget logs for a machine within the time period"""
        if not hasattr(self.data_store, 'get_widget_logs'):
            return []
        
        # Get a large batch of logs and filter by time
        all_logs = self.data_store.get_widget_logs(machine_id, limit=10000)
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_logs = []
        
        for log in all_logs:
            try:
                log_time = datetime.fromisoformat(log.get('timestamp', ''))
                if log_time >= cutoff_time:
                    filtered_logs.append(log)
            except (ValueError, TypeError):
                continue
        
        return filtered_logs
    
    def _extract_speed_tests(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract speed test results from logs"""
        speed_tests = []
        
        for log in logs:
            widget_type = log.get('widget_type', '')
            if widget_type == 'speedtest' or 'speed' in log.get('message', '').lower():
                data = log.get('data', {})
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, ValueError):
                        data = {}

                # Extract speed test data
                if data.get('download') or data.get('upload'):
                    speed_tests.append({
                        'timestamp': log.get('timestamp'),
                        'download': float(data.get('download', 0)),
                        'upload': float(data.get('upload', 0)),
                        'ping': float(data.get('ping', 0))
                    })
        
        return speed_tests
    
    def _extract_wifi_logs(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract WiFi quality logs"""
        wifi_logs = []
        
        for log in logs:
            widget_type = log.get('widget_type', '')
            if widget_type in ('wifi', 'wifi_quality', 'network_wifi'):
                data = log.get('data', {})
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, ValueError):
                        data = {}
                
                wifi_logs.append({
                    'timestamp': log.get('timestamp'),
                    'signal_strength': data.get('signal_strength', data.get('signal', 0)),
                    'noise': data.get('noise', 0),
                    'rssi': data.get('rssi', 0),
                    'snr': data.get('snr', 0),
                    'channel': data.get('channel', 0),
                    'ssid': data.get('ssid', ''),
                    'bssid': data.get('bssid', ''),  # Access point MAC address
                    'tx_rate': data.get('tx_rate', 0),
                    'quality_score': data.get('quality_score', 0),
                    'message': log.get('message', '')
                })
        
        return wifi_logs
    
    def _extract_ping_logs(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract ping/latency logs"""
        ping_logs = []
        
        for log in logs:
            widget_type = log.get('widget_type', '')
            if widget_type == 'ping' or 'ping' in log.get('message', '').lower():
                data = log.get('data', {})
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, ValueError):
                        data = {}
                
                if data.get('latency') or data.get('avg_latency'):
                    ping_logs.append({
                        'timestamp': log.get('timestamp'),
                        'latency': float(data.get('latency', data.get('avg_latency', 0))),
                        'packet_loss': float(data.get('packet_loss', 0)),
                        'target': data.get('target', '8.8.8.8')
                    })
        
        return ping_logs
    
    def _detect_slowdowns(self, speed_tests: List[Dict], wifi_logs: List[Dict], 
                          ping_logs: List[Dict], machine_id: str) -> List[SlowdownIncident]:
        """
        Detect slowdown incidents from speed tests and correlate with other data.
        Requires CONSECUTIVE_SLOW_COUNT consecutive slow tests to trigger an incident.
        """
        incidents = []
        
        if not speed_tests:
            return incidents
        
        # Sort by timestamp
        sorted_tests = sorted(speed_tests, key=lambda x: x.get('timestamp', ''))
        
        # Find consecutive slow tests (matching endpoint agent logic)
        slow_streak = []
        
        for test in sorted_tests:
            download = test.get('download', 0)
            upload = test.get('upload', 0)
            
            is_slow = download < self.SLOW_DOWNLOAD_THRESHOLD or upload < self.SLOW_UPLOAD_THRESHOLD
            
            if is_slow:
                slow_streak.append(test)
            else:
                # End of slow streak - only create incident if we have enough consecutive slow tests
                if len(slow_streak) >= self.CONSECUTIVE_SLOW_COUNT:
                    incident = self._create_incident(slow_streak, wifi_logs, ping_logs, machine_id)
                    if incident:
                        incidents.append(incident)
                slow_streak = []
        
        # Check final streak
        if len(slow_streak) >= self.CONSECUTIVE_SLOW_COUNT:
            incident = self._create_incident(slow_streak, wifi_logs, ping_logs, machine_id)
            if incident:
                incidents.append(incident)
        
        # Analyze each incident with delta analysis
        for incident in incidents:
            self._analyze_metric_changes(incident, wifi_logs, ping_logs)
            self._identify_triggers(incident)
        
        logger.info(f"Detected {len(incidents)} slowdown incidents for {machine_id}")
        return incidents
    
    def _create_incident(self, tests: List[Dict], wifi_logs: List[Dict], 
                         ping_logs: List[Dict], machine_id: str) -> Optional[SlowdownIncident]:
        """Create a slowdown incident from a group of slow tests"""
        if not tests:
            return None
        
        try:
            start_time = datetime.fromisoformat(tests[0]['timestamp'])
            end_time = datetime.fromisoformat(tests[-1]['timestamp'])
        except (ValueError, TypeError):
            start_time = datetime.now()
            end_time = datetime.now()
        
        avg_download = sum(t.get('download', 0) for t in tests) / len(tests)
        avg_upload = sum(t.get('upload', 0) for t in tests) / len(tests)
        avg_ping = sum(t.get('ping', 0) for t in tests) / len(tests)
        
        # Detect connection type and extract access point info
        connection_type = self._detect_connection_type(wifi_logs, start_time, end_time)
        access_point = None
        if connection_type == "wifi":
            access_point = self._extract_access_point_info(wifi_logs, start_time, end_time)
        
        incident = SlowdownIncident(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time,
            speed_tests=tests,
            avg_download=avg_download,
            avg_upload=avg_upload,
            avg_ping=avg_ping,
            connection_type=connection_type,
            access_point=access_point
        )
        
        # Find correlated factors (connection-type aware)
        incident.factors = self._find_correlated_factors(incident, wifi_logs, ping_logs)
        
        # Generate summary and recommendations
        incident.summary = self._generate_summary(incident)
        incident.recommendations = self._generate_recommendations(incident)
        
        return incident
    
    def _detect_connection_type(self, wifi_logs: List[Dict], 
                                 start_time: datetime, end_time: datetime) -> str:
        """Detect whether the connection was WiFi or Ethernet during the incident"""
        # Get WiFi logs during the incident
        incident_wifi = []
        for log in wifi_logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'])
                if start_time <= log_time <= end_time:
                    incident_wifi.append(log)
            except (ValueError, TypeError):
                continue
        
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
            rssi = sample.get('rssi', 0)
            if isinstance(rssi, (int, float)) and rssi < 0:
                return "wifi"
        
        # Default to unknown if we can't determine
        return "unknown"
    
    def _extract_access_point_info(self, wifi_logs: List[Dict], 
                                    start_time: datetime, end_time: datetime) -> Optional[AccessPointInfo]:
        """Extract access point information during the incident period"""
        # Get WiFi logs during the incident
        incident_wifi = []
        for log in wifi_logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'])
                if start_time <= log_time <= end_time:
                    incident_wifi.append(log)
            except (ValueError, TypeError):
                continue
        
        if not incident_wifi:
            return None
        
        # Get the most common SSID and BSSID during the incident
        ssids = [log.get('ssid', '') for log in incident_wifi if log.get('ssid')]
        bssids = [log.get('bssid', '') for log in incident_wifi if log.get('bssid')]
        channels = [log.get('channel', 0) for log in incident_wifi if log.get('channel')]
        rssis = [log.get('rssi', 0) for log in incident_wifi if log.get('rssi', 0) < 0]
        snrs = [log.get('snr', 0) for log in incident_wifi if log.get('snr', 0) > 0]
        tx_rates = [log.get('tx_rate', 0) for log in incident_wifi if log.get('tx_rate', 0) > 0]
        
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
    
    def _find_correlated_factors(self, incident: SlowdownIncident, 
                                  wifi_logs: List[Dict], ping_logs: List[Dict]) -> List[CorrelatedFactor]:
        """Find factors that correlate with the slowdown (connection-type aware)"""
        factors = []
        
        # Time window for correlation (matching endpoint agent: 5 minutes before/after)
        window_start = incident.start_time - timedelta(minutes=self.CORRELATION_WINDOW_MINUTES)
        window_end = incident.end_time + timedelta(minutes=self.CORRELATION_WINDOW_MINUTES)
        
        # Only check WiFi-specific factors if using WiFi
        if incident.connection_type != "ethernet":
            # Check WiFi logs for issues
            for log in wifi_logs:
                try:
                    log_time = datetime.fromisoformat(log['timestamp'])
                    if window_start <= log_time <= window_end:
                        # Check RSSI (preferred, like endpoint agent)
                        rssi = log.get('rssi', 0)
                        if rssi and rssi < 0:  # Valid RSSI is negative
                            if rssi < self.VERY_WEAK_SIGNAL_RSSI:
                                factors.append(CorrelatedFactor(
                                    category='wifi_signal',
                                    description=f'Very weak WiFi signal ({rssi} dBm)',
                                    severity=SeverityLevel.CRITICAL,
                                    timestamp=log['timestamp'],
                                    metrics={'rssi': rssi}
                                ))
                            elif rssi < self.WEAK_SIGNAL_RSSI:
                                factors.append(CorrelatedFactor(
                                    category='wifi_signal',
                                    description=f'Weak WiFi signal ({rssi} dBm)',
                                    severity=SeverityLevel.WARNING,
                                    timestamp=log['timestamp'],
                                    metrics={'rssi': rssi}
                                ))
                        else:
                            # Fallback to percentage-based signal strength
                            signal = log.get('signal_strength', 100)
                            if signal < self.WEAK_SIGNAL_PERCENT:
                                factors.append(CorrelatedFactor(
                                    category='wifi_signal',
                                    description=f'Weak WiFi signal ({signal}%)',
                                    severity=SeverityLevel.WARNING if signal > 40 else SeverityLevel.CRITICAL,
                                    timestamp=log['timestamp'],
                                    metrics={'signal_strength': signal}
                                ))
                        
                        # Check quality score
                        quality_score = log.get('quality_score', 100)
                        if quality_score and quality_score < self.LOW_QUALITY_SCORE:
                            factors.append(CorrelatedFactor(
                                category='wifi_quality',
                                description=f'Low WiFi quality score ({quality_score}%)',
                                severity=SeverityLevel.WARNING,
                                timestamp=log['timestamp'],
                                metrics={'quality_score': quality_score}
                            ))
                        
                        # Check noise level
                        noise = log.get('noise', 0)
                        if noise and noise < 0:  # Valid noise is negative
                            # Calculate SNR if we have both RSSI and noise
                            if rssi and rssi < 0:
                                snr = rssi - noise
                                if snr < self.LOW_SNR_THRESHOLD:
                                    factors.append(CorrelatedFactor(
                                        category='interference',
                                        description=f'Poor signal-to-noise ratio ({snr} dB)',
                                        severity=SeverityLevel.WARNING,
                                        timestamp=log['timestamp'],
                                        metrics={'snr': snr, 'rssi': rssi, 'noise': noise}
                                    ))
                        
                        # Check for WiFi events in message
                        message = log.get('message', '').lower()
                        if 'disconnect' in message or 'roam' in message or 'switch' in message:
                            factors.append(CorrelatedFactor(
                                category='wifi_event',
                                description=log.get('message', 'WiFi event detected'),
                                severity=SeverityLevel.WARNING,
                                timestamp=log['timestamp'],
                                metrics={}
                            ))
                except (ValueError, TypeError):
                    continue
        
        # Check ping logs for latency spikes and packet loss
        for log in ping_logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'])
                if window_start <= log_time <= window_end:
                    latency = log.get('latency', 0)
                    packet_loss = log.get('packet_loss', 0)
                    
                    if latency > self.HIGH_INTERNET_LATENCY:
                        factors.append(CorrelatedFactor(
                            category='internet_latency',
                            description=f'High internet latency ({latency:.0f}ms)',
                            severity=SeverityLevel.WARNING if latency < 200 else SeverityLevel.CRITICAL,
                            timestamp=log['timestamp'],
                            metrics={'latency': latency}
                        ))
                    elif latency > self.HIGH_GATEWAY_LATENCY:
                        factors.append(CorrelatedFactor(
                            category='gateway_latency',
                            description=f'Elevated latency ({latency:.0f}ms)',
                            severity=SeverityLevel.INFO,
                            timestamp=log['timestamp'],
                            metrics={'latency': latency}
                        ))
                    
                    if packet_loss > self.PACKET_LOSS_THRESHOLD:
                        factors.append(CorrelatedFactor(
                            category='packet_loss',
                            description=f'Packet loss ({packet_loss:.1f}%)',
                            severity=SeverityLevel.CRITICAL if packet_loss > 20 else SeverityLevel.WARNING,
                            timestamp=log['timestamp'],
                            metrics={'packet_loss': packet_loss}
                        ))
            except (ValueError, TypeError):
                continue
        
        return factors
    
    def _analyze_metric_changes(self, incident: SlowdownIncident, 
                                 wifi_logs: List[Dict], ping_logs: List[Dict]) -> None:
        """
        Compare metrics BEFORE the slowdown vs DURING the slowdown
        to identify what changed right before the speed drop.
        """
        # Define time windows (matching endpoint agent)
        # "Before" = 15 minutes before the incident started
        # "During" = the incident period itself
        before_start = incident.start_time - timedelta(minutes=15)
        before_end = incident.start_time - timedelta(minutes=1)
        during_start = incident.start_time
        during_end = incident.end_time
        
        # Analyze WiFi metric changes
        self._compare_wifi_metrics(incident, wifi_logs, before_start, before_end, during_start, during_end)
        
        # Analyze ping metric changes
        self._compare_ping_metrics(incident, ping_logs, before_start, before_end, during_start, during_end)
    
    def _compare_wifi_metrics(self, incident: SlowdownIncident, wifi_logs: List[Dict],
                               before_start: datetime, before_end: datetime,
                               during_start: datetime, during_end: datetime) -> None:
        """Compare WiFi metrics before vs during the slowdown"""
        # Get samples for each period
        before_samples = []
        during_samples = []
        
        for log in wifi_logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'])
                if before_start <= log_time <= before_end:
                    before_samples.append(log)
                elif during_start <= log_time <= during_end:
                    during_samples.append(log)
            except (ValueError, TypeError):
                continue
        
        if not before_samples or not during_samples:
            return
        
        # Compare RSSI (signal strength in dBm)
        before_rssi = [log.get('rssi', 0) for log in before_samples if log.get('rssi', 0) < 0]
        during_rssi = [log.get('rssi', 0) for log in during_samples if log.get('rssi', 0) < 0]
        
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
        
        # Compare signal strength percentage (fallback)
        before_signal = [log.get('signal_strength', 0) for log in before_samples if log.get('signal_strength', 0) > 0]
        during_signal = [log.get('signal_strength', 0) for log in during_samples if log.get('signal_strength', 0) > 0]
        
        if before_signal and during_signal and not before_rssi:  # Only use if RSSI not available
            before_avg = sum(before_signal) / len(before_signal)
            during_avg = sum(during_signal) / len(during_signal)
            change = during_avg - before_avg
            change_pct = (change / before_avg) * 100 if before_avg != 0 else 0
            
            is_significant = change < -10  # 10% drop is significant
            direction = "decreased" if change < -5 else ("increased" if change > 5 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="WiFi Signal Strength",
                category="wifi_signal",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"Signal {'dropped' if change < 0 else 'improved'} from {before_avg:.0f}% to {during_avg:.0f}%"
            ))
        
        # Compare quality score
        before_quality = [log.get('quality_score', 0) for log in before_samples if log.get('quality_score', 0) > 0]
        during_quality = [log.get('quality_score', 0) for log in during_samples if log.get('quality_score', 0) > 0]
        
        if before_quality and during_quality:
            before_avg = sum(before_quality) / len(before_quality)
            during_avg = sum(during_quality) / len(during_quality)
            change = during_avg - before_avg
            change_pct = (change / before_avg) * 100 if before_avg != 0 else 0
            
            is_significant = change < -15  # 15% drop is significant
            direction = "decreased" if change < -5 else ("increased" if change > 5 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="WiFi Quality Score",
                category="wifi_quality",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"Quality {'dropped' if change < 0 else 'improved'} from {before_avg:.0f}% to {during_avg:.0f}%"
            ))
    
    def _compare_ping_metrics(self, incident: SlowdownIncident, ping_logs: List[Dict],
                               before_start: datetime, before_end: datetime,
                               during_start: datetime, during_end: datetime) -> None:
        """Compare ping metrics before vs during the slowdown"""
        before_samples = []
        during_samples = []
        
        for log in ping_logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'])
                if before_start <= log_time <= before_end:
                    before_samples.append(log)
                elif during_start <= log_time <= during_end:
                    during_samples.append(log)
            except (ValueError, TypeError):
                continue
        
        if not before_samples or not during_samples:
            return
        
        # Compare latency
        before_latency = [log.get('latency', 0) for log in before_samples if log.get('latency', 0) > 0]
        during_latency = [log.get('latency', 0) for log in during_samples if log.get('latency', 0) > 0]
        
        if before_latency and during_latency:
            before_avg = sum(before_latency) / len(before_latency)
            during_avg = sum(during_latency) / len(during_latency)
            change = during_avg - before_avg
            change_pct = (change / before_avg) * 100 if before_avg != 0 else 0
            
            # Higher latency is worse
            is_significant = change > 20  # 20ms increase is significant
            direction = "increased" if change > 5 else ("decreased" if change < -5 else "stable")
            
            incident.metric_changes.append(MetricChange(
                metric_name="Latency",
                category="latency",
                before_value=round(before_avg, 1),
                during_value=round(during_avg, 1),
                change_amount=round(change, 1),
                change_percent=round(change_pct, 1),
                direction=direction,
                is_significant=is_significant,
                description=f"Latency {'increased' if change > 0 else 'decreased'} from {before_avg:.0f}ms to {during_avg:.0f}ms"
            ))
        
        # Compare packet loss
        before_loss = [log.get('packet_loss', 0) for log in before_samples]
        during_loss = [log.get('packet_loss', 0) for log in during_samples]
        
        if before_loss and during_loss:
            before_avg = sum(before_loss) / len(before_loss)
            during_avg = sum(during_loss) / len(during_loss)
            change = during_avg - before_avg
            
            # Higher packet loss is worse
            is_significant = change > 2  # 2% increase is significant
            direction = "increased" if change > 1 else ("decreased" if change < -1 else "stable")
            
            if is_significant or during_avg > 0:
                incident.metric_changes.append(MetricChange(
                    metric_name="Packet Loss",
                    category="packet_loss",
                    before_value=round(before_avg, 1),
                    during_value=round(during_avg, 1),
                    change_amount=round(change, 1),
                    change_percent=0,  # Packet loss is already a percentage
                    direction=direction,
                    is_significant=is_significant,
                    description=f"Packet loss {'increased' if change > 0 else 'decreased'} from {before_avg:.1f}% to {during_avg:.1f}%"
                ))
    
    def _identify_triggers(self, incident: SlowdownIncident) -> None:
        """Identify likely trigger factors based on significant metric changes"""
        triggers = []
        
        for change in incident.metric_changes:
            if change.is_significant:
                if change.category == 'wifi_signal':
                    triggers.append(f"WiFi signal degradation ({change.description})")
                elif change.category == 'wifi_quality':
                    triggers.append(f"WiFi quality drop ({change.description})")
                elif change.category == 'interference':
                    triggers.append(f"Increased interference ({change.description})")
                elif change.category == 'latency':
                    triggers.append(f"Latency spike ({change.description})")
                elif change.category == 'packet_loss':
                    triggers.append(f"Packet loss increase ({change.description})")
        
        # Also check for WiFi events in factors
        for factor in incident.factors:
            if factor.category == 'wifi_event':
                triggers.append(f"WiFi event: {factor.description}")
        
        incident.trigger_factors = triggers
    
    def _generate_summary(self, incident: SlowdownIncident) -> str:
        """Generate a human-readable summary of the incident (connection-type aware)"""
        duration = (incident.end_time - incident.start_time).total_seconds() / 60
        
        # Connection type label
        conn_label = {
            "wifi": "WiFi",
            "ethernet": "Ethernet (wired)",
            "unknown": "Network"
        }.get(incident.connection_type, "Network")
        
        summary = f"{conn_label} slowdown detected: {incident.avg_download:.1f} Mbps download, "
        summary += f"{incident.avg_upload:.1f} Mbps upload over {duration:.0f} minutes. "
        
        # Include trigger factors if identified
        if incident.trigger_factors:
            summary += f"Likely causes: {'; '.join(incident.trigger_factors[:3])}. "
        elif incident.factors:
            categories = set(f.category for f in incident.factors)
            if 'wifi_signal' in categories:
                summary += "Weak WiFi signal detected. "
            if 'interference' in categories:
                summary += "WiFi interference detected. "
            if 'internet_latency' in categories or 'gateway_latency' in categories:
                summary += "High latency observed. "
            if 'packet_loss' in categories:
                summary += "Packet loss detected. "
            if 'wifi_event' in categories:
                summary += "WiFi connectivity event detected. "
        elif incident.connection_type == "ethernet":
            summary += "No local factors identified on wired connection - likely ISP or router issue. "
        
        return summary.strip()
    
    def _generate_recommendations(self, incident: SlowdownIncident) -> List[str]:
        """Generate recommendations based on incident factors, metric changes, and connection type"""
        recommendations = []
        
        categories = set(f.category for f in incident.factors)
        
        # Also check metric changes for additional context
        significant_changes = [c for c in incident.metric_changes if c.is_significant]
        change_categories = set(c.category for c in significant_changes)
        
        # WiFi-specific recommendations (only for WiFi connections)
        if incident.connection_type == "wifi":
            if 'wifi_signal' in categories or 'wifi_signal' in change_categories:
                recommendations.append("Consider moving closer to the WiFi router or adding a WiFi extender")
                recommendations.append("Check for physical obstructions between device and router")
            
            if 'wifi_quality' in categories or 'wifi_quality' in change_categories:
                recommendations.append("WiFi quality degraded - check for interference from other devices")
            
            if 'interference' in categories:
                recommendations.append("High interference detected - try changing WiFi channel or moving away from other electronics")
            
            if 'wifi_event' in categories:
                recommendations.append("Investigate WiFi stability - frequent disconnections may indicate interference or router issues")
        
        # Recommendations for both WiFi and Ethernet
        if 'internet_latency' in categories or 'latency' in change_categories:
            recommendations.append("Check for network congestion or bandwidth-heavy applications")
            if incident.connection_type == "wifi":
                recommendations.append("Consider using a wired Ethernet connection for critical work")
        
        if 'gateway_latency' in categories:
            recommendations.append("Router may be overloaded - consider restarting or upgrading router")
        
        if 'packet_loss' in categories or 'packet_loss' in change_categories:
            recommendations.append("Packet loss may indicate network hardware issues - check cables and router")
            recommendations.append("Contact ISP if packet loss persists")
        
        # Ethernet-specific recommendations
        if incident.connection_type == "ethernet":
            if not incident.factors:
                recommendations.append("Check Ethernet cable for damage or loose connections")
                recommendations.append("Try a different Ethernet port on your router")
                recommendations.append("Test with a different Ethernet cable")
            recommendations.append("Check router/switch for issues - restart if needed")
        
        if not recommendations:
            recommendations.append("Monitor the situation - slowdown may be temporary ISP issue")
        
        return recommendations
    
    def _determine_status(self, incidents: List[SlowdownIncident], 
                          speed_tests: List[Dict]) -> Dict[str, Any]:
        """Determine overall network status"""
        if not speed_tests:
            return {
                'status': 'unknown',
                'message': 'No speed test data available'
            }
        
        avg_download = sum(t.get('download', 0) for t in speed_tests) / len(speed_tests)
        avg_upload = sum(t.get('upload', 0) for t in speed_tests) / len(speed_tests)
        avg_ping = sum(t.get('ping', 0) for t in speed_tests) / len(speed_tests)
        
        # Check for active issues (recent incidents)
        now = datetime.now()
        active_incidents = [i for i in incidents 
                          if (now - i.end_time).total_seconds() < 1800]  # 30 min
        
        if active_incidents:
            return {
                'status': 'degraded',
                'message': f'Active network issues detected ({len(active_incidents)} ongoing)',
                'avg_download': avg_download,
                'avg_upload': avg_upload,
                'avg_ping': avg_ping
            }
        
        if incidents:
            return {
                'status': 'slowdowns',
                'message': f'{len(incidents)} slowdown incident(s) detected in analysis period',
                'avg_download': avg_download,
                'avg_upload': avg_upload,
                'avg_ping': avg_ping
            }
        
        if avg_download < self.SLOW_DOWNLOAD_THRESHOLD:
            return {
                'status': 'poor',
                'message': f'Average download speed is low ({avg_download:.1f} Mbps)',
                'avg_download': avg_download,
                'avg_upload': avg_upload,
                'avg_ping': avg_ping
            }
        
        return {
            'status': 'healthy',
            'message': 'Network performance is normal',
            'avg_download': avg_download,
            'avg_upload': avg_upload,
            'avg_ping': avg_ping
        }
    
    def _calculate_fleet_health(self, report: Dict[str, Any]) -> int:
        """Calculate fleet health score (0-100)"""
        if report['machines_analyzed'] == 0:
            return 0
        
        # Start with 100 and deduct for issues
        score = 100
        
        # Deduct for machines with issues
        issue_ratio = report['machines_with_issues'] / report['machines_analyzed']
        score -= issue_ratio * 40  # Max 40 point deduction
        
        # Deduct for total incidents
        if report['total_incidents'] > 0:
            incident_penalty = min(report['total_incidents'] * 5, 30)  # Max 30 point deduction
            score -= incident_penalty
        
        return max(0, int(score))
    
    def _incident_to_dict(self, incident: SlowdownIncident) -> Dict[str, Any]:
        """Convert incident to dictionary for JSON serialization"""
        return {
            'machine_id': incident.machine_id,
            'start_time': incident.start_time.isoformat(),
            'end_time': incident.end_time.isoformat(),
            'duration_minutes': (incident.end_time - incident.start_time).total_seconds() / 60,
            'avg_download': incident.avg_download,
            'avg_upload': incident.avg_upload,
            'avg_ping': incident.avg_ping,
            'test_count': len(incident.speed_tests),
            'connection_type': incident.connection_type,  # "wifi", "ethernet", or "unknown"
            'access_point': incident.access_point.to_dict() if incident.access_point else None,
            'factors': [
                {
                    'category': f.category,
                    'description': f.description,
                    'severity': f.severity.value,
                    'timestamp': f.timestamp,
                    'metrics': f.metrics
                }
                for f in incident.factors
            ],
            'metric_changes': [
                {
                    'metric_name': m.metric_name,
                    'category': m.category,
                    'before_value': m.before_value,
                    'during_value': m.during_value,
                    'change_amount': m.change_amount,
                    'change_percent': m.change_percent,
                    'direction': m.direction,
                    'is_significant': m.is_significant,
                    'description': m.description
                }
                for m in incident.metric_changes
            ],
            'trigger_factors': incident.trigger_factors,
            'summary': incident.summary,
            'recommendations': incident.recommendations
        }
