"""
System Pressure Logger
Tracks CPU, memory, and system pressure over time with configurable retention
Persists data to disk to survive restarts
"""
import psutil
import threading
import time
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Data persistence file path
DATA_DIR = Path.home() / "Library" / "Application Support" / "Atlas"
PRESSURE_LOG_FILE = DATA_DIR / "pressure_history.json"

# Thresholds for spike detection
THRESHOLDS = {
    'cpu_warning': 75,
    'cpu_critical': 90,
    'memory_warning': 80,
    'memory_critical': 90,
    'pressure_warning': 40,
    'pressure_critical': 60
}


class PressureLogger:
    """Logs system pressure metrics over time with spike detection"""
    
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
        
        # Sample every 10 seconds
        self.sample_interval = 10
        
        # Store samples with different granularities:
        # - Last 10 min: every 10 sec = 60 samples
        # - Last hour: every 1 min = 60 samples (aggregated from 10-sec samples)
        # - Last 7 days: every 5 min = 2016 samples (aggregated)

        self.samples_10sec = deque(maxlen=60)   # 10 minutes of 10-second samples
        self.samples_1min = deque(maxlen=60)    # 1 hour of 1-minute samples
        self.samples_5min = deque(maxlen=2016)  # 7 days of 5-minute samples (7 * 24 * 12 = 2016)
        
        # Track spikes (events where thresholds were exceeded)
        # Keep enough for 7 days of potential spikes (estimate ~100/day max = 700)
        self.spikes = deque(maxlen=1000)  # Keep last 1000 spike events
        
        # Aggregation buffers
        self._minute_buffer = []
        self._five_min_buffer = []
        self._last_minute_mark = None
        self._last_five_min_mark = None
        
        # Running stats
        self.is_running = False
        self._thread = None
        self._last_save_time = 0
        self._save_interval = 60  # Save to disk every 60 seconds
        
        # Load persisted data on startup
        self._load_from_disk()
        
    def start(self):
        """Start the pressure logging thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self._thread = threading.Thread(target=self._logging_loop, daemon=True)
        self._thread.start()
        logger.info("Pressure logger started")
    
    def stop(self):
        """Stop the pressure logging thread"""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        # Save data before stopping
        self._save_to_disk()
        logger.info("Pressure logger stopped")
    
    def _save_to_disk(self):
        """Save current data to disk for persistence"""
        try:
            # Ensure data directory exists
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            with self._data_lock:
                data = {
                    'saved_at': datetime.now().isoformat(),
                    'samples_10sec': list(self.samples_10sec),
                    'samples_1min': list(self.samples_1min),
                    'samples_5min': list(self.samples_5min),
                    'spikes': list(self.spikes)
                }

            # Write to temp file first, then rename for atomic write
            temp_file = PRESSURE_LOG_FILE.with_suffix('.json.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f)
            temp_file.replace(PRESSURE_LOG_FILE)
            
            logger.debug(f"Saved pressure data to disk: {len(data['samples_5min'])} 5-min samples, {len(data['spikes'])} spikes")
            
        except Exception as e:
            logger.error(f"Failed to save pressure data to disk: {e}")
    
    def _load_from_disk(self):
        """Load persisted data from disk

        Loads the last N samples for each granularity (not filtered by time),
        so historical data survives restarts. Only 7-day samples are time-filtered.
        """
        try:
            if not PRESSURE_LOG_FILE.exists():
                logger.info("No pressure history file found, starting fresh")
                return

            with open(PRESSURE_LOG_FILE, 'r') as f:
                data = json.load(f)

            saved_at = data.get('saved_at', 'unknown')
            now = time.time()

            # 7 days in seconds
            seven_days = 7 * 24 * 60 * 60  # 604800 seconds

            with self._data_lock:
                # Load 10-second samples - keep last 60 samples (the deque maxlen)
                # This preserves the "last 10 minutes of logs" even after restart
                for sample in data.get('samples_10sec', []):
                    self.samples_10sec.append(sample)

                # Load 1-minute samples - keep last 60 samples (the deque maxlen)
                # This preserves the "last 1 hour of logs" even after restart
                for sample in data.get('samples_1min', []):
                    self.samples_1min.append(sample)

                # Load 5-minute samples (only if within last 7 days)
                for sample in data.get('samples_5min', []):
                    if sample.get('epoch', 0) > now - seven_days:
                        self.samples_5min.append(sample)

                # Load spikes (only if within last 7 days)
                for spike in data.get('spikes', []):
                    if spike.get('epoch', 0) > now - seven_days:
                        self.spikes.append(spike)

            logger.info(f"Loaded pressure history from {saved_at}: "
                       f"{len(self.samples_10sec)} 10s, {len(self.samples_1min)} 1m, "
                       f"{len(self.samples_5min)} 5m samples, {len(self.spikes)} spikes")

        except Exception as e:
            logger.error(f"Failed to load pressure data from disk: {e}")
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current CPU, memory, and pressure metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            try:
                load_avg = psutil.getloadavg()
                cpu_count = psutil.cpu_count() or 1
                normalized_load = load_avg[0] / cpu_count
            except (AttributeError, OSError):
                normalized_load = 0
            
            # Calculate pressure score (same logic as system_monitor_widget)
            pressure_score = 0
            if cpu_percent > 90: pressure_score += 40
            elif cpu_percent > 75: pressure_score += 30
            elif cpu_percent > 50: pressure_score += 15
            elif cpu_percent > 25: pressure_score += 5
            
            if memory.percent > 90: pressure_score += 40
            elif memory.percent > 80: pressure_score += 30
            elif memory.percent > 65: pressure_score += 15
            elif memory.percent > 50: pressure_score += 5
            
            if normalized_load > 2.0: pressure_score += 20
            elif normalized_load > 1.5: pressure_score += 15
            elif normalized_load > 1.0: pressure_score += 10
            elif normalized_load > 0.7: pressure_score += 5
            
            return {
                'timestamp': datetime.now().isoformat(),
                'epoch': time.time(),
                'cpu': round(cpu_percent, 1),
                'memory': round(memory.percent, 1),
                'pressure': pressure_score,
                'load': round(normalized_load, 2)
            }
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return None
    
    def _check_spikes(self, metrics: Dict[str, Any]):
        """Check if current metrics exceed thresholds and log spikes"""
        spike_types = []
        
        if metrics['cpu'] >= THRESHOLDS['cpu_critical']:
            spike_types.append(('cpu', 'critical', metrics['cpu']))
        elif metrics['cpu'] >= THRESHOLDS['cpu_warning']:
            spike_types.append(('cpu', 'warning', metrics['cpu']))
        
        if metrics['memory'] >= THRESHOLDS['memory_critical']:
            spike_types.append(('memory', 'critical', metrics['memory']))
        elif metrics['memory'] >= THRESHOLDS['memory_warning']:
            spike_types.append(('memory', 'warning', metrics['memory']))
        
        if metrics['pressure'] >= THRESHOLDS['pressure_critical']:
            spike_types.append(('pressure', 'critical', metrics['pressure']))
        elif metrics['pressure'] >= THRESHOLDS['pressure_warning']:
            spike_types.append(('pressure', 'warning', metrics['pressure']))
        
        for metric_type, severity, value in spike_types:
            spike = {
                'timestamp': metrics['timestamp'],
                'epoch': metrics['epoch'],
                'type': metric_type,
                'severity': severity,
                'value': value,
                'cpu': metrics['cpu'],
                'memory': metrics['memory'],
                'pressure': metrics['pressure']
            }
            with self._data_lock:
                self.spikes.append(spike)
    
    def _aggregate_samples(self, samples: List[Dict]) -> Dict[str, Any]:
        """Aggregate multiple samples into one summary"""
        if not samples:
            return None
        
        cpu_values = [s['cpu'] for s in samples]
        mem_values = [s['memory'] for s in samples]
        pressure_values = [s['pressure'] for s in samples]
        
        return {
            'timestamp': samples[-1]['timestamp'],
            'epoch': samples[-1]['epoch'],
            'cpu': round(sum(cpu_values) / len(cpu_values), 1),
            'cpu_max': max(cpu_values),
            'cpu_min': min(cpu_values),
            'memory': round(sum(mem_values) / len(mem_values), 1),
            'memory_max': max(mem_values),
            'memory_min': min(mem_values),
            'pressure': round(sum(pressure_values) / len(pressure_values), 1),
            'pressure_max': max(pressure_values),
            'pressure_min': min(pressure_values),
            'samples': len(samples)
        }
    
    def _logging_loop(self):
        """Main logging loop"""
        while self.is_running:
            try:
                metrics = self._get_current_metrics()
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
                            # Aggregate minute data
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
                            # Aggregate 5-minute data
                            if self._five_min_buffer:
                                aggregated = self._aggregate_samples(self._five_min_buffer)
                                if aggregated:
                                    self.samples_5min.append(aggregated)
                            self._five_min_buffer = []
                            self._last_five_min_mark = current_five_min
                    
                    # Check for spikes
                    self._check_spikes(metrics)
                    
                    # Periodic save to disk
                    current_time = time.time()
                    if current_time - self._last_save_time >= self._save_interval:
                        self._save_to_disk()
                        self._last_save_time = current_time
                
                time.sleep(self.sample_interval)
                
            except Exception as e:
                logger.error(f"Error in pressure logging loop: {e}")
                time.sleep(self.sample_interval)
    
    def get_history(self, period: str = '10m') -> Dict[str, Any]:
        """
        Get historical pressure data for a given period

        Args:
            period: '10m', '1h', '24h', or '7d'

        Returns:
            Dict with samples, stats, spike info, and time_span indicating
            the actual time range of the returned samples.

        Note: For 10m and 1h, returns the last N logged samples (preserving
        history across restarts). For 24h and 7d, filters by actual time.
        """
        now = time.time()

        with self._data_lock:
            if period == '10m':
                # Return last 60 logged samples (10 min worth of samples)
                samples = list(self.samples_10sec)
            elif period == '1h':
                # Return last 60 logged samples (1 hour worth of samples)
                samples = list(self.samples_1min)
            elif period == '24h':
                # Filter 5-min samples to last 24 hours of actual time
                cutoff = now - 86400
                samples = [s for s in self.samples_5min if s.get('epoch', 0) >= cutoff]
            elif period == '7d':
                samples = list(self.samples_5min)
            else:
                samples = list(self.samples_10sec)

            # Get spikes that fall within the sample time range
            if samples:
                oldest_sample_epoch = samples[0].get('epoch', 0)
                recent_spikes = [s for s in self.spikes if s['epoch'] >= oldest_sample_epoch]
            else:
                recent_spikes = []

        if not samples:
            return {
                'period': period,
                'time_span': None,
                'samples': [],
                'stats': None,
                'spikes': recent_spikes
            }

        # Calculate the actual time span of the samples
        oldest_epoch = samples[0].get('epoch', 0)
        newest_epoch = samples[-1].get('epoch', 0)
        oldest_timestamp = samples[0].get('timestamp', '')
        newest_timestamp = samples[-1].get('timestamp', '')

        # Detect gaps in data (indicates restart or missed samples)
        # Expected interval: 10s for 10sec samples, 60s for 1min samples, 300s for 5min samples
        expected_intervals = {'10m': 10, '1h': 60, '24h': 300, '7d': 300}
        expected_interval = expected_intervals.get(period, 10)
        gap_threshold = expected_interval * 3  # Consider it a gap if > 3x expected interval

        gaps = []
        for i in range(1, len(samples)):
            prev_epoch = samples[i-1].get('epoch', 0)
            curr_epoch = samples[i].get('epoch', 0)
            gap = curr_epoch - prev_epoch
            if gap > gap_threshold:
                gaps.append({
                    'start': samples[i-1].get('timestamp', ''),
                    'end': samples[i].get('timestamp', ''),
                    'duration_seconds': gap,
                    'duration_human': self._format_duration(gap)
                })

        time_span = {
            'start_epoch': oldest_epoch,
            'end_epoch': newest_epoch,
            'start_time': oldest_timestamp,
            'end_time': newest_timestamp,
            'duration_seconds': newest_epoch - oldest_epoch,
            'duration_human': self._format_duration(newest_epoch - oldest_epoch),
            'sample_count': len(samples),
            'has_gaps': len(gaps) > 0,
            'gap_count': len(gaps),
            'gaps': gaps[:5]  # Limit to first 5 gaps to keep response size reasonable
        }

        # Calculate period stats
        cpu_values = [s['cpu'] for s in samples]
        mem_values = [s['memory'] for s in samples]
        pressure_values = [s['pressure'] for s in samples]

        stats = {
            'cpu_avg': round(sum(cpu_values) / len(cpu_values), 1),
            'cpu_max': max(cpu_values),
            'cpu_min': min(cpu_values),
            'memory_avg': round(sum(mem_values) / len(mem_values), 1),
            'memory_max': max(mem_values),
            'memory_min': min(mem_values),
            'pressure_avg': round(sum(pressure_values) / len(pressure_values), 1),
            'pressure_max': max(pressure_values),
            'pressure_min': min(pressure_values),
            'sample_count': len(samples),
            'spike_count': len(recent_spikes)
        }

        return {
            'period': period,
            'time_span': time_span,
            'samples': samples,
            'stats': stats,
            'spikes': recent_spikes
        }

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s" if secs > 0 else f"{mins}m"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
        else:
            days = int(seconds / 86400)
            hours = int((seconds % 86400) / 3600)
            return f"{days}d {hours}h" if hours > 0 else f"{days}d"
    
    def get_current(self) -> Dict[str, Any]:
        """Get current metrics with recent spike status"""
        metrics = self._get_current_metrics()
        
        with self._data_lock:
            # Get spikes from last 5 minutes
            cutoff = time.time() - 300
            recent_spikes = [s for s in self.spikes if s['epoch'] >= cutoff]
        
        return {
            'current': metrics,
            'recent_spikes': recent_spikes,
            'thresholds': THRESHOLDS
        }


# Singleton instance
_pressure_logger = None

def get_pressure_logger() -> PressureLogger:
    """Get or create the singleton pressure logger"""
    global _pressure_logger
    if _pressure_logger is None:
        _pressure_logger = PressureLogger()
        _pressure_logger.start()
    return _pressure_logger
