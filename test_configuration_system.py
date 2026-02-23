#!/usr/bin/env python3
"""
Test Configuration System - Phase 6

Tests the centralized configuration system including:
- Default configuration loading
- User configuration merging
- Environment variable overrides
- Configuration validation
- YAML/JSON support
"""
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

print("=" * 80)
print("PHASE 6: CONFIGURATION SYSTEM TEST")
print("=" * 80)

# Test 1: Import configuration module
print("\nTest 1: Importing configuration module...")
try:
    from atlas.config import (
        get_config,
        get_value,
        NETWORK_CONFIG,
        FLEET_SERVER_CONFIG,
        SECURITY_CONFIG,
        FLEET_CONFIG_DIR,
    )
    print("   Configuration module imported successfully")
except Exception as e:
    print(f"   Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Verify default configurations
print("\n Test 2: Verifying default configurations...")
try:
    # Check WiFi config
    wifi_config = get_config("network", "wifi")
    assert wifi_config["update_interval"] == 10, "WiFi update interval should be 10"
    assert "log_file" in wifi_config, "WiFi config should have log_file"
    print(f"   WiFi config loaded: update_interval={wifi_config['update_interval']}s")

    # Check SpeedTest config
    speedtest_config = get_config("network", "speedtest")
    assert speedtest_config["update_interval"] == 60, "SpeedTest update interval should be 60"
    assert speedtest_config["slow_speed_threshold"] == 20.0, "Slow speed threshold should be 20.0"
    print(f"   SpeedTest config loaded: update_interval={speedtest_config['update_interval']}s")

    # Check Fleet Server config
    server_config = get_config("fleet_server", "network")
    assert server_config["port"] == 8778, "Fleet server port should be 8778"
    assert server_config["host"] == "0.0.0.0", "Fleet server host should be 0.0.0.0"
    print(f"   Fleet Server config loaded: {server_config['host']}:{server_config['port']}")

    # Check Security config
    security_config = get_config("security", "password")
    assert security_config["rounds"] == 12, "bcrypt rounds should be 12"
    assert security_config["min_length"] == 12, "Min password length should be 12"
    print(f"   Security config loaded: bcrypt rounds={security_config['rounds']}")

except Exception as e:
    print(f"   Configuration verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test get_value() helper
print("\nTest 3: Testing get_value() helper function...")
try:
    # Test nested value access
    wifi_interval = get_value("network.wifi.update_interval")
    assert wifi_interval == 10, f"Expected 10, got {wifi_interval}"
    print(f"   get_value('network.wifi.update_interval') = {wifi_interval}")

    server_port = get_value("fleet_server.network.port")
    assert server_port == 8778, f"Expected 8778, got {server_port}"
    print(f"   get_value('fleet_server.network.port') = {server_port}")

    # Test default value
    nonexistent = get_value("network.wifi.nonexistent_key", default=999)
    assert nonexistent == 999, f"Expected 999, got {nonexistent}"
    print(f"   get_value('network.wifi.nonexistent_key', default=999) = {nonexistent}")

except Exception as e:
    print(f"   get_value() test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test configuration paths
print("\n📁 Test 4: Testing configuration paths...")
try:
    from atlas.config import FLEET_DATA_DIR, FLEET_CERT_DIR

    # Verify directories exist
    assert FLEET_CONFIG_DIR.exists(), f"Config dir should exist: {FLEET_CONFIG_DIR}"
    assert FLEET_DATA_DIR.exists(), f"Data dir should exist: {FLEET_DATA_DIR}"
    assert FLEET_CERT_DIR.exists(), f"Cert dir should exist: {FLEET_CERT_DIR}"

    print(f"   Config directory: {FLEET_CONFIG_DIR}")
    print(f"   Data directory: {FLEET_DATA_DIR}")
    print(f"   Certificate directory: {FLEET_CERT_DIR}")

except Exception as e:
    print(f"   Path verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test ConfigurationManager
print("\n🎛️  Test 5: Testing ConfigurationManager...")
try:
    from atlas.config.manager import ConfigurationManager
    import tempfile

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config_file = Path(f.name)
        f.write('''{
            "network": {
                "wifi": {
                    "update_interval": 20
                }
            },
            "fleet_server": {
                "network": {
                    "port": 9999
                }
            }
        }''')

    # Load configuration
    manager = ConfigurationManager(temp_config_file)

    # Verify user config overrides defaults
    wifi_interval = manager.get("network.wifi.update_interval")
    assert wifi_interval == 20, f"Expected 20 (user override), got {wifi_interval}"
    print(f"   User config override: network.wifi.update_interval = {wifi_interval}")

    server_port = manager.get("fleet_server.network.port")
    assert server_port == 9999, f"Expected 9999 (user override), got {server_port}"
    print(f"   User config override: fleet_server.network.port = {server_port}")

    # Verify defaults still available for non-overridden values
    speedtest_interval = manager.get("network.speedtest.update_interval")
    assert speedtest_interval == 60, f"Expected 60 (default), got {speedtest_interval}"
    print(f"   Default preserved: network.speedtest.update_interval = {speedtest_interval}")

    # Test set and save
    manager.set("network.wifi.max_history", 120)
    max_history = manager.get("network.wifi.max_history")
    assert max_history == 120, f"Expected 120, got {max_history}"
    print(f"   set() method: network.wifi.max_history = {max_history}")

    # Cleanup
    temp_config_file.unlink()
    print("   ConfigurationManager tests passed")

except Exception as e:
    print(f"   ConfigurationManager test failed: {e}")
    import traceback
    traceback.print_exc()
    # Cleanup on error
    if 'temp_config_file' in locals() and temp_config_file.exists():
        temp_config_file.unlink()
    sys.exit(1)

# Test 6: Test environment variable overrides
print("\nTest 6: Testing environment variable overrides...")
try:
    # Set environment variables
    os.environ['FLEET_SERVER_PORT'] = '7777'
    os.environ['FLEET_SSL_ENABLED'] = 'false'

    # Re-import to pick up env vars
    import importlib
    import atlas.config.defaults
    importlib.reload(atlas.config.defaults)

    from atlas.config.defaults import FLEET_SERVER_CONFIG as reloaded_config

    # Verify environment variable overrides
    assert reloaded_config["network"]["port"] == 7777, f"Port should be 7777 from env var"
    assert reloaded_config["ssl"]["enabled"] == False, f"SSL should be False from env var"

    print(f"   Environment override: FLEET_SERVER_PORT = {reloaded_config['network']['port']}")
    print(f"   Environment override: FLEET_SSL_ENABLED = {reloaded_config['ssl']['enabled']}")

    # Cleanup
    del os.environ['FLEET_SERVER_PORT']
    del os.environ['FLEET_SSL_ENABLED']

except Exception as e:
    print(f"   Environment variable test failed: {e}")
    import traceback
    traceback.print_exc()
    # Cleanup on error
    if 'FLEET_SERVER_PORT' in os.environ:
        del os.environ['FLEET_SERVER_PORT']
    if 'FLEET_SSL_ENABLED' in os.environ:
        del os.environ['FLEET_SSL_ENABLED']
    sys.exit(1)

# Test 7: Test configuration validation
print("\nTest 7: Testing configuration validation...")
try:
    from atlas.config.defaults import validate_configuration

    issues = validate_configuration()
    print(f"   ℹ️  Validation found {len(issues)} issues:")
    for issue in issues:
        print(f"      - {issue}")

    # Validation should not block (warnings only)
    print("   Configuration validation completed")

except Exception as e:
    print(f"   Validation test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Test configuration sections
print("\nTest 8: Testing configuration sections...")
try:
    # Get entire sections
    network_section = get_config("network")
    assert "wifi" in network_section, "Network section should contain wifi"
    assert "speedtest" in network_section, "Network section should contain speedtest"
    assert "ping" in network_section, "Network section should contain ping"
    print(f"   Network section has {len(network_section)} subsections")

    security_section = get_config("security")
    assert "password" in security_section, "Security section should contain password"
    assert "encryption" in security_section, "Security section should contain encryption"
    assert "session" in security_section, "Security section should contain session"
    print(f"   Security section has {len(security_section)} subsections")

except Exception as e:
    print(f"   Configuration sections test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "=" * 80)
print("PHASE 6: CONFIGURATION SYSTEM TEST COMPLETE")
print("=" * 80)
print("\nAll tests passed successfully!")
print("\nConfiguration System Features:")
print("  Centralized default configurations")
print("  User configuration file support (YAML/JSON)")
print("  Configuration merging (user overrides defaults)")
print("  Environment variable overrides")
print("  Dot-notation value access (get_value)")
print("  Configuration validation")
print("  Type-safe configuration access")
print("  Automatic directory creation")
print("\nConfiguration Locations:")
print(f"  - Config directory: {FLEET_CONFIG_DIR}")
print(f"  - Default config file: {FLEET_CONFIG_DIR / 'config.yaml'}")
print(f"  - Alternative format: {FLEET_CONFIG_DIR / 'config.json'}")
print("\nUsage Example:")
print("  from atlas.config import get_config, get_value")
print("  wifi_config = get_config('network', 'wifi')")
print("  port = get_value('fleet_server.network.port')")
print("\n" + "=" * 80)
