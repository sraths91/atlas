# Fleet Agent Deployment Guide

## Quick Deployment Options

### Option 1: Self-Installing Script (Easiest)

Perfect for quick deployments to a few machines.

**Step 1: Create the installer**
```bash
cd fleet-agent
./create_installer.sh
```

**Step 2: Deploy to target Macs**
```bash
# Copy to remote Mac
scp dist/fleet-agent-installer.sh admin@mac:~/

# Run installer (will prompt for server details)
ssh admin@mac 'sudo ~/fleet-agent-installer.sh'
```

The installer will:
- Prompt for your fleet server URL and API key
- Install all dependencies automatically
- Configure auto-start on boot
- Start the agent immediately

**No manual configuration needed!**

---

### Option 2: macOS Package (.pkg)

Professional installer package for large-scale deployments.

**Step 1: Build the package**
```bash
cd fleet-agent
chmod +x build_macos_pkg.sh
./build_macos_pkg.sh
```

This creates: `dist/FleetAgent.pkg`

**Step 2: Deploy**

**Option A: Manual installation on each Mac**
```bash
sudo installer -pkg FleetAgent.pkg -target /
```

**Option B: Via Jamf Pro**
1. Upload `FleetAgent.pkg` to Jamf Pro
2. Create policy to deploy package
3. Add script to configure server URL:
```bash
#!/bin/bash
CONFIG="/Library/Application Support/FleetAgent/config.json"
cat > "$CONFIG" << EOF
{
    "server_url": "http://your-server:8768",
    "api_key": "your-api-key",
    "interval": 10
}
EOF
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

**Option C: Via Apple Remote Desktop**
1. Copy package to all Macs
2. Run installation command remotely

---

### Option 3: Direct Python Installation

For development or manual control.

**Step 1: Install on target Mac**
```bash
# Install via pip
pip3 install -e /path/to/fleet-agent

# Or from built wheel
cd fleet-agent
python3 setup.py bdist_wheel
pip3 install dist/*.whl
```

**Step 2: Create config**
```bash
mkdir -p ~/.fleet-agent
cat > ~/.fleet-agent/config.json << EOF
{
    "server_url": "http://your-server:8768",
    "api_key": "your-api-key",
    "interval": 10
}
EOF
```

**Step 3: Run agent**
```bash
fleet-agent --config ~/.fleet-agent/config.json
```

---

## Configuration

### Configuration File Location

After installation, edit:
```
/Library/Application Support/FleetAgent/config.json
```

### Configuration Options

```json
{
    "server_url": "http://fleet.example.com:8768",
    "api_key": "your-secret-key",
    "interval": 10,
    "machine_id": null
}
```

**Options:**
- `server_url` *(required)*: Fleet server URL with port
- `api_key` *(optional)*: Authentication key
- `interval` *(optional)*: Report interval in seconds (default: 10)
- `machine_id` *(optional)*: Custom ID (default: hostname)

---

## Managing the Service

### Start Service
```bash
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

### Stop Service
```bash
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
```

### Check Status
```bash
sudo launchctl list | grep fleet
```

### View Logs
```bash
# Real-time logs
tail -f /var/log/fleet-agent.log

# Error logs
tail -f /var/log/fleet-agent.error.log

# System logs
log stream --predicate 'subsystem == "com.fleet.agent"'
```

### Restart Service
```bash
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

---

## Verification

### Test Connectivity
```bash
# From target Mac, test server connectivity
curl http://your-server:8768/api/fleet/summary

# Should return JSON with fleet statistics
```

### Verify Agent is Running
```bash
# Check process
ps aux | grep fleet-agent

# Check LaunchDaemon status
sudo launchctl list | grep com.fleet.agent

# View recent logs
tail -20 /var/log/fleet-agent.log
```

### Check on Fleet Dashboard
1. Open fleet server dashboard: `http://your-server:8768/dashboard`
2. Look for the new machine in the list
3. Verify metrics are updating

---

## Deployment Scenarios

### Small Office (5-20 Macs)

Use self-installing script:
```bash
# Create installer once
./create_installer.sh

# Deploy to each Mac
for mac in mac1 mac2 mac3; do
    scp dist/fleet-agent-installer.sh admin@$mac:~/
    ssh admin@$mac 'sudo ~/fleet-agent-installer.sh'
done
```

### Medium Business (20-100 Macs)

Use .pkg with configuration script:
```bash
# Build package
./build_macos_pkg.sh

# Deploy via ARD or Jamf
# Include post-install configuration script
```

### Enterprise (100+ Macs)

Use MDM (Jamf/Intune) with configuration profile:
1. Build and upload .pkg to MDM
2. Create configuration profile with settings
3. Deploy to computer groups
4. Monitor deployment via MDM

---

## Updating

### Update Configuration
```bash
# Edit config
sudo nano /Library/Application\ Support/FleetAgent/config.json

# Restart service
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

### Update Agent
```bash
# Rebuild package with new version
./build_macos_pkg.sh

# Deploy update (will preserve config)
sudo installer -pkg dist/FleetAgent.pkg -target /
```

---

## Uninstallation

### Manual Uninstall
```bash
# Stop service
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist

# Remove files
sudo rm /Library/LaunchDaemons/com.fleet.agent.plist
sudo rm -rf /Library/Application\ Support/FleetAgent
sudo rm /usr/local/bin/fleet-agent

# Remove logs
sudo rm /var/log/fleet-agent*.log

# Uninstall pip package (if installed that way)
pip3 uninstall -y mac-fleet-agent
```

### Uninstall Script
```bash
#!/bin/bash
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist 2>/dev/null
sudo rm /Library/LaunchDaemons/com.fleet.agent.plist
sudo rm -rf /Library/Application\ Support/FleetAgent
sudo rm /usr/local/bin/fleet-agent
sudo rm /var/log/fleet-agent*.log
echo "Fleet Agent uninstalled"
```

---

## Troubleshooting

### Agent Not Connecting

**Check configuration:**
```bash
cat /Library/Application\ Support/FleetAgent/config.json
```

**Test server connectivity:**
```bash
curl -v http://your-server:8768/api/fleet/summary
```

**Check firewall:**
- Ensure port 8768 (or your custom port) is open
- Test with: `telnet your-server 8768`

**View logs:**
```bash
tail -50 /var/log/fleet-agent.error.log
```

### Service Not Starting

**Check LaunchDaemon:**
```bash
sudo launchctl list | grep fleet
```

**Verify file permissions:**
```bash
ls -la /Library/LaunchDaemons/com.fleet.agent.plist
ls -la /usr/local/bin/fleet-agent
```

**Test manually:**
```bash
/usr/local/bin/fleet-agent /Library/Application\ Support/FleetAgent/config.json
```

### High Resource Usage

**Increase reporting interval:**
Edit config, change `interval` to 30 or 60 seconds.

**Check for network issues:**
Frequent connection failures cause retries.

---

## Security Considerations

### API Key Management
- Generate unique API keys per environment
- Rotate keys periodically
- Use configuration management to distribute keys securely

### Network Security
- Use HTTPS for fleet server in production
- Implement firewall rules to restrict access
- Consider VPN for remote machines

### Permissions
- Agent runs as root (required for system metrics)
- Configuration files should be readable only by root
- Logs are world-readable (contains no sensitive data)

---

## Support

**Logs:** `/var/log/fleet-agent.log`  
**Config:** `/Library/Application Support/FleetAgent/config.json`  
**Service:** `/Library/LaunchDaemons/com.fleet.agent.plist`

For issues, check logs first, then verify configuration and connectivity.
