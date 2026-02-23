"""
Network Speed Correlation Analyzer

Correlates WiFi signal strength with speed test results to identify
signal thresholds that impact network performance.
"""
import json
import csv
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Data file paths
DATA_DIR = Path.home() / "Library" / "Application Support" / "Atlas"
WIFI_HISTORY_FILE = DATA_DIR / "wifi_signal_history.json"
SPEEDTEST_LOG_FILE = Path.home() / "speedtest_history.csv"


class SpeedCorrelationAnalyzer:
    """Analyzes correlation between WiFi signal strength and speed test results"""

    def __init__(self):
        self.wifi_samples = []
        self.speedtest_results = []
        self._load_data()

    def _load_data(self):
        """Load WiFi history and speed test data"""
        # Load WiFi samples
        try:
            if WIFI_HISTORY_FILE.exists():
                with open(WIFI_HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    # Combine all sample types for broader coverage
                    self.wifi_samples = []
                    for key in ['samples_10sec', 'samples_1min', 'samples_5min', 'samples_15min']:
                        if key in data:
                            self.wifi_samples.extend(data[key])
                    # Sort by epoch
                    self.wifi_samples.sort(key=lambda x: x.get('epoch', 0))
                    logger.info(f"Loaded {len(self.wifi_samples)} WiFi samples")
        except Exception as e:
            logger.error(f"Error loading WiFi history: {e}")
            self.wifi_samples = []

        # Load speed test results
        try:
            if SPEEDTEST_LOG_FILE.exists():
                with open(SPEEDTEST_LOG_FILE, 'r') as f:
                    reader = csv.DictReader(f)
                    self.speedtest_results = []
                    for row in reader:
                        try:
                            # Parse timestamp
                            ts = row.get('timestamp', '')
                            if ts:
                                dt = datetime.fromisoformat(ts)
                                epoch = dt.timestamp()
                                self.speedtest_results.append({
                                    'timestamp': ts,
                                    'epoch': epoch,
                                    'download': float(row.get('download', 0)),
                                    'upload': float(row.get('upload', 0)),
                                    'ping': float(row.get('ping', 0)),
                                    'jitter': float(row.get('jitter', 0)) if row.get('jitter') else 0,
                                    'server': row.get('server', '')
                                })
                        except (ValueError, TypeError) as e:
                            continue
                    logger.info(f"Loaded {len(self.speedtest_results)} speed test results")
        except Exception as e:
            logger.error(f"Error loading speed test history: {e}")
            self.speedtest_results = []

    def refresh_data(self):
        """Reload data from files"""
        self._load_data()

    def _find_closest_wifi_sample(self, epoch: float, max_delta: float = 60) -> Optional[Dict[str, Any]]:
        """Find the WiFi sample closest to the given epoch time"""
        if not self.wifi_samples:
            return None

        closest = None
        min_delta = float('inf')

        for sample in self.wifi_samples:
            sample_epoch = sample.get('epoch', 0)
            delta = abs(sample_epoch - epoch)
            if delta < min_delta and delta <= max_delta:
                min_delta = delta
                closest = sample

        return closest

    def get_correlated_data(self, hours: int = 168) -> List[Dict[str, Any]]:
        """
        Get speed test results correlated with WiFi signal data.
        Returns list of combined records.
        """
        self.refresh_data()

        cutoff = datetime.now().timestamp() - (hours * 3600)
        correlated = []

        for test in self.speedtest_results:
            if test['epoch'] < cutoff:
                continue

            wifi = self._find_closest_wifi_sample(test['epoch'])

            record = {
                'timestamp': test['timestamp'],
                'epoch': test['epoch'],
                'download': test['download'],
                'upload': test['upload'],
                'ping': test['ping'],
                'jitter': test['jitter'],
                'server': test['server'],
                # WiFi data (if available)
                'rssi': wifi.get('rssi') if wifi else None,
                'snr': wifi.get('snr') if wifi else None,
                'noise': wifi.get('noise') if wifi else None,
                'channel': wifi.get('channel') if wifi else None,
                'band': wifi.get('band') if wifi else None,
                'channel_width': wifi.get('channel_width') if wifi else None,
                'tx_rate': wifi.get('tx_rate') if wifi else None,
                'quality_score': wifi.get('quality_score') if wifi else None,
                'quality_rating': wifi.get('quality_rating') if wifi else None,
                'has_wifi_data': wifi is not None
            }
            correlated.append(record)

        return correlated

    def get_correlation_analysis(self, hours: int = 168) -> Dict[str, Any]:
        """
        Analyze correlation between signal strength and speed.
        Returns statistics and insights.
        """
        data = self.get_correlated_data(hours)

        if not data:
            return {
                'status': 'no_data',
                'message': 'No correlated data available',
                'sample_count': 0
            }

        # Filter to records with WiFi data
        with_wifi = [d for d in data if d['has_wifi_data']]

        if len(with_wifi) < 3:
            return {
                'status': 'insufficient_data',
                'message': 'Need at least 3 correlated samples for analysis',
                'sample_count': len(with_wifi)
            }

        # Group by RSSI ranges
        rssi_ranges = {
            'excellent': {'min': -50, 'max': 0, 'downloads': [], 'uploads': [], 'pings': []},
            'good': {'min': -60, 'max': -50, 'downloads': [], 'uploads': [], 'pings': []},
            'fair': {'min': -70, 'max': -60, 'downloads': [], 'uploads': [], 'pings': []},
            'poor': {'min': -80, 'max': -70, 'downloads': [], 'uploads': [], 'pings': []},
            'unusable': {'min': -100, 'max': -80, 'downloads': [], 'uploads': [], 'pings': []}
        }

        # Group by SNR ranges
        snr_ranges = {
            'excellent': {'min': 40, 'max': 100, 'downloads': [], 'uploads': [], 'pings': []},
            'good': {'min': 25, 'max': 40, 'downloads': [], 'uploads': [], 'pings': []},
            'fair': {'min': 15, 'max': 25, 'downloads': [], 'uploads': [], 'pings': []},
            'poor': {'min': 0, 'max': 15, 'downloads': [], 'uploads': [], 'pings': []}
        }

        # Collect data points for scatter plot
        scatter_data = []

        for record in with_wifi:
            rssi = record['rssi']
            snr = record['snr']
            download = record['download']
            upload = record['upload']
            ping = record['ping']

            scatter_data.append({
                'rssi': rssi,
                'snr': snr,
                'download': download,
                'upload': upload,
                'ping': ping,
                'timestamp': record['timestamp']
            })

            # Categorize by RSSI
            for name, range_info in rssi_ranges.items():
                if range_info['min'] <= rssi < range_info['max']:
                    range_info['downloads'].append(download)
                    range_info['uploads'].append(upload)
                    range_info['pings'].append(ping)
                    break

            # Categorize by SNR
            for name, range_info in snr_ranges.items():
                if range_info['min'] <= snr < range_info['max']:
                    range_info['downloads'].append(download)
                    range_info['uploads'].append(upload)
                    range_info['pings'].append(ping)
                    break

        # Calculate statistics for each range
        rssi_stats = {}
        for name, range_info in rssi_ranges.items():
            if range_info['downloads']:
                rssi_stats[name] = {
                    'sample_count': len(range_info['downloads']),
                    'avg_download': round(statistics.mean(range_info['downloads']), 2),
                    'avg_upload': round(statistics.mean(range_info['uploads']), 2),
                    'avg_ping': round(statistics.mean(range_info['pings']), 2),
                    'min_download': round(min(range_info['downloads']), 2),
                    'max_download': round(max(range_info['downloads']), 2),
                    'rssi_range': f"{range_info['min']} to {range_info['max']} dBm"
                }
            else:
                rssi_stats[name] = {
                    'sample_count': 0,
                    'rssi_range': f"{range_info['min']} to {range_info['max']} dBm"
                }

        snr_stats = {}
        for name, range_info in snr_ranges.items():
            if range_info['downloads']:
                snr_stats[name] = {
                    'sample_count': len(range_info['downloads']),
                    'avg_download': round(statistics.mean(range_info['downloads']), 2),
                    'avg_upload': round(statistics.mean(range_info['uploads']), 2),
                    'avg_ping': round(statistics.mean(range_info['pings']), 2),
                    'snr_range': f"{range_info['min']} to {range_info['max']} dB"
                }
            else:
                snr_stats[name] = {
                    'sample_count': 0,
                    'snr_range': f"{range_info['min']} to {range_info['max']} dB"
                }

        # Calculate simple correlation coefficient
        rssi_values = [d['rssi'] for d in scatter_data]
        download_values = [d['download'] for d in scatter_data]

        correlation = self._calculate_correlation(rssi_values, download_values)

        # Generate insights
        insights = self._generate_insights(rssi_stats, snr_stats, correlation, scatter_data)

        return {
            'status': 'success',
            'sample_count': len(with_wifi),
            'total_tests': len(data),
            'hours_analyzed': hours,
            'rssi_stats': rssi_stats,
            'snr_stats': snr_stats,
            'scatter_data': scatter_data,
            'correlation': {
                'rssi_vs_download': round(correlation, 3) if correlation else None,
                'interpretation': self._interpret_correlation(correlation)
            },
            'insights': insights
        }

    def _calculate_correlation(self, x: List[float], y: List[float]) -> Optional[float]:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) < 3:
            return None

        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        try:
            std_x = statistics.stdev(x)
            std_y = statistics.stdev(y)

            if std_x == 0 or std_y == 0:
                return None

            covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
            correlation = covariance / (std_x * std_y)
            return correlation
        except (ZeroDivisionError, statistics.StatisticsError, ValueError):
            return None

    def _interpret_correlation(self, r: Optional[float]) -> str:
        """Interpret correlation coefficient"""
        if r is None:
            return "Unable to calculate"

        abs_r = abs(r)
        direction = "positive" if r > 0 else "negative"

        if abs_r >= 0.7:
            strength = "strong"
        elif abs_r >= 0.4:
            strength = "moderate"
        elif abs_r >= 0.2:
            strength = "weak"
        else:
            return "No significant correlation"

        # For RSSI (negative values), positive correlation means
        # higher RSSI (less negative) = higher speed
        if r > 0:
            return f"{strength.capitalize()} {direction} correlation: Better signal = faster speeds"
        else:
            return f"{strength.capitalize()} {direction} correlation: Unexpected pattern"

    def _generate_insights(self, rssi_stats: Dict, snr_stats: Dict,
                          correlation: Optional[float], scatter_data: List) -> List[str]:
        """Generate actionable insights from the analysis"""
        insights = []

        # Check for significant speed differences by signal quality
        if rssi_stats.get('excellent', {}).get('sample_count', 0) > 0:
            if rssi_stats.get('fair', {}).get('sample_count', 0) > 0:
                excellent_speed = rssi_stats['excellent'].get('avg_download', 0)
                fair_speed = rssi_stats['fair'].get('avg_download', 0)
                if excellent_speed > 0 and fair_speed > 0:
                    diff_pct = ((excellent_speed - fair_speed) / fair_speed) * 100
                    if diff_pct > 20:
                        insights.append(
                            f"Excellent signal delivers {diff_pct:.0f}% faster downloads "
                            f"({excellent_speed:.0f} vs {fair_speed:.0f} Mbps)"
                        )

        # Check for ping issues at low signal
        if rssi_stats.get('poor', {}).get('sample_count', 0) > 0:
            poor_ping = rssi_stats['poor'].get('avg_ping', 0)
            if poor_ping > 50:
                insights.append(
                    f"Poor signal increases latency significantly (avg {poor_ping:.0f}ms ping)"
                )

        # SNR-based insight
        if snr_stats.get('poor', {}).get('sample_count', 0) > 0:
            snr_poor = snr_stats['poor']
            if snr_poor.get('avg_download', 0) > 0:
                insights.append(
                    f"Low SNR (<15 dB) limits speeds to avg {snr_poor['avg_download']:.0f} Mbps"
                )

        # Correlation insight
        if correlation and correlation > 0.4:
            insights.append(
                "Strong link between signal strength and speed - improving WiFi signal "
                "will likely improve speeds"
            )

        # If most tests are at fair/poor signal
        total_with_data = sum(s.get('sample_count', 0) for s in rssi_stats.values())
        poor_fair_count = (rssi_stats.get('poor', {}).get('sample_count', 0) +
                         rssi_stats.get('fair', {}).get('sample_count', 0))

        if total_with_data > 0 and poor_fair_count / total_with_data > 0.5:
            insights.append(
                "Most tests run at fair/poor signal - consider moving closer to router "
                "or adding a WiFi extender"
            )

        if not insights:
            insights.append("Signal quality appears stable - no significant impact on speeds detected")

        return insights

    def get_summary(self) -> Dict[str, Any]:
        """Get a quick summary of available data"""
        self.refresh_data()

        return {
            'wifi_samples': len(self.wifi_samples),
            'speedtest_results': len(self.speedtest_results),
            'wifi_time_range': {
                'start': self.wifi_samples[0].get('timestamp') if self.wifi_samples else None,
                'end': self.wifi_samples[-1].get('timestamp') if self.wifi_samples else None
            },
            'speedtest_time_range': {
                'start': self.speedtest_results[0].get('timestamp') if self.speedtest_results else None,
                'end': self.speedtest_results[-1].get('timestamp') if self.speedtest_results else None
            }
        }


# Singleton instance
_analyzer = None

def get_speed_correlation_analyzer() -> SpeedCorrelationAnalyzer:
    """Get or create the speed correlation analyzer singleton"""
    global _analyzer
    if _analyzer is None:
        _analyzer = SpeedCorrelationAnalyzer()
    return _analyzer
