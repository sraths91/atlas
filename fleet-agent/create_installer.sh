#!/bin/bash
#
# Create a self-contained installer script for Fleet Agent
# This creates a single shell script that can be deployed to any Mac
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

OUTPUT_FILE="$SCRIPT_DIR/dist/fleet-agent-installer.sh"
mkdir -p "$SCRIPT_DIR/dist"

echo "Creating self-contained installer script..."

# Create the installer script
cat > "$OUTPUT_FILE" << 'INSTALLER_EOF'
#!/bin/bash
#
# Fleet Agent Self-Contained Installer
# This script will install and configure the Fleet Agent on macOS
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "=========================================="
echo "    Fleet Agent Installer v1.0.0"
echo "=========================================="
echo -e "${NC}\n"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root: sudo $0${NC}"
    exit 1
fi

# Configuration
INSTALL_DIR="/Library/Application Support/FleetAgent"
CONFIG_FILE="$INSTALL_DIR/config.json"
LAUNCHDAEMON="/Library/LaunchDaemons/com.fleet.agent.plist"
BIN_DIR="/usr/local/bin"

# Prompt for server details
echo -e "${YELLOW}Please enter your Fleet Server details:${NC}\n"

read -p "Fleet Server URL (e.g., http://192.168.1.100:8768): " SERVER_URL
read -p "API Key (leave empty if not using authentication): " API_KEY
read -p "Reporting interval in seconds [10]: " INTERVAL
INTERVAL=${INTERVAL:-10}

echo ""

# Stop existing service if running
if [ -f "$LAUNCHDAEMON" ]; then
    echo -e "${YELLOW}Stopping existing Fleet Agent...${NC}"
    launchctl unload "$LAUNCHDAEMON" 2>/dev/null || true
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install --upgrade psutil requests urllib3 >/dev/null 2>&1 || {
    echo -e "${RED}❌ Failed to install Python dependencies${NC}"
    echo "Make sure Python 3 and pip3 are installed"
    exit 1
}

# ============================================
# Install Homebrew packages for full functionality
# ============================================
echo -e "${YELLOW}Checking for Homebrew packages...${NC}"

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
        # Non-interactive install
        NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Re-check for Homebrew after installation
        if [ -x "/opt/homebrew/bin/brew" ]; then
            BREW_CMD="/opt/homebrew/bin/brew"
            # Add to PATH for this session
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -x "/usr/local/bin/brew" ]; then
            BREW_CMD="/usr/local/bin/brew"
            eval "$(/usr/local/bin/brew shellenv)"
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
    echo -e "${GREEN}✅ Homebrew found${NC}"

    # Required packages for core functionality
    PACKAGES_TO_INSTALL=""

    # smartmontools - SMART disk health monitoring
    if ! command -v smartctl &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL smartmontools"
    fi

    # speedtest-cli - Network speed testing
    if ! command -v speedtest-cli &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL speedtest-cli"
    fi

    # mtr - Network path analysis
    if ! command -v mtr &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL mtr"
    fi

    # Temperature monitoring - architecture specific
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        if ! command -v macmon &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL macmon"
        fi
    else
        if ! command -v osx-cpu-temp &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL osx-cpu-temp"
        fi
    fi

    # Install packages if any are needed
    if [ -n "$PACKAGES_TO_INSTALL" ]; then
        echo "Installing Homebrew packages:$PACKAGES_TO_INSTALL"
        $BREW_CMD install $PACKAGES_TO_INSTALL 2>/dev/null && \
            echo -e "${GREEN}✅ Homebrew packages installed${NC}" || \
            echo -e "${YELLOW}⚠️  Some packages could not be installed (non-critical)${NC}"
    else
        echo -e "${GREEN}✅ All required Homebrew packages already installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Homebrew not found. Some features will be limited.${NC}"
    echo "Install Homebrew: https://brew.sh"
fi

# Create installation directory
echo -e "${YELLOW}Creating installation directory...${NC}"
mkdir -p "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"

# Extract and install agent code
echo -e "${YELLOW}Installing Fleet Agent...${NC}"
mkdir -p "$BIN_DIR"

# Create the fleet-agent executable
cat > "$BIN_DIR/fleet-agent" << 'AGENT_EOF'
INSTALLER_EOF

# Embed the agent code
cat >> "$OUTPUT_FILE" << 'INSTALLER_EOF'
#!/usr/bin/env python3
"""Fleet Agent - Embedded standalone version"""
import json
import time
import socket
import platform
import logging
import sys
import signal
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import psutil
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError as e:
    print(f"Error: Missing dependency: {e}")
    print("Please install: pip3 install psutil requests urllib3")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FleetAgent:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.server_url = config['server_url'].rstrip('/')
        self.machine_id = config.get('machine_id') or socket.gethostname()
        self.api_key = config.get('api_key')
        self.interval = config.get('interval', 10)
        self.running = False
        self.session = requests.Session()
        self.session.verify = False
        
        logger.info(f"Agent initialized: {self.machine_id} -> {self.server_url}")
    
    def collect_metrics(self):
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net = psutil.net_io_counters()
            
            battery = None
            try:
                bat = psutil.sensors_battery()
                if bat:
                    battery = {'percent': bat.percent, 'plugged': bat.power_plugged}
            except:
                pass
            
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': time.time() - psutil.boot_time(),
                'cpu': {'percent': cpu, 'count': psutil.cpu_count()},
                'memory': {'total': mem.total, 'used': mem.used, 'percent': mem.percent},
                'disk': {'total': disk.total, 'used': disk.used, 'percent': disk.percent},
                'network': {'bytes_sent': net.bytes_sent, 'bytes_recv': net.bytes_recv},
                'battery': battery
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {}
    
    def send_report(self, metrics):
        try:
            # Get machine info
            machine_info = {
                'hostname': socket.gethostname(),
                'os': platform.system(),
                'os_version': platform.mac_ver()[0] if platform.system() == 'Darwin' else platform.version(),
                'architecture': platform.machine(),
                'total_memory': psutil.virtual_memory().total
            }
            
            payload = {
                'machine_id': self.machine_id,
                'machine_info': machine_info,
                'metrics': metrics
            }
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            response = self.session.post(
                f"{self.server_url}/api/fleet/report",
                json=payload,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug("Metrics reported successfully")
                return True
            else:
                logger.warning(f"Server returned {response.status_code}")
                return False
        except Exception as e:
            logger.debug(f"Connection error: {str(e)[:100]}")
            return False
    
    def run(self):
        self.running = True
        logger.info(f"Agent started (interval: {self.interval}s)")
        
        def signal_handler(sig, frame):
            logger.info("Shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while self.running:
            metrics = self.collect_metrics()
            if metrics:
                self.send_report(metrics)
            time.sleep(self.interval)
        
        logger.info("Agent stopped")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: fleet-agent <config_file>")
        sys.exit(1)
    
    agent = FleetAgent(sys.argv[1])
    agent.run()
AGENT_EOF
chmod +x "$BIN_DIR/fleet-agent"

# Create configuration file
echo -e "${YELLOW}Creating configuration...${NC}"
cat > "$CONFIG_FILE" << CONFIG_EOF
{
    "server_url": "$SERVER_URL",
    "api_key": "$API_KEY",
    "interval": $INTERVAL,
    "machine_id": null
}
CONFIG_EOF

chmod 644 "$CONFIG_FILE"

# Create LaunchDaemon
echo -e "${YELLOW}Installing LaunchDaemon...${NC}"
cat > "$LAUNCHDAEMON" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fleet.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/fleet-agent</string>
        <string>/Library/Application Support/FleetAgent/config.json</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>/var/log/fleet-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/fleet-agent.error.log</string>
    <key>ProcessType</key>
    <string>Background</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
PLIST_EOF

chmod 644 "$LAUNCHDAEMON"
chown root:wheel "$LAUNCHDAEMON"

# Create log files
touch /var/log/fleet-agent.log
touch /var/log/fleet-agent.error.log
chmod 644 /var/log/fleet-agent.log
chmod 644 /var/log/fleet-agent.error.log

# Load the service
echo -e "${YELLOW}Starting Fleet Agent service...${NC}"
launchctl load "$LAUNCHDAEMON"

# Wait a moment for service to start
sleep 2

# Check if it's running
if launchctl list | grep -q com.fleet.agent; then
    echo -e "\n${GREEN}=========================================="
    echo "✅ Fleet Agent installed successfully!"
    echo -e "==========================================${NC}\n"
    echo "Configuration: $CONFIG_FILE"
    echo "Logs: /var/log/fleet-agent.log"
    echo ""
    echo "Check status: sudo launchctl list | grep fleet"
    echo "View logs: tail -f /var/log/fleet-agent.log"
    echo "Stop: sudo launchctl unload $LAUNCHDAEMON"
    echo ""
else
    echo -e "\n${YELLOW}⚠️  Service installed but may not be running${NC}"
    echo "Check logs: tail -f /var/log/fleet-agent.error.log"
fi
INSTALLER_EOF

chmod +x "$OUTPUT_FILE"

echo ""
echo "✅ Self-contained installer created!"
echo ""
echo "Location: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "Deploy to any Mac with:"
echo "  scp $OUTPUT_FILE admin@mac:~/"
echo "  ssh admin@mac 'sudo ~/fleet-agent-installer.sh'"
echo ""
