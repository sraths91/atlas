#!/usr/bin/env python3
"""
Set Specific Credentials
"""

import sys
import os
import secrets
import getpass
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from atlas.fleet_config_encryption import EncryptedConfigManager

def main():
    """Set credentials with specified values"""

    print("=" * 60)
    print("FLEET SERVER CREDENTIAL SETUP")
    print("=" * 60)
    print()

    config_path = Path.home() / ".fleet-config.json"

    # Get credentials from environment variables or user input (SECURE)
    username = os.environ.get('FLEET_ADMIN_USER')
    if not username:
        username = input("Enter admin username (default: admin): ").strip()
        if not username:
            username = "admin"

    password = os.environ.get('FLEET_ADMIN_PASSWORD')
    if not password:
        password = getpass.getpass("Enter admin password: ")
        if not password:
            print("Error: Password cannot be empty")
            return 1
        password_confirm = getpass.getpass("Confirm admin password: ")
        if password != password_confirm:
            print("Error: Passwords do not match")
            return 1

    # Generate a secure API key
    api_key = os.environ.get('FLEET_API_KEY', secrets.token_urlsafe(32))

    print()
    print(f"Setting credentials:")
    print(f"   Username: {username}")
    print(f"   Password: {'*' * 12}")  # Never show actual password
    print(f"   API Key: {api_key[:20]}...")
    print()
    
    # SSL certificate paths
    cert_dir = Path.home() / ".fleet-certs"
    ssl_cert = str(cert_dir / "cert.pem")
    ssl_key = str(cert_dir / "privkey.pem")
    
    # Create config data
    config_data = {
        'organization_name': 'ATLAS Fleet',
        'server': {
            'api_key': api_key,
            'fleet_server_url': 'https://localhost:8778',
            'web_username': username,
            'web_password': password
        },
        'ssl': {
            'cert_file': ssl_cert,
            'key_file': ssl_key
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
        print("Credentials:")
        print(f"  Username: {username}")
        print(f"  Password: {'*' * 12}")  # SECURITY: Never display plaintext password
        print(f"  API Key:  {api_key}")
        print()
        print("Fleet Server URL: https://localhost:8778")
        print()
        print("Dashboard Login:")
        print(f"  URL: https://localhost:8778/dashboard")
        print(f"  Username: {username}")
        print(f"  Password: (saved securely)")
        print()
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
