# 🔧 Fix: Machine Showing as Offline Despite Dashboard Updating

## Problem Summary

**Symptoms:**
- ✅ Dashboard for the Mac is updating (widget logs coming through)
- ❌ Machine shows as "offline" on Fleet Server

**Root Cause:**
The **FleetAgent** (which sends regular metric reports) was not running, only the **widget log collector** was active.

---

## ✅ Solution Implemented

I've updated `live_widgets.py` to automatically start the **FleetAgent** when a fleet server URL is provided.

**Changes Made:**
1. ✅ FleetAgent now starts automatically with live_widgets
2. ✅ Reports metrics every 10 seconds to Fleet Server
3. ✅ Keeps machine status as "online" with fresh `last_seen` timestamps

---

## 🔑 API Key Requirement

The Fleet Server requires API key authentication. When starting the agent on Sam's MacBook Air, you need to provide the API key.

### **Option 1: Export API Key as Environment Variable**

On the MacBook Air, before starting the agent:

```bash
# Set the API key (get this from the Fleet Server config)
export FLEET_API_KEY="your-api-key-here"

# Then start the agent
python3 start_atlas_agent.py \
  --fleet-server https://your-server:8768 \
  --machine-id "sams-Air"
```

---

### **Option 2: Pass API Key as Command Line Argument**

```bash
python3 start_atlas_agent.py \
  --fleet-server https://your-server:8768 \
  --machine-id "sams-Air" \
  --api-key "your-api-key-here"
```

---

### **Option 3: Disable API Key (Testing Only)**

For testing on localhost, you can run the server without API key:

```bash
# On server machine
python3 -m atlas.fleet_server --port 8768 --host 0.0.0.0
# (No --api-key parameter = no authentication required)
```

Then agents can connect without API keys.

---

## 📊 What Changed

### **Before:**
```
Widget Logs:  ✅ Sending (every 5 min)
Fleet Metrics: ❌ NOT sending  
Status: Shows as "offline" (no recent last_seen)
```

### **After (With Fix):**
```
Widget Logs:  ✅ Sending (every 5 min)  
Fleet Metrics: ✅ Sending (every 10 sec) ← NEW!
Status: Shows as "online" (fresh last_seen)
```

---

## 🔍 How to Verify It's Working

### **1. Check Agent Logs**

When the agent starts, you should see:

```
Fleet agent initialized for machine: sams-Air
Agent reporting loop started (interval: 10s)
Fleet agent started (reports every 10 seconds to https://...)
```

### **2. Check Server Database**

```bash
# On server machine
sqlite3 ~/.fleet-data/fleet_data.sqlite3 \
  "SELECT machine_id, datetime(last_seen, 'localtime') as last_seen \
   FROM machines ORDER BY last_seen DESC;"
```

Should show recent timestamp (within last 10-30 seconds).

### **3. Check Server API**

```bash
curl -k https://localhost:8768/api/fleet/machines
```

The machine should show `"status": "online"`.

---

## 🚨 Troubleshooting

### **Error: "Connection reset by peer"**

**Problem:** Agent can't connect to server (usually SSL/auth issue)

**Solutions:**

1. **Check API key is correct:**
   ```bash
   # On server, get the API key
   python3 get_api_key.py
   ```

2. **Check server is running and accepting connections:**
   ```bash
   curl -k https://server-ip:8768/api/fleet/machines
   ```

3. **Try HTTP instead of HTTPS (testing only):**
   ```bash
   # Use http:// instead of https://
   --fleet-server http://server-ip:8768
   ```

---

### **Error: "401 Unauthorized"**

**Problem:** API key missing or incorrect

**Solutions:**

1. **Pass API key with agent:**
   ```bash
   --api-key "your-api-key"
   ```

2. **Or set environment variable:**
   ```bash
   export FLEET_API_KEY="your-api-key"
   ```

3. **Or disable auth on server (testing only):**
   ```bash
   # Restart server without --api-key
   python3 -m atlas.fleet_server --port 8768
   ```

---

### **Machine Still Shows Offline**

**Problem:** Reports are sending but status not updating

**Check:**

1. **Verify machine_id matches:**
   ```bash
   # On agent machine
   hostname -s  # Should match machine_id in dashboard
   ```

2. **Check last_seen timestamp:**
   ```bash
   sqlite3 ~/.fleet-data/fleet_data.sqlite3 \
     "SELECT * FROM machines WHERE machine_id='sams-Air';"
   ```

3. **Restart agent with correct machine_id:**
   ```bash
   python3 start_atlas_agent.py \
     --machine-id "$(hostname -s)" \
     --fleet-server https://server:8768
   ```

---

## 📝 For Sam's MacBook Air

### **Quick Start Command:**

```bash
cd /path/to/windsurf-project-2

# Get API key from server (if configured)
# Or use one of the options below

# Option A: With API key
python3 start_atlas_agent.py \
  --fleet-server https://fleet-server-ip:8768 \
  --machine-id "sams-Air" \
  --api-key "YOUR_API_KEY_HERE"

# Option B: If server has no API key requirement
python3 start_atlas_agent.py \
  --fleet-server https://fleet-server-ip:8768 \
  --machine-id "sams-Air"
```

---

## ✅ Expected Behavior After Fix

1. **Agent starts and immediately begins reporting:**
   - First report within 1 second
   - Then every 10 seconds

2. **Machine status updates to "online":**
   - Within first 10 seconds of agent start
   - Stays "online" as long as agent running

3. **Both monitoring systems active:**
   - FleetAgent: Metrics every 10s (keeps status online)
   - Widget logs: Logs every 5 min (dashboard updates)

4. **Server health checks work:**
   - Server pings agent every 60s
   - Measures latency
   - Verifies bidirectional connectivity

---

## 🎯 Summary

**The fix ensures that when you start the agent with:**
```bash
python3 start_atlas_agent.py --fleet-server URL
```

**It now automatically starts:**
1. ✅ Live widget server (port 8767)
2. ✅ **FleetAgent** (reports metrics every 10s) ← **NEW!**
3. ✅ Widget log collector (sends logs every 5 min)
4. ✅ Menu bar icon (if not --no-menubar)
5. ✅ Speed test, ping, WiFi monitors

**Result:** Machine stays online as long as agent is running! 🎉

---

**Next Step:** Start the agent on Sam's MacBook Air with the correct API key and verify it shows as "online"!
