# Mac Fleet Agent

A lightweight monitoring agent that reports system metrics from macOS machines to a central fleet server.

## Features

- **Real-time Monitoring**: CPU, memory, disk, network, battery metrics
- **Secure Communication**: API key authentication and SSL support
- **Zero Configuration**: Automatic machine identification
- **Lightweight**: Minimal resource usage
- **Auto-Restart**: Integrated with macOS LaunchAgent for reliability

## Installation

### Quick Install (Recommended)

Download and run the installer package:

```bash
sudo installer -pkg FleetAgent.pkg -target /
```

The installer will:
- Install the agent and all dependencies
- Create configuration file at `/Library/Application Support/FleetAgent/config.json`
- Set up automatic startup via LaunchDaemon

### Manual Installation

```bash
# Install via pip
pip3 install mac-fleet-agent

# Configure
fleet-agent --server http://your-fleet-server:8768 --api-key YOUR_API_KEY
```

## Configuration

Edit `/Library/Application Support/FleetAgent/config.json`:

```json
{
    "server_url": "http://your-fleet-server:8768",
    "api_key": "your-secret-api-key",
    "interval": 10,
    "machine_id": null
}
```

**Configuration Options:**
- `server_url`: URL of your fleet server (required)
- `api_key`: Authentication key (optional but recommended)
- `interval`: Reporting interval in seconds (default: 10)
- `machine_id`: Custom machine identifier (default: hostname)

## Usage

### Start Agent

```bash
# Using configuration file
fleet-agent --config /Library/Application\ Support/FleetAgent/config.json

# With command-line arguments
fleet-agent --server http://server:8768 --api-key KEY --interval 10

# Debug mode
fleet-agent --config /path/to/config.json --debug
```

### Check Status

```bash
# View logs
sudo log stream --predicate 'subsystem == "com.fleet.agent"' --level debug

# Check if running
ps aux | grep fleet-agent

# LaunchDaemon status
sudo launchctl list | grep com.fleet.agent
```

### Stop Agent

```bash
# If installed as LaunchDaemon
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist

# Kill process
pkill -f fleet-agent
```

## Deployment

### Single Machine

```bash
# Install package
sudo installer -pkg FleetAgent.pkg -target /

# Edit configuration
sudo nano /Library/Application\ Support/FleetAgent/config.json

# Start service
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

### Fleet-Wide (Jamf Pro)

1. Upload `FleetAgent.pkg` to Jamf Pro
2. Create a configuration profile with your server settings
3. Deploy via policy to all Macs

### Fleet-Wide (Manual)

```bash
# Copy installer to each Mac
scp FleetAgent.pkg admin@mac:~/

# SSH to each Mac and install
ssh admin@mac 'sudo installer -pkg ~/FleetAgent.pkg -target /'
```

## Building from Source

```bash
# Clone repository
cd fleet-agent

# Build package
./build_macos_pkg.sh

# Output: dist/FleetAgent.pkg
```

## Metrics Collected

- **System**: Hostname, OS version, hardware specs, serial number
- **CPU**: Usage percentage, load average, core count
- **Memory**: Total, used, available, swap usage
- **Disk**: Usage per partition, I/O statistics
- **Network**: Bytes sent/received, packets, interface status
- **Battery**: Charge level, power status, time remaining
- **Processes**: Process count, top CPU/memory consumers

## Security

- **Encryption**: All communication over HTTPS (if configured)
- **Authentication**: API key validation on server
- **Permissions**: Runs with minimal required privileges
- **Privacy**: Only system metrics collected, no personal data

## Troubleshooting

### Agent Not Connecting

```bash
# Test server connectivity
curl http://your-server:8768/api/fleet/summary

# Check firewall
telnet your-server 8768

# View agent logs
tail -f /var/log/fleet-agent.log
```

### High CPU Usage

- Increase reporting interval to reduce load
- Check for network issues causing retries

### Service Not Starting

```bash
# Check LaunchDaemon
sudo launchctl list | grep fleet

# Reload service
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist

# Check permissions
ls -la /Library/LaunchDaemons/com.fleet.agent.plist
```

## Uninstall

```bash
# Stop service
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist

# Remove files
sudo rm /Library/LaunchDaemons/com.fleet.agent.plist
sudo rm -rf /Library/Application\ Support/FleetAgent
sudo rm /usr/local/bin/fleet-agent

# Uninstall Python package
pip3 uninstall mac-fleet-agent
```

## Support

- **Documentation**: See fleet server documentation
- **Logs**: `/var/log/fleet-agent.log`
- **Issues**: Contact your IT administrator

## License

MIT License - See LICENSE file for details
