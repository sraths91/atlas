# Multi-Tenant Fleet Dashboard Guide

## 🎯 Overview

This guide explains how different organizations can deploy their own isolated fleet dashboards with unique configurations, branding, and security.

**Perfect for:**
- MSPs managing multiple clients
- Organizations with separate departments
- Resellers providing monitoring services
- IT consultants managing different companies

---

## 🚀 Quick Start for Each Organization

### Step 1: Run Setup Wizard

Each organization runs the setup wizard once:

```bash
python3 -m atlas.fleet_config setup
```

**The wizard will ask for:**
- Organization name
- Contact email
- Server port (default: 8768)
- Report interval
- Dashboard title
- Primary color

**It will automatically:**
- Generate unique Organization ID
- Generate secure API key
- Save configuration to `~/.fleet-config.json`
- Create agent installation script

### Step 2: Start Your Fleet Server

```bash
# Using saved configuration
python3 -m atlas.fleet_server --config ~/.fleet-config.json

# Or specify custom config location
python3 -m atlas.fleet_server --config /path/to/my-org-config.json
```

### Step 3: Deploy Agents

Distribute the generated installation script to all machines:

```bash
# The wizard creates: install-agent-XXXXXXXX.sh
./install-agent-XXXXXXXX.sh
```

---

## 📋 Example: Three Different Organizations

### Organization A: "Acme Corp IT"

```bash
# 1. Setup
python3 -m atlas.fleet_config setup
# Enter: Acme Corp IT, port 8768, green theme

# 2. Start server
python3 -m atlas.fleet_server --config ~/.fleet-config.json

# 3. Deploy agents with generated script
# Dashboard: http://acme-server:8768/dashboard
```

### Organization B: "Beta Systems"

```bash
# 1. Setup with different config file
python3 -m atlas.fleet_config setup
# Save to: ~/.fleet-config-beta.json
# Enter: Beta Systems, port 8769, blue theme

# 2. Start server on different port
python3 -m atlas.fleet_server --config ~/.fleet-config-beta.json

# 3. Deploy agents with their unique script
# Dashboard: http://beta-server:8769/dashboard
```

### Organization C: "Gamma Networks"

```bash
# 1. Setup
python3 -m atlas.fleet_config setup
# Save to: ~/.fleet-config-gamma.json
# Enter: Gamma Networks, port 8770, purple theme

# 2. Start server
python3 -m atlas.fleet_server --config ~/.fleet-config-gamma.json

# 3. Deploy agents
# Dashboard: http://gamma-server:8770/dashboard
```

---

## 🔐 Security & Isolation

### Each Organization Gets:

1. **Unique Organization ID**
   - UUID-based identifier
   - Prevents cross-contamination
   - Used in LaunchAgent labels

2. **Unique API Key**
   - 32-byte secure token
   - Required for agent authentication
   - Agents can only report to their server

3. **Separate Configuration**
   - Independent settings
   - Custom branding
   - Different alert thresholds

4. **Isolated Data**
   - Each server stores its own data
   - No shared database
   - Complete data separation

---

## 📁 Configuration File Structure

### Server Configuration (`~/.fleet-config.json`)

```json
{
  "organization": {
    "name": "Acme Corp IT",
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "contact": "admin@acme.com"
  },
  "server": {
    "port": 8768,
    "host": "0.0.0.0",
    "api_key": "secure-generated-key-here",
    "history_size": 1000
  },
  "agent": {
    "report_interval": 10,
    "retry_interval": 30,
    "timeout": 5
  },
  "branding": {
    "primary_color": "#00ff00",
    "secondary_color": "#0a0a0a",
    "logo_url": null,
    "dashboard_title": "Acme Fleet Dashboard"
  },
  "alerts": {
    "cpu_threshold": 90,
    "memory_threshold": 90,
    "disk_threshold": 90,
    "enabled": true
  }
}
```

### Agent Configuration (Auto-generated)

```json
{
  "server_url": "http://fleet.acme.com:8768",
  "organization_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "api_key": "secure-generated-key-here",
  "report_interval": 10
}
```

---

## 🎨 Customization Options

### Branding

```bash
# Edit your config file
nano ~/.fleet-config.json
```

```json
{
  "branding": {
    "primary_color": "#ff6b35",
    "secondary_color": "#1a1a2e",
    "dashboard_title": "My Custom Dashboard",
    "logo_url": "https://mycompany.com/logo.png"
  }
}
```

### Alert Thresholds

```json
{
  "alerts": {
    "cpu_threshold": 85,
    "memory_threshold": 95,
    "disk_threshold": 80,
    "enabled": true
  }
}
```

### Reporting Intervals

```json
{
  "agent": {
    "report_interval": 15,
    "retry_interval": 45,
    "timeout": 10
  }
}
```

---

## 🚀 Deployment Scenarios

### Scenario 1: MSP with Multiple Clients

```bash
# Client A
python3 -m atlas.fleet_server \
  --config /etc/fleet/client-a.json \
  --port 8768

# Client B
python3 -m atlas.fleet_server \
  --config /etc/fleet/client-b.json \
  --port 8769

# Client C
python3 -m atlas.fleet_server \
  --config /etc/fleet/client-c.json \
  --port 8770
```

### Scenario 2: Different Departments

```bash
# IT Department
python3 -m atlas.fleet_server \
  --config /opt/fleet/it-dept.json

# Engineering Department
python3 -m atlas.fleet_server \
  --config /opt/fleet/eng-dept.json

# Sales Department
python3 -m atlas.fleet_server \
  --config /opt/fleet/sales-dept.json
```

### Scenario 3: Multi-Region

```bash
# US Region
python3 -m atlas.fleet_server \
  --config /etc/fleet/us-region.json

# EU Region
python3 -m atlas.fleet_server \
  --config /etc/fleet/eu-region.json

# APAC Region
python3 -m atlas.fleet_server \
  --config /etc/fleet/apac-region.json
```

---

## 📦 Agent Installation Methods

### Method 1: Generated Script (Recommended)

The setup wizard creates a complete installation script:

```bash
# Run on each Mac
./install-agent-XXXXXXXX.sh
```

**What it does:**
- Checks Python installation
- Installs dependencies
- Creates config directory
- Saves agent configuration
- Creates LaunchAgent plist
- Starts agent automatically

### Method 2: Manual with Config File

```bash
# 1. Export agent config
python3 -m atlas.fleet_config export-agent \
  --server http://fleet.company.com:8768 \
  --output agent-config.json

# 2. Copy to target machine
scp agent-config.json user@mac:~/.fleet-agent/config.json

# 3. Start agent
python3 -m atlas.fleet_agent \
  --config ~/.fleet-agent/config.json
```

### Method 3: Command Line

```bash
python3 -m atlas.fleet_agent \
  --server http://fleet.company.com:8768 \
  --api-key "your-api-key-here" \
  --interval 10
```

### Method 4: Jamf Pro Policy

Create a policy with the generated installation script:

1. Upload script to Jamf Pro
2. Create policy targeting scope
3. Set to run at check-in
4. Deploy to machines

---

## 🔧 Configuration Management

### View Current Configuration

```bash
python3 -m atlas.fleet_config
```

### Update Configuration

```bash
# Edit the file
nano ~/.fleet-config.json

# Restart server to apply changes
pkill -f fleet_server
python3 -m atlas.fleet_server --config ~/.fleet-config.json
```

### Export Agent Configuration

```bash
python3 << EOF
from atlas.fleet_config import FleetConfig

config = FleetConfig()
config.export_agent_config_file(
    server_url='http://your-server:8768',
    output_path='agent-config.json'
)
EOF
```

### Generate New API Key

```bash
python3 << EOF
from atlas.fleet_config import FleetConfig

config = FleetConfig()
new_key = config.generate_api_key()
config.save()
print(f"New API key: {new_key}")
print("Remember to update all agents with the new key!")
EOF
```

---

## 🔍 Verification & Testing

### Test Server Configuration

```bash
# Check if server is running
curl http://localhost:8768/api/fleet/summary

# Expected response:
# {"total_machines": 0, "online": 0, ...}
```

### Test Agent Configuration

```bash
# Dry run (doesn't start agent)
python3 -m atlas.fleet_agent \
  --config ~/.fleet-agent/config.json \
  --debug

# Check connectivity
curl -X POST http://your-server:8768/api/fleet/report \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"machine_id":"test","machine_info":{},"metrics":{}}'
```

### Verify Isolation

```bash
# Try to connect agent with wrong API key (should fail)
python3 -m atlas.fleet_agent \
  --server http://server:8768 \
  --api-key "wrong-key"

# Expected: 401 Unauthorized
```

---

## 📊 Monitoring Multiple Dashboards

### Dashboard URLs

Each organization has their own dashboard:

```
Organization A: http://server-a:8768/dashboard
Organization B: http://server-b:8769/dashboard
Organization C: http://server-c:8770/dashboard
```

### Unified View (Optional)

Create a simple HTML page linking to all dashboards:

```html
<!DOCTYPE html>
<html>
<head>
    <title>All Fleet Dashboards</title>
</head>
<body>
    <h1>Fleet Dashboards</h1>
    <ul>
        <li><a href="http://server-a:8768/dashboard">Acme Corp</a></li>
        <li><a href="http://server-b:8769/dashboard">Beta Systems</a></li>
        <li><a href="http://server-c:8770/dashboard">Gamma Networks</a></li>
    </ul>
</body>
</html>
```

---

## 🛠️ Troubleshooting

### Problem: Agents connecting to wrong server

**Solution:** Check agent configuration
```bash
cat ~/.fleet-agent/config.json
# Verify server_url and organization_id
```

### Problem: API key mismatch

**Solution:** Regenerate and redistribute
```bash
# On server
python3 -m atlas.fleet_config
# Note the API key

# Update agent config
nano ~/.fleet-agent/config.json
# Update api_key field
```

### Problem: Port conflicts

**Solution:** Use different ports per organization
```json
{
  "server": {
    "port": 8768  // Change to 8769, 8770, etc.
  }
}
```

---

## 📝 Best Practices

1. **Use Unique Ports** - Avoid conflicts between organizations
2. **Secure API Keys** - Never commit to version control
3. **Regular Backups** - Save configuration files
4. **Document Setup** - Keep notes on each deployment
5. **Test First** - Verify with 1-2 agents before full rollout
6. **Monitor Logs** - Check for authentication errors
7. **Update Together** - Keep server and agents in sync
8. **Use DNS Names** - Easier than IP addresses

---

## 🎯 Quick Reference

### Setup New Organization
```bash
python3 -m atlas.fleet_config setup
```

### Start Server
```bash
python3 -m atlas.fleet_server --config ~/.fleet-config.json
```

### Deploy Agent
```bash
./install-agent-XXXXXXXX.sh
```

### View Configuration
```bash
python3 -m atlas.fleet_config
```

### Check Server Status
```bash
curl http://localhost:8768/api/fleet/summary
```

---

## 📞 Support

- **Configuration Issues**: Check `~/.fleet-config.json`
- **Agent Issues**: Check `~/Library/Logs/fleet-agent.log`
- **Server Issues**: Check server console output
- **API Issues**: Verify API keys match

---

## ✅ Deployment Checklist

Per Organization:

- [ ] Run setup wizard
- [ ] Save configuration file
- [ ] Start fleet server
- [ ] Verify server accessible
- [ ] Generate agent installer
- [ ] Test with 1 agent
- [ ] Deploy to pilot group
- [ ] Monitor for issues
- [ ] Roll out to all machines
- [ ] Document configuration
- [ ] Set up monitoring
- [ ] Train administrators

---

## 🎉 Success!

Each organization now has:
- ✅ Isolated fleet dashboard
- ✅ Unique credentials
- ✅ Custom branding
- ✅ Independent configuration
- ✅ Secure agent communication
- ✅ Easy deployment process

No cross-contamination, no shared data, complete independence! 🚀
