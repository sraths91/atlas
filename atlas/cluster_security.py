"""
Cluster Node Authentication and Data Security
Provides authentication and integrity protection for cluster communications
"""
import os
import json
import hmac
import hashlib
import base64
import time
import logging
from typing import Dict, Any, Optional, Tuple

# Try to import cryptography for HKDF (secure key derivation)
try:
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    HKDF_AVAILABLE = True
except ImportError:
    HKDF_AVAILABLE = False

logger = logging.getLogger(__name__)


class ClusterSecurity:
    """
    Handle authentication and data signing for cluster nodes
    
    Features:
    - Node authentication via shared secret
    - HMAC-SHA256 signatures for data integrity
    - Timestamp validation to prevent replay attacks
    - Node registration verification
    """
    
    def __init__(self, cluster_secret: str):
        """
        Initialize cluster security
        
        Args:
            cluster_secret: Shared secret key for cluster authentication (base64)
        """
        self.enabled = bool(cluster_secret)
        
        if cluster_secret:
            try:
                # Decode the base64 secret
                self.secret = base64.b64decode(cluster_secret)

                # SECURITY: Enforce minimum secret length (32 bytes = 256 bits)
                if len(self.secret) < 32:
                    error_msg = f"Cluster secret too short ({len(self.secret)} bytes). Minimum 32 bytes required for security."
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.info("Cluster authentication enabled (HMAC-SHA256 + HKDF)")
            except Exception as e:
                logger.error(f"Failed to initialize cluster security: {e}")
                self.enabled = False
                self.secret = None
        else:
            self.secret = None
            logger.warning(" Cluster authentication DISABLED - nodes can join without verification!")

    def _derive_encryption_key(self) -> bytes:
        """
        Derive a 32-byte encryption key from the cluster secret using HKDF

        SECURITY: This replaces the insecure ljust() method with proper key derivation.
        Uses HKDF (HMAC-based Key Derivation Function) as recommended by NIST SP 800-108.

        Returns:
            32-byte encryption key
        """
        if not self.secret:
            raise ValueError("No cluster secret available for key derivation")

        if HKDF_AVAILABLE:
            # Use HKDF for secure key derivation (RECOMMENDED)
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,  # Output 32 bytes for AES-256
                salt=b'cluster-encryption-v1',  # Fixed salt for deterministic derivation
                info=b'',  # Optional context info
                backend=default_backend()
            )
            derived_key = hkdf.derive(self.secret)
            return derived_key
        else:
            # Fallback: Use first 32 bytes or pad with zeros (NOT RECOMMENDED)
            # This maintains backward compatibility if cryptography is not available
            logger.warning("HKDF not available - using fallback key derivation (NOT RECOMMENDED)")
            enc_key = self.secret[:32] if len(self.secret) >= 32 else self.secret.ljust(32, b'\x00')
            return enc_key

    def sign_node_data(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign node data with HMAC for integrity protection
        
        Args:
            node_data: Node information dictionary
            
        Returns:
            Node data with signature and timestamp
        """
        if not self.enabled:
            # Return unsigned data
            return node_data
        
        try:
            # Add timestamp to prevent replay attacks
            signed_data = node_data.copy()
            signed_data['_timestamp'] = int(time.time())
            signed_data['_security_version'] = '1.0'
            
            # Create canonical JSON (sorted keys) for consistent signing
            canonical = json.dumps(signed_data, sort_keys=True, separators=(',', ':'))
            
            # Generate HMAC signature
            signature = hmac.new(
                self.secret,
                canonical.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            # Add signature to data
            signed_data['_signature'] = base64.b64encode(signature).decode('utf-8')
            
            logger.debug(f"Node data signed: {node_data.get('node_id', 'unknown')}")
            return signed_data
            
        except Exception as e:
            logger.error(f"Failed to sign node data: {e}")
            return node_data
    
    def verify_node_data(self, signed_data: Dict[str, Any], 
                        max_age_seconds: int = 300) -> Tuple[bool, Optional[str]]:
        """
        Verify node data signature and timestamp
        
        Args:
            signed_data: Node data with signature
            max_age_seconds: Maximum age of timestamp (default 5 minutes)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.enabled:
            # No verification when disabled
            return (True, None)
        
        try:
            # Check required fields
            if '_signature' not in signed_data:
                return (False, "Missing signature")
            
            if '_timestamp' not in signed_data:
                return (False, "Missing timestamp")
            
            # Extract signature
            provided_signature = signed_data['_signature']
            
            # Create canonical data (without signature)
            data_to_verify = {k: v for k, v in signed_data.items() if k != '_signature'}
            canonical = json.dumps(data_to_verify, sort_keys=True, separators=(',', ':'))
            
            # Compute expected signature
            expected_signature_bytes = hmac.new(
                self.secret,
                canonical.encode('utf-8'),
                hashlib.sha256
            ).digest()
            expected_signature = base64.b64encode(expected_signature_bytes).decode('utf-8')
            
            # Verify signature with timing-safe comparison
            if not hmac.compare_digest(provided_signature, expected_signature):
                logger.warning(f"Invalid signature for node: {signed_data.get('node_id', 'unknown')}")
                return (False, "Invalid signature - node authentication failed")
            
            # Verify timestamp (prevent replay attacks)
            timestamp = signed_data['_timestamp']
            age = int(time.time()) - timestamp
            
            if age < 0:
                return (False, "Timestamp is in the future")
            
            if age > max_age_seconds:
                return (False, f"Timestamp too old ({age}s > {max_age_seconds}s)")
            
            logger.debug(f"Node data verified: {signed_data.get('node_id', 'unknown')}")
            return (True, None)
            
        except Exception as e:
            logger.error(f"Failed to verify node data: {e}")
            return (False, f"Verification error: {str(e)}")
    
    def sign_heartbeat(self, node_id: str, timestamp: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a signed heartbeat message
        
        Args:
            node_id: Node identifier
            timestamp: Unix timestamp (defaults to now)
            
        Returns:
            Signed heartbeat dictionary
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        heartbeat = {
            'node_id': node_id,
            'timestamp': timestamp,
            'type': 'heartbeat'
        }
        
        return self.sign_node_data(heartbeat)
    
    def verify_heartbeat(self, heartbeat: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Verify a heartbeat message
        
        Args:
            heartbeat: Heartbeat dictionary with signature
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Heartbeats should be recent (within 30 seconds)
        return self.verify_node_data(heartbeat, max_age_seconds=30)
    
    def encrypt_cluster_data(self, data: Dict[str, Any]) -> str:
        """
        Encrypt sensitive cluster data (optional additional layer)
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        if not self.enabled:
            return json.dumps(data)
        
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import os

            # SECURITY FIX: Use HKDF for secure key derivation instead of ljust()
            enc_key = self._derive_encryption_key()

            # Create cipher
            cipher = AESGCM(enc_key)
            
            # Encrypt data
            json_data = json.dumps(data).encode('utf-8')
            nonce = os.urandom(12)
            ciphertext = cipher.encrypt(nonce, json_data, None)
            
            # Return nonce + ciphertext as base64
            encrypted = base64.b64encode(nonce + ciphertext).decode('utf-8')
            return encrypted
            
        except ImportError:
            logger.warning("cryptography not available, using signed but unencrypted data")
            return json.dumps(data)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return json.dumps(data)
    
    def decrypt_cluster_data(self, encrypted: str) -> Dict[str, Any]:
        """
        Decrypt cluster data
        
        Args:
            encrypted: Encrypted data as base64 string
            
        Returns:
            Decrypted data dictionary
        """
        if not self.enabled:
            return json.loads(encrypted)
        
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            # SECURITY FIX: Use HKDF for secure key derivation instead of ljust()
            enc_key = self._derive_encryption_key()

            # Create cipher
            cipher = AESGCM(enc_key)
            
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted)
            
            # Extract nonce and ciphertext
            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]
            
            # Decrypt
            plaintext = cipher.decrypt(nonce, ciphertext, None)
            
            # Parse JSON
            data = json.loads(plaintext.decode('utf-8'))
            return data
            
        except ImportError:
            return json.loads(encrypted)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt cluster data: {e}")
    
    @staticmethod
    def generate_cluster_secret() -> str:
        """
        Generate a new random cluster secret
        
        Returns:
            Base64-encoded secret string (256 bits)
        """
        # Generate 32 random bytes (256 bits)
        secret = os.urandom(32)
        
        # Encode as base64
        return base64.b64encode(secret).decode('utf-8')
    
    def get_security_status(self) -> Dict[str, Any]:
        """
        Get current security configuration status
        
        Returns:
            Dictionary with security status
        """
        return {
            'enabled': self.enabled,
            'authentication': 'HMAC-SHA256' if self.enabled else 'DISABLED',
            'signing': 'enabled' if self.enabled else 'disabled',
            'replay_protection': 'enabled' if self.enabled else 'disabled',
            'warning': None if self.enabled else ' Cluster nodes can join without authentication!'
        }


def generate_cluster_secret_for_config() -> str:
    """
    Utility function to generate a cluster secret for configuration
    
    Returns:
        Base64-encoded cluster secret
    """
    return ClusterSecurity.generate_cluster_secret()


# Example usage:
if __name__ == '__main__':
    # Generate a new cluster secret
    secret = ClusterSecurity.generate_cluster_secret()
    print(f"New cluster secret: {secret}")
    print("\nAdd this to your config.yaml:")
    print(f"cluster:")
    print(f"  cluster_secret: '{secret}'")
    
    # Test signing and verification
    security = ClusterSecurity(secret)
    
    node_data = {
        'node_id': 'server-01',
        'host': '10.0.1.100',
        'port': 8778,
        'status': 'active'
    }
    
    # Sign
    signed = security.sign_node_data(node_data)
    print(f"\nSigned node data: {json.dumps(signed, indent=2)}")
    
    # Verify
    valid, error = security.verify_node_data(signed)
    print(f"\nVerification: {'VALID' if valid else f'INVALID - {error}'}")
    
    # Test tampering
    signed['host'] = '10.0.0.666'
    valid, error = security.verify_node_data(signed)
    print(f"After tampering: {'VALID' if valid else f'INVALID - {error}'}")
