# ⚡ Quick Restart Trigger Reference

## 🎯 Common Scenarios

### **Scenario 1: Production Server (Recommended)**

**Goal:** Maximum uptime, smart restarts, daily maintenance

```xml
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
    <key>SuccessfulExit</key>
    <false/>
    <key>NetworkState</key>
    <true/>
</dict>

<key>ThrottleInterval</key>
<integer>10</integer>

<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

**Result:**
- ✅ Restarts on crash or error
- ✅ Only runs when network available
- ✅ Daily fresh restart at 3 AM
- ✅ 10-second cooldown

---

### **Scenario 2: Manual Control**

**Goal:** Easy enable/disable without commands

```xml
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
    <key>PathState</key>
    <dict>
        <key>/Users/samraths/.atlas/enabled</key>
        <true/>
    </dict>
</dict>
```

**Usage:**
```bash
# Enable agent
mkdir -p ~/.atlas && touch ~/.atlas/enabled

# Disable agent
rm ~/.atlas/enabled
```

**Result:**
- ✅ Simple file-based control
- ✅ No sudo needed
- ✅ Instant enable/disable

---

### **Scenario 3: Memory Leak Prevention**

**Goal:** Restart every 6 hours to clear memory

```xml
<key>KeepAlive</key>
<true/>

<key>StartInterval</key>
<integer>21600</integer>  <!-- 6 hours -->
```

**Result:**
- ✅ Forced restart every 6 hours
- ✅ Prevents memory leaks
- ✅ Fresh state regularly

---

### **Scenario 4: Network-Dependent**

**Goal:** Only run when internet available

```xml
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
    <key>NetworkState</key>
    <true/>
</dict>
```

**Result:**
- ✅ Starts when network connects
- ✅ Stops when network disconnects
- ✅ Saves resources when offline

---

### **Scenario 5: Depend on Fleet Server**

**Goal:** Only run when Fleet Server is running

```xml
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
    <key>OtherJobEnabled</key>
    <dict>
        <key>com.fleet.server</key>
        <true/>
    </dict>
</dict>
```

**Result:**
- ✅ Starts with Fleet Server
- ✅ Stops with Fleet Server
- ✅ Dependency management

---

### **Scenario 6: Aggressive Restart**

**Goal:** Always running, fast restart, no delays

```xml
<key>KeepAlive</key>
<true/>

<key>ThrottleInterval</key>
<integer>3</integer>
```

**Result:**
- ✅ Restarts on ANY exit
- ✅ 3-second restart time
- ✅ Maximum uptime

---

### **Scenario 7: Conservative Restart**

**Goal:** Slow, careful restarts to prevent loops

```xml
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
</dict>

<key>ThrottleInterval</key>
<integer>60</integer>
```

**Result:**
- ✅ Only restarts on crashes
- ✅ 60-second cooldown
- ✅ Prevents rapid restart loops

---

### **Scenario 8: Scheduled Maintenance**

**Goal:** Daily restart during low-usage time

```xml
<key>KeepAlive</key>
<true/>

<key>StartCalendarInterval</key>
<array>
    <!-- 3 AM daily -->
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <!-- Sunday midnight (weekly deep restart) -->
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>0</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</array>
```

**Result:**
- ✅ Daily restart at 3 AM
- ✅ Weekly restart Sunday midnight
- ✅ Predictable maintenance windows

---

## 📊 Parameter Quick Reference

| Parameter | Values | Purpose |
|-----------|--------|---------|
| **Crashed** | true/false | Restart on crash/kill |
| **SuccessfulExit** | false (restart on error)<br>true (restart on success) | Control exit behavior |
| **NetworkState** | true/false | Require network |
| **PathState** | path + true/false | File-based control |
| **OtherJobEnabled** | job + true/false | Service dependency |
| **ThrottleInterval** | seconds (1-300) | Restart cooldown |
| **StartInterval** | seconds | Periodic restart |
| **StartCalendarInterval** | time dict | Scheduled restart |
| **ExitTimeOut** | seconds (5-120) | Shutdown timeout |

---

## 🔄 How to Apply Changes

### **1. Edit plist file:**
```bash
sudo nano /Library/LaunchDaemons/com.atlas.agent.plist
```

### **2. Validate syntax:**
```bash
plutil -lint /Library/LaunchDaemons/com.atlas.agent.plist
```

### **3. Reload service:**
```bash
sudo launchctl bootout system /Library/LaunchDaemons/com.atlas.agent.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.atlas.agent.plist
```

### **4. Verify it's running:**
```bash
sudo launchctl list | grep atlas
lsof -i :8767
```

---

## 🧪 Testing Triggers

### **Test Crash Restart:**
```bash
# Kill process
sudo kill -9 $(pgrep -f "live_widgets")

# Wait for throttle interval
sleep 10

# Check if restarted
pgrep -f "live_widgets"
```

### **Test Network Restart:**
```bash
# Disable WiFi
sudo networksetup -setairportpower en0 off

# Agent should stop within ~10 seconds
lsof -i :8767  # Should show nothing

# Enable WiFi
sudo networksetup -setairportpower en0 on

# Agent should restart
sleep 10
lsof -i :8767  # Should show agent
```

### **Test File-Based Control:**
```bash
# If PathState is configured:

# Disable
rm ~/.atlas/enabled
sleep 10
lsof -i :8767  # Should be empty

# Enable
touch ~/.atlas/enabled
sleep 10
lsof -i :8767  # Should show agent
```

---

## 💡 Recommendations

### **For Most Users:**
```xml
<!-- Simple, reliable, production-ready -->
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
    <key>SuccessfulExit</key>
    <false/>
</dict>
<key>ThrottleInterval</key>
<integer>10</integer>
```

### **For Power Users:**
```xml
<!-- Network-aware with manual control -->
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
    <key>SuccessfulExit</key>
    <false/>
    <key>NetworkState</key>
    <true/>
    <key>PathState</key>
    <dict>
        <key>/Users/samraths/.atlas/enabled</key>
        <true/>
    </dict>
</dict>
<key>ThrottleInterval</key>
<integer>10</integer>
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

---

## 🎯 Decision Tree

```
Do you need network for operation?
├─ YES → Add NetworkState: true
└─ NO  → Skip NetworkState

Do you want manual control?
├─ YES → Add PathState with ~/.atlas/enabled
└─ NO  → Skip PathState

Does it have memory leaks?
├─ YES → Add StartInterval (periodic restart)
└─ NO  → Skip StartInterval

Do you want scheduled maintenance?
├─ YES → Add StartCalendarInterval (3 AM daily)
└─ NO  → Skip StartCalendarInterval

How stable is it?
├─ VERY STABLE   → ThrottleInterval: 10
├─ SOMEWHAT      → ThrottleInterval: 30
└─ UNSTABLE      → ThrottleInterval: 60

How critical is uptime?
├─ CRITICAL      → KeepAlive: true (restart always)
├─ IMPORTANT     → Crashed: true + SuccessfulExit: false
└─ DEVELOPMENT   → Crashed: true only
```

---

## ✅ Summary

**Current Setup (Default):**
- Restart on crash ✅
- Restart on error exit ✅
- 10-second throttle ✅

**Common Additions:**
1. **NetworkState** - Require internet (recommended)
2. **Daily restart** - Fresh start at 3 AM (good for memory)
3. **PathState** - File-based enable/disable (user control)

**Use the advanced plist template for full configuration options!**

**Files available:**
- `com.atlas.agent.plist` - Simple version (current)
- `com.atlas.agent.advanced.plist` - All options (template)
- `RESTART_TRIGGERS_GUIDE.md` - Detailed documentation
