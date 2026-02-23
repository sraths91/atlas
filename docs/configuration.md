# ATLAS Fleet Monitoring Platform - Configuration Guide

This guide explains how to configure the ATLAS Fleet Monitoring Platform using centralized configuration management.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration Files](#configuration-files)
4. [Environment Variables](#environment-variables)
5. [Configuration Reference](#configuration-reference)
6. [Programmatic Access](#programmatic-access)
7. [Validation](#validation)
8. [Migration Guide](#migration-guide)

---

## Overview

The ATLAS Fleet Monitoring Platform uses a **three-tier configuration system**:

1. **Default Configuration** - Built-in defaults (lowest priority)
2. **User Configuration File** - YAML or JSON file in `~/.fleet-config/` (medium priority)
3. **Environment Variables** - System environment variables (highest priority)

This allows you to:
- ✅ Use the platform without any configuration (sensible defaults)
- ✅ Override specific settings via configuration file
- ✅ Deploy with environment variables (cloud-friendly)
- ✅ Validate configuration before startup

---

## Quick Start

### Option 1: Use Defaults (No Configuration Needed)

```bash
# Just run the server - it works out of the box
python3 atlas/fleet_server.py
```

### Option 2: Create User Configuration File

```bash
# Create configuration directory
mkdir -p ~/.fleet-config

# Copy example configuration
cp config.example.yaml ~/.fleet-config/config.yaml

# Edit configuration
nano ~/.fleet-config/config.yaml

# Uncomment and modify the values you want to change
```

### Option 3: Use Environment Variables

```bash
# Set environment variables
export FLEET_SERVER_PORT=8778
export FLEET_SSL_ENABLED=true
export FLEET_API_KEY=your_secure_api_key

# Run server
python3 atlas/fleet_server.py
```

---

## Configuration Files

### File Locations

The configuration system looks for user configuration in these locations (in order):

1. `~/.fleet-config/config.yaml` (YAML format, preferred)
2. `~/.fleet-config/config.json` (JSON format, fallback)

**Note**: YAML format requires PyYAML (`pip install pyyaml`)

### File Format

#### YAML Example (`~/.fleet-config/config.yaml`):

```yaml
network:
  wifi:
    update_interval: 15  # Override default (10)
  speedtest:
    update_interval: 120  # Override default (60)

fleet_server:
  network:
    port: 8778
  ssl:
    enabled: true
    min_tls_version: "TLSv1_2"
  auth:
    session_expiry: 28800  # 8 hours

security:
  password:
    min_length: 12
    require_password_complexity: true
```

#### JSON Example (`~/.fleet-config/config.json`):

```json
{
  "network": {
    "wifi": {
      "update_interval": 15
    },
    "speedtest": {
      "update_interval": 120
    }
  },
  "fleet_server": {
    "network": {
      "port": 8778
    },
    "ssl": {
      "enabled": true,
      "min_tls_version": "TLSv1_2"
    }
  }
}
```

### Creating Configuration Files

**Export Example Configuration**:

```python
from atlas.config.manager import ConfigurationManager
from pathlib import Path

manager = ConfigurationManager()
manager.export_example(output_file=Path("~/.fleet-config/config.example.yaml"))
```

---

## Environment Variables

Environment variables provide the **highest priority** configuration and are ideal for:
- Cloud deployments
- Docker containers
- CI/CD pipelines
- Production secrets

### Supported Environment Variables

#### Fleet Server

```bash
# Server network settings
export FLEET_SERVER_PORT=8778

# SSL/TLS settings
export FLEET_SSL_ENABLED=true

# Server URL for agents
export FLEET_SERVER_URL=https://fleet.example.com:8778
```

#### Fleet Agent

```bash
# API key for authentication
export FLEET_API_KEY=your_secure_api_key_here

# Server connection
export FLEET_SERVER_URL=https://fleet.example.com:8778
```

#### Security

```bash
# Password requirements
export FLEET_MIN_PASSWORD_LENGTH=16
```

### Environment Variable Types

The system automatically converts environment variable values to the correct type:

- **Strings**: Used as-is
- **Integers**: Parsed as `int(value)`
- **Floats**: Parsed as `float(value)`
- **Booleans**: "true", "1", "yes", "on" → True; otherwise False

**Example**:
```bash
export FLEET_SERVER_PORT=7777           # Converted to int: 7777
export FLEET_SSL_ENABLED=true           # Converted to bool: True
export FLEET_MIN_PASSWORD_LENGTH=16     # Converted to int: 16
```

---

## Configuration Reference

### Network Monitoring

#### WiFi Monitor

```yaml
network:
  wifi:
    log_file: ~/wifi_quality.csv          # WiFi quality log file
    events_file: ~/wifi_events.csv        # WiFi events log file
    diagnostics_file: ~/network_diagnostics.csv
    update_interval: 10                   # Seconds between checks
    max_history: 60                       # Entries to keep in memory
    retention_days: 7                     # Days to keep CSV logs
```

#### SpeedTest Monitor

```yaml
network:
  speedtest:
    log_file: ~/speedtest_history.csv     # Speed test results log
    update_interval: 60                   # Seconds between tests (1 minute)
    max_history: 20                       # Entries to keep in memory
    retention_days: 7                     # Days to keep CSV logs
    slow_speed_threshold: 20.0            # Mbps - alert threshold
    consecutive_slow_trigger: 5           # Consecutive slow tests before alert
    slow_alert_cooldown: 300              # Seconds between alerts (5 minutes)
```

#### Ping Monitor

```yaml
network:
  ping:
    log_file: ~/ping_history.csv          # Ping results log
    update_interval: 5                    # Seconds between tests
    max_history: 100                      # Entries to keep in memory
    retention_days: 7                     # Days to keep CSV logs
    ping_count: 3                         # Pings per test
    ping_timeout: 2                       # Timeout in seconds
    packet_loss_threshold: 10.0           # Percent - alert threshold
    latency_threshold: 100                # Milliseconds - alert threshold
```

### Fleet Server

#### Network Settings

```yaml
fleet_server:
  network:
    host: "0.0.0.0"                       # Listen on all interfaces
    port: 8778                            # Fleet server port
    backlog: 5                            # Queued connections
```

#### SSL/TLS Settings

```yaml
fleet_server:
  ssl:
    enabled: true                         # Enable HTTPS
    cert_file: ~/.fleet-certs/cert.pem
    key_file: ~/.fleet-certs/privkey.pem
    min_tls_version: "TLSv1_2"            # Minimum TLS 1.2 (SECURITY)
    max_tls_version: "TLSv1_3"            # Maximum TLS 1.3
    verify_client_certs: false            # Mutual TLS (optional)
```

#### Authentication Settings

```yaml
fleet_server:
  auth:
    api_key_header: "X-API-Key"
    session_cookie_name: "fleet_session"
    session_expiry: 28800                 # 8 hours
    password_hash_rounds: 12              # bcrypt rounds (2^12 = 4096)
    min_password_length: 12
    require_password_complexity: true
```

#### Storage Settings

```yaml
fleet_server:
  storage:
    data_dir: ~/.fleet-data
    persistence_file: ~/.fleet-data/fleet_data.json
    encrypted_persistence_file: ~/.fleet-data/fleet_data.enc
    max_history_per_machine: 100          # Data points per machine
    max_command_queue_size: 50
    data_retention_days: 30
```

### Security

#### Password Settings

```yaml
security:
  password:
    algorithm: "bcrypt"
    rounds: 12                            # 2^12 = 4,096 iterations
    min_length: 12
    require_uppercase: true
    require_lowercase: true
    require_digits: true
    require_special: true
```

#### Encryption Settings

```yaml
security:
  encryption:
    algorithm: "fernet"                   # AES-128-CBC + HMAC-SHA256
    kdf: "pbkdf2hmac"
    kdf_iterations: 600000                # OWASP recommendation
    kdf_hash: "sha256"
    salt_length: 32                       # Bytes
    key_length: 32                        # Bytes
```

#### Session Settings

```yaml
security:
  session:
    token_length: 32                      # Bytes (256 bits)
    token_algorithm: "urlsafe_base64"
    expiry: 28800                         # Seconds (8 hours)
    cookie_secure: true                   # HTTPS only
    cookie_httponly: true                 # No JavaScript access
    cookie_samesite: "Strict"             # CSRF protection
```

---

## Programmatic Access

### Basic Configuration Access

```python
from atlas.config import get_config, get_value

# Get entire section
wifi_config = get_config("network", "wifi")
print(wifi_config["update_interval"])  # 10

# Get specific value using dot notation
port = get_value("fleet_server.network.port")  # 8778
ssl_enabled = get_value("fleet_server.ssl.enabled")  # True

# Get with default fallback
custom = get_value("network.wifi.custom_setting", default=42)  # 42
```

### Using Configuration Manager

```python
from atlas.config.manager import ConfigurationManager

# Load configuration (auto-detects config.yaml or config.json)
manager = ConfigurationManager()

# Get values
wifi_interval = manager.get("network.wifi.update_interval")
server_port = manager.get("fleet_server.network.port")

# Set values
manager.set("network.wifi.update_interval", 20)

# Save to file
manager.save()

# Get entire section
fleet_server_config = manager.get_section("fleet_server")
```

### Direct Dictionary Access

```python
from atlas.config import NETWORK_CONFIG, FLEET_SERVER_CONFIG

# Access configuration dictionaries directly
print(NETWORK_CONFIG["wifi"]["update_interval"])  # 10
print(FLEET_SERVER_CONFIG["network"]["port"])  # 8778
```

---

## Validation

### Automatic Validation

Configuration is automatically validated on import:

```python
from atlas.config import validate_configuration

# Validate configuration
issues = validate_configuration()

if issues:
    for issue in issues:
        if issue.startswith("ERROR"):
            print(f"❌ {issue}")
        else:
            print(f"⚠️  {issue}")
```

### Common Validation Checks

- **bcrypt rounds**: Must be ≥ 10 (recommended ≥ 12)
- **KDF iterations**: Must be ≥ 100,000 (recommended ≥ 600,000)
- **Cluster secret length**: Must be ≥ 32 bytes (256 bits)
- **Server port**: Must be 1-65535
- **SSL certificate**: Must exist if SSL enabled

### Example Validation Output

```
WARNING: bcrypt rounds < 10 (insecure, should be >= 12)
ERROR: Cluster secret minimum length < 32 bytes (insecure)
WARNING: SSL enabled but certificate file not found: /path/to/cert.pem
```

---

## Migration Guide

### Migrating from Hardcoded Values

**Before (Hardcoded)**:
```python
# In wifi_widget.py
LOG_FILE = os.path.expanduser('~/wifi_quality.csv')
UPDATE_INTERVAL = 10
```

**After (Centralized)**:
```python
# In wifi_widget.py
from atlas.config import get_value

LOG_FILE = get_value("network.wifi.log_file")
UPDATE_INTERVAL = get_value("network.wifi.update_interval")
```

### Migrating Deployments

**Before**:
```bash
# Edit source code to change port
nano atlas/fleet_server.py
# Change: port = 8778
```

**After**:
```bash
# Set environment variable
export FLEET_SERVER_PORT=7777
python3 atlas/fleet_server.py
```

### Creating User Configuration

**Step 1**: Export example configuration
```bash
python3 -c "
from atlas.config.manager import ConfigurationManager
from pathlib import Path
manager = ConfigurationManager()
manager.export_example(Path.home() / '.fleet-config' / 'config.yaml')
"
```

**Step 2**: Edit configuration
```bash
nano ~/.fleet-config/config.yaml
```

**Step 3**: Verify configuration
```python
from atlas.config.manager import ConfigurationManager

manager = ConfigurationManager()
errors = manager.validate()

if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✅ Configuration valid!")
```

---

## Best Practices

### 1. Use Environment Variables for Secrets

```bash
# ✅ GOOD: Store API keys in environment
export FLEET_API_KEY=$(cat /secure/location/api_key)

# ❌ BAD: Store API keys in config file
# ~/.fleet-config/config.yaml:
# fleet_agent:
#   server:
#     api_key: "hardcoded_secret_key"  # Don't do this!
```

### 2. Use Configuration Files for Non-Secrets

```yaml
# ✅ GOOD: Store settings in config file
network:
  wifi:
    update_interval: 15
fleet_server:
  network:
    port: 8778
```

### 3. Validate Configuration in Production

```python
# At application startup
from atlas.config.manager import ConfigurationManager

manager = ConfigurationManager()
errors = manager.validate()

if errors:
    for error in errors:
        if error.startswith("ERROR"):
            raise RuntimeError(f"Configuration error: {error}")
        else:
            logger.warning(f"Configuration warning: {error}")
```

### 4. Use Different Configs for Different Environments

```bash
# Development
cp config.dev.yaml ~/.fleet-config/config.yaml

# Staging
cp config.staging.yaml ~/.fleet-config/config.yaml

# Production (use environment variables)
export FLEET_SERVER_PORT=8778
export FLEET_SSL_ENABLED=true
export FLEET_API_KEY=$PRODUCTION_API_KEY
```

---

## Troubleshooting

### Configuration Not Loading

**Problem**: User configuration file not found

**Solution**:
```bash
# Check if file exists
ls -la ~/.fleet-config/config.yaml

# Create if missing
mkdir -p ~/.fleet-config
cp config.example.yaml ~/.fleet-config/config.yaml
```

### Environment Variables Not Working

**Problem**: Environment variables not overriding configuration

**Solution**:
```bash
# Verify environment variable is set
echo $FLEET_SERVER_PORT

# Re-export if needed
export FLEET_SERVER_PORT=7777

# Check in Python
python3 -c "import os; print(os.environ.get('FLEET_SERVER_PORT'))"
```

### YAML Parsing Error

**Problem**: YAML configuration file has syntax error

**Solution**:
```bash
# Validate YAML syntax
python3 -c "
import yaml
with open('~/.fleet-config/config.yaml') as f:
    config = yaml.safe_load(f)
    print('✅ YAML valid')
"
```

### Invalid Configuration Values

**Problem**: Configuration validation fails

**Solution**:
```python
from atlas.config.manager import ConfigurationManager

manager = ConfigurationManager()
errors = manager.validate()

for error in errors:
    print(f"Error: {error}")
    # Fix the issue in config file or environment variable
```

---

## Support

For more information:
- **Configuration Examples**: See `config.example.yaml`
- **Source Code**: `atlas/config/`
- **Tests**: `test_configuration_system.py`
- **Summary**: `/tmp/phase6_complete_summary.txt`

For issues or questions, please open an issue on the project repository.
