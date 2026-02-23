#!/bin/bash
#
# Build macOS installer package for Fleet Agent
# Creates a self-contained .pkg with all dependencies
#
# Usage:
#   ./build_macos_pkg.sh                                    # Basic package (requires manual config)
#   ./build_macos_pkg.sh --server-url URL --api-key KEY    # Pre-configured package
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
SERVER_URL=""
API_KEY=""
INTERVAL="10"

while [[ $# -gt 0 ]]; do
    case $1 in
        --server-url)
            SERVER_URL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--server-url URL] [--api-key KEY] [--interval SECONDS]"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}======================================"
echo "Fleet Agent Package Builder"
echo -e "======================================${NC}\n"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
PKG_NAME="FleetAgent"
PKG_VERSION="1.0.0"
PKG_IDENTIFIER="com.fleet.agent"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"
PAYLOAD_DIR="$BUILD_DIR/payload"
RESOURCES_DIR="$SCRIPT_DIR/resources"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

# Show configuration
if [ -n "$SERVER_URL" ]; then
    echo -e "${BLUE}📦 Pre-configured Package${NC}"
    echo -e "   Server URL: ${GREEN}$SERVER_URL${NC}"
    if [ -n "$API_KEY" ]; then
        echo -e "   API Key: ${GREEN}[configured]${NC}"
    else
        echo -e "   API Key: ${YELLOW}[not set]${NC}"
    fi
    echo -e "   Interval: ${GREEN}${INTERVAL}s${NC}"
    echo -e "   ${GREEN}✓ Package will be ready to use immediately after installation${NC}"
else
    echo -e "${YELLOW}⚠️  Basic Package (requires manual configuration)${NC}"
    echo -e "   Users will need to run Configuration app after installation\n"
fi
echo ""

echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR" "$PAYLOAD_DIR"

# Create virtual environment for building
echo -e "\n${YELLOW}Creating virtual environment...${NC}"
python3 -m venv "$BUILD_DIR/venv"
source "$BUILD_DIR/venv/bin/activate"

# Install the package and its dependencies
echo -e "\n${YELLOW}Installing fleet-agent and dependencies...${NC}"
pip install --upgrade pip setuptools wheel
pip install -e .

# Create configuration app
echo -e "\n${YELLOW}Creating configuration app...${NC}"
chmod +x "$SCRIPT_DIR/create_config_app.sh"
"$SCRIPT_DIR/create_config_app.sh"

# Create payload structure
echo -e "\n${YELLOW}Building package payload...${NC}"

# Install to payload directory
mkdir -p "$PAYLOAD_DIR/usr/local/bin"
mkdir -p "$PAYLOAD_DIR/Library/Python/3.9/lib/python/site-packages"
mkdir -p "$PAYLOAD_DIR/tmp/fleet-agent-resources"
mkdir -p "$PAYLOAD_DIR/Applications"

# Copy the installed files
echo "Copying fleet-agent executable..."
cp "$BUILD_DIR/venv/bin/fleet-agent" "$PAYLOAD_DIR/usr/local/bin/"
chmod 755 "$PAYLOAD_DIR/usr/local/bin/fleet-agent"

# Bundle Python dependencies
echo "Bundling Python dependencies..."
SITE_PACKAGES="$BUILD_DIR/venv/lib/python*/site-packages"
for pkg in fleet_agent psutil requests urllib3 certifi charset_normalizer idna; do
    if [ -d $SITE_PACKAGES/$pkg ] || [ -d $SITE_PACKAGES/$pkg-*.dist-info ]; then
        echo "  - $pkg"
        cp -R $SITE_PACKAGES/$pkg* "$PAYLOAD_DIR/Library/Python/3.9/lib/python/site-packages/" 2>/dev/null || true
    fi
done

# Copy resource files
echo "Copying resources..."
cp "$RESOURCES_DIR/com.fleet.agent.plist" "$PAYLOAD_DIR/tmp/fleet-agent-resources/"

# Create config template with optional pre-configuration
if [ -n "$SERVER_URL" ]; then
    echo "Creating pre-configured config template..."
    cat > "$PAYLOAD_DIR/tmp/fleet-agent-resources/config.json.template" << EOF
{
    "server_url": "$SERVER_URL",
    "api_key": "$API_KEY",
    "interval": $INTERVAL,
    "machine_id": null
}
EOF
else
    echo "Creating default config template..."
    cp "$RESOURCES_DIR/config.json.template" "$PAYLOAD_DIR/tmp/fleet-agent-resources/"
fi

# Copy configuration app to Applications
echo "Copying configuration app..."
cp -R "$BUILD_DIR/app/Fleet Agent Configuration.app" "$PAYLOAD_DIR/Applications/"

# Make scripts executable
echo "Preparing installation scripts..."
chmod +x "$SCRIPTS_DIR/preinstall"
chmod +x "$SCRIPTS_DIR/postinstall"

# Build component package
echo -e "\n${YELLOW}Building component package...${NC}"
pkgbuild \
    --root "$PAYLOAD_DIR" \
    --identifier "$PKG_IDENTIFIER" \
    --version "$PKG_VERSION" \
    --scripts "$SCRIPTS_DIR" \
    --install-location "/" \
    "$BUILD_DIR/${PKG_NAME}-component.pkg"

# Create distribution XML
echo -e "\n${YELLOW}Creating distribution package...${NC}"
cat > "$BUILD_DIR/distribution.xml" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>Fleet Agent</title>
    <organization>com.fleet</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="true" hostArchitectures="x86_64,arm64"/>
    
    <welcome file="welcome.html" mime-type="text/html"/>
    <conclusion file="conclusion.html" mime-type="text/html"/>
    
    <pkg-ref id="$PKG_IDENTIFIER"/>
    
    <choices-outline>
        <line choice="default">
            <line choice="$PKG_IDENTIFIER"/>
        </line>
    </choices-outline>
    
    <choice id="default"/>
    
    <choice id="$PKG_IDENTIFIER" visible="false">
        <pkg-ref id="$PKG_IDENTIFIER"/>
    </choice>
    
    <pkg-ref id="$PKG_IDENTIFIER" version="$PKG_VERSION" onConclusion="none">
        ${PKG_NAME}-component.pkg
    </pkg-ref>
</installer-gui-script>
EOF

# Create welcome and conclusion HTML
cat > "$BUILD_DIR/welcome.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }
        h1 { color: #007AFF; }
    </style>
</head>
<body>
    <h1>Fleet Agent Installation</h1>
    <p>This installer will install the Fleet Agent on your Mac.</p>
    <p><strong>The Fleet Agent will:</strong></p>
    <ul>
        <li>Monitor system metrics (CPU, memory, disk, network)</li>
        <li>Report data to your fleet management server</li>
        <li>Run automatically at system startup</li>
    </ul>
    <p><strong>After installation:</strong></p>
    <ol>
        <li>Open <strong>Fleet Agent Configuration</strong> from your Applications folder</li>
        <li>Enter your fleet server URL and API key</li>
        <li>The agent will start automatically!</li>
    </ol>
    <p><em>It's that simple! No command-line needed.</em></p>
</body>
</html>
EOF

# Create conclusion screen (different based on pre-configuration)
if [ -n "$SERVER_URL" ]; then
    # Pre-configured version
    cat > "$BUILD_DIR/conclusion.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
            padding: 20px;
            line-height: 1.6;
        }
        h1 { color: #34C759; }
        .step { 
            background: #f0f8ff; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 15px 0;
            border-left: 4px solid #007AFF;
        }
        .important {
            font-size: 18px;
            font-weight: bold;
            color: #007AFF;
            margin: 20px 0;
        }
        code { 
            background-color: #f5f5f5; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-family: 'Monaco', monospace; 
        }
    </style>
</head>
<body>
    <h1>✅ Installation Complete!</h1>
    <p>The Fleet Agent has been installed successfully.</p>
    
    <div class="important">
        📱 One More Step: Configure the Agent
    </div>
    
    <div class="step">
        <h3>How to Configure:</h3>
        <ol>
            <li>Go to your <strong>Applications</strong> folder</li>
            <li>Double-click <strong>Fleet Agent Configuration</strong></li>
            <li>Enter your fleet server URL (e.g., <code>http://192.168.1.100:8768</code>)</li>
            <li>Enter your API key (if required)</li>
            <li>Click <strong>Configure</strong></li>
        </ol>
        <p><strong>That's it!</strong> The agent will start automatically.</p>
    </div>
    
    <h3>Verify It's Working:</h3>
    <p>Check your fleet dashboard at: <code>http://your-server:8768/dashboard</code></p>
    <p>Your Mac should appear within 10 seconds!</p>
    
    <h3>Need Help?</h3>
    <p>• Configuration app location: <code>/Applications/Fleet Agent Configuration.app</code></p>
    <p>• View logs: <code>/var/log/fleet-agent.log</code></p>
    <p>• To reconfigure: Just run the Configuration app again</p>
</body>
</html>
EOF
else
    # Pre-configured version - no configuration needed
    cat > "$BUILD_DIR/conclusion.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
            padding: 20px;
            line-height: 1.6;
        }
        h1 { color: #34C759; }
        .success { 
            background: #d4edda; 
            padding: 20px; 
            border-radius: 8px; 
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }
        .info {
            background: #f0f8ff;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #007AFF;
        }
        code { 
            background-color: #f5f5f5; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-family: 'Monaco', monospace; 
        }
    </style>
</head>
<body>
    <h1>🎉 Installation Complete!</h1>
    
    <div class="success">
        <h2>✅ Fleet Agent is Ready!</h2>
        <p><strong>The agent has been pre-configured and is now running.</strong></p>
        <p>Your Mac is already reporting to the fleet server!</p>
    </div>
    
    <div class="info">
        <h3>What's Running:</h3>
        <p>The Fleet Agent is now:</p>
        <ul>
            <li>✓ Monitoring system metrics (CPU, memory, disk, network)</li>
            <li>✓ Reporting to your fleet management server</li>
            <li>✓ Running automatically in the background</li>
            <li>✓ Set to start on every boot</li>
        </ul>
    </div>
    
    <h3>Verify It's Working:</h3>
    <p>1. Open your fleet dashboard</p>
    <p>2. Your Mac should appear in the list within 10 seconds</p>
    <p>3. Metrics will update every few seconds</p>
    
    <h3>View Logs (Optional):</h3>
    <p>Monitor agent activity: <code>/var/log/fleet-agent.log</code></p>
    
    <h3>Need to Reconfigure?</h3>
    <p>Run <strong>Fleet Agent Configuration</strong> from your Applications folder</p>
    
    <p><em>No further action required - you're all set!</em></p>
</body>
</html>
EOF
fi

# Build final product package
productbuild \
    --distribution "$BUILD_DIR/distribution.xml" \
    --package-path "$BUILD_DIR" \
    --resources "$BUILD_DIR" \
    "$DIST_DIR/${PKG_NAME}.pkg"

# Deactivate virtual environment
deactivate

echo -e "\n${GREEN}======================================"
echo "✅ Package built successfully!"
echo -e "======================================${NC}\n"
echo -e "Package location: ${GREEN}$DIST_DIR/${PKG_NAME}.pkg${NC}"
echo -e "Package size: $(du -h "$DIST_DIR/${PKG_NAME}.pkg" | cut -f1)"
echo ""
echo -e "${YELLOW}Installation:${NC}"
echo "  sudo installer -pkg $DIST_DIR/${PKG_NAME}.pkg -target /"
echo ""
echo -e "${YELLOW}After installation:${NC}"
echo "  1. Edit: /Library/Application Support/FleetAgent/config.json"
echo "  2. Start: sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist"
echo ""
