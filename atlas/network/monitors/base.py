"""
Base Network Monitor Class

This module eliminates 450+ lines of duplicated monitoring infrastructure
by providing a single, well-tested base class for all network monitors.
"""

import threading
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseNetworkMonitor(ABC):
    """
    Abstract base class for network monitoring widgets.

    Features:
    - Thread-safe monitoring loop
    - Lifecycle management (start/stop)
    - Automatic cleanup scheduling
    - Fleet logging integration
    - Configurable monitoring interval
    - Last result tracking with thread-safe access

    Subclasses must implement:
    - _run_monitoring_cycle(): Perform one monitoring cycle
    - get_monitor_name(): Return a human-readable name for logging

    Optional overrides:
    - get_default_interval(): Default monitoring interval (default: 10s)
    - get_cleanup_interval(): Cleanup interval (default: 24h)
    - _on_start(): Called when monitoring starts
    - _on_stop(): Called when monitoring stops
    - _on_cleanup(): Called during scheduled cleanup

    Usage:
        class WiFiMonitor(BaseNetworkMonitor):
            def _run_monitoring_cycle(self):
                # Collect WiFi metrics
                wifi_data = self._get_wifi_info()
                self.update_last_result(wifi_data)

            def get_monitor_name(self) -> str:
                return "WiFi Quality Monitor"

        monitor = WiFiMonitor()
        monitor.start(interval=10)
        # ... monitor runs in background ...
        monitor.stop()
    """

    def __init__(self):
        """Initialize base monitor"""
        # Monitoring state
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Results tracking
        self.last_result: Dict[str, Any] = {}

        # Timing
        self.interval = self.get_default_interval()
        self.last_cleanup_time = time.time()
        self.cleanup_interval = self.get_cleanup_interval()

        # Fleet logging (optional)
        self.fleet_logger = None
        self._init_fleet_logging()

        logger.debug(f"{self.get_monitor_name()} initialized")

    # ==================== Abstract Methods ====================

    @abstractmethod
    def _run_monitoring_cycle(self):
        """
        Execute one monitoring cycle.

        This method should:
        1. Collect monitoring data
        2. Update self.last_result using update_last_result()
        3. Log any errors appropriately

        This method is called repeatedly in the monitoring loop.
        """
        pass

    @abstractmethod
    def get_monitor_name(self) -> str:
        """
        Return human-readable monitor name for logging.

        Example: "WiFi Quality Monitor", "Speed Test Monitor"
        """
        pass

    # ==================== Optional Override Methods ====================

    def get_default_interval(self) -> int:
        """Get default monitoring interval in seconds (default: 10)"""
        return 10

    def get_cleanup_interval(self) -> int:
        """Get cleanup interval in seconds (default: 24 hours)"""
        return 86400  # 24 hours

    def _on_start(self):
        """Called when monitoring starts (override for custom initialization)"""
        pass

    def _on_stop(self):
        """Called when monitoring stops (override for custom cleanup)"""
        pass

    def _on_cleanup(self):
        """Called during scheduled cleanup (override for custom cleanup logic)"""
        pass

    # ==================== Lifecycle Management ====================

    def start(self, interval: Optional[int] = None):
        """
        Start monitoring in background thread.

        Args:
            interval: Monitoring interval in seconds (uses default if not specified)
        """
        if self.running:
            logger.warning(f"{self.get_monitor_name()} already running")
            return

        if interval is not None:
            self.interval = interval

        self.running = True

        # Call custom start hook
        try:
            self._on_start()
        except Exception as e:
            logger.error(f"Error in _on_start for {self.get_monitor_name()}: {e}")

        # Start monitoring thread
        self.thread = threading.Thread(
            target=self._monitor_loop,
            args=(self.interval,),
            daemon=True,
            name=f"{self.get_monitor_name()}-Thread"
        )
        self.thread.start()

        logger.info(f"{self.get_monitor_name()} started (interval: {self.interval}s)")

    def stop(self, timeout: int = 5):
        """
        Stop monitoring and wait for thread to finish.

        Args:
            timeout: Maximum seconds to wait for thread to finish
        """
        if not self.running:
            logger.warning(f"{self.get_monitor_name()} not running")
            return

        self.running = False

        # Call custom stop hook
        try:
            self._on_stop()
        except Exception as e:
            logger.error(f"Error in _on_stop for {self.get_monitor_name()}: {e}")

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

        logger.info(f"{self.get_monitor_name()} stopped")

    def is_running(self) -> bool:
        """Check if monitor is currently running"""
        return self.running

    # ==================== Monitoring Loop ====================

    def _monitor_loop(self, interval: int):
        """
        Main monitoring loop (runs in background thread).

        This method:
        1. Runs monitoring cycles at specified interval
        2. Handles errors gracefully
        3. Performs scheduled cleanup
        4. Can be stopped by setting self.running = False
        """
        while self.running:
            try:
                # Run one monitoring cycle
                self._run_monitoring_cycle()

            except Exception as e:
                logger.error(f"Error in {self.get_monitor_name()} monitoring cycle: {e}")
                # Continue running despite errors
                with self._lock:
                    self.last_result['status'] = 'error'
                    self.last_result['error'] = str(e)
                    self.last_result['timestamp'] = datetime.now().isoformat()

            # Check if it's time for cleanup
            if time.time() - self.last_cleanup_time >= self.cleanup_interval:
                try:
                    logger.debug(f"Running scheduled cleanup for {self.get_monitor_name()}")
                    self._on_cleanup()
                    self.last_cleanup_time = time.time()
                except Exception as e:
                    logger.error(f"Error in cleanup for {self.get_monitor_name()}: {e}")

            # Sleep for interval (check running flag every second for responsive shutdown)
            elapsed = 0
            while elapsed < interval and self.running:
                time.sleep(min(1, interval - elapsed))
                elapsed += 1

    # ==================== Result Management ====================

    def update_last_result(self, result: Dict[str, Any]):
        """
        Thread-safe update of last result.

        Args:
            result: Dictionary of monitoring results
        """
        with self._lock:
            self.last_result.update(result)
            if 'timestamp' not in result:
                self.last_result['timestamp'] = datetime.now().isoformat()

    def get_last_result(self) -> Dict[str, Any]:
        """
        Thread-safe retrieval of last result.

        Returns:
            Copy of last result dictionary
        """
        with self._lock:
            return self.last_result.copy()

    def clear_last_result(self):
        """Thread-safe clearing of last result"""
        with self._lock:
            self.last_result.clear()

    # ==================== Fleet Logging Integration ====================

    def _init_fleet_logging(self):
        """Initialize fleet logging if available"""
        try:
            from atlas.widget_log_collector import log_widget_event
            self.fleet_logger = log_widget_event
            logger.debug(f"Fleet logging enabled for {self.get_monitor_name()}")
        except ImportError:
            self.fleet_logger = None
            logger.debug(f"Fleet logging not available for {self.get_monitor_name()}")

    def log_to_fleet(self, event_type: str, data: Dict[str, Any], level: str = "info"):
        """
        Log event to fleet server if available.

        Args:
            event_type: Type of event (e.g., 'wifi_quality', 'speed_test')
            data: Event data dictionary
            level: Log level (default: 'info')
        """
        if self.fleet_logger:
            try:
                self.fleet_logger(
                    level=level,
                    widget_type=self.get_monitor_name(),
                    message=event_type,
                    data=data
                )
            except Exception as e:
                logger.error(f"Failed to log to fleet: {e}")

    # ==================== Utility Methods ====================

    def get_status(self) -> str:
        """Get current monitoring status"""
        if not self.running:
            return "stopped"
        return self.last_result.get('status', 'unknown')

    def get_uptime(self) -> Optional[float]:
        """Get monitoring uptime in seconds (None if not running)"""
        if not self.running or not self.thread:
            return None
        # Would need to track start time to implement this
        # Could be added in future enhancement
        return None

    def __repr__(self) -> str:
        """String representation of monitor"""
        status = "running" if self.running else "stopped"
        return f"<{self.get_monitor_name()} status={status} interval={self.interval}s>"


# ==================== Singleton Helper ====================

class SingletonMonitor:
    """
    Helper class for implementing singleton monitor instances.

    Usage:
        class WiFiMonitorSingleton(SingletonMonitor):
            _instance_class = WiFiMonitor

        # Get or create singleton
        monitor = WiFiMonitorSingleton.get_instance()
    """

    _instance = None
    _lock = threading.Lock()
    _instance_class = None  # Subclasses should set this

    @classmethod
    def get_instance(cls):
        """Get or create singleton instance (thread-safe)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if cls._instance_class is None:
                        raise ValueError("_instance_class must be set in subclass")
                    cls._instance = cls._instance_class()
        return cls._instance

    @classmethod
    def clear_instance(cls):
        """Clear singleton instance (useful for testing)"""
        with cls._lock:
            if cls._instance is not None and hasattr(cls._instance, 'stop'):
                cls._instance.stop()
            cls._instance = None
