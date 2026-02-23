"""
Centralized Configuration Defaults for ATLAS Fleet Monitoring Platform

This module consolidates all hardcoded configuration values from across the codebase
into a single, well-organized source of truth.

Phase 6: Configuration Consolidation
"""
import os
from pathlib import Path
from typing import Dict, Any, List

# ============================================================================
# BASE PATHS
# ============================================================================

# User home directory
HOME_DIR = Path.home()

# Fleet configuration directory
FLEET_CONFIG_DIR = HOME_DIR / ".fleet-config"

# Fleet certificates directory
FLEET_CERT_DIR = HOME_DIR / ".fleet-certs"

# Fleet data directory
FLEET_DATA_DIR = HOME_DIR / ".fleet-data"

# Ensure directories exist with restrictive permissions (owner-only access)
FLEET_CONFIG_DIR.mkdir(mode=0o700, exist_ok=True)
FLEET_CERT_DIR.mkdir(mode=0o700, exist_ok=True)
FLEET_DATA_DIR.mkdir(mode=0o700, exist_ok=True)


# ============================================================================
# PORT CONFIGURATION
# ============================================================================

# Fleet server port (HTTPS)
FLEET_SERVER_PORT = 8778

# Agent widget/dashboard port
AGENT_WIDGET_PORT = 8767


# ============================================================================
# QUERY PARAMETER UTILITIES
# ============================================================================

def safe_int_param(params: dict, key: str, default: int = 24,
                   min_val: int = 1, max_val: int = 8760) -> int:
    """Safely parse an integer query parameter with bounds clamping.

    Args:
        params: Query parameter dict from parse_qs (values are lists)
        key: Parameter name
        default: Default value if missing or invalid
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Clamped integer value, or default on parse failure
    """
    try:
        val = int(params.get(key, [str(default)])[0])
        return max(min_val, min(val, max_val))
    except (ValueError, TypeError, IndexError):
        return default


# ============================================================================
# NETWORK MONITORING CONFIGURATION
# ============================================================================

NETWORK_CONFIG: Dict[str, Any] = {
    # WiFi Monitor Configuration
    "wifi": {
        "log_file": str(HOME_DIR / "wifi_quality.csv"),
        "events_file": str(HOME_DIR / "wifi_events.csv"),
        "diagnostics_file": str(HOME_DIR / "network_diagnostics.csv"),
        "update_interval": 10,  # seconds
        "max_history": 60,  # entries to keep in memory
        "retention_days": 7,  # days to keep CSV logs
        "external_ping_targets": [
            ("8.8.8.8", "Google DNS"),
            ("1.1.1.1", "Cloudflare DNS"),
        ],
        "dns_test_domains": ["google.com", "cloudflare.com", "apple.com"],
        "signal_thresholds": {
            "excellent": -50,  # dBm
            "good": -60,
            "fair": -70,
            "poor": -80,
        },
        "quality_thresholds": {
            "packet_loss_warning": 5.0,  # percent
            "packet_loss_critical": 20.0,
            "latency_warning": 100,  # ms
            "latency_critical": 500,
        },
    },

    # SpeedTest Monitor Configuration
    "speedtest": {
        "log_file": str(HOME_DIR / "speedtest_history.csv"),
        "update_interval": 60,  # seconds (1 minute)
        "max_history": 20,  # entries to keep in memory
        "retention_days": 7,  # days to keep CSV logs
        "slow_speed_threshold": 20.0,  # Mbps
        "consecutive_slow_trigger": 5,  # consecutive slow tests before alert
        "slow_alert_cooldown": 300,  # seconds (5 minutes)
        "test_timeout": 60,  # seconds
    },

    # Ping Monitor Configuration
    "ping": {
        "log_file": str(HOME_DIR / "ping_history.csv"),
        "update_interval": 5,  # seconds
        "max_history": 100,  # entries to keep in memory
        "retention_days": 7,  # days to keep CSV logs
        "default_targets": [
            ("8.8.8.8", "Google DNS"),
            ("1.1.1.1", "Cloudflare DNS"),
        ],
        "ping_count": 3,
        "ping_timeout": 2,  # seconds
        "packet_loss_threshold": 10.0,  # percent
        "latency_threshold": 100,  # ms
    },

    # Network Analyzer Configuration
    "analyzer": {
        "analysis_window": 3600,  # seconds (1 hour)
        "issue_detection_threshold": 5,  # consecutive issues before reporting
    },
}


# ============================================================================
# FLEET SERVER CONFIGURATION
# ============================================================================

FLEET_SERVER_CONFIG: Dict[str, Any] = {
    # Server Network Settings
    "network": {
        "host": "0.0.0.0",  # Listen on all interfaces
        "port": 8778,
        "backlog": 5,  # Number of queued connections
    },

    # SSL/TLS Settings
    "ssl": {
        "enabled": True,
        "cert_file": str(FLEET_CERT_DIR / "cert.pem"),
        "key_file": str(FLEET_CERT_DIR / "privkey.pem"),
        "min_tls_version": "TLSv1_2",  # TLS 1.2 minimum (SECURITY)
        "max_tls_version": "TLSv1_3",  # TLS 1.3 maximum
        "verify_client_certs": False,  # Set True for mutual TLS
    },

    # Authentication Settings
    "auth": {
        "api_key_header": "X-API-Key",
        "session_cookie_name": "fleet_session",
        "session_expiry": 28800,  # seconds (8 hours)
        "password_hash_rounds": 12,  # bcrypt rounds (2^12 = 4096 iterations)
        "min_password_length": 12,
        "require_password_complexity": True,
    },

    # Data Storage Settings
    "storage": {
        "data_dir": str(FLEET_DATA_DIR),
        "persistence_file": str(FLEET_DATA_DIR / "fleet_data.json"),
        "encrypted_persistence_file": str(FLEET_DATA_DIR / "fleet_data.enc"),
        "max_history_per_machine": 100,  # data points
        "max_command_queue_size": 50,
        "data_retention_days": 30,
    },

    # Agent Communication Settings
    "agent": {
        "report_interval": 60,  # seconds (how often agents should report)
        "health_check_timeout": 300,  # seconds (5 minutes)
        "offline_threshold": 180,  # seconds (3 minutes)
        "max_report_size": 10485760,  # bytes (10 MB)
    },

    # Request Body Limits
    "body_limits": {
        "max_body_size": 10485760,  # bytes (10 MB) - reject requests larger than this
        "max_json_body_size": 5242880,  # bytes (5 MB) - for JSON API endpoints
    },

    # End-to-End Encryption (E2EE) Settings
    "e2ee": {
        "enabled": False,  # Set True to require E2EE
        "key_rotation_interval": 7776000,  # seconds (90 days)
        "encryption_key_file": str(FLEET_CONFIG_DIR / "encryption_key.key"),
    },

    # Cluster/HA Settings
    "cluster": {
        "enabled": False,
        "mode": "standalone",  # "standalone", "primary", "replica"
        "secret_file": str(FLEET_CONFIG_DIR / "cluster_secret.key"),
        "min_secret_length": 32,  # bytes (256 bits)
        "replay_window": 30,  # seconds (SECURITY: reduced from 300)
        "sync_interval": 10,  # seconds
        "health_check_interval": 5,  # seconds
    },

    # Rate Limiting (Future Enhancement)
    "rate_limit": {
        "enabled": False,
        "requests_per_minute": 60,
        "burst_size": 10,
    },

    # Logging Settings
    "logging": {
        "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "log_file": str(FLEET_DATA_DIR / "fleet_server.log"),
        "max_log_size": 10485760,  # bytes (10 MB)
        "backup_count": 5,
    },
}


# ============================================================================
# FLEET AGENT CONFIGURATION
# ============================================================================

FLEET_AGENT_CONFIG: Dict[str, Any] = {
    # Agent Identity
    "identity": {
        "machine_id": None,  # Auto-generated on first run
        "organization_name": "ATLAS Fleet",
    },

    # Server Connection
    "server": {
        "url": "https://localhost:8778",
        "api_key": None,  # Set via environment or config file
        "verify_ssl": True,
        "timeout": 30,  # seconds
    },

    # Reporting Settings
    "reporting": {
        "interval": 60,  # seconds
        "retry_attempts": 3,
        "retry_backoff": 2.0,  # exponential backoff multiplier
        "max_retry_delay": 300,  # seconds (5 minutes)
    },

    # Data Collection
    "collection": {
        "include_widgets": True,
        "widget_log_max_size": 1000,  # lines
        "collect_system_info": True,
        "collect_network_info": True,
    },

    # End-to-End Encryption
    "e2ee": {
        "enabled": False,
        "encryption_key": None,  # Set via config
    },

    # Daemon Settings
    "daemon": {
        "pid_file": "/tmp/fleet_agent.pid",
        "log_file": str(HOME_DIR / "fleet_agent.log"),
        "working_directory": str(HOME_DIR),
    },
}


# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================

DISPLAY_CONFIG: Dict[str, Any] = {
    # Layout Manager
    "layout": {
        "default_layout": "full",  # full, compact, minimal
        "refresh_interval": 1000,  # milliseconds
        "transition_duration": 300,  # milliseconds
    },

    # Theme Settings
    "theme": {
        "default_theme": "dark",  # dark, light, auto
        "color_scheme": "blue",  # blue, green, red, purple
        "font_family": "San Francisco, -apple-system, BlinkMacSystemFont, Helvetica, Arial",
        "font_size_base": 14,  # pixels
    },

    # Widget Server
    "widget_server": {
        "host": "127.0.0.1",
        "port": 8080,
        "auto_reload": True,
    },

    # Web Viewer
    "web_viewer": {
        "default_view": "dashboard",
        "auto_refresh": True,
        "refresh_interval": 5000,  # milliseconds
    },
}


# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

SECURITY_CONFIG: Dict[str, Any] = {
    # Password Hashing (bcrypt)
    "password": {
        "algorithm": "bcrypt",
        "rounds": 12,  # 2^12 = 4,096 iterations
        "min_length": 12,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_digits": True,
        "require_special": True,
    },

    # Encryption (Configuration files)
    "encryption": {
        "algorithm": "fernet",  # AES-128-CBC + HMAC-SHA256
        "kdf": "pbkdf2hmac",
        "kdf_iterations": 600000,  # OWASP recommendation for PBKDF2
        "kdf_hash": "sha256",
        "salt_length": 32,  # bytes
        "key_length": 32,  # bytes
    },

    # Session Management
    "session": {
        "token_length": 32,  # bytes (256 bits)
        "token_algorithm": "urlsafe_base64",
        "expiry": 28800,  # seconds (8 hours)
        "cookie_secure": True,
        "cookie_httponly": True,
        "cookie_samesite": "Strict",
    },

    # Brute Force Protection
    "brute_force": {
        "enabled": True,
        "max_attempts": 5,
        "lockout_duration": 1800,  # seconds (30 minutes)
        "cleanup_interval": 3600,  # seconds (1 hour)
    },

    # Certificate Management
    "certificates": {
        "key_size": 4096,  # bits (SECURITY: upgraded from 2048)
        "validity_days": 365,
        "auto_renewal": True,
        "renewal_before_days": 30,
        "encrypt_private_keys": True,
    },

    # Content Security Policy
    # SECURITY NOTE: 'unsafe-inline' is used because the dashboard generates
    # dynamic inline scripts/styles. For production deployments requiring
    # stricter CSP, implement nonce-based CSP by:
    # 1. Generate a random nonce per request
    # 2. Add nonce to all inline <script> and <style> tags
    # 3. Replace 'unsafe-inline' with 'nonce-{random}'
    # See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
    "csp": {
        "enabled": True,
        "default_src": ["'self'"],
        "script_src": ["'self'", "'unsafe-inline'"],  # SECURITY: Consider nonce-based CSP
        "style_src": ["'self'", "'unsafe-inline'"],   # SECURITY: Consider nonce-based CSP
        "img_src": ["'self'", "data:"],
        "font_src": ["'self'"],
        "connect_src": ["'self'", "wss:", "ws:"],  # Allow WebSocket connections
        "frame_ancestors": ["'none'"],  # Prevent framing (clickjacking)
    },

    # Security Headers
    "headers": {
        "x_frame_options": "DENY",
        "x_content_type_options": "nosniff",
        "x_xss_protection": "1; mode=block",
        "strict_transport_security": "max-age=31536000; includeSubDomains",
        "referrer_policy": "no-referrer",
    },
}


# ============================================================================
# PACKAGE BUILDER CONFIGURATION
# ============================================================================

PACKAGE_CONFIG: Dict[str, Any] = {
    # Build Settings
    "build": {
        "output_dir": str(HOME_DIR / "Desktop" / "fleet-installers"),
        "temp_dir": "/tmp/fleet-build",
        "identifier_prefix": "com.atlas.fleet",
    },

    # Package Types
    "standalone": {
        "name": "ATLAS Fleet Monitor",
        "version": "1.0.0",
        "install_location": "/Applications/ATLAS Fleet Monitor.app",
    },

    "agent": {
        "name": "ATLAS Fleet Agent",
        "version": "1.0.0",
        "install_location": "/Library/Application Support/ATLASFleetAgent",
        "launch_daemon_label": "com.atlas.fleet.agent",
    },

    "cluster": {
        "name": "ATLAS Fleet Cluster Node",
        "version": "1.0.0",
        "install_location": "/Library/Application Support/ATLASFleetCluster",
    },
}


# ============================================================================
# ENVIRONMENT VARIABLE OVERRIDES
# ============================================================================

def get_env_override(key: str, default: Any, value_type: type = str) -> Any:
    """
    Get configuration value from environment variable if set, otherwise return default.

    Args:
        key: Environment variable name (e.g., "FLEET_SERVER_PORT")
        default: Default value if env var not set
        value_type: Type to cast the value to (str, int, bool, float)

    Returns:
        Environment variable value (casted to value_type) or default
    """
    value = os.environ.get(key)
    if value is None:
        return default

    try:
        if value_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        return value_type(value)
    except (ValueError, AttributeError):
        return default


# Apply environment variable overrides
FLEET_SERVER_CONFIG["network"]["port"] = get_env_override(
    "FLEET_SERVER_PORT",
    FLEET_SERVER_CONFIG["network"]["port"],
    int
)

FLEET_SERVER_CONFIG["ssl"]["enabled"] = get_env_override(
    "FLEET_SSL_ENABLED",
    FLEET_SERVER_CONFIG["ssl"]["enabled"],
    bool
)

FLEET_AGENT_CONFIG["server"]["url"] = get_env_override(
    "FLEET_SERVER_URL",
    FLEET_AGENT_CONFIG["server"]["url"]
)

FLEET_AGENT_CONFIG["server"]["api_key"] = get_env_override(
    "FLEET_API_KEY",
    FLEET_AGENT_CONFIG["server"]["api_key"]
)

SECURITY_CONFIG["password"]["min_length"] = get_env_override(
    "FLEET_MIN_PASSWORD_LENGTH",
    SECURITY_CONFIG["password"]["min_length"],
    int
)


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_configuration() -> List[str]:
    """
    Validate configuration values and return list of warnings/errors.

    Returns:
        List of validation messages (empty if all valid)
    """
    issues = []

    # Validate security settings
    if SECURITY_CONFIG["password"]["rounds"] < 10:
        issues.append("WARNING: bcrypt rounds < 10 (insecure, should be >= 12)")

    if SECURITY_CONFIG["encryption"]["kdf_iterations"] < 100000:
        issues.append("WARNING: KDF iterations < 100000 (OWASP recommends >= 600000)")

    if FLEET_SERVER_CONFIG["cluster"]["min_secret_length"] < 32:
        issues.append("ERROR: Cluster secret minimum length < 32 bytes (insecure)")

    # Validate network settings
    if not (1024 <= FLEET_SERVER_CONFIG["network"]["port"] <= 65535):
        issues.append(f"WARNING: Fleet server port {FLEET_SERVER_CONFIG['network']['port']} outside typical range (1024-65535)")

    # Validate paths
    cert_file = Path(FLEET_SERVER_CONFIG["ssl"]["cert_file"])
    if FLEET_SERVER_CONFIG["ssl"]["enabled"] and not cert_file.exists():
        issues.append(f"WARNING: SSL enabled but certificate file not found: {cert_file}")

    return issues


# Run validation on import (warnings only, doesn't block)
_validation_issues = validate_configuration()
if _validation_issues:
    import logging
    logger = logging.getLogger(__name__)
    for issue in _validation_issues:
        if issue.startswith("ERROR"):
            logger.error(issue)
        else:
            logger.warning(issue)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_config(section: str, subsection: str = None) -> Dict[str, Any]:
    """
    Get configuration section.

    Args:
        section: Main configuration section (network, fleet_server, fleet_agent, etc.)
        subsection: Optional subsection name

    Returns:
        Configuration dictionary

    Examples:
        >>> get_config("network", "wifi")
        {'log_file': '/Users/user/wifi_quality.csv', ...}

        >>> get_config("fleet_server")
        {'network': {...}, 'ssl': {...}, ...}
    """
    config_map = {
        "network": NETWORK_CONFIG,
        "fleet_server": FLEET_SERVER_CONFIG,
        "fleet_agent": FLEET_AGENT_CONFIG,
        "display": DISPLAY_CONFIG,
        "security": SECURITY_CONFIG,
        "package": PACKAGE_CONFIG,
    }

    if section not in config_map:
        raise ValueError(f"Unknown configuration section: {section}")

    config = config_map[section]

    if subsection:
        if subsection not in config:
            raise ValueError(f"Unknown subsection '{subsection}' in section '{section}'")
        return config[subsection]

    return config


def get_value(path: str, default: Any = None) -> Any:
    """
    Get configuration value by dot-separated path.

    Args:
        path: Dot-separated path (e.g., "network.wifi.update_interval")
        default: Default value if path not found

    Returns:
        Configuration value or default

    Examples:
        >>> get_value("network.wifi.update_interval")
        10

        >>> get_value("network.wifi.nonexistent", default=99)
        99
    """
    parts = path.split(".")
    if len(parts) < 2:
        raise ValueError(f"Path must have at least 2 parts: {path}")

    try:
        config = get_config(parts[0], parts[1] if len(parts) > 1 else None)

        # Navigate remaining parts
        for part in parts[2:]:
            config = config[part]

        return config
    except (KeyError, ValueError):
        return default


# ============================================================================
# EXPORTS
# ============================================================================

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
