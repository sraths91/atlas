"""
macOS Notification System for ATLAS Agent

Sends native macOS notifications when network slowdowns are detected.
Uses osascript to trigger macOS notification center.
"""

import subprocess
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages macOS notifications for network events"""

    def __init__(self):
        """Initialize notification manager with rate limiting"""
        self.last_notification_time: Optional[datetime] = None
        self.min_notification_interval = timedelta(minutes=15)  # Don't spam
        self.notification_history_file = Path.home() / ".config" / "atlas-agent" / "notification_history.json"
        self.notification_history_file.parent.mkdir(parents=True, exist_ok=True)
        self.enabled = True  # Can be disabled via settings

    def send_slowdown_notification(self,
                                   download_speed: float,
                                   upload_speed: float,
                                   duration_minutes: int,
                                   primary_cause: Optional[str] = None) -> bool:
        """
        Send a notification about a network slowdown

        Args:
            download_speed: Current download speed in Mbps
            upload_speed: Current upload speed in Mbps
            duration_minutes: How long the slowdown has been occurring
            primary_cause: Optional description of the likely cause

        Returns:
            True if notification was sent, False if skipped (rate limited)
        """
        if not self.enabled:
            logger.debug("Notifications disabled")
            return False

        # Check rate limiting
        if self.last_notification_time:
            time_since_last = datetime.now() - self.last_notification_time
            if time_since_last < self.min_notification_interval:
                logger.debug(f"Skipping notification (rate limited, {time_since_last.seconds}s since last)")
                return False

        # Build notification content
        title = "Network Slowdown Detected"

        # Format the message
        message_parts = [
            f"Download: {download_speed:.1f} Mbps",
            f"Upload: {upload_speed:.1f} Mbps"
        ]

        if duration_minutes > 0:
            message_parts.append(f"Duration: {duration_minutes} min")

        if primary_cause:
            message_parts.append(f"Cause: {primary_cause}")

        message = " • ".join(message_parts)

        # Send the notification
        success = self._send_macos_notification(title, message)

        if success:
            self.last_notification_time = datetime.now()
            self._log_notification(title, message)
            logger.info(f"Sent slowdown notification: {message}")

        return success

    def send_recovery_notification(self, new_speed: float) -> bool:
        """
        Send a notification when network speed recovers

        Args:
            new_speed: The recovered download speed in Mbps

        Returns:
            True if notification was sent
        """
        if not self.enabled:
            return False

        title = "Network Speed Recovered"
        message = f"Download speed is now {new_speed:.1f} Mbps"

        success = self._send_macos_notification(title, message)

        if success:
            self._log_notification(title, message)
            logger.info(f"Sent recovery notification: {message}")

        return success

    def send_custom_notification(self, title: str, message: str) -> bool:
        """
        Send a custom notification

        Args:
            title: Notification title
            message: Notification message

        Returns:
            True if notification was sent
        """
        if not self.enabled:
            return False

        success = self._send_macos_notification(title, message)

        if success:
            self._log_notification(title, message)

        return success

    def _send_macos_notification(self, title: str, message: str) -> bool:
        """
        Send a notification using macOS notification center via osascript

        Args:
            title: Notification title
            message: Notification message

        Returns:
            True if successful, False otherwise
        """
        try:
            # Escape backslashes and quotes for AppleScript double-quoted strings
            title = title.replace('\\', '\\\\').replace('"', '\\"')
            message = message.replace('\\', '\\\\').replace('"', '\\"')

            # Use osascript to send notification
            script = f'display notification "{message}" with title "{title}" sound name "Submarine"'

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                timeout=5
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.error("Notification command timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def _log_notification(self, title: str, message: str):
        """Log notification to history file"""
        try:
            # Load existing history
            history = []
            if self.notification_history_file.exists():
                with open(self.notification_history_file, 'r') as f:
                    history = json.load(f)

            # Add new entry
            history.append({
                'timestamp': datetime.now().isoformat(),
                'title': title,
                'message': message
            })

            # Keep only last 50 notifications
            history = history[-50:]

            # Save history
            with open(self.notification_history_file, 'w') as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to log notification: {e}")

    def get_notification_history(self, limit: int = 20) -> list:
        """
        Get recent notification history

        Args:
            limit: Maximum number of notifications to return

        Returns:
            List of notification dictionaries
        """
        try:
            if self.notification_history_file.exists():
                with open(self.notification_history_file, 'r') as f:
                    history = json.load(f)
                return history[-limit:]
            return []
        except Exception as e:
            logger.error(f"Failed to read notification history: {e}")
            return []

    def enable_notifications(self):
        """Enable notifications"""
        self.enabled = True
        logger.info("Notifications enabled")

    def disable_notifications(self):
        """Disable notifications"""
        self.enabled = False
        logger.info("Notifications disabled")

    def is_enabled(self) -> bool:
        """Check if notifications are enabled"""
        return self.enabled

    def set_min_interval_minutes(self, minutes: int):
        """
        Set minimum interval between notifications

        Args:
            minutes: Minimum minutes between notifications (1-120)
        """
        if 1 <= minutes <= 120:
            self.min_notification_interval = timedelta(minutes=minutes)
            logger.info(f"Notification interval set to {minutes} minutes")
        else:
            logger.warning(f"Invalid interval: {minutes} (must be 1-120)")


# Singleton instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get the singleton notification manager instance"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


# Testing function
def test_notification():
    """Test notification system"""
    manager = get_notification_manager()
    manager.send_slowdown_notification(
        download_speed=8.5,
        upload_speed=2.3,
        duration_minutes=5,
        primary_cause="WiFi signal degradation"
    )


if __name__ == "__main__":
    # Test when run directly
    logging.basicConfig(level=logging.INFO)
    test_notification()
