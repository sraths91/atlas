#!/usr/bin/env python3
"""
Fleet Agent Package Builder
Creates downloadable installer packages for client Macs
"""

import os
import json
import tempfile
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentPackageBuilder:
    """Build Fleet Agent installer packages"""
    
    def __init__(self, config_path=None):
        """Initialize builder with config (supports encrypted configs)"""
        if config_path is None:
            config_path = Path.home() / ".fleet-config.json"
        
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path):
        """Load config from file, supporting both encrypted and plaintext formats"""
        config_path = Path(config_path)
        
        # Try using FleetConfig which handles encryption
        try:
            from .fleet_config import FleetConfig
            fleet_config = FleetConfig(str(config_path))
            config = fleet_config.config
            if config:
                logger.info("Loaded configuration via FleetConfig (encryption-aware)")
                return config
        except Exception as e:
            logger.debug(f"FleetConfig load failed: {e}")
        
        # Try encrypted config directly
        encrypted_path = Path(str(config_path) + ".encrypted")
        if encrypted_path.exists():
            try:
                from .fleet_config_encryption import EncryptedConfigManager
                manager = EncryptedConfigManager(str(config_path))
                config = manager.decrypt_config()
                if config:
                    logger.info(f"Loaded encrypted configuration from {encrypted_path}")
                    return config
            except Exception as e:
                logger.debug(f"Encrypted config load failed: {e}")
        
        # Fall back to plaintext
        if config_path.exists():
            with open(config_path, 'r') as f:
                logger.info(f"Loaded plaintext configuration from {config_path}")
                return json.load(f)
        
        raise FileNotFoundError(
            f"No configuration found. Checked:\n"
            f"  - {config_path}\n"
            f"  - {encrypted_path}\n"
            f"Please run the setup wizard or create a config file."
        )
    
    def _save_encryption_key(self, encryption_key):
        """Save a newly generated encryption key back to the config"""
        try:
            # Update config in memory
            if 'server' not in self.config:
                self.config['server'] = {}
            self.config['server']['encryption_key'] = encryption_key
            
            # Try to save using encrypted config manager
            config_path = Path.home() / ".fleet-config.json"
            try:
                from .fleet_config_encryption import EncryptedConfigManager
                manager = EncryptedConfigManager(str(config_path))
                manager.encrypt_config(self.config)
                logger.info("Saved encryption key to encrypted config")
            except Exception as e:
                logger.warning(f"Could not save to encrypted config: {e}")
                # Fall back to updating in-memory only
        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")
    
    def _build_pkg(self, payload_dir, output_path, identifier, version="1.0.0", install_location="/Library/FleetAgent"):
        """Build a macOS .pkg installer using pkgbuild.
        
        Args:
            payload_dir: Directory containing files to install
            output_path: Path for the output .pkg file
            identifier: Bundle identifier (e.g., com.atlas.fleet-agent)
            version: Package version
            install_location: Where to install files on target system
            
        Returns:
            Path to the created .pkg file, or None if pkgbuild failed
        """
        try:
            # Create scripts directory for pre/post install scripts
            scripts_dir = payload_dir.parent / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            
            # Create postinstall script
            postinstall = scripts_dir / "postinstall"
            postinstall_content = f'''#!/bin/bash
#
# ATLAS Agent Post-Install Script
#

INSTALL_DIR="{install_location}"
ACTUAL_USER="${{SUDO_USER:-$USER}}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "Running post-install for user: $ACTUAL_USER"

# Create user directories
mkdir -p "$ACTUAL_HOME/.fleet"
mkdir -p "$ACTUAL_HOME/Library/Logs"

# Set ownership
chown -R $ACTUAL_USER "$INSTALL_DIR" 2>/dev/null || true
chown -R $ACTUAL_USER "$ACTUAL_HOME/.fleet" 2>/dev/null || true

# Install Python dependencies
echo "Installing Python dependencies..."
sudo -u $ACTUAL_USER pip3 install --user psutil requests cryptography bcrypt rumps PyJWT 2>/dev/null || true

# ============================================
# Install Homebrew packages for full functionality
# ============================================
echo ""
echo "Checking for Homebrew and installing required packages..."

# Check if Homebrew is installed, install if not
HOMEBREW_PREFIX=""
if [ -x "/opt/homebrew/bin/brew" ]; then
    HOMEBREW_PREFIX="/opt/homebrew"
    BREW_CMD="/opt/homebrew/bin/brew"
elif [ -x "/usr/local/bin/brew" ]; then
    HOMEBREW_PREFIX="/usr/local"
    BREW_CMD="/usr/local/bin/brew"
fi

# Install Homebrew if not found (non-interactive for PKG deployment)
if [ -z "$BREW_CMD" ]; then
    echo "Homebrew not found. Attempting to install Homebrew..."

    if [ -n "$ACTUAL_USER" ] && [ "$ACTUAL_USER" != "root" ]; then
        echo "Installing Homebrew for user: $ACTUAL_USER"

        # Non-interactive Homebrew installation
        sudo -u "$ACTUAL_USER" NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>/dev/null || true

        # Re-check for Homebrew after installation
        if [ -x "/opt/homebrew/bin/brew" ]; then
            HOMEBREW_PREFIX="/opt/homebrew"
            BREW_CMD="/opt/homebrew/bin/brew"
            echo "Homebrew installed successfully at /opt/homebrew/bin/brew"
        elif [ -x "/usr/local/bin/brew" ]; then
            HOMEBREW_PREFIX="/usr/local"
            BREW_CMD="/usr/local/bin/brew"
            echo "Homebrew installed successfully at /usr/local/bin/brew"
        else
            echo "Homebrew installation failed. Continuing without Homebrew packages."
        fi
    else
        echo "Cannot install Homebrew as root. Skipping."
    fi
fi

if [ -n "$BREW_CMD" ]; then
    echo "Homebrew found at: $BREW_CMD"

    # Define required packages with their binary names for checking
    # Format: "package_name:binary_name:description"
    REQUIRED_PACKAGES=(
        "smartmontools:smartctl:SMART disk health monitoring"
        "speedtest-cli:speedtest-cli:Network speed testing"
    )

    # Define recommended packages (optional but enhance functionality)
    RECOMMENDED_PACKAGES=(
        "mtr:mtr:Network path analysis (traceroute + ping)"
    )

    # Detect CPU architecture for temperature monitoring
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        # Apple Silicon - use macmon (sudoless)
        TEMP_PACKAGES=("macmon:macmon:CPU temperature monitoring (Apple Silicon)")
    else
        # Intel - use osx-cpu-temp
        TEMP_PACKAGES=("osx-cpu-temp:osx-cpu-temp:CPU temperature monitoring (Intel)")
    fi

    # Combine all packages
    ALL_PACKAGES=("${{REQUIRED_PACKAGES[@]}}" "${{RECOMMENDED_PACKAGES[@]}}" "${{TEMP_PACKAGES[@]}}")

    INSTALLED_COUNT=0
    SKIPPED_COUNT=0

    for pkg_info in "${{ALL_PACKAGES[@]}}"; do
        IFS=':' read -r pkg_name binary_name description <<< "$pkg_info"

        # Check if binary already exists
        if [ -x "$HOMEBREW_PREFIX/bin/$binary_name" ] || [ -x "$HOMEBREW_PREFIX/sbin/$binary_name" ] || command -v "$binary_name" &> /dev/null; then
            echo "  ✓ $pkg_name already installed ($description)"
            ((SKIPPED_COUNT++))
        else
            echo "  Installing $pkg_name ($description)..."
            if sudo -u $ACTUAL_USER $BREW_CMD install "$pkg_name" 2>/dev/null; then
                echo "    ✓ $pkg_name installed successfully"
                ((INSTALLED_COUNT++))
            else
                echo "    ⚠ Could not install $pkg_name (non-critical, some features may be limited)"
            fi
        fi
    done

    echo ""
    echo "Homebrew packages: $INSTALLED_COUNT installed, $SKIPPED_COUNT already present"

else
    echo "⚠ Homebrew not found. Some features will be limited."
    echo "  To install Homebrew, visit: https://brew.sh"
    echo ""
    echo "  After installing Homebrew, run these commands for full functionality:"
    echo "    brew install smartmontools  # SMART disk health"
    echo "    brew install speedtest-cli  # Network speed tests"
    echo "    brew install mtr            # Network path analysis"
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        echo "    brew install macmon         # CPU temperature (Apple Silicon)"
    else
        echo "    brew install osx-cpu-temp   # CPU temperature (Intel)"
    fi
fi

# ============================================
# Install LaunchAgent/LaunchDaemon plists with path substitution
# ============================================
LAUNCH_AGENT_DIR="$ACTUAL_HOME/Library/LaunchAgents"
LAUNCH_DAEMON_DIR="/Library/LaunchDaemons"
mkdir -p "$LAUNCH_AGENT_DIR"
PYTHON_PATH=$(which python3)
FLEET_PORT="8778"

# Menu Bar → LaunchAgent (starts at login, needs GUI)
if [ -f "$INSTALL_DIR/com.atlas.menubar.plist" ]; then
    sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__ACTUAL_USER__|$ACTUAL_USER|g; s|__ACTUAL_HOME__|$ACTUAL_HOME|g; s|__FLEET_PORT__|$FLEET_PORT|g" \
        "$INSTALL_DIR/com.atlas.menubar.plist" > "$LAUNCH_AGENT_DIR/com.atlas.menubar.plist"
    chown $ACTUAL_USER "$LAUNCH_AGENT_DIR/com.atlas.menubar.plist"
    echo "  ✓ Menu bar agent configured (login-time)"
fi

# Core Agent → LaunchDaemon (starts at boot)
if [ -f "$INSTALL_DIR/com.atlas.agent.daemon.plist" ]; then
    sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__ACTUAL_USER__|$ACTUAL_USER|g; s|__ACTUAL_HOME__|$ACTUAL_HOME|g; s|__FLEET_PORT__|$FLEET_PORT|g" \
        "$INSTALL_DIR/com.atlas.agent.daemon.plist" > "$LAUNCH_DAEMON_DIR/com.atlas.agent.core.plist"
    chown root:wheel "$LAUNCH_DAEMON_DIR/com.atlas.agent.core.plist"
    chmod 644 "$LAUNCH_DAEMON_DIR/com.atlas.agent.core.plist"
    echo "  ✓ Core agent configured (boot-time)"
fi

# Fleet Server → LaunchDaemon (starts at boot)
if [ -f "$INSTALL_DIR/com.atlas.fleetserver.daemon.plist" ]; then
    sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__ACTUAL_USER__|$ACTUAL_USER|g; s|__ACTUAL_HOME__|$ACTUAL_HOME|g; s|__FLEET_PORT__|$FLEET_PORT|g" \
        "$INSTALL_DIR/com.atlas.fleetserver.daemon.plist" > "$LAUNCH_DAEMON_DIR/com.atlas.fleetserver.plist"
    chown root:wheel "$LAUNCH_DAEMON_DIR/com.atlas.fleetserver.plist"
    chmod 644 "$LAUNCH_DAEMON_DIR/com.atlas.fleetserver.plist"
    echo "  ✓ Fleet server configured (boot-time)"
fi

# Check if setup wizard exists and config doesn't
if [ -f "$INSTALL_DIR/setup_fleet_connection.py" ] && [ ! -f "$ACTUAL_HOME/.fleet-config.json.encrypted" ]; then
    echo ""
    echo "======================================"
    echo "Fleet Server Configuration Required"
    echo "======================================"
    echo ""
    echo "Run the setup wizard to configure your fleet server:"
    echo "  python3 $INSTALL_DIR/setup_fleet_connection.py"
    echo ""
fi

echo ""
echo "======================================"
echo "ATLAS Agent installation complete!"
echo "======================================"
echo ""
echo "Installed components:"
echo "  ✓ ATLAS monitoring agent"
echo "  ✓ Python dependencies"
if [ -n "$BREW_CMD" ]; then
    echo "  ✓ Homebrew packages for enhanced monitoring"
fi
echo ""
exit 0
'''
            with open(postinstall, 'w') as f:
                f.write(postinstall_content)
            os.chmod(postinstall, 0o755)
            
            # Build the package using pkgbuild
            cmd = [
                'pkgbuild',
                '--root', str(payload_dir),
                '--identifier', identifier,
                '--version', version,
                '--install-location', install_location,
                '--scripts', str(scripts_dir),
                str(output_path)
            ]
            
            logger.info(f"Running pkgbuild: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"pkgbuild failed: {result.stderr}")
                return None
            
            logger.info(f"Successfully created package: {output_path}")
            return output_path
            
        except FileNotFoundError:
            logger.warning("pkgbuild not found - falling back to zip")
            return None
        except Exception as e:
            logger.error(f"Error building pkg: {e}")
            return None
    
    def create_agent_config(self, widget_config=None, tool_config=None,
                            widget_order=None, tool_order=None):
        """Create agent configuration file with custom settings and ordering"""
        # Default to all enabled if not specified
        if widget_config is None:
            widget_config = {
                'system_monitor': True,
                'wifi': True,
                'wifi_analyzer': True,
                'speedtest': True,
                'speedtest_history': True,
                'ping': True,
                'network_testing': True,
                'network_quality': True,
                'network_analysis': True,
                'wifi_roaming': True,
                'vpn_status': True,
                'saas_health': True,
                'security_dashboard': True,
                'system_health': True,
                'power': True,
                'display': True,
                'peripherals': True,
                'disk_health': True,
                'processes': True
            }

        if tool_config is None:
            tool_config = {
                'metrics': True,
                'logs': True,
                'commands': True,
                'autostart': True
            }

        # Default ordering if not specified
        if widget_order is None:
            widget_order = list(widget_config.keys())
        if tool_order is None:
            tool_order = list(tool_config.keys())
        
        # Handle different config structures (encrypted vs FleetConfig)
        server_config = self.config.get('server', {})
        
        # Get API key - try multiple locations
        api_key = (
            server_config.get('api_key') or
            self.config.get('security', {}).get('api_key') or
            ''
        )
        
        # Get server URL - try fleet_server_url first (encrypted config), then build from host/port
        if 'fleet_server_url' in server_config:
            server_url = server_config['fleet_server_url']
        else:
            protocol = server_config.get('protocol', 'http')
            host = server_config.get('host', 'localhost')
            port = server_config.get('port', 8778)
            server_url = f"{protocol}://{host}:{port}"
        
        # Get or generate E2EE encryption key
        encryption_key = server_config.get('encryption_key')
        if not encryption_key:
            # Auto-generate encryption key if not set
            try:
                from .encryption import DataEncryption
                encryption_key = DataEncryption.generate_key()
                logger.info("Generated new E2EE encryption key for agent package")
                # Save the key back to config for future packages
                self._save_encryption_key(encryption_key)
            except Exception as e:
                logger.warning(f"Could not generate encryption key: {e}")
                encryption_key = None
        
        agent_config = {
            "fleet_server": {
                "url": server_url,
                "api_key": api_key,
                "encryption_key": encryption_key
            },
            "dashboard_auth": {
                "enabled": True,
                "auth_mode": "local"
            },
            "agent": {
                "report_interval": 30,
                "retry_attempts": 3,
                "retry_delay": 5
            },
            "widgets": {
                "enabled": any(widget_config.values()),
                "order": widget_order,
                "log_interval": 300,
                **{k: v for k, v in widget_config.items()}
            },
            "tools": {
                "order": tool_order,
                "metrics": tool_config.get('metrics', True),
                "logs": tool_config.get('logs', True),
                "commands": tool_config.get('commands', True),
                "autostart": tool_config.get('autostart', True)
            }
        }
        return agent_config
    
    def build_installer_script(self, agent_config):
        """Build the installer shell script"""
        script = f'''#!/bin/bash
#
# Fleet Agent Installer
# Generated: {datetime.now().isoformat()}
#

set -e

echo "======================================"
echo "Fleet Agent Installer"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This installer must be run with sudo"
    echo "   Usage: sudo bash install_fleet_agent.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${{SUDO_USER:-$USER}}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing for user: $ACTUAL_USER"
echo ""

# Install directory
INSTALL_DIR="$ACTUAL_HOME/Library/FleetAgent"
CONFIG_DIR="$ACTUAL_HOME/.fleet"

echo "Step 1: Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# Copy files
echo "Step 2: Installing Fleet Agent..."

# Create agent config
cat > "$CONFIG_DIR/agent-config.json" << 'AGENT_CONFIG_EOF'
{json.dumps(agent_config, indent=2)}
AGENT_CONFIG_EOF

chmod 600 "$CONFIG_DIR/agent-config.json"

# Set up dashboard auth to use macOS local password (no separate account needed)
DASHBOARD_AUTH_DIR="$ACTUAL_HOME/.config/atlas-agent"
mkdir -p "$DASHBOARD_AUTH_DIR"
cat > "$DASHBOARD_AUTH_DIR/dashboard_auth.json" << 'DASHBOARD_AUTH_EOF'
{
    "enabled": true,
    "auth_mode": "local",
    "session_timeout_hours": 24,
    "require_auth_for_api": false,
    "allow_touchid": true
}
DASHBOARD_AUTH_EOF
chown $ACTUAL_USER "$DASHBOARD_AUTH_DIR/dashboard_auth.json"
chmod 600 "$DASHBOARD_AUTH_DIR/dashboard_auth.json"

# Download or copy fleet agent
echo "Step 3: Installing dependencies..."

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "Installing Python dependencies..."
    # Try to install pip
    if command -v python3 &> /dev/null; then
        python3 -m ensurepip --upgrade 2>/dev/null || true
    fi
fi

# Install required packages
pip3 install --user psutil requests cryptography 2>/dev/null || {{
    echo " Warning: Could not install Python packages automatically"
    echo "   Please run: pip3 install psutil requests cryptography"
}}

# Create LaunchAgent
echo "Step 4: Setting up auto-start..."

LAUNCH_AGENT_DIR="$ACTUAL_HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENT_DIR"

cat > "$LAUNCH_AGENT_DIR/com.fleet.agent.plist" << 'LAUNCHAGENT_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fleet.agent</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>-m</string>
        <string>atlas.fleet_agent</string>
        <string>--config</string>
        <string>$CONFIG_DIR/agent-config.json</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$ACTUAL_HOME/Library/Logs/fleet_agent.log</string>
    
    <key>StandardErrorPath</key>
    <string>$ACTUAL_HOME/Library/Logs/fleet_agent_error.log</string>
</dict>
</plist>
LAUNCHAGENT_EOF

chown $ACTUAL_USER "$LAUNCH_AGENT_DIR/com.fleet.agent.plist"

# Start the agent
echo "Step 5: Starting Fleet Agent..."

# Load as the actual user
sudo -u $ACTUAL_USER launchctl load "$LAUNCH_AGENT_DIR/com.fleet.agent.plist" 2>/dev/null || true

echo ""
echo "======================================"
echo "Fleet Agent Installed Successfully!"
echo "======================================"
echo ""
echo "Server: {agent_config['fleet_server']['url']}"
echo "Config: $CONFIG_DIR/agent-config.json"
echo "Logs: $ACTUAL_HOME/Library/Logs/fleet_agent.log"
echo ""
echo "The agent is now running and will start automatically on boot."
echo ""
'''
        return script
    
    def build_package(self, output_dir=None, widget_config=None, tool_config=None,
                      widget_order=None, tool_order=None):
        """Build the complete installer package using split-mode (boot + login)"""
        if output_dir is None:
            output_dir = Path.home() / "Downloads"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Get agent config
            agent_config = self.create_agent_config(widget_config, tool_config,
                                                     widget_order, tool_order)
            
            # Copy the entire atlas package
            source_dir = Path(__file__).parent.parent  # Go up to project root
            package_dir = tmpdir / "atlas_agent"
            package_dir.mkdir()
            
            # Copy atlas module
            shutil.copytree(
                source_dir / "atlas",
                package_dir / "atlas",
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.DS_Store')
            )
            
            # Copy split-mode installer files
            installer_files = [
                'install_split_mode.sh',
                'start_atlas_agent.py',
                'start_agent_daemon.py',
                'launch_atlas_with_config.py',
                'repair_credentials.py',
                'update_fleet_config.py',
                'show_credentials.py',
                'com.atlas.fleetserver.daemon.plist',
                'com.atlas.agent.daemon.plist',
                'com.atlas.menubar.plist'
            ]
            
            for file in installer_files:
                src = source_dir / file
                if src.exists():
                    shutil.copy2(src, package_dir / file)
            
            # Create pre-configured encrypted config
            # Handle different config structures (encrypted vs FleetConfig)
            server_config = self.config.get('server', {})
            security_config = self.config.get('security', {})
            
            config_data = {
                'organization_name': self.config.get('organization', {}).get('name', 
                                     self.config.get('organization_name', 'Fleet Organization')),
                'server': {
                    'api_key': server_config.get('api_key') or security_config.get('api_key', ''),
                    'fleet_server_url': agent_config['fleet_server']['url'],
                    'web_username': server_config.get('web_username') or security_config.get('web_username', ''),
                    'web_password': server_config.get('web_password') or security_config.get('web_password', '')
                }
            }
            
            # Save config template
            config_template_path = package_dir / "fleet-config-template.json"
            with open(config_template_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            # Save agent config with widget/tool selections and ordering
            agent_config_path = package_dir / "agent-config.json"
            with open(agent_config_path, 'w') as f:
                json.dump(agent_config, f, indent=2)

            # Create README
            readme = f'''# ATLAS Fleet Agent Installer (Split-Mode)

This package installs the ATLAS Fleet monitoring system with split-mode startup:
- **Fleet Server + Core Agent** start at boot (before login)
- **Menu Bar App** starts at login (with GUI access)

## Installation

1. Open Terminal
2. Navigate to this folder
3. Run: **sudo ./install_split_mode.sh**
4. Enter your password when prompted

## What Gets Installed

### Boot-Time Services (LaunchDaemons)
- Fleet Server on port 8778 (HTTPS)
- Core Agent on port 8767 (HTTP)
- Start immediately at system boot
- Auto-restart on crash

### Login-Time Services (LaunchAgent)
- Menu Bar icon with status indicator
- Starts when you log in
- Shows real-time connection status

## Configuration

**Fleet Server:** {agent_config['fleet_server']['url']}
**API Key:** {agent_config['fleet_server']['api_key'][:20]}...

The installer will:
1. Check for existing credentials (or create new ones)
2. Install Fleet Server as a system daemon
3. Install Core Agent as a system daemon
4. Install Menu Bar app as a user agent
5. Start all services immediately

## After Installation

**Access Dashboards:**
- Fleet Dashboard: {agent_config['fleet_server']['url']}/dashboard
- Agent Dashboard: http://localhost:8767
- Menu Bar Icon: Check top-right corner of screen

**View Logs:**
```bash
tail -f /var/log/atlas-fleetserver.log
tail -f /var/log/atlas-agent.log
tail -f ~/.atlas-menubar.log
```

**Management Commands:**
```bash
# Check status
sudo launchctl list | grep atlas
launchctl list | grep atlas

# Restart services
sudo launchctl kickstart -k system/com.atlas.fleetserver
sudo launchctl kickstart -k system/com.atlas.agent.core
launchctl kickstart -k gui/$(id -u)/com.atlas.menubar
```

## Uninstall

To remove all ATLAS components:

```bash
# Stop services
sudo launchctl bootout system /Library/LaunchDaemons/com.atlas.fleetserver.plist
sudo launchctl bootout system /Library/LaunchDaemons/com.atlas.agent.core.plist
launchctl unload ~/Library/LaunchAgents/com.atlas.menubar.plist

# Remove files
sudo rm /Library/LaunchDaemons/com.atlas.fleetserver.plist
sudo rm /Library/LaunchDaemons/com.atlas.agent.core.plist
rm ~/Library/LaunchAgents/com.atlas.menubar.plist
rm -rf ~/.fleet-config.json.encrypted
rm -rf ~/.fleet-data
rm -rf ~/.fleet-certs
```

## Support

For issues, contact your Fleet administrator.

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Package Type:** Split-Mode (Boot + Login)
'''
            
            readme_path = package_dir / "README.md"
            with open(readme_path, 'w') as f:
                f.write(readme)
            
            # Try to build .pkg first, fall back to .zip
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            package_name = f"ATLAS_Fleet_Agent_{timestamp}"
            
            # Try building .pkg
            pkg_path = output_dir / f"{package_name}.pkg"
            result = self._build_pkg(
                payload_dir=package_dir,
                output_path=pkg_path,
                identifier="com.atlas.fleet-agent",
                version="1.0.0",
                install_location="/Library/FleetAgent"
            )
            
            if result:
                return result
            
            # Fall back to zip if pkgbuild failed
            logger.warning("Falling back to zip package")
            output_path = output_dir / f"{package_name}.zip"
            shutil.make_archive(
                str(output_dir / package_name),
                'zip',
                tmpdir
            )
            
            return output_path
    
    def build_standalone_package(self, output_dir=None, widget_config=None, tool_config=None,
                                 widget_order=None, tool_order=None, standalone_options=None):
        """Build a standalone ATLAS agent installer package.

        Creates a complete monitoring solution that works independently without
        requiring a fleet server. Perfect for individual users, home labs, or
        organizations that want local-only monitoring.

        INCLUDED FEATURES:
        ✓ Real-time system monitoring (CPU, Memory, Disk, Network)
        ✓ Local web dashboard (http://localhost:8767)
        ✓ macOS menu bar app with quick stats
        ✓ Network quality monitoring (WiFi, Speed Tests, Ping)
        ✓ Network Analysis tool - automatic root cause analysis for slowdowns
        ✓ CSV exports (4 data types × 3 time ranges = 12 export options)
        ✓ JSON API for programmatic access
        ✓ 7-day local data retention with automatic cleanup
        ✓ Process monitoring with kill capability
        ✓ Feature discovery help system

        NO FLEET SERVER REQUIRED - fully standalone operation.
        Optional: Can be upgraded to fleet mode later by providing server URL.

        Args:
            output_dir: Directory for installer (default: ~/Downloads)
            widget_config: Dict of enabled widgets (default: all enabled)
            tool_config: Dict of enabled tools (default: all enabled)
            standalone_options: Dict with 'include_setup_wizard', 'include_menubar'

        Returns:
            Path to generated installer package

        Package Contents:
            - Complete atlas monitoring module
            - Local dashboard server (Flask-based)
            - macOS menu bar application (optional)
            - Setup wizard for easy installation
            - All monitoring widgets and analysis tools
            - Documentation and help system

        Example:
            builder = AgentPackageBuilder()
            pkg_path = builder.build_standalone_package()
            # Creates: ~/Downloads/atlas-standalone-agent-YYYYMMDD.pkg
        """
        if output_dir is None:
            output_dir = Path.home() / "Downloads"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default standalone options
        if standalone_options is None:
            standalone_options = {
                'include_setup_wizard': True,
                'include_menubar': True
            }
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Copy the entire atlas package
            source_dir = Path(__file__).parent.parent  # Go up to project root
            package_dir = tmpdir / "atlas_standalone_agent"
            package_dir.mkdir()
            
            # Copy atlas module
            shutil.copytree(
                source_dir / "atlas",
                package_dir / "atlas",
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.DS_Store')
            )
            
            # Copy essential installer files (without pre-configured credentials)
            installer_files = [
                'start_atlas_agent.py',
                'start_agent_daemon.py',
                'launch_atlas_with_config.py',
                'set_credentials.py',
                'repair_credentials.py',
                'update_fleet_config.py',
                'show_credentials.py',
                'com.atlas.agent.daemon.plist',
            ]
            
            if standalone_options.get('include_menubar', True):
                installer_files.append('com.atlas.menubar.plist')
            
            for file in installer_files:
                src = source_dir / file
                if src.exists():
                    shutil.copy2(src, package_dir / file)
            
            # Create widget config file (without server credentials)
            widget_cfg = widget_config or {
                'system_monitor': True,
                'wifi': True,
                'wifi_analyzer': True,
                'speedtest': True,
                'speedtest_history': True,
                'ping': True,
                'network_testing': True,
                'network_quality': True,
                'network_analysis': True,
                'wifi_roaming': True,
                'vpn_status': True,
                'saas_health': True,
                'security_dashboard': True,
                'system_health': True,
                'power': True,
                'display': True,
                'peripherals': True,
                'disk_health': True,
                'processes': True
            }
            
            tool_cfg = tool_config or {
                'metrics': True,
                'logs': True,
                'commands': True,
                'autostart': True
            }
            
            # Default ordering if not specified
            w_order = widget_order or list(widget_cfg.keys())
            t_order = tool_order or list(tool_cfg.keys())

            agent_config_template = {
                "fleet_server": {
                    "url": "",  # To be configured by user
                    "api_key": ""  # To be configured by user
                },
                "agent": {
                    "report_interval": 30,
                    "retry_attempts": 3,
                    "retry_delay": 5
                },
                "widgets": {
                    "enabled": any(widget_cfg.values()),
                    "order": w_order,
                    "log_interval": 300,
                    **widget_cfg
                },
                "tools": {
                    "order": t_order,
                    **tool_cfg
                }
            }
            
            # Save agent config template
            config_template_path = package_dir / "agent-config-template.json"
            with open(config_template_path, 'w') as f:
                json.dump(agent_config_template, f, indent=2)
            
            # Create standalone installer script
            standalone_installer = self._create_standalone_installer(
                standalone_options.get('include_setup_wizard', True),
                standalone_options.get('include_menubar', True)
            )
            
            installer_path = package_dir / "install_standalone.sh"
            with open(installer_path, 'w') as f:
                f.write(standalone_installer)
            os.chmod(installer_path, 0o755)
            
            # Create setup wizard script if requested
            if standalone_options.get('include_setup_wizard', True):
                setup_wizard = self._create_setup_wizard()
                wizard_path = package_dir / "setup_fleet_connection.py"
                with open(wizard_path, 'w') as f:
                    f.write(setup_wizard)
                os.chmod(wizard_path, 0o755)
            
            # Create README
            readme = self._create_standalone_readme(standalone_options)
            readme_path = package_dir / "README.md"
            with open(readme_path, 'w') as f:
                f.write(readme)
            
            # Try to build .pkg first, fall back to .zip
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            package_name = f"ATLAS_Standalone_Agent_{timestamp}"
            
            # Try building .pkg
            pkg_path = output_dir / f"{package_name}.pkg"
            result = self._build_pkg(
                payload_dir=package_dir,
                output_path=pkg_path,
                identifier="com.atlas.standalone-agent",
                version="1.0.0",
                install_location="/Library/FleetAgent"
            )
            
            if result:
                logger.info(f"Standalone package created: {result}")
                return result
            
            # Fall back to zip if pkgbuild failed
            logger.warning("Falling back to zip package")
            output_path = output_dir / f"{package_name}.zip"
            shutil.make_archive(
                str(output_dir / package_name),
                'zip',
                tmpdir
            )
            
            logger.info(f"Standalone package created: {output_path}")
            return output_path
    
    def _create_standalone_installer(self, include_wizard, include_menubar):
        """Create the standalone installer shell script"""
        menubar_section = '''
# Install Menu Bar App (LaunchAgent) + Core Agent (LaunchDaemon)
echo "Step 5: Setting up services..."
LAUNCH_AGENT_DIR="$ACTUAL_HOME/Library/LaunchAgents"
LAUNCH_DAEMON_DIR="/Library/LaunchDaemons"
mkdir -p "$LAUNCH_AGENT_DIR"
PYTHON_PATH=$(which python3)
FLEET_PORT="8778"

if [ -f "com.atlas.menubar.plist" ]; then
    sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__ACTUAL_USER__|$ACTUAL_USER|g; s|__ACTUAL_HOME__|$ACTUAL_HOME|g; s|__FLEET_PORT__|$FLEET_PORT|g" \
        com.atlas.menubar.plist > "$LAUNCH_AGENT_DIR/com.atlas.menubar.plist"
    chown $ACTUAL_USER "$LAUNCH_AGENT_DIR/com.atlas.menubar.plist"
    echo "   ✓ Menu Bar app configured (login-time)"
fi

if [ -f "com.atlas.agent.daemon.plist" ]; then
    sed "s|__PYTHON_PATH__|$PYTHON_PATH|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__ACTUAL_USER__|$ACTUAL_USER|g; s|__ACTUAL_HOME__|$ACTUAL_HOME|g; s|__FLEET_PORT__|$FLEET_PORT|g" \
        com.atlas.agent.daemon.plist > "$LAUNCH_DAEMON_DIR/com.atlas.agent.core.plist"
    chown root:wheel "$LAUNCH_DAEMON_DIR/com.atlas.agent.core.plist"
    chmod 644 "$LAUNCH_DAEMON_DIR/com.atlas.agent.core.plist"
    echo "   ✓ Core agent configured (boot-time)"
fi
''' if include_menubar else ''

        wizard_section = '''
# Run setup wizard
if [ -f "setup_fleet_connection.py" ]; then
    echo ""
    echo "======================================"
    echo "Fleet Server Configuration"
    echo "======================================"
    echo ""
    sudo -u $ACTUAL_USER python3 "$INSTALL_DIR/setup_fleet_connection.py"
fi
''' if include_wizard else '''
echo ""
echo " No fleet server configured!"
echo "   Run: python3 ~/Library/FleetAgent/setup_fleet_connection.py"
echo "   Or manually edit: ~/.fleet-config.json"
'''

        return f'''#!/bin/bash
#
# ATLAS Standalone Agent Installer
# Generated: {datetime.now().isoformat()}
#
# This installer does NOT include pre-configured server credentials.
# After installation, run the setup wizard to configure your fleet server.
#

set -e

echo "======================================"
echo "ATLAS Standalone Agent Installer"
echo "======================================"
echo ""
echo "This is a STANDALONE package"
echo "   No fleet server credentials included"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This installer must be run with sudo"
    echo "   Usage: sudo ./install_standalone.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${{SUDO_USER:-$USER}}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing for user: $ACTUAL_USER"
echo ""

# Install directory
INSTALL_DIR="$ACTUAL_HOME/Library/FleetAgent"
CONFIG_DIR="$ACTUAL_HOME/.fleet"

echo "Step 1: Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
chown -R $ACTUAL_USER "$INSTALL_DIR"
chown -R $ACTUAL_USER "$CONFIG_DIR"

# Copy files
echo "Step 2: Copying agent files..."
cp -r atlas "$INSTALL_DIR/"
cp *.py "$INSTALL_DIR/" 2>/dev/null || true
cp *.json "$INSTALL_DIR/" 2>/dev/null || true
cp *.plist "$INSTALL_DIR/" 2>/dev/null || true
chown -R $ACTUAL_USER "$INSTALL_DIR"

# Install dependencies
echo "Step 3: Installing Python dependencies..."
sudo -u $ACTUAL_USER pip3 install --user psutil requests cryptography bcrypt rumps PyJWT 2>/dev/null || {{
    echo "⚠ Warning: Could not install Python packages automatically"
    echo "   Please run: pip3 install psutil requests cryptography bcrypt rumps PyJWT"
}}

# ============================================
# Install Homebrew packages for full functionality
# ============================================
echo ""
echo "Step 4: Installing Homebrew packages for enhanced monitoring..."

# Check if Homebrew is installed, install if not
HOMEBREW_PREFIX=""
if [ -x "/opt/homebrew/bin/brew" ]; then
    HOMEBREW_PREFIX="/opt/homebrew"
    BREW_CMD="/opt/homebrew/bin/brew"
elif [ -x "/usr/local/bin/brew" ]; then
    HOMEBREW_PREFIX="/usr/local"
    BREW_CMD="/usr/local/bin/brew"
fi

# Install Homebrew if not found
if [ -z "$BREW_CMD" ]; then
    echo "   Homebrew not found. Attempting to install Homebrew..."

    if [ -n "$ACTUAL_USER" ] && [ "$ACTUAL_USER" != "root" ]; then
        echo "   Installing Homebrew for user: $ACTUAL_USER"

        # Non-interactive Homebrew installation
        sudo -u "$ACTUAL_USER" NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>/dev/null || true

        # Re-check for Homebrew after installation
        if [ -x "/opt/homebrew/bin/brew" ]; then
            HOMEBREW_PREFIX="/opt/homebrew"
            BREW_CMD="/opt/homebrew/bin/brew"
            echo "   ✓ Homebrew installed successfully"
        elif [ -x "/usr/local/bin/brew" ]; then
            HOMEBREW_PREFIX="/usr/local"
            BREW_CMD="/usr/local/bin/brew"
            echo "   ✓ Homebrew installed successfully"
        else
            echo "   ⚠ Homebrew installation failed. Continuing without Homebrew packages."
        fi
    else
        echo "   ⚠ Cannot install Homebrew as root. Skipping."
    fi
fi

if [ -n "$BREW_CMD" ]; then
    echo "   Homebrew found at: $BREW_CMD"

    # Required packages for core functionality
    PACKAGES_TO_INSTALL=""

    # smartmontools - SMART disk health monitoring
    if ! command -v smartctl &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL smartmontools"
        echo "   • smartmontools (SMART disk health)"
    else
        echo "   ✓ smartmontools already installed"
    fi

    # speedtest-cli - Network speed testing
    if ! command -v speedtest-cli &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL speedtest-cli"
        echo "   • speedtest-cli (network speed tests)"
    else
        echo "   ✓ speedtest-cli already installed"
    fi

    # mtr - Network path analysis
    if ! command -v mtr &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL mtr"
        echo "   • mtr (network diagnostics)"
    else
        echo "   ✓ mtr already installed"
    fi

    # Temperature monitoring - architecture specific
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        if ! command -v macmon &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL macmon"
            echo "   • macmon (CPU temperature - Apple Silicon)"
        else
            echo "   ✓ macmon already installed"
        fi
    else
        if ! command -v osx-cpu-temp &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL osx-cpu-temp"
            echo "   • osx-cpu-temp (CPU temperature - Intel)"
        else
            echo "   ✓ osx-cpu-temp already installed"
        fi
    fi

    # Install packages if any are needed
    if [ -n "$PACKAGES_TO_INSTALL" ]; then
        echo ""
        echo "   Installing packages..."
        if sudo -u $ACTUAL_USER $BREW_CMD install $PACKAGES_TO_INSTALL 2>/dev/null; then
            echo "   ✓ Homebrew packages installed successfully"
        else
            echo "   ⚠ Some packages could not be installed (non-critical)"
        fi
    else
        echo "   ✓ All required Homebrew packages already installed"
    fi
else
    echo "   ⚠ Homebrew not found and could not be installed - some features will be limited"
fi

{menubar_section}
{wizard_section}
echo ""
echo "======================================"
echo "ATLAS Agent Installed Successfully!"
echo "======================================"
echo ""
echo "📁 Install Location: $INSTALL_DIR"
echo "📁 Config Location:  $CONFIG_DIR"
echo ""
echo "Installed components:"
echo "  ✓ ATLAS monitoring agent"
echo "  ✓ Python dependencies"
if [ -n "$BREW_CMD" ]; then
echo "  ✓ Homebrew packages for enhanced monitoring"
fi
echo ""
echo "Next Steps:"
echo "  1. Configure fleet server connection (if not done)"
echo "  2. Start the agent manually or reboot"
echo ""
echo "Commands:"
echo "  Configure: python3 $INSTALL_DIR/setup_fleet_connection.py"
echo "  Start:     python3 -m atlas.fleet_agent"
echo ""
'''
    
    def _create_setup_wizard(self):
        """Create the setup wizard Python script"""
        return '''#!/usr/bin/env python3
"""
ATLAS Fleet Server Connection Setup Wizard
Configure the agent to connect to a fleet server
"""

import os
import sys
import json
import secrets
from pathlib import Path

def main():
    print("=" * 60)
    print("ATLAS Fleet Server Connection Setup")
    print("=" * 60)
    print()
    
    config_path = Path.home() / ".fleet-config.json"
    
    # Check for existing config
    if config_path.exists():
        print(f" Existing configuration found at {config_path}")
        response = input("Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            return 0
    
    print()
    print("Enter your Fleet Server details:")
    print("-" * 40)
    
    # Get server URL
    server_url = input("Fleet Server URL (e.g., https://fleet.company.com:8778): ").strip()
    if not server_url:
        print("Server URL is required")
        return 1
    
    # Ensure URL has protocol
    if not server_url.startswith('http'):
        server_url = 'https://' + server_url
    
    # Get API key
    api_key = input("API Key (leave blank to generate new): ").strip()
    if not api_key:
        api_key = secrets.token_urlsafe(32)
        print(f"   Generated API Key: {api_key}")
    
    # Get web credentials (optional)
    print()
    print("Web Dashboard Credentials (optional):")
    web_username = input("Username (default: admin): ").strip() or "admin"
    web_password = input("Password (leave blank to skip): ").strip()
    
    # Create config
    config_data = {
        'organization_name': 'ATLAS Fleet',
        'server': {
            'api_key': api_key,
            'fleet_server_url': server_url,
            'web_username': web_username,
            'web_password': web_password
        }
    }
    
    # Try to encrypt config
    try:
        sys.path.insert(0, str(Path(__file__).parent / "atlas"))
        from fleet_config_encryption import EncryptedConfigManager
        
        manager = EncryptedConfigManager(str(config_path))
        manager.encrypt_config(config_data)
        print()
        print(f"Configuration saved (encrypted) to:")
        print(f"   {config_path}.encrypted")
    except ImportError:
        # Fall back to plaintext
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        os.chmod(config_path, 0o600)
        print()
        print(f"Configuration saved to:")
        print(f"   {config_path}")
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print(f"Fleet Server: {server_url}")
    print(f"API Key: {api_key[:20]}...")
    print()
    print("To start the agent:")
    print("  python3 -m atlas.fleet_agent")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
'''
    
    def _create_standalone_readme(self, standalone_options):
        """Create README for standalone package"""
        wizard_section = '''
## Quick Setup

Run the setup wizard to configure your fleet server connection:

```bash
python3 ~/Library/FleetAgent/setup_fleet_connection.py
```

The wizard will ask for:
- Fleet Server URL (e.g., https://fleet.company.com:8778)
- API Key (can generate a new one)
- Web dashboard credentials (optional)
''' if standalone_options.get('include_setup_wizard', True) else '''
## Manual Configuration

Create a configuration file at `~/.fleet-config.json`:

```json
{
  "organization_name": "Your Organization",
  "server": {
    "api_key": "your-api-key-here",
    "fleet_server_url": "https://fleet.company.com:8778",
    "web_username": "admin",
    "web_password": "your-password"
  }
}
```
'''
        
        return f'''# ATLAS Standalone Agent Installer

This is a **standalone** agent package that does NOT include pre-configured 
fleet server credentials. This allows you to:

- Distribute to multiple organizations
- Let users choose their own fleet server
- Test before connecting to production
- Deploy to machines that will connect to different servers

## Installation

1. Open Terminal
2. Navigate to this folder
3. Run: `sudo ./install_standalone.sh`
4. Follow the setup wizard to configure your fleet server
{wizard_section}
## What Gets Installed

- ATLAS Agent (monitors system metrics)
- Widget system (WiFi, Speedtest, Ping, Health, Processes)
- Auto-start configuration (LaunchAgent)
{"- Menu Bar app for status and quick access" if standalone_options.get('include_menubar', True) else ""}
{"- Setup wizard for easy configuration" if standalone_options.get('include_setup_wizard', True) else ""}

## After Installation

1. **Configure Fleet Server** (if not done during install):
   ```bash
   python3 ~/Library/FleetAgent/setup_fleet_connection.py
   ```

2. **Start the Agent**:
   ```bash
   python3 -m atlas.fleet_agent
   ```

3. **View Logs**:
   ```bash
   tail -f ~/Library/Logs/fleet_agent.log
   ```

## Connecting to a Fleet Server

To connect this agent to a fleet server, you need:

1. **Fleet Server URL**: The address of your fleet server (e.g., `https://192.168.1.100:8778`)
2. **API Key**: The authentication key from your fleet server
3. **Credentials**: (Optional) Web dashboard username/password

Get these from your fleet server administrator or from the fleet server's 
Settings page.

## Uninstall

```bash
# Stop agent
launchctl unload ~/Library/LaunchAgents/com.atlas.agent.plist

# Remove files
rm -rf ~/Library/FleetAgent
rm -rf ~/.fleet-config.json*
rm ~/Library/LaunchAgents/com.atlas.*.plist
```

## Support

For issues, contact your Fleet administrator.

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Package Type:** Standalone (no pre-configured credentials)
'''

    def build_quick_install(self, output_dir=None):
        """Build a single-file quick installer"""
        if output_dir is None:
            output_dir = Path.home() / "Downloads"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        agent_config = self.create_agent_config()
        
        # Create self-contained installer
        installer = f'''#!/bin/bash
#
# Fleet Agent Quick Installer
# Generated: {datetime.now().isoformat()}
#
# Usage: curl -sSL http://your-server:8778/install.sh | sudo bash
#

set -e

FLEET_SERVER_URL="{agent_config['fleet_server']['url']}"
FLEET_API_KEY="{agent_config['fleet_server']['api_key']}"

echo "======================================"
echo "Fleet Agent Quick Installer"
echo "======================================"
echo ""
echo "Server: $FLEET_SERVER_URL"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This installer must be run with sudo"
    exit 1
fi

# Get actual user
ACTUAL_USER="${{SUDO_USER:-$USER}}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo "Installing for user: $ACTUAL_USER"
echo ""

# Install Python dependencies
echo "Installing dependencies..."
pip3 install --user psutil requests cryptography 2>/dev/null || true

# Create config directory
CONFIG_DIR="$ACTUAL_HOME/.fleet"
mkdir -p "$CONFIG_DIR"

# Create agent config
cat > "$CONFIG_DIR/agent-config.json" << 'EOF'
{json.dumps(agent_config, indent=2)}
EOF

chmod 600 "$CONFIG_DIR/agent-config.json"

# Download fleet agent from server
echo "Downloading Fleet Agent..."
INSTALL_DIR="$ACTUAL_HOME/Library/FleetAgent"
mkdir -p "$INSTALL_DIR"

# Try to download from fleet server
curl -sSL "$FLEET_SERVER_URL/download/fleet_agent.py" -o "$INSTALL_DIR/fleet_agent.py" 2>/dev/null || {{
    echo " Could not download from server"
    echo "   Please install manually"
    exit 1
}}

# Create LaunchAgent
LAUNCH_AGENT_DIR="$ACTUAL_HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENT_DIR"

cat > "$LAUNCH_AGENT_DIR/com.fleet.agent.plist" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fleet.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>$INSTALL_DIR/fleet_agent.py</string>
        <string>--config</string>
        <string>$CONFIG_DIR/agent-config.json</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$ACTUAL_HOME/Library/Logs/fleet_agent.log</string>
    <key>StandardErrorPath</key>
    <string>$ACTUAL_HOME/Library/Logs/fleet_agent_error.log</string>
</dict>
</plist>
PLIST_EOF

chown $ACTUAL_USER "$LAUNCH_AGENT_DIR/com.fleet.agent.plist"

# Start agent
echo "Starting Fleet Agent..."
sudo -u $ACTUAL_USER launchctl load "$LAUNCH_AGENT_DIR/com.fleet.agent.plist" 2>/dev/null || true

echo ""
echo "Fleet Agent installed successfully!"
echo ""
'''
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f"install_fleet_agent_{timestamp}.sh"
        
        with open(output_path, 'w') as f:
            f.write(installer)
        
        os.chmod(output_path, 0o755)
        
        return output_path

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build Fleet Agent installer package')
    parser.add_argument('--config', help='Path to fleet config file')
    parser.add_argument('--output', help='Output directory', default=str(Path.home() / "Downloads"))
    parser.add_argument('--quick', action='store_true', help='Build quick installer script')
    
    args = parser.parse_args()
    
    try:
        builder = AgentPackageBuilder(args.config)
        
        if args.quick:
            output_path = builder.build_quick_install(args.output)
            print(f"Quick installer created: {output_path}")
        else:
            output_path = builder.build_package(args.output)
            print(f"Installer package created: {output_path}")
        
        print(f"\nDistribute this file to install Fleet Agent on other Macs.")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
