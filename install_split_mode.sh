#!/bin/bash
#
# ATLAS Split-Mode Installer
# Fleet Server + Core Agent start at boot (LaunchDaemons)
# Menu Bar app starts at login (LaunchAgent)
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ATLAS Split-Mode Installer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run with sudo${NC}"
    echo "Usage: sudo ./install_split_mode.sh"
    exit 1
fi

# Get actual user
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "User: $ACTUAL_USER"
echo "Home: $ACTUAL_HOME"
echo ""

# Configuration
INSTALL_DIR="$ACTUAL_HOME/Library/FleetAgent"
LAUNCH_DAEMONS_DIR="/Library/LaunchDaemons"
LAUNCH_AGENTS_DIR="$ACTUAL_HOME/Library/LaunchAgents"
FLEET_PORT="8778"

# Determine install source (script's directory or INSTALL_DIR if already installed)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$SCRIPT_DIR/atlas" ]; then
    SOURCE_DIR="$SCRIPT_DIR"
else
    SOURCE_DIR="$INSTALL_DIR"
fi

# Copy files to install location if running from a package
if [ "$SOURCE_DIR" != "$INSTALL_DIR" ]; then
    echo "Installing files to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cp -r "$SOURCE_DIR/atlas" "$INSTALL_DIR/"
    cp "$SOURCE_DIR"/*.py "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SOURCE_DIR"/*.json "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SOURCE_DIR"/*.plist "$INSTALL_DIR/" 2>/dev/null || true
    chown -R "$ACTUAL_USER:staff" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR" || {
    echo -e "${RED}Error: Install directory not found: $INSTALL_DIR${NC}"
    exit 1
}

# Detect Python path
PYTHON_PATH=$(which python3)

# Check if encrypted config exists
if [ ! -f "$ACTUAL_HOME/.fleet-config.json.encrypted" ]; then
    echo -e "${YELLOW}⚠️  No encrypted config found${NC}"
    echo -e "${YELLOW}Setting up credentials...${NC}"
    echo ""
    
    sudo -u "$ACTUAL_USER" python3 repair_credentials.py
    echo ""
fi

echo -e "${YELLOW}Using Python: $PYTHON_PATH${NC}"
echo ""

# ============================================
# Install Homebrew packages for full functionality
# ============================================
echo -e "${YELLOW}Installing Homebrew packages for enhanced monitoring...${NC}"
echo ""

# Check if Homebrew is installed, install if not
BREW_CMD=""
if [ -x "/opt/homebrew/bin/brew" ]; then
    BREW_CMD="/opt/homebrew/bin/brew"
elif [ -x "/usr/local/bin/brew" ]; then
    BREW_CMD="/usr/local/bin/brew"
fi

# Install Homebrew if not found
if [ -z "$BREW_CMD" ]; then
    echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
    echo ""
    echo "This will install Homebrew (https://brew.sh) - the missing package manager for macOS."
    echo "Homebrew is required for full monitoring functionality."
    echo ""
    read -p "Install Homebrew now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing Homebrew (this may take a few minutes)..."
        # Run as the actual user, not root
        sudo -u "$ACTUAL_USER" /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Re-check for Homebrew after installation
        if [ -x "/opt/homebrew/bin/brew" ]; then
            BREW_CMD="/opt/homebrew/bin/brew"
        elif [ -x "/usr/local/bin/brew" ]; then
            BREW_CMD="/usr/local/bin/brew"
        fi

        if [ -n "$BREW_CMD" ]; then
            echo -e "${GREEN}✅ Homebrew installed successfully!${NC}"
        else
            echo -e "${YELLOW}⚠️  Homebrew installation may have failed. Continuing without Homebrew packages.${NC}"
        fi
    else
        echo "Skipping Homebrew installation. Some monitoring features will be limited."
    fi
fi

if [ -n "$BREW_CMD" ]; then
    echo -e "${GREEN}✅ Homebrew found at: $BREW_CMD${NC}"

    # Required packages for core functionality
    PACKAGES_TO_INSTALL=""

    # smartmontools - SMART disk health monitoring
    if ! command -v smartctl &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL smartmontools"
        echo "  • smartmontools (SMART disk health)"
    else
        echo -e "  ${GREEN}✅ smartmontools already installed${NC}"
    fi

    # speedtest-cli - Network speed testing
    if ! command -v speedtest-cli &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL speedtest-cli"
        echo "  • speedtest-cli (network speed tests)"
    else
        echo -e "  ${GREEN}✅ speedtest-cli already installed${NC}"
    fi

    # mtr - Network path analysis
    if ! command -v mtr &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL mtr"
        echo "  • mtr (network diagnostics)"
    else
        echo -e "  ${GREEN}✅ mtr already installed${NC}"
    fi

    # Temperature monitoring - architecture specific
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        if ! command -v macmon &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL macmon"
            echo "  • macmon (CPU temperature - Apple Silicon)"
        else
            echo -e "  ${GREEN}✅ macmon already installed${NC}"
        fi
    else
        if ! command -v osx-cpu-temp &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL osx-cpu-temp"
            echo "  • osx-cpu-temp (CPU temperature - Intel)"
        else
            echo -e "  ${GREEN}✅ osx-cpu-temp already installed${NC}"
        fi
    fi

    # Install packages if any are needed
    if [ -n "$PACKAGES_TO_INSTALL" ]; then
        echo ""
        echo "Installing packages..."
        sudo -u "$ACTUAL_USER" $BREW_CMD install $PACKAGES_TO_INSTALL 2>/dev/null && \
            echo -e "${GREEN}✅ Homebrew packages installed successfully${NC}" || \
            echo -e "${YELLOW}⚠️  Some packages could not be installed (non-critical)${NC}"
    else
        echo -e "${GREEN}✅ All required Homebrew packages already installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Homebrew not found. Some monitoring features will be limited.${NC}"
    echo ""
    echo "To enable all monitoring features, install Homebrew:"
    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo ""
    echo "Then install required packages:"
    echo "  brew install smartmontools speedtest-cli mtr"
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        echo "  brew install macmon"
    else
        echo "  brew install osx-cpu-temp"
    fi
fi
echo ""

# Stop existing services
echo -e "${YELLOW}Stopping existing services...${NC}"
launchctl bootout system /Library/LaunchDaemons/com.atlas.fleetserver.plist 2>/dev/null || true
launchctl bootout system /Library/LaunchDaemons/com.atlas.agent.core.plist 2>/dev/null || true
sudo -u "$ACTUAL_USER" launchctl unload "$LAUNCH_AGENTS_DIR/com.atlas.menubar.plist" 2>/dev/null || true
sudo -u "$ACTUAL_USER" launchctl unload "$LAUNCH_AGENTS_DIR/com.atlas.agent.plist" 2>/dev/null || true
sudo -u "$ACTUAL_USER" launchctl unload "$LAUNCH_AGENTS_DIR/com.atlas.fleetserver.plist" 2>/dev/null || true
sleep 2

# Create log files with proper permissions
echo -e "${YELLOW}Setting up log files...${NC}"
touch /var/log/atlas-fleetserver.log /var/log/atlas-fleetserver.error.log
touch /var/log/atlas-agent.log /var/log/atlas-agent.error.log
chown "$ACTUAL_USER:staff" /var/log/atlas-*.log
chmod 644 /var/log/atlas-*.log

# Install Fleet Server LaunchDaemon
echo -e "${YELLOW}Installing Fleet Server (boot-time)...${NC}"
sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__ACTUAL_USER__|$ACTUAL_USER|g; s|__ACTUAL_HOME__|$ACTUAL_HOME|g; s|__FLEET_PORT__|$FLEET_PORT|g" \
    com.atlas.fleetserver.daemon.plist > "$LAUNCH_DAEMONS_DIR/com.atlas.fleetserver.plist"
chown root:wheel "$LAUNCH_DAEMONS_DIR/com.atlas.fleetserver.plist"
chmod 644 "$LAUNCH_DAEMONS_DIR/com.atlas.fleetserver.plist"
launchctl bootstrap system "$LAUNCH_DAEMONS_DIR/com.atlas.fleetserver.plist"
echo -e "${GREEN}  ✅ Fleet Server installed on port $FLEET_PORT (starts at boot)${NC}"

# Install Core Agent LaunchDaemon
echo -e "${YELLOW}Installing Core Agent (boot-time)...${NC}"
sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__ACTUAL_USER__|$ACTUAL_USER|g; s|__ACTUAL_HOME__|$ACTUAL_HOME|g; s|__FLEET_PORT__|$FLEET_PORT|g" \
    com.atlas.agent.daemon.plist > "$LAUNCH_DAEMONS_DIR/com.atlas.agent.core.plist"
chown root:wheel "$LAUNCH_DAEMONS_DIR/com.atlas.agent.core.plist"
chmod 644 "$LAUNCH_DAEMONS_DIR/com.atlas.agent.core.plist"
launchctl bootstrap system "$LAUNCH_DAEMONS_DIR/com.atlas.agent.core.plist"
echo -e "${GREEN}  ✅ Core Agent installed on port 8767 (starts at boot)${NC}"

# Install Menu Bar LaunchAgent
echo -e "${YELLOW}Installing Menu Bar App (login-time)...${NC}"
mkdir -p "$LAUNCH_AGENTS_DIR"
chown "$ACTUAL_USER:staff" "$LAUNCH_AGENTS_DIR"
sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__ACTUAL_USER__|$ACTUAL_USER|g; s|__ACTUAL_HOME__|$ACTUAL_HOME|g; s|__FLEET_PORT__|$FLEET_PORT|g" \
    com.atlas.menubar.plist > "$LAUNCH_AGENTS_DIR/com.atlas.menubar.plist"
chown "$ACTUAL_USER:staff" "$LAUNCH_AGENTS_DIR/com.atlas.menubar.plist"
chmod 644 "$LAUNCH_AGENTS_DIR/com.atlas.menubar.plist"
sudo -u "$ACTUAL_USER" launchctl load "$LAUNCH_AGENTS_DIR/com.atlas.menubar.plist"
echo -e "${GREEN}  ✅ Menu Bar App installed (starts at login)${NC}"

# Wait for services
echo ""
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 5

# Check status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check daemons
if launchctl list | grep -q "com.atlas.fleetserver"; then
    echo -e "${GREEN}✅ Fleet Server: Running (boot-time)${NC}"
else
    echo -e "${YELLOW}⚠️  Fleet Server: Starting...${NC}"
fi

if launchctl list | grep -q "com.atlas.agent.core"; then
    echo -e "${GREEN}✅ Core Agent: Running (boot-time)${NC}"
else
    echo -e "${YELLOW}⚠️  Core Agent: Starting...${NC}"
fi

# Check menu bar
if sudo -u "$ACTUAL_USER" launchctl list 2>/dev/null | grep -q "com.atlas.menubar"; then
    echo -e "${GREEN}✅ Menu Bar: Running (login-time)${NC}"
else
    echo -e "${YELLOW}⚠️  Menu Bar: Starting...${NC}"
fi

echo ""
echo -e "${GREEN}Boot-Time Services (LaunchDaemons):${NC}"
echo "  ✅ Fleet Server on port $FLEET_PORT"
echo "  ✅ Core Agent on port 8767"
echo "  ✅ Start immediately at boot (before login)"
echo "  ✅ Auto-restart on crash"
echo ""
echo -e "${GREEN}Login-Time Services (LaunchAgents):${NC}"
echo "  ✅ Menu Bar icon with status"
echo "  ✅ Start when user logs in"
echo "  ✅ GUI access enabled"
echo ""
echo -e "${GREEN}Access:${NC}"
echo "  Fleet Dashboard: https://localhost:$FLEET_PORT/dashboard"
echo "  Agent Dashboard: http://localhost:8767"
echo "  Menu Bar Icon:   Check top-right corner after login"
echo ""
echo -e "${GREEN}Logs:${NC}"
echo "  Fleet Server: tail -f /var/log/atlas-fleetserver.log"
echo "  Core Agent:   tail -f /var/log/atlas-agent.log"
echo "  Menu Bar:     tail -f $ACTUAL_HOME/.atlas-menubar.log"
echo ""
echo -e "${GREEN}Management Commands:${NC}"
echo "  Status (daemons): sudo launchctl list | grep atlas"
echo "  Status (menubar): launchctl list | grep atlas"
echo "  Restart server:   sudo launchctl kickstart -k system/com.atlas.fleetserver"
echo "  Restart agent:    sudo launchctl kickstart -k system/com.atlas.agent.core"
echo "  Restart menubar:  launchctl kickstart -k gui/\$(id -u)/com.atlas.menubar"
echo ""

# Test endpoints
sleep 2
if curl -s -f http://localhost:8767/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Agent is responding on http://localhost:8767${NC}"
else
    echo -e "${YELLOW}⚠️  Agent starting up... (check logs)${NC}"
fi

if curl -s -k -f https://localhost:$FLEET_PORT/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Fleet Server is responding on https://localhost:$FLEET_PORT${NC}"
else
    echo -e "${YELLOW}⚠️  Fleet Server starting up... (check logs)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Fleet Server and Core Agent start at BOOT!${NC}"
echo -e "${GREEN}🎉 Menu Bar icon appears at LOGIN!${NC}"
echo ""
