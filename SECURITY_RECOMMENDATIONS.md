# 🔒 Fleet Server Security Recommendations

## 📊 Current Security Status

### ✅ Already Implemented (Strong Foundation!)

| Security Feature | Status | Details |
|-----------------|--------|---------|
| **SSL/TLS Encryption** | ✅ Active | Self-signed certificate, valid until 2028 |
| **Password Hashing** | ✅ Active | SHA-256 with random salt |
| **Password Complexity** | ✅ Active | 12+ chars, mixed case, numbers, symbols |
| **Brute Force Protection** | ✅ Active | Login attempt tracking per IP |
| **Session Management** | ✅ Active | HttpOnly, SameSite=Strict cookies |
| **API Key Authentication** | ✅ Active | For agent communications |
| **Cluster Node Auth** | ✅ Active | HMAC-SHA256 signatures |
| **Agent Payload Encryption** | ✅ Active | AES-256-GCM (if configured) |
| **Database Encryption** | ✅ Active | Optional encryption at rest |
| **Redis Password** | ✅ Active | Optional backend authentication |

---

## 🚨 Security Improvements Recommended

### **Priority 1: Critical** 🔴

#### 1. **Add Secure Flag to Cookies**

**Location:** `fleet_server.py` line 986

**Current:**
```python
Set-Cookie: fleet_session={token}; Path=/; Max-Age=28800; HttpOnly; SameSite=Strict
```

**Should be:**
```python
Set-Cookie: fleet_session={token}; Path=/; Max-Age=28800; HttpOnly; SameSite=Strict; Secure
```

**Fix:**
```python
# Replace line 986:
self.send_header('Set-Cookie', 
    f'fleet_session={session_token}; Path=/; Max-Age=28800; '
    f'HttpOnly; SameSite=Strict; Secure')
```

**Impact:** Prevents cookies from being sent over unencrypted HTTP

---

#### 2. **Restrict CORS (Cross-Origin Resource Sharing)**

**Location:** `fleet_server.py` lines 246, 254, 293

**Current:**
```python
Access-Control-Allow-Origin: *  # ❌ Allows ANY website
```

**Should be:**
```python
# Option A: No CORS (most secure for internal use)
# Remove Access-Control-Allow-Origin header entirely

# Option B: Specific origins only
Access-Control-Allow-Origin: https://192.168.50.191:8768
```

**Fix:**
```python
# In _send_json and _send_html methods:
# REMOVE this line:
# self.send_header('Access-Control-Allow-Origin', '*')

# Or replace with:
allowed_origin = 'https://192.168.50.191:8768'
self.send_header('Access-Control-Allow-Origin', allowed_origin)
```

**Impact:** Prevents malicious websites from accessing your Fleet Server API

---

### **Priority 2: High** 🟠

#### 3. **Add Security Headers**

**Location:** `fleet_server.py` in `_send_html` and `_send_json` methods

**Missing headers:**
```python
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: default-src 'self'
X-XSS-Protection: 1; mode=block
Referrer-Policy: no-referrer-when-downgrade
```

**Fix:** Use the `SecurityHeaders` class I just created:

```python
# In fleet_server.py, add to imports:
from .security_headers import SecurityHeaders

# In FleetServerHandler.__init__:
self.security_headers = SecurityHeaders(
    use_ssl=bool(ssl_cert),
    allowed_origins=[]  # No CORS for security
)

# In _send_html and _send_json methods, add:
headers = self.security_headers.get_security_headers()
for key, value in headers.items():
    self.send_header(key, value)
```

**Impact:** Protects against clickjacking, XSS, MIME sniffing, and other attacks

---

#### 4. **Upgrade Password Hashing Algorithm**

**Location:** `fleet_user_manager.py` line 74-75

**Current:**
```python
def _hash_password(self, password: str, salt: str) -> str:
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
```

**Problem:** SHA-256 is too fast for password hashing (attackers can brute force faster)

**Should use:**
```python
# Install: pip install bcrypt
import bcrypt

def _hash_password(self, password: str, salt: bytes = None) -> bytes:
    if salt is None:
        salt = bcrypt.gensalt(rounds=12)  # Work factor
    return bcrypt.hashpw(password.encode(), salt)
```

**Impact:** Makes brute force attacks 10,000x slower if database is compromised

**Note:** This requires database migration for existing users

---

### **Priority 3: Medium** 🟡

#### 5. **Add Rate Limiting on API Endpoints**

**Location:** `fleet_server.py` in API handler methods

**Current:** No rate limiting (can be abused)

**Should add:**
```python
# Use RateLimiter class from security_headers.py
from .security_headers import RateLimiter

# In FleetServerHandler.__init__:
self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

# In do_POST before processing:
client_ip = self.client_address[0]
if not self.rate_limiter.is_allowed(client_ip):
    self._send_json({'error': 'Rate limit exceeded'}, 429)
    return
```

**Impact:** Prevents API abuse and DoS attacks

---

#### 6. **Reduce Session Timeout**

**Location:** `fleet_server.py` line 986

**Current:**
```python
Max-Age=28800  # 8 hours
```

**Recommended for production:**
```python
Max-Age=3600   # 1 hour
# or
Max-Age=7200   # 2 hours
```

**Impact:** Reduces window for session hijacking

---

#### 7. **Add CSRF Protection**

**Location:** Login and API forms

**Current:** No CSRF tokens

**Should add:**
```python
# Generate CSRF token with session
csrf_token = secrets.token_urlsafe(32)
session_data['csrf_token'] = csrf_token

# Validate on form submission
if request_csrf_token != session_csrf_token:
    return error("CSRF token mismatch")
```

**Impact:** Prevents cross-site request forgery attacks

---

### **Priority 4: Low** 🟢

#### 8. **Add Security Logging**

**Recommend logging:**
```python
# Failed login attempts (already tracked)
# API authentication failures
# Rate limit violations
# Invalid CSRF tokens
# Suspicious activity patterns
```

---

#### 9. **Input Validation**

**Add validation for:**
```python
# Username: alphanumeric only, max length
# Hostnames: valid DNS format
# IP addresses: valid IP format
# Ports: 1-65535 range
# File paths: prevent directory traversal
```

---

## 🛠️ Implementation Guide

### **Quick Wins (< 30 minutes)**

**1. Add Secure Cookie Flag:**

```bash
# Edit fleet_server.py line 986:
sed -i '' 's/SameSite=Strict/SameSite=Strict; Secure/' atlas/fleet_server.py
```

**2. Remove CORS (if not needed):**

```python
# In fleet_server.py, comment out lines 246, 254, 293:
# self.send_header('Access-Control-Allow-Origin', '*')
```

**3. Reduce Session Timeout:**

```bash
# Edit fleet_server.py line 986:
sed -i '' 's/Max-Age=28800/Max-Age=3600/' atlas/fleet_server.py
```

---

### **Moderate Effort (1-2 hours)**

**4. Add Security Headers:**

```python
# 1. Already created: atlas/security_headers.py
# 2. Import and use in fleet_server.py:

from .security_headers import SecurityHeaders

# In FleetServerHandler:
self.security_headers = SecurityHeaders(use_ssl=True)

# In _send_html and _send_json:
for key, value in self.security_headers.get_security_headers().items():
    self.send_header(key, value)
```

**5. Add Rate Limiting:**

```python
# Use RateLimiter from security_headers.py:

from .security_headers import RateLimiter

self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

# In do_POST:
if not self.rate_limiter.is_allowed(self.client_address[0]):
    self._send_json({'error': 'Rate limit exceeded'}, 429)
    return
```

---

### **Larger Projects (4+ hours)**

**6. Upgrade Password Hashing:**

```bash
# 1. Install bcrypt
pip install bcrypt

# 2. Modify fleet_user_manager.py
# 3. Create migration script for existing users
# 4. Test thoroughly before deploying
```

**7. Add CSRF Protection:**

```python
# 1. Generate CSRF tokens with sessions
# 2. Add hidden fields to forms
# 3. Validate tokens on submission
# 4. Return 403 on mismatch
```

---

## 📋 Security Checklist

### **Pre-Production Checklist:**

- [ ] **SSL/TLS enabled** with valid certificate
- [ ] **Secure cookie flag** added to session cookies
- [ ] **CORS restricted** or disabled
- [ ] **Security headers** added (X-Frame-Options, CSP, etc.)
- [ ] **Rate limiting** enabled on API endpoints
- [ ] **Password hashing** upgraded to bcrypt/argon2
- [ ] **Session timeout** reduced to 1-2 hours
- [ ] **CSRF protection** added to forms
- [ ] **Security logging** implemented
- [ ] **Input validation** added to all user inputs
- [ ] **Firewall rules** configured (only required ports open)
- [ ] **Database encrypted** (if storing sensitive data)
- [ ] **Cluster secret** configured (if using clustering)
- [ ] **Redis password** set (if using Redis)
- [ ] **Strong admin password** set (12+ chars, complexity rules)
- [ ] **Failed login** monitoring enabled
- [ ] **Regular security updates** planned

---

## 🎯 Recommended Configuration

### **Production Config (config.yaml):**

```yaml
organization:
  name: "Your Organization"

server:
  host: "0.0.0.0"
  port: 8768
  
  # Strong credentials
  api_key: "generate_strong_random_key_32_chars"
  web_username: "admin"
  web_password: "Strong!Password123$WithSymbols"
  
  # Enable encryption
  encryption_key: "base64_encoded_256_bit_key"
  db_encryption_key: "base64_encoded_db_key"
  
  # Security settings
  session_timeout: 3600  # 1 hour
  max_login_attempts: 5
  lockout_duration: 900  # 15 minutes

ssl:
  enabled: true
  cert_file: "/path/to/cert.pem"
  key_file: "/path/to/privkey.pem"

cluster:
  enabled: true
  
  # Critical: Set cluster secret for node authentication
  cluster_secret: "base64_encoded_cluster_secret"
  
  # Secure Redis
  redis_host: "10.0.1.50"
  redis_port: 6379
  redis_password: "strong_redis_password"
  redis_db: 0

security:
  # New section (if implementing)
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
  
  cors:
    enabled: false
    allowed_origins: []
  
  headers:
    strict_transport_security: true
    content_security_policy: true
    x_frame_options: "DENY"
```

---

## 🔐 Security Best Practices

### **1. Credential Management:**

```bash
# Generate strong random keys:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Store securely:
- Use environment variables for production
- Never commit credentials to git
- Rotate keys regularly (every 90 days)
```

### **2. Network Security:**

```bash
# Firewall rules:
sudo ufw allow 8768/tcp  # Fleet Server
sudo ufw allow 6379/tcp from 10.0.1.0/24  # Redis (cluster only)
sudo ufw enable

# Private network for cluster:
- Use VPN or private VLAN
- Restrict Redis to cluster IPs only
- No public internet access to Redis
```

### **3. Monitoring:**

```bash
# Watch logs for:
- Failed login attempts (> 5 from same IP)
- Rate limit violations
- Invalid API keys
- Unusual traffic patterns
- Error spikes

# Set up alerts:
tail -f /var/log/fleet-server.log | grep -i "error\|fail\|attack\|violation"
```

### **4. Regular Updates:**

```bash
# Keep dependencies updated:
pip list --outdated
pip install --upgrade package_name

# Security patches:
- Monitor security advisories
- Test updates in staging
- Apply patches within 30 days
```

---

## ✅ Summary

### **Current Security Rating: B+**

**Strengths:**
- ✅ Strong encryption (SSL/TLS, AES-256-GCM)
- ✅ Good authentication (sessions, API keys, cluster secrets)
- ✅ Password complexity requirements
- ✅ Brute force protection

**Weaknesses:**
- ⚠️ Missing security headers
- ⚠️ CORS wide open
- ⚠️ No Secure cookie flag
- ⚠️ SHA-256 for passwords (should use bcrypt)
- ⚠️ No rate limiting

### **With Recommended Fixes: A**

Implementing the Priority 1 and Priority 2 fixes will bring security to production-grade levels.

### **Priority Order:**

1. **Add Secure cookie flag** (5 minutes) 🔴
2. **Restrict/remove CORS** (5 minutes) 🔴
3. **Add security headers** (30 minutes) 🟠
4. **Add rate limiting** (1 hour) 🟠
5. **Upgrade password hashing** (4 hours) 🟡
6. **Add CSRF protection** (2 hours) 🟡

**Your security foundation is solid - these improvements will make it excellent!** 🔒✨
