#!/usr/bin/env python3
"""
Standalone test script for private key encryption.
Tests that private keys are always encrypted and require passphrase.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from avcpm_agent import (
    create_agent,
    sign_data,
    verify_signature,
    get_agent_dir,
    list_agents,
    get_agent,
    _derive_key,
    _encrypt_data,
    _decrypt_data,
)

def test_passphrase_required_for_creation():
    """Test that passphrase is required for agent creation."""
    print("Test 1: Passphrase required for agent creation")
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, ".avcpm")
        try:
            agent = create_agent("Test Agent", "test@example.com", base_dir=base_dir)
            print("  FAIL: Should have raised ValueError")
            return False
        except ValueError as e:
            if "Passphrase is required" in str(e):
                print("  PASS: Correctly requires passphrase")
                return True
            else:
                print(f"  FAIL: Wrong error: {e}")
                return False

def test_passphrase_too_short():
    """Test that short passphrase is rejected."""
    print("Test 2: Short passphrase rejected")
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, ".avcpm")
        try:
            agent = create_agent("Test Agent", "test@example.com", base_dir=base_dir, passphrase="short")
            print("  FAIL: Should have raised ValueError")
            return False
        except ValueError as e:
            if "at least 8 characters" in str(e):
                print("  PASS: Correctly rejects short passphrase")
                return True
            else:
                print(f"  FAIL: Wrong error: {e}")
                return False

def test_encrypted_key_creation():
    """Test that agent creates encrypted key."""
    print("Test 3: Encrypted key creation")
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, ".avcpm")
        passphrase = "secure_passphrase_123"
        
        agent = create_agent("Test Agent", "test@example.com", base_dir=base_dir, passphrase=passphrase)
        
        agent_dir = get_agent_dir(agent["agent_id"], base_dir=base_dir)
        encrypted_path = os.path.join(agent_dir, "private.pem.enc")
        plaintext_path = os.path.join(agent_dir, "private.pem")
        
        if not os.path.exists(encrypted_path):
            print("  FAIL: Encrypted key not created")
            return False
        
        if os.path.exists(plaintext_path):
            print("  FAIL: Plaintext key should not exist")
            return False
        
        print("  PASS: Encrypted key created, no plaintext key")
        return True

def test_sign_requires_passphrase():
    """Test that signing requires passphrase."""
    print("Test 4: Sign requires passphrase")
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, ".avcpm")
        passphrase = "secure_passphrase_123"
        
        agent = create_agent("Test Agent", "test@example.com", base_dir=base_dir, passphrase=passphrase)
        
        try:
            signature = sign_data(agent["agent_id"], "test data", base_dir=base_dir)
            print("  FAIL: Should have raised ValueError")
            return False
        except ValueError as e:
            if "Passphrase is required" in str(e):
                print("  PASS: Correctly requires passphrase for signing")
                return True
            else:
                print(f"  FAIL: Wrong error: {e}")
                return False

def test_sign_and_verify_with_passphrase():
    """Test signing and verification with passphrase."""
    print("Test 5: Sign and verify with passphrase")
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, ".avcpm")
        passphrase = "secure_passphrase_123"
        
        agent = create_agent("Test Agent", "test@example.com", base_dir=base_dir, passphrase=passphrase)
        
        data = "Hello, World!"
        signature = sign_data(agent["agent_id"], data, base_dir=base_dir, passphrase=passphrase)
        
        if not isinstance(signature, bytes) or len(signature) == 0:
            print("  FAIL: Invalid signature")
            return False
        
        is_valid = verify_signature(agent["agent_id"], data, signature, base_dir=base_dir)
        if not is_valid:
            print("  FAIL: Signature verification failed")
            return False
        
        # Test that wrong data fails
        is_invalid = verify_signature(agent["agent_id"], "wrong data", signature, base_dir=base_dir)
        if is_invalid:
            print("  FAIL: Should have rejected wrong data")
            return False
        
        print("  PASS: Sign and verify work correctly with passphrase")
        return True

def test_encryption_roundtrip():
    """Test encryption/decryption functions."""
    print("Test 6: Encryption roundtrip")
    passphrase = "test_passphrase_123"
    data = b"This is secret data that should be encrypted"
    
    encrypted = _encrypt_data(data, passphrase)
    decrypted = _decrypt_data(encrypted, passphrase)
    
    if decrypted != data:
        print("  FAIL: Decrypted data doesn't match original")
        return False
    
    # Test wrong passphrase fails
    try:
        _decrypt_data(encrypted, "wrong_passphrase")
        print("  FAIL: Should have failed with wrong passphrase")
        return False
    except ValueError:
        pass
    
    print("  PASS: Encryption/decryption work correctly")
    return True

def test_key_derivation():
    """Test PBKDF2 key derivation."""
    print("Test 7: PBKDF2 key derivation")
    passphrase = "test_passphrase"
    salt = os.urandom(16)
    
    key1 = _derive_key(passphrase, salt)
    key2 = _derive_key(passphrase, salt)
    
    if key1 != key2:
        print("  FAIL: Same passphrase should produce same key")
        return False
    
    different_salt = os.urandom(16)
    key3 = _derive_key(passphrase, different_salt)
    
    if key1 == key3:
        print("  FAIL: Different salts should produce different keys")
        return False
    
    print("  PASS: Key derivation is deterministic and salt-dependent")
    return True

def test_registry_encryption_flag():
    """Test that registry marks agents as encrypted."""
    print("Test 8: Registry encryption flag")
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, ".avcpm")
        passphrase = "secure_passphrase_123"
        
        agent = create_agent("Test Agent", "test@example.com", base_dir=base_dir, passphrase=passphrase)
        
        agent_info = get_agent(agent["agent_id"], base_dir=base_dir)
        
        if not agent_info.get("encrypted", False):
            print("  FAIL: Registry should mark agent as encrypted")
            return False
        
        print("  PASS: Registry correctly marks agent as encrypted")
        return True

def main():
    print("=" * 60)
    print("Private Key Encryption Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_passphrase_required_for_creation,
        test_passphrase_too_short,
        test_encrypted_key_creation,
        test_sign_requires_passphrase,
        test_sign_and_verify_with_passphrase,
        test_encryption_roundtrip,
        test_key_derivation,
        test_registry_encryption_flag,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
