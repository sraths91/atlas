"""
Network Analysis Settings Manager
Stores and manages customizable thresholds for network analysis
"""

import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class NetworkAnalysisSettings:
    """Manages network analysis threshold settings"""

    DEFAULT_SETTINGS = {
        "slow_download_threshold": 20.0,  # Mbps
        "slow_upload_threshold": 5.0,  # Mbps
        "high_ping_threshold": 100.0,  # ms
        "consecutive_slow_count": 3,  # Number of consecutive slow tests
    }

    def __init__(self, settings_file: Optional[str] = None):
        """
        Initialize settings manager

        Args:
            settings_file: Path to settings JSON file (default: ~/.config/atlas-agent/network_analysis_settings.json)
        """
        if settings_file is None:
            config_dir = Path.home() / ".config" / "atlas-agent"
            config_dir.mkdir(parents=True, exist_ok=True)
            settings_file = config_dir / "network_analysis_settings.json"

        self.settings_file = Path(settings_file)
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or return defaults"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new settings
                    settings = self.DEFAULT_SETTINGS.copy()
                    settings.update(loaded)
                    logger.info(f"Loaded network analysis settings from {self.settings_file}")
                    return settings
            except Exception as e:
                logger.warning(f"Failed to load settings from {self.settings_file}: {e}")
                return self.DEFAULT_SETTINGS.copy()
        else:
            logger.info("Using default network analysis settings")
            return self.DEFAULT_SETTINGS.copy()

    def _save_settings(self) -> bool:
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.info(f"Saved network analysis settings to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings to {self.settings_file}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Set a setting value and save to file

        Args:
            key: Setting key
            value: Setting value

        Returns:
            True if saved successfully
        """
        self.settings[key] = value
        return self._save_settings()

    def update(self, settings_dict: Dict[str, Any]) -> bool:
        """
        Update multiple settings at once

        Args:
            settings_dict: Dictionary of settings to update

        Returns:
            True if saved successfully
        """
        self.settings.update(settings_dict)
        return self._save_settings()

    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults"""
        self.settings = self.DEFAULT_SETTINGS.copy()
        return self._save_settings()

    def get_all(self) -> Dict[str, Any]:
        """Get all current settings"""
        return self.settings.copy()

    def validate_settings(self, settings_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate settings before applying

        Args:
            settings_dict: Settings to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate slow_download_threshold
        if "slow_download_threshold" in settings_dict:
            value = settings_dict["slow_download_threshold"]
            if not isinstance(value, (int, float)) or value <= 0 or value > 10000:
                return False, "Download threshold must be between 0 and 10000 Mbps"

        # Validate slow_upload_threshold
        if "slow_upload_threshold" in settings_dict:
            value = settings_dict["slow_upload_threshold"]
            if not isinstance(value, (int, float)) or value <= 0 or value > 10000:
                return False, "Upload threshold must be between 0 and 10000 Mbps"

        # Validate high_ping_threshold
        if "high_ping_threshold" in settings_dict:
            value = settings_dict["high_ping_threshold"]
            if not isinstance(value, (int, float)) or value <= 0 or value > 10000:
                return False, "Ping threshold must be between 0 and 10000 ms"

        # Validate consecutive_slow_count
        if "consecutive_slow_count" in settings_dict:
            value = settings_dict["consecutive_slow_count"]
            if not isinstance(value, int) or value < 1 or value > 20:
                return False, "Consecutive count must be between 1 and 20"

        return True, None


# Singleton instance
_settings_instance: Optional[NetworkAnalysisSettings] = None
_settings_lock = threading.Lock()


def get_settings() -> NetworkAnalysisSettings:
    """Get the singleton settings instance (thread-safe)"""
    global _settings_instance
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                _settings_instance = NetworkAnalysisSettings()
    return _settings_instance
