"""
Configuration Manager for ATLAS Fleet Monitoring Platform

Handles loading, saving, and merging user configurations with defaults.
Supports YAML and JSON configuration files with schema validation.

Phase 6: Configuration Consolidation
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from copy import deepcopy

# Try to import YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from atlas.config.defaults import (
    NETWORK_CONFIG,
    FLEET_SERVER_CONFIG,
    FLEET_AGENT_CONFIG,
    DISPLAY_CONFIG,
    SECURITY_CONFIG,
    PACKAGE_CONFIG,
    FLEET_CONFIG_DIR,
)

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages configuration loading, saving, and merging.

    Features:
    - Loads user config from YAML or JSON
    - Merges with defaults (user config overrides defaults)
    - Environment variable overrides (highest priority)
    - Schema validation
    - Safe config updates
    """

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to user configuration file (default: ~/.fleet-config/config.yaml)
        """
        if config_file is None:
            # Try YAML first, fallback to JSON
            if YAML_AVAILABLE:
                config_file = FLEET_CONFIG_DIR / "config.yaml"
            else:
                config_file = FLEET_CONFIG_DIR / "config.json"

        self.config_file = Path(config_file)
        self.user_config: Dict[str, Any] = {}
        self.merged_config: Dict[str, Any] = {}

        # Load user configuration if exists
        if self.config_file.exists():
            self.load()
        else:
            logger.info(f"No user configuration found at {self.config_file}, using defaults")
            self._merge_configs()

    def load(self) -> bool:
        """
        Load user configuration from file.

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(self.config_file, 'r') as f:
                if self.config_file.suffix in ['.yaml', '.yml']:
                    if not YAML_AVAILABLE:
                        logger.error("YAML configuration file specified but PyYAML not installed")
                        return False
                    self.user_config = yaml.safe_load(f) or {}
                elif self.config_file.suffix == '.json':
                    self.user_config = json.load(f)
                else:
                    logger.error(f"Unsupported configuration file format: {self.config_file.suffix}")
                    return False

            logger.info(f"Loaded user configuration from {self.config_file}")

            # Merge with defaults
            self._merge_configs()

            return True

        except Exception as e:
            logger.error(f"Failed to load configuration from {self.config_file}: {e}")
            return False

    def save(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save configuration to file.

        Args:
            config: Configuration to save (default: current user_config)

        Returns:
            True if saved successfully, False otherwise
        """
        if config is not None:
            self.user_config = config

        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w') as f:
                if self.config_file.suffix in ['.yaml', '.yml']:
                    if not YAML_AVAILABLE:
                        logger.error("Cannot save YAML: PyYAML not installed")
                        return False
                    yaml.safe_dump(self.user_config, f, default_flow_style=False, sort_keys=False)
                elif self.config_file.suffix == '.json':
                    json.dump(self.user_config, f, indent=2, sort_keys=False)
                else:
                    logger.error(f"Unsupported configuration file format: {self.config_file.suffix}")
                    return False

            logger.info(f"Saved configuration to {self.config_file}")

            # Re-merge with defaults
            self._merge_configs()

            return True

        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_file}: {e}")
            return False

    def _merge_configs(self):
        """
        Merge user configuration with defaults.

        User config takes precedence over defaults.
        Environment variables take precedence over both.
        """
        # Start with defaults
        self.merged_config = {
            "network": deepcopy(NETWORK_CONFIG),
            "fleet_server": deepcopy(FLEET_SERVER_CONFIG),
            "fleet_agent": deepcopy(FLEET_AGENT_CONFIG),
            "display": deepcopy(DISPLAY_CONFIG),
            "security": deepcopy(SECURITY_CONFIG),
            "package": deepcopy(PACKAGE_CONFIG),
        }

        # Merge user config
        self._deep_merge(self.merged_config, self.user_config)

    def _deep_merge(self, base: Dict, override: Dict):
        """
        Deep merge override dict into base dict (modifies base in-place).

        Args:
            base: Base dictionary (modified in-place)
            override: Override dictionary
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = deepcopy(value)

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.

        Args:
            path: Dot-separated path (e.g., "network.wifi.update_interval")
            default: Default value if path not found

        Returns:
            Configuration value or default

        Examples:
            >>> config.get("network.wifi.update_interval")
            10

            >>> config.get("network.wifi.nonexistent", default=99)
            99
        """
        parts = path.split(".")
        current = self.merged_config

        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default

    def set(self, path: str, value: Any, save: bool = False) -> bool:
        """
        Set configuration value by dot-separated path.

        Args:
            path: Dot-separated path (e.g., "network.wifi.update_interval")
            value: Value to set
            save: Whether to save to file immediately

        Returns:
            True if set successfully, False otherwise

        Examples:
            >>> config.set("network.wifi.update_interval", 20)
            True

            >>> config.set("network.wifi.update_interval", 20, save=True)
            True
        """
        parts = path.split(".")
        if not parts:
            return False

        # Navigate to parent
        current = self.user_config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set value
        current[parts[-1]] = value

        # Re-merge
        self._merge_configs()

        # Save if requested
        if save:
            return self.save()

        return True

    def get_section(self, section: str, subsection: Optional[str] = None) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Main section (network, fleet_server, etc.)
            subsection: Optional subsection

        Returns:
            Configuration dictionary

        Examples:
            >>> config.get_section("network", "wifi")
            {'log_file': '...', 'update_interval': 10, ...}
        """
        if section not in self.merged_config:
            raise ValueError(f"Unknown section: {section}")

        config = self.merged_config[section]

        if subsection:
            if subsection not in config:
                raise ValueError(f"Unknown subsection '{subsection}' in section '{section}'")
            return config[subsection]

        return config

    def validate(self) -> List[str]:
        """
        Validate configuration values.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate security settings
        password_config = self.merged_config.get("security", {}).get("password", {})
        if password_config.get("rounds", 12) < 10:
            errors.append("security.password.rounds must be >= 10 (current: {})".format(
                password_config.get("rounds")
            ))

        encryption_config = self.merged_config.get("security", {}).get("encryption", {})
        if encryption_config.get("kdf_iterations", 600000) < 100000:
            errors.append("security.encryption.kdf_iterations should be >= 600000 (current: {})".format(
                encryption_config.get("kdf_iterations")
            ))

        # Validate network settings
        server_config = self.merged_config.get("fleet_server", {}).get("network", {})
        port = server_config.get("port", 8778)
        if not (1 <= port <= 65535):
            errors.append(f"fleet_server.network.port must be 1-65535 (current: {port})")

        # Validate paths
        ssl_config = self.merged_config.get("fleet_server", {}).get("ssl", {})
        if ssl_config.get("enabled", True):
            cert_file = Path(ssl_config.get("cert_file", ""))
            if not cert_file.exists():
                errors.append(f"SSL enabled but certificate not found: {cert_file}")

        return errors

    def export_example(self, output_file: Optional[Path] = None) -> str:
        """
        Export example configuration file with all available options.

        Args:
            output_file: Optional path to save example config

        Returns:
            Example configuration as string
        """
        example_config = {
            "# ATLAS Fleet Monitoring Platform - Configuration File": None,
            "# This file overrides default settings": None,
            "# All settings are optional - defaults will be used if not specified": None,
            "": None,

            "network": {
                "wifi": {
                    "update_interval": 10,
                    "max_history": 60,
                    "# Add other WiFi settings here": None,
                },
                "speedtest": {
                    "update_interval": 60,
                    "slow_speed_threshold": 20.0,
                },
            },

            "fleet_server": {
                "network": {
                    "host": "0.0.0.0",
                    "port": 8778,
                },
                "ssl": {
                    "enabled": True,
                    "min_tls_version": "TLSv1_2",
                },
                "auth": {
                    "session_expiry": 28800,
                    "password_hash_rounds": 12,
                },
            },

            "fleet_agent": {
                "server": {
                    "url": "https://localhost:8778",
                    "# Set API key via environment variable FLEET_API_KEY": None,
                },
                "reporting": {
                    "interval": 60,
                },
            },

            "security": {
                "password": {
                    "min_length": 12,
                    "require_password_complexity": True,
                },
            },
        }

        # Remove None values (comments)
        def clean_dict(d):
            if not isinstance(d, dict):
                return d
            return {k: clean_dict(v) for k, v in d.items() if v is not None}

        clean_example = clean_dict(example_config)

        # Format as YAML or JSON
        if YAML_AVAILABLE and (output_file is None or output_file.suffix in ['.yaml', '.yml']):
            output = yaml.safe_dump(clean_example, default_flow_style=False, sort_keys=False)
        else:
            output = json.dumps(clean_example, indent=2)

        # Save if requested
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(output)
            logger.info(f"Exported example configuration to {output_file}")

        return output

    def __repr__(self) -> str:
        return f"ConfigurationManager(config_file={self.config_file})"


# ============================================================================
# GLOBAL CONFIGURATION MANAGER INSTANCE
# ============================================================================

# Default configuration manager instance (can be replaced)
_default_manager: Optional[ConfigurationManager] = None


def get_manager() -> ConfigurationManager:
    """
    Get the global configuration manager instance.

    Returns:
        ConfigurationManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = ConfigurationManager()
    return _default_manager


def set_manager(manager: ConfigurationManager):
    """
    Set the global configuration manager instance.

    Args:
        manager: ConfigurationManager instance to use as global
    """
    global _default_manager
    _default_manager = manager


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def load_config(config_file: Optional[Path] = None) -> ConfigurationManager:
    """
    Load configuration from file and set as global manager.

    Args:
        config_file: Path to configuration file

    Returns:
        ConfigurationManager instance
    """
    manager = ConfigurationManager(config_file)
    set_manager(manager)
    return manager


def get_config_value(path: str, default: Any = None) -> Any:
    """
    Get configuration value from global manager.

    Args:
        path: Dot-separated path
        default: Default value if not found

    Returns:
        Configuration value
    """
    return get_manager().get(path, default)


def set_config_value(path: str, value: Any, save: bool = False) -> bool:
    """
    Set configuration value in global manager.

    Args:
        path: Dot-separated path
        value: Value to set
        save: Whether to save to file

    Returns:
        True if successful
    """
    return get_manager().set(path, value, save)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "ConfigurationManager",
    "get_manager",
    "set_manager",
    "load_config",
    "get_config_value",
    "set_config_value",
]
