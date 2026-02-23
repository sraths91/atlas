#!/usr/bin/env python3
"""
Repair Fleet Server credentials by setting new username/password
"""

import sys
import os
import getpass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas.fleet_config_encryption import EncryptedConfigManager

def main():
    config_path = os.path.expanduser('~/.fleet-config.json')
    
    print("=" * 60)
    print("FLEET SERVER CREDENTIAL REPAIR")
    print("=" * 60)
    print()
    
    # Check if encrypted config exists
    if not os.path.exists(config_path + '.encrypted'):
        print("No encrypted config found at:")
        print(f"   {config_path}.encrypted")
        print()
        print("Creating new configuration...")
        config = {}
    else:
        print("Found encrypted config, loading...")
        manager = EncryptedConfigManager(config_path)
        config = manager.decrypt_config()
        if not config:
            print(" Could not decrypt, creating new config")
            config = {}
        else:
            print("Config loaded successfully")
    
    print()
    print("=" * 60)
    print("SET NEW WEB DASHBOARD CREDENTIALS")
    print("=" * 60)
    print()
    
    # Get new credentials from user
    username = input("Enter username (default: admin): ").strip() or "admin"
    
    # Get password with confirmation
    while True:
        password = getpass.getpass("Enter password: ")
        if not password:
            print("Password cannot be empty")
            continue
        
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("Passwords don't match, try again")
            continue
        
        break
    
    print()
    print("Setting credentials...")
    
    # Update config structure
    if 'server' not in config:
        config['server'] = {}
    
    config['server']['web_username'] = username
    config['server']['web_password'] = password
    
    # Keep existing values if present
    if 'organization_name' not in config:
        config['organization_name'] = 'My Organization'
    
    if 'api_key' not in config.get('server', {}):
        # Keep existing API key if present, otherwise generate new one
        import secrets
        config['server']['api_key'] = secrets.token_urlsafe(32)
    
    # Save encrypted config
    manager = EncryptedConfigManager(config_path)
    if manager.encrypt_config(config):
        print("Credentials saved successfully!")
        print()
        print("=" * 60)
        print("NEW CREDENTIALS")
        print("=" * 60)
        print(f"Username: {username}")
        print(f"Password: {password}")
        print()
        print("Dashboard URL: http://localhost:8768/dashboard")
        print()
        print(" IMPORTANT: Restart the Fleet Server for changes to take effect:")
        print("   pkill -f fleet_server")
        print("   python3 -m atlas.fleet_server --port 8768 --host 0.0.0.0")
        print()
        print("=" * 60)
        return 0
    else:
        print("Failed to save credentials")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
