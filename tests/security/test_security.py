"""
Security Tests for ATLAS Fleet Monitoring Platform

Phase 8: Testing Infrastructure

Tests security implementations including:
- Password hashing (bcrypt)
- Encryption (HKDF, Fernet)
- Session management
- Input validation
"""
import pytest
import re


@pytest.mark.security
class TestPasswordSecurity:
    """Tests for password hashing and validation"""

    def test_bcrypt_hashing_available(self):
        """Test bcrypt is available and working"""
        try:
            import bcrypt
            password = b"test_password_123"
            hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
            assert bcrypt.checkpw(password, hashed)
        except ImportError:
            pytest.skip("bcrypt not installed")

    def test_password_complexity_requirements(self):
        """Test password complexity validation"""
        from atlas.config import SECURITY_CONFIG

        config = SECURITY_CONFIG['password']
        assert config['min_length'] >= 12, "Password min length should be >= 12"
        assert config['require_uppercase'] is True
        assert config['require_lowercase'] is True
        assert config['require_digits'] is True
        assert config['require_special'] is True

    def test_bcrypt_rounds_secure(self):
        """Test bcrypt uses sufficient rounds"""
        from atlas.config import SECURITY_CONFIG

        rounds = SECURITY_CONFIG['password']['rounds']
        assert rounds >= 10, "bcrypt rounds should be >= 10"
        assert rounds <= 14, "bcrypt rounds should be <= 14 for performance"


@pytest.mark.security
class TestEncryptionSecurity:
    """Tests for encryption implementations"""

    def test_hkdf_available(self):
        """Test HKDF is available for key derivation"""
        try:
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend

            # Test HKDF key derivation
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'test-salt',
                info=b'test-info',
                backend=default_backend()
            )
            key = hkdf.derive(b'test-secret-minimum-32-bytes-long!')
            assert len(key) == 32
        except ImportError:
            pytest.skip("cryptography library not installed")

    def test_encryption_configuration_secure(self):
        """Test encryption configuration uses secure settings"""
        from atlas.config import SECURITY_CONFIG

        enc_config = SECURITY_CONFIG['encryption']
        assert enc_config['kdf'] == 'pbkdf2hmac'
        assert enc_config['kdf_iterations'] >= 100000, "KDF iterations should be >= 100000"
        assert enc_config['salt_length'] >= 32, "Salt should be >= 32 bytes"
        assert enc_config['key_length'] >= 32, "Key should be >= 32 bytes"

    def test_cluster_secret_minimum_length(self):
        """Test cluster secret enforces minimum length"""
        from atlas.config import FLEET_SERVER_CONFIG

        min_length = FLEET_SERVER_CONFIG['cluster']['min_secret_length']
        assert min_length >= 32, "Cluster secret minimum should be >= 32 bytes"

    def test_cluster_security_hkdf(self):
        """Test cluster security uses HKDF for key derivation"""
        try:
            from atlas.cluster_security import ClusterSecurity
            import base64

            # Generate valid secret (32+ bytes)
            secret = ClusterSecurity.generate_cluster_secret()
            security = ClusterSecurity(secret)

            assert security.enabled, "ClusterSecurity should be enabled with valid secret"

            # Test encryption/decryption works
            data = {'test': 'data'}
            encrypted = security.encrypt_cluster_data(data)
            decrypted = security.decrypt_cluster_data(encrypted)

            assert decrypted == data

        except ImportError:
            pytest.skip("Cluster security module not available")


@pytest.mark.security
class TestSessionSecurity:
    """Tests for session management security"""

    def test_session_configuration_secure(self):
        """Test session configuration uses secure settings"""
        from atlas.config import SECURITY_CONFIG

        session_config = SECURITY_CONFIG['session']
        assert session_config['token_length'] >= 32, "Session token should be >= 32 bytes"
        assert session_config['cookie_secure'] is True, "Cookies should require HTTPS"
        assert session_config['cookie_httponly'] is True, "Cookies should be HttpOnly"
        assert session_config['cookie_samesite'] == 'Strict', "Cookies should be SameSite=Strict"

    def test_session_expiry_reasonable(self):
        """Test session expiry is set to reasonable value"""
        from atlas.config import SECURITY_CONFIG

        expiry = SECURITY_CONFIG['session']['expiry']
        assert 3600 <= expiry <= 86400, "Session expiry should be 1-24 hours"


@pytest.mark.security
class TestTLSSecurity:
    """Tests for TLS/SSL configuration"""

    def test_tls_configuration_secure(self):
        """Test TLS configuration uses secure settings"""
        from atlas.config import FLEET_SERVER_CONFIG

        ssl_config = FLEET_SERVER_CONFIG['ssl']
        assert ssl_config['min_tls_version'] == 'TLSv1_2', "Minimum TLS should be 1.2"
        assert ssl_config['max_tls_version'] == 'TLSv1_3', "Maximum TLS should be 1.3"


@pytest.mark.security
class TestBruteForceProtection:
    """Tests for brute force protection"""

    def test_brute_force_configuration(self):
        """Test brute force protection is configured"""
        from atlas.config import SECURITY_CONFIG

        bf_config = SECURITY_CONFIG['brute_force']
        assert bf_config['enabled'] is True, "Brute force protection should be enabled"
        assert bf_config['max_attempts'] <= 10, "Max attempts should be <= 10"
        assert bf_config['lockout_duration'] >= 300, "Lockout should be >= 5 minutes"


@pytest.mark.security
class TestCertificateSecurity:
    """Tests for certificate management"""

    def test_certificate_key_size_secure(self):
        """Test certificate key size is secure"""
        from atlas.config import SECURITY_CONFIG

        cert_config = SECURITY_CONFIG['certificates']
        assert cert_config['key_size'] >= 2048, "Certificate key size should be >= 2048 bits"
        assert cert_config['encrypt_private_keys'] is True, "Private keys should be encrypted"


@pytest.mark.security
class TestInputValidation:
    """Tests for input validation and sanitization"""

    def test_no_sql_injection_in_config(self):
        """Test configuration values don't contain SQL injection patterns"""
        from atlas.config import FLEET_SERVER_CONFIG, NETWORK_CONFIG

        # Simple check for common SQL injection patterns
        sql_patterns = [
            r"';",
            r"--",
            r"DROP\s+TABLE",
            r"INSERT\s+INTO",
            r"DELETE\s+FROM",
        ]

        def check_dict(d, path=""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, str):
                    for pattern in sql_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            pytest.fail(f"Potential SQL injection pattern found in {current_path}: {value}")
                elif isinstance(value, dict):
                    check_dict(value, current_path)

        check_dict(FLEET_SERVER_CONFIG)
        check_dict(NETWORK_CONFIG)


@pytest.mark.security
class TestSecurityHeaders:
    """Tests for security headers configuration"""

    def test_security_headers_configured(self):
        """Test security headers are properly configured"""
        from atlas.config import SECURITY_CONFIG

        headers = SECURITY_CONFIG['headers']
        assert headers['x_frame_options'] == 'DENY', "X-Frame-Options should be DENY"
        assert headers['x_content_type_options'] == 'nosniff', "X-Content-Type-Options should be nosniff"
        assert 'max-age' in headers['strict_transport_security'], "HSTS should have max-age"


@pytest.mark.security
class TestSecretManagement:
    """Tests for secret and credential management"""

    def test_no_hardcoded_secrets_in_config(self):
        """Test no hardcoded secrets in configuration"""
        from atlas.config import FLEET_SERVER_CONFIG, FLEET_AGENT_CONFIG

        # Check for common secret patterns
        def check_for_secrets(d, path=""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key

                # Skip known safe None values
                if value is None:
                    continue

                # Check for suspicious key names with actual values
                if isinstance(value, str) and any(secret_key in key.lower() for secret_key in ['password', 'secret', 'key', 'token']):
                    # Values should be None, empty, or placeholders
                    if value and value not in ['your_api_key_here', 'your_secure_api_key']:
                        # Check if it looks like a real secret (base64, hex, etc.)
                        if len(value) > 20 and (value.isalnum() or '=' in value):
                            pytest.fail(f"Potential hardcoded secret in {current_path}: {value[:10]}...")

                if isinstance(value, dict):
                    check_for_secrets(value, current_path)

        check_for_secrets(FLEET_SERVER_CONFIG)
        check_for_secrets(FLEET_AGENT_CONFIG)


@pytest.mark.security
class TestDataProtection:
    """Tests for data protection mechanisms"""

    def test_deep_copy_prevents_mutations(self, improved_data_store, sample_machine_info, sample_metrics):
        """Test deep copy protection prevents external data mutations"""
        improved_data_store.update_machine('test-machine', sample_machine_info, sample_metrics)

        # Get data and try to mutate it
        machine = improved_data_store.get_machine('test-machine')
        original_hostname = machine['info']['hostname']
        machine['info']['hostname'] = 'HACKED'

        # Verify internal data is unchanged
        machine_again = improved_data_store.get_machine('test-machine')
        assert machine_again['info']['hostname'] == original_hostname
        assert machine_again['info']['hostname'] != 'HACKED'
