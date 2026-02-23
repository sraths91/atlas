# Pre-Configured Package Deployment

## 🎯 Overview

You can now build Fleet Agent packages with **server URL and API key baked in**! This means:

✅ Users just double-click to install  
✅ **No configuration needed** after installation  
✅ Agent starts automatically and immediately  
✅ Perfect for mass deployment  

---

## 🚀 Building Pre-Configured Packages

### Quick Example

```bash
cd fleet-agent

# Build with your server settings embedded
./build_macos_pkg.sh \
    --server-url "http://192.168.1.100:8768" \
    --api-key "your-secret-api-key"
```

That's it! The package now contains your settings.

### Full Options

```bash
./build_macos_pkg.sh \
    --server-url "http://your-server:8768" \
    --api-key "your-secret-key" \
    --interval 10
```

**Parameters:**
- `--server-url` - Your fleet server URL (required for pre-config)
- `--api-key` - Your API key (optional but recommended)
- `--interval` - Reporting interval in seconds (default: 10)

### Build Without Pre-Configuration

```bash
# Standard build (requires manual configuration)
./build_macos_pkg.sh
```

Users will need to run the Configuration app after installation.

---

## 📦 What Happens When Pre-Configured

### During Build:

```
📦 Pre-configured Package
   Server URL: http://192.168.1.100:8768
   API Key: [configured]
   Interval: 10s
   ✓ Package will be ready to use immediately after installation
```

### During Installation on Target Mac:

1. User double-clicks `FleetAgent.pkg`
2. Standard macOS installer runs
3. Installation completes
4. **Agent starts automatically** (no configuration needed!)
5. Mac immediately begins reporting to fleet server

### Installation Conclusion Screen:

Shows a green success message:
```
🎉 Installation Complete!
✅ Fleet Agent is Ready!

The agent has been pre-configured and is now running.
Your Mac is already reporting to the fleet server!

No further action required - you're all set!
```

---

## 🎯 Deployment Scenarios

### Scenario 1: Single Environment (Most Common)

**Use Case:** All Macs report to the same server

```bash
# Build once
./build_macos_pkg.sh \
    --server-url "http://fleet.company.com:8768" \
    --api-key "production-key-abc123"

# Deploy everywhere
# Copy FleetAgent.pkg to USB
# Install on all Macs
# Done!
```

### Scenario 2: Multiple Environments

**Use Case:** Different servers for dev/staging/production

```bash
# Production package
./build_macos_pkg.sh \
    --server-url "http://fleet-prod.company.com:8768" \
    --api-key "prod-key"

# Rename for clarity
mv dist/FleetAgent.pkg dist/FleetAgent-Production.pkg

# Staging package
./build_macos_pkg.sh \
    --server-url "http://fleet-staging.company.com:8768" \
    --api-key "staging-key"

mv dist/FleetAgent.pkg dist/FleetAgent-Staging.pkg

# Development package
./build_macos_pkg.sh \
    --server-url "http://localhost:8768" \
    --api-key "dev-key"

mv dist/FleetAgent.pkg dist/FleetAgent-Development.pkg
```

### Scenario 3: Client-Specific Packages (MSP)

**Use Case:** Managed Service Provider with multiple clients

```bash
# Client A
./build_macos_pkg.sh \
    --server-url "http://fleet-clienta.example.com:8768" \
    --api-key "clienta-secret-key"
mv dist/FleetAgent.pkg dist/FleetAgent-ClientA.pkg

# Client B
./build_macos_pkg.sh \
    --server-url "http://fleet-clientb.example.com:8768" \
    --api-key "clientb-secret-key"
mv dist/FleetAgent.pkg dist/FleetAgent-ClientB.pkg

# Deploy appropriate package to each client
```

---

## 💾 USB Deployment with Pre-Configuration

### Perfect Workflow:

1. **Build pre-configured package:**
   ```bash
   ./build_macos_pkg.sh \
       --server-url "http://your-server:8768" \
       --api-key "your-key"
   ```

2. **Copy to USB:**
   ```bash
   cp dist/FleetAgent.pkg /Volumes/USB_DRIVE/
   ```

3. **On each Mac:**
   - Copy FleetAgent.pkg from USB to Desktop
   - Double-click to install
   - **Done!** Mac is now reporting

**No per-machine configuration!** ✨

---

## 🔍 Verification

### Check Installation on Mac

```bash
# Check if agent is running
sudo launchctl list | grep fleet

# View logs
tail -f /var/log/fleet-agent.log

# Check configuration
cat /Library/Application\ Support/FleetAgent/config.json
```

### Check on Fleet Dashboard

```
http://your-server:8768/dashboard
```

Your Mac should appear within 10 seconds!

---

## 🔄 Reconfiguration

If you need to change settings on an installed Mac:

### Option 1: Run Configuration App
1. Go to Applications folder
2. Double-click "Fleet Agent Configuration"
3. Enter new settings
4. Click "Configure"

### Option 2: Reinstall with New Package
1. Build new package with updated settings
2. Install over existing installation
3. Configuration is updated automatically

### Option 3: Manual Edit
```bash
sudo nano /Library/Application\ Support/FleetAgent/config.json
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

---

## 📋 Comparison: Pre-Configured vs Standard

### Pre-Configured Package

**Build:**
```bash
./build_macos_pkg.sh --server-url URL --api-key KEY
```

**Deploy:**
1. Double-click package
2. Enter password
3. ✅ Done!

**Time per Mac:** ~1 minute

**Best for:**
- Mass deployment
- Same configuration everywhere
- Non-technical users
- USB deployments
- Quick rollouts

---

### Standard Package

**Build:**
```bash
./build_macos_pkg.sh
```

**Deploy:**
1. Double-click package
2. Enter password
3. Open Configuration app
4. Enter server URL
5. Enter API key
6. Click Configure
7. ✅ Done!

**Time per Mac:** ~3 minutes

**Best for:**
- Different servers per Mac
- Testing environments
- Custom configurations
- Training purposes

---

## 🔐 Security Considerations

### API Key Storage

Pre-configured packages contain the API key in plain text in:
```
/Library/Application Support/FleetAgent/config.json
```

**Security measures:**
- File is owned by root
- Readable only by root and system
- Not accessible to standard users
- Transmitted over network (use HTTPS in production)

**Best practices:**
1. Use environment-specific API keys
2. Rotate keys periodically
3. Restrict physical access to packages
4. Use HTTPS for fleet server in production
5. Consider storing packages on secure file shares

---

## 💡 Pro Tips

### 1. **Name Your Packages**
```bash
./build_macos_pkg.sh --server-url URL --api-key KEY
mv dist/FleetAgent.pkg dist/FleetAgent-Production-v1.0.0.pkg
```

### 2. **Keep a Build Script**
```bash
#!/bin/bash
# build_all_packages.sh

cd fleet-agent

echo "Building Production package..."
./build_macos_pkg.sh \
    --server-url "http://prod.example.com:8768" \
    --api-key "prod-key-here"
mv dist/FleetAgent.pkg ../packages/FleetAgent-Production.pkg

echo "Building Staging package..."
./build_macos_pkg.sh \
    --server-url "http://staging.example.com:8768" \
    --api-key "staging-key-here"
mv dist/FleetAgent.pkg ../packages/FleetAgent-Staging.pkg

echo "✅ All packages built!"
```

### 3. **Test Before Mass Deployment**
Always test on one Mac first!

```bash
# Build package
./build_macos_pkg.sh --server-url URL --api-key KEY

# Install on test Mac
# Verify on dashboard
# Then deploy to fleet
```

### 4. **Document Your Builds**
Create a README with each package:
```
FleetAgent-Production.pkg
Built: 2024-11-25
Server: http://fleet.company.com:8768
API Key: prod-***-***
Interval: 10s
```

### 5. **Version Control Your Build Commands**
Store build commands in version control for reproducibility.

---

## 📊 Example Deployment

### Small Office (20 Macs)

**Setup:**
```bash
# Build once
./build_macos_pkg.sh \
    --server-url "http://192.168.1.100:8768" \
    --api-key "office-secret-key-12345"

# Copy to USB
cp dist/FleetAgent.pkg /Volumes/USB_DRIVE/
```

**Deploy to each Mac (1 minute each):**
1. Insert USB
2. Copy FleetAgent.pkg to Desktop
3. Double-click
4. Enter admin password
5. Done!

**Total time:** ~20 minutes for 20 Macs!

**Verification:**
- Open http://192.168.1.100:8768/dashboard
- See all 20 Macs reporting
- All green status

---

## 🆚 Before and After

### Before Pre-Configuration Feature

**Deploy process:**
1. Build generic package
2. Install on each Mac (1 min)
3. Open Configuration app (30 sec)
4. Type server URL (30 sec)
5. Type API key (30 sec)
6. Click Configure (10 sec)

**Total: ~3 minutes per Mac**

**For 50 Macs: 2.5 hours**

---

### After Pre-Configuration Feature

**Deploy process:**
1. Build pre-configured package once
2. Install on each Mac (1 min)
3. Done!

**Total: ~1 minute per Mac**

**For 50 Macs: 50 minutes**

**Saves: 1 hour 40 minutes!** 🎉

---

## ✅ Summary

**Pre-configured packages are perfect when:**
- ✅ Deploying to many Macs
- ✅ All Macs use same server
- ✅ You want fastest deployment
- ✅ Users are non-technical
- ✅ Using USB deployment

**Build command:**
```bash
./build_macos_pkg.sh \
    --server-url "http://your-server:8768" \
    --api-key "your-secret-key"
```

**Result:**
- Package: 845KB
- Install time: 1 minute
- Configuration: None needed!
- Auto-start: Yes
- Ready to monitor: Immediately

**It doesn't get easier than this!** 🚀
