# 🔧 ATLAS Menu Bar Icon - Troubleshooting Guide

## ❌ Problem: No Icon Appearing in Menu Bar

### **Common Issues & Solutions**

---

## 🎯 Solution 1: Run from Terminal (Recommended for Testing)

The menu bar app **must run in foreground** with GUI access. 

### **Step-by-Step:**

1. **Open Terminal** (Applications → Utilities → Terminal)

2. **Navigate to project:**
   ```bash
   cd /Users/samraths/CascadeProjects/windsurf-project-2
   ```

3. **Run the simple test first:**
   ```bash
   python3 test_menubar.py
   ```

4. **Look for icon in menu bar** (top-right corner, next to WiFi/battery/clock)

5. **If test works**, run the full version:
   ```bash
   python3 start_atlas_agent.py --fleet-server https://localhost:8768
   ```

**Important:** Keep the Terminal window open! If you close it, the icon disappears.

---

## 🎯 Solution 2: Double-Click Launcher (macOS Native)

### **Option A: Using .command file**

1. **In Finder**, navigate to:
   ```
   /Users/samraths/CascadeProjects/windsurf-project-2/
   ```

2. **Double-click:** `launch_atlas_menubar.command`

3. **Grant permissions** if macOS asks

4. **Check menu bar** for icon (top-right corner)

### **Option B: Make it a .app bundle**

For a proper macOS app, we need to create an Application bundle:

```bash
# Create app bundle structure
mkdir -p ATLAS.app/Contents/MacOS
mkdir -p ATLAS.app/Contents/Resources

# Create launcher script
cat > ATLAS.app/Contents/MacOS/ATLAS << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../../.."
exec python3 start_atlas_agent.py --fleet-server https://localhost:8768
EOF

chmod +x ATLAS.app/Contents/MacOS/ATLAS

# Create Info.plist
cat > ATLAS.app/Contents/Info.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>ATLAS</string>
    <key>CFBundleName</key>
    <string>ATLAS Agent</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <string>1</string>
</dict>
</plist>
EOF
```

Then double-click `ATLAS.app` to launch!

---

## 🎯 Solution 3: Check Permissions

macOS might be blocking the app from showing icons.

### **Grant Accessibility Permissions:**

1. Open **System Preferences** → **Security & Privacy**
2. Click **Privacy** tab
3. Select **Accessibility** from left sidebar
4. Click 🔒 lock icon (bottom-left) to unlock
5. Click **+** button
6. Add **Terminal** or **Python**
7. Restart the app

---

## 🎯 Solution 4: Verify rumps Installation

Check if `rumps` is properly installed:

```bash
# Check installation
python3 -c "import rumps; print('✅ rumps installed:', rumps.__version__)"

# If not installed or error:
pip3 install --upgrade rumps

# Verify PyObjC (rumps dependency)
python3 -c "import objc; print('✅ PyObjC installed')"
```

---

## 🎯 Solution 5: Port Conflict Resolution

If the agent port (8767) is already in use:

```bash
# Check what's using port 8767
lsof -i :8767

# Kill existing process
pkill -f "live_widgets"

# Or use a different port
python3 start_atlas_agent.py --port 8888 --fleet-server https://localhost:8768
```

---

## 🎯 Solution 6: Run Menu Bar Only (Agent Already Running)

If your agent is already running separately:

```bash
# Just start the menu bar icon (no agent)
python3 -m atlas.menubar_agent \
  --fleet-server https://localhost:8768 \
  --agent-port 8767
```

---

## 📋 Diagnostic Checklist

Run through this checklist:

```bash
# 1. Check rumps installed
python3 -c "import rumps; print('✅ OK')" || echo "❌ Install: pip3 install rumps"

# 2. Check icons exist
ls -l atlas/menubar_icons/*.png || echo "❌ Run: python3 atlas/create_menubar_icons.py"

# 3. Check port available
lsof -i :8767 || echo "✅ Port available"

# 4. Test simple menu bar
python3 test_menubar.py
```

---

## 🔍 Where to Look for Icon

The menu bar icon appears in the **top-right corner** of your screen:

```
┌─────────────────────────────────────────────────────┐
│  Apple  File  Edit  View  ...        🔋 📶 🔍 🕐 ⏵│
│                                           ↑          │
│                                    Look here!       │
│                                    (next to clock)   │
└─────────────────────────────────────────────────────┘
```

**Icon appearance:**
- Small triangular network symbol (ATLAS logo)
- Colored dots showing status (green/yellow/red)
- About 18-22 pixels in size
- May be slightly transparent/gray if inactive

---

## 🐛 Debug Mode

Run with verbose logging to see what's happening:

```bash
# Enable debug logging
export PYTHONUNBUFFERED=1

# Run with logging
python3 start_atlas_agent.py --fleet-server https://localhost:8768 2>&1 | tee atlas-debug.log

# Check for errors in log
grep -i error atlas-debug.log
grep -i exception atlas-debug.log
```

---

## ⚠️ Known Issues

### **Issue 1: Icon Doesn't Show in Terminal SSH Sessions**

**Problem:** Running from SSH or remote terminal

**Solution:** Must run from local Terminal with GUI access
```bash
# Don't run via SSH
# Run directly on the Mac with GUI
```

### **Issue 2: Python Not Linked to GUI Framework**

**Problem:** Python installed without GUI support

**Solution:** Use system Python or install Python with Tk
```bash
# Use macOS system Python
/usr/bin/python3 start_atlas_agent.py

# Or install Python with GUI support
brew install python-tk@3.9
```

### **Issue 3: macOS Blocking GUI Applications**

**Problem:** Security settings prevent icon from showing

**Solution:** Run from Applications folder or grant permissions
```bash
# Move to Applications
sudo cp -r ATLAS.app /Applications/
open /Applications/ATLAS.app
```

---

## ✅ Expected Behavior

When working correctly:

1. **Terminal shows:**
   ```
   🚀 Starting ATLAS Fleet Agent...
   ✅ ATLAS Agent started!
   Menu bar icon: Check top-right corner of screen
   ```

2. **Menu bar shows:**
   - Small ATLAS triangular icon
   - Colored dots (green/yellow/red)
   - Icon is clickable

3. **Clicking icon shows:**
   - Dropdown menu with options
   - Status message
   - Dashboard links

---

## 🆘 Still Not Working?

### **Quick Test:**

Try this minimal example:

```python
# Create test.py
import rumps

class SimpleApp(rumps.App):
    def __init__(self):
        super().__init__("Test", "🔴")
        
app = SimpleApp()
app.run()
```

```bash
# Run it
python3 test.py
```

If you see a **red circle** in your menu bar, `rumps` is working!

If **nothing appears**:
- You may need to install PyObjC: `pip3 install pyobjc-framework-Cocoa`
- Or reinstall rumps: `pip3 uninstall rumps && pip3 install rumps`
- Or use system Python: `/usr/bin/python3 test.py`

---

## 📱 Alternative: Run Without Menu Bar

If menu bar icon won't work, run agent in background mode:

```bash
# Start agent without menu bar
python3 start_atlas_agent.py --no-menubar

# Access via browser only
open http://localhost:8767
```

---

## 📝 Common Error Messages

### **"Address already in use"**
```bash
pkill -f "live_widgets"
```

### **"No module named 'rumps'"**
```bash
pip3 install rumps
```

### **"Icon file not found"**
```bash
cd atlas
python3 create_menubar_icons.py
```

### **"Cannot import objc"**
```bash
pip3 install pyobjc-framework-Cocoa
```

---

## 🎯 Recommended: Simple Launch Command

**Easiest way to start:**

```bash
cd /Users/samraths/CascadeProjects/windsurf-project-2
python3 test_menubar.py
```

If that works, then:
```bash
python3 start_atlas_agent.py --fleet-server https://localhost:8768
```

**Keep Terminal window open** - if you close it, icon disappears!

---

## 📖 Next Steps

1. **Try the simple test:** `python3 test_menubar.py`
2. **Check menu bar** (top-right corner)
3. **If icon appears** → Success! Run full version
4. **If no icon** → Check permissions and PyObjC
5. **If still issues** → Run without menu bar: `--no-menubar`

---

**The most common issue is running from background/daemon mode. Run from Terminal in foreground!**
