#!/usr/bin/env python3
"""
ATLAS Agent - Display & Graphics Monitor

Monitors display and GPU metrics:
- Connected displays (count, type, connection)
- Display resolution and refresh rate
- GPU temperature (discrete GPU only)
- GPU memory usage (VRAM)
- GPU utilization (integrated with system monitor)

Provides comprehensive graphics subsystem monitoring for fleet management.
"""

import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from atlas.core.logging import CSVLogger
    CSV_AVAILABLE = True
except ImportError:
    CSV_AVAILABLE = False
    logging.warning("CSVLogger not available - display monitoring will use basic logging")

logger = logging.getLogger(__name__)


class DisplayMonitor:
    """Monitors display and GPU metrics"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.is_available = True

        # Setup data directory
        data_dir = os.path.expanduser("~/.atlas_agent/data")
        os.makedirs(data_dir, exist_ok=True)

        # Initialize CSV loggers
        if CSV_AVAILABLE:
            try:
                self.display_logger = CSVLogger(
                    log_file=os.path.join(data_dir, "display_status.csv"),
                    fieldnames=[
                        'timestamp', 'display_count', 'primary_resolution',
                        'primary_refresh_rate', 'display_types', 'connections'
                    ],
                    max_history=10000
                )

                self.gpu_logger = CSVLogger(
                    log_file=os.path.join(data_dir, "gpu_status.csv"),
                    fieldnames=[
                        'timestamp', 'gpu_name', 'gpu_vendor', 'vram_total_mb',
                        'vram_used_mb', 'vram_free_mb', 'gpu_temp_celsius',
                        'has_discrete_gpu', 'is_apple_silicon', 'unified_memory_mb'
                    ],
                    max_history=10000
                )
            except Exception as e:
                logger.error(f"Failed to initialize CSV loggers: {e}")
                self.display_logger = None
                self.gpu_logger = None
        else:
            self.display_logger = None
            self.gpu_logger = None

        # Cache for display/GPU info (updated periodically)
        self._display_cache = None
        self._gpu_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 60  # 60 second cache

        # Start background monitoring thread
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        logger.info("Display Monitor initialized")

    def _get_display_info(self) -> Dict:
        """Get connected display information using system_profiler"""
        try:
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning("system_profiler failed for displays")
                return self._get_display_info_fallback()

            data = json.loads(result.stdout)
            displays_data = data.get('SPDisplaysDataType', [])

            if not displays_data:
                return {
                    'display_count': 0,
                    'displays': [],
                    'primary_resolution': 'Unknown',
                    'primary_refresh_rate': 0
                }

            displays = []
            display_count = 0
            primary_resolution = 'Unknown'
            primary_refresh_rate = 0

            for gpu in displays_data:
                gpu_displays = gpu.get('spdisplays_ndrvs', [])

                for disp in gpu_displays:
                    display_count += 1

                    # Parse resolution
                    resolution = disp.get('_spdisplays_resolution', 'Unknown')

                    # Parse refresh rate (if available)
                    refresh_str = disp.get('spdisplays_refresh', '0')
                    refresh_rate = 0
                    if refresh_str and isinstance(refresh_str, str):
                        match = re.search(r'(\d+)', refresh_str)
                        if match:
                            refresh_rate = int(match.group(1))

                    # Connection type
                    connection = disp.get('spdisplays_connection_type', 'Unknown')

                    # Display type (built-in vs external)
                    # Check connection type to determine if internal
                    raw_type = disp.get('_spdisplays_display-type', '')
                    is_internal = (
                        'internal' in connection.lower() or
                        'built' in str(raw_type).lower() or
                        'color lcd' in disp.get('_name', '').lower() or
                        connection.lower() == 'spdisplays_internal'
                    )
                    display_type = 'Built-in' if is_internal else 'External'

                    displays.append({
                        'resolution': resolution,
                        'refresh_rate': refresh_rate,
                        'connection': connection,
                        'type': display_type,
                        'name': disp.get('_name', 'Unknown Display')
                    })

                    # First display is primary
                    if display_count == 1:
                        primary_resolution = resolution
                        primary_refresh_rate = refresh_rate

            return {
                'display_count': display_count,
                'displays': displays,
                'primary_resolution': primary_resolution,
                'primary_refresh_rate': primary_refresh_rate,
                'display_types': ', '.join([d['type'] for d in displays]),
                'connections': ', '.join([d['connection'] for d in displays])
            }

        except subprocess.TimeoutExpired:
            logger.warning("system_profiler timed out")
            return self._get_display_info_fallback()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse display JSON: {e}")
            return self._get_display_info_fallback()
        except Exception as e:
            logger.error(f"Error getting display info: {e}")
            return self._get_display_info_fallback()

    def _get_display_info_fallback(self) -> Dict:
        """Fallback method using simpler commands"""
        try:
            # Try to count displays using system_profiler without JSON
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Count occurrences of "Resolution:" to estimate display count
            display_count = result.stdout.count('Resolution:')

            # Try to extract first resolution
            resolution_match = re.search(r'Resolution:\s*(.+)', result.stdout)
            primary_resolution = resolution_match.group(1).strip() if resolution_match else 'Unknown'

            return {
                'display_count': display_count,
                'displays': [],
                'primary_resolution': primary_resolution,
                'primary_refresh_rate': 0,
                'display_types': 'Unknown',
                'connections': 'Unknown'
            }
        except Exception as e:
            logger.error(f"Display fallback failed: {e}")
            return {
                'display_count': 0,
                'displays': [],
                'primary_resolution': 'Unknown',
                'primary_refresh_rate': 0,
                'display_types': 'Unknown',
                'connections': 'Unknown'
            }

    def _get_gpu_info(self) -> Dict:
        """Get GPU information including VRAM and temperature"""
        try:
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning("system_profiler failed for GPU")
                return self._get_gpu_info_fallback()

            data = json.loads(result.stdout)
            displays_data = data.get('SPDisplaysDataType', [])

            if not displays_data:
                return {
                    'gpu_name': 'Unknown',
                    'gpu_vendor': 'Unknown',
                    'vram_total_mb': 0,
                    'vram_used_mb': 0,
                    'vram_free_mb': 0,
                    'gpu_temp_celsius': 0,
                    'has_discrete_gpu': False,
                    'is_apple_silicon': False,
                    'unified_memory_mb': 0
                }

            # Get first GPU (primary)
            gpu = displays_data[0]

            gpu_name = gpu.get('sppci_model', 'Unknown GPU')
            gpu_vendor = gpu.get('sppci_vendor', 'Unknown')

            # Detect Apple Silicon (M1, M2, M3, M4, etc.)
            is_apple_silicon = bool(re.search(r'Apple M\d', gpu_name))

            # Parse VRAM
            vram_str = gpu.get('sppci_vram', '0 MB')
            vram_total_mb = 0
            if isinstance(vram_str, str):
                # Parse formats like "8192 MB" or "8 GB"
                match = re.search(r'(\d+)\s*(MB|GB)', vram_str, re.IGNORECASE)
                if match:
                    value = int(match.group(1))
                    unit = match.group(2).upper()
                    vram_total_mb = value * 1024 if unit == 'GB' else value

            # For Apple Silicon, get unified memory info
            unified_memory_mb = 0
            if is_apple_silicon:
                unified_memory_mb = self._get_unified_memory()
                # Apple Silicon doesn't have dedicated VRAM - it uses unified memory
                # Report unified memory as total "GPU memory" for Apple Silicon
                if unified_memory_mb > 0:
                    vram_total_mb = unified_memory_mb

            # Detect discrete GPU
            has_discrete_gpu = 'AMD' in gpu_vendor or 'NVIDIA' in gpu_vendor or 'Radeon' in gpu_name or 'GeForce' in gpu_name

            # Get GPU temperature (discrete GPU only)
            gpu_temp = 0
            if has_discrete_gpu:
                gpu_temp = self._get_gpu_temperature()

            # Estimate VRAM/memory usage
            display_info = self._display_cache or self._get_display_info()
            display_count = display_info.get('display_count', 1)

            if is_apple_silicon and unified_memory_mb > 0:
                # For Apple Silicon, estimate GPU memory usage from unified memory
                # GPU typically uses 10-30% of unified memory depending on workload
                estimated_used_mb = self._get_apple_silicon_gpu_memory_usage(unified_memory_mb)
                vram_free_mb = max(0, unified_memory_mb - estimated_used_mb)
            else:
                # Rough estimate for discrete GPU: ~500MB per 4K display, ~200MB per 1080p
                estimated_used_mb = min(500 * display_count, vram_total_mb // 2) if vram_total_mb > 0 else 0
                vram_free_mb = max(0, vram_total_mb - estimated_used_mb)

            return {
                'gpu_name': gpu_name,
                'gpu_vendor': gpu_vendor,
                'vram_total_mb': vram_total_mb,
                'vram_used_mb': estimated_used_mb,
                'vram_free_mb': vram_free_mb,
                'gpu_temp_celsius': gpu_temp,
                'has_discrete_gpu': has_discrete_gpu,
                'is_apple_silicon': is_apple_silicon,
                'unified_memory_mb': unified_memory_mb
            }

        except subprocess.TimeoutExpired:
            logger.warning("system_profiler timed out for GPU")
            return self._get_gpu_info_fallback()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPU JSON: {e}")
            return self._get_gpu_info_fallback()
        except Exception as e:
            logger.error(f"Error getting GPU info: {e}")
            return self._get_gpu_info_fallback()

    def _get_gpu_info_fallback(self) -> Dict:
        """Fallback GPU info using text parsing"""
        try:
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Extract GPU name
            gpu_match = re.search(r'Chipset Model:\s*(.+)', result.stdout)
            gpu_name = gpu_match.group(1).strip() if gpu_match else 'Unknown GPU'

            # Detect Apple Silicon
            is_apple_silicon = bool(re.search(r'Apple M\d', gpu_name))

            # Extract VRAM
            vram_match = re.search(r'VRAM.*?:\s*(\d+)\s*(MB|GB)', result.stdout, re.IGNORECASE)
            vram_total_mb = 0
            if vram_match:
                value = int(vram_match.group(1))
                unit = vram_match.group(2).upper()
                vram_total_mb = value * 1024 if unit == 'GB' else value

            # For Apple Silicon, get unified memory
            unified_memory_mb = 0
            if is_apple_silicon:
                unified_memory_mb = self._get_unified_memory()
                if unified_memory_mb > 0:
                    vram_total_mb = unified_memory_mb

            return {
                'gpu_name': gpu_name,
                'gpu_vendor': 'Apple' if is_apple_silicon else 'Unknown',
                'vram_total_mb': vram_total_mb,
                'vram_used_mb': 0,
                'vram_free_mb': vram_total_mb,
                'gpu_temp_celsius': 0,
                'has_discrete_gpu': False,
                'is_apple_silicon': is_apple_silicon,
                'unified_memory_mb': unified_memory_mb
            }
        except Exception as e:
            logger.error(f"GPU fallback failed: {e}")
            return {
                'gpu_name': 'Unknown',
                'gpu_vendor': 'Unknown',
                'vram_total_mb': 0,
                'vram_used_mb': 0,
                'vram_free_mb': 0,
                'gpu_temp_celsius': 0,
                'has_discrete_gpu': False,
                'is_apple_silicon': False,
                'unified_memory_mb': 0
            }

    def _get_gpu_temperature(self) -> float:
        """Get GPU temperature (discrete GPU only)"""
        try:
            # Try using ioreg to get GPU temperature sensors
            result = subprocess.run(
                ['ioreg', '-r', '-c', 'AppleGraphicsPowerManagement'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Look for temperature values
            temp_match = re.search(r'"Temperature"\s*=\s*(\d+)', result.stdout)
            if temp_match:
                # Temperature is typically in centi-degrees Celsius
                temp_raw = int(temp_match.group(1))
                return temp_raw / 100.0

            return 0

        except Exception as e:
            logger.debug(f"Could not get GPU temperature: {e}")
            return 0

    def _get_unified_memory(self) -> int:
        """Get total unified memory for Apple Silicon Macs (in MB)"""
        try:
            # Use sysctl to get total physical memory
            result = subprocess.run(
                ['sysctl', '-n', 'hw.memsize'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                # hw.memsize returns bytes
                total_bytes = int(result.stdout.strip())
                total_mb = total_bytes // (1024 * 1024)
                return total_mb

            return 0

        except Exception as e:
            logger.debug(f"Could not get unified memory: {e}")
            return 0

    def _get_apple_silicon_gpu_memory_usage(self, unified_memory_mb: int) -> int:
        """Estimate GPU memory usage on Apple Silicon from system memory pressure"""
        try:
            # Use vm_stat to get memory usage info
            result = subprocess.run(
                ['vm_stat'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return 0

            # Parse vm_stat output
            output = result.stdout
            page_size = 16384  # Apple Silicon uses 16KB pages

            # Look for page size in output
            page_match = re.search(r'page size of (\d+) bytes', output)
            if page_match:
                page_size = int(page_match.group(1))

            # Get wired memory (closest proxy for GPU memory usage)
            # GPU allocations are typically wired (non-swappable)
            wired_match = re.search(r'Pages wired down:\s+(\d+)', output)
            if wired_match:
                wired_pages = int(wired_match.group(1))
                wired_mb = (wired_pages * page_size) // (1024 * 1024)
                # GPU typically accounts for ~30-50% of wired memory
                # This is a rough estimate as macOS doesn't expose exact GPU memory usage
                estimated_gpu_mb = int(wired_mb * 0.4)
                return min(estimated_gpu_mb, unified_memory_mb // 2)

            return 0

        except Exception as e:
            logger.debug(f"Could not estimate GPU memory usage: {e}")
            return 0

    def get_display_status(self) -> Dict:
        """Get current display status"""
        current_time = time.time()

        # Return cached data if still valid
        if self._display_cache and (current_time - self._cache_timestamp) < self._cache_ttl:
            return self._display_cache

        # Refresh cache
        self._display_cache = self._get_display_info()
        self._cache_timestamp = current_time

        return self._display_cache

    def get_gpu_status(self) -> Dict:
        """Get current GPU status"""
        current_time = time.time()

        # Return cached data if still valid
        if self._gpu_cache and (current_time - self._cache_timestamp) < self._cache_ttl:
            return self._gpu_cache

        # Refresh cache
        self._gpu_cache = self._get_gpu_info()
        self._cache_timestamp = current_time

        return self._gpu_cache

    def get_status(self) -> Dict:
        """Get combined display and GPU status"""
        display_status = self.get_display_status()
        gpu_status = self.get_gpu_status()

        return {
            'timestamp': datetime.now().isoformat(),
            'display': display_status,
            'gpu': gpu_status,
            'status': 'healthy' if display_status['display_count'] > 0 else 'warning'
        }

    def stop(self):
        """Stop background display monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                # Collect display status
                display_status = self.get_display_status()

                # Log to CSV
                if self.display_logger:
                    self.display_logger.append({
                        'timestamp': datetime.now().isoformat(),
                        'display_count': display_status['display_count'],
                        'primary_resolution': display_status['primary_resolution'],
                        'primary_refresh_rate': display_status['primary_refresh_rate'],
                        'display_types': display_status.get('display_types', 'Unknown'),
                        'connections': display_status.get('connections', 'Unknown')
                    })

                # Collect GPU status
                gpu_status = self.get_gpu_status()

                # Log to CSV
                if self.gpu_logger:
                    self.gpu_logger.append({
                        'timestamp': datetime.now().isoformat(),
                        'gpu_name': gpu_status['gpu_name'],
                        'gpu_vendor': gpu_status['gpu_vendor'],
                        'vram_total_mb': gpu_status['vram_total_mb'],
                        'vram_used_mb': gpu_status['vram_used_mb'],
                        'vram_free_mb': gpu_status['vram_free_mb'],
                        'gpu_temp_celsius': gpu_status['gpu_temp_celsius'],
                        'has_discrete_gpu': gpu_status['has_discrete_gpu'],
                        'is_apple_silicon': gpu_status.get('is_apple_silicon', False),
                        'unified_memory_mb': gpu_status.get('unified_memory_mb', 0)
                    })

                # Sleep in small intervals to allow graceful shutdown
                for _ in range(300):
                    if not self._running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in display monitor loop: {e}")
                for _ in range(60):
                    if not self._running:
                        break
                    time.sleep(1)


# Singleton instance
_monitor_instance = None
_monitor_lock = threading.Lock()


def get_display_monitor() -> DisplayMonitor:
    """Get singleton DisplayMonitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        with _monitor_lock:
            if _monitor_instance is None:
                _monitor_instance = DisplayMonitor()
    return _monitor_instance


def get_display_status() -> Dict:
    """Get current display status"""
    monitor = get_display_monitor()
    return monitor.get_status()


if __name__ == '__main__':
    # Test the monitor
    logging.basicConfig(level=logging.INFO)

    logger.info("Testing Display Monitor...")
    monitor = get_display_monitor()

    logger.info("=== Display Status ===")
    display_status = monitor.get_display_status()
    logger.info(f"Display Count: {display_status['display_count']}")
    logger.info(f"Primary Resolution: {display_status['primary_resolution']}")
    logger.info(f"Primary Refresh Rate: {display_status['primary_refresh_rate']} Hz")

    if display_status['displays']:
        logger.info("Connected Displays:")
        for i, disp in enumerate(display_status['displays'], 1):
            logger.info(f"  {i}. {disp['name']}")
            logger.info(f"     Resolution: {disp['resolution']}")
            logger.info(f"     Refresh Rate: {disp['refresh_rate']} Hz")
            logger.info(f"     Connection: {disp['connection']}")
            logger.info(f"     Type: {disp['type']}")

    logger.info("=== GPU Status ===")
    gpu_status = monitor.get_gpu_status()
    logger.info(f"GPU: {gpu_status['gpu_name']}")
    logger.info(f"Vendor: {gpu_status['gpu_vendor']}")
    logger.info(f"VRAM Total: {gpu_status['vram_total_mb']} MB")
    logger.info(f"VRAM Used: {gpu_status['vram_used_mb']} MB (estimated)")
    logger.info(f"VRAM Free: {gpu_status['vram_free_mb']} MB")
    logger.info(f"GPU Temperature: {gpu_status['gpu_temp_celsius']}°C")
    logger.info(f"Discrete GPU: {gpu_status['has_discrete_gpu']}")

    logger.info("=== Combined Status ===")
    status = monitor.get_status()
    logger.info(json.dumps(status, indent=2))

    logger.info("Display Monitor test complete")
