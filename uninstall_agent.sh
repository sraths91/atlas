#!/bin/bash
#
# Atlas Agent Uninstaller
# Removes the LaunchDaemon and stops the service
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Atlas Agent Uninstaller${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run with sudo${NC}"
    echo "Usage: sudo ./uninstall_agent.sh"
    exit 1
fi

LAUNCHDAEMON_PATH="/Library/LaunchDaemons/com.atlas.agent.plist"

# Check if service exists
if [ ! -f "$LAUNCHDAEMON_PATH" ]; then
    echo -e "${YELLOW}Atlas Agent is not installed${NC}"
    exit 0
fi

echo -e "${YELLOW}Stopping Atlas Agent...${NC}"

# Unload the service
if launchctl list | grep -q com.atlas.agent; then
    launchctl bootout system "$LAUNCHDAEMON_PATH" 2>/dev/null || true
    echo -e "${GREEN}✅ Agent stopped${NC}"
else
    echo -e "${YELLOW}Agent was not running${NC}"
fi

# Remove plist file
echo -e "${YELLOW}Removing LaunchDaemon...${NC}"
rm -f "$LAUNCHDAEMON_PATH"
echo -e "${GREEN}✅ LaunchDaemon removed${NC}"

# Ask about log files
echo ""
read -p "Remove log files? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f /var/log/atlas-agent.log
    rm -f /var/log/atlas-agent-error.log
    echo -e "${GREEN}✅ Log files removed${NC}"
else
    echo -e "${YELLOW}Log files preserved at:${NC}"
    echo "  /var/log/atlas-agent.log"
    echo "  /var/log/atlas-agent-error.log"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Uninstallation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Atlas Agent has been removed"
echo "To reinstall, run: sudo ./install_agent.sh"
echo ""
