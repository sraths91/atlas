# Let's Encrypt Quick Start - Fleet Dashboard

## 🚀 5-Minute Setup

### Step 1: Install Dependencies (30 seconds)
```bash
pip3 install acme certbot schedule psutil
```

### Step 2: Get a Domain (if you don't have one)
**Free Option - DuckDNS:**
1. Go to https://www.duckdns.org
2. Sign in (Google/GitHub)
3. Create subdomain: `myfleet.duckdns.org`
4. Update IP: `curl "https://www.duckdns.org/update?domains=myfleet&token=YOUR_TOKEN&ip="`

### Step 3: Run Interactive Setup (2 minutes)
```bash
python3 -m atlas.fleet_letsencrypt setup
```

**Enter when prompted:**
- Domain: `myfleet.duckdns.org`
- Email: `your@email.com`
- Staging: `n` (use `y` for testing first)
- Webroot: Press Enter (uses default)

### Step 4: Update Fleet Config (30 seconds)
The setup will show you the certificate paths. Update `~/.fleet-config.json.encrypted`:

```json
{
  "ssl": {
    "cert_file": "/Users/YOUR_USERNAME/.fleet-certs/fullchain.pem",
    "key_file": "/Users/YOUR_USERNAME/.fleet-certs/privkey.pem"
  }
}
```

### Step 5: Restart Server (30 seconds)
```bash
pkill -f fleet_server
python3 -m atlas.fleet_server
```

### Step 6: Enable Auto-Renewal (1 minute)
```bash
python3 -m atlas.fleet_cert_renewal \
    --domain myfleet.duckdns.org \
    --webroot ~/.fleet-certs/acme-challenge \
    --email your@email.com &

echo $! > ~/.fleet-cert-renewal.pid
```

## ✅ Done!

Visit: `https://myfleet.duckdns.org:8768`

No more browser warnings! 🎉

---

## 📋 Checklist

- [ ] Dependencies installed
- [ ] Domain configured and pointing to server
- [ ] Port 80 accessible from internet
- [ ] Certificate obtained
- [ ] Fleet config updated
- [ ] Server restarted with HTTPS
- [ ] Auto-renewal service running
- [ ] Tested HTTPS access

---

## 🔧 Common Commands

### Check Certificate Expiration
```bash
python3 << 'EOF'
from atlas.fleet_letsencrypt import LetsEncryptManager
from datetime import datetime
m = LetsEncryptManager()
e = m.check_expiration()
print(f"Expires: {e}, Days left: {(e - datetime.now()).days}")
EOF
```

### Manual Renewal
```bash
python3 -m atlas.fleet_cert_renewal \
    --domain myfleet.duckdns.org \
    --webroot ~/.fleet-certs/acme-challenge \
    --email your@email.com \
    --check-now
```

### View Renewal Logs
```bash
tail -f ~/Library/Logs/fleet_cert_renewal.log
```

### Test with Staging
```bash
python3 -m atlas.fleet_letsencrypt setup
# Choose staging: y
```

---

## ⚠️ Troubleshooting

### "Port 80 not accessible"
```bash
# Check if port 80 is open
nc -zv yourdomain.com 80

# Open firewall (if needed)
sudo ufw allow 80
```

### "Challenge validation failed"
```bash
# Test challenge URL
curl http://yourdomain.com/.well-known/acme-challenge/test

# Check webroot permissions
ls -la ~/.fleet-certs/acme-challenge/
```

### "Rate limit exceeded"
- Use staging environment for testing
- Wait 7 days for rate limit reset
- Let's Encrypt limit: 50 certs/week per domain

---

## 📚 Full Documentation

- Setup Guide: `LETSENCRYPT_SETUP.md`
- Certificate Summary: `CERTIFICATE_SUMMARY.md`
- Let's Encrypt Docs: https://letsencrypt.org/docs/

---

## 💡 Pro Tips

1. **Test with Staging First**: Use `--staging` flag to avoid rate limits
2. **Keep Renewal Service Running**: Add to launchd or cron
3. **Monitor Expiration**: Check logs weekly
4. **Backup Certificates**: `tar -czf certs-backup.tar.gz ~/.fleet-certs/`
5. **Use Dynamic DNS**: If you don't have a static IP

---

## 🎯 One-Liner Setup (Advanced)

```bash
pip3 install acme certbot schedule psutil && \
python3 -m atlas.fleet_letsencrypt setup && \
python3 -m atlas.fleet_cert_renewal \
    --domain YOUR_DOMAIN \
    --webroot ~/.fleet-certs/acme-challenge \
    --email YOUR_EMAIL &
```

Replace `YOUR_DOMAIN` and `YOUR_EMAIL` with your values.
