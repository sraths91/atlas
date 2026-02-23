"""
Fleet Automatic Certificate Management
Handles both Let's Encrypt (for domains) and self-signed (for internal IPs)
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
import socket
import ipaddress

logger = logging.getLogger(__name__)

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtensionOID
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography package not available")


class AutoCertificateManager:
    """Automatically manage certificates based on domain or IP"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize certificate manager
        
        Args:
            config_dir: Directory for certificates
        """
        if config_dir is None:
            config_dir = str(Path.home() / ".fleet-certs")

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True, mode=0o700)
        
        self.cert_path = self.config_dir / "cert.pem"
        self.key_path = self.config_dir / "privkey.pem"
        self.fullchain_path = self.config_dir / "fullchain.pem"
    
    def is_ip_address(self, host: str) -> bool:
        """Check if host is an IP address"""
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            return False
    
    def is_private_ip(self, host: str) -> bool:
        """Check if host is a private IP address"""
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private
        except ValueError:
            return False
    
    def get_local_ip(self) -> str:
        """Get the local IP address"""
        try:
            # Connect to external host to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def generate_self_signed_cert(self, host: str, organization: str = "Fleet Dashboard",
                                  validity_days: int = 825) -> bool:
        """
        Generate self-signed certificate for internal use
        
        Args:
            host: Hostname or IP address
            organization: Organization name for certificate
            validity_days: Certificate validity in days (default: 825 = ~2 years)
            
        Returns:
            True if successful
        """
        if not CRYPTO_AVAILABLE:
            logger.error("cryptography package not available")
            return False
        
        try:
            logger.info(f"Generating self-signed certificate for {host}...")
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Determine if host is IP or domain
            is_ip = self.is_ip_address(host)
            
            # Create certificate subject
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, host),
            ])
            
            # Build certificate
            builder = x509.CertificateBuilder()
            builder = builder.subject_name(subject)
            builder = builder.issuer_name(issuer)
            builder = builder.public_key(private_key.public_key())
            builder = builder.serial_number(x509.random_serial_number())
            builder = builder.not_valid_before(datetime.utcnow())
            builder = builder.not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
            
            # Add Subject Alternative Name (critical for modern browsers)
            san_list = []
            if is_ip:
                # Add IP address
                san_list.append(x509.IPAddress(ipaddress.ip_address(host)))
                # Also add localhost variants
                san_list.append(x509.DNSName("localhost"))
                san_list.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))
            else:
                # Add DNS name
                san_list.append(x509.DNSName(host))
                # Add www variant if applicable
                if not host.startswith("www."):
                    san_list.append(x509.DNSName(f"www.{host}"))
            
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )
            
            # Add basic constraints
            builder = builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            
            # Add key usage
            builder = builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            
            # Add extended key usage
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=False,
            )
            
            # Sign certificate
            certificate = builder.sign(private_key, hashes.SHA256(), default_backend())
            
            # Save certificate
            with open(self.cert_path, 'wb') as f:
                f.write(certificate.public_bytes(serialization.Encoding.PEM))
            
            with open(self.fullchain_path, 'wb') as f:
                f.write(certificate.public_bytes(serialization.Encoding.PEM))
            
            # Save private key
            with open(self.key_path, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Set permissions
            os.chmod(self.key_path, 0o600)
            os.chmod(self.cert_path, 0o644)
            os.chmod(self.fullchain_path, 0o644)
            
            logger.info(f"Self-signed certificate generated successfully!")
            logger.info(f"   Certificate: {self.cert_path}")
            logger.info(f"   Private key: {self.key_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate certificate: {e}", exc_info=True)
            return False
    
    def install_system_trust_macos(self) -> bool:
        """
        Install certificate in macOS system trust store
        This eliminates browser warnings for self-signed certificates
        
        Returns:
            True if successful
        """
        if not self.cert_path.exists():
            logger.error("Certificate not found")
            return False
        
        try:
            logger.info("Installing certificate in macOS trust store...")
            logger.info("This will require administrator password...")
            
            # Add to system keychain
            cmd = [
                'sudo', 'security', 'add-trusted-cert',
                '-d',  # Add to admin cert store
                '-r', 'trustRoot',  # Trust as root
                '-k', '/Library/Keychains/System.keychain',
                str(self.cert_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info("Certificate installed in system trust store!")
                logger.info("   Browsers will now trust this certificate")
                return True
            else:
                logger.error(f"Failed to install certificate: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing certificate: {e}")
            return False
    
    def remove_system_trust_macos(self) -> bool:
        """Remove certificate from macOS system trust store"""
        try:
            logger.info("Removing certificate from system trust store...")
            
            # Find and delete certificate
            cmd = [
                'sudo', 'security', 'delete-certificate',
                '-c', 'Fleet Dashboard',  # Common name
                '/Library/Keychains/System.keychain'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info("Certificate removed from trust store")
                return True
            else:
                logger.warning(f"Certificate may not exist in trust store: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing certificate: {e}")
            return False
    
    def setup_certificate(self, host: str, email: Optional[str] = None,
                         force_self_signed: bool = False) -> Tuple[bool, str]:
        """
        Automatically set up certificate based on host type
        
        Args:
            host: Hostname or IP address
            email: Email for Let's Encrypt (if using domain)
            force_self_signed: Force self-signed even for domains
            
        Returns:
            (success, message)
        """
        # Check if host is IP address
        is_ip = self.is_ip_address(host)
        is_private = self.is_private_ip(host) if is_ip else False
        
        # Determine certificate strategy
        if is_ip or force_self_signed:
            logger.info(f"Host is {'private IP' if is_private else 'IP address'}, using self-signed certificate")
            
            # Generate self-signed certificate
            if not self.generate_self_signed_cert(host):
                return False, "Failed to generate self-signed certificate"
            
            # Offer to install in system trust
            if sys.platform == 'darwin':  # macOS
                print("\n" + "="*60)
                print("CERTIFICATE GENERATED")
                print("="*60)
                print(f"\nA self-signed certificate has been created for {host}")
                print("\nTo eliminate browser warnings, you can install this")
                print("certificate in your system trust store.")
                print("\nThis requires administrator password.")
                print("\nOptions:")
                print("  1. Install now (recommended for internal use)")
                print("  2. Skip (you'll see browser warnings)")
                print("  3. Manual install later")
                
                choice = input("\nChoose option (1/2/3): ").strip()
                
                if choice == '1':
                    if self.install_system_trust_macos():
                        return True, "Certificate generated and installed in system trust"
                    else:
                        return True, "Certificate generated but failed to install in trust store"
                elif choice == '3':
                    print(f"\nTo install manually later, run:")
                    print(f"sudo security add-trusted-cert -d -r trustRoot \\")
                    print(f"  -k /Library/Keychains/System.keychain {self.cert_path}")
                    return True, "Certificate generated (manual install available)"
                else:
                    return True, "Certificate generated (browser warnings will appear)"
            else:
                return True, "Certificate generated (install in trust store manually)"
        
        else:
            # Domain name - use Let's Encrypt
            logger.info(f"Host is domain name, using Let's Encrypt")
            
            if not email:
                return False, "Email required for Let's Encrypt"
            
            try:
                from .fleet_letsencrypt import LetsEncryptManager
                
                manager = LetsEncryptManager()
                
                # Register account
                if not manager.account_key_path.exists():
                    logger.info("Registering Let's Encrypt account...")
                    if not manager.register_account(email):
                        return False, "Failed to register Let's Encrypt account"
                
                # Obtain certificate
                webroot = str(self.config_dir / "acme-challenge")
                os.makedirs(webroot, exist_ok=True)
                
                logger.info(f"Obtaining Let's Encrypt certificate for {host}...")
                if manager.obtain_certificate(host, webroot):
                    # Copy Let's Encrypt certs to our location
                    le_paths = manager.get_certificate_paths()
                    
                    import shutil
                    shutil.copy(le_paths['cert'], self.cert_path)
                    shutil.copy(le_paths['key'], self.key_path)
                    shutil.copy(le_paths['fullchain'], self.fullchain_path)
                    
                    return True, "Let's Encrypt certificate obtained successfully"
                else:
                    return False, "Failed to obtain Let's Encrypt certificate"
                    
            except ImportError:
                return False, "Let's Encrypt support not available (install acme package)"
    
    def get_certificate_info(self) -> Optional[dict]:
        """Get information about current certificate"""
        if not self.cert_path.exists():
            return None
        
        try:
            with open(self.cert_path, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Extract subject
            subject_attrs = {}
            for attr in cert.subject:
                subject_attrs[attr.oid._name] = attr.value
            
            # Check if self-signed
            is_self_signed = cert.issuer == cert.subject
            
            # Get SANs
            sans = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                sans = [str(name) for name in san_ext.value]
            except x509.ExtensionNotFound:
                pass
            
            return {
                'subject': subject_attrs,
                'issuer': cert.issuer.rfc4514_string(),
                'not_before': cert.not_valid_before,
                'not_after': cert.not_valid_after,
                'is_self_signed': is_self_signed,
                'sans': sans,
                'serial_number': cert.serial_number,
            }
            
        except Exception as e:
            logger.error(f"Error reading certificate: {e}")
            return None
    
    def get_certificate_paths(self) -> dict:
        """Get paths to certificate files"""
        return {
            'cert': str(self.cert_path),
            'key': str(self.key_path),
            'fullchain': str(self.fullchain_path)
        }


def interactive_setup():
    """Interactive certificate setup"""
    print("="*60)
    print("Fleet Dashboard - Automatic Certificate Setup")
    print("="*60)
    
    if not CRYPTO_AVAILABLE:
        print("\ncryptography package not installed!")
        print("Install with: pip3 install cryptography")
        return False
    
    print("\nThis wizard will set up SSL certificates for your Fleet Dashboard.")
    print("\nOptions:")
    print("  1. Internal IP (e.g., 192.168.1.100) - Self-signed certificate")
    print("  2. Domain name (e.g., fleet.example.com) - Let's Encrypt")
    print()
    
    # Get host
    host = input("Enter your hostname or IP address: ").strip()
    if not host:
        print("Host required")
        return False
    
    # Create manager
    manager = AutoCertificateManager()
    
    # Determine if IP or domain
    is_ip = manager.is_ip_address(host)
    
    if is_ip:
        print(f"\n✓ Detected IP address: {host}")
        print("  Using self-signed certificate")
        
        # Generate certificate
        success, message = manager.setup_certificate(host)
        
        if success:
            print(f"\n{message}")
            print(f"\nCertificate files:")
            paths = manager.get_certificate_paths()
            for name, path in paths.items():
                print(f"  {name}: {path}")
            
            print(f"\nAdd to your Fleet config:")
            print(f"  'ssl': {{")
            print(f"    'cert_file': '{paths['fullchain']}',")
            print(f"    'key_file': '{paths['key']}'")
            print(f"  }}")
            
            # Show certificate info
            info = manager.get_certificate_info()
            if info:
                print(f"\nCertificate Details:")
                print(f"  Valid from: {info['not_before']}")
                print(f"  Valid until: {info['not_after']}")
                print(f"  SANs: {', '.join(info['sans'])}")
            
            return True
        else:
            print(f"\n{message}")
            return False
    
    else:
        print(f"\n✓ Detected domain name: {host}")
        print("  Using Let's Encrypt")
        
        email = input("Enter your email address: ").strip()
        if not email:
            print("Email required for Let's Encrypt")
            return False
        
        staging = input("Use staging environment for testing? (y/N): ").strip().lower() == 'y'
        
        print("\n Let's Encrypt requires:")
        print("  • Domain must point to this server")
        print("  • Port 80 must be accessible from internet")
        print()
        
        ready = input("Ready to proceed? (y/N): ").strip().lower()
        if ready != 'y':
            print("Setup cancelled")
            return False
        
        success, message = manager.setup_certificate(host, email=email)
        
        if success:
            print(f"\n{message}")
            paths = manager.get_certificate_paths()
            print(f"\nCertificate files:")
            for name, path in paths.items():
                print(f"  {name}: {path}")
            return True
        else:
            print(f"\n{message}")
            return False


if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        interactive_setup()
    else:
        print("Usage:")
        print("  python fleet_cert_auto.py setup    # Interactive setup")
        print("\nOr use programmatically:")
        print("  from fleet_cert_auto import AutoCertificateManager")
        print("  manager = AutoCertificateManager()")
        print("  manager.setup_certificate('192.168.1.100')  # For IP")
        print("  manager.setup_certificate('fleet.example.com', 'admin@example.com')  # For domain")
