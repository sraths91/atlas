# Deploying Atlas via Jamf Pro

## Overview
This guide explains how to package and deploy the Atlas dashboard as a macOS application through Jamf Pro.

## Deployment Options

### Option 1: LaunchAgent with Python Script (Recommended for Quick Deploy)

**Pros:**
- Simple deployment
- Easy updates
- No code signing required
- Works immediately

**Steps:**

1. **Create deployment package structure:**
```bash
/Library/Application Support/Atlas/
├── atlas/          # Python package
├── requirements.txt
└── start_dashboard.sh         # Startup script
```

2. **Create LaunchAgent plist:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.company.atlas</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Library/Application Support/Atlas/start_dashboard.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/atlas.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/atlas.error.log</string>
</dict>
</plist>
```

3. **Create startup script:**
```bash
#!/bin/bash
cd "/Library/Application Support/Atlas"
/usr/bin/python3 -m atlas.app --theme cyberpunk --refresh-rate 1.0
```

---

### Option 2: Native macOS .app Bundle (Recommended for Production)

**Pros:**
- Professional appearance
- Can be code-signed and notarized
- Shows up in Applications folder
- Better user experience

**Steps:**

1. **Install py2app:**
```bash
pip3 install py2app
```

2. **Create setup.py for py2app:**
```python
from setuptools import setup

APP = ['atlas/app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['atlas'],
    'iconfile': 'icon.icns',  # Optional
    'plist': {
        'CFBundleName': 'Atlas',
        'CFBundleDisplayName': 'Atlas',
        'CFBundleIdentifier': 'com.company.atlas',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': False,  # Set to True to hide from Dock
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
```

3. **Build the app:**
```bash
python3 setup.py py2app
```

This creates: `dist/Atlas.app`

4. **Package for Jamf:**
```bash
# Create PKG installer
pkgbuild --root dist/ \
         --identifier com.company.atlas \
         --version 1.0.0 \
         --install-location /Applications \
         Atlas-1.0.0.pkg
```

---

### Option 3: Docker Container (Advanced)

**Pros:**
- Isolated environment
- Consistent across machines
- Easy dependency management

**Cons:**
- Requires Docker Desktop
- More complex setup

---

## Jamf Pro Deployment Steps

### 1. Create the Package

**For LaunchAgent approach:**
```bash
# Create package structure
mkdir -p payload/Library/Application\ Support/Atlas
mkdir -p payload/Library/LaunchAgents

# Copy files
cp -r atlas payload/Library/Application\ Support/Atlas/
cp requirements.txt payload/Library/Application\ Support/Atlas/
cp start_dashboard.sh payload/Library/Application\ Support/Atlas/
cp com.company.atlas.plist payload/Library/LaunchAgents/

# Set permissions
chmod +x payload/Library/Application\ Support/Atlas/start_dashboard.sh

# Build package
pkgbuild --root payload \
         --identifier com.company.atlas \
         --version 1.0.0 \
         --scripts scripts \
         Atlas-1.0.0.pkg
```

### 2. Create Post-Install Script

Create `scripts/postinstall`:
```bash
#!/bin/bash

# Install Python dependencies
cd "/Library/Application Support/Atlas"
/usr/bin/python3 -m pip install -r requirements.txt

# Set permissions
chmod 755 "/Library/Application Support/Atlas/start_dashboard.sh"
chmod 644 "/Library/LaunchAgents/com.company.atlas.plist"

# Load LaunchAgent for current user
if [ "$USER" != "root" ]; then
    launchctl load /Library/LaunchAgents/com.company.atlas.plist
fi

exit 0
```

### 3. Upload to Jamf Pro

1. Log into Jamf Pro
2. Go to **Settings** → **Computer Management** → **Packages**
3. Click **+ New**
4. Upload `Atlas-1.0.0.pkg`
5. Set display name: "Atlas Dashboard"
6. Set category (e.g., "Monitoring Tools")

### 4. Create Policy

1. Go to **Computers** → **Policies**
2. Click **+ New**
3. Configure:
   - **Display Name:** Install Atlas
   - **Trigger:** Recurring Check-in, Enrollment Complete
   - **Execution Frequency:** Once per computer
   - **Packages:** Add Atlas-1.0.0.pkg
   - **Scope:** Select target computers/groups

### 5. Create Self Service Policy (Optional)

For user-initiated installation:
1. Enable **Self Service**
2. Add description and icon
3. Set **Make Available in Self Service**
4. Users can install from Self Service app

---

## Configuration Management

### Using Jamf Pro Configuration Profiles

Create a configuration profile to manage settings:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>PayloadType</key>
            <string>com.company.atlas</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>PayloadIdentifier</key>
            <string>com.company.atlas.settings</string>
            <key>theme</key>
            <string>cyberpunk</string>
            <key>refresh_rate</key>
            <real>1.0</real>
            <key>port</key>
            <integer>8767</integer>
            <key>auto_start_browser</key>
            <true/>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>Atlas Settings</string>
    <key>PayloadIdentifier</key>
    <string>com.company.atlas.profile</string>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>GENERATE-UUID-HERE</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>
```

---

## Monitoring & Maintenance

### Extension Attributes

Create Jamf extension attributes to monitor:

**1. Check if service is running:**
```bash
#!/bin/bash
if launchctl list | grep -q "com.company.atlas"; then
    echo "<result>Running</result>"
else
    echo "<result>Not Running</result>"
fi
```

**2. Check version:**
```bash
#!/bin/bash
VERSION=$(defaults read "/Library/Application Support/Atlas/version.plist" CFBundleShortVersionString 2>/dev/null)
echo "<result>${VERSION:-Not Installed}</result>"
```

**3. Check dashboard accessibility:**
```bash
#!/bin/bash
if curl -s http://localhost:8767 > /dev/null; then
    echo "<result>Accessible</result>"
else
    echo "<result>Not Accessible</result>"
fi
```

### Smart Groups

Create smart groups based on extension attributes:
- **Atlas - Installed**
- **Atlas - Running**
- **Atlas - Needs Update**

---

## Updates

### Rolling Out Updates

1. Build new package with incremented version
2. Upload to Jamf Pro
3. Create update policy:
   - Trigger: Recurring check-in
   - Scope: Computers with older version
   - Execution: Once per computer per version

### Automatic Updates via Git

Add to startup script:
```bash
#!/bin/bash
cd "/Library/Application Support/Atlas"

# Pull latest changes
git pull origin main

# Install dependencies
/usr/bin/python3 -m pip install -r requirements.txt

# Start application
/usr/bin/python3 -m atlas.app --theme cyberpunk --refresh-rate 1.0
```

---

## Security Considerations

### 1. Code Signing (Recommended for Production)

```bash
# Sign the application
codesign --force --deep --sign "Developer ID Application: Your Name" \
         "Atlas.app"

# Verify signature
codesign --verify --verbose "Atlas.app"
```

### 2. Notarization (Required for macOS 10.15+)

```bash
# Create DMG
hdiutil create -volname "Atlas" \
               -srcfolder "Atlas.app" \
               -ov -format UDZO \
               Atlas.dmg

# Notarize
xcrun notarytool submit Atlas.dmg \
                        --apple-id "your@email.com" \
                        --team-id "TEAMID" \
                        --password "app-specific-password" \
                        --wait

# Staple notarization
xcrun stapler staple Atlas.dmg
```

### 3. Restrict Network Access

Use Jamf Pro to configure firewall rules allowing only localhost access.

---

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
tail -f /var/log/atlas.log
tail -f /var/log/atlas.error.log

# Manually load LaunchAgent
launchctl load -w /Library/LaunchAgents/com.company.atlas.plist
```

**Port already in use:**
```bash
# Find process using port 8767
lsof -i :8767

# Kill process
kill -9 <PID>
```

**Dependencies missing:**
```bash
# Reinstall dependencies
cd "/Library/Application Support/Atlas"
/usr/bin/python3 -m pip install -r requirements.txt --force-reinstall
```

---

## Best Practices

1. **Version Control:** Use semantic versioning (1.0.0, 1.0.1, etc.)
2. **Testing:** Test on multiple macOS versions before deployment
3. **Staged Rollout:** Deploy to pilot group first
4. **Monitoring:** Set up extension attributes and smart groups
5. **Documentation:** Provide user guide in Self Service description
6. **Uninstall Script:** Create uninstall policy for easy removal

---

## Quick Start Script

I'll create a deployment script that automates this process...
