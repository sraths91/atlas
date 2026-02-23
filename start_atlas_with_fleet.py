#!/usr/bin/env python3
"""
ATLAS Agent Startup Script with Fleet Server Configuration
Starts the ATLAS agent with E2EE encryption and fleet server connection.
This script is used by the LaunchAgent for automatic startup.
"""
import sys
import time
import os
import json
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlas.live_widgets import start_live_widget_server

logger = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / '.fleet-config.json'

def load_fleet_config():
    """Load fleet config from file or environment variables."""
    config = {}

    # Try config file first
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded fleet config from {CONFIG_PATH}")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read {CONFIG_PATH}: {e}")

    # Extract values with env var fallback
    fleet_server = (
        config.get('fleet_server')
        or os.environ.get('FLEET_SERVER_URL')
    )
    machine_id = (
        config.get('machine_id')
        or os.environ.get('FLEET_MACHINE_ID')
    )
    api_key = (
        config.get('api_key')
        or os.environ.get('FLEET_API_KEY')
    )
    encryption_key = (
        config.get('encryption_key')
        or os.environ.get('FLEET_ENCRYPTION_KEY')
    )

    if not fleet_server or not api_key:
        logger.error(
            "Fleet config missing. Create %s with fleet_server/api_key "
            "or set FLEET_SERVER_URL/FLEET_API_KEY environment variables.",
            CONFIG_PATH,
        )
        sys.exit(1)

    return fleet_server, machine_id, api_key, encryption_key


if __name__ == '__main__':
    print("Starting ATLAS Agent local dashboard on port 8767...")

    fleet_server, machine_id, api_key, encryption_key = load_fleet_config()

    thread = start_live_widget_server(
        port=8767,
        fleet_server=fleet_server,
        machine_id=machine_id,
        api_key=api_key,
        encryption_key=encryption_key
    )

    print("Server started! Dashboard available at http://localhost:8767")
    print(f"Fleet server: {fleet_server}")
    print(f"E2EE: {'Enabled' if encryption_key else 'Disabled'}")

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
