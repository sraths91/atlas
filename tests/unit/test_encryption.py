"""
Unit Tests for atlas.encryption.DataEncryption

Tests key generation, encrypt/decrypt roundtrips, disabled mode,
invalid keys, wrong-key decryption, and complex payloads.
"""
import pytest
import base64

from atlas.encryption import DataEncryption, ENCRYPTION_AVAILABLE

# Skip the entire module if the cryptography library is not installed
pytestmark = pytest.mark.skipif(
    not ENCRYPTION_AVAILABLE,
    reason="cryptography library not installed"
)


@pytest.mark.unit
class TestDataEncryption:
    """Tests for DataEncryption (AES-256-GCM)."""

    def test_generate_key(self):
        """generate_key returns a base64 string that decodes to 32 bytes."""
        key_str = DataEncryption.generate_key()
        assert isinstance(key_str, str)

        key_bytes = base64.b64decode(key_str)
        assert len(key_bytes) == 32

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting a payload recovers the original data."""
        key = DataEncryption.generate_key()
        enc = DataEncryption(key)
        assert enc.enabled is True

        original = {'hello': 'world'}
        encrypted = enc.encrypt_payload(original)

        # Encrypted payload should have the marker fields
        assert encrypted.get('encrypted') is True
        assert 'nonce' in encrypted
        assert 'ciphertext' in encrypted

        decrypted = enc.decrypt_payload(encrypted)
        assert decrypted == original

    def test_disabled_without_key(self):
        """DataEncryption(None) is disabled; encrypt_payload returns data unchanged."""
        enc = DataEncryption(None)
        assert enc.enabled is False

        data = {'status': 'ok', 'value': 42}
        result = enc.encrypt_payload(data)
        assert result is data  # same object, not a copy

    def test_invalid_key_length(self):
        """A key that is not 32 bytes results in enabled=False."""
        short_key = base64.b64encode(b'short').decode()
        enc = DataEncryption(short_key)
        assert enc.enabled is False

    def test_decrypt_non_encrypted(self):
        """Decrypting data without the 'encrypted' flag returns it unchanged."""
        key = DataEncryption.generate_key()
        enc = DataEncryption(key)

        plain_data = {'some': 'data', 'count': 5}
        result = enc.decrypt_payload(plain_data)
        assert result == plain_data

    def test_decrypt_wrong_key(self):
        """Decrypting with a different key raises ValueError."""
        key1 = DataEncryption.generate_key()
        key2 = DataEncryption.generate_key()

        enc1 = DataEncryption(key1)
        enc2 = DataEncryption(key2)

        original = {'secret': 'message'}
        encrypted = enc1.encrypt_payload(original)

        with pytest.raises(ValueError, match="Failed to decrypt"):
            enc2.decrypt_payload(encrypted)

    def test_encrypt_complex_payload(self):
        """Encrypt/decrypt a nested dict with lists, ints, floats, and nulls."""
        key = DataEncryption.generate_key()
        enc = DataEncryption(key)

        complex_data = {
            'string': 'hello',
            'integer': 42,
            'float': 3.14159,
            'null_value': None,
            'boolean': True,
            'nested': {
                'list': [1, 2, 3, 'four', None],
                'deep': {
                    'key': 'value',
                    'numbers': [0.1, 0.2, 0.3],
                },
            },
            'empty_list': [],
            'empty_dict': {},
        }

        encrypted = enc.encrypt_payload(complex_data)
        assert encrypted.get('encrypted') is True

        decrypted = enc.decrypt_payload(encrypted)
        assert decrypted == complex_data

    def test_disabled_decrypt_returns_data_unchanged(self):
        """When encryption is disabled, decrypt_payload returns the input unchanged."""
        enc = DataEncryption(None)
        assert enc.enabled is False

        data = {'encrypted': True, 'nonce': 'abc', 'ciphertext': 'def'}
        result = enc.decrypt_payload(data)
        # Disabled instance returns data as-is, does not attempt decryption
        assert result is data
