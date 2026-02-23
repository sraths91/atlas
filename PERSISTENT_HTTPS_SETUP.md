# Persistent HTTPS Setup for ATLAS Fleet Server

## Problem

After fixing the HTTPS/TLS connection issues, the system would revert to HTTP or fail to start properly after a reboot because:

1. **LaunchDaemons had outdated configuration** - They didn't include the API key or proper paths
2. **SSL configuration wasn't persistent** - The encrypted config could become corrupted or missing SSL paths
3. **Code changes weren't reflected** - The TLS version fix in `fleet_server.py` wasn't being used by LaunchDaemons
4. **Multiple service managers conflicted** - Both user-level and system-level services competed for ports

## Solution

### 1. Updated SSL/TLS Configuration

**File:** `atlas/fleet_server.py` (lines 2950-2952)

```python
# Set minimum TLS version for compatibility
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.maximum_version = ssl.TLSVersion.TLSv1_3
```

This fixes the `ERR_SSL_PROTOCOL_ERROR` and `wrong version number` errors by ensuring TLS 1.2/1.3 compatibility.

### 2. Persistent Encrypted Configuration

**File:** `set_credentials.py`

The configuration now includes SSL certificate paths:

```python
config_data = {
    'organization_name': 'ATLAS Fleet',
    'server': {
        'api_key': api_key,
        'fleet_server_url': 'https://localhost:8768',
        'web_username': username,
        'web_password': password
    },
    'ssl': {
        'cert_file': '/Users/samraths/.fleet-certs/cert.pem',
        'key_file': '/Users/samraths/.fleet-certs/privkey.pem'
    }
}
```

### 3. System-Level LaunchDaemons

**Location:** `/Library/LaunchDaemons/`

Both services are configured as system-level daemons that:
- Start automatically at boot (before user login)
- Run as the user (not root) for proper file access
- Include the API key directly in the plist
- Use the correct project paths
- Auto-restart on failure

### 4. Installation Script

**File:** `install_persistent_https.sh`

This script:
1. ✅ Verifies/creates encrypted config with SSL paths
2. ✅ Extracts API key from config
3. ✅ Creates LaunchDaemon plists with correct configuration
4. ✅ Sets up log files with proper permissions
5. ✅ Stops conflicting services
6. ✅ Loads and starts services
7. ✅ Verifies HTTPS is working

## Installation

```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
sudo ./install_persistent_https.sh
```

## What Happens on Reboot

1. **System boots** → `launchd` starts
2. **Fleet Server starts** (as LaunchDaemon)
   - Loads encrypted config from `~/.fleet-config.json.encrypted`
   - Reads SSL certificate paths from config
   - Applies TLS 1.2/1.3 configuration
   - Starts HTTPS server on port 8768
3. **Core Agent starts** (as LaunchDaemon)
   - Uses API key from plist
   - Connects to Fleet Server via HTTPS
   - No SSL errors due to TLS version compatibility
4. **Services auto-restart** if they crash

## Verification After Reboot

```bash
# Check services are running
sudo launchctl list | grep atlas

# Check ports
lsof -i :8768 -i :8767

# Test HTTPS
curl -k https://localhost:8768/

# Test agent health
curl http://localhost:8767/api/agent/health

# Check logs
tail -f /var/log/atlas-fleetserver.log
tail -f /var/log/atlas-agent.log
```

## Key Files

### Configuration
- `~/.fleet-config.json.encrypted` - Encrypted config with SSL paths and credentials
- `~/.fleet-certs/cert.pem` - SSL certificate
- `~/.fleet-certs/privkey.pem` - SSL private key

### LaunchDaemons
- `/Library/LaunchDaemons/com.atlas.fleetserver.plist` - Fleet Server service
- `/Library/LaunchDaemons/com.atlas.agent.core.plist` - Core Agent service

### Logs
- `/var/log/atlas-fleetserver.log` - Fleet Server output
- `/var/log/atlas-fleetserver.error.log` - Fleet Server errors
- `/var/log/atlas-agent.log` - Agent output
- `/var/log/atlas-agent.error.log` - Agent errors

### Code
- `atlas/fleet_server.py` - Contains TLS version fix
- `set_credentials.py` - Creates config with SSL paths

## Management Commands

### Check Status
```bash
sudo launchctl list | grep atlas
```

### Restart Services
```bash
# Restart Fleet Server
sudo launchctl kickstart -k system/com.atlas.fleetserver

# Restart Agent
sudo launchctl kickstart -k system/com.atlas.agent.core
```

### Stop Services
```bash
sudo launchctl unload /Library/LaunchDaemons/com.atlas.fleetserver.plist
sudo launchctl unload /Library/LaunchDaemons/com.atlas.agent.core.plist
```

### Start Services
```bash
sudo launchctl load /Library/LaunchDaemons/com.atlas.fleetserver.plist
sudo launchctl load /Library/LaunchDaemons/com.atlas.agent.core.plist
```

### View Logs
```bash
# Real-time logs
tail -f /var/log/atlas-fleetserver.log
tail -f /var/log/atlas-agent.log

# Recent errors
tail -50 /var/log/atlas-fleetserver.error.log
tail -50 /var/log/atlas-agent.error.log
```

## Troubleshooting

### Issue: Services don't start after reboot

**Check:**
```bash
sudo launchctl list | grep atlas
cat /var/log/atlas-fleetserver.error.log
```

**Solution:** Reinstall with `sudo ./install_persistent_https.sh`

### Issue: HTTPS not working

**Check:**
```bash
python3 -c "from atlas.fleet_config import FleetConfig; c = FleetConfig(); print('SSL Cert:', c.get('ssl.cert_file'))"
```

**Solution:** If SSL paths are missing, run `python3 set_credentials.py`

### Issue: Agent can't connect

**Check:**
```bash
grep -i "ssl\|error" /var/log/atlas-agent.error.log
```

**Solution:** Verify API key matches in both config and agent plist

### Issue: Port already in use

**Check:**
```bash
lsof -i :8768
lsof -i :8767
```

**Solution:**
```bash
# Kill processes
sudo killall -9 Python
sleep 3

# Restart services
sudo launchctl kickstart -k system/com.atlas.fleetserver
sudo launchctl kickstart -k system/com.atlas.agent.core
```

## Benefits of This Setup

1. ✅ **Survives reboots** - Services start automatically
2. ✅ **HTTPS always enabled** - SSL paths in persistent config
3. ✅ **TLS compatibility** - Version fix applied on every start
4. ✅ **Auto-recovery** - Services restart on crash
5. ✅ **No manual intervention** - Fully automated
6. ✅ **Proper permissions** - Runs as user, not root
7. ✅ **Centralized logs** - Easy troubleshooting
8. ✅ **Single source of truth** - LaunchDaemons use updated code

## Security Notes

- API key is stored in LaunchDaemon plist (readable by root only)
- Encrypted config contains credentials (user-readable only)
- SSL certificates are self-signed (for localhost use)
- Web dashboard requires username/password authentication

## Future Improvements

1. Store API key in macOS Keychain instead of plist
2. Use proper CA-signed certificates
3. Add health monitoring and alerting
4. Implement automatic certificate renewal
5. Add configuration validation on startup
