# 🚀 ATLAS Agent Auto-Start Configuration Guide

## Overview

This guide shows you how to ensure the ATLAS agent **always starts with the correct API key** and launches automatically on system startup.

---

## 🔐 How It Works

The system uses **encrypted configuration** to store credentials securely:

1. **Encrypted Config File:** `~/.fleet-config.json.encrypted`
   - Stores API key, Fleet Server URL, and web credentials
   - Encrypted using machine-specific key
   - Cannot be decrypted on other machines

2. **Smart Launcher:** `launch_atlas_with_config.py`
   - Automatically loads API key from encrypted config
   - No need to manually pass credentials
   - One command to start everything correctly

3. **Auto-Start:** LaunchAgent (`com.atlas.agent.plist`)
   - Starts agent automatically on login
   - Restarts if it crashes
   - Runs in background with menu bar icon

---

## 📋 Initial Setup (One-Time)

### Step 1: Set Credentials

If you haven't already, set your credentials:

```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
python3 repair_credentials.py
```

**This creates:**
- ✅ Web username/password for dashboard login
- ✅ API key for agent-to-server communication
- ✅ Encrypted config file at `~/.fleet-config.json.encrypted`

---

### Step 2: Configure Fleet Server URL

Update the config with your Fleet Server URL:

```bash
python3 update_fleet_config.py
```

**Enter the URL when prompted** (or press Enter to use default: `https://localhost:8768`)

---

### Step 3: Test Manual Launch

Test that the smart launcher works:

```bash
python3 launch_atlas_with_config.py
```

**Expected output:**
```
======================================================================
ATLAS AGENT LAUNCHER
======================================================================

✅ Configuration loaded successfully

Fleet Server:  https://localhost:8768
Machine ID:    sams-Air
API Key:       UwAQCK3W4-l4ser_RPd-...

======================================================================

[Agent starts with menu bar icon...]
```

**If successful**, you should see:
- ✅ Menu bar icon appears (top-right corner)
- ✅ Agent dashboard accessible at http://localhost:8767
- ✅ Machine shows as "online" on Fleet Server

Press `Ctrl+C` to stop, then proceed to auto-start setup.

---

### Step 4: Install Auto-Start

Install the LaunchAgent for automatic startup:

```bash
./setup_auto_start.sh
```

**This will:**
- ✅ Install LaunchAgent to `~/Library/LaunchAgents/`
- ✅ Start the agent immediately
- ✅ Configure auto-start on every login

---

## ✅ Verification

### Check Agent is Running

```bash
launchctl list | grep atlas
```

**Expected output:**
```
-	0	com.atlas.agent
```

### View Logs

```bash
# Standard output
tail -f ~/.atlas-agent.log

# Errors (if any)
tail -f ~/.atlas-agent.error.log
```

### Check Dashboard

Open browser:
- **Agent Dashboard:** http://localhost:8767
- **Fleet Dashboard:** https://localhost:8768/dashboard

---

## 🎯 Daily Use

### Normal Operation

**Nothing to do!** The agent starts automatically when you log in.

**Menu bar icon shows status:**
- 🟢 Green dot = Connected & reporting
- 🟡 Yellow dot = Running but disconnected
- 🔴 Red dot = Error or offline

### Manual Control

```bash
# Stop agent
launchctl unload ~/Library/LaunchAgents/com.atlas.agent.plist

# Start agent
launchctl load ~/Library/LaunchAgents/com.atlas.agent.plist

# Restart agent
launchctl kickstart -k gui/$(id -u)/com.atlas.agent

# Check status
launchctl list | grep atlas
```

---

## 🔧 Managing Configuration

### Update Fleet Server URL

```bash
python3 update_fleet_config.py
```

**After changing URL, restart the agent:**
```bash
launchctl kickstart -k gui/$(id -u)/com.atlas.agent
```

### Change Web Credentials

```bash
python3 repair_credentials.py
```

**Then restart the Fleet Server** to load new credentials.

### View Current Config

```bash
python3 show_credentials.py
```

**Shows:**
- Dashboard URL
- Web username/password
- API key (truncated for security)

---

## 📂 Important Files

### Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| **Encrypted Config** | `~/.fleet-config.json.encrypted` | Stores all credentials |
| **LaunchAgent** | `~/Library/LaunchAgents/com.atlas.agent.plist` | Auto-start configuration |
| **Agent Logs** | `~/.atlas-agent.log` | Standard output |
| **Error Logs** | `~/.atlas-agent.error.log` | Error messages |

### Project Files

| File | Purpose |
|------|---------|
| `launch_atlas_with_config.py` | Smart launcher (loads config automatically) |
| `repair_credentials.py` | Set/reset web & API credentials |
| `update_fleet_config.py` | Update Fleet Server URL |
| `show_credentials.py` | View current credentials |
| `setup_auto_start.sh` | Install auto-start LaunchAgent |

---

## 🐛 Troubleshooting

### Agent Not Starting

**Check if LaunchAgent is loaded:**
```bash
launchctl list | grep atlas
```

**If not found, load it:**
```bash
launchctl load ~/Library/LaunchAgents/com.atlas.agent.plist
```

**Check logs for errors:**
```bash
tail -50 ~/.atlas-agent.error.log
```

---

### "401 Unauthorized" Errors

**Problem:** API key mismatch between agent and server

**Solution:**
1. Get API key from config:
   ```bash
   python3 show_credentials.py
   ```

2. Restart agent to use correct key:
   ```bash
   launchctl kickstart -k gui/$(id -u)/com.atlas.agent
   ```

---

### Machine Shows Offline

**Problem:** Agent not reporting to server

**Check logs:**
```bash
tail -f ~/.atlas-agent.log
```

**Look for:**
- ✅ `Fleet agent started`
- ✅ `POST /api/fleet/report HTTP/1.1" 200` (every 10 seconds)

**If seeing 401 errors:**
```bash
# Verify API keys match
python3 show_credentials.py
launchctl kickstart -k gui/$(id -u)/com.atlas.agent
```

---

### Config Decryption Fails

**Problem:** Encrypted config can't be read

**Possible causes:**
1. Config file corrupted
2. System changed (different Mac)
3. Keychain issues

**Solution:** Recreate config:
```bash
# Backup old config
mv ~/.fleet-config.json.encrypted ~/.fleet-config.json.encrypted.bak

# Create new config
python3 repair_credentials.py
python3 update_fleet_config.py

# Restart agent
launchctl kickstart -k gui/$(id -u)/com.atlas.agent
```

---

### Menu Bar Icon Not Appearing

**Problem:** Agent running but icon not visible

**Cause:** LaunchAgent doesn't have GUI access

**Solution:** Use Login Items instead:

1. Open **System Preferences** → **Users & Groups** → **Login Items**
2. Click **+** button
3. Navigate to: `/Users/samraths/CascadeProjects/windsurf-project-2/`
4. Add: `launch_atlas_menubar.command`

---

## 🔄 Uninstall Auto-Start

If you want to remove auto-start:

```bash
# Stop and unload agent
launchctl unload ~/Library/LaunchAgents/com.atlas.agent.plist

# Remove LaunchAgent
rm ~/Library/LaunchAgents/com.atlas.agent.plist

# Optional: Remove config
rm ~/.fleet-config.json.encrypted

# Optional: Remove logs
rm ~/.atlas-agent.log ~/.atlas-agent.error.log
```

---

## 🎯 Summary

### What Ensures Proper Launch Every Time

1. **✅ Encrypted Config Storage**
   - API key stored securely in `~/.fleet-config.json.encrypted`
   - Machine-specific encryption prevents copying to other systems
   - Same config used by both agent and server

2. **✅ Smart Launcher Script**
   - Automatically loads API key from config
   - No manual credential management needed
   - Validates config before starting

3. **✅ LaunchAgent Auto-Start**
   - Starts on every login
   - Restarts if crashes
   - Runs with correct environment

4. **✅ Centralized Credential Management**
   - One script to update credentials: `repair_credentials.py`
   - Changes propagate automatically
   - No hardcoded passwords anywhere

---

## 📞 Quick Reference

### Common Commands

```bash
# Start agent manually
python3 launch_atlas_with_config.py

# Update credentials
python3 repair_credentials.py

# Update Fleet Server URL
python3 update_fleet_config.py

# View current config
python3 show_credentials.py

# Restart auto-started agent
launchctl kickstart -k gui/$(id -u)/com.atlas.agent

# View logs
tail -f ~/.atlas-agent.log

# Check if running
launchctl list | grep atlas
```

---

## ✨ Best Practices

1. **Always use the launcher scripts** - Don't start the agent manually with hardcoded credentials
2. **Keep config encrypted** - Never store plaintext passwords
3. **Monitor logs** - Check `~/.atlas-agent.log` if issues occur
4. **Update config centrally** - Use `update_fleet_config.py` and `repair_credentials.py`
5. **Test after updates** - Restart agent after changing configuration

---

**Your ATLAS agent is now configured to start automatically with the correct API key every time!** 🎉
