"""
Fleet Let's Encrypt Integration
Automatic SSL certificate management using Let's Encrypt ACME protocol
"""

import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)

# Try to import acme libraries
try:
    from acme import client, messages, challenges, crypto_util
    from acme.client import ClientV2
    import josepy as jose
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    ACME_AVAILABLE = True
except ImportError:
    ACME_AVAILABLE = False
    logger.warning("ACME libraries not available. Install: pip install acme certbot")


class LetsEncryptManager:
    """Manage Let's Encrypt certificates for Fleet Server"""
    
    # Let's Encrypt ACME endpoints
    STAGING_DIRECTORY = "https://acme-staging-v02.api.letsencrypt.org/directory"
    PRODUCTION_DIRECTORY = "https://acme-v02.api.letsencrypt.org/directory"
    
    def __init__(self, config_dir: Optional[str] = None, staging: bool = False):
        """
        Initialize Let's Encrypt manager
        
        Args:
            config_dir: Directory for certificates and account info
            staging: Use Let's Encrypt staging environment (for testing)
        """
        if config_dir is None:
            config_dir = str(Path.home() / ".fleet-certs")

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True, mode=0o700)
        
        self.staging = staging
        self.directory_url = self.STAGING_DIRECTORY if staging else self.PRODUCTION_DIRECTORY
        
        self.account_key_path = self.config_dir / "account.key"
        self.cert_path = self.config_dir / "cert.pem"
        self.key_path = self.config_dir / "privkey.pem"
        self.chain_path = self.config_dir / "chain.pem"
        self.fullchain_path = self.config_dir / "fullchain.pem"
        
        if not ACME_AVAILABLE:
            logger.error("ACME libraries not available. Cannot use Let's Encrypt.")
    
    def is_available(self) -> bool:
        """Check if Let's Encrypt integration is available"""
        return ACME_AVAILABLE
    
    def _generate_account_key(self) -> jose.JWKRSA:
        """Generate or load ACME account key"""
        if self.account_key_path.exists():
            # Load existing key
            with open(self.account_key_path, 'rb') as f:
                key_data = f.read()
            private_key = serialization.load_pem_private_key(
                key_data, password=None, backend=default_backend()
            )
            return jose.JWKRSA(key=private_key)
        
        # Generate new key
        logger.info("Generating new ACME account key...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Save key
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(self.account_key_path, 'wb') as f:
            f.write(key_pem)
        os.chmod(self.account_key_path, 0o600)
        
        return jose.JWKRSA(key=private_key)
    
    def _generate_csr(self, domain: str) -> Tuple[bytes, rsa.RSAPrivateKey]:
        """Generate Certificate Signing Request"""
        # Generate private key for certificate
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Create CSR
        csr_builder = x509.CertificateSigningRequestBuilder()
        csr_builder = csr_builder.subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ]))
        
        # Add Subject Alternative Name
        csr_builder = csr_builder.add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
            ]),
            critical=False,
        )
        
        csr = csr_builder.sign(private_key, hashes.SHA256(), default_backend())
        
        return csr.public_bytes(serialization.Encoding.DER), private_key
    
    def register_account(self, email: str) -> bool:
        """
        Register account with Let's Encrypt
        
        Args:
            email: Contact email for certificate notifications
            
        Returns:
            True if successful
        """
        if not ACME_AVAILABLE:
            logger.error("ACME libraries not available")
            return False
        
        try:
            # Generate or load account key
            account_key = self._generate_account_key()
            
            # Create ACME client
            net = client.ClientNetwork(account_key, user_agent='Fleet-Dashboard/1.0')
            directory = messages.Directory.from_json(net.get(self.directory_url).json())
            acme_client = ClientV2(directory, net=net)
            
            # Register account
            logger.info(f"Registering account with Let's Encrypt ({self.directory_url})...")
            registration = messages.NewRegistration.from_data(
                email=email,
                terms_of_service_agreed=True
            )
            
            account = acme_client.new_account(registration)
            logger.info(f"Account registered successfully: {account.uri}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register account: {e}")
            return False
    
    def obtain_certificate(self, domain: str, webroot_path: str) -> bool:
        """
        Obtain certificate using HTTP-01 challenge
        
        Args:
            domain: Domain name for certificate
            webroot_path: Path where challenge files can be served
            
        Returns:
            True if successful
        """
        if not ACME_AVAILABLE:
            logger.error("ACME libraries not available")
            return False
        
        try:
            # Load account key
            if not self.account_key_path.exists():
                logger.error("No account key found. Register account first.")
                return False
            
            account_key = self._generate_account_key()
            
            # Create ACME client
            net = client.ClientNetwork(account_key, user_agent='Fleet-Dashboard/1.0')
            directory = messages.Directory.from_json(net.get(self.directory_url).json())
            acme_client = ClientV2(directory, net=net)
            
            # Create new order
            logger.info(f"Requesting certificate for {domain}...")
            order = acme_client.new_order(domain)
            
            # Get HTTP-01 challenge
            for authz in order.authorizations:
                for challenge in authz.body.challenges:
                    if isinstance(challenge.chall, challenges.HTTP01):
                        # Respond to challenge
                        response, validation = challenge.response_and_validation(account_key)
                        
                        # Write challenge file
                        challenge_dir = Path(webroot_path) / ".well-known" / "acme-challenge"
                        challenge_dir.mkdir(parents=True, exist_ok=True)
                        
                        challenge_file = challenge_dir / challenge.chall.encode("token")
                        with open(challenge_file, 'w') as f:
                            f.write(validation)
                        
                        logger.info(f"Challenge file created: {challenge_file}")
                        logger.info(f"Validation URL: http://{domain}/.well-known/acme-challenge/{challenge.chall.encode('token')}")
                        
                        # Notify Let's Encrypt
                        acme_client.answer_challenge(challenge, response)
                        
                        # Wait for validation
                        logger.info("Waiting for challenge validation...")
                        for _ in range(30):  # Wait up to 30 seconds
                            time.sleep(1)
                            authz_status = acme_client.poll(authz)
                            if authz_status.body.status == messages.STATUS_VALID:
                                logger.info("Challenge validated successfully!")
                                break
                        else:
                            logger.error("Challenge validation timed out")
                            return False
                        
                        # Clean up challenge file
                        challenge_file.unlink()
                        break
            
            # Generate CSR
            csr_der, private_key = self._generate_csr(domain)
            
            # Finalize order
            logger.info("Finalizing certificate order...")
            finalized_order = acme_client.finalize_order(order, csr_der)
            
            # Download certificate
            cert_pem = finalized_order.fullchain_pem
            
            # Save certificate and key
            with open(self.fullchain_path, 'w') as f:
                f.write(cert_pem)
            
            # Extract cert and chain
            certs = cert_pem.split('\n\n')
            with open(self.cert_path, 'w') as f:
                f.write(certs[0] + '\n')
            
            if len(certs) > 1:
                with open(self.chain_path, 'w') as f:
                    f.write('\n\n'.join(certs[1:]))
            
            # Save private key
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(self.key_path, 'wb') as f:
                f.write(key_pem)
            os.chmod(self.key_path, 0o600)
            
            logger.info(f"Certificate obtained successfully!")
            logger.info(f"Certificate: {self.cert_path}")
            logger.info(f"Private key: {self.key_path}")
            logger.info(f"Full chain: {self.fullchain_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to obtain certificate: {e}", exc_info=True)
            return False
    
    def renew_certificate(self, domain: str, webroot_path: str) -> bool:
        """
        Renew existing certificate
        
        Args:
            domain: Domain name
            webroot_path: Path where challenge files can be served
            
        Returns:
            True if successful
        """
        logger.info(f"Renewing certificate for {domain}...")
        return self.obtain_certificate(domain, webroot_path)
    
    def check_expiration(self) -> Optional[datetime]:
        """
        Check certificate expiration date
        
        Returns:
            Expiration datetime or None if no certificate
        """
        if not self.cert_path.exists():
            return None
        
        try:
            with open(self.cert_path, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            return cert.not_valid_after
            
        except Exception as e:
            logger.error(f"Failed to check expiration: {e}")
            return None
    
    def needs_renewal(self, days_before: int = 30) -> bool:
        """
        Check if certificate needs renewal
        
        Args:
            days_before: Renew if expiring within this many days
            
        Returns:
            True if renewal needed
        """
        expiration = self.check_expiration()
        if expiration is None:
            return True  # No certificate, needs one
        
        renewal_date = datetime.now() + timedelta(days=days_before)
        return expiration <= renewal_date
    
    def get_certificate_paths(self) -> Dict[str, str]:
        """Get paths to certificate files"""
        return {
            'cert': str(self.cert_path),
            'key': str(self.key_path),
            'chain': str(self.chain_path),
            'fullchain': str(self.fullchain_path)
        }


def setup_letsencrypt_interactive():
    """Interactive setup for Let's Encrypt"""
    print("=" * 60)
    print("Fleet Dashboard - Let's Encrypt Setup")
    print("=" * 60)
    
    if not ACME_AVAILABLE:
        print("\nACME libraries not installed!")
        print("Install with: pip3 install acme certbot")
        return False
    
    print("\nThis will obtain a free SSL certificate from Let's Encrypt.")
    print("Requirements:")
    print("  • A domain name pointing to this server")
    print("  • Port 80 accessible from the internet")
    print("  • Email address for notifications")
    print()
    
    # Get configuration
    domain = input("Enter your domain name (e.g., fleet.example.com): ").strip()
    if not domain:
        print("Domain name required")
        return False
    
    email = input("Enter your email address: ").strip()
    if not email:
        print("Email address required")
        return False
    
    staging = input("Use staging environment for testing? (y/N): ").strip().lower() == 'y'
    
    # Create manager
    manager = LetsEncryptManager(staging=staging)
    
    # Register account
    print("\nRegistering account with Let's Encrypt...")
    if not manager.register_account(email):
        print("Failed to register account")
        return False
    
    print("Account registered successfully!")
    
    # Get webroot path
    webroot = input("\nEnter webroot path for HTTP challenge (default: /tmp/acme-challenge): ").strip()
    if not webroot:
        webroot = "/tmp/acme-challenge"
    
    os.makedirs(webroot, exist_ok=True)
    
    print(f"\nObtaining certificate for {domain}...")
    print(f"Make sure port 80 is accessible and points to: {webroot}")
    input("Press Enter when ready...")
    
    # Obtain certificate
    if manager.obtain_certificate(domain, webroot):
        print("\nCertificate obtained successfully!")
        print(f"\nCertificate files:")
        paths = manager.get_certificate_paths()
        for name, path in paths.items():
            print(f"  {name}: {path}")
        
        print(f"\nAdd to your Fleet config:")
        print(f"  'ssl': {{")
        print(f"    'cert_file': '{paths['fullchain']}',")
        print(f"    'key_file': '{paths['key']}'")
        print(f"  }}")
        
        return True
    else:
        print("\nFailed to obtain certificate")
        return False


if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        setup_letsencrypt_interactive()
    else:
        print("Usage:")
        print("  python fleet_letsencrypt.py setup    # Interactive setup")
        print("\nOr use programmatically:")
        print("  from fleet_letsencrypt import LetsEncryptManager")
        print("  manager = LetsEncryptManager()")
        print("  manager.register_account('admin@example.com')")
        print("  manager.obtain_certificate('fleet.example.com', '/var/www/html')")
