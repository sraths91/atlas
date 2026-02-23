# 🔄 Auto-Restart Trigger Parameters Guide

## 📋 Available Restart Triggers

macOS LaunchDaemons support multiple conditions that can trigger an auto-restart. Here's a complete guide to all available parameters.

---

## 🎯 Current Configuration

### **What's Currently Enabled:**

```xml
<key>KeepAlive</key>
<dict>
    <!-- Always keep alive -->
    <true/>
    
    <!-- Restart if exits with non-zero status -->
    <key>SuccessfulExit</key>
    <false/>
    
    <!-- Restart if crashes -->
    <key>Crashed</key>
    <true/>
</dict>

<key>ThrottleInterval</key>
<integer>10</integer>
```

**Current behavior:**
- ✅ Restart if process crashes (segfault, killed, etc.)
- ✅ Restart if process exits with error code
- ✅ Wait 10 seconds between restart attempts
- ✅ Keep trying to restart indefinitely

---

## 🔧 All Available Trigger Parameters

### **1. KeepAlive (Always Running)**

#### **Basic KeepAlive:**
```xml
<!-- Simple: Always restart no matter what -->
<key>KeepAlive</key>
<true/>
```

**Behavior:**
- Restarts on any exit (crash, normal exit, error)
- No conditions checked
- Most aggressive restart policy

---

#### **Conditional KeepAlive:**
```xml
<key>KeepAlive</key>
<dict>
    <!-- Multiple conditions can be combined -->
</dict>
```

---

### **2. Crashed (Process Crashed)**

```xml
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
</dict>
```

**Triggers restart when:**
- ✅ Segmentation fault (SIGSEGV)
- ✅ Bus error (SIGBUS)
- ✅ Abort signal (SIGABRT)
- ✅ Killed by system (SIGKILL)
- ✅ Uncaught exceptions
- ✅ Out of memory kills
- ❌ Normal exit (exit code 0)

**Use case:** Only restart on abnormal termination

---

### **3. SuccessfulExit (Exit Status)**

```xml
<key>KeepAlive</key>
<dict>
    <!-- Restart on error exits -->
    <key>SuccessfulExit</key>
    <false/>
</dict>
```

**When set to `false` (default):**
- ✅ Restart if exit code != 0 (error)
- ❌ Don't restart if exit code = 0 (success)

**When set to `true`:**
- ✅ Restart if exit code = 0 (success)
- ❌ Don't restart if exit code != 0 (error)

**Use case:** 
- `false` = Normal behavior (restart on errors)
- `true` = Unusual (restart only on clean exits)

---

### **4. NetworkState (Network Connectivity)**

```xml
<key>KeepAlive</key>
<dict>
    <key>NetworkState</key>
    <true/>
</dict>
```

**Triggers restart when:**
- ✅ Network interface goes down
- ✅ Network becomes available again
- ✅ Network configuration changes
- ✅ WiFi connects/disconnects

**Use case:** Services that require network connectivity

**Example:**
```xml
<!-- Restart when network is available -->
<key>KeepAlive</key>
<dict>
    <key>NetworkState</key>
    <true/>
</dict>
```

---

### **5. PathState (File/Directory Monitoring)**

```xml
<key>KeepAlive</key>
<dict>
    <key>PathState</key>
    <dict>
        <key>/path/to/file</key>
        <true/>  <!-- Restart when file exists -->
    </dict>
</dict>
```

**Triggers restart based on file existence:**

**When value is `true`:**
- ✅ Restart when file/directory **exists**
- ❌ Stop when file/directory is **deleted**

**When value is `false`:**
- ✅ Restart when file/directory is **deleted**
- ❌ Stop when file/directory **exists**

**Use case:** Conditional startup based on configuration files

**Example:**
```xml
<!-- Only run when config file exists -->
<key>KeepAlive</key>
<dict>
    <key>PathState</key>
    <dict>
        <key>/Users/samraths/.atlas/config.json</key>
        <true/>
    </dict>
</dict>
```

---

### **6. OtherJobEnabled (Dependency on Other Services)**

```xml
<key>KeepAlive</key>
<dict>
    <key>OtherJobEnabled</key>
    <dict>
        <key>com.example.other.service</key>
        <true/>  <!-- Restart when other service is running -->
    </dict>
</dict>
```

**Triggers restart based on other service state:**

**When value is `true`:**
- ✅ Restart when other service is **running**
- ❌ Stop when other service is **stopped**

**When value is `false`:**
- ✅ Restart when other service is **stopped**
- ❌ Stop when other service is **running**

**Use case:** Service dependencies

**Example:**
```xml
<!-- Only run when Fleet Server is running -->
<key>KeepAlive</key>
<dict>
    <key>OtherJobEnabled</key>
    <dict>
        <key>com.fleet.server</key>
        <true/>
    </dict>
</dict>
```

---

### **7. Combining Multiple Conditions**

```xml
<key>KeepAlive</key>
<dict>
    <!-- Restart on crash -->
    <key>Crashed</key>
    <true/>
    
    <!-- Restart on error exit -->
    <key>SuccessfulExit</key>
    <false/>
    
    <!-- Only when network is available -->
    <key>NetworkState</key>
    <true/>
    
    <!-- Only when config exists -->
    <key>PathState</key>
    <dict>
        <key>/Users/samraths/.atlas/enabled</key>
        <true/>
    </dict>
</dict>
```

**All conditions are AND logic:**
- Service runs when **ALL** conditions are met
- Service stops when **ANY** condition fails
- Service restarts when conditions become true again

---

## ⏱️ Restart Timing Parameters

### **1. ThrottleInterval (Restart Delay)**

```xml
<key>ThrottleInterval</key>
<integer>10</integer>
```

**Controls:**
- Minimum seconds between restart attempts
- Prevents rapid restart loops
- Gives time for issues to resolve

**Recommended values:**
- `5` = Fast restart (aggressive)
- `10` = Default (balanced)
- `30` = Slow restart (conservative)
- `60` = Very slow (for problematic services)

---

### **2. ExitTimeOut (Shutdown Timeout)**

```xml
<key>ExitTimeOut</key>
<integer>30</integer>
```

**Controls:**
- How long to wait for graceful shutdown
- SIGTERM sent first
- SIGKILL sent after timeout

**Recommended values:**
- `10` = Quick shutdown
- `30` = Default (gives time to save state)
- `60` = Slow shutdown (complex cleanup)

---

### **3. StartInterval (Periodic Restart)**

```xml
<key>StartInterval</key>
<integer>3600</integer>
```

**Controls:**
- Restart every N seconds regardless of status
- Forces fresh start periodically
- Good for memory leak prevention

**Example:**
```xml
<!-- Restart every hour -->
<key>StartInterval</key>
<integer>3600</integer>
```

**Use case:** Services with memory leaks or that need periodic refresh

---

### **4. StartCalendarInterval (Scheduled Restart)**

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

**Controls:**
- Restart at specific times
- Cron-like scheduling
- Can specify: Minute, Hour, Day, Weekday, Month

**Example - Daily restart at 3 AM:**
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

**Example - Every Sunday at midnight:**
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Weekday</key>
    <integer>0</integer>  <!-- 0 = Sunday -->
    <key>Hour</key>
    <integer>0</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

---

## 🎛️ Recommended Configurations

### **Configuration 1: Production (Bulletproof)**

```xml
<key>KeepAlive</key>
<dict>
    <!-- Restart on crash -->
    <key>Crashed</key>
    <true/>
    
    <!-- Restart on error exit -->
    <key>SuccessfulExit</key>
    <false/>
    
    <!-- Require network -->
    <key>NetworkState</key>
    <true/>
</dict>

<!-- Wait 10 seconds between restarts -->
<key>ThrottleInterval</key>
<integer>10</integer>

<!-- Graceful shutdown timeout -->
<key>ExitTimeOut</key>
<integer>30</integer>

<!-- Daily restart at 3 AM for fresh start -->
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

**Behavior:**
- ✅ Restarts on any crash or error
- ✅ Only runs when network available
- ✅ 10-second cooldown between restarts
- ✅ Daily fresh restart at 3 AM

---

### **Configuration 2: Development (Fast Iteration)**

```xml
<key>KeepAlive</key>
<dict>
    <!-- Restart on crash only -->
    <key>Crashed</key>
    <true/>
</dict>

<!-- Fast restart -->
<key>ThrottleInterval</key>
<integer>3</integer>

<!-- Quick shutdown -->
<key>ExitTimeOut</key>
<integer>10</integer>
```

**Behavior:**
- ✅ Restarts only on crashes (not normal exits)
- ✅ Quick 3-second restart
- ✅ Fast shutdown for development

---

### **Configuration 3: Conservative (Stable)**

```xml
<key>KeepAlive</key>
<dict>
    <!-- Restart on crash -->
    <key>Crashed</key>
    <true/>
    
    <!-- Only when config exists -->
    <key>PathState</key>
    <dict>
        <key>/Users/samraths/.atlas/enabled</key>
        <true/>
    </dict>
</dict>

<!-- Slow restart to prevent loops -->
<key>ThrottleInterval</key>
<integer>30</integer>

<!-- Restart once per hour for fresh state -->
<key>StartInterval</key>
<integer>3600</integer>
```

**Behavior:**
- ✅ Only runs when "enabled" file exists
- ✅ 30-second cooldown (prevents rapid loops)
- ✅ Hourly restart for memory management

---

### **Configuration 4: Network-Dependent**

```xml
<key>KeepAlive</key>
<dict>
    <!-- Always restart -->
    <key>Crashed</key>
    <true/>
    
    <!-- Require network -->
    <key>NetworkState</key>
    <true/>
    
    <!-- Depend on Fleet Server -->
    <key>OtherJobEnabled</key>
    <dict>
        <key>com.fleet.server</key>
        <true/>
    </dict>
</dict>

<key>ThrottleInterval</key>
<integer>15</integer>
```

**Behavior:**
- ✅ Only runs when network available
- ✅ Only runs when Fleet Server is running
- ✅ Restarts when either condition changes

---

### **Configuration 5: Scheduled Maintenance**

```xml
<key>KeepAlive</key>
<true/>

<!-- Restart every 6 hours -->
<key>StartInterval</key>
<integer>21600</integer>

<!-- Also restart daily at 3 AM -->
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>

<key>ThrottleInterval</key>
<integer>10</integer>
```

**Behavior:**
- ✅ Always running
- ✅ Restarts every 6 hours
- ✅ Guaranteed restart at 3 AM
- ✅ Prevents memory leaks

---

## 🔍 Monitoring Restart Triggers

### **Check Why Service Restarted:**

```bash
# View logs
tail -100 /var/log/atlas-agent-error.log

# Check system logs for launchd
log show --predicate 'subsystem == "com.apple.launchd"' --last 1h | grep atlas

# Check exit codes
log show --predicate 'process == "Python"' --last 1h | grep "exit"
```

### **Track Restart Count:**

```bash
# Add to agent code (Python)
import os
import time

restart_count_file = '/tmp/atlas_restart_count'

if os.path.exists(restart_count_file):
    with open(restart_count_file, 'r') as f:
        count = int(f.read().strip()) + 1
else:
    count = 1

with open(restart_count_file, 'w') as f:
    f.write(str(count))

print(f"Agent started (restart #{count})")
```

---

## 🎯 Choosing the Right Configuration

### **Use Simple KeepAlive if:**
- ✅ Want maximum uptime
- ✅ Service is stable
- ✅ No special conditions needed

### **Use Crashed + SuccessfulExit if:**
- ✅ Want smart restart behavior
- ✅ Distinguish crashes from intentional exits
- ✅ Prevent unnecessary restarts

### **Add NetworkState if:**
- ✅ Service requires internet
- ✅ Want to save resources when offline
- ✅ Fleet integration is critical

### **Add PathState if:**
- ✅ Want manual enable/disable via file
- ✅ Conditional startup based on config
- ✅ Easy user control

### **Add StartInterval if:**
- ✅ Service has memory leaks
- ✅ Need periodic fresh start
- ✅ Long-running state cleanup

### **Add StartCalendarInterval if:**
- ✅ Want scheduled restarts
- ✅ Maintenance windows
- ✅ Daily log rotation

---

## 📝 Implementation Examples

### **Example 1: Add Network Dependency**

Edit `com.atlas.agent.plist`:

```xml
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
    
    <key>SuccessfulExit</key>
    <false/>
    
    <!-- ADD THIS -->
    <key>NetworkState</key>
    <true/>
</dict>
```

```bash
# Reload
sudo launchctl bootout system /Library/LaunchDaemons/com.atlas.agent.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.atlas.agent.plist
```

---

### **Example 2: Add Manual Enable/Disable File**

```xml
<key>KeepAlive</key>
<dict>
    <key>Crashed</key>
    <true/>
    
    <!-- ADD THIS -->
    <key>PathState</key>
    <dict>
        <key>/Users/samraths/.atlas/enabled</key>
        <true/>
    </dict>
</dict>
```

```bash
# Create enabled file
mkdir -p ~/.atlas
touch ~/.atlas/enabled

# Service will start

# To disable service:
rm ~/.atlas/enabled
# Service will stop within 10 seconds

# To enable again:
touch ~/.atlas/enabled
# Service will restart
```

---

### **Example 3: Add Daily Restart at 3 AM**

```xml
<!-- Add after KeepAlive section -->
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

```bash
# Reload
sudo launchctl bootout system /Library/LaunchDaemons/com.atlas.agent.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.atlas.agent.plist
```

---

### **Example 4: Add Periodic Restart Every 12 Hours**

```xml
<!-- Add after KeepAlive section -->
<key>StartInterval</key>
<integer>43200</integer>  <!-- 12 hours in seconds -->
```

---

## ✅ Summary

### **Current Setup:**
```
✅ Restart on crash
✅ Restart on error exit
✅ 10-second throttle
```

### **Available Additions:**
```
🔧 NetworkState - Require network
🔧 PathState - Manual enable/disable file
🔧 OtherJobEnabled - Depend on Fleet Server
🔧 StartInterval - Periodic restart
🔧 StartCalendarInterval - Scheduled restart
🔧 Custom throttle timing
```

### **Recommended for Atlas:**
```
✅ Keep current (Crashed + SuccessfulExit)
➕ Add NetworkState (require internet)
➕ Add daily restart at 3 AM (fresh start)
➕ Keep 10-second throttle
```

**To customize your triggers, edit the plist and reload the service!** 🔄✨
