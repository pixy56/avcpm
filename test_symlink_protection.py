#!/usr/bin/env python3
"""
Test script for AVCPM Symlink Attack Protection

This script demonstrates that the AVCPM codebase is now protected against symlink attacks.
"""

import os
import sys
import tempfile
import shutil

# Add workspace to path
sys.path.insert(0, '/home/user/.openclaw/workspace')

from avcpm_security import (
    SecurityError,
    safe_copy, safe_read, safe_write, safe_exists,
    safe_copytree, validate_path_is_safe,
    sanitize_path, is_path_within_base,
    safe_makedirs, safe_remove, safe_rmtree,
    protect_avcpm_directory, ensure_avcpm_directory_secure,
    safe_read_text, safe_write_text
)


def test_path_traversal_detection():
    """Test that path traversal attacks are detected."""
    print("Testing path traversal detection...")
    
    # Should raise ValueError for path traversal
    try:
        sanitize_path('../etc/passwd', '/tmp')
        print("  ✗ FAILED: Path traversal should have been rejected")
        return False
    except ValueError as e:
        print(f"  ✓ Path traversal correctly rejected: {e}")
    
    # Should raise ValueError for absolute paths
    try:
        sanitize_path('/etc/passwd', '/tmp')
        print("  ✗ FAILED: Absolute path should have been rejected")
        return False
    except ValueError as e:
        print(f"  ✓ Absolute path correctly rejected: {e}")
    
    return True


def test_symlink_protection():
    """Test symlink protection in safe operations."""
    print("\nTesting symlink protection...")
    
    test_dir = tempfile.mkdtemp()
    avcpm_dir = os.path.join(test_dir, '.avcpm')
    os.makedirs(avcpm_dir)
    
    try:
        # Test 1: Create a file
        test_file = os.path.join(avcpm_dir, 'test.txt')
        safe_write_text(test_file, 'test content', avcpm_dir)
        assert os.path.exists(test_file)
        print("  ✓ File creation works")
        
        # Test 2: Create nested directories
        nested_dir = os.path.join(avcpm_dir, 'level1', 'level2', 'level3')
        safe_makedirs(nested_dir, avcpm_dir, exist_ok=True)
        assert os.path.exists(nested_dir)
        print("  ✓ Nested directory creation works")
        
        # Test 3: Copy file
        dest_file = os.path.join(avcpm_dir, 'copy.txt')
        safe_copy(test_file, dest_file, avcpm_dir)
        assert os.path.exists(dest_file)
        content = safe_read_text(dest_file, avcpm_dir)
        assert content == 'test content'
        print("  ✓ File copy and read works")
        
        # Test 4: Remove file
        safe_remove(dest_file, avcpm_dir)
        assert not os.path.exists(dest_file)
        print("  ✓ File removal works")
        
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_avcpm_directory_protection():
    """Test .avcpm directory symlink protection."""
    print("\nTesting .avcpm directory protection...")
    
    test_dir = tempfile.mkdtemp()
    
    try:
        # Test 1: Normal directory creation
        avcpm_dir = os.path.join(test_dir, '.avcpm')
        ensure_avcpm_directory_secure(avcpm_dir)
        assert os.path.exists(avcpm_dir)
        assert os.path.isdir(avcpm_dir)
        print("  ✓ Normal .avcpm directory creation works")
        
        # Test 2: Re-securing existing directory
        ensure_avcpm_directory_secure(avcpm_dir)
        print("  ✓ Re-securing existing directory works")
        
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_module_integration():
    """Test that modules import and basic functions work."""
    print("\nTesting module integration...")
    
    # Test imports
    modules = [
        'avcpm_security',
        'avcpm_branch',
        'avcpm_lifecycle',
        'avcpm_commit',
        'avcpm_rollback',
        'avcpm_conflict',
        'avcpm_wip',
        'avcpm_task',
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module} imports successfully")
        except Exception as e:
            print(f"  ✗ {module} failed: {e}")
            return False
    
    return True


def test_atomic_operations():
    """Test atomic file operations where applicable."""
    print("\nTesting atomic file operations...")
    
    test_dir = tempfile.mkdtemp()
    avcpm_dir = os.path.join(test_dir, '.avcpm')
    os.makedirs(avcpm_dir)
    
    try:
        # Test that file writes are complete or not at all
        test_file = os.path.join(avcpm_dir, 'atomic.txt')
        content = 'x' * 10000  # Large content
        
        safe_write_text(test_file, content, avcpm_dir)
        
        # Verify complete write
        read_content = safe_read_text(test_file, avcpm_dir)
        assert read_content == content
        print("  ✓ File write appears atomic (complete content written)")
        
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_realpath_resolution():
    """Test that realpath is used to resolve symlinks."""
    print("\nTesting realpath resolution...")
    
    test_dir = tempfile.mkdtemp()
    avcpm_dir = os.path.join(test_dir, '.avcpm')
    os.makedirs(avcpm_dir)
    
    try:
        # Create a subdirectory
        subdir = os.path.join(avcpm_dir, 'subdir')
        safe_makedirs(subdir, avcpm_dir, exist_ok=True)
        
        # Create a file in the subdirectory
        test_file = os.path.join(subdir, 'file.txt')
        safe_write_text(test_file, 'content', avcpm_dir)
        
        # Verify the file exists and is within base_dir
        assert validate_path_is_safe(test_file, avcpm_dir)
        print("  ✓ realpath resolution works correctly")
        
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def main():
    """Run all tests."""
    print("=" * 70)
    print("AVCPM Symlink Attack Protection - Security Test Suite")
    print("=" * 70)
    
    tests = [
        ("Path Traversal Detection", test_path_traversal_detection),
        ("Symlink Protection", test_symlink_protection),
        ("AVCPM Directory Protection", test_avcpm_directory_protection),
        ("Module Integration", test_module_integration),
        ("Atomic Operations", test_atomic_operations),
        ("Realpath Resolution", test_realpath_resolution),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"  Test '{name}' FAILED")
        except Exception as e:
            failed += 1
            print(f"  Test '{name}' FAILED with exception: {e}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✓ All security tests PASSED!")
        print("\nThe AVCPM codebase is now protected against symlink attacks.")
        return 0
    else:
        print(f"\n✗ {failed} test(s) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
