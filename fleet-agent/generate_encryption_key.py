#!/usr/bin/env python3
"""
Generate an encryption key for Fleet Agent end-to-end encryption
"""
import sys

try:
    from fleet_agent.encryption import generate_encryption_key
    generate_encryption_key()
except ImportError:
    print("ERROR: Fleet Agent not installed")
    print("Install with: pip install -e .")
    sys.exit(1)
