"""
Fleet Configuration Management
Allows different organizations to customize their fleet deployment
"""
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import encryption
try:
    from .fleet_config_encryption import EncryptedConfigManager, ENCRYPTION_AVAILABLE
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logger.warning("Encryption module not available")


class FleetConfig:
    """Configuration for fleet deployment"""
    
    DEFAULT_CONFIG = {
        'organization': {
            'name': 'My Organization',
            'id': None,  # Auto-generated if not provided
            'contact': 'admin@example.com'
        },
        'server': {
            'port': 8778,
            'host': '0.0.0.0',
            'api_key': None,  # Auto-generated if not provided
            'history_size': 1000,
            'db_path': str(Path.home() / '.fleet-data' / 'fleet_data.sqlite3'),
            'history_retention_days': 30
        },
        'agent': {
            'report_interval': 10,
            'retry_interval': 30,
            'timeout': 5
        },
        'branding': {
            'primary_color': '#00ff00',
            'secondary_color': '#0a0a0a',
            'logo_url': None,
            'dashboard_title': 'Fleet Dashboard'
        },
        'alerts': {
            'cpu_threshold': 90,
            'memory_threshold': 90,
            'disk_threshold': 90,
            'enabled': True
        },
        'features': {
            'auto_discovery': True,
            'historical_data': True,
            'alerts': True,
            'api_access': True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration

        Args:
            config_path: Path to config file (default: ~/.fleet-config.json)
        """
        if config_path is None:
            config_path = str(Path.home() / '.fleet-config.json')

        self.config_path = Path(config_path)
        self.encryption_manager = None
        
        if ENCRYPTION_AVAILABLE:
            self.encryption_manager = EncryptedConfigManager(config_path)
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        # Try encrypted config first
        if self.encryption_manager:
            config = self.encryption_manager.decrypt_config()
            if config:
                logger.info("Loaded encrypted configuration")
                return self._merge_config(self.DEFAULT_CONFIG.copy(), config)
        
        # Fall back to plaintext
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    logger.info("Loaded plaintext configuration")
                    
                    # Auto-migrate to encrypted if available
                    if self.encryption_manager:
                        logger.info("Migrating plaintext config to encrypted format...")
                        self.encryption_manager.encrypt_config(config)
                    
                    # Merge with defaults to ensure all keys exist
                    return self._merge_config(self.DEFAULT_CONFIG.copy(), config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                logger.info("Using default configuration")
        
        return self.DEFAULT_CONFIG.copy()
    
    def _merge_config(self, base: Dict, override: Dict) -> Dict:
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._merge_config(base[key], value)
            else:
                base[key] = value
        return base
    
    def save(self):
        """Save configuration to file (encrypted if available)"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use encryption if available
            if self.encryption_manager:
                if self.encryption_manager.encrypt_config(self.config):
                    logger.info(f"Configuration encrypted and saved")
                else:
                    logger.error("Failed to encrypt configuration")
            else:
                # Fall back to plaintext
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
                self.config_path.chmod(0o600)  # Restrict permissions
                logger.warning(f"Configuration saved in plaintext (encryption not available)")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get(self, key_path: str, default=None):
        """
        Get configuration value by dot-notation path
        
        Example: config.get('server.port') -> 8778
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value by dot-notation path
        
        Example: config.set('server.port', 9000)
        """
        keys = key_path.split('.')
        target = self.config
        
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        target[keys[-1]] = value
    
    def generate_org_id(self) -> str:
        """Generate unique organization ID"""
        org_id = str(uuid.uuid4())
        self.set('organization.id', org_id)
        return org_id
    
    def generate_api_key(self) -> str:
        """Generate secure API key"""
        import secrets
        api_key = secrets.token_urlsafe(32)
        self.set('server.api_key', api_key)
        return api_key
    
    def ensure_required_fields(self):
        """Ensure all required fields are set"""
        if not self.get('organization.id'):
            self.generate_org_id()
        
        if not self.get('server.api_key'):
            self.generate_api_key()
    
    def export_agent_config(self, server_url: str) -> Dict[str, Any]:
        """
        Export configuration for agents
        
        Args:
            server_url: URL of the fleet server
        
        Returns:
            Dictionary with agent configuration
        """
        return {
            'server_url': server_url,
            'organization_id': self.get('organization.id'),
            'api_key': self.get('server.api_key'),
            'report_interval': self.get('agent.report_interval'),
            'retry_interval': self.get('agent.retry_interval'),
            'timeout': self.get('agent.timeout')
        }
    
    def export_agent_config_file(self, server_url: str, output_path: str):
        """
        Export agent configuration to file
        
        Args:
            server_url: URL of the fleet server
            output_path: Path to save agent config
        """
        agent_config = self.export_agent_config(server_url)
        
        try:
            with open(output_path, 'w') as f:
                json.dump(agent_config, f, indent=2)
            print(f"Agent configuration exported to: {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting agent config: {e}")
            return False
    
    def get_install_script(self, server_url: str) -> str:
        """
        Generate installation script for agents
        
        Args:
            server_url: URL of the fleet server
        
        Returns:
            Shell script content
        """
        config = self.export_agent_config(server_url)
        
        return f'''#!/bin/bash
# Fleet Agent Installation Script
# Organization: {self.get('organization.name')}
# Generated: $(date)

set -e

echo "Installing Fleet Agent for {self.get('organization.name')}..."

# Configuration
SERVER_URL="{config['server_url']}"
ORG_ID="{config['organization_id']}"
API_KEY="{config['api_key']}"
INTERVAL={config['report_interval']}

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install --user psutil requests

# Create config directory
CONFIG_DIR="$HOME/.fleet-agent"
mkdir -p "$CONFIG_DIR"

# Save configuration
cat > "$CONFIG_DIR/config.json" << 'EOF'
{{
    "server_url": "$SERVER_URL",
    "organization_id": "$ORG_ID",
    "api_key": "$API_KEY",
    "report_interval": $INTERVAL
}}
EOF

echo "Configuration saved to: $CONFIG_DIR/config.json"

# Create LaunchAgent plist
PLIST_PATH="$HOME/Library/LaunchAgents/com.{self.get('organization.id')}.fleet-agent.plist"

cat > "$PLIST_PATH" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{self.get('organization.id')}.fleet-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>atlas.fleet_agent</string>
        <string>--config</string>
        <string>$CONFIG_DIR/config.json</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/fleet-agent.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/fleet-agent.error.log</string>
</dict>
</plist>
EOF

# Load LaunchAgent
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "Fleet Agent installed successfully!"
echo ""
echo "Organization: {self.get('organization.name')}"
echo "Server: $SERVER_URL"
echo "Machine ID: $(hostname)"
echo ""
echo "Logs: $HOME/Library/Logs/fleet-agent.log"
echo ""
echo "To uninstall: launchctl unload $PLIST_PATH"
'''
    
    def display(self):
        """Display current configuration"""
        print("\n" + "="*60)
        print(f"Fleet Configuration: {self.get('organization.name')}")
        print("="*60)
        print(f"\nOrganization:")
        print(f"  Name: {self.get('organization.name')}")
        print(f"  ID: {self.get('organization.id')}")
        print(f"  Contact: {self.get('organization.contact')}")
        print(f"\nServer:")
        print(f"  Port: {self.get('server.port')}")
        print(f"  Host: {self.get('server.host')}")
        print(f"  API Key: {'*' * 20 if self.get('server.api_key') else 'Not set'}")
        print(f"\nAgent:")
        print(f"  Report Interval: {self.get('agent.report_interval')}s")
        print(f"  Retry Interval: {self.get('agent.retry_interval')}s")
        print(f"\nBranding:")
        print(f"  Dashboard Title: {self.get('branding.dashboard_title')}")
        print(f"  Primary Color: {self.get('branding.primary_color')}")
        print(f"\nAlerts:")
        print(f"  Enabled: {self.get('alerts.enabled')}")
        print(f"  CPU Threshold: {self.get('alerts.cpu_threshold')}%")
        print(f"  Memory Threshold: {self.get('alerts.memory_threshold')}%")
        print(f"  Disk Threshold: {self.get('alerts.disk_threshold')}%")
        print("\n" + "="*60 + "\n")


def setup_wizard():
    """Interactive setup wizard for fleet configuration"""
    print("\n" + "="*60)
    print("Fleet Dashboard Setup Wizard")
    print("="*60 + "\n")
    
    config = FleetConfig()
    
    # Organization info
    print("Organization Information:")
    org_name = input(f"  Organization name [{config.get('organization.name')}]: ").strip()
    if org_name:
        config.set('organization.name', org_name)
    
    contact = input(f"  Contact email [{config.get('organization.contact')}]: ").strip()
    if contact:
        config.set('organization.contact', contact)
    
    # Server settings
    print("\nServer Settings:")
    port = input(f"  Server port [{config.get('server.port')}]: ").strip()
    if port:
        config.set('server.port', int(port))
    
    # Agent settings
    print("\nAgent Settings:")
    interval = input(f"  Report interval in seconds [{config.get('agent.report_interval')}]: ").strip()
    if interval:
        config.set('agent.report_interval', int(interval))
    
    # Branding
    print("\nBranding:")
    title = input(f"  Dashboard title [{config.get('branding.dashboard_title')}]: ").strip()
    if title:
        config.set('branding.dashboard_title', title)
    
    color = input(f"  Primary color [{config.get('branding.primary_color')}]: ").strip()
    if color:
        config.set('branding.primary_color', color)
    
    # Generate required fields
    print("\nGenerating secure credentials...")
    config.ensure_required_fields()
    
    # Save configuration
    config.save()
    
    print("\nConfiguration complete!")
    config.display()
    
    # Offer to generate agent installer
    print("\nWould you like to generate an agent installation script?")
    server_url = input("  Server URL (e.g., http://fleet.company.com:8778): ").strip()
    
    if server_url:
        script_path = f"install-agent-{config.get('organization.id')[:8]}.sh"
        script_content = config.get_install_script(server_url)
        
        script_file = Path(script_path)
        with open(script_file, 'w') as f:
            f.write(script_content)

        script_file.chmod(0o755)
        
        print(f"\nAgent installation script created: {script_path}")
        print(f"\nDistribute this script to all machines you want to monitor.")
        print(f"Users can run: ./{script_path}")
    
    return config


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        setup_wizard()
    else:
        config = FleetConfig()
        config.display()
