# 🌐 Cluster Node Installer - User Guide

## 📦 Build & Deploy Additional Cluster Nodes from the Dashboard!

This feature allows you to generate macOS .pkg installers directly from the Settings page that will automatically configure new servers to join your existing cluster - **even across different networks**!

---

## ✨ What Is This?

The **Cluster Node Installer** is a one-click solution to expand your fleet monitoring cluster. Instead of manually configuring each new server, you can:

1. Click a button in the Settings page
2. Download a pre-configured .pkg installer
3. Copy it to a new server (via USB, network, etc.)
4. Install it
5. The new server automatically joins your cluster!

---

## 🎯 Benefits

### ✅ Seamless Deployment
- No manual configuration needed
- All settings automatically copied from primary server
- One-click package generation

### ✅ Cross-Network Support
- Servers can be on different networks
- Only requirement: access to shared backend (Redis/storage)
- Perfect for multi-site deployments

### ✅ Automatic Configuration
- Cluster settings embedded
- Authentication keys included
- Database encryption keys copied
- Redis/storage connection configured

### ✅ Instant Integration
- New server joins cluster on first boot
- Starts handling traffic immediately
- Load balancer detects automatically

---

## 📋 Prerequisites

### Before You Start:

1. **Cluster Mode Enabled**
   - Your primary server must have cluster mode enabled
   - Cluster configuration working (Redis or shared storage)

2. **Shared Backend Accessible**
   - Redis server reachable from both networks
   - Or network filesystem accessible
   - New server must reach the same backend

3. **macOS Target Server**
   - New server must be macOS
   - Admin access to install package

4. **🔌 Ethernet Connection Required** ⚠️
   - **MUST have active wired Ethernet connection**
   - WiFi is NOT supported for server installations
   - Ethernet adapter (built-in or USB/Thunderbolt) required
   - IP address must be assigned via Ethernet
   - See `CLUSTER_ETHERNET_REQUIREMENT.md` for details

---

## 🚀 How To Use

### Step 1: Access Settings Page

1. Log in to your Fleet Dashboard
2. Click **⚙️ Settings** in the navigation
3. Scroll to **🌐 Cluster Node Installer** section

---

### Step 2: Check Cluster Status

The installer will show your current cluster status:

```
✅ Cluster Mode Enabled

Backend: redis
Active Nodes: 2
This Node ID: server-01-abc123
```

If you see "Cluster mode not enabled", you need to [enable cluster mode](#enabling-cluster-mode) first.

---

### Step 3: Configure New Node

**Optional Settings:**

- **Node Name**: Custom name for the new server (e.g., `server-03`)
  - Leave empty to auto-generate from hostname
  
- **Package Name**: Name for the .pkg file
  - Default: `FleetServerClusterNode.pkg`

---

### Step 4: Build Package

Click **📦 Build Cluster Node Package**

The system will:
1. Generate cluster configuration
2. Embed all necessary keys and settings
3. Create LaunchDaemon for auto-start
4. Build macOS .pkg installer
5. Download automatically

**⏱️ This takes ~10-30 seconds**

---

### Step 5: Deploy to New Server

**⚠️ BEFORE INSTALLATION:**

```bash
# Verify Ethernet connection FIRST!
ifconfig | grep -A 10 "en[0-9]:" | grep -E "status|inet "

# Expected output:
#   status: active
#   inet 192.168.1.100 netmask 0xffffff00

# If no Ethernet, installation will fail!
# Connect Ethernet cable before proceeding
```

**Method A: USB Drive**

```bash
# 1. Copy package to USB
cp FleetServerClusterNode.pkg /Volumes/USB/

# 2. On new server, copy from USB
cp /Volumes/USB/FleetServerClusterNode.pkg ~/Desktop/

# 3. Double-click to install
# Installer will check for Ethernet first
```

**Method B: Network Transfer**

```bash
# Using SCP
scp FleetServerClusterNode.pkg admin@new-server:/tmp/

# On new server
sudo installer -pkg /tmp/FleetServerClusterNode.pkg -target /
```

**Method C: Direct Download** (if servers can communicate)

```bash
# Download from primary server
curl -O https://primary-server:8768/path/to/package.pkg

# Install
sudo installer -pkg FleetServerClusterNode.pkg -target /
```

---

### Step 6: Verify Installation

**On the new server:**

```bash
# Check if service is running
launchctl list | grep fleet.server

# View logs
tail -f /var/log/fleet-server.log

# Expected output:
# ✅ Cluster mode ENABLED (node: server-02-xyz789, backend: redis)
# ✅ Registered node in cluster: server-02-xyz789
# ✅ Fleet server started on 0.0.0.0:8768
```

**On the dashboard:**

1. Go to Settings → Cluster Node Installer
2. Check cluster status
3. Should show increased "Active Nodes" count

---

## 🔧 What Gets Configured

### Automatically Included:

| Component | Details |
|-----------|---------|
| **Cluster Backend** | Redis host, port, password, database |
| **Encryption Keys** | Database encryption key (Fernet) |
| **Payload Encryption** | AES-256-GCM key for E2EE |
| **Authentication** | API key, web username, web password |
| **Database Path** | Shared storage location |
| **Session Storage** | Redis configuration for sessions |
| **Heartbeat Settings** | Interval and timeout configuration |
| **Auto-Start** | LaunchDaemon for system boot |
| **SSL/TLS** | Certificate paths (if configured) |

---

## 🌐 Cross-Network Deployment

### How It Works Across Different Networks:

```
Network A (Office)              Network B (Data Center)
┌─────────────────┐            ┌─────────────────┐
│  Primary Server │            │   New Server    │
│  10.0.1.100     │            │  192.168.1.50   │
└─────────────────┘            └─────────────────┘
        │                               │
        └───────────────┬───────────────┘
                        ▼
            ┌─────────────────────┐
            │   Cloud Redis       │
            │   redis.company.com │
            │   (Public IP)       │
            └─────────────────────┘
```

**Key Points:**

1. **Both servers connect to same Redis**
   - Redis must have public IP or VPN access
   - Both servers use same Redis credentials

2. **No Direct Communication Needed**
   - Servers don't need to talk to each other
   - All coordination via Redis

3. **Load Balancer Required**
   - Put both servers behind load balancer
   - LB distributes traffic

---

## 🔐 Security Considerations

### ⚠️ Important Security Notes:

1. **Package Contains Sensitive Data**
   - All encryption keys embedded
   - API keys included
   - Database credentials present
   - **Keep the .pkg file secure!**

2. **Recommended Security Practices:**
   ```bash
   # Encrypt the package before transfer
   openssl enc -aes-256-cbc -salt -in FleetServerClusterNode.pkg \
     -out FleetServerClusterNode.pkg.enc
   
   # On target server, decrypt
   openssl enc -aes-256-cbc -d -in FleetServerClusterNode.pkg.enc \
     -out FleetServerClusterNode.pkg
   ```

3. **Delete After Installation:**
   ```bash
   # After installing
   sudo rm -P /tmp/FleetServerClusterNode.pkg
   ```

4. **Restrict Access:**
   - Only distribute to trusted administrators
   - Use secure channels (encrypted USB, VPN, SSH)
   - Don't email or upload to public locations

---

## 🔍 Troubleshooting

### Issue: Installation Fails - "No Ethernet adapter found"

**Symptoms:**
- Installation fails immediately
- Error message about Ethernet requirement
- Package installer exits

**Error Message:**
```
❌ ERROR: No Ethernet adapter found on this Mac

Fleet Server requires a wired Ethernet connection for:
  • Reliable 24/7 operation
  • Consistent network performance
  • Server-grade stability

Please connect an Ethernet cable and try again.
```

**Solutions:**

```bash
# 1. Check if Mac has Ethernet port
system_profiler SPNetworkDataType | grep Ethernet

# 2. If no built-in Ethernet, you need an adapter:
# - Apple USB-C to Gigabit Ethernet Adapter
# - Apple Thunderbolt to Gigabit Ethernet Adapter
# - Any USB/Thunderbolt Ethernet adapter

# 3. Connect adapter to Mac
# Wait 10 seconds for detection

# 4. Verify adapter detected
networksetup -listallhardwareports | grep Ethernet

# 5. Connect Ethernet cable

# 6. Verify connection active
ifconfig | grep -E "en[0-9]" -A 3 | grep "status: active"

# 7. Try installation again
```

---

### Issue: Installation Fails - "No active Ethernet connection detected"

**Symptoms:**
- Ethernet adapter found
- But not connected or no IP
- Installation aborted

**Error Message:**
```
❌ ERROR: No active Ethernet connection detected

Available Ethernet adapters found, but none are connected:
  • en0 - Status: inactive

Please connect an Ethernet cable and try again.

WiFi connections are NOT supported for Fleet Server installations.
```

**Solutions:**

```bash
# 1. Check Ethernet cable is plugged in
# - Check both ends (Mac and switch/router)
# - Look for link lights

# 2. Check cable is good
# - Try different cable
# - Test cable with another device

# 3. Check switch/router port
# - Try different port
# - Check if port is enabled

# 4. Enable Ethernet interface
sudo ifconfig en0 up

# 5. Request IP address
sudo ipconfig set en0 DHCP

# 6. Wait 10 seconds for IP assignment

# 7. Verify connection
ifconfig en0 | grep "inet "
# Should show: inet 192.168.x.x

# 8. Try installation again
```

---

### Issue: Package Build Fails

**Symptoms:**
- Error message in dashboard
- Download doesn't start

**Solutions:**

```bash
# Check server logs
tail -f /var/log/fleet-server.log

# Verify cluster mode enabled
curl http://localhost:8768/api/fleet/cluster/status

# Check permissions
ls -la /Library/FleetServer/
```

---

### Issue: New Server Won't Join Cluster

**Symptoms:**
- Server starts but doesn't appear in cluster status
- "Connection refused" errors in logs

**Solutions:**

```bash
# 1. Check Redis connectivity from new server
redis-cli -h YOUR_REDIS_HOST -p 6379 -a YOUR_PASSWORD ping

# Should return: PONG

# 2. Verify config file
cat /Library/FleetServer/config/config.yaml

# 3. Check if service is running
launchctl list | grep fleet.server

# 4. Restart service
sudo launchctl stop com.fleet.server.cluster
sudo launchctl start com.fleet.server.cluster

# 5. Check logs
tail -100 /var/log/fleet-server.log
```

---

### Issue: "Cluster mode not enabled" Message

**Symptoms:**
- Can't build package
- Warning message instead of form

**Solution:**

1. Enable cluster mode in primary server config:
   ```yaml
   cluster:
     enabled: true
     backend: redis
     redis_host: "redis.company.com"
     redis_password: "password"
   
   sessions:
     backend: redis
     redis:
       host: "redis.company.com"
       password: "password"
   ```

2. Restart primary server:
   ```bash
   sudo systemctl restart fleet-server
   ```

---

### Issue: Redis Connection Errors

**Symptoms:**
- "Connection refused" in logs
- Nodes not registering

**Solutions:**

```bash
# 1. Verify Redis is accessible
telnet YOUR_REDIS_HOST 6379

# 2. Check Redis configuration
# Edit /etc/redis/redis.conf:
bind 0.0.0.0
requirepass YOUR_PASSWORD

# 3. Restart Redis
sudo systemctl restart redis

# 4. Test from new server
redis-cli -h YOUR_REDIS_HOST -p 6379 -a YOUR_PASSWORD
> PING
# Should return: PONG
```

---

## 📖 Example: Complete Deployment

### Scenario: Add Server in Remote Office

**Initial Setup:**
- Primary server: `server-01` (San Francisco office)
- New server: `server-02` (New York office)
- Redis: Cloud-hosted on AWS
- Different networks, connected via internet

**Steps:**

```bash
# 1. On San Francisco server (via web browser)
# - Go to https://server-01:8768/settings
# - Scroll to Cluster Node Installer
# - Node Name: "nyc-server-01"
# - Click "Build Cluster Node Package"
# - Download: FleetServerClusterNode.pkg

# 2. Secure transfer to New York
# Upload to internal file share (encrypted)
scp FleetServerClusterNode.pkg admin@fileserver:/secure/

# 3. On New York server
scp admin@fileserver:/secure/FleetServerClusterNode.pkg /tmp/

# 4. Install package
sudo installer -pkg /tmp/FleetServerClusterNode.pkg -target /

# 5. Verify installation
tail -f /var/log/fleet-server.log

# Expected output:
# ✅ Cluster mode ENABLED (node: nyc-server-01-def456, backend: redis)
# ✅ Registered node in cluster
# ✅ Fleet server started on 0.0.0.0:8768

# 6. Verify in dashboard
# Go back to https://server-01:8768/settings
# Check Cluster Node Installer section
# Should show: "Active Nodes: 2"

# 7. Update load balancer
# Add new server to backend pool:
# server server-02 nyc-server.company.com:8768 check

# 8. Done! Traffic now distributed across both nodes
```

---

## 🎯 Best Practices

### ✅ DO:

1. **Test in Staging First**
   - Build package
   - Test on staging server
   - Verify cluster joins
   - Then deploy to production

2. **Document Your Nodes**
   - Keep list of node IDs
   - Note which servers are active
   - Track Redis credentials

3. **Monitor After Deployment**
   - Watch logs for errors
   - Check cluster status regularly
   - Monitor Redis connections

4. **Secure Package Distribution**
   - Encrypt before transfer
   - Use secure channels
   - Delete after installation

5. **Keep Backups**
   - Backup Redis data
   - Keep cluster configuration
   - Document recovery procedures

### ❌ DON'T:

1. **Don't Email Packages**
   - Contains all encryption keys
   - Insecure transmission
   - Use encrypted channels only

2. **Don't Reuse Old Packages**
   - Keys may have changed
   - Config may be outdated
   - Always build fresh

3. **Don't Skip Testing**
   - Always test new nodes
   - Verify cluster membership
   - Check traffic routing

4. **Don't Ignore Errors**
   - Check logs immediately
   - Fix issues before adding to LB
   - Monitor during deployment

---

## 📊 Monitoring Your Cluster

### Dashboard Monitoring:

1. **Settings Page**
   - Shows active node count
   - Displays current backend
   - Shows this node's ID

2. **Cluster Status API**
   ```bash
   curl http://localhost:8768/api/fleet/cluster/status
   ```

3. **Health Check API**
   ```bash
   curl http://localhost:8768/api/fleet/cluster/health
   ```

### Redis Monitoring:

```bash
# Check cluster state
redis-cli -h YOUR_REDIS_HOST -p 6379 -a YOUR_PASSWORD
> KEYS fleet:cluster:*

# Check session count
> KEYS fleet:session:*

# Monitor commands
> MONITOR
```

---

## 🚀 What's Next?

After deploying additional nodes:

1. **Configure Load Balancer**
   - See `CLUSTER_SETUP_GUIDE.md`
   - Add new nodes to backend pool
   - Enable health checks

2. **Test Failover**
   - Stop one node
   - Verify traffic continues
   - Check dashboard accessibility

3. **Monitor Performance**
   - Watch request distribution
   - Check response times
   - Monitor resource usage

4. **Plan for Growth**
   - Add more nodes as needed
   - Scale horizontally
   - Consider geographic distribution

---

## 📖 Related Documentation

- **`CLUSTER_SETUP_GUIDE.md`** - Complete cluster setup
- **`CLUSTER_QUICK_START.md`** - 5-minute quick start
- **`config_cluster_example.yaml`** - Configuration reference
- **`SECURITY_COMPLETE.md`** - Security best practices

---

## ✅ Summary

**Your Request:**
> "Can we build an option on the settings page to create a pkg that creates a new server install that is automatically clustered to the first one regardless of the network that the two hosts are on?"

**What You Got:**

✅ **Settings Page Integration** - One-click package builder  
✅ **Automatic Configuration** - All settings embedded  
✅ **Cross-Network Support** - Works across different networks  
✅ **Secure Packaging** - All keys encrypted in package  
✅ **Auto-Join Cluster** - New server registers automatically  
✅ **LaunchDaemon** - Auto-start on boot  
✅ **Complete Documentation** - Full guide with examples  
✅ **Production Ready** - Enterprise-grade deployment  

**You can now:**
- Click a button to build installer packages
- Copy package to any network
- Install on new server
- New server automatically joins cluster
- Zero manual configuration needed!

**Perfect for:**
- Multi-site deployments
- Geographic redundancy
- Rapid cluster expansion
- Disaster recovery setups

**Deploy with confidence - your cluster expansion is fully automated!** 🎉🚀
