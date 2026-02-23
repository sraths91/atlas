# Split-Mode Package Update

## Overview

The Fleet Server's package creator has been updated to generate **split-mode installers** as the primary agent package. This provides better reliability and functionality compared to the previous single-mode installer.

---

## What Changed

### 1. **Agent Package Builder** (`fleet_agent_builder.py`)

**Updated Method:** `build_package()`

**Changes:**
- Now packages the entire `atlas` module (not just select files)
- Includes all split-mode installer scripts and plists
- Creates comprehensive README with split-mode instructions
- Package name changed from `FleetAgent_Installer` to `ATLAS_Fleet_Installer`

**Files Included in Package:**
- `install_split_mode.sh` - Main installer script
- `start_agent_daemon.py` - Core agent launcher (no GUI)
- `launch_atlas_with_config.py` - Smart launcher with auto-config
- `repair_credentials.py` - Credential management
- `update_fleet_config.py` - Config updater
- `show_credentials.py` - Config viewer
- `com.atlas.fleetserver.daemon.plist` - Fleet Server LaunchDaemon
- `com.atlas.agent.daemon.plist` - Core Agent LaunchDaemon
- `com.atlas.menubar.plist` - Menu Bar LaunchAgent
- `atlas/` - Complete Python package
- `fleet-config-template.json` - Pre-configured settings
- `README.md` - Installation instructions

---

### 2. **Fleet Dashboard** (`fleet_server.py`)

**Updated:** Download button and alert message

**Changes:**
- Download filename: `ATLAS_Fleet_Installer.zip` (was `FleetAgent_Installer.zip`)
- Alert message now explains split-mode architecture:
  ```
  ✅ ATLAS Fleet Installer downloaded!
  
  Extract the zip file and run:
    sudo ./install_split_mode.sh
  
  This installs:
  • Fleet Server (starts at boot)
  • Core Agent (starts at boot)
  • Menu Bar App (starts at login)
  ```

---

## Split-Mode Architecture

### Boot-Time Services (LaunchDaemons)
**Start before login, no GUI access**

1. **Fleet Server**
   - Port: 8768 (HTTPS)
   - Location: `/Library/LaunchDaemons/com.atlas.fleetserver.plist`
   - Logs: `/var/log/atlas-fleetserver.log`

2. **Core Agent**
   - Port: 8767 (HTTP)
   - Location: `/Library/LaunchDaemons/com.atlas.agent.core.plist`
   - Logs: `/var/log/atlas-agent.log`
   - Reports metrics every 10 seconds

### Login-Time Services (LaunchAgent)
**Start after user login, has GUI access**

3. **Menu Bar App**
   - Location: `~/Library/LaunchAgents/com.atlas.menubar.plist`
   - Logs: `~/.atlas-menubar.log`
   - Shows status icon in menu bar

---

## Benefits of Split-Mode

### ✅ **Server Available Immediately**
- Fleet Server starts at boot, before any user logs in
- No waiting for login to access monitoring

### ✅ **Agent Reports from Boot**
- Core Agent begins reporting metrics immediately
- Monitoring starts as soon as system boots

### ✅ **Survives Logout**
- Server and agent keep running when user logs out
- Continuous monitoring without interruption

### ✅ **Menu Bar When Needed**
- GUI components only load when user logs in
- No wasted resources when running headless

### ✅ **Auto-Restart**
- All services configured with `KeepAlive`
- Automatic restart on crash

### ✅ **Secure Credential Management**
- API key auto-loaded from encrypted config
- No hardcoded credentials in scripts

---

## Installation Process

### For End Users

1. **Download** package from Fleet Dashboard
2. **Extract** the ZIP file
3. **Run** installer:
   ```bash
   cd atlas_agent
   sudo ./install_split_mode.sh
   ```
4. **Enter** sudo password when prompted
5. **Done!** All services start automatically

### What the Installer Does

1. Checks for existing encrypted config
2. Prompts for credentials if needed (username/password/API key)
3. Installs Fleet Server LaunchDaemon
4. Installs Core Agent LaunchDaemon
5. Installs Menu Bar LaunchAgent
6. Starts all services immediately
7. Configures auto-start for future reboots

---

## Accessing the Package Creator

### From Fleet Dashboard

1. Log into Fleet Dashboard: `https://localhost:8768/dashboard`
2. Look for **"Download Agent Installer"** button
3. Click to generate and download package
4. Package is customized with your server's:
   - Fleet Server URL
   - API Key
   - Organization name

### Programmatically

```python
from atlas.fleet_agent_builder import AgentPackageBuilder

# Initialize with config
builder = AgentPackageBuilder()

# Build package
package_path = builder.build_package(
    output_dir="/path/to/output",
    widget_config={'wifi': True, 'speedtest': True, 'ping': True},
    tool_config={'metrics': True, 'logs': True, 'commands': True}
)

print(f"Package created: {package_path}")
```

---

## Comparison: Old vs New

| Feature | Old Installer | New Split-Mode Installer |
|---------|--------------|--------------------------|
| **Start Time** | After login | At boot (server/agent) + login (menu bar) |
| **Survives Logout** | ❌ No | ✅ Yes |
| **Menu Bar Icon** | ✅ Yes | ✅ Yes |
| **Server Included** | ❌ No | ✅ Yes |
| **Auto-Restart** | ⚠️ Partial | ✅ Full |
| **API Key Management** | ⚠️ Manual | ✅ Automatic |
| **Package Size** | ~50KB | ~2MB (includes full module) |
| **Installation** | User-level | System-level (requires sudo) |

---

## Testing the Package

### Generate Test Package

```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
python3 -m atlas.fleet_agent_builder
```

### Or via Dashboard

1. Open Fleet Dashboard
2. Click "Download Agent Installer"
3. Extract ZIP
4. Review `README.md`
5. Test installation on a clean Mac

---

## Troubleshooting

### Package Generation Fails

**Check:**
- Fleet config exists: `~/.fleet-config.json.encrypted`
- Config has required fields: `server.api_key`, `server.host`, `server.port`

**Fix:**
```bash
python3 repair_credentials.py
```

### Installer Fails on Target Mac

**Common Issues:**
1. **Not running with sudo** → Run: `sudo ./install_split_mode.sh`
2. **Python not installed** → Install Python 3.9+
3. **Port already in use** → Check: `lsof -i :8767` and `lsof -i :8768`

### Services Not Starting

**Check logs:**
```bash
tail -f /var/log/atlas-fleetserver.log
tail -f /var/log/atlas-agent.log
tail -f ~/.atlas-menubar.log
```

**Restart services:**
```bash
sudo launchctl kickstart -k system/com.atlas.fleetserver
sudo launchctl kickstart -k system/com.atlas.agent.core
launchctl kickstart -k gui/$(id -u)/com.atlas.menubar
```

---

## Future Enhancements

Potential improvements for the package creator:

1. **Custom branding** - Allow organization logo/name customization
2. **Selective components** - Option to install only server OR only agent
3. **Pre-configured widgets** - Enable/disable specific monitoring widgets
4. **Update mechanism** - Built-in update checker and installer
5. **Uninstaller** - Dedicated uninstall script in package

---

## Summary

The split-mode installer is now the **primary package** generated by the Fleet Server's package creator. It provides:

- ✅ **Better reliability** - Services start at boot
- ✅ **Complete solution** - Includes server, agent, and menu bar
- ✅ **Automatic configuration** - API keys and credentials managed securely
- ✅ **Professional deployment** - System-level installation with proper LaunchDaemons

**All packages downloaded from the Fleet Dashboard now use this architecture.**

---

**Last Updated:** December 3, 2025
**Package Version:** Split-Mode v1.0
