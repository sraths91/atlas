# Fleet Agent - USB Deployment Guide

## 📦 Deploy Fleet Agent via USB Drive

Perfect for deploying to Macs without network access or when you want a simple drag-and-drop installation.

---

## 🎯 Quick Steps

### 1. Prepare USB Drive

```bash
# Build the package (if not already built)
cd fleet-agent
./build_macos_pkg.sh

# Copy package to USB drive
cp dist/FleetAgent.pkg /Volumes/YOUR_USB_DRIVE/
```

Or manually:
1. Build package: Run `build_macos_pkg.sh`
2. Find: `fleet-agent/dist/FleetAgent.pkg` (848KB)
3. Copy to USB drive

### 2. Install on Target Mac

**On the target Mac:**

1. **Insert USB drive**

2. **Open the USB drive** in Finder

3. **Drag `FleetAgent.pkg` to Desktop** (or any folder)

4. **Double-click `FleetAgent.pkg`**

5. **Follow the installer** (standard macOS installer)
   - Click "Continue"
   - Click "Install"
   - Enter admin password when prompted
   - Installation completes!

6. **Configure the Agent:**
   - Open **Applications** folder
   - Double-click **Fleet Agent Configuration**
   - Enter your fleet server URL (e.g., `http://192.168.1.100:8768`)
   - Enter API key (if required)
   - Click **Configure**

**Done!** The Mac will immediately start reporting to your fleet server.

---

## 🖥️ Visual Guide

### Installation Process

```
USB Drive
   └── FleetAgent.pkg (848KB)
        │
        ├─ Drag to Desktop
        │
        └─ Double-click
             │
             └─ macOS Installer Opens
                  │
                  ├─ Welcome Screen
                  ├─ Installation Type
                  ├─ Install (requires password)
                  └─ Conclusion Screen
                       │
                       └─ Opens Applications Folder
                            │
                            └─ Double-click "Fleet Agent Configuration"
                                 │
                                 ├─ Enter Server URL
                                 ├─ Enter API Key
                                 └─ Click "Configure"
                                      │
                                      └─ ✅ Agent Running!
```

---

## 📋 What Gets Installed

After installation:

```
/Applications/
└── Fleet Agent Configuration.app    ← GUI configuration tool

/usr/local/bin/
└── fleet-agent                       ← Agent executable

/Library/Application Support/FleetAgent/
└── config.json                       ← Configuration file

/Library/LaunchDaemons/
└── com.fleet.agent.plist            ← Auto-start service

/Library/Python/3.9/lib/python/site-packages/
├── fleet_agent/                      ← Agent code
├── psutil/                           ← Dependencies
├── requests/
└── urllib3/

/var/log/
├── fleet-agent.log                   ← Normal logs
└── fleet-agent.error.log            ← Error logs
```

---

## 🔧 Configuration Methods

### Method 1: GUI Configuration App (Recommended)

1. Go to **Applications** folder
2. Double-click **Fleet Agent Configuration**
3. Enter server details
4. Click **Configure**

**Easiest method!** No command-line needed.

### Method 2: Manual Configuration (Advanced)

```bash
# Edit config file
sudo nano /Library/Application\ Support/FleetAgent/config.json

# Update these values:
{
    "server_url": "http://your-server:8768",
    "api_key": "your-api-key",
    "interval": 10
}

# Start service
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

---

## 💾 Deploying to Multiple Macs

### Option 1: Same Configuration for All Macs

**Pre-configure before deployment:**

1. Build package: `./build_macos_pkg.sh`
2. Mount the package and modify config template
3. Rebuild with your settings
4. Copy to USB
5. Deploy to all Macs

### Option 2: Individual Configuration per Mac

1. Copy `FleetAgent.pkg` to USB
2. Install on each Mac
3. Run Configuration app on each Mac
4. Enter appropriate settings

### Option 3: Batch Install Script

Create `install_fleet_agent.sh` on USB:

```bash
#!/bin/bash
# Install Fleet Agent from USB

USB_PATH="/Volumes/USB_DRIVE_NAME"
PKG="$USB_PATH/FleetAgent.pkg"

echo "Installing Fleet Agent..."
sudo installer -pkg "$PKG" -target /

echo "Opening configuration app..."
open "/Applications/Fleet Agent Configuration.app"
```

Make executable:
```bash
chmod +x install_fleet_agent.sh
```

On each Mac, run:
```bash
./install_fleet_agent.sh
```

---

## ✅ Verification

### Check Installation

```bash
# Check if agent is installed
ls -l /usr/local/bin/fleet-agent

# Check if config app is installed
ls -la /Applications/ | grep Fleet

# Check LaunchDaemon
ls -l /Library/LaunchDaemons/com.fleet.agent.plist
```

### Check if Agent is Running

```bash
# Check service status
sudo launchctl list | grep com.fleet.agent

# View logs
tail -f /var/log/fleet-agent.log

# Check on dashboard
# Open: http://your-server:8768/dashboard
```

---

## 🔄 Reconfiguration

If you need to change settings:

1. **Open Configuration App** again
   - Go to Applications
   - Double-click "Fleet Agent Configuration"
   - Enter new settings

2. **Or edit manually:**
   ```bash
   sudo nano /Library/Application\ Support/FleetAgent/config.json
   sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
   sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
   ```

---

## 🗑️ Uninstallation

**Via Configuration App (coming soon)** or manually:

```bash
# Stop service
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist

# Remove files
sudo rm -rf /Library/LaunchDaemons/com.fleet.agent.plist
sudo rm -rf /Library/Application\ Support/FleetAgent
sudo rm -f /usr/local/bin/fleet-agent
sudo rm -rf /Applications/Fleet\ Agent\ Configuration.app
sudo rm -f /var/log/fleet-agent*.log

echo "Fleet Agent uninstalled"
```

---

## 🚨 Troubleshooting

### "Cannot Open Package - Unidentified Developer"

**If you see this error:**

1. **Right-click** on FleetAgent.pkg
2. Select **Open**
3. Click **Open** in the dialog
4. Proceed with installation

Or disable Gatekeeper temporarily:
```bash
sudo spctl --master-disable
# Install package
sudo spctl --master-enable
```

### Service Not Starting After Configuration

1. **Check logs:**
   ```bash
   tail -f /var/log/fleet-agent.error.log
   ```

2. **Verify configuration:**
   ```bash
   cat /Library/Application\ Support/FleetAgent/config.json
   ```

3. **Test connectivity:**
   ```bash
   curl http://your-server:8768/api/fleet/summary
   ```

4. **Reload service:**
   ```bash
   sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
   sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
   ```

### Configuration App Won't Open

**If the app won't open:**

1. Check permissions:
   ```bash
   ls -la /Applications/ | grep Fleet
   ```

2. Try opening from Terminal:
   ```bash
   open "/Applications/Fleet Agent Configuration.app"
   ```

3. Remove quarantine attribute:
   ```bash
   sudo xattr -dr com.apple.quarantine "/Applications/Fleet Agent Configuration.app"
   ```

---

## 💡 Pro Tips

1. **Label your USB drive** clearly (e.g., "Fleet Agent Installer")

2. **Include a README** on the USB with your server URL

3. **Test on one Mac first** before deploying to all

4. **Keep a backup** of FleetAgent.pkg on your server

5. **Version your packages** if you make changes:
   ```bash
   cp FleetAgent.pkg FleetAgent-v1.0.0.pkg
   ```

6. **Pre-configure for common scenarios:**
   - Development environment package
   - Production environment package
   - Different packages per location

---

## 📊 Deployment Workflow

### For Small Office (5-20 Macs)

```
1. Build package once
2. Copy to USB drive
3. Visit each Mac
4. Double-click install
5. Configure via GUI app
6. Verify on dashboard
```

### For Medium Deployment (20-100 Macs)

```
1. Build package
2. Copy to multiple USB drives
3. Distribute to IT staff
4. Each staff member deploys
5. Central monitoring via dashboard
```

---

## 🎓 Example Deployment

**Scenario:** Deploy to 10 office Macs

**Steps:**

1. **Prepare** (5 minutes)
   ```bash
   cd fleet-agent
   ./build_macos_pkg.sh
   cp dist/FleetAgent.pkg /Volumes/USB_DRIVE/
   ```

2. **Deploy to each Mac** (2 minutes per Mac)
   - Insert USB
   - Copy FleetAgent.pkg to Desktop
   - Double-click to install
   - Enter admin password
   - Open Configuration app
   - Enter server URL: `http://192.168.1.100:8768`
   - Enter API key: `your-key`
   - Click Configure

3. **Verify** (1 minute per Mac)
   - Open dashboard: `http://192.168.1.100:8768/dashboard`
   - Confirm Mac appears
   - Check metrics updating

**Total time:** ~5 + (2×10) + (1×10) = **35 minutes** for 10 Macs!

---

## 📞 Support

**USB Deployment Issues:**
- Ensure USB drive is formatted (Mac OS Extended or APFS)
- Package file should be 848KB
- No special permissions needed on USB drive

**Installation Issues:**
- Requires macOS 10.13 or later
- Requires admin password
- About 10MB disk space needed

**Configuration Issues:**
- Server must be accessible from Mac
- Test connectivity: `curl http://server:8768/api/fleet/summary`
- Check firewall allows port 8768

---

## ✅ Summary

**USB Deployment is:**
- ✅ Simple (drag and drop)
- ✅ Fast (2-3 minutes per Mac)
- ✅ No network required during install
- ✅ GUI configuration (no command-line)
- ✅ Professional installer experience
- ✅ Works on any Mac (Intel or Apple Silicon)

**Perfect for:**
- Field deployments
- Offline installations
- Quick deployments
- Non-technical users

**Your deployment is ready to go! 🚀**
