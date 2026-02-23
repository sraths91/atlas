"""
Fleet Crypto - Encryption utilities for fleet configuration and database
"""
import os
import json
import base64
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key_from_password(password: str, salt: bytes = None) -> tuple:
    """
    Derive an encryption key from a password using PBKDF2
    
    Args:
        password: User password
        salt: Optional salt (generated if not provided)
    
    Returns:
        Tuple of (key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_config_file(input_path: str, output_path: str = None, password: str = None):
    """
    Encrypt a configuration file
    
    Args:
        input_path: Path to plain text config file
        output_path: Path for encrypted output (defaults to input_path + '.enc')
        password: Encryption password (prompts if not provided)
    """
    if output_path is None:
        output_path = input_path + '.enc'
    
    if password is None:
        password = getpass.getpass("Enter encryption password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise ValueError("Passwords do not match")
    
    # Read plain text config
    with open(input_path, 'r') as f:
        config_data = f.read()
    
    # Derive key from password
    key, salt = derive_key_from_password(password)
    
    # Encrypt
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(config_data.encode())
    
    # Store salt + encrypted data
    output_data = {
        'salt': base64.b64encode(salt).decode('utf-8'),
        'data': base64.b64encode(encrypted_data).decode('utf-8')
    }
    
    # Write encrypted config
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Config encrypted: {output_path}")
    print(f" Keep your password safe! You'll need it to decrypt.")


def decrypt_config_file(input_path: str, output_path: str = None, password: str = None) -> dict:
    """
    Decrypt a configuration file
    
    Args:
        input_path: Path to encrypted config file
        output_path: Optional path to write decrypted config
        password: Decryption password (prompts if not provided)
    
    Returns:
        Decrypted config as dictionary
    """
    if password is None:
        password = getpass.getpass("Enter decryption password: ")
    
    # Read encrypted config
    with open(input_path, 'r') as f:
        encrypted_config = json.load(f)
    
    # Extract salt and encrypted data
    salt = base64.b64decode(encrypted_config['salt'])
    encrypted_data = base64.b64decode(encrypted_config['data'])
    
    # Derive key from password
    key, _ = derive_key_from_password(password, salt)
    
    # Decrypt
    try:
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)
        config_json = decrypted_data.decode('utf-8')
    except Exception as e:
        raise ValueError("Decryption failed. Wrong password?") from e
    
    # Parse JSON
    config = json.loads(config_json)
    
    # Optionally write to file
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Config decrypted: {output_path}")
    
    return config


def generate_db_key() -> str:
    """
    Generate a random database encryption key
    
    Returns:
        Base64-encoded 32-byte key
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


def main():
    """CLI for config encryption/decryption"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fleet Configuration Encryption Tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Encrypt command
    encrypt_parser = subparsers.add_parser('encrypt', help='Encrypt a config file')
    encrypt_parser.add_argument('input', help='Input config file')
    encrypt_parser.add_argument('--output', help='Output encrypted file (default: input.enc)')
    encrypt_parser.add_argument('--password', help='Encryption password (prompts if not provided)')
    
    # Decrypt command
    decrypt_parser = subparsers.add_parser('decrypt', help='Decrypt a config file')
    decrypt_parser.add_argument('input', help='Input encrypted file')
    decrypt_parser.add_argument('--output', help='Output decrypted file (optional)')
    decrypt_parser.add_argument('--password', help='Decryption password (prompts if not provided)')
    
    # Generate key command
    subparsers.add_parser('generate-key', help='Generate a database encryption key')
    
    args = parser.parse_args()
    
    if args.command == 'encrypt':
        encrypt_config_file(args.input, args.output, args.password)
    
    elif args.command == 'decrypt':
        config = decrypt_config_file(args.input, args.output, args.password)
        if not args.output:
            print("\nDecrypted config:")
            print(json.dumps(config, indent=2))

    elif args.command == 'generate-key':
        key = generate_db_key()
        print("Generated database encryption key:")
        print(f"\n{key}\n")
        print(" Store this securely! Set as environment variable:")
        print(f"export FLEET_DB_KEY='{key}'")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
