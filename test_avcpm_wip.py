"""
Tests for AVCPM Work-in-Progress Tracking Module

Converted from unittest.TestCase to pytest fixtures.
Run with: python -m pytest test_avcpm_wip.py -v
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Import the module under test
import avcpm_wip as wip


# ----- Fixtures -----

@pytest.fixture
def wip_env(tmp_path):
    """Set up WIP test environment."""
    # Store original default
    old_default = wip.DEFAULT_BASE_DIR
    
    yield {
        "test_dir": tmp_path,
        "old_default": old_default
    }
    
    # Cleanup
    wip.DEFAULT_BASE_DIR = old_default


@pytest.fixture
def test_file(tmp_path):
    """Create a test file for WIP testing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("# test")
    return test_file


# ----- Test WIP Tracking -----

class TestWIPTracking:
    """Test cases for WIP tracking functionality."""

    def test_claim_file_success(self, wip_env):
        """Test successful file claim."""
        test_dir = str(wip_env["test_dir"])
        result = wip.claim_file("test.py", "agent1", "TASK-001", test_dir)
        
        assert result["success"] is True
        assert "claim" in result
        assert result["claim"]["file"] == "test.py"
        assert result["claim"]["claimed_by"] == "agent1"
        assert result["claim"]["task_id"] == "TASK-001"
        assert "claimed_at" in result["claim"]
        assert "expires_at" in result["claim"]

    def test_claim_file_already_claimed(self, wip_env):
        """Test claiming a file already claimed by another agent."""
        test_dir = str(wip_env["test_dir"])
        
        # First agent claims
        wip.claim_file("test.py", "agent1", "TASK-001", test_dir)
        
        # Second agent tries to claim
        result = wip.claim_file("test.py", "agent2", "TASK-002", test_dir)
        
        assert result["success"] is False
        assert "agent1" in result["message"]
        assert "TASK-001" in result["message"]

    def test_same_agent_can_reclaim(self, wip_env):
        """Test that same agent can re-claim their own file."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test.py", "agent1", "TASK-001", test_dir)
        result = wip.claim_file("test.py", "agent1", "TASK-002", test_dir)
        
        assert result["success"] is True
        assert result["claim"]["task_id"] == "TASK-002"

    def test_release_file_success(self, wip_env):
        """Test successful file release."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test.py", "agent1", None, test_dir)
        result = wip.release_file("test.py", "agent1", test_dir)
        
        assert result["success"] is True
        assert result["message"] == "Claim released"
        assert wip.is_claimed("test.py", test_dir) is False

    def test_release_file_not_claimed(self, wip_env):
        """Test releasing a file that isn't claimed."""
        test_dir = str(wip_env["test_dir"])
        
        result = wip.release_file("test.py", "agent1", test_dir)
        
        assert result["success"] is False
        assert result["message"] == "File not claimed"

    def test_release_file_wrong_agent(self, wip_env):
        """Test releasing a file claimed by another agent."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test.py", "agent1", None, test_dir)
        result = wip.release_file("test.py", "agent2", test_dir)
        
        assert result["success"] is False
        assert "agent1" in result["message"]

    def test_release_all(self, wip_env):
        """Test releasing all claims by an agent."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test1.py", "agent1", None, test_dir)
        wip.claim_file("test2.py", "agent1", None, test_dir)
        wip.claim_file("test3.py", "agent2", None, test_dir)  # Different agent
        
        result = wip.release_all("agent1", test_dir)
        
        assert result["success"] is True
        assert result["released_count"] == 2
        assert "test1.py" in result["released_files"]
        assert "test2.py" in result["released_files"]
        assert wip.is_claimed("test3.py", test_dir) is True  # Still claimed

    def test_list_claims(self, wip_env):
        """Test listing all claims."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test1.py", "agent1", "TASK-001", test_dir)
        wip.claim_file("test2.py", "agent2", "TASK-002", test_dir)
        
        result = wip.list_claims(test_dir)
        
        assert result["count"] == 2
        assert len(result["claims"]) == 2

    def test_list_my_claims(self, wip_env):
        """Test listing claims by specific agent."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test1.py", "agent1", "TASK-001", test_dir)
        wip.claim_file("test2.py", "agent1", "TASK-002", test_dir)
        wip.claim_file("test3.py", "agent2", "TASK-003", test_dir)
        
        result = wip.list_my_claims("agent1", test_dir)
        
        assert result["count"] == 2
        files = [c["file"] for c in result["claims"]]
        assert "test1.py" in files
        assert "test2.py" in files
        assert "test3.py" not in files

    def test_get_claim(self, wip_env):
        """Test getting claim details."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test.py", "agent1", "TASK-001", test_dir)
        
        claim = wip.get_claim("test.py", test_dir)
        
        assert claim is not None
        assert claim["file"] == "test.py"
        assert claim["claimed_by"] == "agent1"
        assert claim["task_id"] == "TASK-001"

    def test_get_claim_not_exists(self, wip_env):
        """Test getting claim for unclaimed file."""
        test_dir = str(wip_env["test_dir"])
        
        claim = wip.get_claim("test.py", test_dir)
        assert claim is None

    def test_is_claimed(self, wip_env):
        """Test checking if file is claimed."""
        test_dir = str(wip_env["test_dir"])
        
        assert wip.is_claimed("test.py", test_dir) is False
        
        wip.claim_file("test.py", "agent1", None, test_dir)
        
        assert wip.is_claimed("test.py", test_dir) is True

    def test_check_wip_conflicts_no_conflict(self, wip_env):
        """Test conflict check with no conflicts."""
        test_dir = str(wip_env["test_dir"])
        
        result = wip.check_wip_conflicts(["test1.py", "test2.py"], "agent1", test_dir)
        
        assert result["has_conflicts"] is False
        assert len(result["conflicts"]) == 0
        assert len(result["clear"]) == 2

    def test_check_wip_conflicts_with_conflict(self, wip_env):
        """Test conflict detection with conflicting claim."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test1.py", "agent2", "TASK-002", test_dir)
        
        result = wip.check_wip_conflicts(["test1.py", "test2.py"], "agent1", test_dir)
        
        assert result["has_conflicts"] is True
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["file"] == "test1.py"
        assert result["conflicts"][0]["claimed_by"] == "agent2"
        assert len(result["clear"]) == 1
        assert result["clear"][0]["file"] == "test2.py"

    def test_check_wip_conflicts_self_claimed(self, wip_env):
        """Test that self-claimed files don't show as conflicts."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test1.py", "agent1", "TASK-001", test_dir)
        
        result = wip.check_wip_conflicts(["test1.py"], "agent1", test_dir)
        
        assert result["has_conflicts"] is False
        assert len(result["clear"]) == 1
        assert result["clear"][0]["status"] == "self_claimed"

    def test_expire_stale_claims(self, wip_env):
        """Test auto-expiration of stale claims."""
        test_dir = str(wip_env["test_dir"])
        
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
        wip._ensure_wip_dir(test_dir)
        with open(os.path.join(test_dir, wip.WIP_DIR, wip.WIP_REGISTRY), 'w') as f:
            json.dump(registry, f)
        
        # Add a fresh claim
        wip.claim_file("fresh.py", "agent2", "NEW-TASK", test_dir)
        
        # Expire stale claims
        result = wip.expire_stale_claims(max_age_hours=24, base_dir=test_dir)
        
        assert result["expired_count"] == 1
        assert result["expired_files"][0]["file"] == "stale.py"
        assert wip.is_claimed("fresh.py", test_dir) is True  # Still there
        assert wip.is_claimed("stale.py", test_dir) is False  # Expired

    def test_expire_no_stale_claims(self, wip_env):
        """Test expiration when no stale claims exist."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test.py", "agent1", None, test_dir)
        
        result = wip.expire_stale_claims(max_age_hours=24, base_dir=test_dir)
        
        assert result["expired_count"] == 0
        assert len(result["expired_files"]) == 0
        assert wip.is_claimed("test.py", test_dir) is True  # Still there

    def test_claim_files_glob(self, wip_env):
        """Test claiming multiple files with glob pattern."""
        test_dir = str(wip_env["test_dir"])
        
        # Create test files
        for i in range(3):
            with open(os.path.join(test_dir, f"test{i}.py"), 'w') as f:
                f.write("# test")
        
        results = wip.claim_files("test*.py", "agent1", "TASK-001", test_dir)
        
        assert len(results) == 3
        for r in results:
            assert r["success"] is True
        
        # Verify all claimed
        for i in range(3):
            assert wip.is_claimed(f"test{i}.py", test_dir) is True

    def test_path_normalization(self, wip_env):
        """Test that paths are normalized."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("./subdir/../test.py", "agent1", None, test_dir)
        
        # Should be normalized in registry
        registry = wip._load_registry(test_dir)
        assert "test.py" in registry["claims"]

    def test_registry_persistence(self, wip_env):
        """Test that claims persist across operations."""
        test_dir = str(wip_env["test_dir"])
        
        wip.claim_file("test.py", "agent1", "TASK-001", test_dir)
        
        # Load fresh registry
        registry = wip._load_registry(test_dir)
        
        assert "test.py" in registry["claims"]
        assert registry["claims"]["test.py"]["claimed_by"] == "agent1"

    def test_ensure_wip_dir(self, wip_env):
        """Test that .avcpm directory is created."""
        test_dir = str(wip_env["test_dir"])
        
        wip._ensure_wip_dir(test_dir)
        assert os.path.exists(os.path.join(test_dir, ".avcpm"))


# ----- Test CLI -----

class TestCLI:
    """Test CLI interface functionality."""

    def test_cli_claim_and_release(self, tmp_path):
        """Test basic CLI claim and release workflow."""
        import subprocess
        
        test_dir = tmp_path / "test_project"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text("# test")
        
        # Claim
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", str(test_dir),
             "--agent", "agent1", "claim", "test.py", "--task", "TASK-001"],
            capture_output=True, text=True, cwd=str(Path(__file__).parent)
        )
        assert result.returncode == 0
        assert "Claimed" in result.stdout
        
        # List
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", str(test_dir),
             "--agent", "agent1", "list"],
            capture_output=True, text=True, cwd=str(Path(__file__).parent)
        )
        assert result.returncode == 0
        assert "test.py" in result.stdout
        
        # Release
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", str(test_dir),
             "--agent", "agent1", "release", "test.py"],
            capture_output=True, text=True, cwd=str(Path(__file__).parent)
        )
        assert result.returncode == 0
        assert "Released" in result.stdout

    def test_cli_check_conflicts(self, tmp_path):
        """Test CLI conflict checking."""
        import subprocess
        
        test_dir = tmp_path / "test_project"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text("# test")
        
        # First agent claims
        wip.claim_file("test.py", "agent2", "TASK-002", str(test_dir))
        
        # Check as different agent - should find conflict
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", str(test_dir),
             "--agent", "agent1", "check", "test.py"],
            capture_output=True, text=True, cwd=str(Path(__file__).parent)
        )
        assert result.returncode == 1  # Exit code 1 for conflicts
        assert "Conflicts found" in result.stdout

    def test_cli_list_mine(self, tmp_path):
        """Test CLI list --mine option."""
        import subprocess
        
        test_dir = tmp_path / "test_project"
        test_dir.mkdir()
        
        wip.claim_file("test.py", "agent1", "TASK-001", str(test_dir))
        wip.claim_file("other.py", "agent2", "TASK-002", str(test_dir))
        
        result = subprocess.run(
            [sys.executable, "-m", "avcpm_wip", "--base-dir", str(test_dir),
             "--agent", "agent1", "list", "--mine"],
            capture_output=True, text=True, cwd=str(Path(__file__).parent)
        )
        assert result.returncode == 0
        assert "test.py" in result.stdout
        assert "other.py" not in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])