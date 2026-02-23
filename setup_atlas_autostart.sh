#!/bin/bash
# Setup auto-start for ATLAS Fleet Server and Agent
# Installs LaunchAgents so both start automatically at login

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

AGENT_PLIST_SRC="$PROJECT_DIR/com.atlas.agent.plist"
SERVER_PLIST_SRC="$PROJECT_DIR/com.atlas.fleetserver.plist"
AGENT_PLIST_DEST="$LAUNCH_AGENTS_DIR/com.atlas.agent.plist"
SERVER_PLIST_DEST="$LAUNCH_AGENTS_DIR/com.atlas.fleetserver.plist"

echo "============================================"
echo " ATLAS AUTO-START SETUP"
echo "============================================"

# Ensure LaunchAgents directory exists
mkdir -p "$LAUNCH_AGENTS_DIR"

# Resolve python3 path
PYTHON_PATH="$(which python3 || true)"
if [ -z "$PYTHON_PATH" ]; then
  echo "❌ python3 not found in PATH"
  exit 1
fi

echo "Using python: $PYTHON_PATH"

# Function to install one plist with correct python path
install_plist() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [ ! -f "$src" ]; then
    echo "❌ Missing plist: $src"
    return 1
  fi

  # Substitute python path
  sed "s|/usr/local/bin/python3|$PYTHON_PATH|g" "$src" > "$dest"
  echo "✅ Installed $label plist to $dest"

  # Unload if already loaded
  if launchctl list | grep -q "$label"; then
    echo "Unloading existing $label..."
    launchctl unload "$dest" 2>/dev/null || true
  fi

  # Load new plist
  echo "Loading $label..."
  launchctl load "$dest"
}

# Install Fleet Server LaunchAgent
install_plist "$SERVER_PLIST_SRC" "$SERVER_PLIST_DEST" "com.atlas.fleetserver"

# Install Agent LaunchAgent (uses launch_atlas_with_config.py)
install_plist "$AGENT_PLIST_SRC" "$AGENT_PLIST_DEST" "com.atlas.agent"

echo ""
echo "============================================"
echo " ✅ ATLAS AUTO-START CONFIGURED"
echo "============================================"
echo "On next login, the following will start automatically:"
echo "  - Fleet Server (com.atlas.fleetserver) on port 8768"
echo "  - ATLAS Agent + menu bar (com.atlas.agent)"
echo ""
echo "Manual controls:"
echo "  launchctl list | grep atlas          # Check status"
echo "  launchctl unload $SERVER_PLIST_DEST  # Stop server"
echo "  launchctl unload $AGENT_PLIST_DEST   # Stop agent"
echo "  launchctl load   $SERVER_PLIST_DEST  # Start server"
echo "  launchctl load   $AGENT_PLIST_DEST   # Start agent"
echo ""
echo "Logs:"
echo "  tail -f ~/.atlas-fleetserver.log      # Server"
echo "  tail -f ~/.atlas-agent.log            # Agent"
echo ""
