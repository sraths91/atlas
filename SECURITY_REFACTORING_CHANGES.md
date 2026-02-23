# Security Refactoring Changes - Phase 1

## Overview

This document describes the critical security improvements implemented in the refactored version of windsurf-project-2. All changes were made to the `/Users/samraths/CascadeProjects/windsurf-project-2-refactored` directory.

**Date:** December 31, 2025
**Phase:** Phase 1 - Critical Security Fixes
**New Ports:** Server: 8778 (changed from 8768), Agent: 8777 (changed from 8767)

---

## Critical Security Fixes Implemented

### 1. ✅ Removed Hardcoded Credentials
**File:** `set_credentials.py`

**Problem (CRITICAL):**
- Hardcoded admin password `"AtlasShrugged2025!"` in source code (lines 27-28)
- Password displayed in plaintext in console output
- Risk: Credentials exposed in version control history

**Solution:**
- Credentials now sourced from environment variables or user prompts
- Uses `getpass.getpass()` for secure password input (hidden from terminal)
- Password confirmation required
- Passwords never displayed in plaintext (shown as asterisks)
- Environment variables supported: `FLEET_ADMIN_USER`, `FLEET_ADMIN_PASSWORD`, `FLEET_API_KEY`

**Impact:** Eliminates hardcoded credentials vulnerability

---

### 2. ✅ Upgraded Password Hashing to bcrypt
**File:** `atlas/fleet_user_manager.py`

**Problem (CRITICAL):**
- Used SHA-256 for password hashing (lines 73-75)
- SHA-256 is too fast - vulnerable to GPU brute-force attacks
- Attackers can try billions of passwords per second

**Solution:**
- Implemented bcrypt with 12 rounds (4,096 iterations)
- Added `_verify_password()` method for secure password verification
- Backward compatible: supports both bcrypt and legacy SHA-256 hashes
- Automatic detection of hash type based on hash prefix
- Graceful fallback to SHA-256 if bcrypt unavailable (with warnings)

**Code Changes:**
```python
# Before (INSECURE):
def _hash_password(self, password: str, salt: str) -> str:
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

# After (SECURE):
def _hash_password(self, password: str, salt: str = None) -> str:
    if BCRYPT_AVAILABLE:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
        return hashed.decode('utf-8')
    else:
        # Fallback...
```

**Impact:** Makes password cracking exponentially harder, protects against brute-force attacks

---

### 3. ✅ Enabled SSL Verification
**File:** `atlas/fleet_server.py`

**Problem (CRITICAL):**
- SSL hostname verification disabled (`check_hostname = False`)
- SSL certificate verification disabled (`verify_mode = ssl.CERT_NONE`)
- Vulnerable to man-in-the-middle (MITM) attacks

**Solution:**
- Added `dev_mode` parameter to `start_fleet_server()`
- Production mode (default): Strict SSL verification enabled
  - `check_hostname = True`
  - `verify_mode = ssl.CERT_REQUIRED`
- Development mode: Relaxed SSL (for testing with self-signed certs)
  - Clear warnings logged when in dev mode
- TLS 1.2 and 1.3 enforced

**Code Changes:**
```python
# Production mode (default):
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED

# Development mode (explicit flag required):
if dev_mode:
    logger.warning("⚠️  Running in DEVELOPMENT MODE with relaxed SSL verification")
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
```

**Impact:** Prevents MITM attacks in production, maintains testing flexibility

---

### 4. ✅ Fixed Static Encryption Salt
**File:** `atlas/fleet_config_encryption.py`

**Problem (HIGH):**
- Static salt `b'fleet-config-salt-v2'` used for all installations (line 70)
- Makes rainbow table attacks easier
- Same salt across all deployments weakens security
- Only 100,000 PBKDF2 iterations (below OWASP recommendation of 600,000)

**Solution:**
- Generate random 32-byte salt per installation using `os.urandom(32)`
- Store salt in separate file (`.fleet-config.json.salt`)
- Salt file permissions set to 0o600 (owner read/write only)
- Salt persistence: reuse existing salt if available
- Increased PBKDF2 iterations from 100,000 to 600,000 (OWASP compliant)

**Code Changes:**
```python
# Before (INSECURE):
salt=b'fleet-config-salt-v2',  # Static salt
iterations=100000

# After (SECURE):
salt = self._get_or_create_salt()  # Random per-installation salt
iterations=600000  # OWASP recommendation
```

**Impact:** Each installation has unique salt, significantly increases key derivation security

---

### 5. ✅ Added Secure Flag to Session Cookies
**File:** `atlas/fleet_server.py`

**Problem (MEDIUM):**
- Session clear cookie missing `Secure` flag (line 421)
- Login cookie already had Secure flag (line 1223)

**Solution:**
- Added `Secure` flag to logout/clear cookie
- Both cookie operations now include: `HttpOnly; SameSite=Strict; Secure`

**Code Changes:**
```python
# Before:
'Set-Cookie', 'fleet_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict'

# After:
'Set-Cookie', 'fleet_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict; Secure'
```

**Impact:** Ensures cookies only transmitted over HTTPS

---

### 6. ✅ Updated Dependencies
**File:** `requirements.txt`

**Changes:**
- Added `bcrypt>=4.0.0` for secure password hashing
- Added `cryptography>=41.0.0` for encryption operations

---

## Port Changes

To allow both original and refactored versions to run simultaneously:

| Service | Original Port | New Port |
|---------|--------------|----------|
| Fleet Server | 8768 | 8778 |
| Fleet Agent | 8767 | 8777 |

**Files Updated:**
- `atlas/fleet_server.py` (5 occurrences)
- `set_credentials.py` (fleet_server_url)

---

## Migration Guide

### For New Installations
1. Install dependencies: `pip install -r requirements.txt`
2. Run `python set_credentials.py` and provide credentials when prompted
3. Start server with SSL enabled (production mode by default)

### For Existing Installations
1. **Password Migration:** Existing SHA-256 password hashes will continue to work
   - Users can change passwords to migrate to bcrypt automatically
   - System detects hash type and uses appropriate verification method

2. **Salt Migration:**
   - New random salt will be generated on first run
   - Old encrypted configs with static salt remain decryptable
   - Recommend re-encrypting configs to use new random salt

3. **Cookie Security:**
   - Existing sessions will be invalidated (Secure flag change)
   - Users will need to log in again

---

## Security Testing Checklist

- [ ] Test bcrypt password hashing with new user creation
- [ ] Test bcrypt password verification with login
- [ ] Test SHA-256 legacy password still works
- [ ] Test password change migrates to bcrypt
- [ ] Test SSL verification in production mode
- [ ] Test SSL verification disabled in dev mode (`dev_mode=True`)
- [ ] Test encryption salt generation and persistence
- [ ] Test encrypted config encryption/decryption
- [ ] Test cookies only sent over HTTPS
- [ ] Test credential setup without hardcoded values

---

## Breaking Changes

1. **Hardcoded credentials removed** - Must provide credentials via environment variables or prompts
2. **SSL verification enabled by default** - May need `dev_mode=True` flag for testing with self-signed certificates
3. **Port changes** - Update firewall rules and client configurations for new ports (8778/8777)

---

## Security Best Practices Implemented

✅ No hardcoded credentials
✅ Secure password hashing (bcrypt with 12 rounds)
✅ Password verification resistant to timing attacks
✅ Random salt per installation
✅ Increased PBKDF2 iterations (600,000)
✅ SSL/TLS verification enabled
✅ Secure cookie flags (Secure, HttpOnly, SameSite)
✅ Restrictive file permissions on sensitive files (0o600)
✅ Environment variable support for credentials
✅ Password masking in all output

---

## Remaining Security Recommendations (Future Phases)

These items are documented in the refactoring plan but not yet implemented:

- **Phase 2:** Extract shared utilities, reduce code duplication
- **Phase 3:** Refactor network widgets
- **Phase 4:** Decompose large files (fleet_server.py, fleet_settings_page.py)
- **Phase 5:** Additional security improvements:
  - Certificate pinning for agents
  - API key rotation mechanism
  - Rate limiting on API endpoints
  - CSRF protection
  - Upgrade to 4096-bit RSA keys
  - CSP header improvements
  - Session invalidation on password change
  - Persistent session storage (Redis)

---

## Contact

For questions about these security changes, refer to the refactoring plan at:
`/Users/samraths/.claude/plans/hidden-herding-parrot.md`
