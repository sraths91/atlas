# Let's Encrypt Integration for Fleet Dashboard

## Overview
Automatic SSL certificate management using Let's Encrypt, eliminating browser security warnings without manual certificate management.

## Features
- ✅ **Automatic Certificate Issuance**: Get free SSL certificates from Let's Encrypt
- ✅ **Auto-Renewal**: Certificates automatically renew before expiration
- ✅ **HTTP-01 Challenge**: Standard domain validation method
- ✅ **No Manual Intervention**: Set it up once, forget about it
- ✅ **Staging Support**: Test with Let's Encrypt staging environment
- ✅ **Monitoring**: Track expiration and renewal status

## Requirements

### 1. Domain Name
You need a domain name pointing to your server:
- **Option A**: Purchase a domain (e.g., from Namecheap, Google Domains)
- **Option B**: Use a free subdomain service (e.g., DuckDNS, No-IP)
- **Option C**: Use a local DNS server for internal networks

### 2. Port 80 Access
Let's Encrypt validates domain ownership via HTTP:
- Port 80 must be accessible from the internet
- Or use DNS-01 challenge (advanced, not yet implemented)

### 3. Python Dependencies
```bash
pip3 install acme certbot schedule psutil
```

## Quick Start

### Method 1: Interactive Setup
```bash
# Run interactive setup wizard
python3 -m atlas.fleet_letsencrypt setup

# Follow the prompts:
# 1. Enter your domain name (e.g., fleet.example.com)
# 2. Enter your email address
# 3. Choose staging (for testing) or production
# 4. Specify webroot path for HTTP challenge
```

### Method 2: Programmatic Setup
```python
from atlas.fleet_letsencrypt import LetsEncryptManager

# Create manager
manager = LetsEncryptManager(staging=False)  # Use production

# Register account
manager.register_account('admin@example.com')

# Obtain certificate
manager.obtain_certificate(
    domain='fleet.example.com',
    webroot_path='/var/www/html'
)

# Get certificate paths
paths = manager.get_certificate_paths()
print(f"Certificate: {paths['fullchain']}")
print(f"Private key: {paths['key']}")
```

### Method 3: Command Line
```bash
# One-time certificate request
python3 << 'EOF'
from atlas.fleet_letsencrypt import LetsEncryptManager

manager = LetsEncryptManager()
manager.register_account('admin@example.com')
manager.obtain_certificate('fleet.example.com', '/tmp/acme-challenge')
EOF
```

## Automatic Renewal

### Setup Auto-Renewal Service

#### Option A: Run as Background Service
```bash
# Start renewal service (checks every 12 hours)
python3 -m atlas.fleet_cert_renewal \
    --domain fleet.example.com \
    --webroot /var/www/html \
    --email admin@example.com \
    --interval 12 &

# Save PID for later
echo $! > ~/.fleet-cert-renewal.pid
```

#### Option B: Use launchd (macOS)
Create `~/Library/LaunchAgents/com.fleet.cert-renewal.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fleet.cert-renewal</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>-m</string>
        <string>atlas.fleet_cert_renewal</string>
        <string>--domain</string>
        <string>fleet.example.com</string>
        <string>--webroot</string>
        <string>/var/www/html</string>
        <string>--email</string>
        <string>admin@example.com</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/Library/Logs/fleet_cert_renewal.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/Library/Logs/fleet_cert_renewal_error.log</string>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.fleet.cert-renewal.plist
```

#### Option C: Use cron
```bash
# Edit crontab
crontab -e

# Add line to check twice daily (at 3 AM and 3 PM)
0 3,15 * * * /usr/local/bin/python3 -m atlas.fleet_cert_renewal --domain fleet.example.com --webroot /var/www/html --email admin@example.com --check-now
```

## Integration with Fleet Server

### Update Fleet Configuration

After obtaining certificates, update your `~/.fleet-config.json`:

```json
{
  "server": {
    "port": 8768,
    "host": "0.0.0.0",
    "api_key": "your-api-key-here"
  },
  "ssl": {
    "cert_file": "/Users/YOUR_USERNAME/.fleet-certs/fullchain.pem",
    "key_file": "/Users/YOUR_USERNAME/.fleet-certs/privkey.pem"
  }
}
```

### Restart Fleet Server
```bash
# Stop current server
pkill -f fleet_server

# Start with SSL
python3 -m atlas.fleet_server
```

The server will automatically use the SSL certificates and listen on HTTPS (port 8768).

## Domain Setup Examples

### Example 1: DuckDNS (Free Dynamic DNS)

1. **Sign up at https://www.duckdns.org**
2. **Create subdomain**: `myfleet.duckdns.org`
3. **Update IP**: Use DuckDNS update URL
   ```bash
   curl "https://www.duckdns.org/update?domains=myfleet&token=YOUR_TOKEN&ip="
   ```
4. **Get certificate**:
   ```bash
   python3 -m atlas.fleet_letsencrypt setup
   # Enter: myfleet.duckdns.org
   ```

### Example 2: No-IP (Free Dynamic DNS)

1. **Sign up at https://www.noip.com**
2. **Create hostname**: `myfleet.ddns.net`
3. **Install DUC** (Dynamic Update Client)
4. **Get certificate**:
   ```bash
   python3 -m atlas.fleet_letsencrypt setup
   # Enter: myfleet.ddns.net
   ```

### Example 3: Own Domain

1. **Purchase domain** (e.g., from Namecheap)
2. **Create A record**: `fleet.yourdomain.com` → Your server IP
3. **Wait for DNS propagation** (up to 48 hours)
4. **Get certificate**:
   ```bash
   python3 -m atlas.fleet_letsencrypt setup
   # Enter: fleet.yourdomain.com
   ```

## HTTP Challenge Setup

### Option 1: Temporary HTTP Server
The simplest approach for initial setup:

```python
# Start simple HTTP server for challenge
import http.server
import socketserver
import os

os.chdir('/tmp/acme-challenge')
PORT = 80

Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()
```

### Option 2: Nginx Reverse Proxy
If you want to run Fleet on 8768 but serve challenges on port 80:

```nginx
server {
    listen 80;
    server_name fleet.example.com;
    
    # ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect everything else to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name fleet.example.com;
    
    ssl_certificate /Users/YOUR_USERNAME/.fleet-certs/fullchain.pem;
    ssl_certificate_key /Users/YOUR_USERNAME/.fleet-certs/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8768;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 3: Built-in Challenge Server
Fleet server can serve challenges directly:

```python
# In fleet_server.py, add route:
if path.startswith('/.well-known/acme-challenge/'):
    challenge_path = os.path.join(
        '/tmp/acme-challenge',
        path.replace('/.well-known/acme-challenge/', '')
    )
    if os.path.exists(challenge_path):
        with open(challenge_path, 'r') as f:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f.read().encode())
        return
```

## Monitoring & Troubleshooting

### Check Certificate Status
```bash
# Check expiration
python3 << 'EOF'
from atlas.fleet_letsencrypt import LetsEncryptManager

manager = LetsEncryptManager()
expiration = manager.check_expiration()
if expiration:
    from datetime import datetime
    days_left = (expiration - datetime.now()).days
    print(f"Certificate expires in {days_left} days ({expiration})")
else:
    print("No certificate found")
EOF
```

### View Certificate Details
```bash
openssl x509 -in ~/.fleet-certs/cert.pem -text -noout
```

### Test Renewal
```bash
# Use staging to test without rate limits
python3 -m atlas.fleet_cert_renewal \
    --domain fleet.example.com \
    --webroot /tmp/acme-challenge \
    --email admin@example.com \
    --staging \
    --check-now
```

### Common Issues

#### Issue: "Port 80 not accessible"
**Solution**: 
- Check firewall: `sudo ufw allow 80`
- Check router port forwarding
- Verify domain DNS points to your IP

#### Issue: "Challenge validation failed"
**Solution**:
- Ensure webroot path is correct
- Check file permissions
- Verify HTTP server is running
- Test URL: `curl http://yourdomain.com/.well-known/acme-challenge/test`

#### Issue: "Rate limit exceeded"
**Solution**:
- Use staging environment for testing
- Let's Encrypt limits: 50 certificates per domain per week
- Wait for rate limit reset (weekly)

#### Issue: "Certificate not loading in server"
**Solution**:
- Check file paths in config
- Verify file permissions (should be readable)
- Restart server after obtaining certificate
- Check server logs for SSL errors

## Rate Limits

Let's Encrypt has rate limits:
- **Certificates per Registered Domain**: 50 per week
- **Duplicate Certificate**: 5 per week
- **Failed Validations**: 5 per account per hostname per hour

**Recommendation**: Use staging environment for testing!

## Security Best Practices

1. **Protect Private Keys**
   ```bash
   chmod 600 ~/.fleet-certs/privkey.pem
   ```

2. **Use Strong Ciphers**
   Configure server to use modern TLS ciphers only

3. **Enable HSTS**
   Add `Strict-Transport-Security` header

4. **Monitor Expiration**
   Set up alerts for certificate expiration

5. **Backup Certificates**
   ```bash
   tar -czf fleet-certs-backup.tar.gz ~/.fleet-certs/
   ```

## Migration from Self-Signed

If you're currently using self-signed certificates:

1. **Obtain Let's Encrypt certificate** (follow Quick Start)
2. **Update config** with new certificate paths
3. **Restart server**
4. **Remove old self-signed certificates**
5. **Update agents** to use new HTTPS URL

No agent reconfiguration needed - they'll automatically trust Let's Encrypt certificates!

## Cost Analysis

| Item | Cost |
|------|------|
| Let's Encrypt Certificate | **FREE** |
| Domain Name (optional) | $10-15/year |
| Dynamic DNS (optional) | **FREE** |
| Renewal Service | **FREE** |
| **Total** | **$0-15/year** |

Compare to commercial certificates: $50-200/year

## Status & Roadmap

### Current Status
✅ HTTP-01 challenge support
✅ Automatic renewal
✅ Staging environment support
✅ Certificate monitoring
✅ Integration with Fleet server

### Planned Features
- [ ] DNS-01 challenge (for wildcard certs)
- [ ] Multiple domain support (SAN certificates)
- [ ] Web UI for certificate management
- [ ] Email notifications for expiration
- [ ] Automatic rollback on renewal failure
- [ ] Certificate transparency monitoring

## Support

For issues or questions:
1. Check logs: `~/Library/Logs/fleet_cert_renewal.log`
2. Test with staging environment first
3. Verify domain DNS and port 80 access
4. Review Let's Encrypt documentation

## References

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [ACME Protocol](https://tools.ietf.org/html/rfc8555)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)
