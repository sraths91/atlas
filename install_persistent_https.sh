#!/bin/bash
# Install ATLAS Fleet Server and Agent with persistent HTTPS configuration
# This ensures the system works correctly after reboots

set -e

echo "============================================================"
echo "ATLAS Fleet Server - Persistent HTTPS Installation"
echo "============================================================"
echo ""

# Check if running as root for system-level services
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script needs sudo privileges to install system services"
    echo "Please run: sudo ./install_persistent_https.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing for user: $ACTUAL_USER"
echo "Home directory: $ACTUAL_HOME"
echo "Project directory: $PROJECT_DIR"
echo ""

# Step 1: Ensure credentials are configured
echo "Step 1: Checking credentials..."
if [ ! -f "$ACTUAL_HOME/.fleet-config.json.encrypted" ]; then
    echo "⚠️  No encrypted config found. Creating one..."
    sudo -u $ACTUAL_USER python3 "$PROJECT_DIR/set_credentials.py"
else
    echo "✅ Encrypted config exists"
    # Verify it has SSL paths
    SSL_CERT=$(sudo -u $ACTUAL_USER python3 -c "from atlas.fleet_config import FleetConfig; c = FleetConfig(); print(c.get('ssl.cert_file', ''))" 2>/dev/null || echo "")
    if [ -z "$SSL_CERT" ]; then
        echo "⚠️  Config missing SSL paths. Recreating..."
        sudo -u $ACTUAL_USER python3 "$PROJECT_DIR/set_credentials.py"
    else
        echo "✅ SSL configuration present: $SSL_CERT"
    fi
fi

# Get the API key from config
API_KEY=$(sudo -u $ACTUAL_USER python3 -c "from atlas.fleet_config import FleetConfig; c = FleetConfig(); print(c.get('server.api_key', ''))" 2>/dev/null || echo "")
if [ -z "$API_KEY" ]; then
    echo "❌ Failed to get API key from config"
    exit 1
fi
echo "✅ API Key loaded: ${API_KEY:0:20}..."
echo ""

# Step 2: Create/update LaunchDaemon for Fleet Server
echo "Step 2: Installing Fleet Server LaunchDaemon..."
cat > /Library/LaunchDaemons/com.atlas.fleetserver.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlas.fleetserver</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>atlas.fleet_server</string>
        <string>--port</string>
        <string>8768</string>
        <string>--host</string>
        <string>0.0.0.0</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>/var/log/atlas-fleetserver.log</string>

    <key>StandardErrorPath</key>
    <string>/var/log/atlas-fleetserver.error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>PYTHONPATH</key>
        <string>$PROJECT_DIR</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>UserName</key>
    <string>$ACTUAL_USER</string>

    <key>GroupName</key>
    <string>staff</string>
</dict>
</plist>
EOF

chmod 644 /Library/LaunchDaemons/com.atlas.fleetserver.plist
echo "✅ Fleet Server LaunchDaemon created"
echo ""

# Step 3: Create/update LaunchDaemon for Core Agent
echo "Step 3: Installing Core Agent LaunchDaemon..."
cat > /Library/LaunchDaemons/com.atlas.agent.core.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlas.agent.core</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>atlas.live_widgets</string>
        <string>--port</string>
        <string>8767</string>
        <string>--fleet-server</string>
        <string>https://localhost:8768</string>
        <string>--api-key</string>
        <string>$API_KEY</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>/var/log/atlas-agent.log</string>

    <key>StandardErrorPath</key>
    <string>/var/log/atlas-agent.error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>PYTHONPATH</key>
        <string>$PROJECT_DIR</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>UserName</key>
    <string>$ACTUAL_USER</string>

    <key>GroupName</key>
    <string>staff</string>
</dict>
</plist>
EOF

chmod 644 /Library/LaunchDaemons/com.atlas.agent.core.plist
echo "✅ Core Agent LaunchDaemon created"
echo ""

# Step 4: Create log files with correct permissions
echo "Step 4: Setting up log files..."
touch /var/log/atlas-fleetserver.log
touch /var/log/atlas-fleetserver.error.log
touch /var/log/atlas-agent.log
touch /var/log/atlas-agent.error.log
chown $ACTUAL_USER:staff /var/log/atlas-*.log
chmod 644 /var/log/atlas-*.log
echo "✅ Log files created"
echo ""

# Step 5: Stop any running services
echo "Step 5: Stopping existing services..."
launchctl unload /Library/LaunchDaemons/com.atlas.fleetserver.plist 2>/dev/null || true
launchctl unload /Library/LaunchDaemons/com.atlas.agent.core.plist 2>/dev/null || true
killall -9 Python 2>/dev/null || true
sleep 3
echo "✅ Existing services stopped"
echo ""

# Step 6: Load and start services
echo "Step 6: Starting services..."
launchctl load /Library/LaunchDaemons/com.atlas.fleetserver.plist
sleep 5
launchctl load /Library/LaunchDaemons/com.atlas.agent.core.plist
sleep 5
echo "✅ Services started"
echo ""

# Step 7: Verify services are running
echo "Step 7: Verifying installation..."
echo ""

# Check Fleet Server
if lsof -i :8768 >/dev/null 2>&1; then
    echo "✅ Fleet Server is running on port 8768"
    if curl -k -s https://localhost:8768/ | head -1 | grep -q "DOCTYPE"; then
        echo "✅ Fleet Server HTTPS is working"
    else
        echo "⚠️  Fleet Server HTTPS test failed"
        tail -10 /var/log/atlas-fleetserver.error.log
    fi
else
    echo "❌ Fleet Server is NOT running"
    tail -20 /var/log/atlas-fleetserver.error.log
fi

echo ""

# Check Agent
if lsof -i :8767 >/dev/null 2>&1; then
    echo "✅ Core Agent is running on port 8767"
    if curl -s http://localhost:8767/api/agent/health | grep -q "healthy"; then
        echo "✅ Core Agent health check passed"
    else
        echo "⚠️  Core Agent health check failed"
    fi
else
    echo "❌ Core Agent is NOT running"
    tail -20 /var/log/atlas-agent.error.log
fi

echo ""
echo "============================================================"
echo "✅ Installation Complete!"
echo "============================================================"
echo ""
echo "Services Configuration:"
echo "  Fleet Server: HTTPS on port 8768 (starts at boot)"
echo "  Core Agent:   HTTP on port 8767 (starts at boot)"
echo ""
echo "Access:"
echo "  Dashboard: https://localhost:8768/dashboard"
echo "  Username:  admin"
echo "  Password:  AtlasShrugged2025!"
echo ""
echo "Logs:"
echo "  Fleet Server: tail -f /var/log/atlas-fleetserver.log"
echo "  Core Agent:   tail -f /var/log/atlas-agent.log"
echo ""
echo "Management:"
echo "  Status:  sudo launchctl list | grep atlas"
echo "  Restart: sudo launchctl kickstart -k system/com.atlas.fleetserver"
echo "           sudo launchctl kickstart -k system/com.atlas.agent.core"
echo ""
echo "🎉 The system will automatically start on reboot!"
echo ""
