"""
Configuration Package for ATLAS Fleet Monitoring Platform

Provides centralized configuration management with environment variable overrides
and validation.

Phase 6: Configuration Consolidation

Usage:
    from atlas.config import get_config, get_value, FLEET_SERVER_CONFIG

    # Get entire section
    wifi_config = get_config("network", "wifi")
    print(wifi_config["update_interval"])  # 10

    # Get specific value by path
    update_interval = get_value("network.wifi.update_interval")  # 10
    port = get_value("fleet_server.network.port")  # 8778

    # Use configuration dictionaries directly
    print(FLEET_SERVER_CONFIG["network"]["port"])  # 8778
"""

from atlas.config.defaults import (
    # Configuration dictionaries
    NETWORK_CONFIG,
    FLEET_SERVER_CONFIG,
    FLEET_AGENT_CONFIG,
    DISPLAY_CONFIG,
    SECURITY_CONFIG,
    PACKAGE_CONFIG,

    # Path constants
    HOME_DIR,
    FLEET_CONFIG_DIR,
    FLEET_CERT_DIR,
    FLEET_DATA_DIR,

    # Helper functions
    get_config,
    get_value,
    get_env_override,
    validate_configuration,
)

__all__ = [
    # Configuration dictionaries
    "NETWORK_CONFIG",
    "FLEET_SERVER_CONFIG",
    "FLEET_AGENT_CONFIG",
    "DISPLAY_CONFIG",
    "SECURITY_CONFIG",
    "PACKAGE_CONFIG",

    # Path constants
    "HOME_DIR",
    "FLEET_CONFIG_DIR",
    "FLEET_CERT_DIR",
    "FLEET_DATA_DIR",

    # Helper functions
    "get_config",
    "get_value",
    "get_env_override",
    "validate_configuration",
]
