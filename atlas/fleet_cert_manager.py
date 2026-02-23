#!/usr/bin/env python3
"""
Fleet Certificate Manager
Handles SSL certificate management, validation, and expiration tracking
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key

class CertificateManager:
    """Manage SSL certificates for Fleet Server"""
    
    def __init__(self, config_path=None):
        """Initialize certificate manager"""
        if config_path is None:
            config_path = Path.home() / ".fleet-config.json"
        
        self.config_path = Path(config_path)
        self.config_dir = Path.home() / ".fleet"
        self.config_dir.mkdir(exist_ok=True, mode=0o700)
    
    def get_certificate_info(self):
        """Get information about current certificate"""
        try:
            # Load config
            if not self.config_path.exists():
                return None
            
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            cert_file = config.get('ssl', {}).get('cert_file')
            if not cert_file or not Path(cert_file).exists():
                return None
            
            # Read certificate
            with open(cert_file, 'rb') as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Extract information
            subject = cert.subject
            cn = None
            for attribute in subject:
                if attribute.oid._name == 'commonName':
                    cn = attribute.value
                    break
            
            # Get SANs
            sans = []
            try:
                san_extension = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                sans = list(san_extension.value.get_values_for_type(x509.DNSName))
            except (x509.ExtensionNotFound, ValueError):
                pass

            # Get expiration
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after
            
            # Calculate days until expiration
            now = datetime.utcnow()
            days_until_expiry = (not_after - now).days
            
            # Get issuer
            issuer = cert.issuer
            issuer_cn = None
            for attribute in issuer:
                if attribute.oid._name == 'commonName':
                    issuer_cn = attribute.value
                    break
            
            # Determine certificate type
            is_self_signed = (issuer_cn == cn)
            is_wildcard = cn and cn.startswith('*.')
            
            return {
                'common_name': cn,
                'sans': sans,
                'not_before': not_before.isoformat(),
                'not_after': not_after.isoformat(),
                'days_until_expiry': days_until_expiry,
                'issuer': issuer_cn,
                'is_self_signed': is_self_signed,
                'is_wildcard': is_wildcard,
                'cert_file': cert_file,
                'expires_soon': days_until_expiry <= 30,
                'expired': days_until_expiry < 0
            }
        
        except Exception as e:
            return None
    
    def validate_certificate_pair(self, cert_data, key_data):
        """Validate certificate and key pair"""
        try:
            # Load certificate
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Load private key
            try:
                private_key = load_pem_private_key(key_data, password=None, backend=default_backend())
            except (ValueError, TypeError):
                return False, "Invalid private key format or password required"
            
            # Extract certificate details
            subject = cert.subject
            cn = None
            for attribute in subject:
                if attribute.oid._name == 'commonName':
                    cn = attribute.value
                    break
            
            # Get SANs
            sans = []
            try:
                san_extension = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                sans = list(san_extension.value.get_values_for_type(x509.DNSName))
            except (x509.ExtensionNotFound, ValueError):
                pass

            # Check expiration
            now = datetime.utcnow()
            if cert.not_valid_after < now:
                return False, "Certificate has expired"
            
            if cert.not_valid_before > now:
                return False, "Certificate is not yet valid"
            
            # Validation passed
            info = {
                'common_name': cn,
                'sans': sans,
                'not_after': cert.not_valid_after.isoformat(),
                'days_until_expiry': (cert.not_valid_after - now).days
            }
            
            return True, info
        
        except Exception as e:
            return False, f"Certificate validation error: {str(e)}"
    
    def update_certificate(self, cert_data, key_data):
        """Update SSL certificate"""
        try:
            # Validate first
            valid, result = self.validate_certificate_pair(cert_data, key_data)
            if not valid:
                return False, result
            
            # Backup old certificates
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                
                old_cert = config.get('ssl', {}).get('cert_file')
                old_key = config.get('ssl', {}).get('key_file')
                
                if old_cert and Path(old_cert).exists():
                    backup_cert = f"{old_cert}.backup"
                    with open(old_cert, 'rb') as f_in:
                        with open(backup_cert, 'wb') as f_out:
                            f_out.write(f_in.read())

                if old_key and Path(old_key).exists():
                    backup_key = f"{old_key}.backup"
                    with open(old_key, 'rb') as f_in:
                        with open(backup_key, 'wb') as f_out:
                            f_out.write(f_in.read())
            
            # Write new certificate and key
            cert_path = self.config_dir / "fleet_cert.pem"
            key_path = self.config_dir / "fleet_key.pem"
            
            with open(cert_path, 'wb') as f:
                f.write(cert_data)
            cert_path.chmod(0o644)

            with open(key_path, 'wb') as f:
                f.write(key_data)
            key_path.chmod(0o600)
            
            # Update config
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                
                if 'ssl' not in config:
                    config['ssl'] = {}
                
                config['ssl']['cert_file'] = str(cert_path)
                config['ssl']['key_file'] = str(key_path)
                config['ssl']['enabled'] = True
                config['ssl']['last_updated'] = datetime.now().isoformat()
                
                with open(self.config_path, 'w') as f:
                    json.dump(config, f, indent=2)

                self.config_path.chmod(0o600)
            
            return True, {
                'message': 'Certificate updated successfully',
                'cert_info': result,
                'cert_path': str(cert_path),
                'key_path': str(key_path)
            }
        
        except Exception as e:
            return False, f"Error updating certificate: {str(e)}"
    
    def get_expiration_warning(self):
        """Get certificate expiration warning if applicable"""
        info = self.get_certificate_info()
        if not info:
            return None
        
        days = info['days_until_expiry']
        
        if days < 0:
            return {
                'level': 'critical',
                'message': f"SSL certificate has EXPIRED {abs(days)} days ago!",
                'days': days,
                'action': 'Renew certificate immediately'
            }
        elif days <= 7:
            return {
                'level': 'critical',
                'message': f"SSL certificate expires in {days} days!",
                'days': days,
                'action': 'Renew certificate urgently'
            }
        elif days <= 14:
            return {
                'level': 'warning',
                'message': f"SSL certificate expires in {days} days",
                'days': days,
                'action': 'Plan certificate renewal soon'
            }
        elif days <= 30:
            return {
                'level': 'info',
                'message': f"SSL certificate expires in {days} days",
                'days': days,
                'action': 'Consider renewing certificate'
            }
        
        return None

def main():
    """Test certificate manager"""
    manager = CertificateManager()
    
    # Get certificate info
    info = manager.get_certificate_info()
    if info:
        print("Certificate Information:")
        print(f"  Common Name: {info['common_name']}")
        print(f"  SANs: {', '.join(info['sans']) if info['sans'] else 'None'}")
        print(f"  Expires: {info['not_after']}")
        print(f"  Days until expiry: {info['days_until_expiry']}")
        print(f"  Issuer: {info['issuer']}")
        print(f"  Self-signed: {info['is_self_signed']}")
        print(f"  Wildcard: {info['is_wildcard']}")
    else:
        print("No certificate configured")
    
    # Check for warnings
    warning = manager.get_expiration_warning()
    if warning:
        print(f"\n {warning['level'].upper()}: {warning['message']}")
        print(f"   Action: {warning['action']}")

if __name__ == '__main__':
    main()
