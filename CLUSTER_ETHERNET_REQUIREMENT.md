# 🔌 Cluster Server Ethernet Requirement

## ✅ Wired Connection Required

The Fleet Server cluster node installer **requires an active Ethernet connection** before installation. This ensures reliable, server-grade networking for your cluster deployment.

---

## 🎯 Why Ethernet is Required

### Server-Grade Reliability

**WiFi is NOT suitable for server deployments:**

❌ **WiFi Issues:**
- Signal interference
- Disconnections and dropouts
- Variable latency
- Bandwidth fluctuations
- Security vulnerabilities
- Limited simultaneous connections

✅ **Ethernet Benefits:**
- Stable, consistent connection
- No signal interference
- Low, predictable latency
- Full bandwidth utilization
- Better security (physical access required)
- 24/7 reliability

### Cluster Synchronization

**Cluster nodes need reliable connectivity for:**
- Real-time heartbeat monitoring
- Session synchronization
- Database access
- Health checks
- Load balancer communication

**WiFi instability can cause:**
- False failover triggers
- Session loss
- Database lock contention
- Cluster split-brain scenarios
- Degraded user experience

---

## 🔍 What the Installer Checks

### Pre-Installation Verification:

The installer performs these checks **before** installation:

1. **Ethernet Adapter Detection**
   - Checks for built-in Ethernet
   - Detects Thunderbolt Ethernet adapters
   - Detects USB Ethernet adapters

2. **Active Connection Verification**
   - Confirms interface is "active"
   - Verifies IP address assignment
   - Checks link speed

3. **Primary Interface Check**
   - Warns if WiFi is primary service
   - Recommends Ethernet as primary

### Installation Behavior:

```bash
# ✅ PASS: Ethernet connected with IP
✅ Ethernet connected via en0
   IP Address: 192.168.1.100
   Link Speed: 1000baseT

✅ Network requirements verified

Proceeding with installation...

# ❌ FAIL: No Ethernet adapter found
❌ ERROR: No Ethernet adapter found on this Mac

Fleet Server requires a wired Ethernet connection for:
  • Reliable 24/7 operation
  • Consistent network performance
  • Server-grade stability

Please connect an Ethernet cable and try again.

Installation aborted.

# ❌ FAIL: Ethernet adapter present but not connected
❌ ERROR: No active Ethernet connection detected

Available Ethernet adapters found, but none are connected:
  • en0 - Status: inactive
  • en5 - Status: inactive

Please connect an Ethernet cable and try again.

Installation aborted.
```

---

## 🔧 Supported Ethernet Adapters

### ✅ Supported:

| Type | Examples | Notes |
|------|----------|-------|
| **Built-in Ethernet** | MacBook Pro, Mac Mini, Mac Pro | Best option |
| **Thunderbolt Ethernet** | Apple Thunderbolt Ethernet<br>Belkin Thunderbolt 3 to Ethernet | Excellent performance |
| **USB Ethernet** | USB-C to Ethernet<br>USB 3.0 to Gigabit Ethernet | Good alternative |

### Common Adapters:

- **Apple Thunderbolt to Gigabit Ethernet Adapter** (recommended)
- **Apple USB-C to Gigabit Ethernet Adapter** (recommended)
- **Anker USB-C to Ethernet Adapter**
- **Belkin USB-C to Gigabit Ethernet**
- **TP-Link USB 3.0 to Gigabit Ethernet**

---

## 🚀 Before Installation

### Pre-Installation Checklist:

- [ ] **Ethernet cable connected** to Mac
- [ ] **Cable connected to network switch/router**
- [ ] **Link lights active** on both ends
- [ ] **IP address assigned** (check System Preferences → Network)
- [ ] **Can ping external hosts** (test connectivity)
- [ ] **Ethernet is primary network service** (optional but recommended)

### Quick Test:

```bash
# 1. Check ethernet interfaces
networksetup -listallhardwareports | grep -A 1 Ethernet

# 2. Check IP address
ifconfig | grep "inet " | grep -v 127.0.0.1

# 3. Test connectivity
ping -c 3 8.8.8.8

# 4. Check if Ethernet is primary
networksetup -listnetworkserviceorder
```

---

## ⚙️ Setting Ethernet as Primary

### Why Set as Primary?

Even if Ethernet is connected, macOS may still route traffic through WiFi if it's listed first in the service order.

### How to Set Ethernet as Primary:

**Via System Preferences:**

1. Open **System Preferences** → **Network**
2. Click the **gear icon** (⚙️) at the bottom
3. Select **"Set Service Order..."**
4. **Drag Ethernet** to the top of the list
5. Click **OK**
6. Click **Apply**

**Via Command Line:**

```bash
# List current order
networksetup -listnetworkserviceorder

# Set Ethernet first (adjust names as needed)
sudo networksetup -ordernetworkservices "Ethernet" "Wi-Fi" "Bluetooth PAN"
```

**Verify:**

```bash
# Check routing
netstat -rn | grep default

# Should show ethernet interface (en0, en5, etc.) for default route
default            192.168.1.1        UGSc           en0
```

---

## 🐛 Troubleshooting

### Issue: "No Ethernet adapter found"

**Symptoms:**
- Installer fails immediately
- Error message about no adapter

**Solutions:**

```bash
# 1. Check if Mac has built-in Ethernet
system_profiler SPNetworkDataType | grep Ethernet

# 2. If no built-in, connect USB/Thunderbolt adapter
# 3. Wait 10 seconds for macOS to detect
# 4. Verify detection
networksetup -listallhardwareports

# 5. Try installation again
```

---

### Issue: "No active Ethernet connection detected"

**Symptoms:**
- Ethernet adapter detected
- But marked as inactive
- No IP address

**Solutions:**

```bash
# 1. Check cable is plugged in both ends
# 2. Check link lights on adapter and switch
# 3. Try different cable
# 4. Try different switch port

# 5. Check if interface is enabled
networksetup -getinfo "Ethernet"

# 6. If disabled, enable it
sudo ifconfig en0 up

# 7. Request DHCP address
sudo ipconfig set en0 DHCP

# 8. Verify IP assigned
ifconfig en0 | grep "inet "

# 9. Try installation again
```

---

### Issue: "WiFi appears to be primary network service"

**Symptoms:**
- Warning during installation
- Installation continues but with warning

**Solutions:**

```bash
# 1. Set Ethernet as primary (see above)
sudo networksetup -ordernetworkservices "Ethernet" "Wi-Fi"

# 2. Disable WiFi during server operation
sudo networksetup -setairportpower en1 off

# 3. Or just ensure Ethernet has priority
# Installation will proceed with warning
```

---

### Issue: Adapter Detected but "Status: unknown"

**Symptoms:**
- Adapter shows up but status unclear
- May have IP but marked inactive

**Solutions:**

```bash
# 1. Reset networking
sudo ifconfig en0 down
sudo ifconfig en0 up

# 2. Renew DHCP lease
sudo ipconfig set en0 DHCP
sudo ipconfig set en0 BOOTP
sudo ipconfig set en0 DHCP

# 3. Check system preferences
# Network → Ethernet → Configure IPv4 → Using DHCP

# 4. Restart network services
sudo killall -HUP mDNSResponder

# 5. Try installation again
```

---

## 📊 Network Requirements

### Minimum Requirements:

| Requirement | Specification |
|-------------|---------------|
| **Connection Type** | Wired Ethernet (required) |
| **Speed** | 100 Mbps minimum, 1 Gbps recommended |
| **IP Assignment** | DHCP or Static |
| **Connectivity** | Must reach cluster backend (Redis/storage) |
| **Latency** | <50ms to backend (recommended) |
| **Uptime** | 24/7 stable connection |

### Recommended Setup:

- **Gigabit Ethernet** (1000baseT)
- **Managed Switch** with monitoring
- **Static IP** or DHCP reservation
- **Redundant switches** for failover
- **UPS power backup** for switch and server

---

## 🔐 Security Considerations

### Wired Network Benefits:

✅ **Physical Security:**
- Attacker needs physical access
- No over-the-air attacks
- Harder to intercept traffic

✅ **Network Segmentation:**
- Easier to isolate server traffic
- VLAN support on managed switches
- Better firewall control

✅ **Monitoring:**
- Predictable traffic patterns
- Easier anomaly detection
- Better performance metrics

### Best Practices:

1. **Use Managed Switch:**
   - Port security (MAC filtering)
   - VLAN segmentation
   - Traffic monitoring

2. **Network Segmentation:**
   - Separate server VLAN
   - Restrict access to management
   - Firewall between networks

3. **Physical Security:**
   - Secure server room/closet
   - Lock network equipment
   - Cable management

---

## 📖 Example Scenarios

### Scenario 1: MacBook Pro (No Built-in Ethernet)

```bash
# Problem: MacBook Pro doesn't have Ethernet port

# Solution:
1. Purchase USB-C to Gigabit Ethernet adapter
   Recommendation: Apple USB-C to Gigabit Ethernet ($29)

2. Connect adapter to MacBook Pro

3. Connect Ethernet cable to adapter

4. Verify in System Preferences → Network
   Should show "Ethernet" or "USB 10/100/1000 LAN"

5. Run installation
   ✅ Ethernet connected via en6
   Installation proceeds
```

---

### Scenario 2: Mac Mini (Built-in Ethernet)

```bash
# Setup: Mac Mini with built-in Ethernet port

1. Connect Ethernet cable directly to Mac Mini

2. Cable connects to network switch

3. Verify link lights on both ends
   ✅ Green/amber lights active

4. Check System Preferences → Network
   ✅ Ethernet - Status: Connected
   ✅ IP Address: 192.168.1.100

5. Run installation
   ✅ Ethernet connected via en0
   ✅ Link Speed: 1000baseT
   Installation proceeds
```

---

### Scenario 3: Remote Office Deployment

```bash
# Setup: Remote office, connecting to cloud Redis

1. Ensure reliable internet connection via Ethernet
   - Connect Mac to office router via Ethernet
   - Router has internet connectivity
   - Can reach cloud Redis server

2. Test connectivity to backend
   redis-cli -h redis.company.com -p 6379 -a password ping

3. Verify Ethernet is active
   ifconfig en0 | grep "inet "
   ✅ inet 10.0.1.100

4. Run installation
   ✅ Ethernet connected via en0
   ✅ IP Address: 10.0.1.100
   ✅ Can reach Redis backend
   Installation proceeds
```

---

## ✅ Summary

### Installation Requirements:

✅ **Wired Ethernet connection** (built-in or adapter)  
✅ **Active connection** with IP address  
✅ **Network connectivity** to cluster backend  
✅ **Link speed** 100 Mbps minimum  

### What Happens During Installation:

1. **Pre-install check** verifies Ethernet
2. **Installation proceeds** only if Ethernet active
3. **Warning shown** if WiFi is primary
4. **Installation fails** if no Ethernet found

### Why This Matters:

- **Reliability:** Servers need stable connections
- **Performance:** Consistent latency and bandwidth
- **Cluster Health:** Reliable node communication
- **User Experience:** No dropouts or delays

---

## 🚀 Ready to Install?

**Quick Check:**

```bash
# Run this before installation:
ifconfig | grep -A 10 "en[0-9]:" | grep -E "status|inet "

# Expected output:
#   status: active
#   inet 192.168.1.100 netmask 0xffffff00

# If you see "status: active" and an IP address, you're good to go! ✅
```

**Then install:**

```bash
sudo installer -pkg FleetServerClusterNode.pkg -target /

# Installation will verify Ethernet before proceeding
```

---

**Your cluster servers will be stable and reliable with wired Ethernet!** 🔌✅
