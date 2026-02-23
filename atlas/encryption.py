"""
End-to-End Encryption for Fleet Agent
Uses AES-256-GCM for payload encryption
"""
import os
import base64
import hashlib
import json
import logging
from typing import Dict, Any, Optional, Tuple

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    ENCRYPTION_AVAILABLE = True
except ImportError as e:
    ENCRYPTION_AVAILABLE = False
    import logging
    logging.debug(f"Cryptography not available: {e}")

logger = logging.getLogger(__name__)


class DataEncryption:
    """
    Handle end-to-end encryption of data payloads
    Uses AES-256-GCM for authenticated encryption
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with a key
        
        Args:
            encryption_key: Base64-encoded 256-bit encryption key
                           If None, encryption is disabled
        """
        self.enabled = False
        self.cipher = None
        
        if not ENCRYPTION_AVAILABLE:
            logger.warning("cryptography library not available - encryption disabled")
            return
        
        if encryption_key:
            try:
                # Decode the base64 key
                key_bytes = base64.b64decode(encryption_key)
                
                # Verify key length (should be 32 bytes for AES-256)
                if len(key_bytes) != 32:
                    raise ValueError(f"Invalid key length: {len(key_bytes)} bytes (expected 32)")
                
                # Initialize AES-GCM cipher
                self.cipher = AESGCM(key_bytes)
                self.enabled = True
                logger.info("End-to-end encryption enabled (AES-256-GCM)")
                
            except Exception as e:
                logger.error(f"Failed to initialize encryption: {e}")
                self.enabled = False
        else:
            logger.warning("No encryption key provided - data will be sent unencrypted")
    
    def encrypt_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt a data payload
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Dictionary with encrypted data or original if encryption disabled
        """
        if not self.enabled:
            # Return unencrypted data
            return data
        
        try:
            # Convert data to JSON bytes
            json_data = json.dumps(data).encode('utf-8')
            
            # Generate random nonce (96 bits for GCM)
            nonce = os.urandom(12)
            
            # Encrypt data with authenticated encryption
            ciphertext = self.cipher.encrypt(nonce, json_data, None)
            
            # Return encrypted payload
            encrypted_payload = {
                'encrypted': True,
                'version': '1',
                'nonce': base64.b64encode(nonce).decode('utf-8'),
                'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
            }
            
            logger.debug("Payload encrypted successfully")
            return encrypted_payload
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            # Fall back to unencrypted
            return data
    
    def decrypt_payload(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt an encrypted payload
        
        Args:
            encrypted_data: Dictionary with encrypted data
            
        Returns:
            Decrypted dictionary
        """
        if not self.enabled:
            return encrypted_data
        
        try:
            # Check if data is encrypted
            if not encrypted_data.get('encrypted'):
                return encrypted_data
            
            # Extract nonce and ciphertext
            nonce = base64.b64decode(encrypted_data['nonce'])
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            
            # Decrypt data
            plaintext = self.cipher.decrypt(nonce, ciphertext, None)
            
            # Parse JSON
            data = json.loads(plaintext.decode('utf-8'))
            
            logger.debug("Payload decrypted successfully")
            return data
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt payload: {e}")
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new random 256-bit encryption key
        
        Returns:
            Base64-encoded key string
        """
        if not ENCRYPTION_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        # Generate 32 random bytes (256 bits)
        key = os.urandom(32)
        
        # Encode as base64 for easy storage/transmission
        return base64.b64encode(key).decode('utf-8')
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """
        Derive an encryption key from a password using PBKDF2
        
        Args:
            password: Password string
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (base64_key, base64_salt)
        """
        if not ENCRYPTION_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        # Generate salt if not provided
        if salt is None:
            salt = os.urandom(16)
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode('utf-8'))
        
        # Return both key and salt as base64
        return (
            base64.b64encode(key).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )


def generate_encryption_key() -> None:
    """
    CLI utility to generate a new encryption key
    """
    if not ENCRYPTION_AVAILABLE:
        print("ERROR: cryptography library not installed")
        print("Install with: pip install cryptography")
        return
    
    key = DataEncryption.generate_key()
    print("\n" + "="*70)
    print("NEW ENCRYPTION KEY GENERATED")
    print("="*70)
    print(f"\nKey: {key}")
    print("\nAdd this to your configuration:")
    print(f'  "encryption_key": "{key}"')
    print("\nIMPORTANT:")
    print("- Store this key securely")
    print("- Use the same key on both agent and server")
    print("- Never commit this key to version control")
    print("- Rotate keys periodically")
    print("="*70 + "\n")


if __name__ == '__main__':
    generate_encryption_key()
