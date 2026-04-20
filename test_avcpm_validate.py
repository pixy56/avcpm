#!/usr/bin/env python3
"""
Tests for AVCPM Checksum Validator.

Run with: python -m pytest test_avcpm_validate.py -v
Or: python test_avcpm_validate.py
"""

import os
import sys
import json
import tempfile
import shutil
import hashlib
import unittest
from pathlib import Path

# Import the module under test
import avcpm_validate as validator


class TestChecksumValidation(unittest.TestCase):
    """Test cases for checksum validation functionality."""

    def setUp(self):
        """Create temporary directories for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.staging_dir = os.path.join(self.temp_dir, "staging")
        self.ledger_dir = os.path.join(self.temp_dir, "ledger")
        
        os.makedirs(self.staging_dir)
        os.makedirs(self.ledger_dir)

    def tearDown(self):
        """Clean up temporary directories after each test."""
        shutil.rmtree(self.temp_dir)

    def _create_test_file(self, filename: str, content: str) -> str:
        """Create a test file with given content and return its checksum."""
        filepath = os.path.join(self.staging_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        
        sha256 = hashlib.sha256()
        sha256.update(content.encode())
        return sha256.hexdigest()

    def _create_ledger_entry(self, commit_id: str, changes: list):
        """Create a ledger entry with given changes."""
        entry = {
            "commit_id": commit_id,
            "timestamp": "2026-04-19T12:00:00",
            "agent_id": "TestAgent",
            "task_id": "TEST-001",
            "rationale": "Test commit",
            "changes": changes
        }
        
        ledger_file = os.path.join(self.ledger_dir, f"{commit_id}.json")
        with open(ledger_file, "w") as f:
            json.dump(entry, f, indent=4)

    def test_calculate_checksum(self):
        """Test checksum calculation."""
        content = "Hello, World!"
        filepath = os.path.join(self.temp_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write(content)
        
        expected = hashlib.sha256(content.encode()).hexdigest()
        actual = validator.calculate_checksum(filepath)
        
        self.assertEqual(expected, actual)

    def test_validate_all_pass(self):
        """Test validation when all checksums match."""
        # Create a test file
        content = "test content"
        checksum = self._create_test_file("test.txt", content)
        
        # Create ledger entry with matching checksum
        self._create_ledger_entry("20260101120000", [
            {
                "file": "test.txt",
                "checksum": checksum,
                "staging_path": f"{self.staging_dir}/test.txt"
            }
        ])
        
        # Run validation
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        
        self.assertTrue(report.success)
        self.assertEqual(report.files_checked, 1)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 0)
        self.assertEqual(report.errors, 0)

    def test_validate_checksum_mismatch(self):
        """Test validation detects checksum mismatches."""
        # Create a test file
        content = "test content"
        self._create_test_file("test.txt", content)
        
        # Create ledger entry with WRONG checksum
        wrong_checksum = "a" * 64  # Invalid checksum
        self._create_ledger_entry("20260101120000", [
            {
                "file": "test.txt",
                "checksum": wrong_checksum,
                "staging_path": f"{self.staging_dir}/test.txt"
            }
        ])
        
        # Run validation
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        
        self.assertFalse(report.success)
        self.assertEqual(report.files_checked, 1)
        self.assertEqual(report.passed, 0)
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.errors, 0)
        
        # Verify the mismatch was detected correctly
        self.assertEqual(report.results[0].status, "failed")
        self.assertEqual(report.results[0].expected_checksum, wrong_checksum)
        self.assertNotEqual(report.results[0].actual_checksum, wrong_checksum)

    def test_validate_missing_file(self):
        """Test validation detects missing files referenced in ledger."""
        # Create ledger entry for file that doesn't exist
        self._create_ledger_entry("20260101120000", [
            {
                "file": "missing.txt",
                "checksum": "a" * 64,
                "staging_path": f"{self.staging_dir}/missing.txt"
            }
        ])
        
        # Run validation (no files in staging)
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        
        self.assertFalse(report.success)
        self.assertEqual(report.files_checked, 0)
        self.assertEqual(report.errors, 1)
        self.assertEqual(len(report.orphaned_entries), 1)
        self.assertEqual(report.orphaned_entries[0]["file"], "missing.txt")

    def test_validate_orphaned_file(self):
        """Test validation detects files in staging not in ledger."""
        # Create a file in staging
        self._create_test_file("orphaned.txt", "orphan content")
        
        # No ledger entry
        
        # Run validation
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        
        self.assertFalse(report.success)
        self.assertEqual(report.files_checked, 1)
        self.assertEqual(report.errors, 1)
        self.assertEqual(report.results[0].status, "orphaned_entry")

    def test_validate_multiple_files_mixed_results(self):
        """Test validation with multiple files having different statuses."""
        # File 1: Passes
        content1 = "file one content"
        checksum1 = self._create_test_file("file1.txt", content1)
        
        # File 2: Fails (wrong checksum)
        content2 = "file two content"
        self._create_test_file("file2.txt", content2)
        wrong_checksum2 = "b" * 64
        
        # File 3: Orphaned (no ledger entry)
        self._create_test_file("orphaned.txt", "orphan")
        
        # Create ledger with entries for file1 and file2
        self._create_ledger_entry("20260101120000", [
            {
                "file": "file1.txt",
                "checksum": checksum1,
                "staging_path": f"{self.staging_dir}/file1.txt"
            },
            {
                "file": "file2.txt",
                "checksum": wrong_checksum2,
                "staging_path": f"{self.staging_dir}/file2.txt"
            }
        ])
        
        # Run validation
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        
        self.assertFalse(report.success)
        self.assertEqual(report.files_checked, 3)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.errors, 1)  # orphaned file
        
        # Check individual results
        statuses = {r.file: r.status for r in report.results}
        self.assertEqual(statuses["file1.txt"], "passed")
        self.assertEqual(statuses["file2.txt"], "failed")
        self.assertEqual(statuses["orphaned.txt"], "orphaned_entry")

    def test_validate_empty_staging(self):
        """Test validation with empty staging directory."""
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        
        self.assertTrue(report.success)
        self.assertEqual(report.files_checked, 0)
        self.assertEqual(report.passed, 0)
        self.assertEqual(report.failed, 0)
        self.assertEqual(report.errors, 0)

    def test_validate_empty_ledger(self):
        """Test validation with empty ledger directory."""
        # Create file in staging without ledger entry
        self._create_test_file("untracked.txt", "content")
        
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        
        self.assertFalse(report.success)
        self.assertEqual(report.files_checked, 1)
        self.assertEqual(report.errors, 1)  # orphaned file
        self.assertEqual(report.results[0].status, "orphaned_entry")

    def test_validate_subdirectory_files(self):
        """Test validation of files in subdirectories."""
        # Create file in subdirectory
        content = "nested content"
        checksum = self._create_test_file("subdir/nested.txt", content)
        
        self._create_ledger_entry("20260101120000", [
            {
                "file": "subdir/nested.txt",
                "checksum": checksum,
                "staging_path": f"{self.staging_dir}/subdir/nested.txt"
            }
        ])
        
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        
        self.assertTrue(report.success)
        self.assertEqual(report.files_checked, 1)
        self.assertEqual(report.passed, 1)

    def test_fix_mismatches(self):
        """Test the --fix functionality for mismatched checksums."""
        # Create a test file
        content = "content that will change"
        self._create_test_file("test.txt", content)
        
        # Create ledger entry with wrong checksum
        wrong_checksum = "c" * 64
        self._create_ledger_entry("20260101120000", [
            {
                "file": "test.txt",
                "checksum": wrong_checksum,
                "staging_path": f"{self.staging_dir}/test.txt"
            }
        ])
        
        # Validate - should fail
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        self.assertFalse(report.success)
        self.assertEqual(report.failed, 1)
        
        # Fix mismatches
        fixes = validator.fix_mismatches(report, self.ledger_dir)
        self.assertEqual(fixes, 1)
        
        # Re-validate - should pass
        report = validator.validate_checksums(self.staging_dir, self.ledger_dir)
        self.assertTrue(report.success)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 0)

    def test_load_ledger_entries(self):
        """Test loading ledger entries from directory."""
        # Create multiple ledger entries
        self._create_ledger_entry("20260101120000", [
            {"file": "a.txt", "checksum": "1" * 64, "staging_path": f"{self.staging_dir}/a.txt"}
        ])
        self._create_ledger_entry("20260101130000", [
            {"file": "b.txt", "checksum": "2" * 64, "staging_path": f"{self.staging_dir}/b.txt"}
        ])
        
        entries = validator.load_ledger_entries(self.ledger_dir)
        
        self.assertEqual(len(entries), 2)
        commit_ids = [e["commit_id"] for e in entries]
        self.assertIn("20260101120000", commit_ids)
        self.assertIn("20260101130000", commit_ids)

    def test_build_checksum_index(self):
        """Test building checksum index from ledger entries."""
        entries = [
            {
                "commit_id": "001",
                "changes": [
                    {
                        "file": "test.txt",
                        "checksum": "abc123",
                        "staging_path": "/staging/test.txt"
                    }
                ]
            }
        ]
        
        index = validator.build_checksum_index(entries)
        
        self.assertIn("/staging/test.txt", index)
        self.assertEqual(index["/staging/test.txt"]["checksum"], "abc123")
        self.assertEqual(index["/staging/test.txt"]["file"], "test.txt")


class TestCLI(unittest.TestCase):
    """Test CLI functionality."""

    def setUp(self):
        """Create temporary directories for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.staging_dir = os.path.join(self.temp_dir, "staging")
        self.ledger_dir = os.path.join(self.temp_dir, "ledger")
        
        os.makedirs(self.staging_dir)
        os.makedirs(self.ledger_dir)

    def tearDown(self):
        """Clean up temporary directories after each test."""
        shutil.rmtree(self.temp_dir)

    def test_main_success_exit_code(self):
        """Test main exits with 0 on success."""
        # Create a valid file and ledger
        content = "test"
        sha256 = hashlib.sha256(content.encode()).hexdigest()
        
        filepath = os.path.join(self.staging_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write(content)
        
        entry = {
            "commit_id": "001",
            "changes": [{
                "file": "test.txt",
                "checksum": sha256,
                "staging_path": filepath
            }]
        }
        
        ledger_file = os.path.join(self.ledger_dir, "001.json")
        with open(ledger_file, "w") as f:
            json.dump(entry, f)
        
        # Patch sys.argv and run main
        original_argv = sys.argv
        try:
            sys.argv = [
                "avcpm_validate.py",
                "--staging-dir", self.staging_dir,
                "--ledger-dir", self.ledger_dir,
                "--quiet"
            ]
            
            try:
                validator.main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)
        finally:
            sys.argv = original_argv

    def test_main_failure_exit_code(self):
        """Test main exits with 1 on failure."""
        # Create a file with wrong checksum
        content = "test"
        filepath = os.path.join(self.staging_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write(content)
        
        entry = {
            "commit_id": "001",
            "changes": [{
                "file": "test.txt",
                "checksum": "wrong" * 16,
                "staging_path": filepath
            }]
        }
        
        ledger_file = os.path.join(self.ledger_dir, "001.json")
        with open(ledger_file, "w") as f:
            json.dump(entry, f)
        
        # Patch sys.argv and run main
        original_argv = sys.argv
        try:
            sys.argv = [
                "avcpm_validate.py",
                "--staging-dir", self.staging_dir,
                "--ledger-dir", self.ledger_dir,
                "--quiet"
            ]
            
            try:
                validator.main()
            except SystemExit as e:
                self.assertEqual(e.code, 1)
        finally:
            sys.argv = original_argv


class TestReport(unittest.TestCase):
    """Test ValidationReport dataclass."""

    def test_report_success_property(self):
        """Test report success property."""
        # Empty report should be success
        report = validator.ValidationReport()
        self.assertTrue(report.success)
        
        # Report with failures should not be success
        report.failed = 1
        self.assertFalse(report.success)
        
        # Report with errors should not be success
        report.failed = 0
        report.errors = 1
        self.assertFalse(report.success)
        
        # Report with orphaned entries should not be success
        report.errors = 0
        report.orphaned_entries = [{"file": "missing.txt"}]
        self.assertFalse(report.success)


if __name__ == "__main__":
    unittest.main(verbosity=2)