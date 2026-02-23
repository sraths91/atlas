#!/usr/bin/env python3
"""
Reset or show Fleet Server web credentials
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas.fleet_config import FleetConfig

# Load config
config = FleetConfig()

# Get current credentials
current_user = config.get('server.web_username')
current_pass = config.get('server.web_password')

print("=" * 60)
print("Fleet Server Web Credentials")
print("=" * 60)

if current_user:
    print(f"Username: {current_user}")
    print(f"Password: {'*' * len(current_pass) if current_pass else '(not set)'}")
    print()
    print("To login to dashboard:")
    print(f"  URL: http://localhost:8768/dashboard")
    print(f"  Username: {current_user}")
    if current_pass:
        print(f"  Password: <stored in encrypted config>")
    print()
    print("To disable authentication, restart server with:")
    print("  python3 -m atlas.fleet_server --port 8768")
    print("  (Don't use --config parameter)")
else:
    print("Web authentication is NOT configured")
    print("   You can access the dashboard without login")
    print()
    print("If you're seeing a login page, the server might be")
    print("loading credentials from ~/.fleet-config.json.encrypted")
    print()
    print("To start server WITHOUT authentication:")
    print("  mv ~/.fleet-config.json.encrypted ~/.fleet-config.json.encrypted.backup")
    print("  python3 -m atlas.fleet_server --port 8768 --host 0.0.0.0")

print("=" * 60)
