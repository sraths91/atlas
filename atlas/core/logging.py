"""
Shared CSV logging infrastructure for all monitors

This module eliminates 600+ lines of duplicated code across network widgets
by providing a single, well-tested CSV logging implementation.
"""

import csv
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


class CSVLogger:
    """
    Generic CSV logger for widget data with automatic cleanup and history management.

    Features:
    - Thread-safe operations
    - Automatic file initialization with headers
    - Rolling history with configurable retention
    - Old log cleanup (default: 7 days)
    - In-memory history cache for quick access

    Usage:
        logger = CSVLogger(
            log_file="~/wifi_quality.csv",
            fieldnames=['timestamp', 'ssid', 'rssi', 'quality_score'],
            max_history=60,
            retention_days=7
        )

        # Append entries
        logger.append({'timestamp': '2025-12-31T10:00:00', 'ssid': 'MyWiFi', ...})

        # Get recent history
        recent = logger.get_history()
    """

    def __init__(self,
                 log_file: str,
                 fieldnames: List[str],
                 max_history: int = 100,
                 retention_days: int = 7):
        """
        Initialize CSV logger

        Args:
            log_file: Path to CSV file (will be created if doesn't exist)
            fieldnames: List of column names for the CSV
            max_history: Maximum number of entries to keep in memory
            retention_days: Number of days to retain log entries
        """
        self.log_file = str(Path(log_file).expanduser())
        self.fieldnames = fieldnames
        self.max_history = max_history
        self.retention_days = retention_days

        # Thread-safe in-memory history
        self.history = deque(maxlen=max_history)
        self._lock = threading.Lock()

        # Initialize log file and load history
        self._initialize_log_file()
        self._load_recent_history()
        self._cleanup_old_logs()

    def _initialize_log_file(self):
        """Initialize CSV log file with headers if it doesn't exist"""
        try:
            log_path = Path(self.log_file)
            if not log_path.exists():
                # Create parent directory if needed
                log_path.parent.mkdir(parents=True, exist_ok=True)

                # Write header
                with open(log_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                    writer.writeheader()

                logger.info(f"Initialized CSV log file: {self.log_file}")
        except Exception as e:
            logger.error(f"Failed to initialize log file {self.log_file}: {e}")

    def _load_recent_history(self) -> List[Dict[str, Any]]:
        """Load recent history from log file into memory"""
        try:
            if not Path(self.log_file).exists():
                return []

            with self._lock:
                with open(self.log_file, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    all_rows = list(reader)
                    recent_rows = all_rows[-self.max_history:]

                    self.history.clear()
                    for row in recent_rows:
                        self.history.append(row)

                logger.debug(f"Loaded {len(self.history)} entries from {self.log_file}")
                return list(self.history)
        except Exception as e:
            logger.error(f"Failed to load history from {self.log_file}: {e}")
            return []

    def _cleanup_old_logs(self):
        """Remove log entries older than retention period"""
        try:
            if not Path(self.log_file).exists():
                return

            with open(self.log_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                all_rows = list(reader)

            if not all_rows or not fieldnames:
                return

            cutoff_time = datetime.now() - timedelta(days=self.retention_days)
            recent_rows = []
            removed_count = 0

            for row in all_rows:
                try:
                    # Parse timestamp (assumes ISO format)
                    row_time = datetime.fromisoformat(row.get('timestamp', ''))
                    if row_time >= cutoff_time:
                        recent_rows.append(row)
                    else:
                        removed_count += 1
                except (ValueError, KeyError):
                    # Keep rows with invalid timestamps
                    recent_rows.append(row)

            # Rewrite file if entries were removed
            if removed_count > 0:
                with open(self.log_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(recent_rows)

                logger.info(f"Cleaned up {removed_count} old entries from {self.log_file}")
        except Exception as e:
            logger.error(f"Failed to cleanup old logs from {self.log_file}: {e}")

    def append(self, entry: Dict[str, Any]):
        """
        Append an entry to the log file and in-memory history

        Args:
            entry: Dictionary with values for each field in fieldnames
        """
        try:
            with self._lock:
                # Append to file
                with open(self.log_file, 'a', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                    writer.writerow(entry)

                # Add to in-memory history
                self.history.append(entry)
        except Exception as e:
            logger.error(f"Failed to append to log file {self.log_file}: {e}")

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get the in-memory history

        Returns:
            List of dictionaries containing recent log entries
        """
        with self._lock:
            return list(self.history)

    def clear_history(self):
        """Clear in-memory history (does not affect log file)"""
        with self._lock:
            self.history.clear()

    def reload_history(self):
        """Reload history from log file"""
        self._load_recent_history()

    def get_log_path(self) -> str:
        """Get the full path to the log file"""
        return self.log_file
