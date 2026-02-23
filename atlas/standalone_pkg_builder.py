"""
Standalone Server Package Builder

Generates macOS .pkg installers for deploying standalone Fleet Servers
(not clustered - independent operation with own database).
"""
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StandaloneServerPackageBuilder:
    """Build .pkg installers for standalone servers"""
    
    def __init__(self):
        """Initialize package builder"""
        self.temp_dir = None
    
    def build_package(self, output_path: str, server_config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Build standalone server installer package
        
        Args:
            output_path: Where to save the .pkg file
            server_config: Configuration for the server
        
        Returns:
            (success, message/error)
        """
        try:
            # Create temporary build directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix='fleet_standalone_pkg_'))
            logger.info(f"Building standalone server package in: {self.temp_dir}")

            # Create package structure
            pkg_root = self.temp_dir / 'package_root'
            scripts_dir = self.temp_dir / 'scripts'
            pkg_root.mkdir(parents=True, exist_ok=True)
            scripts_dir.mkdir(parents=True, exist_ok=True)

            # Create installation directories
            install_dir = pkg_root / 'Library' / 'FleetServer'
            config_dir = pkg_root / 'Library' / 'FleetServer' / 'config'
            install_dir.mkdir(parents=True, exist_ok=True)
            config_dir.mkdir(parents=True, exist_ok=True)

            # Generate standalone server configuration
            config_content = self._generate_server_config(server_config)
            config_path = config_dir / 'config.yaml'
            config_path.write_text(config_content)

            # Copy server files (if available)
            self._copy_server_files(str(install_dir))

            # Generate preinstall script (checks for ethernet)
            preinstall_script = self._generate_preinstall_script()
            preinstall_path = scripts_dir / 'preinstall'
            preinstall_path.write_text(preinstall_script)
            preinstall_path.chmod(0o755)

            # Generate installation script
            postinstall_script = self._generate_postinstall_script(server_config)
            postinstall_path = scripts_dir / 'postinstall'
            postinstall_path.write_text(postinstall_script)
            postinstall_path.chmod(0o755)

            # Generate LaunchDaemon for auto-start
            launchd_plist = self._generate_launchd_plist()
            launchd_dir = pkg_root / 'Library' / 'LaunchDaemons'
            launchd_dir.mkdir(parents=True, exist_ok=True)
            launchd_path = launchd_dir / 'com.fleet.server.plist'
            launchd_path.write_text(launchd_plist)
            
            # Build the package
            success = self._build_pkg(str(pkg_root), str(scripts_dir), output_path, server_config)

            if success:
                logger.info(f"Successfully built standalone server package: {output_path}")
                return True, f"Package created successfully: {output_path}"
            else:
                return False, "Failed to build package"

        except Exception as e:
            logger.error(f"Error building standalone package: {e}", exc_info=True)
            return False, f"Error: {str(e)}"

        finally:
            # Cleanup temp directory
            if self.temp_dir and self.temp_dir.exists():
                try:
                    shutil.rmtree(self.temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp dir: {e}")
    
    def _generate_server_config(self, server_config: Dict[str, Any]) -> str:
        """Generate config.yaml for standalone server"""
        
        # Build standalone server configuration
        config = {
            'organization': {
                'name': server_config.get('server_name', 'Fleet Monitoring')
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8778,
                # New server will prompt for admin account on first run
                'db_path': '/Library/FleetServer/data/fleet_data.db',
                # Generate new encryption keys on install
                'history_size': 10000,
                'history_retention_days': 90,
            },
            'ssl': {
                'enabled': False,
                'cert_path': '/Library/FleetServer/certs/server.crt',
                'key_path': '/Library/FleetServer/certs/server.key',
            },
            'cluster': {
                'enabled': False  # Standalone mode
            },
        }
        
        # Convert to YAML format
        try:
            import yaml
            yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
        except ImportError:
            # Fallback to manual YAML generation
            yaml_content = self._dict_to_yaml(config)
        
        return yaml_content
    
    def _dict_to_yaml(self, d: Dict, indent: int = 0) -> str:
        """Simple dict to YAML converter (fallback)"""
        lines = []
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append('  ' * indent + f"{key}:")
                lines.append(self._dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append('  ' * indent + f"{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append('  ' * (indent + 1) + '-')
                        lines.append(self._dict_to_yaml(item, indent + 2))
                    else:
                        lines.append('  ' * (indent + 1) + f"- {item}")
            elif value is None:
                lines.append('  ' * indent + f"{key}: null")
            elif isinstance(value, bool):
                lines.append('  ' * indent + f"{key}: {'true' if value else 'false'}")
            elif isinstance(value, (int, float)):
                lines.append('  ' * indent + f"{key}: {value}")
            else:
                lines.append('  ' * indent + f'{key}: "{value}"')
        return '\n'.join(lines)
    
    def _copy_server_files(self, install_dir: str):
        """Copy fleet server files to package"""
        readme_path = Path(install_dir) / 'README.txt'
        with open(readme_path, 'w') as f:
            f.write("""Fleet Server - Standalone Installation

This package configures a new standalone Fleet Server.

The server code must be installed separately. Run:
    pip3 install -r requirements.txt

Or copy the atlas package to:
    /Library/FleetServer/atlas/

Configuration has been set up for standalone operation (no clustering).
""")
    
    def _generate_preinstall_script(self) -> str:
        """Generate preinstall script that checks for ethernet connection"""
        # Reuse the same ethernet check from cluster package
        return '''#!/bin/bash
set -e

echo "=============================================="
echo "Fleet Server - Pre-Installation Check"
echo "=============================================="
echo ""

# Function to check if ethernet is connected
check_ethernet_connection() {
    echo "Checking network connectivity..."
    echo ""
    
    # Get list of all network interfaces
    interfaces=$(networksetup -listallhardwareports | grep -A 1 "Hardware Port: Ethernet" | grep "Device:" | awk '{print $2}')
    
    # Also check for Thunderbolt Ethernet and USB Ethernet
    thunderbolt_interfaces=$(networksetup -listallhardwareports | grep -A 1 "Hardware Port: Thunderbolt Ethernet" | grep "Device:" | awk '{print $2}')
    usb_interfaces=$(networksetup -listallhardwareports | grep -A 1 "Hardware Port: USB.*Ethernet" | grep "Device:" | awk '{print $2}')
    
    # Combine all ethernet interfaces
    all_ethernet="$interfaces $thunderbolt_interfaces $usb_interfaces"
    
    # Check if any interface is found
    if [ -z "$all_ethernet" ]; then
        echo "ERROR: No Ethernet adapter found on this Mac"
        echo ""
        echo "Fleet Server requires a wired Ethernet connection for:"
        echo "  • Reliable 24/7 operation"
        echo "  • Consistent network performance"
        echo "  • Server-grade stability"
        echo ""
        echo "Please connect an Ethernet cable and try again."
        echo ""
        exit 1
    fi
    
    # Check if any ethernet interface is active and has an IP
    ethernet_connected=false
    active_interface=""
    
    for interface in $all_ethernet; do
        # Check if interface is up
        status=$(ifconfig "$interface" 2>/dev/null | grep "status:" | awk '{print $2}')
        
        if [ "$status" = "active" ]; then
            # Check if it has an IP address
            ip_address=$(ifconfig "$interface" 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}')
            
            if [ -n "$ip_address" ]; then
                ethernet_connected=true
                active_interface="$interface"
                echo "Ethernet connected via $interface"
                echo "   IP Address: $ip_address"
                
                # Get additional interface info
                speed=$(networksetup -getMedia "$interface" 2>/dev/null | grep "Active:" | cut -d: -f2)
                if [ -n "$speed" ]; then
                    echo "   Link Speed: $speed"
                fi
                
                echo ""
                break
            fi
        fi
    done
    
    if [ "$ethernet_connected" = false ]; then
        echo "ERROR: No active Ethernet connection detected"
        echo ""
        echo "Available Ethernet adapters found, but none are connected:"
        for interface in $all_ethernet; do
            status=$(ifconfig "$interface" 2>/dev/null | grep "status:" | awk '{print $2}' || echo "unknown")
            echo "  • $interface - Status: $status"
        done
        echo ""
        echo "Fleet Server requires a wired Ethernet connection for:"
        echo "  • Reliable 24/7 operation"
        echo "  • Consistent network performance"
        echo "  • Server-grade stability"
        echo ""
        echo "Please connect an Ethernet cable to one of the adapters above and try again."
        echo ""
        echo "WiFi connections are NOT supported for Fleet Server installations."
        echo ""
        exit 1
    fi
    
    # Additional check: ensure we're not primarily on WiFi
    primary_service=$(networksetup -listnetworkserviceorder | grep "\\(1\\)" | sed 's/^.*) //' || echo "")
    
    if echo "$primary_service" | grep -i "wi-fi\\|airport" > /dev/null; then
        echo " WARNING: WiFi appears to be the primary network service"
        echo ""
        echo "For best performance, Ethernet should be the primary network interface."
        echo ""
        echo "You can change this in System Preferences → Network:"
        echo "  1. Click the gear icon → Set Service Order"
        echo "  2. Drag Ethernet to the top"
        echo "  3. Click OK and Apply"
        echo ""
        echo "Installation will continue, but network performance may be affected."
        echo ""
        sleep 3
    fi
    
    return 0
}

# Run the ethernet check
check_ethernet_connection

echo "Network requirements verified"
echo ""
echo "Proceeding with installation..."
echo ""

exit 0
'''
    
    def _generate_postinstall_script(self, server_config: Dict[str, Any]) -> str:
        """Generate postinstall script"""
        server_name = server_config.get('server_name', '')
        return f'''#!/bin/bash
set -e

echo "Installing Fleet Server (Standalone Mode)..."

# Set permissions
chmod -R 755 /Library/FleetServer
chmod 600 /Library/FleetServer/config/config.yaml

# Create data directory
mkdir -p /Library/FleetServer/data
mkdir -p /Library/FleetServer/certs
chmod 700 /Library/FleetServer/data

# Get hostname if not specified
HOSTNAME=$(hostname)
SERVER_ID="$HOSTNAME-$(date +%s)"

echo "Server ID: $SERVER_ID"
echo "Hostname: $HOSTNAME"
echo ""

# Install Python dependencies (if requirements.txt exists)
if [ -f "/Library/FleetServer/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip3 install -r /Library/FleetServer/requirements.txt || true
fi

# ============================================
# Install Homebrew packages for full functionality
# ============================================
echo ""
echo "Installing Homebrew packages for enhanced monitoring..."

# Check if Homebrew is installed, install if not
BREW_CMD=""
if [ -x "/opt/homebrew/bin/brew" ]; then
    BREW_CMD="/opt/homebrew/bin/brew"
elif [ -x "/usr/local/bin/brew" ]; then
    BREW_CMD="/usr/local/bin/brew"
fi

# Install Homebrew if not found (non-interactive for PKG deployment)
if [ -z "$BREW_CMD" ]; then
    echo "Homebrew not found. Attempting to install Homebrew..."

    # Get the console user (the user logged in at the GUI)
    CONSOLE_USER=$(stat -f "%Su" /dev/console)

    if [ -n "$CONSOLE_USER" ] && [ "$CONSOLE_USER" != "root" ]; then
        echo "Installing Homebrew for user: $CONSOLE_USER"

        # Non-interactive Homebrew installation
        sudo -u "$CONSOLE_USER" NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>/dev/null || true

        # Re-check for Homebrew after installation
        if [ -x "/opt/homebrew/bin/brew" ]; then
            BREW_CMD="/opt/homebrew/bin/brew"
            echo "Homebrew installed successfully at /opt/homebrew/bin/brew"
        elif [ -x "/usr/local/bin/brew" ]; then
            BREW_CMD="/usr/local/bin/brew"
            echo "Homebrew installed successfully at /usr/local/bin/brew"
        else
            echo "Homebrew installation failed. Continuing without Homebrew packages."
        fi
    else
        echo "No console user found. Skipping Homebrew installation."
    fi
fi

if [ -n "$BREW_CMD" ]; then
    echo "Homebrew found at: $BREW_CMD"

    # Required packages for core functionality
    PACKAGES_TO_INSTALL=""

    # smartmontools - SMART disk health monitoring
    if ! command -v smartctl &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL smartmontools"
        echo "  • smartmontools (SMART disk health)"
    else
        echo "  ✓ smartmontools already installed"
    fi

    # speedtest-cli - Network speed testing
    if ! command -v speedtest-cli &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL speedtest-cli"
        echo "  • speedtest-cli (network speed tests)"
    else
        echo "  ✓ speedtest-cli already installed"
    fi

    # mtr - Network path analysis
    if ! command -v mtr &> /dev/null; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL mtr"
        echo "  • mtr (network diagnostics)"
    else
        echo "  ✓ mtr already installed"
    fi

    # Temperature monitoring - architecture specific
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        if ! command -v macmon &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL macmon"
            echo "  • macmon (CPU temperature - Apple Silicon)"
        else
            echo "  ✓ macmon already installed"
        fi
    else
        if ! command -v osx-cpu-temp &> /dev/null; then
            PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL osx-cpu-temp"
            echo "  • osx-cpu-temp (CPU temperature - Intel)"
        else
            echo "  ✓ osx-cpu-temp already installed"
        fi
    fi

    # Install packages if any are needed
    if [ -n "$PACKAGES_TO_INSTALL" ]; then
        echo ""
        echo "Installing packages..."
        $BREW_CMD install $PACKAGES_TO_INSTALL 2>/dev/null && \\
            echo "✓ Homebrew packages installed successfully" || \\
            echo "⚠ Some packages could not be installed (non-critical)"
    else
        echo "✓ All required Homebrew packages already installed"
    fi
else
    echo "⚠ Homebrew not found. Some monitoring features will be limited."
    echo ""
    echo "To enable all monitoring features, install Homebrew:"
    echo "  /bin/bash -c \\"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\\""
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

# Load LaunchDaemon
echo "Configuring auto-start service..."
launchctl load /Library/LaunchDaemons/com.fleet.server.plist

# Start the service
echo "Starting Fleet Server..."
launchctl start com.fleet.server

echo ""
echo "Fleet Server installed successfully (Standalone Mode)!"
echo ""
echo "Access your dashboard at: http://$HOSTNAME:8778"
echo "   or: http://$(ipconfig getifaddr en0):8778"
echo ""
echo "On first access, you'll be prompted to create an admin account"
echo ""
echo "Configuration: /Library/FleetServer/config/config.yaml"
echo "📂 Database: /Library/FleetServer/data/fleet_data.db"
echo "Logs: /var/log/fleet-server.log"
echo ""
echo "Check status with: launchctl list | grep fleet.server"
echo ""

exit 0
'''
    
    def _generate_launchd_plist(self) -> str:
        """Generate LaunchDaemon plist"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fleet.server</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>-m</string>
        <string>atlas.fleet_server</string>
        <string>--config</string>
        <string>/Library/FleetServer/config/config.yaml</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Library/FleetServer</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/var/log/fleet-server.log</string>
    
    <key>StandardErrorPath</key>
    <string>/var/log/fleet-server-error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
'''
    
    def _build_pkg(self, pkg_root: str, scripts_dir: str, output_path: str, 
                   server_config: Dict[str, Any]) -> bool:
        """Build the actual .pkg file using pkgbuild"""
        try:
            # Generate package identifier
            pkg_id = "com.fleet.server.standalone"
            version = server_config.get('version', '1.0.0')
            
            # Build command
            cmd = [
                'pkgbuild',
                '--root', pkg_root,
                '--scripts', scripts_dir,
                '--identifier', pkg_id,
                '--version', version,
                '--install-location', '/',
                output_path
            ]
            
            logger.info(f"Building package: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Package built successfully")
                return True
            else:
                logger.error(f"pkgbuild failed: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Error running pkgbuild: {e}")
            return False


def build_standalone_server_package(output_path: str,
                                    server_name: Optional[str] = None) -> tuple[bool, str]:
    """
    Build a standalone server installer package
    
    Args:
        output_path: Where to save the .pkg file
        server_name: Optional name for the server
    
    Returns:
        (success, message)
    """
    server_config = {
        'version': '1.0.0',
        'server_name': server_name or 'Fleet Server'
    }
    
    builder = StandaloneServerPackageBuilder()
    return builder.build_package(output_path, server_config)
