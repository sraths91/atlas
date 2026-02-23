"""
Fleet Configuration Encryption
Handles secure storage of sensitive configuration data like API keys
"""

import json
import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    ENCRYPTION_AVAILABLE = True
except ImportError as e:
    ENCRYPTION_AVAILABLE = False
    logger.warning(f"cryptography package not available - config encryption disabled: {e}")


class EncryptedConfigManager:
    """Manages encrypted configuration files"""

    def __init__(self, config_path: str):
        config_path_obj = Path(config_path).expanduser()
        self.config_path = str(config_path_obj)
        self.encrypted_path = self.config_path + '.encrypted'
        self.salt_path = self.config_path + '.salt'  # Store salt separately
        self._cipher = None

        if not ENCRYPTION_AVAILABLE:
            logger.warning("Encryption not available - using plaintext config")

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create a new random one"""
        import secrets
        salt_file = Path(self.salt_path)
        if salt_file.exists():
            # Load existing salt
            try:
                return salt_file.read_bytes()
            except Exception as e:
                logger.warning(f"Could not load salt file, generating new one: {e}")

        # Generate new random salt (32 bytes = 256 bits)
        salt = secrets.token_bytes(32)

        # Save salt to file with restrictive permissions
        try:
            # Create parent directory if needed
            salt_file.parent.mkdir(parents=True, exist_ok=True)

            # Write salt file
            salt_file.write_bytes(salt)

            # Set restrictive permissions (owner read/write only)
            salt_file.chmod(0o600)

            logger.info(f"Generated new encryption salt: {self.salt_path}")
        except Exception as e:
            logger.error(f"Could not save salt file: {e}")

        return salt

    def _get_machine_key(self) -> bytes:
        """Generate a machine-specific encryption key using stable identifiers"""
        import platform
        import uuid
        import subprocess

        # Get stable hardware UUID (doesn't change on reboot or hostname change)
        hardware_uuid = None
        try:
            if platform.system() == 'Darwin':  # macOS
                result = subprocess.run(
                    ['system_profiler', 'SPHardwareDataType'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'Hardware UUID' in line:
                        hardware_uuid = line.split(':')[1].strip()
                        break
        except Exception:
            pass

        # Combine stable machine identifiers (avoid hostname which can change)
        machine_data = (
            (hardware_uuid or str(uuid.getnode())) +  # Hardware UUID or MAC address
            platform.machine() +  # Architecture (stable)
            platform.system()  # OS (stable)
        )

        # Get or create random salt (SECURITY FIX: no more static salt!)
        salt = self._get_or_create_salt()

        # Derive key using PBKDF2HMAC with random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,  # SECURITY: Use random salt instead of static
            iterations=600000,  # SECURITY: Increased from 100k to 600k (OWASP recommendation)
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_data.encode()))
        return key
    
    def _get_cipher(self):
        """Get or create Fernet cipher"""
        if not ENCRYPTION_AVAILABLE:
            return None
        
        if self._cipher is None:
            key = self._get_machine_key()
            self._cipher = Fernet(key)
        return self._cipher
    
    def encrypt_config(self, config: Dict[str, Any]) -> bool:
        """Encrypt and save configuration"""
        if not ENCRYPTION_AVAILABLE:
            # Fall back to plaintext
            logger.warning("Saving config in plaintext (encryption not available)")
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        
        try:
            cipher = self._get_cipher()
            
            # Convert config to JSON
            config_json = json.dumps(config, indent=2)
            
            # Encrypt
            encrypted_data = cipher.encrypt(config_json.encode())
            
            # Save encrypted data
            with open(self.encrypted_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            Path(self.encrypted_path).chmod(0o600)

            # Remove plaintext version if it exists
            config_file = Path(self.config_path)
            if config_file.exists():
                config_file.unlink()
            
            logger.info(f"Config encrypted and saved to {self.encrypted_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error encrypting config: {e}")
            return False
    
    def decrypt_config(self) -> Optional[Dict[str, Any]]:
        """Load and decrypt configuration"""
        # Try encrypted file first
        encrypted_file = Path(self.encrypted_path)
        if ENCRYPTION_AVAILABLE and encrypted_file.exists():
            try:
                cipher = self._get_cipher()
                
                with open(self.encrypted_path, 'rb') as f:
                    encrypted_data = f.read()
                
                # Decrypt
                decrypted_data = cipher.decrypt(encrypted_data)
                
                # Parse JSON
                config = json.loads(decrypted_data.decode())
                logger.info(f"Config decrypted from {self.encrypted_path}")
                return config
            
            except Exception as e:
                error_name = type(e).__name__
                if error_name == 'InvalidToken':
                    logger.error(f"Error decrypting config: Key mismatch - config was encrypted on a different machine or machine ID changed")
                    logger.error("Run 'python3 setup_atlas_config.py' to create a new configuration")
                else:
                    logger.error(f"Error decrypting config: {error_name}: {e}")
                return None
        
        # Fall back to plaintext
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.warning(f"Loaded plaintext config from {self.config_path}")
                
                # Automatically encrypt it
                if ENCRYPTION_AVAILABLE:
                    logger.info("Migrating plaintext config to encrypted format...")
                    self.encrypt_config(config)
                
                return config
            except Exception as e:
                logger.error(f"Error loading plaintext config: {e}")
                return None
        
        return None
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update specific config values"""
        config = self.decrypt_config() or {}
        
        # Deep merge updates
        def deep_update(base, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    deep_update(base[key], value)
                else:
                    base[key] = value
        
        deep_update(config, updates)
        
        return self.encrypt_config(config)
    
    def get_value(self, key_path: str, default=None):
        """Get a value from config using dot notation (e.g., 'server.api_key')"""
        config = self.decrypt_config()
        if not config:
            return default
        
        keys = key_path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value


def migrate_to_encrypted_config(plaintext_path: str) -> bool:
    """Migrate a plaintext config file to encrypted format"""
    if not ENCRYPTION_AVAILABLE:
        logger.warning("Cannot migrate - encryption not available")
        return False

    plaintext_file = Path(plaintext_path).expanduser()

    if not plaintext_file.exists():
        logger.warning(f"Config file not found: {plaintext_file}")
        return False

    try:
        # Load plaintext config
        with open(plaintext_file, 'r') as f:
            config = json.load(f)

        # Create encrypted version
        manager = EncryptedConfigManager(str(plaintext_file))
        success = manager.encrypt_config(config)
        
        if success:
            logger.info(f"Successfully migrated {plaintext_file} to encrypted format")
            return True
        else:
            logger.error("Failed to encrypt config")
            return False
            
    except Exception as e:
        logger.error(f"Error migrating config: {e}")
        return False


if __name__ == '__main__':
    # Test encryption
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'migrate':
        # Migrate existing config
        config_path = sys.argv[2] if len(sys.argv) > 2 else '~/.fleet-config.json'
        if migrate_to_encrypted_config(config_path):
            print(f"Successfully encrypted {config_path}")
        else:
            print(f"Failed to encrypt {config_path}")
    else:
        # Test encryption/decryption
        manager = EncryptedConfigManager('/tmp/test-config.json')
        
        test_config = {
            'server': {
                'api_key': 'test-secret-key-12345',
                'port': 8778
            },
            'organization': 'Test Org'
        }
        
        print("Testing encryption...")
        if manager.encrypt_config(test_config):
            print("Encryption successful")
            
            print("\nTesting decryption...")
            decrypted = manager.decrypt_config()
            if decrypted == test_config:
                print("Decryption successful")
                print(f"Decrypted config: {decrypted}")
            else:
                print("Decryption failed - data mismatch")
        else:
            print("Encryption failed")
