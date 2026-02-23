#!/usr/bin/env python3
"""
Test end-to-end encryption between agent and server
"""
import json
import sys

# Test agent encryption
sys.path.insert(0, 'fleet-agent')
from fleet_agent.encryption import DataEncryption as AgentEncryption

# Test server decryption
from atlas.encryption import DataEncryption as ServerEncryption

def test_encryption():
    """Test that agent encryption and server decryption work together"""
    
    # Generate a test key
    key = AgentEncryption.generate_key()
    print(f"\nGenerated test key: {key[:20]}...")
    
    # Create encryption/decryption instances with same key
    agent = AgentEncryption(key)
    server = ServerEncryption(key)
    
    # Test data (simulating agent metrics)
    test_data = {
        'machine_id': 'test-mac-001',
        'machine_info': {
            'hostname': 'TestMac',
            'os': 'macOS 14.0'
        },
        'metrics': {
            'cpu': 45.2,
            'memory': 68.5,
            'disk': 72.1
        }
    }
    
    print("\nAgent: Encrypting payload...")
    encrypted = agent.encrypt_payload(test_data)
    
    print(f"Encrypted payload created")
    print(f"   - encrypted: {encrypted.get('encrypted')}")
    print(f"   - version: {encrypted.get('version')}")
    print(f"   - nonce: {encrypted.get('nonce')[:20]}...")
    print(f"   - ciphertext: {encrypted.get('ciphertext')[:40]}...")
    
    print("\nServer: Decrypting payload...")
    decrypted = server.decrypt_payload(encrypted)
    
    print("Decrypted successfully")
    print(f"   - machine_id: {decrypted.get('machine_id')}")
    print(f"   - CPU: {decrypted.get('metrics', {}).get('cpu')}%")
    
    # Verify data matches
    if decrypted == test_data:
        print("\nSUCCESS: Data matches perfectly!")
        print("   Agent encryption → Server decryption working correctly!")
        return True
    else:
        print("\nFAILED: Data doesn't match!")
        print(f"   Original: {test_data}")
        print(f"   Decrypted: {decrypted}")
        return False

def test_key_mismatch():
    """Test that mismatched keys fail gracefully"""
    print("\n\nTesting key mismatch protection...")
    
    # Create two different keys
    key1 = AgentEncryption.generate_key()
    key2 = AgentEncryption.generate_key()
    
    print(f"   Key 1: {key1[:20]}...")
    print(f"   Key 2: {key2[:20]}...")
    
    # Agent uses key1, server uses key2
    agent = AgentEncryption(key1)
    server = ServerEncryption(key2)
    
    test_data = {'test': 'data'}
    
    encrypted = agent.encrypt_payload(test_data)
    print("\nAgent encrypted with Key 1")
    
    try:
        decrypted = server.decrypt_payload(encrypted)
        print("FAILED: Should have rejected mismatched key!")
        return False
    except Exception as e:
        print(f"SUCCESS: Correctly rejected mismatched key")
        print(f"   Error: {str(e)[:50]}...")
        return True

if __name__ == '__main__':
    print("="*70)
    print("End-to-End Encryption Test")
    print("="*70)
    
    # Test 1: Normal encryption/decryption
    success1 = test_encryption()
    
    # Test 2: Key mismatch protection
    success2 = test_key_mismatch()
    
    print("\n" + "="*70)
    if success1 and success2:
        print("ALL TESTS PASSED!")
        print("   Agent and server encryption is working correctly!")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
    print("="*70 + "\n")
