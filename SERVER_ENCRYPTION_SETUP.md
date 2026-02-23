# ✅ Server Encryption Configuration

## 🔒 Setting Up End-to-End Encryption on the Fleet Server

The fleet server has been updated to decrypt encrypted payloads from agents. Here's how to configure it:

---

## 🔑 Step 1: Use the Same Encryption Key

The server must use the **exact same encryption key** as your agents.

### Generate the Key (if you haven't already):

```bash
cd fleet-agent
python3 -c "import sys; sys.path.insert(0, '.'); \
from fleet_agent.encryption import generate_encryption_key; \
generate_encryption_key()"
```

**Example output:**
```
Key: q1BNznn+XQ8lJr5Cf/lMg8yoLsNxxp+XvZp/xLJ0VMY=
```

**Save this key!** You'll need it for both the server and all agents.

---

## 📝 Step 2: Configure the Server

### Method 1: Environment Variable (Recommended)

```bash
export FLEET_ENCRYPTION_KEY="q1BNznn+XQ8lJr5Cf/lMg8yoLsNxxp+XvZp/xLJ0VMY="

# Then start the server
python3 -m atlas.fleet_server --config config.yaml
```

### Method 2: Configuration File

Create or edit your `config.yaml`:

```yaml
organization:
  name: "Your Organization"

server:
  port: 8768
  host: "0.0.0.0"
  api_key: "your-api-key-here"
  
  # Add this line with your encryption key
  encryption_key: "q1BNznn+XQ8lJr5Cf/lMg8yoLsNxxp+XvZp/xLJ0VMY="
  
  # Optional: Database encryption (different from payload encryption)
  db_encryption_key: "different-key-for-database"
  
  # Database settings
  db_path: "~/.fleet-data/fleet_data.sqlite3"
  history_size: 1000
  history_retention_days: 30
  
  # Web UI authentication
  web_username: "admin"
  web_password: "your-secure-password"

ssl:
  # Optional: HTTPS configuration
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/key.pem"
```

### Method 3: Command Line (Not Recommended - key visible in process list)

```bash
python3 -m atlas.fleet_server \
    --port 8768 \
    --api-key your-api-key \
    --config config.yaml
    
# Note: Command-line doesn't support encryption_key parameter yet
# Use config file or environment variable instead
```

---

## 🚀 Step 3: Start the Server

```bash
# Make sure encryption key is set
export FLEET_ENCRYPTION_KEY="q1BNznn+XQ8lJr5Cf/lMg8yoLsNxxp+XvZp/xLJ0VMY="

# Start the server
python3 -m atlas.fleet_server --config config.yaml
```

### Expected Output:

```
2024-11-25 11:40:00 - atlas.fleet_server - INFO - End-to-end payload encryption ENABLED (AES-256-GCM)
2024-11-25 11:40:00 - atlas.fleet_server - INFO - Starting fleet server for: Your Organization
2024-11-25 11:40:00 - atlas.fleet_server - INFO - Using persistent data store at: ~/.fleet-data/fleet_data.sqlite3
2024-11-25 11:40:00 - atlas.fleet_server - INFO - Fleet server started on 0.0.0.0:8768 (HTTPS)
2024-11-25 11:40:00 - atlas.fleet_server - INFO - SSL/TLS enabled with certificate: /path/to/cert.pem
2024-11-25 11:40:00 - atlas.fleet_server - INFO - API key authentication enabled (for agents)
2024-11-25 11:40:00 - atlas.fleet_server - INFO - Web authentication enabled (username: admin)
```

**Look for:** `End-to-end payload encryption ENABLED (AES-256-GCM)`

---

## ⚠️ Important Notes

### 1. **Same Key for All**
- The encryption key must be **identical** on:
  - The server
  - All agents

### 2. **Two Types of Encryption**
Don't confuse these two different encryption keys:

| Type | Config Key | Purpose |
|------|-----------|---------|
| **Payload Encryption** | `encryption_key` | Encrypts data in transit (E2EE) |
| **Database Encryption** | `db_encryption_key` | Encrypts stored data at rest |

**You need BOTH for maximum security!**

### 3. **Key Storage Security**
- ✅ Store in environment variables
- ✅ Store in protected config files (chmod 600)
- ✅ Use secret management systems (Vault, etc.)
- ❌ Don't commit keys to git
- ❌ Don't share keys via email
- ❌ Don't log keys

---

## 🔍 Verification

### Check Server Logs:

```bash
# Look for this line
grep "End-to-end payload encryption ENABLED" /var/log/fleet-server.log
```

### Test with Agent:

1. Configure an agent with the encryption key
2. Start the agent
3. Check server logs for:
   ```
   Successfully decrypted agent payload
   ```

4. If you see errors like:
   ```
   Failed to decrypt payload
   ```
   Then the keys don't match!

---

## 🛠️ Example Complete Setup

### Server Configuration (`config.yaml`):

```yaml
organization:
  name: "Acme Corporation"

server:
  port: 8768
  host: "0.0.0.0"
  
  # Agent authentication
  api_key: "fleet-api-key-abc123xyz789"
  
  # End-to-end encryption (SAME as agents)
  encryption_key: "q1BNznn+XQ8lJr5Cf/lMg8yoLsNxxp+XvZp/xLJ0VMY="
  
  # Database encryption (different key)
  db_encryption_key: "database-encryption-key-different"
  
  # Storage
  db_path: "~/.fleet-data/fleet_data.sqlite3"
  history_size: 10000
  history_retention_days: 90
  
  # Web UI
  web_username: "admin"
  web_password: "SecurePassword123!"

ssl:
  cert_file: "/etc/fleet/cert.pem"
  key_file: "/etc/fleet/key.pem"
```

### Agent Configuration (`/Library/Application Support/FleetAgent/config.json`):

```json
{
    "server_url": "https://fleet.company.com:8768",
    "api_key": "fleet-api-key-abc123xyz789",
    "encryption_key": "q1BNznn+XQ8lJr5Cf/lMg8yoLsNxxp+XvZp/xLJ0VMY=",
    "verify_ssl": true,
    "interval": 10,
    "machine_id": null
}
```

**Notice:** Same `api_key` and `encryption_key` on both!

---

## 🔄 What Happens

### When Agent Sends Data:

1. **Agent:** Collects metrics
2. **Agent:** Encrypts with AES-256-GCM using `encryption_key`
3. **Agent:** Sends encrypted payload over HTTPS
4. **Server:** Receives HTTPS request (TLS decryption)
5. **Server:** Detects `"encrypted": true` in payload
6. **Server:** Decrypts with matching `encryption_key`
7. **Server:** Processes decrypted data
8. **Server:** Stores in database (encrypted if `db_encryption_key` set)

### Security Layers:

```
┌─────────────────────────────────┐
│  Layer 3: Database Encryption   │ ← db_encryption_key
├─────────────────────────────────┤
│  Layer 2: Payload Encryption    │ ← encryption_key (E2EE)
├─────────────────────────────────┤
│  Layer 1: Transport (HTTPS/TLS) │ ← SSL cert/key
└─────────────────────────────────┘
```

---

## 🚨 Troubleshooting

### Error: "Decryption failed"

**Cause:** Keys don't match

**Solution:**
1. Verify server config has correct key
2. Verify agent config has correct key  
3. Ensure no whitespace/line breaks in keys
4. Restart both server and agent

### Error: "Server not configured for encryption"

**Cause:** Server doesn't have encryption_key configured

**Solution:**
1. Add `encryption_key` to server config
2. Or set `FLEET_ENCRYPTION_KEY` environment variable
3. Restart server

### Warning: "End-to-end payload encryption DISABLED"

**Cause:** Server started without encryption_key

**Solution:**
1. Check config file has `encryption_key` line
2. Check environment variable `FLEET_ENCRYPTION_KEY`
3. Restart server with key configured

### Agent Can't Connect

**Symptoms:** Agent logs show connection errors

**Check:**
1. Server URL correct in agent config
2. Server is running
3. API keys match
4. Firewall allows port 8768
5. SSL certificates valid (if using HTTPS)

---

## 📊 Configuration Priority

Settings are loaded in this order (last wins):

1. **Defaults** (hardcoded)
2. **Config file** (`config.yaml`)
3. **Environment variables** (`FLEET_*`)
4. **Command-line arguments** (for some settings)

### Example Priority:

```bash
# Config file has: encryption_key: "key-from-file"
# Environment has: FLEET_ENCRYPTION_KEY="key-from-env"

# Result: Uses "key-from-env" (environment wins)
```

---

## 🔐 Security Best Practices

### ✅ DO:
1. Use strong, random encryption keys (32+ bytes)
2. Use same key on server and all agents
3. Store keys securely (environment variables, secret managers)
4. Use HTTPS (not HTTP)
5. Rotate keys periodically (every 90 days)
6. Monitor logs for decryption failures
7. Use different keys for different purposes (payload vs database)

### ❌ DON'T:
1. Use weak or predictable keys
2. Commit keys to version control
3. Share keys via insecure channels
4. Reuse keys across environments
5. Log encryption keys
6. Use same key for payload and database encryption

---

## ✅ Checklist

Before going to production:

- [ ] Encryption key generated
- [ ] Same key configured on server and all agents
- [ ] Server shows "End-to-end payload encryption ENABLED"
- [ ] Agents successfully sending encrypted data
- [ ] Server logs show "Successfully decrypted agent payload"
- [ ] HTTPS enabled (not HTTP)
- [ ] SSL certificates valid
- [ ] API keys configured
- [ ] Web UI password set
- [ ] Database encryption enabled
- [ ] Keys stored securely (not in code/git)
- [ ] Key rotation schedule established
- [ ] Backup plan for keys documented

---

## 📖 Related Documentation

- **Agent Security:** `fleet-agent/SECURITY.md`
- **Agent Configuration:** `fleet-agent/README.md`
- **Encryption Implementation:** `ENCRYPTION_IMPLEMENTED.md`

---

## 🎉 Summary

**Server encryption configuration:**

1. **Generate key:** Run encryption key generator
2. **Configure server:** Add `encryption_key` to config.yaml
3. **Start server:** Server logs should show "ENABLED"
4. **Configure agents:** Use same key
5. **Test:** Verify encrypted communication works

**Your fleet server is now ready to receive encrypted data!** 🔒
