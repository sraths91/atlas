# Quick Deployment Guide for Jamf Pro

## 🚀 Quick Start (5 Minutes)

### Option 1: LaunchAgent Package (Recommended)

**Best for:** Quick deployment, easy updates, no code signing needed

```bash
# 1. Build the package
./build_jamf_package.sh

# 2. Upload to Jamf Pro
# File: Atlas-1.0.0.pkg

# 3. Create policy in Jamf Pro
# - Trigger: Enrollment Complete, Recurring Check-in
# - Package: Atlas-1.0.0.pkg
# - Scope: All Computers (or specific group)
```

**Result:** Dashboard runs automatically on all Macs at http://localhost:8767

---

### Option 2: Native macOS App

**Best for:** Professional deployment, Applications folder

```bash
# 1. Build the app
./build_macos_app.sh

# 2. Upload to Jamf Pro
# File: dist/Atlas-1.0.0.pkg

# 3. Create policy in Jamf Pro
# - Package: Atlas-1.0.0.pkg
# - Install location: /Applications
```

**Result:** App appears in Applications folder

---

## 📋 Jamf Pro Configuration

### 1. Upload Package

1. Log into Jamf Pro
2. **Settings** → **Computer Management** → **Packages**
3. Click **+ New**
4. Upload `Atlas-1.0.0.pkg`
5. Display Name: "Atlas Dashboard"
6. Category: "Monitoring" or "Utilities"

### 2. Create Installation Policy

1. **Computers** → **Policies** → **+ New**
2. **General:**
   - Display Name: "Install Atlas"
   - Enabled: ✓
   - Category: Monitoring
3. **Packages:**
   - Add: Atlas-1.0.0.pkg
   - Action: Install
4. **Maintenance:**
   - Update Inventory: ✓
5. **Scope:**
   - Targets: All Computers (or specific group)
6. **Self Service:**
   - Make Available in Self Service: ✓ (optional)
   - Description: "System monitoring dashboard"

### 3. Set Triggers

- ✓ Recurring Check-in
- ✓ Enrollment Complete
- ✓ Startup (optional)

### 4. Execution Frequency

- Once per computer
- Or: Ongoing (for updates)

---

## 🎯 Testing

### Test on Single Machine

```bash
# 1. Install package manually
sudo installer -pkg Atlas-1.0.0.pkg -target /

# 2. Check if service is running
launchctl list | grep atlas

# 3. Access dashboard
open http://localhost:8767

# 4. Check logs
tail -f /var/log/atlas.log
```

### Verify in Jamf Pro

1. Create test policy scoped to one computer
2. Run `sudo jamf policy` on test machine
3. Verify installation
4. Expand to production

---

## 📊 Monitoring

### Create Extension Attributes

**1. Installation Status**
```bash
#!/bin/bash
if [ -d "/Library/Application Support/Atlas" ]; then
    echo "<result>Installed</result>"
else
    echo "<result>Not Installed</result>"
fi
```

**2. Service Status**
```bash
#!/bin/bash
if launchctl list | grep -q "com.company.atlas"; then
    echo "<result>Running</result>"
else
    echo "<result>Stopped</result>"
fi
```

**3. Dashboard Accessibility**
```bash
#!/bin/bash
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8767 | grep -q "200"; then
    echo "<result>Accessible</result>"
else
    echo "<result>Not Accessible</result>"
fi
```

### Create Smart Groups

1. **Atlas - Installed**
   - Criteria: Extension Attribute "Installation Status" is "Installed"

2. **Atlas - Running**
   - Criteria: Extension Attribute "Service Status" is "Running"

3. **Atlas - Issues**
   - Criteria: Extension Attribute "Dashboard Accessibility" is "Not Accessible"

---

## 🔄 Updates

### Deploy Update

```bash
# 1. Update version in build script
# Edit: VERSION="1.0.1"

# 2. Rebuild package
./build_jamf_package.sh

# 3. Upload new version to Jamf Pro

# 4. Create update policy
# - Scope: Computers with version < 1.0.1
# - Package: Atlas-1.0.1.pkg
```

### Automatic Updates

Add to startup script for git-based updates:
```bash
cd "/Library/Application Support/Atlas"
git pull origin main
pip3 install -r requirements.txt
```

---

## 🗑️ Uninstall

### Create Uninstall Policy

1. **Computers** → **Policies** → **+ New**
2. **Files and Processes:**
   - Execute Command:
   ```bash
   launchctl unload /Library/LaunchAgents/com.company.atlas.plist
   rm -rf "/Library/Application Support/Atlas"
   rm -f /Library/LaunchAgents/com.company.atlas.plist
   rm -f /var/log/atlas.log
   rm -f /var/log/atlas.error.log
   ```

---

## 🔧 Troubleshooting

### Dashboard Not Starting

```bash
# Check if LaunchAgent is loaded
launchctl list | grep atlas

# Load manually
launchctl load /Library/LaunchAgents/com.company.atlas.plist

# Check logs
tail -50 /var/log/atlas.error.log
```

### Port Already in Use

```bash
# Find what's using port 8767
lsof -i :8767

# Kill the process
kill -9 <PID>

# Restart service
launchctl unload /Library/LaunchAgents/com.company.atlas.plist
launchctl load /Library/LaunchAgents/com.company.atlas.plist
```

### Dependencies Missing

```bash
cd "/Library/Application Support/Atlas"
pip3 install -r requirements.txt --force-reinstall
```

---

## 📱 User Experience

### What Users See

**LaunchAgent Method:**
- Nothing visible (runs in background)
- Access via: http://localhost:8767
- Can bookmark in browser

**App Bundle Method:**
- Icon in Applications folder
- Can add to Dock
- Double-click to launch

### User Instructions

Create Self Service description:
```
Atlas Dashboard

A real-time system monitoring dashboard for your Mac.

After installation:
1. Open your web browser
2. Go to: http://localhost:8767
3. Bookmark for easy access

Features:
• CPU, Memory, Disk, Network monitoring
• Speed test and ping monitoring
• WiFi quality tracking
• Export data to CSV

The dashboard runs automatically in the background.
```

---

## 🎨 Customization

### Change Theme

Edit startup script:
```bash
/usr/bin/python3 -m atlas.app --theme ocean --refresh-rate 1.0
```

Available themes:
- `default` - Green
- `cyberpunk` - Pink/Cyan
- `ocean` - Blue
- `sunset` - Orange/Pink
- `forest` - Green
- `monochrome` - Black/White

### Change Port

Edit startup script:
```bash
/usr/bin/python3 -m atlas.app --port 8080
```

### Auto-Open Browser

Add to startup script:
```bash
sleep 5
open http://localhost:8767
```

---

## 📞 Support

### Common Issues

| Issue | Solution |
|-------|----------|
| Dashboard not accessible | Check if service is running: `launchctl list \| grep atlas` |
| Port conflict | Change port in startup script |
| High CPU usage | Increase refresh rate: `--refresh-rate 5.0` |
| Missing widgets | Check logs: `/var/log/atlas.error.log` |

### Logs Location

- **Standard Output:** `/var/log/atlas.log`
- **Errors:** `/var/log/atlas.error.log`
- **Jamf Policy:** `/var/log/jamf.log`

---

## ✅ Checklist

- [ ] Package built successfully
- [ ] Uploaded to Jamf Pro
- [ ] Policy created and scoped
- [ ] Tested on pilot machine
- [ ] Extension attributes created
- [ ] Smart groups configured
- [ ] Self Service description added
- [ ] User documentation provided
- [ ] Monitoring dashboard set up
- [ ] Uninstall policy created

---

## 🚀 Next Steps

1. **Build package:** `./build_jamf_package.sh`
2. **Test locally:** `sudo installer -pkg Atlas-1.0.0.pkg -target /`
3. **Upload to Jamf Pro**
4. **Deploy to pilot group**
5. **Monitor for issues**
6. **Roll out to production**

**Questions?** Check the full deployment guide: `JAMF_DEPLOYMENT.md`
