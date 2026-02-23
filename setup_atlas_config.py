#!/usr/bin/env python3
"""
ATLAS Configuration Setup
Creates and manages encrypted configuration for ATLAS agent and fleet server
"""

import sys
import os
import getpass
import secrets
import socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas.fleet_config_encryption import EncryptedConfigManager, ENCRYPTION_AVAILABLE


def print_header(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def get_yes_no(prompt, default=True):
    """Get a yes/no response from user"""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    if not response:
        return default
    return response in ('y', 'yes')


def setup_standalone():
    """Setup for standalone mode (local monitoring only)"""
    print_header("STANDALONE MODE SETUP")
    
    config = {
        'mode': 'standalone',
        'machine_id': socket.gethostname().split('.')[0],
        'agent': {
            'port': 8767,
            'auto_start': True
        }
    }
    
    # Ask for machine ID
    machine_id = input(f"Machine ID [{config['machine_id']}]: ").strip()
    if machine_id:
        config['machine_id'] = machine_id
    
    return config


def setup_fleet_agent():
    """Setup for fleet agent mode (connects to fleet server)"""
    print_header("FLEET AGENT SETUP")
    
    print("This setup will configure the agent to connect to a Fleet Server.")
    print()
    
    config = {
        'mode': 'fleet_agent',
        'machine_id': socket.gethostname().split('.')[0],
        'server': {}
    }
    
    # Machine ID
    machine_id = input(f"Machine ID [{config['machine_id']}]: ").strip()
    if machine_id:
        config['machine_id'] = machine_id
    
    # Fleet server URL
    default_url = "https://localhost:8768"
    fleet_url = input(f"Fleet Server URL [{default_url}]: ").strip()
    config['server']['fleet_server_url'] = fleet_url or default_url
    
    # API Key (for authentication)
    print()
    print("Enter the API key from your Fleet Server (for authentication).")
    print()
    
    api_key = input("API Key: ").strip()
    if not api_key:
        if get_yes_no("Generate a new API key?", True):
            api_key = secrets.token_urlsafe(32)
            print(f"\nGenerated API Key: {api_key}")
            print(" Save this key! You'll need to add it to the Fleet Server config too.")
    
    config['server']['api_key'] = api_key
    
    # E2EE Encryption Key (for payload encryption)
    print()
    print("End-to-End Encryption (E2EE) encrypts all data sent to the server.")
    print("Both agent and server must use the SAME encryption key.")
    print()
    
    if get_yes_no("Enable E2EE payload encryption?", True):
        encryption_key = input("Encryption Key (leave blank to generate): ").strip()
        if not encryption_key:
            try:
                from atlas.encryption import DataEncryption
                encryption_key = DataEncryption.generate_key()
                print(f"\nGenerated Encryption Key: {encryption_key}")
                print(" IMPORTANT: Use this SAME key on the Fleet Server!")
            except Exception as e:
                print(f"Could not generate key: {e}")
                encryption_key = None
        
        if encryption_key:
            config['server']['encryption_key'] = encryption_key
    
    return config


def setup_fleet_server():
    """Setup for fleet server mode"""
    print_header("FLEET SERVER SETUP")
    
    print("This setup will configure the Fleet Server credentials.")
    print()
    
    config = {
        'mode': 'fleet_server',
        'organization_name': 'My Organization',
        'server': {}
    }
    
    # Organization name
    org_name = input(f"Organization Name [{config['organization_name']}]: ").strip()
    if org_name:
        config['organization_name'] = org_name
    
    # Web dashboard credentials
    print()
    print("Set up web dashboard login credentials:")
    username = input("Username [admin]: ").strip() or "admin"
    
    while True:
        password = getpass.getpass("Password: ")
        if not password:
            print("Password cannot be empty")
            continue
        
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("Passwords don't match, try again")
            continue
        break
    
    config['server']['web_username'] = username
    config['server']['web_password'] = password
    
    # API Key for agents (authentication)
    print()
    print("API Key is used for agent authentication.")
    if get_yes_no("Generate API key for agent authentication?", True):
        api_key = secrets.token_urlsafe(32)
        config['server']['api_key'] = api_key
        print(f"\nGenerated API Key: {api_key}")
        print("Share this key with agents that need to connect to this server.")
    
    # E2EE Encryption Key (for payload encryption)
    print()
    print("End-to-End Encryption (E2EE) encrypts all data received from agents.")
    print("All agents must use the SAME encryption key to communicate with this server.")
    print()
    
    if get_yes_no("Enable E2EE payload encryption?", True):
        encryption_key = input("Encryption Key (leave blank to generate): ").strip()
        if not encryption_key:
            try:
                from atlas.encryption import DataEncryption
                encryption_key = DataEncryption.generate_key()
                print(f"\nGenerated Encryption Key: {encryption_key}")
                print("=" * 50)
                print(" IMPORTANT: Configure ALL agents with this key!")
                print("=" * 50)
            except Exception as e:
                print(f"Could not generate key: {e}")
                encryption_key = None
        
        if encryption_key:
            config['server']['encryption_key'] = encryption_key
    
    return config


def view_current_config():
    """View current configuration (redacted)"""
    print_header("CURRENT CONFIGURATION")
    
    config_path = os.path.expanduser('~/.fleet-config.json')
    
    if not os.path.exists(config_path + '.encrypted'):
        print("No configuration found.")
        return
    
    manager = EncryptedConfigManager(config_path)
    config = manager.decrypt_config()
    
    if not config:
        print("Could not decrypt configuration.")
        print("   The config may have been created on a different machine.")
        print("   Run this script again to create a new configuration.")
        return
    
    print(f"Mode: {config.get('mode', 'unknown')}")
    print(f"Machine ID: {config.get('machine_id', 'not set')}")
    print(f"Organization: {config.get('organization_name', 'not set')}")
    
    if 'server' in config:
        print()
        print("Server Settings:")
        server = config['server']
        if 'fleet_server_url' in server:
            print(f"  Fleet URL: {server['fleet_server_url']}")
        if 'api_key' in server:
            key = server['api_key']
            print(f"  API Key (auth): {key[:8]}...{key[-8:]}")
        if 'encryption_key' in server:
            key = server['encryption_key']
            print(f"  E2EE Key: {key[:8]}...{key[-8:]} (enabled)")
        else:
            print(f"  E2EE Key: Not configured (data sent unencrypted)")
        if 'web_username' in server:
            print(f"  Web Username: {server['web_username']}")
        if 'web_password' in server:
            print(f"  Web Password: {'*' * 8}")


def delete_config():
    """Delete current configuration"""
    print_header("DELETE CONFIGURATION")
    
    config_path = os.path.expanduser('~/.fleet-config.json')
    encrypted_path = config_path + '.encrypted'
    
    if not os.path.exists(encrypted_path):
        print("No configuration found to delete.")
        return
    
    if get_yes_no("Are you sure you want to delete the configuration?", False):
        os.remove(encrypted_path)
        print("Configuration deleted.")
    else:
        print("Cancelled.")


def main():
    print_header("ATLAS CONFIGURATION SETUP")
    
    if not ENCRYPTION_AVAILABLE:
        print(" WARNING: cryptography package not installed!")
        print("   Configuration will be stored in PLAINTEXT.")
        print()
        print("   Install cryptography for secure storage:")
        print("   pip install cryptography")
        print()
    
    print("What would you like to do?")
    print()
    print("  1. Setup STANDALONE mode (local monitoring only)")
    print("  2. Setup FLEET AGENT (connect to a fleet server)")
    print("  3. Setup FLEET SERVER (run a fleet server)")
    print("  4. View current configuration")
    print("  5. Delete configuration and start fresh")
    print("  6. Exit")
    print()
    
    choice = input("Enter choice [1-6]: ").strip()
    
    config = None
    
    if choice == '1':
        config = setup_standalone()
    elif choice == '2':
        config = setup_fleet_agent()
    elif choice == '3':
        config = setup_fleet_server()
    elif choice == '4':
        view_current_config()
        return 0
    elif choice == '5':
        delete_config()
        return 0
    elif choice == '6':
        print("Exiting.")
        return 0
    else:
        print("Invalid choice.")
        return 1
    
    if config:
        # Save configuration
        print_header("SAVING CONFIGURATION")
        
        config_path = os.path.expanduser('~/.fleet-config.json')
        manager = EncryptedConfigManager(config_path)
        
        if manager.encrypt_config(config):
            print("Configuration saved successfully!")
            print()
            print(f"   Encrypted file: {config_path}.encrypted")
            print()
            
            if config.get('mode') == 'standalone':
                print("To start the agent in standalone mode:")
                print("   launchctl load ~/Library/LaunchAgents/com.atlas.agent.plist")
                print()
                print("Dashboard: http://localhost:8767")
            
            elif config.get('mode') == 'fleet_agent':
                print("To start the agent:")
                print("   launchctl load ~/Library/LaunchAgents/com.atlas.agent.plist")
                print()
                print("The agent will connect to:", config['server'].get('fleet_server_url'))
            
            elif config.get('mode') == 'fleet_server':
                print("To start the fleet server:")
                print("   python3 -m atlas.fleet_server --port 8768")
                print()
                print(f"Dashboard: http://localhost:8768/dashboard")
                print(f"Username: {config['server'].get('web_username')}")
        else:
            print("Failed to save configuration")
            return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
