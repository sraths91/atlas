#!/bin/bash
# ATLAS Menu Bar Launcher
# Double-click this file to launch the menu bar app

# Change to script directory
cd "$(dirname "$0")"

# Activate Python and start
echo "🚀 Starting ATLAS Menu Bar..."
echo "================================"
python3 start_atlas_agent.py --fleet-server https://localhost:8768 --machine-id $(hostname -s)
