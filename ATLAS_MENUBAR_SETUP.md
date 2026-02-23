# 🎯 ATLAS Menu Bar Agent - Setup & Usage Guide

## ✨ Overview

Your ATLAS Fleet Agent now has a **professional menu bar icon** that displays in the top-right corner of your Mac, just like system icons!

**Features:**
- 🎨 **ATLAS Logo Icon** - Based on your ATLAS branding
- 🟢 **Status Indicators** - Green/Yellow/Red dots show connection status
- 📊 **Live Monitoring** - Updates every 5 seconds
- 🖱️ **Quick Actions** - Click icon for dashboard access, reconnect, quit
- 🌗 **Dark Mode Ready** - Automatically adapts to macOS appearance

---

## 🎨 Icon Design

Based on your **ATLAS logo**, the menu bar icon features:

```
     ╱╲        Triangular network icon
    ╱  ╲       with connected nodes
   ╱ ●  ╲      Status shown via colored dots:
  ╱      ●     🟢 Green = Connected & Running
 ╱________╲    🟡 Yellow = Running but disconnected
●          ●   🔴 Red = Error or not running
```

**Color Scheme:**
- **Dark Slate Blue** (#2C4B5C) - Main structure
- **Teal Green** (#5FB59D) - Connected status
- **Yellow** (#FFAA00) - Warning status  
- **Red** (#FF4444) - Error status

---

## 📦 Installation

### **Step 1: Install Dependencies**

```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2

# Install rumps (macOS menu bar framework)
pip3 install rumps

# Install Pillow (for icon generation, if not already installed)
pip3 install Pillow
```

### **Step 2: Verify Icon Files**

Icons are already created in:
```
atlas/menubar_icons/
├── atlas_connected@1x.png      (green dots)
├── atlas_connected@2x.png      (green dots, Retina)
├── atlas_connected@3x.png      (green dots, high-res)
├── atlas_warning@1x.png        (yellow dots)
├── atlas_warning@2x.png        (yellow dots, Retina)
├── atlas_warning@3x.png        (yellow dots, high-res)
├── atlas_error@1x.png          (red dots)
├── atlas_error@2x.png          (red dots, Retina)
├── atlas_error@3x.png          (red dots, high-res)
├── atlas_disconnected@1x.png   (gray dots)
├── atlas_disconnected@2x.png   (gray dots, Retina)
└── atlas_disconnected@3x.png   (gray dots, high-res)
```

---

## 🚀 Usage

### **Option 1: Start with Menu Bar Icon (Recommended)**

```bash
# Basic usage
python3 start_atlas_agent.py

# With Fleet Server
python3 start_atlas_agent.py \
  --fleet-server https://localhost:8768 \
  --machine-id $(hostname -s)

# With custom port
python3 start_atlas_agent.py \
  --port 8767 \
  --fleet-server https://localhost:8768 \
  --machine-id my-mac
```

**What happens:**
1. ✅ Agent starts on port 8767
2. ✅ Menu bar icon appears (top-right corner)
3. ✅ Icon shows green dots when connected
4. ✅ Click icon to access menu

---

### **Option 2: Start Without Menu Bar (Background Mode)**

```bash
# Run without menu bar icon
python3 start_atlas_agent.py --no-menubar

# Or use the original command
python3 -m atlas.live_widgets \
  --port 8767 \
  --fleet-server https://localhost:8768
```

---

### **Option 3: Menu Bar Only (Agent Already Running)**

```bash
# If agent is already running, start just the menu bar
python3 -m atlas.menubar_agent \
  --fleet-server https://localhost:8768 \
  --agent-port 8767
```

---

## 🖱️ Menu Bar Features

### **Click the Icon to Access:**

```
┌─────────────────────────────────┐
│ Status: ✅ Running & Connected  │
├─────────────────────────────────┤
│ Open Dashboard                  │
│ Open Fleet Dashboard            │
├─────────────────────────────────┤
│ Reconnect                       │
├─────────────────────────────────┤
│ Quit ATLAS Agent                │
└─────────────────────────────────┘
```

### **Menu Options:**

1. **Status** - Shows current connection state
2. **Open Dashboard** - Opens http://localhost:8767 in browser
3. **Open Fleet Dashboard** - Opens Fleet Server dashboard
4. **Reconnect** - Force reconnection check
5. **Quit ATLAS Agent** - Close menu bar app (agent keeps running)

---

## 🎨 Status Indicators

### **🟢 Green Dots - Connected & Healthy**
```
Status: ✅ Running & Connected
```
- ✅ Agent running on localhost:8767
- ✅ Connected to Fleet Server
- ✅ All systems operational

---

### **🟡 Yellow Dots - Warning**
```
Status: ⚠️ Running (Disconnected from Fleet)
```
- ✅ Agent running locally
- ❌ Cannot reach Fleet Server
- ⚠️ Check network or Fleet Server status

---

### **🔴 Red Dots - Error**
```
Status: ❌ Agent Not Running
```
- ❌ Agent not responding on port 8767
- ❌ Service may have crashed
- 🔧 Restart required

---

### **⚪ Gray Dots - Disconnected**
```
Status: ⚪ Disconnected
```
- Agent initializing or stopped
- No Fleet Server configured

---

## 🔄 Auto-Start on Login

### **Option 1: LaunchAgent (Recommended)**

Create a LaunchAgent to start the menu bar app on login:

```bash
# Create LaunchAgent plist
cat > ~/Library/LaunchAgents/com.atlas.menubar.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlas.menubar</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/samraths/CascadeProjects/windsurf-project-2/start_atlas_agent.py</string>
        <string>--fleet-server</string>
        <string>https://localhost:8768</string>
        <string>--machine-id</string>
        <string>YOUR_MACHINE_ID</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/tmp/atlas-menubar.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/atlas-menubar-error.log</string>
</dict>
</plist>
EOF

# Load the LaunchAgent
launchctl load ~/Library/LaunchAgents/com.atlas.menubar.plist
```

**Uninstall:**
```bash
launchctl unload ~/Library/LaunchAgents/com.atlas.menubar.plist
rm ~/Library/LaunchAgents/com.atlas.menubar.plist
```

---

### **Option 2: Login Items (System Preferences)**

1. Open **System Preferences** → **Users & Groups**
2. Click **Login Items** tab
3. Click **+** button
4. Navigate to and select `start_atlas_agent.py`
5. Check **Hide** to minimize window on startup

---

## 🧪 Testing

### **Test 1: Verify Icons Created**

```bash
ls -lh atlas/menubar_icons/
```

Expected: 12 PNG files (3 sizes × 4 status types)

---

### **Test 2: Start Menu Bar App**

```bash
python3 start_atlas_agent.py
```

Expected:
- ✅ Console shows "Starting ATLAS Fleet Agent..."
- ✅ Icon appears in menu bar (top-right)
- ✅ Icon shows green dots (if agent healthy)

---

### **Test 3: Click Icon**

Click the ATLAS icon in menu bar

Expected:
- ✅ Dropdown menu appears
- ✅ Status shows current state
- ✅ Menu options are clickable

---

### **Test 4: Open Dashboard**

Click **Open Dashboard** from menu

Expected:
- ✅ Browser opens to http://localhost:8767
- ✅ Dashboard loads successfully

---

## 🔧 Troubleshooting

### **Icon Not Appearing**

**Problem:** No icon in menu bar

**Solutions:**
```bash
# 1. Check if rumps is installed
pip3 list | grep rumps

# 2. Install rumps if missing
pip3 install rumps

# 3. Verify icon files exist
ls atlas/menubar_icons/

# 4. Check logs for errors
tail -f /tmp/atlas-menubar.log
```

---

### **Icon Shows Red Dots**

**Problem:** Icon appears but shows red dots

**Solutions:**
```bash
# 1. Check if agent is running
curl http://localhost:8767/api/agent/health

# 2. Start agent if not running
python3 -m atlas.live_widgets --port 8767

# 3. Check agent logs
# Look for startup errors
```

---

### **Icon Shows Yellow Dots**

**Problem:** Icon shows yellow dots (agent running but disconnected)

**Solutions:**
```bash
# 1. Check Fleet Server is running
curl -k https://localhost:8768/api/fleet/machines

# 2. Start Fleet Server if needed
python3 -m atlas.fleet_server --config config.json

# 3. Verify Fleet Server URL is correct
# Click icon → Check status message
```

---

### **Menu Bar App Crashes**

**Problem:** App starts then immediately quits

**Solutions:**
```bash
# 1. Check error logs
tail -f /tmp/atlas-menubar-error.log

# 2. Run with verbose output
python3 start_atlas_agent.py --no-menubar
# (Test agent without menu bar)

# 3. Verify all dependencies
pip3 install --upgrade rumps Pillow requests
```

---

## 📝 Command Reference

### **Start Commands:**

```bash
# Full featured (agent + menu bar + fleet)
python3 start_atlas_agent.py \
  --fleet-server https://localhost:8768 \
  --machine-id $(hostname -s)

# Agent only (no menu bar)
python3 start_atlas_agent.py --no-menubar

# Custom port
python3 start_atlas_agent.py --port 8888

# With API key authentication
python3 start_atlas_agent.py \
  --fleet-server https://server:8768 \
  --api-key YOUR_API_KEY \
  --machine-id my-mac
```

### **Icon Generation:**

```bash
# Regenerate icons (if needed)
cd atlas
python3 create_menubar_icons.py
```

---

## 🎯 Integration with Existing Setup

### **If Using LaunchDaemon (from previous setup):**

You now have **two options**:

**Option A: Replace with Menu Bar Version**
```bash
# 1. Uninstall old LaunchDaemon
sudo launchctl unload /Library/LaunchDaemons/com.atlas.agent.plist
sudo rm /Library/LaunchDaemons/com.atlas.agent.plist

# 2. Install new LaunchAgent with menu bar
cp ~/Library/LaunchAgents/com.atlas.menubar.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.atlas.menubar.plist
```

**Option B: Keep Both (Agent in background + Menu Bar)**
```bash
# Keep LaunchDaemon for agent
# Add LaunchAgent for menu bar only
python3 -m atlas.menubar_agent \
  --fleet-server https://localhost:8768 \
  --agent-port 8767
```

---

## 📊 File Structure

```
windsurf-project-2/
├── start_atlas_agent.py              # Main launcher
├── atlas/
│   ├── menubar_agent.py              # Menu bar app
│   ├── create_menubar_icons.py       # Icon generator
│   ├── menubar_icons/                # Icon assets
│   │   ├── atlas_connected@2x.png   # Green (connected)
│   │   ├── atlas_warning@2x.png     # Yellow (warning)
│   │   ├── atlas_error@2x.png       # Red (error)
│   │   └── atlas_disconnected@2x.png # Gray (disconnected)
│   └── live_widgets.py               # Agent server
└── ATLAS_MENUBAR_SETUP.md            # This file
```

---

## ✅ Summary

**What You Got:**

✅ **Professional Menu Bar Icon** - ATLAS logo in menu bar  
✅ **Live Status Indicators** - Green/Yellow/Red dots  
✅ **Quick Access Menu** - Dashboard, reconnect, quit  
✅ **Auto Dark Mode** - Adapts to macOS appearance  
✅ **Easy Integration** - Works with existing agent  
✅ **Auto-Start Support** - LaunchAgent for login  

**Status Indicators:**
- 🟢 **Green** - Connected & Running
- 🟡 **Yellow** - Running but Disconnected  
- 🔴 **Red** - Error or Not Running
- ⚪ **Gray** - Disconnected

**Quick Start:**
```bash
# Install
pip3 install rumps

# Run
python3 start_atlas_agent.py --fleet-server https://localhost:8768

# Look for icon in top-right corner of screen!
```

---

**Your ATLAS agent now has a beautiful, professional menu bar presence!** 🎉✨
