#!/bin/bash
#
# Quick deployment script for Fleet Agent
# Usage: ./deploy_to_mac.sh username@hostname
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 username@hostname"
    echo ""
    echo "Example: $0 admin@192.168.1.100"
    echo "         $0 admin@macbook-pro.local"
    exit 1
fi

TARGET="$1"
INSTALLER="dist/fleet-agent-installer.sh"

# Check if installer exists
if [ ! -f "$INSTALLER" ]; then
    echo "Error: Installer not found at $INSTALLER"
    echo "Run ./create_installer.sh first"
    exit 1
fi

echo "======================================"
echo "Fleet Agent Deployment"
echo "======================================"
echo ""
echo "Target: $TARGET"
echo "Installer: $INSTALLER"
echo ""

# Copy installer
echo "Copying installer to $TARGET..."
scp "$INSTALLER" "$TARGET:~/" || {
    echo "Error: Failed to copy installer"
    exit 1
}

echo ""
echo "Running installer on $TARGET..."
echo "(You will be prompted for server details)"
echo ""

# Run installer
ssh -t "$TARGET" 'sudo ~/fleet-agent-installer.sh' || {
    echo ""
    echo "Error: Installation failed"
    exit 1
}

echo ""
echo "======================================"
echo "✅ Deployment Complete!"
echo "======================================"
echo ""
echo "To verify:"
echo "  ssh $TARGET 'tail -f /var/log/fleet-agent.log'"
echo ""
echo "To check status:"
echo "  ssh $TARGET 'sudo launchctl list | grep fleet'"
echo ""
