#!/usr/bin/env python3
"""
Fleet Server Setup Wizard
Creates initial admin credentials and generates API keys
"""

import os
import sys
import json
import secrets
import hashlib
import base64
import shutil
import subprocess
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography import x509
from cryptography.hazmat.backends import default_backend

def generate_api_key():
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

def generate_encryption_key():
    """Generate Fernet encryption key"""
    return Fernet.generate_key().decode()

def hash_password(password):
    """Hash password with bcrypt (secure) or SHA-256 (fallback)"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    except ImportError:
        # Fallback to SHA-256 if bcrypt not available
        print("Warning: bcrypt not available - using SHA-256 (install bcrypt for better security)")
        return hashlib.sha256(password.encode()).hexdigest()

def get_input(prompt, default=None, password=False):
    """Get user input with optional default"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    if password:
        import getpass
        value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    
    return value if value else default

def validate_certificate(cert_path, key_path):
    """Validate SSL certificate and key (supports wildcards)"""
    try:
        # Read certificate
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        
        # Try to load as PEM
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        except (ValueError, TypeError):
            return False, "Invalid certificate format. Must be PEM format."
        
        # Extract certificate details
        try:
            # Get subject common name (CN)
            subject = cert.subject
            cn = None
            for attribute in subject:
                if attribute.oid._name == 'commonName':
                    cn = attribute.value
                    break
            
            # Get Subject Alternative Names (SANs) - includes wildcards
            san_extension = None
            try:
                san_extension = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                sans = san_extension.value.get_values_for_type(x509.DNSName)
            except (x509.ExtensionNotFound, ValueError):
                sans = []
            
            # Check for wildcard certificates
            has_wildcard = False
            if cn and cn.startswith('*.'):
                has_wildcard = True
            for san in sans:
                if san.startswith('*.'):
                    has_wildcard = True
                    break
            
            # Display certificate info
            if cn:
                print(f"   Certificate CN: {cn}")
            if sans:
                print(f"   SANs: {', '.join(sans)}")
            if has_wildcard:
                print(f"   Wildcard certificate detected")
            
        except Exception as e:
            # Certificate info extraction failed, but cert is still valid
            pass
        
        # Check if key exists
        if not Path(key_path).exists():
            return False, "Private key file not found."
        
        # Read and validate key
        with open(key_path, 'rb') as f:
            key_data = f.read()
        
        # Try to load the private key
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            
            private_key = load_pem_private_key(key_data, password=None, backend=default_backend())
        except Exception as e:
            return False, f"Invalid private key format: {str(e)}"
        
        # Validation passed
        return True, cert
    
    except Exception as e:
        return False, f"Error validating certificate: {str(e)}"

def generate_self_signed_cert(domain, output_dir):
    """Generate a self-signed certificate using OpenSSL (supports wildcards)"""
    try:
        cert_path = output_dir / "fleet_cert.pem"
        key_path = output_dir / "fleet_key.pem"
        
        # Check if domain is a wildcard
        is_wildcard = domain.startswith('*.')
        
        # For wildcard certificates, we need to create a config file with SAN
        if is_wildcard:
            # Create OpenSSL config for wildcard cert
            config_path = output_dir / "openssl_temp.cnf"
            
            # Extract base domain (e.g., *.company.com -> company.com)
            base_domain = domain[2:]
            
            config_content = f"""
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = {domain}

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = {domain}
DNS.2 = {base_domain}
"""
            
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Generate with config file
            cmd = [
                'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
                '-keyout', str(key_path),
                '-out', str(cert_path),
                '-days', '365',
                '-nodes',
                '-config', str(config_path),
                '-extensions', 'v3_req'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            # Clean up config file
            try:
                config_path.unlink()
            except OSError:
                pass
        else:
            # Standard certificate (non-wildcard)
            cmd = [
                'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
                '-keyout', str(key_path),
                '-out', str(cert_path),
                '-days', '365',
                '-nodes',
                '-subj', f'/CN={domain}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            if is_wildcard:
                print(f"   Wildcard certificate generated for {domain}")
            return True, cert_path, key_path
        else:
            return False, None, None
    
    except Exception as e:
        return False, None, None

def setup_ssl_certificates(domain, config_dir):
    """Setup SSL certificates"""
    print()
    print("SSL Certificate Setup")
    print("-" * 60)
    print()
    print("To secure your Fleet Server with HTTPS, you need an SSL certificate.")
    print()
    print("Options:")
    print("  1. Use existing certificate (recommended for production)")
    print("  2. Generate self-signed certificate (for testing)")
    print("  3. Skip SSL setup (use HTTP only - not recommended)")
    print()
    
    choice = get_input("Choose option", default="2")
    
    if choice == "1":
        # Use existing certificate
        print()
        print("Please provide the paths to your SSL certificate files:")
        print("(Files will be copied to the Fleet configuration directory)")
        print()
        
        while True:
            cert_path = get_input("Certificate file path (.pem or .crt)")
            if not cert_path:
                print("Certificate path is required")
                continue
            
            cert_path = Path(cert_path).expanduser()
            if not cert_path.exists():
                print(f"File not found: {cert_path}")
                continue
            
            key_path = get_input("Private key file path (.pem or .key)")
            if not key_path:
                print("Private key path is required")
                continue
            
            key_path = Path(key_path).expanduser()
            if not key_path.exists():
                print(f"File not found: {key_path}")
                continue
            
            # Validate certificate
            valid, result = validate_certificate(cert_path, key_path)
            if not valid:
                print(f"{result}")
                retry = get_input("Try again? (yes/no)", default="yes")
                if retry.lower() not in ['yes', 'y']:
                    return None, None, False
                continue
            
            # Copy files to config directory
            dest_cert = config_dir / "fleet_cert.pem"
            dest_key = config_dir / "fleet_key.pem"
            
            shutil.copy2(cert_path, dest_cert)
            shutil.copy2(key_path, dest_key)
            
            # Set secure permissions
            os.chmod(dest_cert, 0o644)
            os.chmod(dest_key, 0o600)
            
            print(f"Certificate installed")
            print(f"   Certificate: {dest_cert}")
            print(f"   Private key: {dest_key}")
            
            return dest_cert, dest_key, True
    
    elif choice == "2":
        # Generate self-signed certificate
        print()
        print("Generating self-signed certificate...")
        print(" Note: Self-signed certificates will show a security warning")
        print("   in browsers. Use a proper certificate for production.")
        print()
        
        success, cert_path, key_path = generate_self_signed_cert(domain, config_dir)
        
        if success:
            os.chmod(cert_path, 0o644)
            os.chmod(key_path, 0o600)
            
            print(f"Self-signed certificate generated")
            print(f"   Certificate: {cert_path}")
            print(f"   Private key: {key_path}")
            print()
            print(" Browsers will show a security warning. You can:")
            print("   - Click 'Advanced' and proceed anyway (for testing)")
            print("   - Replace with a proper certificate later")
            
            return cert_path, key_path, True
        else:
            print("Failed to generate certificate")
            print("   OpenSSL may not be installed or accessible")
            return None, None, False
    
    else:
        # Skip SSL
        print()
        print(" Skipping SSL setup - server will use HTTP only")
        print("   Your connection will NOT be secure")
        print("   Passwords and data will be transmitted in plain text")
        print()
        confirm = get_input("Are you sure? (yes/no)", default="no")
        if confirm.lower() in ['yes', 'y']:
            return None, None, False
        else:
            # Retry SSL setup
            return setup_ssl_certificates(domain, config_dir)

def setup_wizard():
    """Run the setup wizard"""
    print("=" * 60)
    print("Fleet Server Setup Wizard")
    print("=" * 60)
    print()
    print("This wizard will help you set up your Fleet Server.")
    print("You'll create an admin account and generate security keys.")
    print()
    
    # Get admin credentials
    print("Step 1: Create Admin Account")
    print("-" * 60)
    
    admin_username = get_input("Admin username", default="admin")
    
    while True:
        admin_password = get_input("Admin password", password=True)
        if len(admin_password) < 8:
            print("Password must be at least 8 characters long")
            continue
        
        admin_password_confirm = get_input("Confirm password", password=True)
        if admin_password != admin_password_confirm:
            print("Passwords don't match. Please try again.")
            continue
        
        break
    
    print("Admin account created")
    print()
    
    # Generate keys
    print("Step 2: Generate Security Keys")
    print("-" * 60)
    
    api_key = generate_api_key()
    encryption_key = generate_encryption_key()
    
    print(f"API Key generated: {api_key[:16]}...")
    print(f"Encryption Key generated: {encryption_key[:16]}...")
    print()
    
    # Get server configuration
    print("Step 3: Server Configuration")
    print("-" * 60)
    
    # Get server hostname/IP
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"\nDetected hostname: {hostname}")
    print(f"Detected local IP: {local_ip}")
    print()
    print("Enter the domain or IP address for your Fleet Server.")
    print("Examples:")
    print("  - fleet.company.com (if you have a domain)")
    print("  - 192.168.1.100 (local IP)")
    print("  - fleet.local (local hostname)")
    print()
    
    server_host = get_input("Fleet Server domain/hostname/IP", default=local_ip)
    
    print()
    
    # SSL Configuration
    print("Step 4: SSL/HTTPS Configuration")
    print("-" * 60)
    
    # Create config directory for certificates
    config_dir = Path.home() / ".fleet"
    config_dir.mkdir(exist_ok=True, mode=0o700)
    
    # Setup SSL certificates
    cert_path, key_path, use_ssl = setup_ssl_certificates(server_host, config_dir)
    
    # Determine port based on SSL
    if use_ssl:
        default_port = "443"
        protocol = "https"
    else:
        default_port = "8778"
        protocol = "http"
    
    server_port = get_input(f"Fleet Server port", default=default_port)
    
    print()
    
    # Data retention
    print("Step 5: Data Retention")
    print("-" * 60)
    
    retention_days = get_input("Keep data for how many days?", default="2")
    
    print()
    
    # Create configuration
    config = {
        "server": {
            "host": server_host,
            "port": int(server_port),
            "api_key": api_key,
            "use_ssl": use_ssl,
            "protocol": protocol
        },
        "admin": {
            "username": admin_username,
            "password_hash": hash_password(admin_password)
        },
        "security": {
            "encryption_key": encryption_key,
            "api_key": api_key
        },
        "ssl": {
            "enabled": use_ssl,
            "cert_file": str(cert_path) if cert_path else None,
            "key_file": str(key_path) if key_path else None
        },
        "retention": {
            "days": int(retention_days)
        },
        "setup_complete": True
    }
    
    # Save configuration
    config_path = Path.home() / ".fleet-config.json"
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    os.chmod(config_path, 0o600)  # Read/write for owner only
    
    print("=" * 60)
    print("Setup Complete! ")
    print("=" * 60)
    print()
    print("Configuration saved to:", config_path)
    print()
    print("Your Fleet Server Details:")
    print("-" * 60)
    
    # Show correct URL based on SSL
    if use_ssl:
        if server_port == "443":
            server_url = f"https://{server_host}"
        else:
            server_url = f"https://{server_host}:{server_port}"
    else:
        server_url = f"http://{server_host}:{server_port}"
    
    print(f"Server URL: {server_url}")
    print(f"Protocol: {protocol.upper()}")
    if use_ssl:
        print(f"SSL Certificate: {cert_path}")
        print(f"SSL Private Key: {key_path}")
    print(f"Admin Username: {admin_username}")
    print(f"Admin Password: {admin_password}")
    print(f"API Key: {api_key}")
    print()
    print(" IMPORTANT: Save these credentials securely!")
    print("   The API key is needed to install agents on other Macs.")
    print()
    
    if use_ssl and choice == "2":
        print(" SSL Certificate Warning:")
        print("-" * 60)
        print("You're using a self-signed certificate. Browsers will show:")
        print("  'Your connection is not private' or 'Not secure'")
        print()
        print("To proceed in your browser:")
        print("  1. Click 'Advanced' or 'Show details'")
        print("  2. Click 'Proceed to {server_host}' or 'Accept the risk'")
        print()
        print("For production, get a proper certificate from:")
        print("  - Let's Encrypt (free): https://letsencrypt.org")
        print("  - Your domain registrar")
        print("  - A certificate authority")
        print()
    
    print("Next Steps:")
    print("-" * 60)
    print("1. Start the Fleet Server:")
    print(f"   FLEET_DB_KEY='{encryption_key}' \\")
    print(f"   FLEET_WEB_USERNAME='{admin_username}' \\")
    print(f"   FLEET_WEB_PASSWORD='{admin_password}' \\")
    if use_ssl:
        print(f"   FLEET_SSL_CERT='{cert_path}' \\")
        print(f"   FLEET_SSL_KEY='{key_path}' \\")
    print(f"   python3 -m atlas.fleet_server --config {config_path}")
    print()
    print("2. Access the dashboard:")
    print(f"   {server_url}/dashboard")
    print()
    print("3. Download agent installer from dashboard")
    print()
    
    # Create environment file
    env_file = Path.home() / ".fleet-env"
    with open(env_file, 'w') as f:
        f.write(f"export FLEET_DB_KEY='{encryption_key}'\n")
        f.write(f"export FLEET_WEB_USERNAME='{admin_username}'\n")
        f.write(f"export FLEET_WEB_PASSWORD='{admin_password}'\n")
        f.write(f"export FLEET_API_KEY='{api_key}'\n")
        if use_ssl:
            f.write(f"export FLEET_SSL_CERT='{cert_path}'\n")
            f.write(f"export FLEET_SSL_KEY='{key_path}'\n")
    
    os.chmod(env_file, 0o600)
    
    print(f"Environment variables saved to: {env_file}")
    print(f"Load with: source {env_file}")
    print()
    
    return config

if __name__ == '__main__':
    try:
        # Check if already configured
        config_path = Path.home() / ".fleet-config.json"
        if config_path.exists():
            print(" Fleet Server is already configured!")
            print(f"Configuration file: {config_path}")
            print()
            response = input("Do you want to reconfigure? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Setup cancelled.")
                sys.exit(0)
        
        config = setup_wizard()
        
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during setup: {e}")
        sys.exit(1)
