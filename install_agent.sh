#!/bin/bash
#
# ATLAS Fleet Agent & Server Installer
# Installs both Fleet Server and Agent with auto-start on login
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ATLAS Fleet Agent & Server Installer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get the actual user (not root if using sudo, otherwise current user)
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
    ACTUAL_HOME=$(eval echo ~$SUDO_USER)
    echo -e "${YELLOW}Note: Running with sudo, installing for user: $ACTUAL_USER${NC}"
else
    ACTUAL_USER="$USER"
    ACTUAL_HOME="$HOME"
fi

echo "User: $ACTUAL_USER"
echo "Home: $ACTUAL_HOME"
echo ""

# Configuration
PROJECT_DIR="$ACTUAL_HOME/CascadeProjects/windsurf-project-2"
LAUNCH_AGENTS_DIR="$ACTUAL_HOME/Library/LaunchAgents"

# Check if we're in the project directory
if [ ! -f "launch_atlas_with_config.py" ]; then
    echo -e "${RED}Error: Must run from project directory${NC}"
    echo "Expected: $PROJECT_DIR"
    exit 1
fi

# Check if encrypted config exists
if [ ! -f "$ACTUAL_HOME/.fleet-config.json.encrypted" ]; then
    echo -e "${YELLOW}⚠️  No encrypted config found${NC}"
    echo -e "${YELLOW}Setting up credentials...${NC}"
    echo ""
    
    # Run as the actual user, not root
    if [ -n "$SUDO_USER" ]; then
        sudo -u "$ACTUAL_USER" python3 repair_credentials.py
    else
        python3 repair_credentials.py
    fi
    
    echo ""
fi

# Get Python path
PYTHON_PATH=$(which python3)
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
        if [ -n "$SUDO_USER" ]; then
            # Run as the actual user, not root
            sudo -u "$ACTUAL_USER" /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        else
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi

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
        if [ -n "$SUDO_USER" ]; then
            sudo -u "$ACTUAL_USER" $BREW_CMD install $PACKAGES_TO_INSTALL 2>/dev/null && \
                echo -e "${GREEN}✅ Homebrew packages installed successfully${NC}" || \
                echo -e "${YELLOW}⚠️  Some packages could not be installed (non-critical)${NC}"
        else
            $BREW_CMD install $PACKAGES_TO_INSTALL 2>/dev/null && \
                echo -e "${GREEN}✅ Homebrew packages installed successfully${NC}" || \
                echo -e "${YELLOW}⚠️  Some packages could not be installed (non-critical)${NC}"
        fi
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

# Create LaunchAgents directory
mkdir -p "$LAUNCH_AGENTS_DIR"
chown "$ACTUAL_USER:staff" "$LAUNCH_AGENTS_DIR"

# Function to install a LaunchAgent plist
install_launchagent() {
    local plist_src="$1"
    local plist_name="$2"
    local label="$3"
    local plist_dest="$LAUNCH_AGENTS_DIR/$plist_name"
    
    if [ ! -f "$plist_src" ]; then
        echo -e "${RED}Error: $plist_src not found${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Installing $label...${NC}"
    
    # Substitute paths
    sed "s|/usr/local/bin/python3|$PYTHON_PATH|g; s|/Users/samraths|$ACTUAL_HOME|g" "$plist_src" > "$plist_dest"
    chown "$ACTUAL_USER:staff" "$plist_dest"
    chmod 644 "$plist_dest"
    
    # Unload if already loaded (run as user)
    if sudo -u "$ACTUAL_USER" launchctl list 2>/dev/null | grep -q "$label"; then
        echo "  Unloading existing $label..."
        sudo -u "$ACTUAL_USER" launchctl unload "$plist_dest" 2>/dev/null || true
        sleep 1
    fi
    
    # Load the plist (run as user)
    echo "  Loading $label..."
    sudo -u "$ACTUAL_USER" launchctl load "$plist_dest"
    
    echo -e "${GREEN}  ✅ $label installed${NC}"
}

# Install Fleet Server LaunchAgent
install_launchagent "com.atlas.fleetserver.plist" "com.atlas.fleetserver.plist" "com.atlas.fleetserver"

# Install ATLAS Agent LaunchAgent (with menu bar)
install_launchagent "com.atlas.agent.plist" "com.atlas.agent.plist" "com.atlas.agent"

# Wait for services to start
echo ""
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 5

# Check status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check Fleet Server
if sudo -u "$ACTUAL_USER" launchctl list 2>/dev/null | grep -q "com.atlas.fleetserver"; then
    echo -e "${GREEN}✅ Fleet Server: Running${NC}"
else
    echo -e "${YELLOW}⚠️  Fleet Server: Starting...${NC}"
fi

# Check Agent
if sudo -u "$ACTUAL_USER" launchctl list 2>/dev/null | grep -q "com.atlas.agent"; then
    echo -e "${GREEN}✅ ATLAS Agent: Running${NC}"
else
    echo -e "${YELLOW}⚠️  ATLAS Agent: Starting...${NC}"
fi

echo ""
echo -e "${GREEN}Features Enabled:${NC}"
echo "  ✅ Auto-start on login"
echo "  ✅ Auto-restart on crash"
echo "  ✅ Fleet Server on port 8768"
echo "  ✅ Agent with menu bar icon on port 8767"
echo "  ✅ API key auto-loaded from encrypted config"
echo ""
echo -e "${GREEN}Access:${NC}"
echo "  Fleet Dashboard: https://localhost:8768/dashboard"
echo "  Agent Dashboard: http://localhost:8767"
echo "  Menu Bar Icon:   Check top-right corner of screen"
echo ""
echo -e "${GREEN}Logs:${NC}"
echo "  Fleet Server: tail -f $ACTUAL_HOME/.atlas-fleetserver.log"
echo "  Agent:        tail -f $ACTUAL_HOME/.atlas-agent.log"
echo ""
echo -e "${GREEN}Management Commands:${NC}"
echo "  Status:   launchctl list | grep atlas"
echo "  Restart:  launchctl kickstart -k gui/\$(id -u)/com.atlas.agent"
echo "            launchctl kickstart -k gui/\$(id -u)/com.atlas.fleetserver"
echo "  Stop:     launchctl unload $LAUNCH_AGENTS_DIR/com.atlas.*.plist"
echo "  Start:    launchctl load $LAUNCH_AGENTS_DIR/com.atlas.*.plist"
echo ""
echo -e "${GREEN}Credential Management:${NC}"
echo "  Update password: python3 repair_credentials.py"
echo "  Update server:   python3 update_fleet_config.py"
echo "  View config:     python3 show_credentials.py"
echo ""

# Test endpoints
sleep 2
if curl -s -f http://localhost:8767/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Agent is responding on http://localhost:8767${NC}"
else
    echo -e "${YELLOW}⚠️  Agent starting up... (check logs in a moment)${NC}"
fi

if curl -s -k -f https://localhost:8768/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Fleet Server is responding on https://localhost:8768${NC}"
else
    echo -e "${YELLOW}⚠️  Fleet Server starting up... (check logs in a moment)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Both Fleet Server and Agent will start automatically on login!${NC}"
echo ""
