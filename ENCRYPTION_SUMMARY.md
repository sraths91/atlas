# Fleet Configuration Encryption

## Overview
The Fleet Dashboard now uses **AES-256 encryption** via Fernet (symmetric encryption) to protect sensitive configuration data, including API keys.

## Implementation Details

### Encryption Method
- **Algorithm**: AES-256 in CBC mode with HMAC authentication (Fernet)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations
- **Key Source**: Machine-specific identifiers (hostname, MAC address, architecture, OS)
- **Salt**: Static salt for consistency across restarts

### What's Encrypted
- **Server Config**: `~/.fleet-config.json.encrypted`
  - API keys
  - Server settings
  - Organization details
  - All sensitive configuration
- **Agent Config** (when using config files): `<config-path>.encrypted`
  - API keys
  - Server URLs
  - Agent settings
  - Machine identifiers

### Security Features
1. **Machine-Bound Encryption**: Keys are derived from machine-specific data, so encrypted configs can't be moved to other machines
2. **Automatic Migration**: Plaintext configs are automatically encrypted on first load
3. **Secure Permissions**: Encrypted files have 600 permissions (owner read/write only)
4. **Plaintext Removal**: Original plaintext files are deleted after encryption
5. **Fallback Support**: If encryption is unavailable, falls back to plaintext with warnings

### File Locations

#### Server
- **Encrypted**: `~/.fleet-config.json.encrypted` (binary, AES-256)
- **Plaintext** (removed): `~/.fleet-config.json`

#### Agent
- **Command-line agents**: API key passed as parameter (not stored)
- **Config-based agents**: 
  - **Encrypted**: `<config-path>.encrypted` (binary, AES-256)
  - **Plaintext** (auto-migrated): `<config-path>`
  - Same encryption as server
  - Automatic decryption on load

### Verification

Check if encryption is active:
```bash
# Server logs should show:
# "Loaded encrypted configuration"
# "Config encrypted and saved to ~/.fleet-config.json.encrypted"

# Verify encrypted file exists
ls -la ~/.fleet-config.json.encrypted

# Verify permissions (should be -rw-------)
stat -f "%Sp" ~/.fleet-config.json.encrypted

# Verify it's binary/encrypted (not readable)
head -c 50 ~/.fleet-config.json.encrypted
```

### API Key Management Workflow

1. **Initial Setup**: API key generated and stored in encrypted config
2. **Viewing Key**: Admin must authenticate with password to view key in settings
3. **Regeneration**: Requires password confirmation, updates encrypted config
4. **Agent Distribution**: Admins copy key from settings to configure remote agents

### Dependencies

Required Python package:
```bash
pip3 install cryptography
```

If not available, system falls back to plaintext with warnings in logs.

### Security Notes

- ✅ API keys are never logged
- ✅ Config files have restrictive permissions (600)
- ✅ Encryption keys are machine-bound
- ✅ Password required to view/regenerate API keys
- ✅ Automatic encryption of existing plaintext configs
- ⚠️  Encrypted configs cannot be transferred between machines
- ⚠️  If machine identifiers change (hostname, MAC), config must be re-created

### Troubleshooting

**Config not encrypting:**
- Check logs for "cryptography package not available"
- Install: `pip3 install cryptography`
- Restart server

**Cannot decrypt config:**
- Machine identifiers may have changed
- Restore from backup or regenerate config
- Check file permissions

**Viewing encrypted config:**
```python
from atlas.fleet_config_encryption import EncryptedConfigManager

manager = EncryptedConfigManager('~/.fleet-config.json')
config = manager.decrypt_config()
print(config)
```

## Testing Encryption

### Test Server Config
```bash
# Check server config is encrypted
ls -la ~/.fleet-config.json.encrypted

# Verify it's binary (not readable)
head -c 50 ~/.fleet-config.json.encrypted

# Test decryption
python3 << 'EOF'
from atlas.fleet_config_encryption import EncryptedConfigManager
manager = EncryptedConfigManager('~/.fleet-config.json')
config = manager.decrypt_config()
print(f"✅ Decrypted: {config is not None}")
print(f"✅ API Key present: {'server' in config and 'api_key' in config.get('server', {})}")
EOF
```

### Test Agent Config
```bash
# Create test agent config
python3 << 'EOF'
from atlas.fleet_config_encryption import EncryptedConfigManager

config = {
    "fleet_server": {
        "url": "http://192.168.50.191:8768",
        "api_key": "YOUR_API_KEY_HERE"
    },
    "agent": {"report_interval": 10},
    "machine_id": "TestAgent"
}

manager = EncryptedConfigManager('/tmp/test-agent.json')
manager.encrypt_config(config)
print("✅ Agent config encrypted")
EOF

# Test agent can load it
python3 -m atlas.fleet_agent --config /tmp/test-agent.json --help
# Should show: "Loaded encrypted configuration from /tmp/test-agent.json"
```

## Status

✅ **Server-side encryption**: ACTIVE
✅ **Agent-side encryption**: ACTIVE
✅ **API key protection**: ENABLED  
✅ **Automatic migration**: ENABLED
✅ **Password-protected viewing**: ENABLED
✅ **Secure regeneration**: ENABLED
✅ **Both server and agents can decrypt**: VERIFIED
