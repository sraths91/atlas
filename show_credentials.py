#!/usr/bin/env python3
"""
Show Fleet Server credentials
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from atlas.fleet_config_encryption import EncryptedConfigManager
    
    # Decrypt config
    # Note: EncryptedConfigManager adds .encrypted extension automatically
    config_path = os.path.expanduser('~/.fleet-config.json')
    
    if not os.path.exists(config_path + '.encrypted'):
        print("No encrypted config found")
        sys.exit(1)
    
    manager = EncryptedConfigManager(config_path)
    config = manager.decrypt_config()
    
    if not config:
        print("Error: Could not decrypt config")
        sys.exit(1)
    
    print("=" * 60)
    print("FLEET SERVER CREDENTIALS")
    print("=" * 60)
    print()
    
    # Web UI credentials
    web_user = config.get('server', {}).get('web_username')
    web_pass = config.get('server', {}).get('web_password')
    
    if web_user or web_pass:
        print("Web Dashboard Login:")
        print(f"   URL: http://localhost:8768/dashboard")
        print(f"   Username: {web_user if web_user else '(not set)'}")
        print(f"   Password: {web_pass if web_pass else '(not set)'}")
        print()
    else:
        print("No web authentication configured")
        print()
    
    # API Key
    api_key = config.get('server', {}).get('api_key')
    if api_key:
        print("API Key (for agents):")
        print(f"   {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
        print()
    
    print("=" * 60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
