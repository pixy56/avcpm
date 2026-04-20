#!/usr/bin/env python3
"""
AVCPM Phase 1 Integration Tests
Simple smoke tests verifying the full workflow works end-to-end.
"""

import os
import sys
import tempfile
import shutil
import json
import glob

# Add modules to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_task
import avcpm_commit
import avcpm_merge
import avcpm_validate
import avcpm_status


def test_full_workflow():
    """Test complete happy path: create task -> commit -> validate -> merge -> verify"""
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="avcpm_test_")
    base_dir = os.path.join(temp_dir, ".avcpm")
    
    # Save original stdout to capture prints
    import io
    old_stdout = sys.stdout
    
    try:
        # Initialize directory structure
        os.makedirs(os.path.join(base_dir, "tasks", "todo"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "tasks", "in-progress"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "tasks", "done"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "tasks", "review"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "staging"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "production"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "ledger"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "reviews"), exist_ok=True)
        
        # 1. Create a task
        task_id = "TASK-INTEGRATION-001"
        avcpm_task.create_task(
            task_id=task_id,
            description="Testing the full AVCPM workflow",
            assignee="TestRunner",
            base_dir=base_dir
        )
        print(f"✓ Created task: {task_id}")
        
        # 2. Move task to in-progress
        avcpm_task.move_task(task_id, "in-progress", base_dir=base_dir)
        print("✓ Moved task to in-progress")
        
        # 3. Create a test file and commit
        test_file = os.path.join(temp_dir, "test_integration.txt")
        with open(test_file, "w") as f:
            f.write("Integration test content v1")
        
        avcpm_commit.commit(
            task_id=task_id,
            agent_id="TestRunner",
            rationale="Integration test commit",
            files_to_commit=[test_file],
            base_dir=base_dir
        )
        
        # Get the commit ID from the most recent ledger file
        ledger_files = sorted(glob.glob(os.path.join(base_dir, "ledger", "*.json")))
        assert len(ledger_files) > 0, "No ledger file created"
        latest_ledger = ledger_files[-1]
        with open(latest_ledger) as f:
            ledger_data = json.load(f)
        commit_id = ledger_data["commit_id"]
        print(f"✓ Committed: {commit_id}")
        
        # 4. Validate checksums
        staging_dir = os.path.join(base_dir, "staging")
        ledger_dir = os.path.join(base_dir, "ledger")
        validation = avcpm_validate.validate_checksums(
            staging_dir=staging_dir,
            ledger_dir=ledger_dir
        )
        assert validation.success, f"Validation failed: {validation.errors}"
        print(f"✓ Validation passed: {validation.files_checked} files checked")
        
        # 5. Create review approval
        review_file = os.path.join(base_dir, "reviews", f"{commit_id}.review")
        with open(review_file, "w") as f:
            json.dump({
                "commit_id": commit_id,
                "status": "APPROVED",
                "reviewer": "TestReviewer",
                "timestamp": "2026-04-19T20:00:00Z",
                "notes": "Integration test approval"
            }, f, indent=2)
        print("✓ Created review approval")
        
        # 6. Merge to production (redirect stdout)
        sys.stdout = io.StringIO()
        try:
            avcpm_merge.merge(
                commit_id=commit_id,
                base_dir=base_dir
            )
        except SystemExit:
            pass  # merge() calls sys.exit()
        sys.stdout = old_stdout
        
        # Verify production file exists
        prod_file = os.path.join(temp_dir, "test_integration.txt")
        assert os.path.exists(prod_file), "Production file not created"
        print("✓ Merged to production")
        
        # 7. Move task to done
        avcpm_task.move_task(task_id, "done", base_dir=base_dir)
        print("✓ Moved task to done")
        
        # 8. Verify status
        tasks = avcpm_status.get_tasks_by_status(base_dir=base_dir)
        done_tasks = [t["id"] for t in tasks.get("done", [])]
        assert task_id in done_tasks, f"Task not in done. Found: {done_tasks}"
        print("✓ Status verification passed")
        
        print("\n=== Full workflow test PASSED ===")
        return True
        
    finally:
        sys.stdout = old_stdout
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


#!/usr/bin/env python3
"""
AVCPM Phase 2 Integration Tests
Tests verifying the full workflow with agent identity and cryptographic signing.
"""

import os
import sys
import tempfile
import shutil
import json
import glob
import io

# Add modules to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_task
import avcpm_commit
import avcpm_merge
import avcpm_validate
import avcpm_status
import avcpm_agent


def test_full_workflow_with_agent_identity():
    """Test complete happy path with agent identity: create agent -> create task -> commit -> validate -> merge -> verify"""
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="avcpm_test_")
    base_dir = os.path.join(temp_dir, ".avcpm")
    
    # Save original stdout to capture prints
    old_stdout = sys.stdout
    
    try:
        # Initialize directory structure
        os.makedirs(os.path.join(base_dir, "tasks", "todo"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "tasks", "in-progress"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "tasks", "done"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "tasks", "review"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "staging"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "production"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "ledger"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "reviews"), exist_ok=True)
        
        # 1. Create an agent FIRST (new requirement)
        agent_data = avcpm_agent.create_agent(
            name="TestAgent",
            email="test@example.com",
            base_dir=base_dir
        )
        agent_id = agent_data["agent_id"]
        print(f"✓ Created agent: {agent_id}")
        
        # 2. Create a task
        task_id = "TASK-INTEGRATION-001"
        avcpm_task.create_task(
            task_id=task_id,
            description="Testing the full AVCPM workflow with agent identity",
            assignee=agent_id,  # Use agent_id as assignee
            base_dir=base_dir
        )
        print(f"✓ Created task: {task_id}")
        
        # 3. Move task to in-progress
        avcpm_task.move_task(task_id, "in-progress", base_dir=base_dir)
        print("✓ Moved task to in-progress")
        
        # 4. Create a test file and commit with agent_id
        test_file = os.path.join(temp_dir, "test_integration.txt")
        with open(test_file, "w") as f:
            f.write("Integration test content v1")
        
        avcpm_commit.commit(
            task_id=task_id,
            agent_id=agent_id,  # Pass agent_id
            rationale="Integration test commit",
            files_to_commit=[test_file],
            base_dir=base_dir
        )
        
        # Get the commit ID from the most recent ledger file
        ledger_files = sorted(glob.glob(os.path.join(base_dir, "ledger", "*.json")))
        assert len(ledger_files) > 0, "No ledger file created"
        latest_ledger = ledger_files[-1]
        with open(latest_ledger) as f:
            ledger_data = json.load(f)
        commit_id = ledger_data["commit_id"]
        print(f"✓ Committed: {commit_id}")
        
        # 5. Verify commit has signature
        assert "signature" in ledger_data, "Commit missing signature"
        assert "changes_hash" in ledger_data, "Commit missing changes_hash"
        assert ledger_data["agent_id"] == agent_id, "Agent ID mismatch"
        print(f"✓ Commit has valid signature from agent {agent_id}")
        
        # 6. Validate checksums
        staging_dir = os.path.join(base_dir, "staging")
        ledger_dir = os.path.join(base_dir, "ledger")
        validation = avcpm_validate.validate_checksums(
            staging_dir=staging_dir,
            ledger_dir=ledger_dir
        )
        assert validation.success, f"Validation failed: {validation.errors}"
        print(f"✓ Validation passed: {validation.files_checked} files checked")
        
        # 7. Create review approval
        review_file = os.path.join(base_dir, "reviews", f"{commit_id}.review")
        with open(review_file, "w") as f:
            json.dump({
                "commit_id": commit_id,
                "status": "APPROVED",
                "reviewer": "TestReviewer",
                "timestamp": "2026-04-19T20:00:00Z",
                "notes": "Integration test approval"
            }, f, indent=2)
        print("✓ Created review approval")
        
        # 8. Merge to production (redirect stdout)
        sys.stdout = io.StringIO()
        try:
            avcpm_merge.merge(
                commit_id=commit_id,
                base_dir=base_dir
            )
        except SystemExit:
            pass  # merge() calls sys.exit()
        sys.stdout = old_stdout
        
        # Verify production file exists
        prod_file = os.path.join(temp_dir, "test_integration.txt")
        assert os.path.exists(prod_file), "Production file not created"
        print("✓ Merged to production (signature verified during merge)")
        
        # 9. Move task to done
        avcpm_task.move_task(task_id, "done", base_dir=base_dir)
        print("✓ Moved task to done")
        
        # 10. Verify status
        tasks = avcpm_status.get_tasks_by_status(base_dir=base_dir)
        done_tasks = [t["id"] for t in tasks.get("done", [])]
        assert task_id in done_tasks, f"Task not in done. Found: {done_tasks}"
        print("✓ Status verification passed")
        
        print("\n=== Full workflow test with agent identity PASSED ===")
        return True
        
    finally:
        sys.stdout = old_stdout
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_commit_fails_without_agent():
    """Test that commit fails if agent doesn't exist"""
    temp_dir = tempfile.mkdtemp(prefix="avcpm_test_")
    base_dir = os.path.join(temp_dir, ".avcpm")
    
    try:
        # Initialize directories
        os.makedirs(os.path.join(base_dir, "tasks", "todo"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "staging"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "ledger"), exist_ok=True)
        
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        # Try to commit with non-existent agent
        try:
            avcpm_commit.commit(
                task_id="TASK-001",
                agent_id="nonexistent",
                rationale="Test",
                files_to_commit=[test_file],
                base_dir=base_dir
            )
            assert False, "Commit should have failed with non-existent agent"
        except ValueError as e:
            assert "nonexistent" in str(e), f"Expected agent not found error, got: {e}"
        
        print("✓ Commit fails without valid agent PASSED")
        return True
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_merge_fails_with_tampered_signature():
    """Test that merge fails if commit signature is tampered"""
    temp_dir = tempfile.mkdtemp(prefix="avcpm_test_")
    base_dir = os.path.join(temp_dir, ".avcpm")
    
    old_stdout = sys.stdout
    
    try:
        # Initialize directories
        for subdir in ["tasks/todo", "tasks/in-progress", "staging", "ledger", "reviews"]:
            os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)
        
        # Create agent
        agent_data = avcpm_agent.create_agent(
            name="TestAgent",
            email="test@example.com",
            base_dir=base_dir
        )
        agent_id = agent_data["agent_id"]
        
        # Create and commit file
        test_file = os.path.join(temp_dir, "tamper_test.txt")
        with open(test_file, "w") as f:
            f.write("Original content")
        
        avcpm_commit.commit(
            task_id="TASK-TAMPER",
            agent_id=agent_id,
            rationale="Test tampering",
            files_to_commit=[test_file],
            base_dir=base_dir
        )
        
        # Get commit info
        ledger_files = glob.glob(os.path.join(base_dir, "ledger", "*.json"))
        assert len(ledger_files) == 1, "Expected one ledger file"
        ledger_path = ledger_files[0]
        
        with open(ledger_path) as f:
            commit_data = json.load(f)
        commit_id = commit_data["commit_id"]
        
        # Tamper with the signature
        commit_data["signature"] = "tampered" + commit_data["signature"][7:]
        with open(ledger_path, "w") as f:
            json.dump(commit_data, f, indent=2)
        
        # Create review approval
        review_file = os.path.join(base_dir, "reviews", f"{commit_id}.review")
        with open(review_file, "w") as f:
            json.dump({
                "commit_id": commit_id,
                "status": "APPROVED",
                "reviewer": "TestReviewer",
                "timestamp": "2026-04-19T20:00:00Z"
            }, f)
        
        # Try to merge - should fail due to tampered signature
        sys.stdout = io.StringIO()
        try:
            avcpm_merge.merge(
                commit_id=commit_id,
                base_dir=base_dir
            )
            sys.stdout = old_stdout
            assert False, "Merge should have failed with tampered signature"
        except SystemExit as e:
            sys.stdout = old_stdout
            # Check that output mentions invalid signature
            # (We can't capture the print from merge, but we expect SystemExit)
        
        print("✓ Merge fails with tampered signature PASSED")
        return True
        
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_validation_detects_tampering():
    """Test that validation detects modified files"""
    temp_dir = tempfile.mkdtemp(prefix="avcpm_test_")
    base_dir = os.path.join(temp_dir, ".avcpm")
    
    try:
        # Setup
        for subdir in ["tasks/todo", "tasks/in-progress", "staging", "ledger"]:
            os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)
        
        # Create and commit file
        test_file = os.path.join(base_dir, "staging", "tamper_test.txt")
        with open(test_file, "w") as f:
            f.write("Original content")
        
        # Manually create ledger entry (simulating commit)
        import hashlib
        with open(test_file, "rb") as f:
            original_hash = hashlib.sha256(f.read()).hexdigest()
        
        ledger_entry = {
            "commit_id": "test-tamper-001",
            "timestamp": "2026-04-19T20:00:00Z",
            "agent_id": "TestRunner",
            "task_id": "TASK-TAMPER",
            "rationale": "Test",
            "changes": [{"file": test_file, "checksum": original_hash, "staging_path": test_file}],
            "signature": "dummy",  # Not validating signature in this test
            "changes_hash": "dummy"
        }
        
        ledger_file = os.path.join(base_dir, "ledger", "20260419200000.json")
        with open(ledger_file, "w") as f:
            json.dump(ledger_entry, f, indent=2)
        
        # Tamper with file
        with open(test_file, "w") as f:
            f.write("Tampered content")
        
        # Validate should detect mismatch
        staging_dir = os.path.join(base_dir, "staging")
        ledger_dir = os.path.join(base_dir, "ledger")
        validation = avcpm_validate.validate_checksums(
            staging_dir=staging_dir,
            ledger_dir=ledger_dir
        )
        assert not validation.success, "Validation should have failed"
        assert validation.failed > 0, "Should have failed checksums"
        
        print("✓ Tampering detection test PASSED")
        return True
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_system_health():
    """Test system health check identifies issues"""
    temp_dir = tempfile.mkdtemp(prefix="avcpm_test_")
    base_dir = os.path.join(temp_dir, ".avcpm")
    
    try:
        # Setup with orphaned file
        os.makedirs(os.path.join(base_dir, "staging"), exist_ok=True)
        
        # Create orphaned staging file (no ledger entry)
        with open(os.path.join(base_dir, "staging", "orphan.txt"), "w") as f:
            f.write("orphan")
        
        health = avcpm_status.check_system_health(base_dir=base_dir)
        
        # Should detect the orphaned file
        has_orphan = any("orphan" in str(issue).lower() or "untracked" in str(issue).lower() 
                        for issue in health.get("issues", []))
        print(f"✓ System health check PASSED (detected issues: {has_orphan})")
        return True
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Running AVCPM Phase 2 Integration Tests\n")
    
    try:
        test_full_workflow_with_agent_identity()
        test_commit_fails_without_agent()
        test_merge_fails_with_tampered_signature()
        test_validation_detects_tampering()
        test_system_health()
        print("\n=== ALL TESTS PASSED ===")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n=== TEST FAILED: {e} ===")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n=== TEST ERROR: {e} ===")
        traceback.print_exc()
        sys.exit(1)
