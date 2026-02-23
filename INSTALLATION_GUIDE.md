# 🚀 ATLAS Fleet Server & Agent Installation Guide

## Overview

This guide covers the complete installation of the ATLAS Fleet monitoring system, including:
- Fleet Server (central monitoring dashboard)
- ATLAS Agent (runs on each Mac, reports to Fleet Server)
- Menu bar icon with live status
- Auto-start on login (both server and agent)
- Automatic API key management

---

## 📋 Prerequisites

- macOS 10.14 or later
- Python 3.9 or later
- Terminal access

---

## 🎯 Quick Install (Recommended)

### One-Command Installation

```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
./install_agent.sh
```

**This single script will:**
1. ✅ Check for encrypted config (create if missing)
2. ✅ Set up credentials (username, password, API key)
3. ✅ Install Fleet Server LaunchAgent
4. ✅ Install ATLAS Agent LaunchAgent (with menu bar)
5. ✅ Configure auto-start on login
6. ✅ Start both services immediately

**No sudo required** - runs as your user account.

---

## 📝 What Gets Installed

### 1. Fleet Server
- **Location:** Runs from project directory
- **Port:** 8768 (HTTPS)
- **LaunchAgent:** `~/Library/LaunchAgents/com.atlas.fleetserver.plist`
- **Logs:** `~/.atlas-fleetserver.log` and `~/.atlas-fleetserver.error.log`
- **Auto-start:** Yes, on every login

### 2. ATLAS Agent
- **Location:** Runs from project directory
- **Port:** 8767 (HTTP)
- **LaunchAgent:** `~/Library/LaunchAgents/com.atlas.agent.plist`
- **Logs:** `~/.atlas-agent.log` and `~/.atlas-agent.error.log`
- **Menu Bar:** Icon appears in top-right corner
- **Auto-start:** Yes, on every login

### 3. Configuration
- **Encrypted Config:** `~/.fleet-config.json.encrypted`
- **Contains:**
  - API key (for agent authentication)
  - Fleet Server URL
  - Web username/password (for dashboard login)

---

## 🔧 Installation Steps (Detailed)

### Step 1: Navigate to Project

```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
```

### Step 2: Run Installer

```bash
./install_agent.sh
```

### Step 3: Set Credentials (First Time Only)

If no encrypted config exists, you'll be prompted:

```
⚠️  No encrypted config found
Setting up credentials...

Enter username (default: admin): admin
Enter password: [your-password]
Confirm password: [your-password]
```

**This creates:**
- Web login credentials for Fleet dashboard
- API key for agent-to-server communication
- Encrypted config file

### Step 4: Verify Installation

The installer will show:

```
✅ Installation Complete!

✅ Fleet Server: Running
✅ ATLAS Agent: Running

Features Enabled:
  ✅ Auto-start on login
  ✅ Auto-restart on crash
  ✅ Fleet Server on port 8768
  ✅ Agent with menu bar icon on port 8767
  ✅ API key auto-loaded from encrypted config
```

### Step 5: Access Dashboards

**Fleet Dashboard:**
```
https://localhost:8768/dashboard
```
Login with credentials you set in Step 3.

**Agent Dashboard:**
```
http://localhost:8767
```
No login required.

**Menu Bar Icon:**
Check top-right corner of screen for ATLAS icon with status dot.

---

## ✅ Verification

### Check Services Are Running

```bash
launchctl list | grep atlas
```

**Expected output:**
```
-	0	com.atlas.agent
-	0	com.atlas.fleetserver
```

### Check Logs

```bash
# Fleet Server logs
tail -f ~/.atlas-fleetserver.log

# Agent logs
tail -f ~/.atlas-agent.log
```

### Test Endpoints

```bash
# Test agent
curl http://localhost:8767/

# Test Fleet Server
curl -k https://localhost:8768/
```

---

## 🔄 After Reboot

**Both services start automatically** when you log in.

1. Log into your Mac
2. Wait ~5-10 seconds
3. Check menu bar for ATLAS icon (top-right)
4. Open dashboards in browser

**No manual intervention needed!**

---

## 🛠️ Management Commands

### Check Status

```bash
launchctl list | grep atlas
```

### Restart Services

```bash
# Restart agent
launchctl kickstart -k gui/$(id -u)/com.atlas.agent

# Restart Fleet Server
launchctl kickstart -k gui/$(id -u)/com.atlas.fleetserver
```

### Stop Services

```bash
# Stop agent
launchctl unload ~/Library/LaunchAgents/com.atlas.agent.plist

# Stop Fleet Server
launchctl unload ~/Library/LaunchAgents/com.atlas.fleetserver.plist
```

### Start Services

```bash
# Start agent
launchctl load ~/Library/LaunchAgents/com.atlas.agent.plist

# Start Fleet Server
launchctl load ~/Library/LaunchAgents/com.atlas.fleetserver.plist
```

---

## 🔐 Credential Management

### Change Password or API Key

```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
python3 repair_credentials.py
```

Then restart services:
```bash
launchctl kickstart -k gui/$(id -u)/com.atlas.agent
launchctl kickstart -k gui/$(id -u)/com.atlas.fleetserver
```

### Update Fleet Server URL

```bash
python3 update_fleet_config.py
```

Then restart agent:
```bash
launchctl kickstart -k gui/$(id -u)/com.atlas.agent
```

### View Current Configuration

```bash
python3 show_credentials.py
```

---

## 🐛 Troubleshooting

### Services Not Starting

**Check logs:**
```bash
tail -50 ~/.atlas-fleetserver.error.log
tail -50 ~/.atlas-agent.error.log
```

**Common issues:**
- Python path incorrect in plist
- Port already in use (8767 or 8768)
- Missing dependencies

**Solution:**
```bash
# Reinstall
./install_agent.sh
```

### Menu Bar Icon Not Appearing

**Cause:** LaunchAgent may not have GUI access

**Solution 1:** Check if agent is running
```bash
launchctl list | grep com.atlas.agent
```

**Solution 2:** Restart agent
```bash
launchctl kickstart -k gui/$(id -u)/com.atlas.agent
```

**Solution 3:** Check logs
```bash
tail -f ~/.atlas-agent.log
```

### "401 Unauthorized" Errors

**Cause:** API key mismatch

**Solution:**
```bash
# View current API key
python3 show_credentials.py

# Restart agent to reload config
launchctl kickstart -k gui/$(id -u)/com.atlas.agent
```

### Port Already in Use

**Check what's using the port:**
```bash
lsof -i :8767  # Agent
lsof -i :8768  # Fleet Server
```

**Kill the process:**
```bash
kill -9 <PID>
```

Then restart services.

---

## 🗑️ Uninstallation

### Remove Auto-Start

```bash
# Stop services
launchctl unload ~/Library/LaunchAgents/com.atlas.agent.plist
launchctl unload ~/Library/LaunchAgents/com.atlas.fleetserver.plist

# Remove LaunchAgents
rm ~/Library/LaunchAgents/com.atlas.agent.plist
rm ~/Library/LaunchAgents/com.atlas.fleetserver.plist
```

### Remove Configuration (Optional)

```bash
# Remove encrypted config
rm ~/.fleet-config.json.encrypted

# Remove logs
rm ~/.atlas-agent.log ~/.atlas-agent.error.log
rm ~/.atlas-fleetserver.log ~/.atlas-fleetserver.error.log

# Remove data
rm -rf ~/.fleet-data/
rm -rf ~/.fleet-certs/
```

---

## 📊 File Locations

### Configuration Files
- **Encrypted Config:** `~/.fleet-config.json.encrypted`
- **Fleet Data:** `~/.fleet-data/fleet_data.sqlite3`
- **SSL Certificates:** `~/.fleet-certs/`

### LaunchAgents
- **Agent:** `~/Library/LaunchAgents/com.atlas.agent.plist`
- **Fleet Server:** `~/Library/LaunchAgents/com.atlas.fleetserver.plist`

### Logs
- **Agent Output:** `~/.atlas-agent.log`
- **Agent Errors:** `~/.atlas-agent.error.log`
- **Server Output:** `~/.atlas-fleetserver.log`
- **Server Errors:** `~/.atlas-fleetserver.error.log`

### Project Files
- **Smart Launcher:** `launch_atlas_with_config.py`
- **Credential Manager:** `repair_credentials.py`
- **Config Updater:** `update_fleet_config.py`
- **Config Viewer:** `show_credentials.py`
- **Installer:** `install_agent.sh`

---

## 🎯 Summary

### What You Get

After running `./install_agent.sh`:

1. ✅ **Fleet Server** running on port 8768
2. ✅ **ATLAS Agent** running on port 8767
3. ✅ **Menu bar icon** with live status
4. ✅ **Auto-start on login** (both services)
5. ✅ **Auto-restart on crash**
6. ✅ **Encrypted credential storage**
7. ✅ **Automatic API key management**

### How It Works

- **On Login:** LaunchAgents start both services
- **Agent:** Uses `launch_atlas_with_config.py` to auto-load API key
- **Server:** Loads credentials from encrypted config
- **Menu Bar:** Shows real-time connection status
- **Monitoring:** Agent reports to server every 10 seconds

### Zero Maintenance

Once installed:
- No manual startup needed
- No API keys to remember
- No configuration files to edit
- Just log in and everything works!

---

## 📞 Quick Reference

```bash
# Install (one-time)
./install_agent.sh

# Check status
launchctl list | grep atlas

# View logs
tail -f ~/.atlas-agent.log
tail -f ~/.atlas-fleetserver.log

# Restart
launchctl kickstart -k gui/$(id -u)/com.atlas.agent
launchctl kickstart -k gui/$(id -u)/com.atlas.fleetserver

# Update credentials
python3 repair_credentials.py

# Access dashboards
open https://localhost:8768/dashboard  # Fleet
open http://localhost:8767              # Agent
```

---

**Installation complete! Your ATLAS Fleet monitoring system is now fully automated.** 🎉
