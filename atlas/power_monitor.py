#!/usr/bin/env python3
"""
Enhanced Power Monitor for ATLAS Agent

Tracks advanced power metrics including:
- Battery health and cycle count
- Battery chemistry and design capacity
- Thermal throttling detection
- Power management events (sleep/wake)
- Charging patterns and power source

Business Value:
- Proactive battery replacement (prevent unexpected shutdowns)
- Thermal management (identify overheating issues)
- Power optimization (identify battery drain issues)
- Asset lifecycle planning (track battery degradation)

Author: ATLAS Agent Development Team
Date: January 2026
"""

import subprocess
import plistlib
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import os
import re
import shutil
import logging
import json

from atlas.core.logging import CSVLogger

logger = logging.getLogger(__name__)


def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon (arm64)."""
    import platform
    return platform.machine() == 'arm64'


def ensure_temp_monitoring_installed() -> str:
    """
    Check if CPU temperature monitoring tools are installed and install if needed.

    For Apple Silicon: Uses macmon (sudoless, designed for M-series chips)
    For Intel Macs: Uses osx-cpu-temp (reads SMC sensors)

    Returns:
        str: The tool that's available ('macmon', 'osx-cpu-temp', or None)
    """
    # Check which architecture we're on
    on_apple_silicon = is_apple_silicon()

    if on_apple_silicon:
        # Apple Silicon - use macmon
        if shutil.which('macmon'):
            logger.info("macmon is already installed (Apple Silicon)")
            return 'macmon'

        # Check if Homebrew is available
        brew_path = shutil.which('brew')
        if not brew_path:
            logger.warning("Homebrew not found - cannot auto-install macmon")
            logger.info("To enable CPU temperature monitoring on Apple Silicon, install Homebrew and run: brew install macmon")
            return None

        logger.info("macmon not found, attempting to install via Homebrew (Apple Silicon)...")

        try:
            result = subprocess.run(
                [brew_path, 'install', 'macmon'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info("Successfully installed macmon via Homebrew")
                return 'macmon'
            else:
                logger.warning(f"Failed to install macmon: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning("Homebrew installation timed out")
            return None
        except Exception as e:
            logger.warning(f"Error installing macmon: {e}")
            return None
    else:
        # Intel Mac - use osx-cpu-temp
        if shutil.which('osx-cpu-temp'):
            logger.info("osx-cpu-temp is already installed (Intel)")
            return 'osx-cpu-temp'

        brew_path = shutil.which('brew')
        if not brew_path:
            logger.warning("Homebrew not found - cannot auto-install osx-cpu-temp")
            logger.info("To enable CPU temperature monitoring, install Homebrew and run: brew install osx-cpu-temp")
            return None

        logger.info("osx-cpu-temp not found, attempting to install via Homebrew (Intel)...")

        try:
            result = subprocess.run(
                [brew_path, 'install', 'osx-cpu-temp'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info("Successfully installed osx-cpu-temp via Homebrew")
                return 'osx-cpu-temp'
            else:
                logger.warning(f"Failed to install osx-cpu-temp: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning("Homebrew installation timed out")
            return None
        except Exception as e:
            logger.warning(f"Error installing osx-cpu-temp: {e}")
            return None


# Keep legacy function for backwards compatibility
def ensure_osx_cpu_temp_installed() -> bool:
    """Legacy function - now calls ensure_temp_monitoring_installed()."""
    return ensure_temp_monitoring_installed() is not None


class PowerMonitor:
    """
    Monitor for advanced power and thermal metrics.

    Features:
    - Battery health percentage and cycle count
    - Battery design vs. current capacity
    - Thermal throttling detection (CPU frequency monitoring)
    - Sleep/wake event tracking
    - Charging patterns and power source changes
    - Temperature monitoring

    CSV Output Files:
    - battery_health.csv: Battery health metrics
    - power_events.csv: Sleep/wake and power source events
    - thermal_metrics.csv: CPU temperature and throttling data
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, data_dir: str = None):
        """
        Initialize the Power Monitor.

        Args:
            data_dir: Directory for CSV log files (default: ~/.atlas_agent/data)
        """
        if data_dir is None:
            data_dir = os.path.expanduser('~/.atlas_agent/data')

        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

        # CSV loggers for power metrics
        self.battery_logger = CSVLogger(
            log_file=os.path.join(self.data_dir, 'battery_health.csv'),
            fieldnames=[
                'timestamp', 'health_percentage', 'cycle_count', 'design_capacity',
                'current_capacity', 'max_capacity', 'is_charging', 'time_remaining',
                'amperage', 'voltage', 'temperature', 'battery_installed'
            ]
        )

        self.power_events_logger = CSVLogger(
            log_file=os.path.join(self.data_dir, 'power_events.csv'),
            fieldnames=[
                'timestamp', 'event_type', 'power_source', 'battery_level',
                'details'
            ]
        )

        self.thermal_logger = CSVLogger(
            log_file=os.path.join(self.data_dir, 'thermal_metrics.csv'),
            fieldnames=[
                'timestamp', 'cpu_temperature', 'cpu_temp_source', 'cpu_frequency',
                'cpu_max_frequency', 'is_throttled', 'thermal_pressure', 'fan_speed'
            ]
        )

        # Track previous state for event detection
        self.last_power_source = None
        self.last_battery_level = None
        self.last_sleep_wake_time = None

        # Statistics
        self.total_power_events = 0
        self.total_throttle_events = 0

        # Cache for system_profiler SPPowerDataType (battery health changes very slowly)
        self._sp_power_cache = None
        self._sp_power_cache_time = 0
        self._sp_power_cache_ttl = 600  # Cache for 10 minutes

        # Background monitoring thread
        self.monitor_thread = None
        self.running = False
        self.collection_interval = 120  # Check every 2 minutes (reduced from 60s to limit IOKit/SMC stress)

    def start(self):
        """Start background power monitoring."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """Stop background power monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                self._collect_battery_metrics()
                self._collect_thermal_metrics()
                self._check_power_events()
            except Exception as e:
                logger.error(f"Error in power monitor loop: {e}")

            # Sleep in small intervals to allow graceful shutdown
            for _ in range(self.collection_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _collect_battery_metrics(self):
        """Collect battery health and status metrics using pmset and system_profiler."""
        try:
            timestamp = datetime.now().isoformat()

            # Method 1: pmset -g batt (fast, real-time status)
            result = subprocess.run(
                ['pmset', '-g', 'batt'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return

            # Parse pmset output
            # Example: "InternalBattery-0 (id=12345678)	96%; discharging; 5:32 remaining present: true"
            # Note: "discharging" contains "charging", so check for specific states
            output_lower = result.stdout.lower()
            is_charging = 'charging;' in output_lower and 'discharging' not in output_lower
            is_on_ac = 'ac power' in output_lower
            battery_level = 0
            time_remaining = 'N/A'

            for line in result.stdout.split('\n'):
                # Extract battery percentage
                match = re.search(r'(\d+)%', line)
                if match:
                    battery_level = int(match.group(1))

                # Extract time remaining
                match = re.search(r'(\d+:\d+) remaining', line)
                if match:
                    time_remaining = match.group(1)

            # Method 2: system_profiler SPPowerDataType (detailed battery info)
            # Cached to avoid frequent IOKit walks — battery health changes very slowly
            import json
            import time as _time
            now = _time.time()
            if self._sp_power_cache and (now - self._sp_power_cache_time) < self._sp_power_cache_ttl:
                data = self._sp_power_cache
            else:
                result = subprocess.run(
                    ['system_profiler', 'SPPowerDataType', '-json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    # Fallback to basic data if system_profiler fails
                    self.battery_logger.append({
                        'timestamp': timestamp,
                        'health_percentage': 0,
                        'cycle_count': 0,
                        'design_capacity': 0,
                        'current_capacity': 0,
                        'max_capacity': 0,
                        'is_charging': is_charging,
                        'time_remaining': time_remaining,
                        'amperage': 0,
                        'voltage': 0,
                        'temperature': 0,
                        'battery_installed': True
                    })
                    return

                data = json.loads(result.stdout)
                self._sp_power_cache = data
                self._sp_power_cache_time = now

            # Parse battery data
            power_data = data.get('SPPowerDataType', [])
            if not power_data:
                return

            battery_info = {}
            battery_health_info = {}
            battery_charge_info = {}
            for item in power_data:
                # Look for battery information in different possible structures
                # New macOS structure (Tahoe/Sequoia+)
                if 'sppower_battery_health_info' in item:
                    battery_health_info = item.get('sppower_battery_health_info', {})
                if 'sppower_battery_charge_info' in item:
                    battery_charge_info = item.get('sppower_battery_charge_info', {})
                if 'sppower_battery_model_info' in item:
                    battery_info = item.get('sppower_battery_model_info', {})
                elif '_items' in item:
                    # Check nested items for battery info (legacy structure)
                    for nested in item['_items']:
                        if 'sppower_battery_cycle_count' in nested:
                            battery_info = nested
                            break

            # Extract battery metrics - prefer new structure, fall back to legacy
            cycle_count = battery_health_info.get('sppower_battery_cycle_count',
                          battery_info.get('sppower_battery_cycle_count', 0))
            health_str = battery_health_info.get('sppower_battery_health',
                         battery_info.get('sppower_battery_health', 'Unknown'))
            max_capacity_str = battery_health_info.get('sppower_battery_health_maximum_capacity', '')

            # Parse max capacity percentage (e.g., "91%")
            max_capacity_pct = 0
            if max_capacity_str and '%' in max_capacity_str:
                try:
                    max_capacity_pct = int(max_capacity_str.replace('%', ''))
                except ValueError:
                    pass

            design_capacity = battery_info.get('sppower_battery_design_capacity', 0)
            max_capacity = battery_info.get('sppower_battery_max_capacity', 0)
            current_capacity = battery_info.get('sppower_battery_current_capacity', battery_level)
            amperage = battery_info.get('sppower_battery_amperage', 0)
            voltage = battery_info.get('sppower_battery_voltage', 0)
            temperature = battery_info.get('sppower_battery_temperature', 0)
            battery_installed = battery_info.get('sppower_battery_installed', 'Yes') == 'Yes'

            # Determine health percentage
            # Priority: max_capacity_pct from health_info, then calculate from capacities
            if max_capacity_pct > 0:
                health_percentage = max_capacity_pct
            elif isinstance(health_str, str) and health_str not in ['Unknown', 'Good', 'Fair', 'Poor']:
                # Try to parse as number
                try:
                    health_percentage = int(health_str)
                except ValueError:
                    health_percentage = 0
            elif max_capacity and design_capacity and design_capacity > 0:
                health_percentage = int((max_capacity / design_capacity) * 100)
            else:
                # Map text health to approximate percentage
                health_map = {'Good': 85, 'Fair': 70, 'Poor': 40}
                health_percentage = health_map.get(health_str, 0)

            # Log battery metrics
            self.battery_logger.append({
                'timestamp': timestamp,
                'health_percentage': health_percentage,
                'cycle_count': cycle_count,
                'design_capacity': design_capacity,
                'current_capacity': current_capacity,
                'max_capacity': max_capacity,
                'is_charging': is_charging,
                'time_remaining': time_remaining,
                'amperage': amperage,
                'voltage': voltage,
                'temperature': temperature,
                'battery_installed': battery_installed
            })

        except subprocess.TimeoutExpired:
            logger.warning("Battery profiler timed out")
        except Exception as e:
            logger.error(f"Error collecting battery metrics: {e}")

    def _collect_thermal_metrics(self):
        """Collect thermal and CPU frequency metrics."""
        try:
            timestamp = datetime.now().isoformat()

            # Get CPU temperature - try multiple sources based on architecture
            cpu_temp = 0
            gpu_temp = 0
            temp_source = None

            # On Apple Silicon, use macmon (sudoless, designed for M-series)
            if is_apple_silicon():
                try:
                    # macmon pipe runs continuously, so we use Popen to read one line and terminate
                    proc = subprocess.Popen(
                        ['macmon', 'pipe'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    try:
                        # Use communicate with timeout to avoid readline() blocking forever
                        stdout, stderr = proc.communicate(timeout=10)

                        # Extract just the first line (one JSON sample)
                        first_line = stdout.split('\n')[0] if stdout else ''

                        if first_line.strip():
                            data = json.loads(first_line.strip())
                            temp_data = data.get('temp', {})
                            cpu_temp = temp_data.get('cpu_temp_avg', 0)
                            gpu_temp = temp_data.get('gpu_temp_avg', 0)
                            if cpu_temp > 0:
                                temp_source = 'macmon'
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                except FileNotFoundError:
                    pass  # macmon not installed
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.debug(f"macmon error: {e}")

            # On Intel or if macmon failed, try osx-cpu-temp
            if cpu_temp == 0:
                try:
                    result = subprocess.run(
                        ['osx-cpu-temp'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        # Output format: "XX.X°C" or "XX.X C"
                        match = re.search(r'(\d+\.?\d*)\s*[°]?C', result.stdout)
                        if match:
                            cpu_temp = float(match.group(1))
                            temp_source = 'osx-cpu-temp'
                except FileNotFoundError:
                    pass  # osx-cpu-temp not installed
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    pass

            # Fallback to powermetrics (requires sudo, Intel only)
            if cpu_temp == 0 and not is_apple_silicon():
                try:
                    result = subprocess.run(
                        ['powermetrics', '-n', '1', '-i', '1000', '--samplers', 'smc'],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    if result.returncode == 0:
                        # Parse temperature from output
                        for line in result.stdout.split('\n'):
                            if 'CPU die temperature' in line:
                                match = re.search(r'(\d+\.?\d*)\s*C', line)
                                if match:
                                    cpu_temp = float(match.group(1))
                                    temp_source = 'powermetrics'
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                    pass  # powermetrics may fail without sudo

            # Get CPU frequency and detect throttling
            cpu_freq = 0
            cpu_max_freq = 0
            is_throttled = False

            try:
                # Get CPU info using sysctl
                result = subprocess.run(
                    ['sysctl', '-n', 'hw.cpufrequency'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    cpu_freq = int(result.stdout.strip()) / 1_000_000  # Convert to MHz

                result = subprocess.run(
                    ['sysctl', '-n', 'hw.cpufrequency_max'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    cpu_max_freq = int(result.stdout.strip()) / 1_000_000  # Convert to MHz

                # Detect throttling: if current freq < 80% of max freq
                if cpu_max_freq > 0 and cpu_freq > 0:
                    is_throttled = (cpu_freq / cpu_max_freq) < 0.8
                    if is_throttled:
                        self.total_throttle_events += 1

            except Exception:
                pass

            # Get thermal pressure (macOS specific)
            thermal_pressure = 'nominal'
            try:
                result = subprocess.run(
                    ['pmset', '-g', 'thermlog'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    # Parse thermal pressure level
                    if 'thermal level' in result.stdout.lower():
                        for line in result.stdout.split('\n'):
                            if 'thermal level' in line.lower():
                                thermal_pressure = line.split(':')[-1].strip()
            except Exception:
                pass

            # Get fan speed (if available via powermetrics)
            fan_speed = 0
            # Note: Fan speed monitoring typically requires SMC access or third-party tools

            # Log thermal metrics
            self.thermal_logger.append({
                'timestamp': timestamp,
                'cpu_temperature': cpu_temp,
                'cpu_temp_source': temp_source,
                'cpu_frequency': cpu_freq,
                'cpu_max_frequency': cpu_max_freq,
                'is_throttled': is_throttled,
                'thermal_pressure': thermal_pressure,
                'fan_speed': fan_speed
            })

        except Exception as e:
            logger.error(f"Error collecting thermal metrics: {e}")

    def _check_power_events(self):
        """Check for power-related events (sleep/wake, power source changes)."""
        try:
            timestamp = datetime.now().isoformat()

            # Get current power source
            result = subprocess.run(
                ['pmset', '-g', 'ps'],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode != 0:
                return

            current_power_source = 'Unknown'
            if 'AC Power' in result.stdout:
                current_power_source = 'AC'
            elif 'Battery Power' in result.stdout:
                current_power_source = 'Battery'

            # Extract battery level
            battery_level = 0
            match = re.search(r'(\d+)%', result.stdout)
            if match:
                battery_level = int(match.group(1))

            # Detect power source change event
            if self.last_power_source and self.last_power_source != current_power_source:
                self.power_events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'power_source_change',
                    'power_source': current_power_source,
                    'battery_level': battery_level,
                    'details': f'Changed from {self.last_power_source} to {current_power_source}'
                })
                self.total_power_events += 1

            # Detect low battery event
            if battery_level < 20 and (self.last_battery_level is None or self.last_battery_level >= 20):
                self.power_events_logger.append({
                    'timestamp': timestamp,
                    'event_type': 'low_battery',
                    'power_source': current_power_source,
                    'battery_level': battery_level,
                    'details': f'Battery level dropped to {battery_level}%'
                })
                self.total_power_events += 1

            # Update last known state
            self.last_power_source = current_power_source
            self.last_battery_level = battery_level

            # Check sleep/wake events (from pmset log)
            # Note: This requires parsing system logs which may need elevated privileges
            # For now, we'll skip detailed sleep/wake tracking

        except Exception as e:
            logger.error(f"Error checking power events: {e}")

    # Public API Methods

    def get_battery_health(self) -> Dict[str, Any]:
        """
        Get current battery health status.

        Returns:
            Dictionary with battery health metrics
        """
        try:
            # Read latest battery metrics
            history = self.battery_logger.get_history()
            if not history:
                return {
                    'health_percentage': 0,
                    'cycle_count': 0,
                    'status': 'Unknown',
                    'recommendation': 'Unable to read battery data'
                }

            latest = history[-1]
            health_pct = int(latest.get('health_percentage', 0))
            cycle_count = int(latest.get('cycle_count', 0))

            # Determine battery status
            status = 'Excellent'
            recommendation = 'Battery is in good health'

            if health_pct >= 80:
                status = 'Good'
            elif health_pct >= 60:
                status = 'Fair'
                recommendation = 'Consider battery replacement soon'
            else:
                status = 'Poor'
                recommendation = 'Battery replacement recommended'

            # Check cycle count (typical Mac batteries rated for 1000 cycles)
            if cycle_count > 800:
                recommendation = 'High cycle count - monitor battery closely'

            # Get real-time battery status from pmset (more accurate than cached data)
            current_charge = 0
            power_source = 'Unknown'
            is_charging = False
            time_remaining = 'N/A'

            try:
                result = subprocess.run(
                    ['pmset', '-g', 'batt'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    output_lower = result.stdout.lower()
                    # Detect power source
                    if 'ac power' in output_lower:
                        power_source = 'AC Power'
                    elif 'battery power' in output_lower:
                        power_source = 'Battery'

                    # Detect charging state - "discharging" contains "charging" so be specific
                    is_charging = 'charging;' in output_lower and 'discharging' not in output_lower

                    # Extract battery percentage
                    match = re.search(r'(\d+)%', result.stdout)
                    if match:
                        current_charge = int(match.group(1))

                    # Extract time remaining
                    match = re.search(r'(\d+:\d+) remaining', result.stdout)
                    if match:
                        time_remaining = match.group(1)
            except Exception:
                pass

            return {
                'health_percentage': health_pct,
                'cycle_count': cycle_count,
                'design_capacity': int(latest.get('design_capacity', 0)),
                'max_capacity': int(latest.get('max_capacity', 0)),
                'status': status,
                'recommendation': recommendation,
                'is_charging': is_charging,
                'time_remaining': time_remaining,
                'current_charge': current_charge,
                'power_source': power_source
            }

        except Exception as e:
            logger.error(f"Error getting battery health: {e}")
            return {
                'health_percentage': 0,
                'cycle_count': 0,
                'status': 'Error',
                'recommendation': f'Error reading battery data: {e}'
            }

    def get_thermal_status(self) -> Dict[str, Any]:
        """
        Get current thermal and throttling status.

        Returns:
            Dictionary with thermal metrics
        """
        try:
            # Read latest thermal metrics
            history = self.thermal_logger.get_history()
            if not history:
                return {
                    'cpu_temperature': 0,
                    'cpu_temp_source': None,
                    'is_throttled': False,
                    'throttle_events_24h': 0,
                    'status': 'Unknown'
                }

            # Find the most recent entry with valid CPU temperature
            # (Some collections may fail to get temp, so we look back)
            latest = history[-1]
            for entry in reversed(history):
                try:
                    temp = float(entry.get('cpu_temperature', 0))
                    if temp > 0 and entry.get('cpu_temp_source'):
                        latest = entry
                        break
                except (ValueError, TypeError):
                    continue
            is_throttled = latest.get('is_throttled', 'False') == 'True' or latest.get('is_throttled', False) == True

            # Count throttle events in last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            throttle_events = 0

            for entry in history:
                try:
                    entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                    if entry_time >= cutoff_time:
                        if entry.get('is_throttled', 'False') == 'True' or entry.get('is_throttled', False) == True:
                            throttle_events += 1
                except ValueError:
                    continue

            # Determine thermal status
            status = 'Normal'
            if throttle_events > 10:
                status = 'Frequent Throttling'
            elif is_throttled:
                status = 'Currently Throttled'

            return {
                'cpu_temperature': float(latest.get('cpu_temperature', 0)),
                'cpu_temp_source': latest.get('cpu_temp_source'),
                'cpu_frequency': float(latest.get('cpu_frequency', 0)),
                'cpu_max_frequency': float(latest.get('cpu_max_frequency', 0)),
                'is_throttled': is_throttled,
                'thermal_pressure': latest.get('thermal_pressure', 'nominal'),
                'throttle_events_24h': throttle_events,
                'status': status
            }

        except Exception as e:
            logger.error(f"Error getting thermal status: {e}")
            return {
                'cpu_temperature': 0,
                'cpu_temp_source': None,
                'is_throttled': False,
                'throttle_events_24h': 0,
                'status': 'Error'
            }

    def get_power_summary(self) -> Dict[str, Any]:
        """
        Get summary of power metrics and recent events.

        Returns:
            Dictionary with power summary
        """
        battery_health = self.get_battery_health()
        thermal_status = self.get_thermal_status()

        # Get recent power events
        recent_events = []
        try:
            history = self.power_events_logger.get_history()
            cutoff_time = datetime.now() - timedelta(hours=24)

            for entry in history:
                try:
                    entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                    if entry_time >= cutoff_time:
                        recent_events.append(entry)
                except ValueError:
                    continue
        except Exception:
            pass

        return {
            'battery': battery_health,
            'thermal': thermal_status,
            'recent_events': recent_events[-10:],  # Last 10 events
            'total_power_events': self.total_power_events
        }


# Singleton accessor
def get_power_monitor(data_dir: str = None) -> PowerMonitor:
    """
    Get the singleton PowerMonitor instance.

    Args:
        data_dir: Directory for CSV log files

    Returns:
        PowerMonitor singleton instance
    """
    with PowerMonitor._lock:
        if PowerMonitor._instance is None:
            PowerMonitor._instance = PowerMonitor(data_dir)
            PowerMonitor._instance.start()
        return PowerMonitor._instance


# Test harness
if __name__ == '__main__':
    logger.info("Testing Power Monitor...")

    monitor = PowerMonitor()

    logger.info("1. Collecting battery metrics...")
    monitor._collect_battery_metrics()

    logger.info("2. Collecting thermal metrics...")
    monitor._collect_thermal_metrics()

    logger.info("3. Checking power events...")
    monitor._check_power_events()

    logger.info("4. Getting battery health...")
    health = monitor.get_battery_health()
    logger.info(f"   Health: {health['health_percentage']}%")
    logger.info(f"   Cycle Count: {health['cycle_count']}")
    logger.info(f"   Status: {health['status']}")

    logger.info("5. Getting thermal status...")
    thermal = monitor.get_thermal_status()
    logger.info(f"   CPU Temp: {thermal['cpu_temperature']}°C")
    logger.info(f"   Throttled: {thermal['is_throttled']}")

    logger.info("Power Monitor: Ready for Integration")
