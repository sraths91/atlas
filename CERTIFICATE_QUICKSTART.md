# SSL Certificate Quick Start - Fleet Dashboard

## Choose Your Setup

### 🏠 Internal Network (IP Address)
**Use Case**: Accessing via `https://192.168.1.100:8768`

```bash
# Install dependencies
pip3 install cryptography

# Run setup
python3 -m atlas.fleet_cert_auto setup

# Enter IP: 192.168.1.100
# Choose: Option 1 (Install in system trust)
# Enter admin password when prompted
```

**Result**: ✅ No browser warnings, works immediately

---

### 🌐 Public Access (Domain Name)
**Use Case**: Accessing via `https://fleet.example.com:8768`

```bash
# Install dependencies
pip3 install acme certbot cryptography

# Run setup
python3 -m atlas.fleet_cert_auto setup

# Enter domain: fleet.example.com
# Enter email: your@email.com
# Ensure port 80 is accessible
```

**Result**: ✅ Trusted certificate, auto-renewal

---

## Comparison

| Feature | Internal IP | Domain Name |
|---------|-------------|-------------|
| **Setup Time** | 2 minutes | 5 minutes |
| **Certificate Type** | Self-signed | Let's Encrypt |
| **Trust** | Manual install | Automatic |
| **Renewal** | Manual (~2 years) | Auto (90 days) |
| **Internet Required** | No | Yes |
| **Port 80 Required** | No | Yes |
| **Multi-device** | Install on each | Automatic |
| **Best For** | Internal use | Public access |

---

## After Setup

### Update Fleet Config
```json
{
  "ssl": {
    "cert_file": "/Users/USERNAME/.fleet-certs/fullchain.pem",
    "key_file": "/Users/USERNAME/.fleet-certs/privkey.pem"
  }
}
```

### Restart Server
```bash
pkill -f fleet_server
python3 -m atlas.fleet_server
```

### Test
```bash
# Internal IP
open https://192.168.1.100:8768

# Domain
open https://fleet.example.com:8768
```

---

## Multi-Device Setup

### Internal IP (Self-Signed)
**On each client device:**
```bash
# Copy certificate from server
scp user@192.168.1.100:~/.fleet-certs/cert.pem ~/fleet-cert.pem

# Install (macOS)
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain ~/fleet-cert.pem

# Install (Windows)
# Double-click cert.pem → Install → Local Machine → Trusted Root

# Install (Linux)
sudo cp ~/fleet-cert.pem /usr/local/share/ca-certificates/fleet.crt
sudo update-ca-certificates
```

### Domain (Let's Encrypt)
**No action needed** - browsers automatically trust Let's Encrypt!

---

## Quick Commands

### Check Certificate Expiration
```bash
python3 << 'EOF'
from atlas.fleet_cert_auto import AutoCertificateManager
from datetime import datetime
m = AutoCertificateManager()
info = m.get_certificate_info()
if info:
    days = (info['not_after'] - datetime.now()).days
    print(f"Expires in {days} days")
EOF
```

### View Certificate Details
```bash
openssl x509 -in ~/.fleet-certs/cert.pem -text -noout
```

### Remove Certificate from Trust
```bash
# macOS
sudo security delete-certificate -c "Fleet Dashboard" \
  /Library/Keychains/System.keychain
```

---

## Troubleshooting

### Browser Still Shows Warning (Internal IP)
```bash
# Verify certificate is installed
security find-certificate -c "Fleet Dashboard" \
  /Library/Keychains/System.keychain

# Reinstall if needed
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  ~/.fleet-certs/cert.pem

# Clear browser cache and restart browser
```

### Let's Encrypt Validation Failed (Domain)
```bash
# Check port 80 is accessible
nc -zv yourdomain.com 80

# Verify DNS points to your server
dig yourdomain.com

# Test with staging first
python3 -m atlas.fleet_letsencrypt setup
# Choose staging: y
```

---

## Full Documentation

- **Internal IP Setup**: `INTERNAL_IP_CERTIFICATES.md`
- **Let's Encrypt Setup**: `LETSENCRYPT_SETUP.md`
- **Complete Guide**: `CERTIFICATE_SUMMARY.md`

---

## Decision Tree

```
Do you have a domain name?
├─ No → Use Internal IP setup (self-signed)
│        • 2 minute setup
│        • Install certificate on each device
│        • Works offline
│
└─ Yes → Do you want public internet access?
         ├─ No → Use Internal IP setup
         │        • Simpler, no port 80 needed
         │
         └─ Yes → Use Let's Encrypt
                  • Automatic trust
                  • Auto-renewal
                  • Requires port 80
```

---

## One-Liner Setup

### Internal IP
```bash
pip3 install cryptography && python3 -m atlas.fleet_cert_auto setup
```

### Domain
```bash
pip3 install acme certbot cryptography && python3 -m atlas.fleet_cert_auto setup
```

---

**Choose your path and get started! No more security warnings!** 🔒✅
