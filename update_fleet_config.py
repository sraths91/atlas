#!/usr/bin/env python3
"""
Update fleet configuration with server URL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas.fleet_config_encryption import EncryptedConfigManager

def main():
    config_path = os.path.expanduser('~/.fleet-config.json')
    
    print("=" * 60)
    print("UPDATE FLEET CONFIGURATION")
    print("=" * 60)
    print()
    
    # Load existing config
    manager = EncryptedConfigManager(config_path)
    config = manager.decrypt_config() or {}
    
    # Get current values
    current_url = config.get('server', {}).get('fleet_server_url', 'https://localhost:8768')
    
    print(f"Current Fleet Server URL: {current_url}")
    print()
    
    # Get new URL
    new_url = input("Enter Fleet Server URL (or press Enter to keep current): ").strip()
    
    if new_url:
        if 'server' not in config:
            config['server'] = {}
        config['server']['fleet_server_url'] = new_url
        print(f"\nUpdated to: {new_url}")
    else:
        # Ensure current URL is saved
        if 'server' not in config:
            config['server'] = {}
        config['server']['fleet_server_url'] = current_url
        print(f"\nKeeping: {current_url}")
    
    # Save
    if manager.encrypt_config(config):
        print("Configuration saved")
        print()
        print("=" * 60)
        print("CURRENT CONFIGURATION")
        print("=" * 60)
        print(f"Fleet Server: {config['server']['fleet_server_url']}")
        print(f"API Key: {config['server'].get('api_key', 'Not set')[:20]}...")
        print(f"Web Username: {config['server'].get('web_username', 'Not set')}")
        print()
        return 0
    else:
        print("Failed to save configuration")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelled")
        sys.exit(1)
