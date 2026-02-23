#!/bin/bash
# Setup ATLAS Agent Auto-Start
# This script installs the ATLAS agent to start automatically on login

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_FILE="com.atlas.agent.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_FILE"

echo "=============================================="
echo "ATLAS AGENT AUTO-START SETUP"
echo "=============================================="
echo ""

# Check if config exists
if [ ! -f "$HOME/.fleet-config.json.encrypted" ]; then
    echo "❌ No encrypted config found!"
    echo "   Please run: python3 repair_credentials.py first"
    exit 1
fi

echo "✅ Found encrypted config"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found!"
    echo "   Please install Python 3"
    exit 1
fi

echo "✅ Python 3 found: $(which python3)"
echo ""

# Update plist with correct Python path
PYTHON_PATH=$(which python3)
echo "Updating plist with Python path: $PYTHON_PATH"
sed "s|/usr/local/bin/python3|$PYTHON_PATH|g" "$PROJECT_DIR/$PLIST_FILE" > /tmp/atlas_agent.plist.tmp

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Stop existing agent if running
if launchctl list | grep -q "com.atlas.agent"; then
    echo "Stopping existing agent..."
    launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true
fi

# Copy plist file
echo "Installing LaunchAgent..."
cp /tmp/atlas_agent.plist.tmp "$INSTALLED_PLIST"
rm /tmp/atlas_agent.plist.tmp

# Load the agent
echo "Loading LaunchAgent..."
launchctl load "$INSTALLED_PLIST"

echo ""
echo "=============================================="
echo "✅ ATLAS AGENT AUTO-START INSTALLED"
echo "=============================================="
echo ""
echo "The agent will now start automatically when you log in."
echo ""
echo "Useful commands:"
echo "  Check status:  launchctl list | grep atlas"
echo "  View logs:     tail -f ~/.atlas-agent.log"
echo "  Stop agent:    launchctl unload $INSTALLED_PLIST"
echo "  Start agent:   launchctl load $INSTALLED_PLIST"
echo "  Restart:       launchctl kickstart -k gui/\$(id -u)/com.atlas.agent"
echo ""
echo "The agent is starting now..."
sleep 2
if launchctl list | grep -q "com.atlas.agent"; then
    echo "✅ Agent is running"
else
    echo "⚠️  Agent may still be starting..."
    echo "   Check logs: tail -f ~/.atlas-agent.log"
fi
echo ""
