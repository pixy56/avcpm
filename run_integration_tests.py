#!/usr/bin/env python3
"""
Standalone test runner for AVCPM integration tests.
Does not require pytest - runs tests directly.
"""

from __future__ import annotations

import os
import sys
import json
import shutil
import hashlib
import tempfile
import traceback
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules under test
import avcpm_task
import avcpm_commit
import avcpm_merge
import avcpm_validate
import avcpm_status
from typing import Any, Dict, List, Optional, Tuple, Union


# =============================================================================
# Test Framework
# =============================================================================

class TestResult:
    """Simple test result container."""
    def __init__(self) -> None:
        self.passed = []
        self.failed = []
        self.skipped = []
        self.bugs_found = []

    def add_pass(self, test_name: Any) -> None:
        self.passed.append(test_name)
        print(f"  ✓ {test_name}")

    def add_fail(self, test_name: Any, error: Any) -> None:
        self.failed.append((test_name, error))
        print(f"  ✗ {test_name}")
        print(f"    Error: {str(error)[:200]}")

    def add_bug(self, test_name: Any, description: str) -> None:
        self.bugs_found.append((test_name, description))
        print(f"  ⚠ {test_name}")
        print(f"    BUG DOCUMENTED: {description}")

    def summary(self) -> Any:
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Passed:  {len(self.passed)}")
        print(f"Failed:  {len(self.failed)}")
        print(f"Bugs Documented: {len(self.bugs_found)}")
        print("=" * 70)
        
        if self.bugs_found:
            print("\nBUGS FOUND:")
            for test_name, desc in self.bugs_found:
                print(f"  - {test_name}: {desc}")
        
        if self.failed:
            print("\nFAILED TESTS:")
            for test_name, error in self.failed:
                print(f"  - {test_name}: {error}")
        
        print("\n" + "=" * 70)
        
        return len(self.failed) == 0


@contextmanager
def temp_avcpm_dir() -> None:
    """Create a temporary AVCPM directory structure."""
    temp_dir = tempfile.mkdtemp(prefix="avcpm_test_")
    
    # Create directory structure
    dirs = [
        os.path.join(temp_dir, ".avcpm", "tasks", "todo"),
        os.path.join(temp_dir, ".avcpm", "tasks", "in-progress"),
        os.path.join(temp_dir, ".avcpm", "tasks", "review"),
        os.path.join(temp_dir, ".avcpm", "tasks", "done"),
        os.path.join(temp_dir, ".avcpm", "ledger"),
        os.path.join(temp_dir, ".avcpm", "staging"),
        os.path.join(temp_dir, ".avcpm", "reviews"),
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def mock_avcpm_paths(temp_dir: Any) -> Any:
    """Set up mock paths for testing."""
    base = temp_dir
    avcpm_base = os.path.join(base, ".avcpm")
    
    # Store original values
    originals = {
        'task': avcpm_task.BASE_DIR,
        'commit_ledger': avcpm_commit.LEDGER_DIR,
        'commit_staging': avcpm_commit.STAGING_DIR,
        'merge_reviews': avcpm_merge.REVIEWS_DIR,
        'merge_staging': avcpm_merge.STAGING_DIR,
        'status_base': avcpm_status.BASE_DIR,
        'status_tasks': avcpm_status.TASKS_DIR,
        'status_ledger': avcpm_status.LEDGER_DIR,
        'status_staging': avcpm_status.STAGING_DIR,
        'status_reviews': avcpm_status.REVIEWS_DIR,
    }
    
    # Set mock values
    avcpm_task.BASE_DIR = os.path.join(avcpm_base, "tasks")
    avcpm_commit.LEDGER_DIR = os.path.join(avcpm_base, "ledger")
    avcpm_commit.STAGING_DIR = os.path.join(avcpm_base, "staging")
    avcpm_merge.REVIEWS_DIR = os.path.join(avcpm_base, "reviews")
    avcpm_merge.STAGING_DIR = os.path.join(avcpm_base, "staging")
    avcpm_status.BASE_DIR = avcpm_base
    avcpm_status.TASKS_DIR = os.path.join(avcpm_base, "tasks")
    avcpm_status.LEDGER_DIR = os.path.join(avcpm_base, "ledger")
    avcpm_status.STAGING_DIR = os.path.join(avcpm_base, "staging")
    avcpm_status.REVIEWS_DIR = os.path.join(avcpm_base, "reviews")
    
    return originals


def restore_avcpm_paths(originals: Any) -> None:
    """Restore original path values."""
    avcpm_task.BASE_DIR = originals['task']
    avcpm_commit.LEDGER_DIR = originals['commit_ledger']
    avcpm_commit.STAGING_DIR = originals['commit_staging']
    avcpm_merge.REVIEWS_DIR = originals['merge_reviews']
    avcpm_merge.STAGING_DIR = originals['merge_staging']
    avcpm_status.BASE_DIR = originals['status_base']
    avcpm_status.TASKS_DIR = originals['status_tasks']
    avcpm_status.LEDGER_DIR = originals['status_ledger']
    avcpm_status.STAGING_DIR = originals['status_staging']
    avcpm_status.REVIEWS_DIR = originals['status_reviews']


def create_approval(reviews_dir: Any, commit_id: str, approver: Any="test_user", notes: Any="LGTM") -> Any:
    """Create an approval review file."""
    review_path = os.path.join(reviews_dir, f"{commit_id}.review")
    review_content = f"""APPROVED
Approver: {approver}
Date: {datetime.now().isoformat()}
Notes: {notes}
"""
    with open(review_path, "w") as f:
        f.write(review_content)
    return review_path


def create_rejection(reviews_dir: Any, commit_id: str, reviewer: Any="test_user", reason: str="Needs work") -> Any:
    """Create a rejection review file."""
    review_path = os.path.join(reviews_dir, f"{commit_id}.review")
    review_content = f"""REJECTED
Reviewer: {reviewer}
Date: {datetime.now().isoformat()}
Reason: {reason}
"""
    with open(review_path, "w") as f:
        f.write(review_content)
    return review_path


# =============================================================================
# Tests
# =============================================================================

def test_full_happy_path() -> Tuple[Any, ...]:
    """Test complete workflow: task → commit → validate → approve → merge → status."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            base_path = temp_dir
            task_id = "TEST-001"
            agent_id = "integration-tester"
            rationale = "Testing full AVCPM workflow"
            
            # Create test file
            sample_file = os.path.join(temp_dir, "test_file.txt")
            with open(sample_file, "w") as f:
                f.write("This is test content for AVCPM integration testing.")
            
            # Step 1: Create task
            avcpm_task.create_task(task_id, "Integration test task", "tester")
            
            task_path = os.path.join(avcpm_task.BASE_DIR, "todo", f"{task_id}.json")
            assert os.path.exists(task_path), "Task file should be created"
            
            # Step 2 & 3: Commit
            avcpm_commit.commit(task_id, agent_id, rationale, [sample_file])
            
            # Get commit_id
            ledger_files = os.listdir(avcpm_commit.LEDGER_DIR)
            assert len(ledger_files) == 1, "Should have one ledger entry"
            
            with open(os.path.join(avcpm_commit.LEDGER_DIR, ledger_files[0]), "r") as f:
                ledger_data = json.load(f)
            commit_id = ledger_data["commit_id"]
            
            # Verify staging
            staging_file = os.path.join(avcpm_commit.STAGING_DIR, os.path.basename(sample_file))
            assert os.path.exists(staging_file), "File should be in staging"
            
            # Step 4: Validate
            report = avcpm_validate.validate_checksums(
                staging_dir=avcpm_commit.STAGING_DIR,
                ledger_dir=avcpm_commit.LEDGER_DIR
            )
            
            assert report.success, f"Validation should pass: {report.results}"
            assert report.passed == 1, "Should have 1 passed"
            
            # Step 5: Approve
            create_approval(avcpm_merge.REVIEWS_DIR, commit_id)
            
            # Step 6: Merge
            # NOTE: avcpm_merge uses hardcoded paths and looks for ledger in .avcpm/ledger
            # relative to current working directory, not using avcpm_commit.LEDGER_DIR
            # We need to change to the temp directory for merge to work
            orig_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            dest_file = os.path.join(temp_dir, "production_file.txt")
            ledger_data["changes"][0]["file"] = dest_file
            with open(os.path.join(".avcpm", "ledger", ledger_files[0]), "w") as f:
                json.dump(ledger_data, f, indent=4)
            
            try:
                avcpm_merge.merge(commit_id)
            except SystemExit as e:
                os.chdir(orig_cwd)
                if e.code != 0:
                    raise AssertionError(f"Merge failed with exit code {e.code}")
            finally:
                os.chdir(orig_cwd)
            
            assert os.path.exists(dest_file), "Production file should exist"
            
            # Step 7: Check status
            tasks_report = avcpm_status.generate_tasks_report()
            health_report = avcpm_status.check_system_health()
            
            assert tasks_report["summary"]["todo"] == 1
            assert health_report["healthy"]
            
            return True, "Full happy path completed successfully"
            
        finally:
            restore_avcpm_paths(originals)


def test_task_workflow_states() -> Tuple[Any, ...]:
    """Test moving tasks through workflow states."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            task_id = "WORKFLOW-001"
            
            # Create task
            avcpm_task.create_task(task_id, "Workflow test", "tester")
            
            # Verify in todo
            assert os.path.exists(os.path.join(avcpm_task.BASE_DIR, "todo", f"{task_id}.json"))
            
            # Move through states
            for col in ["in-progress", "review", "done"]:
                avcpm_task.move_task(task_id, col)
                assert os.path.exists(os.path.join(avcpm_task.BASE_DIR, col, f"{task_id}.json"))
                
                with open(os.path.join(avcpm_task.BASE_DIR, col, f"{task_id}.json"), "r") as f:
                    data = json.load(f)
                assert data["status_history"][-1]["status"] == col
            
            return True, "Task workflow states work correctly"
        finally:
            restore_avcpm_paths(originals)


def test_merge_without_approval() -> Tuple[Any, ...]:
    """Test that merge fails without approval."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            task_id = "NO-APPROVE"
            
            sample_file = os.path.join(temp_dir, "test.txt")
            with open(sample_file, "w") as f:
                f.write("content")
            
            avcpm_task.create_task(task_id, "No approval test", "tester")
            avcpm_commit.commit(task_id, "tester", "Test", [sample_file])
            
            # Get commit_id
            ledger_files = os.listdir(avcpm_commit.LEDGER_DIR)
            with open(os.path.join(avcpm_commit.LEDGER_DIR, ledger_files[0]), "r") as f:
                commit_id = json.load(f)["commit_id"]
            
            # Attempt merge without approval
            try:
                avcpm_merge.merge(commit_id)
                return False, "Merge should have failed without approval"
            except SystemExit as e:
                if e.code == 1:
                    return True, "Correctly rejected merge without approval"
                raise AssertionError(f"Unexpected exit code: {e.code}")
            
        finally:
            restore_avcpm_paths(originals)


def test_validate_tampered_file() -> Tuple[Any, ...]:
    """Test validation catches tampered files."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            task_id = "TAMPER-001"
            
            sample_file = os.path.join(temp_dir, "test.txt")
            with open(sample_file, "w") as f:
                f.write("original content")
            
            avcpm_task.create_task(task_id, "Tamper test", "tester")
            avcpm_commit.commit(task_id, "tester", "Test", [sample_file])
            
            # Get ledger info
            with open(os.listdir(avcpm_commit.LEDGER_DIR)[0], "r") as f:
                ledger_data = json.load(f)
            staging_file = ledger_data["changes"][0]["staging_path"]
            
            # Tamper with file
            with open(staging_file, "w") as f:
                f.write("TAMPERED CONTENT")
            
            # Validate
            report = avcpm_validate.validate_checksums(
                staging_dir=avcpm_commit.STAGING_DIR,
                ledger_dir=avcpm_commit.LEDGER_DIR
            )
            
            if not report.success and report.failed == 1:
                return True, "Correctly detected tampered file"
            else:
                return False, f"Failed to detect tampering: {report.results}"
            
        finally:
            restore_avcpm_paths(originals)


def test_validate_missing_file() -> Tuple[Any, ...]:
    """Test validation handles missing files."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            task_id = "MISSING-001"
            
            sample_file = os.path.join(temp_dir, "test.txt")
            with open(sample_file, "w") as f:
                f.write("content")
            
            avcpm_task.create_task(task_id, "Missing file test", "tester")
            avcpm_commit.commit(task_id, "tester", "Test", [sample_file])
            
            # Get staging path and delete file
            with open(os.listdir(avcpm_commit.LEDGER_DIR)[0], "r") as f:
                ledger_data = json.load(f)
            staging_file = ledger_data["changes"][0]["staging_path"]
            os.remove(staging_file)
            
            # Validate
            report = avcpm_validate.validate_checksums(
                staging_dir=avcpm_commit.STAGING_DIR,
                ledger_dir=avcpm_commit.LEDGER_DIR
            )
            
            if len(report.orphaned_entries) >= 1:
                return True, "Correctly detected orphaned ledger entry"
            else:
                return False, f"Failed to detect orphaned entry: {report}"
            
        finally:
            restore_avcpm_paths(originals)


def test_validate_untracked_file() -> Tuple[Any, ...]:
    """Test validation detects untracked staging files."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            # Create untracked file in staging
            untracked = os.path.join(avcpm_commit.STAGING_DIR, "untracked.txt")
            with open(untracked, "w") as f:
                f.write("not tracked")
            
            report = avcpm_validate.validate_checksums(
                staging_dir=avcpm_commit.STAGING_DIR,
                ledger_dir=avcpm_commit.LEDGER_DIR
            )
            
            orphaned = [r for r in report.results if r.status == "orphaned_entry"]
            if len(orphaned) == 1:
                return True, "Correctly detected untracked file"
            else:
                return False, f"Failed to detect untracked file: {report.results}"
            
        finally:
            restore_avcpm_paths(originals)


def test_duplicate_task_id() -> Tuple[Any, ...]:
    """Test duplicate task handling."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            task_id = "DUPLICATE-001"
            
            avcpm_task.create_task(task_id, "First", "tester")
            
            try:
                avcpm_task.create_task(task_id, "Second", "tester")
                return False, "Should reject duplicate task ID"
            except SystemExit as e:
                if e.code == 1:
                    return True, "Correctly rejected duplicate task ID"
                raise AssertionError(f"Unexpected exit code: {e.code}")
            
        finally:
            restore_avcpm_paths(originals)


def test_multiple_files_commit() -> Tuple[Any, ...]:
    """Test committing multiple files."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            task_id = "MULTI-001"
            
            files = []
            for i in range(3):
                filepath = os.path.join(temp_dir, f"file_{i}.txt")
                with open(filepath, "w") as f:
                    f.write(f"Content {i}")
                files.append(filepath)
            
            avcpm_task.create_task(task_id, "Multi-file test", "tester")
            avcpm_commit.commit(task_id, "tester", "Multiple files", files)
            
            report = avcpm_validate.validate_checksums(
                staging_dir=avcpm_commit.STAGING_DIR,
                ledger_dir=avcpm_commit.LEDGER_DIR
            )
            
            if report.success and report.passed == 3:
                return True, "Multi-file commit validated successfully"
            else:
                return False, f"Multi-file validation failed: {report}"
            
        finally:
            restore_avcpm_paths(originals)


def test_status_health_check() -> Tuple[Any, ...]:
    """Test status health check detects issues."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            task_id = "HEALTH-001"
            
            sample_file = os.path.join(temp_dir, "test.txt")
            with open(sample_file, "w") as f:
                f.write("content")
            
            avcpm_task.create_task(task_id, "Health test", "tester")
            avcpm_commit.commit(task_id, "tester", "Health test", [sample_file])
            
            # Delete task to create orphaned ledger
            os.remove(os.path.join(avcpm_task.BASE_DIR, "todo", f"{task_id}.json"))
            
            health = avcpm_status.check_system_health()
            
            if not health["healthy"] and any(task_id in issue for issue in health["issues"]):
                return True, "Health check detected orphaned task"
            else:
                return False, f"Health check missed orphaned task: {health}"
            
        finally:
            restore_avcpm_paths(originals)


def test_empty_file_commit() -> Tuple[Any, ...]:
    """Test committing empty files."""
    with temp_avcpm_dir() as temp_dir:
        originals = mock_avcpm_paths(temp_dir)
        try:
            task_id = "EMPTY-001"
            
            empty_file = os.path.join(temp_dir, "empty.txt")
            with open(empty_file, "w") as f:
                pass  # Empty file
            
            avcpm_task.create_task(task_id, "Empty file test", "tester")
            avcpm_commit.commit(task_id, "tester", "Empty commit", [empty_file])
            
            report = avcpm_validate.validate_checksums(
                staging_dir=avcpm_commit.STAGING_DIR,
                ledger_dir=avcpm_commit.LEDGER_DIR
            )
            
            if report.success:
                return True, "Empty file commit works"
            else:
                return False, f"Empty file validation failed: {report}"
            
        finally:
            restore_avcpm_paths(originals)


# =============================================================================
# Main Runner
# =============================================================================

def main() -> None:
    print("=" * 70)
    print("AVCPM Phase 1 Integration Test Suite")
    print("=" * 70)
    print()
    
    results = TestResult()
    
    tests = [
        ("Happy Path: Full Workflow", test_full_happy_path),
        ("Happy Path: Task Workflow States", test_task_workflow_states),
        ("Error Case: Merge Without Approval", test_merge_without_approval),
        ("Error Case: Validate Tampered File", test_validate_tampered_file),
        ("Error Case: Validate Missing File", test_validate_missing_file),
        ("Error Case: Validate Untracked File", test_validate_untracked_file),
        ("Error Case: Duplicate Task ID", test_duplicate_task_id),
        ("Complex: Multiple Files Commit", test_multiple_files_commit),
        ("Status: Health Check", test_status_health_check),
        ("Edge Case: Empty File", test_empty_file_commit),
    ]
    
    for test_name, test_func in tests:
        try:
            success, message = test_func()
            if success:
                results.add_pass(f"{test_name}: {message}")
            else:
                results.add_fail(test_name, message)
        except Exception as e:
            results.add_fail(test_name, f"{type(e).__name__}: {e}")
            traceback.print_exc()
    
    # Report bugs found
    print("\n" + "-" * 70)
    print("BUGS DOCUMENTED (Behavioral Issues Found During Testing)")
    print("-" * 70)
    bugs = [
        ("avcpm_merge.merge()", "Uses sys.exit(1) instead of raising exceptions for errors"),
        ("avcpm_task.create_task()", "Uses sys.exit(1) instead of raising exceptions for duplicates"),
        ("avcpm_task.move_task()", "Uses sys.exit(1) instead of raising exceptions for invalid status/task not found"),
        ("avcpm_commit.commit()", "Prints warnings to stdout instead of returning status/errors"),
        ("Module CLI Mode", "All modules use sys.exit() which prevents programmatic error handling"),
    ]
    for module, issue in bugs:
        results.add_bug(module, issue)
    
    # Final summary
    all_passed = results.summary()
    
    print("\nRECOMMENDATIONS:")
    print("- Consider replacing sys.exit() calls with proper exceptions for library usage")
    print("- Add return values/status codes instead of printing to stdout")
    print("- Consider adding a programmatic API mode separate from CLI")
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())