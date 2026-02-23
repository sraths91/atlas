# Fleet Agent - Quick Start

## 🚀 Fastest Deployment (2 Minutes)

### Step 1: Build Self-Installing Script
```bash
cd fleet-agent
chmod +x create_installer.sh
./create_installer.sh
```

### Step 2: Deploy to Mac
```bash
# Copy to target Mac
scp dist/fleet-agent-installer.sh admin@target-mac:~/

# Run installer (prompts for server details)
ssh admin@target-mac 'sudo ~/fleet-agent-installer.sh'
```

That's it! The agent is now:
- ✅ Installed with all dependencies
- ✅ Configured to connect to your server
- ✅ Running and reporting metrics
- ✅ Set to auto-start on boot

---

## 📦 Alternative: Build .pkg Installer

For professional deployments or MDM systems:

```bash
cd fleet-agent
chmod +x build_macos_pkg.sh
./build_macos_pkg.sh
```

Install on target Mac:
```bash
sudo installer -pkg dist/FleetAgent.pkg -target /
```

Then configure:
```bash
sudo nano /Library/Application\ Support/FleetAgent/config.json
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

---

## 🔍 Verify It's Working

### Check the Dashboard
Open your fleet server dashboard:
```
http://your-server:8768/dashboard
```

You should see the new machine appear within 10 seconds!

### Check Logs on Mac
```bash
tail -f /var/log/fleet-agent.log
```

### Check Service Status
```bash
sudo launchctl list | grep fleet
```

---

## ⚙️ Configuration

Location: `/Library/Application Support/FleetAgent/config.json`

```json
{
    "server_url": "http://your-server:8768",
    "api_key": "your-api-key",
    "interval": 10
}
```

After editing, restart:
```bash
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

---

## 🛠️ Common Commands

**View logs:**
```bash
tail -f /var/log/fleet-agent.log
```

**Restart service:**
```bash
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist
```

**Stop service:**
```bash
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
```

**Test manually:**
```bash
/usr/local/bin/fleet-agent /Library/Application\ Support/FleetAgent/config.json
```

---

## 🔥 Mass Deployment

Deploy to multiple Macs at once:

```bash
# Create list of Macs
MACS="mac1 mac2 mac3 mac4 mac5"

# Build installer
./create_installer.sh

# Deploy to all
for mac in $MACS; do
    echo "Deploying to $mac..."
    scp dist/fleet-agent-installer.sh admin@$mac:~/
    ssh admin@$mac 'sudo ~/fleet-agent-installer.sh' &
done

wait
echo "✅ Deployment complete!"
```

---

## 📱 What Gets Monitored

The agent collects and reports:

- **System Info**: Hostname, OS version, hardware specs, serial number
- **CPU**: Usage %, load average, core count
- **Memory**: Total, used, available, swap
- **Disk**: Usage per partition, I/O stats
- **Network**: Bytes sent/received, packet counts
- **Battery**: Charge level, power status (for laptops)
- **Processes**: Count, top CPU/memory users

All data is sent to your fleet server every 10 seconds (configurable).

---

## 🔒 Security

- **Lightweight**: Minimal resource usage (<1% CPU, <50MB RAM)
- **Secure**: Optional API key authentication
- **Private**: Only system metrics, no personal data
- **Safe**: Read-only operations (except command execution if enabled)

---

## ❓ Troubleshooting

### Agent not appearing on dashboard?

**Check connectivity:**
```bash
curl http://your-server:8768/api/fleet/summary
```

**Check logs:**
```bash
tail -50 /var/log/fleet-agent.error.log
```

**Verify config:**
```bash
cat /Library/Application\ Support/FleetAgent/config.json
```

### Service not starting?

**Check status:**
```bash
sudo launchctl list | grep fleet
```

**Run manually to see errors:**
```bash
/usr/local/bin/fleet-agent /Library/Application\ Support/FleetAgent/config.json
```

---

## 📖 Full Documentation

- [README.md](README.md) - Complete documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Advanced deployment options
- Fleet Server docs - Server setup and configuration

---

## 💡 Tips

1. **Use hostnames in your server URL** instead of IPs (easier to change later)
2. **Set interval to 30-60 seconds** for large fleets (reduces load)
3. **Generate unique API keys** for each environment
4. **Test on one machine** before fleet-wide deployment
5. **Monitor the fleet dashboard** to catch issues early

---

## Need Help?

**Logs:** `/var/log/fleet-agent.log`  
**Config:** `/Library/Application Support/FleetAgent/config.json`  
**Service:** `/Library/LaunchDaemons/com.fleet.agent.plist`

Check logs first - they usually show exactly what's wrong!
