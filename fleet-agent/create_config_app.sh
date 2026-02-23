#!/bin/bash
#
# Create Fleet Agent Configuration App
# This creates a simple GUI app for configuring the fleet agent
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_NAME="Fleet Agent Configuration.app"
APP_DIR="$SCRIPT_DIR/build/app"
APP_PATH="$APP_DIR/$APP_NAME"

echo "Creating Fleet Agent Configuration App..."

# Clean and create app structure
rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Create Info.plist
cat > "$APP_PATH/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>configure</string>
    <key>CFBundleIdentifier</key>
    <string>com.fleet.agent.config</string>
    <key>CFBundleName</key>
    <string>Fleet Agent Configuration</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Create the main executable script
cat > "$APP_PATH/Contents/MacOS/configure" << 'SCRIPT_EOF'
#!/bin/bash

CONFIG_FILE="/Library/Application Support/FleetAgent/config.json"
LAUNCHDAEMON="/Library/LaunchDaemons/com.fleet.agent.plist"

# Check if running with admin privileges
if [ "$EUID" -ne 0 ]; then
    # Re-run with sudo
    osascript -e 'do shell script "\"'"$0"'\"" with administrator privileges'
    exit 0
fi

# Get current config if it exists
CURRENT_URL=""
CURRENT_KEY=""
CURRENT_INTERVAL="10"

if [ -f "$CONFIG_FILE" ]; then
    CURRENT_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('server_url', ''))" 2>/dev/null || echo "")
    CURRENT_KEY=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('api_key', ''))" 2>/dev/null || echo "")
    CURRENT_INTERVAL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('interval', 10))" 2>/dev/null || echo "10")
fi

# Show configuration dialog
CONFIG_RESULT=$(osascript << APPLESCRIPT
set serverURL to text returned of (display dialog "Enter Fleet Server URL:" default answer "$CURRENT_URL" buttons {"Cancel", "Next"} default button "Next" with title "Fleet Agent Configuration")

set apiKey to text returned of (display dialog "Enter API Key (optional):" default answer "$CURRENT_KEY" buttons {"Cancel", "Next"} default button "Next" with title "Fleet Agent Configuration")

set reportInterval to text returned of (display dialog "Enter reporting interval (seconds):" default answer "$CURRENT_INTERVAL" buttons {"Cancel", "Configure"} default button "Configure" with title "Fleet Agent Configuration")

return serverURL & "|" & apiKey & "|" & reportInterval
APPLESCRIPT
)

if [ $? -ne 0 ]; then
    osascript -e 'display dialog "Configuration cancelled." buttons {"OK"} default button "OK" with title "Fleet Agent"'
    exit 0
fi

# Parse the result
SERVER_URL=$(echo "$CONFIG_RESULT" | cut -d'|' -f1)
API_KEY=$(echo "$CONFIG_RESULT" | cut -d'|' -f2)
INTERVAL=$(echo "$CONFIG_RESULT" | cut -d'|' -f3)

# Validate inputs
if [ -z "$SERVER_URL" ]; then
    osascript -e 'display dialog "Server URL is required!" buttons {"OK"} default button "OK" with icon stop with title "Configuration Error"'
    exit 1
fi

# Create config directory if it doesn't exist
mkdir -p "$(dirname "$CONFIG_FILE")"

# Write configuration
cat > "$CONFIG_FILE" << EOF
{
    "server_url": "$SERVER_URL",
    "api_key": "$API_KEY",
    "interval": $INTERVAL,
    "machine_id": null
}
EOF

chmod 644 "$CONFIG_FILE"

# Stop service if running
launchctl unload "$LAUNCHDAEMON" 2>/dev/null || true

# Start service
if [ -f "$LAUNCHDAEMON" ]; then
    launchctl load "$LAUNCHDAEMON"
    
    # Wait a moment
    sleep 2
    
    # Check if it's running
    if launchctl list | grep -q com.fleet.agent; then
        osascript -e 'display dialog "Fleet Agent configured and started successfully!\n\nThe agent is now reporting to your fleet server." buttons {"OK"} default button "OK" with title "Success!"'
    else
        osascript -e 'display dialog "Configuration saved, but service failed to start.\n\nCheck logs: /var/log/fleet-agent.error.log" buttons {"OK"} default button "OK" with icon caution with title "Warning"'
    fi
else
    osascript -e 'display dialog "Configuration saved!\n\nPlease install the Fleet Agent first." buttons {"OK"} default button "OK" with title "Configuration Saved"'
fi
SCRIPT_EOF

chmod +x "$APP_PATH/Contents/MacOS/configure"

echo "✅ Configuration app created: $APP_PATH"
