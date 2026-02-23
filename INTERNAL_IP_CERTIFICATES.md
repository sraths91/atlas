# Internal IP Certificate Setup - Fleet Dashboard

## Overview
For internal networks using IP addresses (like `192.168.1.100`), Let's Encrypt won't work because they can't validate private IPs. Instead, we use **self-signed certificates with system trust installation** to eliminate browser warnings.

## The Problem
When using internal IPs:
- ❌ Let's Encrypt can't validate private IP addresses
- ❌ Self-signed certificates show browser warnings
- ❌ Users have to click through security warnings

## The Solution
Generate a self-signed certificate and install it in the system trust store:
- ✅ No browser warnings
- ✅ Works with any internal IP
- ✅ No external dependencies
- ✅ One-time setup

## Quick Start

### Method 1: Automatic Setup (Recommended)
```bash
# Install dependencies
pip3 install cryptography

# Run interactive setup
python3 -m atlas.fleet_cert_auto setup

# Enter your internal IP (e.g., 192.168.1.100)
# Choose option 1 to install in system trust
```

### Method 2: Programmatic
```python
from atlas.fleet_cert_auto import AutoCertificateManager

manager = AutoCertificateManager()

# Generate certificate for internal IP
success, message = manager.setup_certificate('192.168.1.100')

# Install in system trust (macOS)
if success:
    manager.install_system_trust_macos()
```

### Method 3: Manual
```bash
# Generate certificate
python3 << 'EOF'
from atlas.fleet_cert_auto import AutoCertificateManager
manager = AutoCertificateManager()
manager.generate_self_signed_cert('192.168.1.100')
EOF

# Install in system trust
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  ~/.fleet-certs/cert.pem
```

## How It Works

### Step 1: Generate Self-Signed Certificate
Creates a certificate with:
- **Subject**: Your IP address
- **SAN (Subject Alternative Name)**: IP address + localhost
- **Validity**: 825 days (~2 years)
- **Key Size**: 2048-bit RSA
- **Signature**: SHA-256

### Step 2: Install in System Trust Store
Adds certificate to macOS keychain:
- **Location**: `/Library/Keychains/System.keychain`
- **Trust Level**: Root certificate
- **Effect**: All browsers trust the certificate

### Step 3: Configure Fleet Server
Updates config to use the certificate:
```json
{
  "ssl": {
    "cert_file": "/Users/USERNAME/.fleet-certs/fullchain.pem",
    "key_file": "/Users/USERNAME/.fleet-certs/privkey.pem"
  }
}
```

## Certificate Details

### What's Included
The generated certificate includes:
- **Common Name (CN)**: Your IP address
- **Subject Alternative Names**:
  - Your IP address (e.g., `192.168.1.100`)
  - `localhost`
  - `127.0.0.1`
- **Key Usage**: Digital Signature, Key Encipherment
- **Extended Key Usage**: Server Authentication, Client Authentication

### Example Certificate
```
Certificate:
    Subject: CN=192.168.1.100, O=Fleet Dashboard
    Issuer: CN=192.168.1.100, O=Fleet Dashboard (self-signed)
    Validity:
        Not Before: Nov 19 2025
        Not After : Feb 17 2028 (825 days)
    Subject Alternative Name:
        IP Address: 192.168.1.100
        DNS: localhost
        IP Address: 127.0.0.1
    Signature Algorithm: sha256WithRSAEncryption
```

## Platform-Specific Instructions

### macOS (Automatic)
```bash
# Run setup wizard
python3 -m atlas.fleet_cert_auto setup

# Choose option 1 when prompted
# Enter admin password when requested
```

### macOS (Manual)
```bash
# Generate certificate
python3 -c "from atlas.fleet_cert_auto import AutoCertificateManager; \
  AutoCertificateManager().generate_self_signed_cert('192.168.1.100')"

# Install in keychain
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  ~/.fleet-certs/cert.pem

# Verify installation
security find-certificate -c "Fleet Dashboard" \
  /Library/Keychains/System.keychain
```

### Windows (Manual)
```powershell
# Generate certificate (use Python script)
python -c "from atlas.fleet_cert_auto import AutoCertificateManager; AutoCertificateManager().generate_self_signed_cert('192.168.1.100')"

# Install certificate
# 1. Double-click cert.pem
# 2. Click "Install Certificate"
# 3. Choose "Local Machine"
# 4. Select "Place all certificates in the following store"
# 5. Browse to "Trusted Root Certification Authorities"
# 6. Click Finish
```

### Linux (Manual)
```bash
# Generate certificate
python3 -c "from atlas.fleet_cert_auto import AutoCertificateManager; \
  AutoCertificateManager().generate_self_signed_cert('192.168.1.100')"

# Install in system trust (Ubuntu/Debian)
sudo cp ~/.fleet-certs/cert.pem /usr/local/share/ca-certificates/fleet-dashboard.crt
sudo update-ca-certificates

# Install in system trust (RHEL/CentOS)
sudo cp ~/.fleet-certs/cert.pem /etc/pki/ca-trust/source/anchors/fleet-dashboard.crt
sudo update-ca-trust
```

## Browser-Specific Setup

### Chrome/Edge
- Uses system trust store
- No additional setup needed after system installation

### Firefox
Firefox uses its own certificate store:

1. Open Firefox
2. Go to `about:preferences#privacy`
3. Scroll to "Certificates" → Click "View Certificates"
4. Go to "Authorities" tab
5. Click "Import"
6. Select `~/.fleet-certs/cert.pem`
7. Check "Trust this CA to identify websites"
8. Click OK

### Safari
- Uses system trust store
- No additional setup needed after system installation

## Multi-Device Setup

### Server (where Fleet Dashboard runs)
```bash
# Generate and install certificate
python3 -m atlas.fleet_cert_auto setup
# Enter server IP: 192.168.1.100
# Choose option 1 to install
```

### Client Devices (accessing the dashboard)
Each device needs the certificate installed:

#### Option 1: Export and Install
```bash
# On server, export certificate
cp ~/.fleet-certs/cert.pem ~/Desktop/fleet-cert.pem

# Transfer to client devices
# Then install on each device (see platform instructions above)
```

#### Option 2: Network Share
```bash
# Share certificate via network
# Clients download and install manually
```

#### Option 3: MDM (Enterprise)
- Deploy certificate via MDM profile
- Automatic installation on all managed devices

## Verification

### Check Certificate Installation
```bash
# macOS
security find-certificate -c "Fleet Dashboard" \
  /Library/Keychains/System.keychain

# Should show certificate details
```

### Test in Browser
```bash
# Start Fleet server
python3 -m atlas.fleet_server

# Open browser
open https://192.168.1.100:8768

# Should show:
# ✅ Green padlock (secure connection)
# ❌ No security warnings
```

### Verify Certificate Details
```bash
# View certificate
openssl x509 -in ~/.fleet-certs/cert.pem -text -noout

# Check expiration
openssl x509 -in ~/.fleet-certs/cert.pem -noout -dates

# Verify key matches
openssl x509 -in ~/.fleet-certs/cert.pem -noout -modulus | md5
openssl rsa -in ~/.fleet-certs/privkey.pem -noout -modulus | md5
# Both should match
```

## Certificate Renewal

Self-signed certificates for internal use typically last 2+ years:

### Check Expiration
```python
from atlas.fleet_cert_auto import AutoCertificateManager
from datetime import datetime

manager = AutoCertificateManager()
info = manager.get_certificate_info()

if info:
    expires = info['not_after']
    days_left = (expires - datetime.now()).days
    print(f"Certificate expires in {days_left} days ({expires})")
```

### Renew Certificate
```bash
# Remove old certificate from trust store
sudo security delete-certificate -c "Fleet Dashboard" \
  /Library/Keychains/System.keychain

# Generate new certificate
python3 -m atlas.fleet_cert_auto setup

# Restart server
pkill -f fleet_server
python3 -m atlas.fleet_server
```

## Troubleshooting

### Issue: Browser Still Shows Warning
**Causes:**
- Certificate not installed in system trust
- Wrong IP address in certificate
- Browser cache

**Solutions:**
```bash
# Verify certificate is installed
security find-certificate -c "Fleet Dashboard" \
  /Library/Keychains/System.keychain

# Clear browser cache
# Chrome: Settings → Privacy → Clear browsing data
# Safari: Develop → Empty Caches

# Restart browser completely
```

### Issue: "Certificate Not Trusted"
**Solution:**
```bash
# Reinstall with correct trust level
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  ~/.fleet-certs/cert.pem
```

### Issue: Works on Server but Not Other Devices
**Solution:**
- Certificate must be installed on EACH device
- Export certificate and install on all client devices

### Issue: Certificate Expired
**Solution:**
```bash
# Generate new certificate
python3 -m atlas.fleet_cert_auto setup

# Update Fleet config if paths changed
# Restart server
```

## Security Considerations

### Pros
- ✅ Eliminates browser warnings
- ✅ Encrypted communication
- ✅ No external dependencies
- ✅ Works offline
- ✅ Free

### Cons
- ⚠️ Self-signed (not validated by CA)
- ⚠️ Must install on each device
- ⚠️ Manual renewal required
- ⚠️ Not suitable for public internet

### Best Practices
1. **Use for internal networks only**
2. **Protect private key** (600 permissions)
3. **Document certificate locations**
4. **Set calendar reminder for renewal**
5. **Keep backup of certificate**
6. **Use strong key size** (2048-bit minimum)

## Comparison: Internal IP vs Domain

| Feature | Internal IP (Self-Signed) | Domain (Let's Encrypt) |
|---------|---------------------------|------------------------|
| **Cost** | Free | Free |
| **Setup** | 5 minutes | 10 minutes |
| **Trust** | Manual install | Automatic |
| **Renewal** | Manual (~2 years) | Automatic (90 days) |
| **Multi-device** | Install on each | Automatic |
| **Internet Required** | No | Yes (for validation) |
| **Best For** | Internal networks | Public access |

## Automation

### Auto-Generate on Server Start
Add to server startup:

```python
# In fleet_server.py
from .fleet_cert_auto import AutoCertificateManager

def ensure_certificate(host):
    """Ensure certificate exists for host"""
    manager = AutoCertificateManager()
    
    cert_info = manager.get_certificate_info()
    if not cert_info:
        # No certificate, generate one
        logger.info(f"Generating certificate for {host}...")
        manager.generate_self_signed_cert(host)
    
    return manager.get_certificate_paths()

# Use in server initialization
if ssl_enabled and not cert_file:
    paths = ensure_certificate(local_ip)
    cert_file = paths['fullchain']
    key_file = paths['key']
```

### Scheduled Renewal
```bash
# Add to crontab (check monthly)
0 0 1 * * /usr/local/bin/python3 -c "from atlas.fleet_cert_auto import AutoCertificateManager; m = AutoCertificateManager(); info = m.get_certificate_info(); from datetime import datetime, timedelta; (info['not_after'] - datetime.now()).days < 30 and m.generate_self_signed_cert('192.168.1.100')"
```

## Summary

### For Internal IP (192.168.x.x, 10.x.x.x)
1. ✅ Use self-signed certificate
2. ✅ Install in system trust store
3. ✅ No browser warnings
4. ✅ Works offline
5. ✅ Free and simple

### For Public Domain (fleet.example.com)
1. ✅ Use Let's Encrypt
2. ✅ Automatic trust
3. ✅ Auto-renewal
4. ✅ No manual installation
5. ✅ Free and automatic

### Quick Decision Guide
- **Internal network only?** → Self-signed + system trust
- **Public internet access?** → Let's Encrypt
- **Both?** → Use domain with Let's Encrypt

## Next Steps

1. **Determine your setup**: Internal IP or domain?
2. **Run setup wizard**: `python3 -m atlas.fleet_cert_auto setup`
3. **Install certificate**: Choose option 1 for system trust
4. **Update Fleet config**: Add SSL certificate paths
5. **Restart server**: `python3 -m atlas.fleet_server`
6. **Test**: Open `https://YOUR_IP:8768` in browser
7. **Deploy to clients**: Install certificate on other devices

**No more security warnings!** 🔒✅
