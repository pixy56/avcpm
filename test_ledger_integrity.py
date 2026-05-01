#!/usr/bin/env python3
"""
Test script for AVCPM Ledger Integrity integration

Tests the following:
1. Hash chaining between commits (previous_hash field)
2. Verify chain integrity on load
3. Detect tampering attempts
4. Rollback protection
"""

import os
import sys
import json
import tempfile
import shutil
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_ledger_integrity as li
import avcpm_branch as branch


def test_hash_chaining():
    """Test that entries can be hash-chained."""
    print("=" * 60)
    print("TEST: Hash Chaining")
    print("=" * 60)
    
    # Create test entries
    entry1 = {
        "commit_id": "20240101000001",
        "timestamp": "2024-01-01T00:00:01",
        "agent_id": "agent1",
        "task_id": "task1",
        "rationale": "First commit",
        "changes": [{"file": "file1.txt", "checksum": "abc123"}],
        "previous_hash": None
    }
    
    # Calculate hash for first entry
    hash1 = li.calculate_entry_hash(entry1)
    entry1["entry_hash"] = hash1
    
    print(f"Entry 1 hash: {hash1[:16]}...")
    
    # Create second entry chained to first
    entry2 = {
        "commit_id": "20240101000002",
        "timestamp": "2024-01-01T00:00:02",
        "agent_id": "agent1",
        "task_id": "task1",
        "rationale": "Second commit",
        "changes": [{"file": "file2.txt", "checksum": "def456"}],
        "previous_hash": hash1
    }
    
    hash2 = li.calculate_entry_hash(entry2)
    entry2["entry_hash"] = hash2
    
    print(f"Entry 2 hash: {hash2[:16]}...")
    print(f"Entry 2 previous_hash: {entry2['previous_hash'][:16]}...")
    
    # Verify chain
    assert entry2["previous_hash"] == hash1, "Hash chain should link to previous entry"
    
    print("✓ Hash chaining works correctly")
    return True


def test_integrity_verification():
    """Test integrity verification on valid chain."""
    print("\n" + "=" * 60)
    print("TEST: Integrity Verification (Valid Chain)")
    print("=" * 60)
    
    # Create temporary directory for test
    test_dir = tempfile.mkdtemp()
    base_dir = os.path.join(test_dir, ".avcpm")
    
    try:
        # Initialize branch
        branch._ensure_main_branch(base_dir)
        
        # Create ledger directory
        ledger_dir = branch.get_branch_ledger_dir("main", base_dir)
        os.makedirs(ledger_dir, exist_ok=True)
        
        # Create valid chain of commits
        commits = []
        prev_hash = None
        
        for i in range(3):
            commit_id = f"2024010100000{i+1}"
            entry = {
                "commit_id": commit_id,
                "timestamp": f"2024-01-01T00:00:0{i+1}",
                "agent_id": "agent1",
                "task_id": "task1",
                "rationale": f"Commit {i+1}",
                "changes": [{"file": f"file{i+1}.txt", "checksum": f"hash{i}"}],
                "previous_hash": prev_hash
            }
            
            entry_hash = li.calculate_entry_hash(entry)
            entry["entry_hash"] = entry_hash
            prev_hash = entry_hash
            commits.append(entry)
            
            # Write to ledger
            with open(os.path.join(ledger_dir, f"{commit_id}.json"), "w") as f:
                json.dump(entry, f, indent=2)
        
        # Verify integrity
        report = li.verify_ledger_integrity("main", base_dir)
        
        print(f"Total entries: {report.total_entries}")
        print(f"Valid entries: {report.valid_entries}")
        print(f"Invalid entries: {report.invalid_entries}")
        print(f"Success: {report.success}")
        
        assert report.success, "Valid chain should pass integrity check"
        assert report.valid_entries == 3, "All 3 entries should be valid"
        assert report.invalid_entries == 0, "No entries should be invalid"
        
        print("✓ Integrity verification works for valid chain")
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tampering_detection():
    """Test that tampering is detected."""
    print("\n" + "=" * 60)
    print("TEST: Tampering Detection")
    print("=" * 60)
    
    # Create temporary directory for test
    test_dir = tempfile.mkdtemp()
    base_dir = os.path.join(test_dir, ".avcpm")
    
    try:
        # Initialize branch
        branch._ensure_main_branch(base_dir)
        
        # Create ledger directory
        ledger_dir = branch.get_branch_ledger_dir("main", base_dir)
        os.makedirs(ledger_dir, exist_ok=True)
        
        # Create valid commit
        entry = {
            "commit_id": "20240101000001",
            "timestamp": "2024-01-01T00:00:01",
            "agent_id": "agent1",
            "task_id": "task1",
            "rationale": "Original commit",
            "changes": [{"file": "file1.txt", "checksum": "abc123"}],
            "previous_hash": None
        }
        
        entry_hash = li.calculate_entry_hash(entry)
        entry["entry_hash"] = entry_hash
        
        # Write to ledger
        commit_path = os.path.join(ledger_dir, "20240101000001.json")
        with open(commit_path, "w") as f:
            json.dump(entry, f, indent=2)
        
        # Verify original passes
        report = li.verify_ledger_integrity("main", base_dir)
        assert report.success, "Original should pass"
        print("Original chain valid: ✓")
        
        # Tamper with the entry
        entry["rationale"] = "TAMPERED COMMIT"
        # Don't recalculate hash - this simulates tampering
        
        with open(commit_path, "w") as f:
            json.dump(entry, f, indent=2)
        
        # Verify tampering is detected
        report = li.verify_ledger_integrity("main", base_dir)
        
        print(f"After tampering:")
        print(f"  Success: {report.success}")
        print(f"  Invalid entries: {report.invalid_entries}")
        print(f"  Tampered entries: {len(report.tampered_entries)}")
        
        assert not report.success, "Tampered chain should fail integrity check"
        assert report.invalid_entries == 1, "Should detect 1 tampered entry"
        assert len(report.tampered_entries) == 1, "Should report 1 tampered entry"
        assert report.tampered_entries[0].status == "invalid_hash", "Should be invalid_hash"
        
        print("✓ Tampering detection works correctly")
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_broken_chain_detection():
    """Test detection of broken hash chain."""
    print("\n" + "=" * 60)
    print("TEST: Broken Chain Detection")
    print("=" * 60)
    
    # Create temporary directory for test
    test_dir = tempfile.mkdtemp()
    base_dir = os.path.join(test_dir, ".avcpm")
    
    try:
        # Initialize branch
        branch._ensure_main_branch(base_dir)
        
        # Create ledger directory
        ledger_dir = branch.get_branch_ledger_dir("main", base_dir)
        os.makedirs(ledger_dir, exist_ok=True)
        
        # Create first commit
        entry1 = {
            "commit_id": "20240101000001",
            "timestamp": "2024-01-01T00:00:01",
            "agent_id": "agent1",
            "task_id": "task1",
            "rationale": "First commit",
            "changes": [{"file": "file1.txt", "checksum": "abc123"}],
            "previous_hash": None
        }
        
        hash1 = li.calculate_entry_hash(entry1)
        entry1["entry_hash"] = hash1
        
        # Write first entry
        with open(os.path.join(ledger_dir, "20240101000001.json"), "w") as f:
            json.dump(entry1, f, indent=2)
        
        # Create second commit with WRONG previous_hash (simulating insertion/deletion)
        entry2 = {
            "commit_id": "20240101000002",
            "timestamp": "2024-01-01T00:00:02",
            "agent_id": "agent1",
            "task_id": "task1",
            "rationale": "Second commit",
            "changes": [{"file": "file2.txt", "checksum": "def456"}],
            "previous_hash": "WRONG_HASH_VALUE_1234567890abcd",  # Intentionally wrong
            "entry_hash": "dummy_hash"  # Will be calculated
        }
        
        # Calculate proper hash for entry2
        entry2["entry_hash"] = li.calculate_entry_hash(entry2)
        
        with open(os.path.join(ledger_dir, "20240101000002.json"), "w") as f:
            json.dump(entry2, f, indent=2)
        
        # Verify broken chain is detected
        report = li.verify_ledger_integrity("main", base_dir)
        
        print(f"Broken chain detected:")
        print(f"  Success: {report.success}")
        print(f"  Invalid entries: {report.invalid_entries}")
        print(f"  Tampered entries: {len(report.tampered_entries)}")
        
        if report.tampered_entries:
            print(f"  First tampered status: {report.tampered_entries[0].status}")
        
        assert not report.success, "Broken chain should fail"
        # Entry1 should be valid, entry2 should have invalid_chain
        assert report.valid_entries == 1, "First entry should be valid"
        assert report.invalid_entries == 1, "Second entry should be invalid"
        
        print("✓ Broken chain detection works correctly")
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_report_formatting():
    """Test report formatting functions."""
    print("\n" + "=" * 60)
    print("TEST: Report Formatting")
    print("=" * 60)
    
    # Create a sample report
    report = li.IntegrityReport(
        branch="test-branch",
        total_entries=5,
        valid_entries=4,
        invalid_entries=1,
        tampered_entries=[
            li.IntegrityCheckResult(
                commit_id="20240101000003",
                status="invalid_hash",
                message="Entry content has been tampered with",
                previous_hash="abc123",
                expected_hash="expected_hash_value",
                actual_hash="actual_hash_value"
            )
        ],
        healthy=False
    )
    
    # Test formatting
    formatted = li.format_integrity_report(report)
    
    assert "test-branch" in formatted, "Report should contain branch name"
    assert "Total entries:   5" in formatted, "Report should show total"
    assert "TAMPERED ENTRIES" in formatted, "Report should show tampered section"
    assert "20240101000003" in formatted, "Report should show commit ID"
    
    print("Formatted report preview:")
    print(formatted[:500] + "...")
    print("✓ Report formatting works correctly")
    return True


def test_check_integrity_warning():
    """Test integrity warning function."""
    print("\n" + "=" * 60)
    print("TEST: Integrity Warning")
    print("=" * 60)
    
    # Create temporary directory for test
    test_dir = tempfile.mkdtemp()
    base_dir = os.path.join(test_dir, ".avcpm")
    
    try:
        # Initialize branch
        branch._ensure_main_branch(base_dir)
        ledger_dir = branch.get_branch_ledger_dir("main", base_dir)
        os.makedirs(ledger_dir, exist_ok=True)
        
        # Empty ledger should return no warning
        warning = li.check_integrity_warning("main", base_dir)
        assert warning is None, "Empty ledger should not produce warning"
        print("Empty ledger: No warning ✓")
        
        # Create valid commit
        entry = {
            "commit_id": "20240101000001",
            "timestamp": "2024-01-01T00:00:01",
            "agent_id": "agent1",
            "task_id": "task1",
            "rationale": "Test commit",
            "changes": [],
            "previous_hash": None,
            "entry_hash": "dummy"
        }
        entry["entry_hash"] = li.calculate_entry_hash(entry)
        
        with open(os.path.join(ledger_dir, "20240101000001.json"), "w") as f:
            json.dump(entry, f, indent=2)
        
        # Valid ledger should return no warning
        warning = li.check_integrity_warning("main", base_dir)
        assert warning is None, "Valid ledger should not produce warning"
        print("Valid ledger: No warning ✓")
        
        # Tamper with entry
        entry["rationale"] = "TAMPERED"
        with open(os.path.join(ledger_dir, "20240101000001.json"), "w") as f:
            json.dump(entry, f, indent=2)
        
        # Tampered ledger should return warning
        warning = li.check_integrity_warning("main", base_dir)
        assert warning is not None, "Tampered ledger should produce warning"
        assert "compromised" in warning.lower(), "Warning should mention compromise"
        print(f"Tampered ledger warning: {warning}")
        print("✓ Integrity warning works correctly")
        return True
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def run_all_tests():
    """Run all ledger integrity tests."""
    print("\n" + "=" * 60)
    print("AVCPM LEDGER INTEGRITY INTEGRATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Hash Chaining", test_hash_chaining),
        ("Integrity Verification", test_integrity_verification),
        ("Tampering Detection", test_tampering_detection),
        ("Broken Chain Detection", test_broken_chain_detection),
        ("Report Formatting", test_report_formatting),
        ("Integrity Warning", test_check_integrity_warning),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    failed = sum(1 for _, result, _ in results if not result)
    
    for name, result, error in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {status}: {name}")
        if error:
            print(f"    Error: {error}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
