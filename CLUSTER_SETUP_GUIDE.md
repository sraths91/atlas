# 🚀 Fleet Server Cluster Mode - High Availability Guide

## ✨ Overview

The Fleet Server now supports **cluster mode** for high availability, redundancy, and seamless failover. Run multiple server instances in a cluster to eliminate single points of failure.

---

## 🎯 Benefits

### Why Use Cluster Mode?

✅ **High Availability** - No single point of failure  
✅ **Automatic Failover** - Seamless user experience during outages  
✅ **Load Distribution** - Better performance under load  
✅ **Zero Downtime** - Rolling updates without service interruption  
✅ **Redundancy** - Multiple servers for reliability  
✅ **Scalability** - Add nodes to handle more load  

---

## 🏗️ Architecture

### Cluster Components:

```
┌──────────────────────────────────────────────┐
│         Load Balancer (HAProxy/Nginx)        │
│         https://fleet.company.com             │
└──────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Node 1     │ │  Node 2     │ │  Node 3     │
│  server-01  │ │  server-02  │ │  server-03  │
│  Port 8768  │ │  Port 8768  │ │  Port 8768  │
└─────────────┘ └─────────────┘ └─────────────┘
        │            │            │
        └────────────┼────────────┘
                     ▼
        ┌──────────────────────────┐
        │   Shared Storage         │
        │  - Database (SQLite/PG)  │
        │  - Sessions (Redis)      │
        │  - Cluster State         │
        └──────────────────────────┘
```

### Key Features:

1. **Node Registration** - Each server registers itself in the cluster
2. **Health Monitoring** - Heartbeats to detect node failures
3. **Shared Sessions** - Users stay logged in across nodes
4. **Shared Database** - All nodes access the same fleet data
5. **Load Balancing** - Traffic distributed across healthy nodes

---

## 📋 Prerequisites

### Required:

1. **Shared Storage** - Network filesystem or Redis
2. **Load Balancer** - HAProxy, Nginx, or AWS ELB
3. **Multiple Servers** - 2+ server instances
4. **Network Connectivity** - All nodes can reach shared storage

### Optional but Recommended:

- Redis server (for production)
- PostgreSQL (for large fleets)
- SSL/TLS certificates
- Monitoring system (Prometheus, Grafana)

---

## 🔧 Configuration

### Step 1: Prepare Shared Storage

#### Option A: Redis (Recommended for Production)

**Install Redis:**

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

**Configure Redis for network access:**

Edit `/etc/redis/redis.conf`:

```conf
bind 0.0.0.0
requirepass YOUR_STRONG_PASSWORD
```

#### Option B: Shared Filesystem (Development/Testing)

**Setup NFS mount:**

```bash
# On NFS server
sudo apt-get install nfs-kernel-server
echo "/fleet-cluster *(rw,sync,no_subtree_check)" | sudo tee -a /etc/exports
sudo exportfs -ra

# On each node
sudo mount nfs-server:/fleet-cluster /mnt/fleet-cluster
```

---

### Step 2: Configure Each Node

**Create `config.yaml` on each server:**

```yaml
organization:
  name: "Your Company"

server:
  # Different for each node or use 0.0.0.0
  host: "0.0.0.0"
  port: 8768
  
  # Same on all nodes
  api_key: "YOUR_API_KEY"
  web_username: "admin"
  web_password: "SecurePassword123!"
  
  # Database encryption (same key on all nodes)
  db_encryption_key: "YOUR_FERNET_KEY"
  db_path: "/mnt/fleet-cluster/fleet_data.sqlite3"
  
  # Payload encryption (same key on all nodes)
  encryption_key: "YOUR_AES_GCM_KEY"

ssl:
  cert_file: "/etc/fleet/cert.pem"
  key_file: "/etc/fleet/key.pem"

# Cluster Configuration
cluster:
  enabled: true
  backend: "redis"  # Options: redis, sqlite, file
  
  # Node configuration (optional - auto-detected if not set)
  hostname: "server-01.company.com"
  node_id: "server-01"  # Optional - auto-generated if not set
  
  # Heartbeat settings
  heartbeat_interval: 10  # seconds
  node_timeout: 30  # seconds
  
  # Redis backend (if using Redis)
  redis_host: "redis.company.com"
  redis_port: 6379
  redis_db: 0
  redis_password: "YOUR_REDIS_PASSWORD"
  
  # File/SQLite backend (if using shared filesystem)
  state_path: "/mnt/fleet-cluster/cluster-state.json"
  
# Shared Sessions Configuration
sessions:
  backend: "redis"  # Options: redis, sqlite, file
  ttl: 3600  # Session timeout in seconds (1 hour)
  
  # Redis backend (recommended)
  redis:
    host: "redis.company.com"
    port: 6379
    db: 1  # Use different DB than cluster state
    password: "YOUR_REDIS_PASSWORD"
  
  # SQLite backend (shared filesystem)
  db_path: "/mnt/fleet-cluster/sessions.db"
  
  # File backend (development only)
  session_dir: "/mnt/fleet-cluster/sessions"
```

**Important:** All nodes must use:
- **Same database** (`db_path`)
- **Same encryption keys**
- **Same API keys**
- **Same session storage**

---

### Step 3: Configure Load Balancer

#### Option A: HAProxy Configuration

**`/etc/haproxy/haproxy.cfg`:**

```haproxy
global
    log /dev/log local0
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000

# Frontend - HTTPS
frontend fleet_frontend
    bind *:443 ssl crt /etc/haproxy/certs/fleet.pem
    bind *:80
    redirect scheme https if !{ ssl_fc }
    
    default_backend fleet_backend
    
    # Health check endpoint
    acl is_health path /api/fleet/cluster/health
    use_backend health_backend if is_health

# Backend - Fleet Servers
backend fleet_backend
    balance roundrobin
    option httpchk GET /api/fleet/cluster/health
    http-check expect status 200
    
    # Cookie-based session persistence (optional)
    cookie SERVERID insert indirect nocache
    
    # Fleet server nodes
    server node1 server-01:8768 check cookie node1 inter 10s fall 3 rise 2
    server node2 server-02:8768 check cookie node2 inter 10s fall 3 rise 2
    server node3 server-03:8768 check cookie node3 inter 10s fall 3 rise 2

# Health check backend (no session persistence)
backend health_backend
    balance roundrobin
    server node1 server-01:8768 check
    server node2 server-02:8768 check
    server node3 server-03:8768 check

# Stats page
listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
    stats admin if TRUE
```

**Start HAProxy:**

```bash
sudo systemctl start haproxy
sudo systemctl enable haproxy
```

#### Option B: Nginx Configuration

**`/etc/nginx/sites-available/fleet`:**

```nginx
upstream fleet_cluster {
    # Least connections load balancing
    least_conn;
    
    # Fleet server nodes
    server server-01:8768 max_fails=3 fail_timeout=30s;
    server server-02:8768 max_fails=3 fail_timeout=30s;
    server server-03:8768 max_fails=3 fail_timeout=30s;
}

# Health check endpoint
upstream fleet_health {
    server server-01:8768;
    server server-02:8768;
    server server-03:8768;
}

server {
    listen 80;
    listen [::]:80;
    server_name fleet.company.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name fleet.company.com;
    
    # SSL configuration
    ssl_certificate /etc/nginx/ssl/fleet.crt;
    ssl_certificate_key /etc/nginx/ssl/fleet.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Proxy settings
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Health check endpoint (no caching)
    location /api/fleet/cluster/health {
        proxy_pass http://fleet_health;
        proxy_cache_bypass 1;
        proxy_no_cache 1;
    }
    
    # All other requests
    location / {
        proxy_pass http://fleet_cluster;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**Enable and restart Nginx:**

```bash
sudo ln -s /etc/nginx/sites-available/fleet /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🚀 Deployment

### Step 1: Start First Node

```bash
# On server-01
cd /path/to/fleet-server
python3 -m atlas.fleet_server --config config.yaml
```

**Expected output:**

```
INFO - Using ENCRYPTED database storage
INFO - End-to-end payload encryption ENABLED (AES-256-GCM)
INFO - Cluster mode ENABLED (node: server-01-abc123, backend: redis)
INFO - Registered node in cluster: server-01-abc123
INFO - Heartbeat thread started (interval: 10s)
INFO - Fleet server started on 0.0.0.0:8768 (HTTPS)
```

---

### Step 2: Start Additional Nodes

```bash
# On server-02
python3 -m atlas.fleet_server --config config.yaml

# On server-03
python3 -m atlas.fleet_server --config config.yaml
```

Each node will:
1. Register in the cluster
2. Connect to shared database
3. Start sending heartbeats
4. Become available for traffic

---

### Step 3: Verify Cluster

**Check cluster status:**

```bash
curl https://fleet.company.com/api/fleet/cluster/status
```

**Expected response:**

```json
{
  "enabled": true,
  "node_id": "server-01-abc123",
  "backend": "redis",
  "total_nodes": 3,
  "active_nodes": 3,
  "inactive_nodes": 0,
  "nodes": [
    {
      "node_id": "server-01-abc123",
      "hostname": "server-01.company.com",
      "port": 8768,
      "status": "active",
      "last_heartbeat": "2024-11-26T10:30:00",
      "url": "https://server-01.company.com:8768"
    },
    {
      "node_id": "server-02-def456",
      "hostname": "server-02.company.com",
      "port": 8768,
      "status": "active",
      "last_heartbeat": "2024-11-26T10:30:05",
      "url": "https://server-02.company.com:8768"
    },
    {
      "node_id": "server-03-ghi789",
      "hostname": "server-03.company.com",
      "port": 8768,
      "status": "active",
      "last_heartbeat": "2024-11-26T10:30:08",
      "url": "https://server-03.company.com:8768"
    }
  ]
}
```

**Check health endpoint:**

```bash
curl https://fleet.company.com/api/fleet/cluster/health
```

**Expected response:**

```json
{
  "status": "healthy",
  "node_id": "server-01-abc123"
}
```

---

## ✅ Verification

### Test Scenarios:

#### 1. Login and Session Persistence

```bash
# Login via load balancer
curl -c cookies.txt -X POST https://fleet.company.com/login \
  -d "username=admin&password=SecurePassword123!"

# Make request (may hit different node)
curl -b cookies.txt https://fleet.company.com/api/fleet/machines

# Should work! Session is shared across nodes
```

#### 2. Node Failure Simulation

```bash
# Stop one node
sudo systemctl stop fleet-server@node2

# Requests still work via other nodes
curl https://fleet.company.com/dashboard

# Check cluster status
curl https://fleet.company.com/api/fleet/cluster/status
# Should show node2 as inactive after timeout
```

#### 3. Rolling Update

```bash
# Update and restart nodes one at a time
# Node 1
sudo systemctl stop fleet-server@node1
# Deploy new version
sudo systemctl start fleet-server@node1

# Node 2
sudo systemctl stop fleet-server@node2
# Deploy new version
sudo systemctl start fleet-server@node2

# Node 3
sudo systemctl stop fleet-server@node3
# Deploy new version
sudo systemctl start fleet-server@node3

# Zero downtime!
```

---

## 📊 Monitoring

### Cluster Endpoints:

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `/api/fleet/cluster/status` | Full cluster status | Yes |
| `/api/fleet/cluster/health` | Health check (for LB) | No |
| `/api/fleet/cluster/nodes` | List active nodes | Yes |

### Metrics to Monitor:

1. **Active Nodes** - Should match deployed count
2. **Heartbeat Age** - Should be < heartbeat_interval
3. **Response Time** - Track per-node performance
4. **Error Rate** - Monitor 503 errors
5. **Session Count** - Track active sessions

### Integration with Monitoring Tools:

**Prometheus metrics endpoint:**

```yaml
# Add to config.yaml
monitoring:
  enabled: true
  port: 9090
  endpoint: "/metrics"
```

**Grafana Dashboard:**

- Import fleet_cluster.json dashboard
- Monitor node health, request rates, errors

---

## 🔧 Troubleshooting

### Issue: Node shows as inactive

**Symptoms:**
- Node in cluster status shows "inactive"
- Load balancer marks node as down

**Solutions:**

```bash
# Check if service is running
sudo systemctl status fleet-server

# Check logs
tail -f /var/log/fleet-server.log

# Check network connectivity to shared storage
ping redis.company.com
telnet redis.company.com 6379

# Restart node
sudo systemctl restart fleet-server
```

### Issue: Sessions not persisting across nodes

**Symptoms:**
- Users logged out when hitting different node
- "Unauthorized" errors randomly

**Solutions:**

```bash
# Verify Redis is accessible
redis-cli -h redis.company.com -a YOUR_PASSWORD ping

# Check session backend configuration
# All nodes must use same session backend

# Verify session TTL is reasonable
# Check sessions.ttl in config.yaml

# Test session creation
curl -c cookies.txt -X POST https://fleet.company.com/login \
  -d "username=admin&password=pass"
curl -b cookies.txt https://fleet.company.com/api/fleet/machines
```

### Issue: Database conflicts

**Symptoms:**
- SQLite "database is locked" errors
- Data inconsistency between nodes

**Solutions:**

```bash
# Use WAL mode for SQLite (better concurrency)
sqlite3 fleet_data.sqlite3 "PRAGMA journal_mode=WAL;"

# Or migrate to PostgreSQL for production
# Edit config.yaml:
#   db_backend: postgresql
#   db_url: postgresql://user:pass@dbserver/fleet

# Verify all nodes use same db_path
grep db_path */config.yaml
```

### Issue: Load balancer health checks failing

**Symptoms:**
- All nodes marked down in HAProxy/Nginx
- 503 errors from load balancer

**Solutions:**

```bash
# Test health endpoint directly
curl http://server-01:8768/api/fleet/cluster/health

# Check firewall rules
sudo iptables -L | grep 8768

# Verify SSL certificates
openssl s_client -connect server-01:8768

# Check load balancer logs
sudo tail -f /var/log/haproxy.log
```

---

## 🔐 Security Considerations

### Best Practices:

1. **Encrypt All Traffic**
   - Use SSL/TLS for load balancer ↔ users
   - Use SSL/TLS for load balancer ↔ nodes
   - Encrypt Redis connections

2. **Isolate Cluster Network**
   - Use private network for node-to-node
   - Firewall rules to restrict access
   - VPN for remote nodes

3. **Secure Shared Storage**
   - Redis requirepass enabled
   - Filesystem permissions (chmod 600)
   - Database encryption keys protected

4. **Monitor Access**
   - Log all cluster events
   - Alert on node failures
   - Track authentication attempts

---

## 📈 Scaling

### Horizontal Scaling:

**Add more nodes:**

```bash
# Simply start new node with same config
python3 -m atlas.fleet_server --config config.yaml

# Node auto-registers in cluster
# Load balancer detects via health checks
```

**Remove nodes:**

```bash
# Stop node gracefully
sudo systemctl stop fleet-server

# Node auto-deregisters after timeout
# Load balancer stops sending traffic
```

### Vertical Scaling:

**Increase per-node capacity:**

```yaml
# config.yaml
server:
  max_connections: 1000
  thread_pool_size: 50
  request_timeout: 60
```

---

## 📋 Configuration Reference

### Cluster Configuration Options:

```yaml
cluster:
  # Enable cluster mode
  enabled: true|false
  
  # Cluster state backend
  backend: "redis"|"sqlite"|"file"
  
  # Node identification (auto-detected if not set)
  hostname: "server-01.company.com"
  node_id: "custom-node-id"
  port: 8768
  
  # Heartbeat configuration
  heartbeat_interval: 10  # How often to send heartbeats (seconds)
  node_timeout: 30  # When to mark node as inactive (seconds)
  
  # Redis backend
  redis_host: "localhost"
  redis_port: 6379
  redis_db: 0
  redis_password: null
  
  # File/SQLite backend
  state_path: "/path/to/cluster-state.json"
```

### Session Configuration Options:

```yaml
sessions:
  # Session storage backend
  backend: "redis"|"sqlite"|"file"
  
  # Session timeout
  ttl: 3600  # seconds (1 hour)
  
  # Redis backend
  redis:
    host: "localhost"
    port: 6379
    db: 1
    password: null
  
  # SQLite backend
  db_path: "/path/to/sessions.db"
  
  # File backend
  session_dir: "/path/to/sessions"
```

---

## 🎉 Summary

You now have a fully redundant, high-availability fleet monitoring system!

**What you get:**

✅ Multiple server instances for redundancy  
✅ Automatic failover on node failure  
✅ Shared sessions across all nodes  
✅ Load balancing for better performance  
✅ Zero-downtime rolling updates  
✅ Health monitoring and alerting  
✅ Production-ready clustering  

**Your fleet monitoring is now enterprise-grade!** 🚀🔥

For questions or issues, check the troubleshooting section or open an issue on GitHub.
