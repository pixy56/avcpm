#!/usr/bin/env python3
"""
Tests for AVCPM Work-in-Progress Tracking Module
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from datetime import datetime, timedelta

# Import the module under test
import avcpm_wip as wip


class TestWIPTracking(unittest.TestCase):
    """Test cases for WIP tracking functionality."""
    
    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.old_default = wip.DEFAULT_BASE_DIR
        
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)
        wip.DEFAULT_BASE_DIR = self.old_default
    
    def test_claim_file_success(self):
        """Test successful file claim."""
        result = wip.claim_file("test.py", "agent1", "TASK-001", self.test_dir)
        
        self.assertTrue(result["success"])
        self.assertIn("claim", result)
        self.assertEqual(result["claim"]["file"], "test.py")
        self.assertEqual(result["claim"]["claimed_by"], "agent1")
        self.assertEqual(result["claim"]["task_id"], "TASK-001")
        self.assertIn("claimed_at", result["claim"])
        self.assertIn("expires_at", result["claim"])
    
    def test_claim_file_already_claimed(self):
        """Test claiming a file already claimed by another agent."""
        # First agent claims
        wip.claim_file("test.py", "agent1", "TASK-001", self.test_dir)
        
        # Second agent tries to claim
        result = wip.claim_file("test.py", "agent2", "TASK-002", self.test_dir)
        
        self.assertFalse(result["success"])
        self.assertIn("agent1", result["message"])
        self.assertIn("TASK-001", result["message"])
    
    def test_same_agent_can_reclaim(self):
        """Test that same agent can re-claim their own file."""
        wip.claim_file("test.py", "agent1", "TASK-001", self.test_dir)
        result = wip.claim_file("test.py", "agent1", "TASK-002", self.test_dir)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["claim"]["task_id"], "TASK-002")
    
    def test_release_file_success(self):
        """Test successful file release."""
        wip.claim_file("test.py", "agent1", None, self.test_dir)
        result = wip.release_file("test.py", "agent1", self.test_dir)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Claim released")
        self.assertFalse(wip.is_claimed("test.py", self.test_dir))
    
    def test_release_file_not_claimed(self):
        """Test releasing a file that isn't claimed."""
        result = wip.release_file("test.py", "agent1", self.test_dir)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "File not claimed")
    
    def test_release_file_wrong_agent(self):
        """Test releasing a file claimed by another agent."""
        wip.claim_file("test.py", "agent1", None, self.test_dir)
        result = wip.release_file("test.py", "agent2", self.test_dir)
        
        self.assertFalse(result["success"])
        self.assertIn("agent1", result["message"])
    
    def test_release_all(self):
        """Test releasing all claims by an agent."""
        wip.claim_file("test1.py", "agent1", None, self.test_dir)
        wip.claim_file("test2.py", "agent1", None, self.test_dir)
        wip.claim_file("test3.py", "agent2", None, self.test_dir)  # Different agent
        
        result = wip.release_all("agent1", self.test_dir)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["released_count"], 2)
        self.assertIn("test1.py", result["released_files"])
        self.assertIn("test2.py", result["released_files"])
        self.assertTrue(wip.is_claimed("test3.py", self.test_dir))  # Still claimed
    
    def test_list_claims(self):
        """Test listing all claims."""
        wip.claim_file("test1.py", "agent1", "TASK-001", self.test_dir)
        wip.claim_file("test2.py", "agent2", "TASK-002", self.test_dir)
        
        result = wip.list_claims(self.test_dir)
        
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["claims"]), 2)
    
    def test_list_my_claims(self):
        """Test listing claims by specific agent."""
        wip.claim_file("test1.py", "agent1", "TASK-001", self.test_dir)
        wip.claim_file("test2.py", "agent1", "TASK-002", self.test_dir)
        wip.claim_file("test3.py", "agent2", "TASK-003", self.test_dir)
        
        result = wip.list_my_claims("agent1", self.test_dir)
        
        self.assertEqual(result["count"], 2)
        files = [c["file"] for c in result["claims"]]
        self.assertIn("test1.py", files)
        self.assertIn("test2.py", files)
        self.assertNotIn("test3.py", files)
    
    def test_get_claim(self):
        """Test getting claim details."""
        wip.claim_file("test.py", "agent1", "TASK-001", self.test_dir)
        
        claim = wip.get_claim("test.py", self.test_dir)
        
        self.assertIsNotNone(claim)
        self.assertEqual(claim["file"], "test.py")
        self.assertEqual(claim["claimed_by"], "agent1")
        self.assertEqual(claim["task_id"], "TASK-001")
    
    def test_get_claim_not_exists(self):
        """Test getting claim for unclaimed file."""
        claim = wip.get_claim("test.py", self.test_dir)
        self.assertIsNone(claim)
    
    def test_is_claimed(self):
        """Test checking if file is claimed."""
        self.assertFalse(wip.is_claimed("test.py", self.test_dir))
        
        wip.claim_file("test.py", "agent1", None, self.test_dir)
        
        self.assertTrue(wip.is_claimed("test.py", self.test_dir))
    
    def test_check_wip_conflicts_no_conflict(self):
        """Test conflict check with no conflicts."""
        result = wip.check_wip_conflicts(["test1.py", "test2.py"], "agent1", self.test_dir)
        
        self.assertFalse(result["has_conflicts"])
        self.assertEqual(len(result["conflicts"]), 0)
        self.assertEqual(len(result["clear"]), 2)
    
    def test_check_wip_conflicts_with_conflict(self):
        """Test conflict detection with conflicting claim."""
        wip.claim_file("test1.py", "agent2", "TASK-002", self.test_dir)
        
        result = wip.check_wip_conflicts(["test1.py", "test2.py"], "agent1", self.test_dir)
        
        self.assertTrue(result["has_conflicts"])
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertEqual(result["conflicts"][0]["file"], "test1.py")
        self.assertEqual(result["conflicts"][0]["claimed_by"], "agent2")
        self.assertEqual(len(result["clear"]), 1)
        self.assertEqual(result["clear"][0]["file"], "test2.py")
    
    def test_check_wip_conflicts_self_claimed(self):
        """Test that self-claimed files don't show as conflicts."""
        wip.claim_file("test1.py", "agent1", "TASK-001", self.test_dir)
        
        result = wip.check_wip_conflicts(["test1.py"], "agent1", self.test_dir)
        
        self.assertFalse(result["has_conflicts"])
        self.assertEqual(len(result["clear"]), 1)
        self.assertEqual(result["clear"][0]["status"], "self_claimed")
    
    def test_expire_stale_claims(self):
        """Test auto-expiration of stale claims."""
        # Create a claim manually with old timestamp
        registry = {"claims": {}}
        old_time = datetime.utcnow() - timedelta(hours=25)
        registry["claims"]["stale.py"] = {
            "file": "stale.py",
            "claimed_by": "agent1",
            "task_id": "OLD-TASK",
            "claimed_at": old_time.isoformat(),
            "expires_at": (old_time + timedelta(hours=24)).isoformat()
        }
        
        # Save registry
        wip._ensure_wip_dir(self.test_dir)
        with open(os.path.join(self.test_dir, wip.WIP_DIR, wip.WIP_REGISTRY), 'w') as f:
            json.dump(registry, f)
        
        # Add a fresh claim
        wip.claim_file("fresh.py", "agent2", "NEW-TASK", self.test_dir)
        
        # Expire stale claims
        result = wip.expire_stale_claims(max_age_hours=24, base_dir=self.test_dir)
        
        self.assertEqual(result["expired_count"], 1)
        self.assertEqual(result["expired_files"][0]["file"], "stale.py")
        self.assertTrue(wip.is_claimed("fresh.py", self.test_dir))  # Still there
        self.assertFalse(wip.is_claimed("stale.py", self.test_dir))  # Expired
    
    def test_expire_no_stale_claims(self):
        """Test expiration when no stale claims exist."""
        wip.claim_file("test.py", "agent1", None, self.test_dir)
        
        result = wip.expire_stale_claims(max_age_hours=24, base_dir=self.test_dir)
        
        self.assertEqual(result["expired_count"], 0)
        self.assertEqual(len(result["expired_files"]), 0)
        self.assertTrue(wip.is_claimed("test.py", self.test_dir))  # Still there
    
    def test_claim_files_glob(self):
        """Test claiming multiple files with glob pattern."""
        # Create test files
        for i in range(3):
            with open(os.path.join(self.test_dir, f"test{i}.py"), 'w') as f:
                f.write("# test")
        
        results = wip.claim_files("test*.py", "agent1", "TASK-001", self.test_dir)
        
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r["success"])
        
        # Verify all claimed
        for i in range(3):
            self.assertTrue(wip.is_claimed(f"test{i}.py", self.test_dir))
    
    def test_path_normalization(self):
        """Test that paths are normalized."""
        wip.claim_file("./subdir/../test.py", "agent1", None, self.test_dir)
        
        # Should be normalized in registry
        registry = wip._load_registry(self.test_dir)
        self.assertIn("test.py", registry["claims"])
    
    def test_registry_persistence(self):
        """Test that claims persist across operations."""
        wip.claim_file("test.py", "agent1", "TASK-001", self.test_dir)
        
        # Load fresh registry
        registry = wip._load_registry(self.test_dir)
        
        self.assertIn("test.py", registry["claims"])
        self.assertEqual(registry["claims"]["test.py"]["claimed_by"], "agent1")
    
    def test_ensure_wip_dir(self):
        """Test that .avcpm directory is created."""
        wip._ensure_wip_dir(self.test_dir)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, ".avcpm")))


class TestCLI(unittest.TestCase):
    """Test CLI interface functionality."""
    
    def setUp(self):
        """Create a temporary directory and test files."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, 'w') as f:
            f.write("# test")
    
    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.test_dir)
    
    def test_cli_claim_and_release(self):
        """Test basic CLI claim and release workflow."""
        import subprocess
        
        # Claim
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", self.test_dir,
             "--agent", "agent1", "claim", "test.py", "--task", "TASK-001"],
            capture_output=True, text=True, cwd="/home/user/.openclaw/workspace"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Claimed", result.stdout)
        
        # List
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", self.test_dir,
             "--agent", "agent1", "list"],
            capture_output=True, text=True, cwd="/home/user/.openclaw/workspace"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("test.py", result.stdout)
        
        # Release
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", self.test_dir,
             "--agent", "agent1", "release", "test.py"],
            capture_output=True, text=True, cwd="/home/user/.openclaw/workspace"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Released", result.stdout)
    
    def test_cli_check_conflicts(self):
        """Test CLI conflict checking."""
        import subprocess
        
        # Claim a file
        wip.claim_file("test.py", "agent2", "TASK-002", self.test_dir)
        
        # Check as different agent - should find conflict
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", self.test_dir,
             "--agent", "agent1", "check", "test.py"],
            capture_output=True, text=True, cwd="/home/user/.openclaw/workspace"
        )
        self.assertEqual(result.returncode, 1)  # Exit code 1 for conflicts
        self.assertIn("Conflicts found", result.stdout)
    
    def test_cli_list_mine(self):
        """Test CLI list --mine option."""
        import subprocess
        
        wip.claim_file("test.py", "agent1", "TASK-001", self.test_dir)
        wip.claim_file("other.py", "agent2", "TASK-002", self.test_dir)
        
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", self.test_dir,
             "--agent", "agent1", "list", "--mine"],
            capture_output=True, text=True, cwd="/home/user/.openclaw/workspace"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("test.py", result.stdout)
        self.assertNotIn("other.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
