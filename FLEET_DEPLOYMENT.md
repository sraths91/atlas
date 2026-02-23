# Fleet Dashboard Deployment Guide

## 🎯 Overview

The Fleet Dashboard allows you to monitor multiple Macs from a single central dashboard. Perfect for IT administrators managing fleets of machines.

**Architecture:**
- **Central Server**: Collects and displays data from all machines
- **Agents**: Run on each Mac, report metrics to central server
- **Dashboard**: Web interface showing fleet status

---

## 🚀 Quick Start (5 Minutes)

### 1. Start the Central Server

On your monitoring machine (or dedicated server):

```bash
# Start fleet server
python3 -m atlas.fleet_server --port 8768

# Or with API key authentication
python3 -m atlas.fleet_server --port 8768 --api-key "your-secret-key"
```

**Access Dashboard:** http://localhost:8768/dashboard

### 2. Deploy Agents to Macs

On each Mac you want to monitor:

```bash
# Install dependencies
pip3 install psutil requests

# Start agent (replace SERVER_IP with your server's IP)
python3 -m atlas.fleet_agent \
    --server http://SERVER_IP:8768 \
    --interval 10

# With API key
python3 -m atlas.fleet_agent \
    --server http://SERVER_IP:8768 \
    --api-key "your-secret-key" \
    --interval 10
```

### 3. View Fleet Dashboard

Open http://SERVER_IP:8768/dashboard in your browser!

---

## 📊 What You'll See

### Fleet Summary
- **Total Machines**: Count of all registered machines
- **Online**: Currently reporting machines
- **Warning**: Machines with delayed reports
- **Offline**: Machines not reporting
- **Average Metrics**: Fleet-wide CPU, Memory, Disk usage

### Machine Cards
Each machine shows:
- Hostname and status (online/warning/offline)
- OS version and hardware specs
- Real-time CPU, Memory, Disk usage
- Visual progress bars with color coding
- Click for detailed view

### Active Alerts
Automatic alerts for:
- CPU usage > 90%
- Memory usage > 90%
- Disk usage > 90%

---

## 🔧 Deployment Options

### Option 1: Dedicated Server (Recommended)

**Best for:** Production environments, large fleets

```bash
# On dedicated server (Linux/Mac)
# 1. Install Python 3.9+
# 2. Install dependencies
pip3 install psutil requests

# 3. Create systemd service (Linux)
sudo nano /etc/systemd/system/fleet-server.service
```

```ini
[Unit]
Description=Atlas Fleet Server
After=network.target

[Service]
Type=simple
User=fleet
WorkingDirectory=/opt/atlas
ExecStart=/usr/bin/python3 -m atlas.fleet_server --port 8768 --api-key YOUR_API_KEY
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable fleet-server
sudo systemctl start fleet-server
```

### Option 2: Docker Container

**Best for:** Easy deployment, portability

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY atlas /app/atlas
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8768

CMD ["python", "-m", "atlas.fleet_server", "--port", "8768"]
```

```bash
# Build and run
docker build -t fleet-server .
docker run -d -p 8768:8768 --name fleet-server fleet-server
```

### Option 3: Jamf Pro Integration

**Best for:** Existing Jamf environments

See `JAMF_FLEET_DEPLOYMENT.md` for detailed instructions.

---

## 🖥️ Agent Deployment

### Manual Deployment

```bash
# On each Mac
python3 -m atlas.fleet_agent \
    --server http://fleet-server.company.com:8768 \
    --machine-id "$(hostname)" \
    --api-key "your-secret-key" \
    --interval 10
```

### LaunchAgent (Auto-start on Mac)

Create `/Library/LaunchAgents/com.company.fleet-agent.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.company.fleet-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>atlas.fleet_agent</string>
        <string>--server</string>
        <string>http://fleet-server.company.com:8768</string>
        <string>--api-key</string>
        <string>your-secret-key</string>
        <string>--interval</string>
        <string>10</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/fleet-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/fleet-agent.error.log</string>
</dict>
</plist>
```

```bash
# Load agent
sudo launchctl load /Library/LaunchAgents/com.company.fleet-agent.plist
```

### Jamf Pro Policy

1. Package the agent with dependencies
2. Create policy with script:

```bash
#!/bin/bash

SERVER_URL="http://fleet-server.company.com:8768"
API_KEY="your-secret-key"

# Install agent
python3 -m atlas.fleet_agent \
    --server "$SERVER_URL" \
    --api-key "$API_KEY" \
    --interval 10 &

echo "Fleet agent started"
```

---

## 🔒 Security

### API Key Authentication

```bash
# Generate secure API key
API_KEY=$(openssl rand -hex 32)

# Start server with API key
python3 -m atlas.fleet_server --api-key "$API_KEY"

# Configure agents with same key
python3 -m atlas.fleet_agent --server http://server:8768 --api-key "$API_KEY"
```

### Firewall Configuration

```bash
# Allow fleet server port (Linux)
sudo ufw allow 8768/tcp

# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
```

### HTTPS/TLS

Use reverse proxy (nginx/Apache) for HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name fleet.company.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8768;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📈 Scaling

### Performance Guidelines

| Machines | Server Specs | Update Interval |
|----------|--------------|-----------------|
| 1-50 | 1 CPU, 512MB RAM | 10s |
| 50-200 | 2 CPU, 1GB RAM | 15s |
| 200-500 | 4 CPU, 2GB RAM | 30s |
| 500+ | 8 CPU, 4GB RAM | 60s |

### Database Backend (Optional)

For large fleets (>100 machines), consider adding persistent storage:

```python
# Use PostgreSQL/MySQL instead of in-memory storage
# See FLEET_DATABASE.md for configuration
```

---

## 🔍 Monitoring & Alerts

### Server Health Check

```bash
# Check if server is running
curl http://localhost:8768/api/fleet/summary

# Expected response:
# {"total_machines": 10, "online": 9, ...}
```

### Agent Health Check

```bash
# On agent machine
ps aux | grep fleet_agent

# Check logs
tail -f /var/log/fleet-agent.log
```

### Integration with Monitoring Tools

**Prometheus:**
```yaml
scrape_configs:
  - job_name: 'fleet'
    static_configs:
      - targets: ['localhost:8768']
```

**Grafana:**
- Import dashboard from `grafana-dashboard.json`
- Configure data source pointing to fleet server

---

## 🛠️ Troubleshooting

### Agent Can't Connect to Server

```bash
# Test connectivity
curl http://SERVER_IP:8768/api/fleet/summary

# Check firewall
telnet SERVER_IP 8768

# Check agent logs
tail -f /var/log/fleet-agent.error.log
```

### Machines Showing Offline

- Check agent is running: `ps aux | grep fleet_agent`
- Verify network connectivity
- Check server logs for errors
- Ensure API keys match

### High Server CPU Usage

- Increase agent reporting interval
- Reduce metrics history size
- Add database backend
- Scale horizontally (multiple servers)

---

## 📊 API Reference

### GET /api/fleet/machines
Returns list of all machines

```json
{
  "machines": [
    {
      "machine_id": "MacBook-Pro",
      "status": "online",
      "info": {...},
      "latest_metrics": {...}
    }
  ]
}
```

### GET /api/fleet/summary
Returns fleet summary

```json
{
  "total_machines": 10,
  "online": 9,
  "warning": 1,
  "offline": 0,
  "avg_cpu": 45.2,
  "avg_memory": 62.8,
  "alerts": [...]
}
```

### POST /api/fleet/report
Agent endpoint for reporting metrics

```json
{
  "machine_id": "MacBook-Pro",
  "machine_info": {...},
  "metrics": {...}
}
```

---

## 🎯 Best Practices

1. **Use API Keys** in production
2. **Set appropriate intervals** (10-30s for most cases)
3. **Monitor server resources** as fleet grows
4. **Set up alerts** for critical thresholds
5. **Regular backups** of configuration
6. **Use HTTPS** for external access
7. **Implement log rotation** for agents
8. **Test failover** scenarios

---

## 📝 Example Configurations

### Small Office (10-20 Macs)
```bash
# Server: Any Mac/Linux machine
# Interval: 10 seconds
# No database needed
python3 -m atlas.fleet_server --port 8768
```

### Medium Enterprise (50-200 Macs)
```bash
# Server: Dedicated VM (2 CPU, 2GB RAM)
# Interval: 15 seconds
# Consider database for history
# Use API key authentication
python3 -m atlas.fleet_server --port 8768 --api-key "$(cat /etc/fleet-key)"
```

### Large Enterprise (500+ Macs)
```bash
# Server: Dedicated server (8 CPU, 8GB RAM)
# Interval: 30-60 seconds
# Database required
# Load balancer for redundancy
# Integration with existing monitoring
```

---

## 🚀 Next Steps

1. **Deploy server** on dedicated machine
2. **Test with 1-2 agents** first
3. **Verify dashboard** shows data
4. **Roll out to pilot group** (10-20 machines)
5. **Monitor performance** and adjust intervals
6. **Deploy fleet-wide** via Jamf/MDM
7. **Set up alerts** and monitoring
8. **Train team** on dashboard usage

---

## 📞 Support

- **Documentation**: See `README.md`
- **Troubleshooting**: See above section
- **API Docs**: See API Reference section
- **Examples**: See `examples/` directory

---

## ✅ Deployment Checklist

- [ ] Server deployed and accessible
- [ ] API key generated (if using auth)
- [ ] Firewall rules configured
- [ ] Test agent connected successfully
- [ ] Dashboard accessible
- [ ] Metrics displaying correctly
- [ ] Alerts configured
- [ ] Monitoring set up
- [ ] Documentation shared with team
- [ ] Backup/recovery plan in place
