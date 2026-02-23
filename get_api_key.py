#!/usr/bin/env python3
"""Helper script to get the Fleet Server API key from config"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

try:
    from atlas.fleet_config import FleetConfig
    
    # Load config (same way fleet_server does)
    config = FleetConfig()
    
    # Get API key (check env var first, then config)
    api_key = os.environ.get('FLEET_API_KEY') or config.get('server.api_key')
    
    if api_key:
        print(api_key)
    else:
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
