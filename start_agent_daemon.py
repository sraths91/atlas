#!/usr/bin/env python3
"""
ATLAS Agent Daemon Launcher (No GUI)
Starts the core agent without menu bar for system boot
"""

import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas.fleet_config_encryption import EncryptedConfigManager
from atlas.live_widgets import start_live_widget_server
import socket

def main():
    """Start agent core without menu bar"""
    
    # Load config
    config_path = os.path.expanduser('~/.fleet-config.json')
    manager = EncryptedConfigManager(config_path)
    config = manager.decrypt_config()
    
    if not config:
        print("ERROR: Could not load encrypted config", file=sys.stderr)
        sys.exit(1)
    
    # Extract values
    server_config = config.get('server', {})
    api_key = server_config.get('api_key')
    fleet_server = server_config.get('fleet_server_url', 'https://localhost:8778')
    machine_id = config.get('machine_id') or socket.gethostname().split('.')[0]
    encryption_key = server_config.get('encryption_key')

    print(f"Starting ATLAS Agent Core (no GUI)")
    print(f"Fleet Server: {fleet_server}")
    print(f"Machine ID: {machine_id}")
    print(f"Port: 8767")
    print(f"E2EE: {'enabled' if encryption_key else 'disabled'}")

    # Start agent without menu bar
    thread = start_live_widget_server(
        port=8767,
        fleet_server=fleet_server,
        machine_id=machine_id,
        api_key=api_key,
        encryption_key=encryption_key
    )
    
    # Keep the process alive
    print("Agent running... Press Ctrl+C to stop")
    try:
        thread.join()  # Wait for the server thread
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == '__main__':
    main()
