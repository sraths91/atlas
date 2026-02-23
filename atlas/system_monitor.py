"""
System monitoring utilities for macOS
"""
import subprocess
import shlex
import re
import psutil
import platform
from typing import Dict, Tuple, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class SystemMonitor:
    """System monitoring for macOS"""
    
    def __init__(self):
        self._prev_net_stats = self._get_net_stats()
        self._prev_time = 0
        self._cpu_count = psutil.cpu_count()
        self._gpu_history = []  # Store recent GPU readings for smoothing
        self._gpu_history_size = 5  # Average over last 5 readings
        self._gpu_cache = None
        self._gpu_cache_time = 0
        self._gpu_cache_ttl = 10  # Cache ioreg GPU result for 10 seconds
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage as a percentage"""
        return psutil.cpu_percent(interval=0.5) / 100.0
    
    def get_memory_usage(self) -> float:
        """Get current memory usage as a percentage"""
        return psutil.virtual_memory().percent / 100.0
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage for all mounted partitions"""
        usage = {}
        for part in psutil.disk_partitions():
            try:
                usage[part.mountpoint] = psutil.disk_usage(part.mountpoint).percent / 100.0
            except Exception as e:
                logger.warning(f"Could not get disk usage for {part.mountpoint}: {e}")
        return usage
    
    def get_network_usage(self) -> Tuple[float, float]:
        """Get network usage in bytes/s (up, down)"""
        current_stats = self._get_net_stats()
        current_time = psutil.cpu_times().user + psutil.cpu_times().system
        
        if self._prev_time == 0:
            self._prev_time = current_time
            self._prev_net_stats = current_stats
            return 0.0, 0.0
        
        time_diff = current_time - self._prev_time
        
        if time_diff == 0:
            return 0.0, 0.0
        
        up = max(0, (current_stats['bytes_sent'] - self._prev_net_stats['bytes_sent']) / time_diff)
        down = max(0, (current_stats['bytes_recv'] - self._prev_net_stats['bytes_recv']) / time_diff)
        
        self._prev_net_stats = current_stats
        self._prev_time = current_time
        
        return up, down
    
    def get_gpu_usage(self) -> Optional[float]:
        """Get GPU usage as a percentage (0-100) for Apple Silicon with smoothing"""
        import time as _time
        current_reading = 0.0

        try:
            # Cache ioreg result to avoid hammering IOKit registry
            now = _time.time()
            if self._gpu_cache and (now - self._gpu_cache_time) < self._gpu_cache_ttl:
                result = self._gpu_cache
            else:
                result = subprocess.run(
                    ['ioreg', '-r', '-d', '1', '-w', '0', '-c', 'IOAccelerator'],
                    capture_output=True, text=True, timeout=2
                )
                self._gpu_cache = result
                self._gpu_cache_time = now
            
            if result.returncode == 0 and result.stdout:
                # Look for "Device Utilization %" in PerformanceStatistics
                # Format: "Device Utilization %"=10
                match = re.search(r'"Device Utilization %"=(\d+)', result.stdout)
                if match:
                    utilization = float(match.group(1))
                    current_reading = utilization / 100.0
                else:
                    # Also try Renderer Utilization as fallback
                    match = re.search(r'"Renderer Utilization %"=(\d+)', result.stdout)
                    if match:
                        utilization = float(match.group(1))
                        current_reading = utilization / 100.0
                
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Could not get GPU info: {e}")
        
        # Add to history for smoothing
        self._gpu_history.append(current_reading)
        
        # Keep only recent readings
        if len(self._gpu_history) > self._gpu_history_size:
            self._gpu_history.pop(0)
        
        # Return smoothed average
        if self._gpu_history:
            return sum(self._gpu_history) / len(self._gpu_history)
        
        return 0.0
    
    def get_battery(self) -> Optional[Dict[str, Any]]:
        """Get battery information"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                return {
                    'percent': battery.percent,
                    'power_plugged': battery.power_plugged,
                    'seconds_left': battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
        except Exception as e:
            logger.debug(f"Could not get battery info: {e}")
        return None
    
    def get_temperatures(self) -> Dict[str, float]:
        """Get system temperatures in Celsius"""
        temps = {}
        
        try:
            # Try to use osx-cpu-temp if available
            result = subprocess.run(
                ['osx-cpu-temp'],
                capture_output=True, text=True, check=True, timeout=10
            )
            # Parse output like "30.0°C"
            match = re.search(r'([\d.]+)', result.stdout)
            if match:
                temps['cpu'] = float(match.group(1))
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fall back to system profiler (parse in Python instead of piping through grep)
            try:
                result = subprocess.run(
                    ['system_profiler', 'SPPowerDataType'],
                    capture_output=True, text=True, check=True, timeout=10
                )
                # Search for temperature line in Python instead of using shell pipe
                for line in result.stdout.splitlines():
                    if 'temperature' in line.lower():
                        match = re.search(r'([\d.]+)', line)
                        if match:
                            temps['cpu'] = float(match.group(1))
                            break
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.warning(f"Could not get temperature info: {e}")
        
        return temps
    
    def _get_net_stats(self) -> Dict[str, int]:
        """Get network statistics"""
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get all system statistics"""
        up, down = self.get_network_usage()
        
        return {
            'cpu': self.get_cpu_usage(),
            'memory': self.get_memory_usage(),
            'disks': self.get_disk_usage(),
            'network': {
                'up': up,
                'down': down
            },
            'gpu': self.get_gpu_usage(),
            'battery': self.get_battery(),
            'temperatures': self.get_temperatures()
        }
