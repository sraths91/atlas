# 🚀 Cluster Mode - Quick Start Guide

## 5-Minute Setup

Get a 3-node high-availability cluster running in 5 minutes!

---

## Prerequisites

- 3 servers (or VMs)
- Redis server (or use Docker)
- Network filesystem or shared storage

---

## Step 1: Install Redis (1 minute)

```bash
# Using Docker (easiest)
docker run -d --name redis \
  -p 6379:6379 \
  redis:latest redis-server --requirepass YOUR_PASSWORD

# Or install natively
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis
redis-server --requirepass YOUR_PASSWORD &
```

---

## Step 2: Setup Shared Storage (1 minute)

### Option A: Simple Directory (Development)

```bash
# On each server, mount the same network share
sudo mkdir -p /mnt/fleet-cluster
# Then mount your network filesystem
```

### Option B: Just Use Redis (Recommended)

No shared filesystem needed! Redis handles everything.

---

## Step 3: Configure Nodes (2 minutes)

**Create `config.yaml` on each server:**

```yaml
server:
  port: 8768
  api_key: "test-api-key-123"
  web_username: "admin"
  web_password: "admin123"
  db_path: "/tmp/fleet_data.sqlite3"  # Or shared path

cluster:
  enabled: true
  backend: "redis"
  redis_host: "YOUR_REDIS_IP"
  redis_password: "YOUR_PASSWORD"

sessions:
  backend: "redis"
  redis:
    host: "YOUR_REDIS_IP"
    password: "YOUR_PASSWORD"
```

**Make sure:**
- Same `api_key` on all nodes
- Same `redis_host` and `redis_password`
- Same database path (if using shared filesystem)

---

## Step 4: Start Nodes (1 minute)

```bash
# On each server
cd fleet-server
python3 -m atlas.fleet_server --config config.yaml
```

**Expected output on each:**

```
✅ Cluster mode ENABLED (node: server-XX-abc123, backend: redis)
✅ Registered node in cluster: server-XX-abc123
✅ Fleet server started on 0.0.0.0:8768
```

---

## Step 5: Verify (30 seconds)

```bash
# Check cluster status from any node
curl http://localhost:8768/api/fleet/cluster/health

# Expected:
{"status": "healthy", "node_id": "server-01-abc123"}

# Login to dashboard
open http://localhost:8768/dashboard
# Login with admin/admin123
```

---

## ✅ You're Done!

Your 3-node cluster is now running!

**Test failover:**

```bash
# Kill one node
# Stop the process on server-02

# Dashboard still works!
open http://localhost:8768/dashboard
```

---

## 🎯 Next Steps

### Add Load Balancer

**Quick HAProxy setup:**

```bash
# Install HAProxy
sudo apt-get install haproxy

# Edit /etc/haproxy/haproxy.cfg
```

Add:

```haproxy
frontend fleet
    bind *:80
    default_backend nodes

backend nodes
    balance roundrobin
    option httpchk GET /api/fleet/cluster/health
    server node1 SERVER1_IP:8768 check
    server node2 SERVER2_IP:8768 check
    server node3 SERVER3_IP:8768 check
```

```bash
sudo systemctl restart haproxy
```

Access via load balancer:

```bash
open http://HAPROXY_IP/dashboard
```

---

## 🔧 Quick Troubleshooting

### Node not joining cluster?

```bash
# Check Redis connectivity
redis-cli -h YOUR_REDIS_IP -a YOUR_PASSWORD ping

# Should return: PONG

# Check server logs
tail -f /var/log/fleet-server.log
```

### Sessions not persisting?

```bash
# Verify all nodes use same Redis
grep redis_host */config.yaml

# Test session in Redis
redis-cli -h YOUR_REDIS_IP -a YOUR_PASSWORD
> KEYS fleet:session:*
```

### Database locked?

```bash
# Use WAL mode
sqlite3 fleet_data.sqlite3 "PRAGMA journal_mode=WAL;"

# Or use PostgreSQL for production
```

---

## 📊 Quick Commands

```bash
# Check cluster status
curl http://localhost:8768/api/fleet/cluster/status

# Check health
curl http://localhost:8768/api/fleet/cluster/health

# List nodes
curl http://localhost:8768/api/fleet/cluster/nodes

# View Redis cluster state
redis-cli -h YOUR_REDIS_IP -a YOUR_PASSWORD
> KEYS fleet:cluster:*

# View session count
redis-cli -h YOUR_REDIS_IP -a YOUR_PASSWORD
> KEYS fleet:session:*
```

---

## 🎉 Success!

You now have a redundant, high-availability fleet monitoring cluster!

**What you can do:**

✅ Stop any node - others keep running  
✅ Update nodes one at a time - zero downtime  
✅ Scale by adding more nodes  
✅ Monitor cluster health  
✅ Load balance traffic  

**For full guide, see:** `CLUSTER_SETUP_GUIDE.md`

---

## Production Checklist

Before going to production:

- [ ] Use strong passwords (not admin123!)
- [ ] Enable SSL/TLS
- [ ] Use proper load balancer (HAProxy/Nginx)
- [ ] Setup monitoring (Prometheus/Grafana)
- [ ] Configure backups
- [ ] Test failover scenarios
- [ ] Document your setup
- [ ] Setup alerting

**Your cluster is production-ready!** 🚀
