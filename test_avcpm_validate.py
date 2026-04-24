"""
Tests for AVCPM Checksum Validator.

Converted from unittest.TestCase to pytest fixtures.
Run with: python -m pytest test_avcpm_validate.py -v
"""

import os
import sys
import json
import hashlib

import pytest

# Import the module under test
import avcpm_validate as validator


# ----- Fixtures -----

@pytest.fixture
def validator_env(tmp_path):
    """Set up validator test environment with staging and ledger dirs."""
    staging_dir = tmp_path / "staging"
    ledger_dir = tmp_path / "ledger"
    
    staging_dir.mkdir()
    ledger_dir.mkdir()
    
    return {
        "staging_dir": str(staging_dir),
        "ledger_dir": str(ledger_dir),
        "temp_dir": tmp_path
    }


# ----- Test Checksum Validation -----

class TestChecksumValidation:
    """Test cases for checksum validation functionality."""

    def _create_test_file(self, staging_dir: str, filename: str, content: str) -> str:
        """Helper to create a test file and return its checksum."""
        filepath = os.path.join(staging_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        
        sha256 = hashlib.sha256()
        sha256.update(content.encode())
        return sha256.hexdigest()

    def _create_ledger_entry(self, ledger_dir: str, commit_id: str, changes: list):
        """Helper to create a ledger entry."""
        entry = {
            "commit_id": commit_id,
            "timestamp": "2026-04-19T12:00:00",
            "agent_id": "TestAgent",
            "task_id": "TEST-001",
            "rationale": "Test commit",
            "changes": changes
        }
        
        ledger_file = os.path.join(ledger_dir, f"{commit_id}.json")
        with open(ledger_file, "w") as f:
            json.dump(entry, f, indent=4)

    def test_calculate_checksum(self, validator_env):
        """Test checksum calculation."""
        content = "Hello, World!"
        filepath = os.path.join(str(validator_env["temp_dir"]), "test.txt")
        with open(filepath, "w") as f:
            f.write(content)
        
        expected = hashlib.sha256(content.encode()).hexdigest()
        actual = validator.calculate_checksum(filepath)
        
        assert expected == actual

    def test_validate_all_pass(self, validator_env):
        """Test validation when all checksums match."""
        staging_dir = validator_env["staging_dir"]
        ledger_dir = validator_env["ledger_dir"]
        
        # Create a test file
        content = "test content"
        checksum = self._create_test_file(staging_dir, "test.txt", content)
        
        # Create ledger entry with matching checksum
        self._create_ledger_entry(ledger_dir, "20260101120000", [
            {
                "file": "test.txt",
                "checksum": checksum,
                "staging_path": f"{staging_dir}/test.txt"
            }
        ])
        
        # Run validation
        report = validator.validate_checksums(staging_dir, ledger_dir)
        
        assert report.success is True
        assert report.files_checked == 1
        assert report.passed == 1
        assert report.failed == 0
        assert report.errors == 0

    def test_validate_checksum_mismatch(self, validator_env):
        """Test validation detects checksum mismatches."""
        staging_dir = validator_env["staging_dir"]
        ledger_dir = validator_env["ledger_dir"]
        
        # Create a test file
        content = "test content"
        self._create_test_file(staging_dir, "test.txt", content)
        
        # Create ledger entry with WRONG checksum
        wrong_checksum = "a" * 64  # Invalid checksum
        self._create_ledger_entry(ledger_dir, "20260101120000", [
            {
                "file": "test.txt",
                "checksum": wrong_checksum,
                "staging_path": f"{staging_dir}/test.txt"
            }
        ])
        
        # Run validation
        report = validator.validate_checksums(staging_dir, ledger_dir)
        
        assert report.success is False
        assert report.files_checked == 1
        assert report.passed == 0
        assert report.failed == 1
        assert report.errors == 0
        
        # Verify the mismatch was detected correctly
        assert report.results[0].status == "failed"
        assert report.results[0].expected_checksum == wrong_checksum
        assert report.results[0].actual_checksum != wrong_checksum

    def test_validate_missing_file(self, validator_env):
        """Test validation detects missing files referenced in ledger."""
        ledger_dir = validator_env["ledger_dir"]
        
        # Create ledger entry for file that doesn't exist
        self._create_ledger_entry(ledger_dir, "20260101120000", [
            {
                "file": "missing.txt",
                "checksum": "a" * 64,
                "staging_path": f"{validator_env['staging_dir']}/missing.txt"
            }
        ])
        
        # Run validation (no files in staging)
        report = validator.validate_checksums(validator_env["staging_dir"], ledger_dir)
        
        assert report.success is False
        assert report.files_checked == 0
        assert report.errors == 1
        assert len(report.orphaned_entries) == 1
        assert report.orphaned_entries[0]["file"] == "missing.txt"

    def test_validate_orphaned_file(self, validator_env):
        """Test validation detects files in staging not in ledger."""
        staging_dir = validator_env["staging_dir"]
        
        # Create a file in staging
        self._create_test_file(staging_dir, "orphaned.txt", "orphan content")
        
        # No ledger entry
        
        # Run validation
        report = validator.validate_checksums(staging_dir, validator_env["ledger_dir"])
        
        assert report.success is False
        assert report.files_checked == 1
        assert report.errors == 1
        assert report.results[0].status == "orphaned_entry"

    def test_validate_multiple_files_mixed_results(self, validator_env):
        """Test validation with multiple files having different statuses."""
        staging_dir = validator_env["staging_dir"]
        ledger_dir = validator_env["ledger_dir"]
        
        # File 1: Passes
        content1 = "file one content"
        checksum1 = self._create_test_file(staging_dir, "file1.txt", content1)
        
        # File 2: Fails (wrong checksum)
        content2 = "file two content"
        self._create_test_file(staging_dir, "file2.txt", content2)
        wrong_checksum2 = "b" * 64
        
        # File 3: Orphaned (no ledger entry)
        self._create_test_file(staging_dir, "orphaned.txt", "orphan")
        
        # Create ledger with entries for file1 and file2
        self._create_ledger_entry(ledger_dir, "20260101120000", [
            {
                "file": "file1.txt",
                "checksum": checksum1,
                "staging_path": f"{staging_dir}/file1.txt"
            },
            {
                "file": "file2.txt",
                "checksum": wrong_checksum2,
                "staging_path": f"{staging_dir}/file2.txt"
            }
        ])
        
        # Run validation
        report = validator.validate_checksums(staging_dir, ledger_dir)
        
        assert report.success is False
        assert report.files_checked == 3
        assert report.passed == 1
        assert report.failed == 1
        assert report.errors == 1  # orphaned file
        
        # Check individual results
        statuses = {r.file: r.status for r in report.results}
        assert statuses["file1.txt"] == "passed"
        assert statuses["file2.txt"] == "failed"
        assert statuses["orphaned.txt"] == "orphaned_entry"

    def test_validate_empty_staging(self, validator_env):
        """Test validation with empty staging directory."""
        report = validator.validate_checksums(
            validator_env["staging_dir"], 
            validator_env["ledger_dir"]
        )
        
        assert report.success is True
        assert report.files_checked == 0
        assert report.passed == 0
        assert report.failed == 0
        assert report.errors == 0

    def test_validate_empty_ledger(self, validator_env):
        """Test validation with empty ledger directory."""
        staging_dir = validator_env["staging_dir"]
        
        # Create file in staging without ledger entry
        self._create_test_file(staging_dir, "untracked.txt", "content")
        
        report = validator.validate_checksums(staging_dir, validator_env["ledger_dir"])
        
        assert report.success is False
        assert report.files_checked == 1
        assert report.errors == 1  # orphaned file
        assert report.results[0].status == "orphaned_entry"

    def test_validate_subdirectory_files(self, validator_env):
        """Test validation of files in subdirectories."""
        staging_dir = validator_env["staging_dir"]
        ledger_dir = validator_env["ledger_dir"]
        
        # Create file in subdirectory
        content = "nested content"
        checksum = self._create_test_file(staging_dir, "subdir/nested.txt", content)
        
        self._create_ledger_entry(ledger_dir, "20260101120000", [
            {
                "file": "subdir/nested.txt",
                "checksum": checksum,
                "staging_path": f"{staging_dir}/subdir/nested.txt"
            }
        ])
        
        report = validator.validate_checksums(staging_dir, ledger_dir)
        
        assert report.success is True
        assert report.files_checked == 1
        assert report.passed == 1

    def test_fix_mismatches(self, validator_env):
        """Test the --fix functionality for mismatched checksums."""
        staging_dir = validator_env["staging_dir"]
        ledger_dir = validator_env["ledger_dir"]
        
        # Create a test file
        content = "content that will change"
        self._create_test_file(staging_dir, "test.txt", content)
        
        # Create ledger entry with wrong checksum
        wrong_checksum = "c" * 64
        self._create_ledger_entry(ledger_dir, "20260101120000", [
            {
                "file": "test.txt",
                "checksum": wrong_checksum,
                "staging_path": f"{staging_dir}/test.txt"
            }
        ])
        
        # Validate - should fail
        report = validator.validate_checksums(staging_dir, ledger_dir)
        assert report.success is False
        assert report.failed == 1
        
        # Fix mismatches
        fixes = validator.fix_mismatches(report, ledger_dir)
        assert fixes == 1
        
        # Re-validate - should pass
        report = validator.validate_checksums(staging_dir, ledger_dir)
        assert report.success is True
        assert report.passed == 1
        assert report.failed == 0

    def test_load_ledger_entries(self, validator_env):
        """Test loading ledger entries from directory."""
        ledger_dir = validator_env["ledger_dir"]
        
        # Create multiple ledger entries
        self._create_ledger_entry(ledger_dir, "20260101120000", [
            {"file": "a.txt", "checksum": "1" * 64, "staging_path": f"{validator_env['staging_dir']}/a.txt"}
        ])
        self._create_ledger_entry(ledger_dir, "20260101130000", [
            {"file": "b.txt", "checksum": "2" * 64, "staging_path": f"{validator_env['staging_dir']}/b.txt"}
        ])
        
        entries = validator.load_ledger_entries(ledger_dir)
        
        assert len(entries) == 2
        commit_ids = [e["commit_id"] for e in entries]
        assert "20260101120000" in commit_ids
        assert "20260101130000" in commit_ids

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
        
        assert "/staging/test.txt" in index
        assert index["/staging/test.txt"]["checksum"] == "abc123"
        assert index["/staging/test.txt"]["file"] == "test.txt"


# ----- Test CLI -----

class TestCLI:
    """Test CLI functionality."""

    def test_main_success_exit_code(self, validator_env, tmp_path):
        """Test main exits with 0 on success."""
        staging_dir = validator_env["staging_dir"]
        ledger_dir = validator_env["ledger_dir"]
        
        # Create a valid file and ledger
        content = "test"
        sha256 = hashlib.sha256(content.encode()).hexdigest()
        
        filepath = os.path.join(staging_dir, "test.txt")
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
        
        ledger_file = os.path.join(ledger_dir, "001.json")
        with open(ledger_file, "w") as f:
            json.dump(entry, f)
        
        # Patch sys.argv and run main
        original_argv = sys.argv
        try:
            sys.argv = [
                "avcpm_validate.py",
                "--staging-dir", staging_dir,
                "--ledger-dir", ledger_dir,
                "--quiet"
            ]
            
            try:
                validator.main()
            except SystemExit as e:
                assert e.code == 0
        finally:
            sys.argv = original_argv

    def test_main_failure_exit_code(self, validator_env, tmp_path):
        """Test main exits with 1 on failure."""
        staging_dir = validator_env["staging_dir"]
        ledger_dir = validator_env["ledger_dir"]
        
        # Create a file with wrong checksum
        content = "test"
        filepath = os.path.join(staging_dir, "test.txt")
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
        
        ledger_file = os.path.join(ledger_dir, "001.json")
        with open(ledger_file, "w") as f:
            json.dump(entry, f)
        
        # Patch sys.argv and run main
        original_argv = sys.argv
        try:
            sys.argv = [
                "avcpm_validate.py",
                "--staging-dir", staging_dir,
                "--ledger-dir", ledger_dir,
                "--quiet"
            ]
            
            try:
                validator.main()
            except SystemExit as e:
                assert e.code == 1
        finally:
            sys.argv = original_argv


# ----- Test Report -----

class TestReport:
    """Test ValidationReport dataclass."""

    def test_report_success_property(self):
        """Test report success property."""
        # Empty report should be success
        report = validator.ValidationReport()
        assert report.success is True
        
        # Report with failures should not be success
        report.failed = 1
        assert report.success is False
        
        # Report with errors should not be success
        report.failed = 0
        report.errors = 1
        assert report.success is False
        
        # Report with orphaned entries should not be success
        report.errors = 0
        report.orphaned_entries = [{"file": "missing.txt"}]
        assert report.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])