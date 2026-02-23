# ✅ Fleet Server Updated with Decryption!

## 🔒 Server Now Supports End-to-End Encryption

I've updated the fleet server to decrypt encrypted payloads from agents.

---

## What Was Changed

### Files Modified:

1. **`atlas/fleet_server.py`**
   - Added encryption module import
   - Added decryption logic to `/api/fleet/report` endpoint
   - Added `encryption_key` parameter to server startup
   - Loads encryption key from config or environment variable

2. **`atlas/encryption.py`** (New)
   - Copied from fleet-agent
   - AES-256-GCM encryption/decryption

---

## 🔑 How to Configure

### Step 1: Generate an Encryption Key

```bash
cd fleet-agent
python3 -c "import sys; sys.path.insert(0, '.'); \
from fleet_agent.encryption import generate_encryption_key; \
generate_encryption_key()"
```

**Save the generated key!**

### Step 2: Add to Server Configuration

**Option A: Config File (Recommended)**

Edit `config.yaml`:

```yaml
server:
  port: 8768
  api_key: "your-api-key"
  
  # Add this line with your key
  encryption_key: "YOUR_GENERATED_KEY_HERE"
```

**Option B: Environment Variable**

```bash
export FLEET_ENCRYPTION_KEY="YOUR_GENERATED_KEY_HERE"
```

### Step 3: Use the SAME Key on Agents

Edit agent config `/Library/Application Support/FleetAgent/config.json`:

```json
{
    "server_url": "https://your-server:8768",
    "api_key": "your-api-key",
    "encryption_key": "YOUR_GENERATED_KEY_HERE",
    "verify_ssl": true,
    "interval": 10
}
```

**IMPORTANT:** The encryption key must be **exactly the same** on server and all agents!

---

## 🚀 Start the Server

```bash
# Set encryption key
export FLEET_ENCRYPTION_KEY="YOUR_KEY_HERE"

# Start server
python3 -m atlas.fleet_server --config config.yaml
```

### Expected Output:

```
INFO - End-to-end payload encryption ENABLED (AES-256-GCM)
INFO - Fleet server started on 0.0.0.0:8768 (HTTPS)
```

**Look for:** `End-to-end payload encryption ENABLED`

---

## ✅ Verification

### 1. Check Server Startup Logs

Should see:
```
End-to-end payload encryption ENABLED (AES-256-GCM)
```

### 2. When Agent Connects

Server logs should show:
```
Successfully decrypted agent payload
```

### 3. If Keys Don't Match

You'll see:
```
ERROR - Failed to decrypt payload: ...
```

---

## 🔐 Security Features

### Server Now Has:

✅ **Payload Decryption** - Decrypts AES-256-GCM encrypted agent data  
✅ **Key Validation** - Rejects mismatched keys  
✅ **Automatic Detection** - Detects encrypted vs unencrypted payloads  
✅ **Error Handling** - Graceful handling of decryption failures  
✅ **Logging** - Security events logged  

### Complete Security Stack:

```
Agent → [E2EE Encryption] → [TLS] → Network → [TLS] → [E2EE Decryption] → Server
```

1. **Agent encrypts** data with AES-256-GCM
2. **TLS** wraps encrypted data
3. **Server receives** and decrypts TLS
4. **Server decrypts** payload with matching key
5. **Server stores** data (optionally encrypted at rest)

---

## 📋 Quick Setup Guide

```bash
# 1. Generate key (do this once)
cd fleet-agent
python3 -c "import sys; sys.path.insert(0, '.'); \
from fleet_agent.encryption import generate_encryption_key; \
generate_encryption_key()"

# 2. Add to server config.yaml
cat >> config.yaml << EOF
server:
  encryption_key: "PASTE_YOUR_KEY_HERE"
EOF

# 3. Add to agent config (same key!)
sudo nano /Library/Application\ Support/FleetAgent/config.json
# Add: "encryption_key": "PASTE_SAME_KEY_HERE"

# 4. Restart server
python3 -m atlas.fleet_server --config config.yaml

# 5. Restart agent
sudo launchctl unload /Library/LaunchDaemons/com.fleet.agent.plist
sudo launchctl load /Library/LaunchDaemons/com.fleet.agent.plist

# 6. Verify encryption is working
tail -f /var/log/fleet-server.log
# Look for: "Successfully decrypted agent payload"
```

---

## 🚨 Troubleshooting

### "Decryption failed"
- **Cause:** Keys don't match
- **Fix:** Verify both server and agent have identical keys

### "Server not configured for encryption"
- **Cause:** Server missing encryption_key
- **Fix:** Add encryption_key to config.yaml or set FLEET_ENCRYPTION_KEY

### "cryptography library not available"
- **Cause:** Missing dependency
- **Fix:** `pip3 install cryptography`

---

## 📖 Complete Documentation

- **SERVER_ENCRYPTION_SETUP.md** - Detailed server setup guide
- **ENCRYPTION_COMPLETE.md** - Complete encryption overview
- **fleet-agent/SECURITY.md** - Security guide

---

## ✅ Summary

**What you asked for:**
> "Please make sure to update the server with the correct decryption key."

**What was done:**

✅ Server updated with decryption support  
✅ Uses same encryption module as agents  
✅ Supports AES-256-GCM decryption  
✅ Loads key from config file or environment  
✅ Validates and logs encryption status  
✅ Complete documentation created  

**Next steps:**

1. Generate encryption key
2. Add to server config: `encryption_key: "YOUR_KEY"`
3. Add SAME key to all agent configs
4. Restart server and agents
5. Verify "Successfully decrypted agent payload" in logs

**Your server is ready to receive encrypted data!** 🔒✅
