#!/usr/bin/env python3
"""
Auto Credential Repair (Non-Interactive)
Creates encrypted config with generated secure values.

NOTE: This is for FLEET SERVER setup only. Agent-only users do NOT need
to run this script — agents authenticate with your macOS login automatically.
"""

import sys
import os
import secrets
import string
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from atlas.fleet_config_encryption import EncryptedConfigManager


def _generate_secure_password(length: int = 24) -> str:
    """Generate a cryptographically secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def main():
    """Auto-repair fleet server credentials with secure generated values"""

    print("=" * 60)
    print("AUTO FLEET SERVER CREDENTIAL REPAIR")
    print("=" * 60)
    print()
    print("NOTE: This is for Fleet Server admin accounts only.")
    print("      Agent-only users authenticate with their macOS login.")
    print()

    config_path = Path.home() / ".fleet-config.json"

    # Generate secure credentials — never use hardcoded defaults
    username = "admin"
    password = _generate_secure_password()
    api_key = secrets.token_urlsafe(32)

    print(f"Creating config with generated credentials:")
    print(f"   Username: {username}")
    print(f"   Password: (generated — shown below)")
    print(f"   API Key: {api_key[:20]}...")
    print()

    # Create config data
    config_data = {
        'organization_name': 'ATLAS Fleet',
        'server': {
            'api_key': api_key,
            'fleet_server_url': 'https://localhost:8768',
            'web_username': username,
            'web_password': password
        }
    }

    try:
        # Save encrypted config
        manager = EncryptedConfigManager(str(config_path))
        manager.encrypt_config(config_data)

        print("=" * 60)
        print("CREDENTIALS SAVED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("Configuration saved to:")
        print(f"  {config_path}.encrypted")
        print()
        print("Fleet Server Credentials:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"  API Key:  {api_key}")
        print()
        print("Fleet Server URL: https://localhost:8768")
        print()
        print("IMPORTANT: Save these credentials! The password was")
        print("randomly generated and cannot be recovered.")
        print()
        print("Next steps:")
        print("  1. Restart server: launchctl kickstart -k gui/$(id -u)/com.atlas.fleetserver")
        print("  2. Access dashboard: https://localhost:8768/dashboard")
        print()

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
