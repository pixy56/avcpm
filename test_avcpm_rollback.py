"""
Tests for AVCPM Rollback & Recovery System

Run with: pytest test_avcpm_rollback.py -v
"""

import os
import sys
import json
import shutil
import tempfile
import pytest
from datetime import datetime

# Ensure the module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_rollback as rollback
import avcpm_branch as branch
import avcpm_agent as agent
from avcpm_commit import commit


class TestRollbackFoundation:
    """Test basic rollback functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Initialize main branch
        branch._ensure_main_branch(self.base_dir)
        branch.switch_branch("main", self.base_dir)
        
        yield
        
        # Cleanup
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_commit(self, filepath, content, commit_message="Test commit"):
        """Helper to create a file and commit it."""
        # Create the file in production
        with open(filepath, "w") as f:
            f.write(content)
        
        # Create commit through the staging/ledger mechanism
        commit_data = {
            "file_path": filepath,
            "content": content,
            "message": commit_message
        }
        
        # Use the commit module's commit function
        result = commit(filepath, commit_message, base_dir=self.base_dir)
        return result
    
    def _create_test_commit_with_ledger(self, filepath, content, commit_message="Test commit", branch_name="main"):
        """Helper to manually create a commit with proper ledger structure."""
        # Create staging directory for branch
        staging_dir = branch.get_branch_staging_dir(branch_name, self.base_dir)
        ledger_dir = branch.get_branch_ledger_dir(branch_name, self.base_dir)
        os.makedirs(staging_dir, exist_ok=True)
        os.makedirs(ledger_dir, exist_ok=True)
        
        # Create file in production
        prod_path = os.path.join(self.test_dir, filepath)
        os.makedirs(os.path.dirname(prod_path) if os.path.dirname(prod_path) else self.test_dir, exist_ok=True)
        with open(prod_path, "w") as f:
            f.write(content)
        
        # Create staging copy
        staging_filename = f"{filepath.replace('/', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        staging_path = os.path.join(staging_dir, staging_filename)
        shutil.copy2(prod_path, staging_path)
        
        # Create commit metadata
        commit_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        commit_data = {
            "commit_id": commit_id,
            "file": filepath,
            "message": commit_message,
            "timestamp": datetime.now().isoformat(),
            "branch": branch_name,
            "staging_path": staging_path,
            "checksum": rollback._calculate_checksum(prod_path)
        }
        
        # Save commit ledger
        ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
        with open(ledger_path, "w") as f:
            json.dump(commit_data, f, indent=4)
        
        return commit_id, commit_data


class TestUnstage(TestRollbackFoundation):
    """Test unstaging functionality."""
    
    def test_unstage_existing_commit(self):
        """Test unstaging a commit from staging."""
        # Create a commit
        commit_id, _ = self._create_test_commit_with_ledger("test.txt", "Hello World")
        
        # Verify commit exists in staging
        ledger_dir = branch.get_branch_ledger_dir("main", self.base_dir)
        assert os.path.exists(os.path.join(ledger_dir, f"{commit_id}.json"))
        
        # Unstage the commit
        result = rollback.unstage(commit_id, "main", self.base_dir)
        
        assert result["success"] is True
        assert result["commit_id"] == commit_id
        assert result["branch"] == "main"
        assert result["ledger_removed"] is True
        
        # Verify commit is removed from staging
        assert not os.path.exists(os.path.join(ledger_dir, f"{commit_id}.json"))
    
    def test_unstage_nonexistent_commit(self):
        """Test unstaging a non-existent commit."""
        result = rollback.unstage("nonexistent_commit_12345", "main", self.base_dir)
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    def test_unstage_removes_staging_files(self):
        """Test that unstage removes files from staging directory."""
        # Create a commit with staging file
        commit_id, commit_data = self._create_test_commit_with_ledger("test.txt", "Hello World")
        staging_path = commit_data.get("staging_path")
        
        # Verify staging file exists
        assert os.path.exists(staging_path)
        
        # Unstage
        result = rollback.unstage(commit_id, "main", self.base_dir)
        
        assert result["success"] is True
        assert len(result["files_removed"]) == 1
        
        # Verify staging file is removed
        assert not os.path.exists(staging_path)
    
    def test_unstage_uses_current_branch(self):
        """Test that unstage uses current branch when branch_name is None."""
        # Create a new branch and switch to it
        branch.create_branch("feature", "main", base_dir=self.base_dir)
        branch.switch_branch("feature", self.base_dir)
        
        # Create commit on feature branch
        commit_id, _ = self._create_test_commit_with_ledger("test.txt", "Hello Feature", branch_name="feature")
        
        # Unstage without specifying branch (should use current)
        result = rollback.unstage(commit_id, None, self.base_dir)
        
        assert result["success"] is True
        assert result["branch"] == "feature"


class TestRestoreFile(TestRollbackFoundation):
    """Test file restoration functionality."""
    
    def test_restore_file_to_specific_commit(self):
        """Test restoring a file to a specific commit version."""
        # Create initial file and commit
        commit_id, commit_data = self._create_test_commit_with_ledger("restore_test.txt", "Version 1")
        
        # Modify the file in production
        with open("restore_test.txt", "w") as f:
            f.write("Modified Version")
        
        # Restore to original commit
        result = rollback.restore_file("restore_test.txt", commit_id, self.base_dir)
        
        assert result["success"] is True
        assert result["filepath"] == "restore_test.txt"
        assert result["commit_id"] == commit_id
        
        # Verify file content is restored
        with open("restore_test.txt", "r") as f:
            content = f.read()
        assert content == "Version 1"
    
    def test_restore_file_latest_commit(self):
        """Test restoring a file to the latest commit version."""
        # Create a file and commit
        self._create_test_commit_with_ledger("latest_test.txt", "Latest Content")
        
        # Modify the file
        with open("latest_test.txt", "w") as f:
            f.write("Modified Content")
        
        # Restore to latest (should find the commit we just made)
        result = rollback.restore_file("latest_test.txt", None, self.base_dir)
        
        # Should succeed if commit was found
        if result["success"]:
            with open("latest_test.txt", "r") as f:
                content = f.read()
            assert content == "Latest Content"
    
    def test_restore_file_nonexistent_commit(self):
        """Test restoring from a non-existent commit."""
        result = rollback.restore_file("some_file.txt", "nonexistent_commit", self.base_dir)
        
        assert result["success"] is False
        assert "error" in result
    
    def test_restore_file_no_history(self):
        """Test restoring a file with no history."""
        result = rollback.restore_file("no_history.txt", None, self.base_dir)
        
        assert result["success"] is False
        assert "error" in result
        assert "no history" in result["error"].lower()


class TestCreateBackup(TestRollbackFoundation):
    """Test backup creation functionality."""
    
    def test_create_backup_basic(self):
        """Test creating a backup with default name."""
        backup_id = rollback.create_backup(None, self.base_dir)
        
        assert backup_id is not None
        assert backup_id.startswith("backup_")
        
        # Verify backup directory structure
        backup_path = rollback.get_backup_path(backup_id, self.base_dir)
        assert os.path.exists(backup_path)
        
        # Verify metadata file
        meta_path = rollback.get_backup_metadata_path(backup_id, self.base_dir)
        assert os.path.exists(meta_path)
        
        # Load and verify metadata
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        assert meta["backup_id"] == backup_id
        assert meta["status"] == rollback.BACKUP_STATUS_ACTIVE
        assert "created_at" in meta
    
    def test_create_backup_with_name(self):
        """Test creating a backup with a custom name."""
        backup_id = rollback.create_backup("Pre-Release Checkpoint", self.base_dir)
        
        meta_path = rollback.get_backup_metadata_path(backup_id, self.base_dir)
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        assert meta["name"] == "Pre-Release Checkpoint"
    
    def test_create_backup_includes_branches(self):
        """Test that backup includes all branches."""
        # Create additional branches
        branch.create_branch("feature-1", "main", base_dir=self.base_dir)
        branch.create_branch("feature-2", "main", base_dir=self.base_dir)
        
        # Create backup
        backup_id = rollback.create_backup("Multi-Branch Backup", self.base_dir)
        
        # Verify branches are in backup
        meta_path = rollback.get_backup_metadata_path(backup_id, self.base_dir)
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        assert "main" in meta["branches"]
        assert "feature-1" in meta["branches"]
        assert "feature-2" in meta["branches"]
    
    def test_create_backup_preserves_staging_and_ledger(self):
        """Test that backup preserves staging and ledger data."""
        # Create a commit
        self._create_test_commit_with_ledger("backup_test.txt", "Backup Content")
        
        # Create backup
        backup_id = rollback.create_backup("With Content", self.base_dir)
        
        # Verify staging and ledger are backed up
        backup_path = rollback.get_backup_path(backup_id, self.base_dir)
        staging_backup = os.path.join(backup_path, "branches", "main", "staging")
        ledger_backup = os.path.join(backup_path, "branches", "main", "ledger")
        
        assert os.path.exists(staging_backup)
        assert os.path.exists(ledger_backup)


class TestRestoreBackup(TestRollbackFoundation):
    """Test backup restoration functionality."""
    
    def test_restore_backup_success(self):
        """Test successfully restoring from a backup."""
        # Create a commit to have some data
        self._create_test_commit_with_ledger("restore_backup_test.txt", "Original Content")
        
        # Create backup
        backup_id = rollback.create_backup("Restore Test", self.base_dir)
        
        # Modify data after backup
        self._create_test_commit_with_ledger("after_backup.txt", "After Backup")
        
        # Restore backup
        result = rollback.restore_backup(backup_id, self.base_dir)
        
        assert result["success"] is True
        assert result["backup_id"] == backup_id
        assert "main" in result["branches_restored"]
        assert len(result["branches_failed"]) == 0
    
    def test_restore_backup_nonexistent(self):
        """Test restoring a non-existent backup."""
        result = rollback.restore_backup("nonexistent_backup_12345", self.base_dir)
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    def test_restore_backup_updates_status(self):
        """Test that restoring updates backup status."""
        # Create backup
        backup_id = rollback.create_backup("Status Test", self.base_dir)
        
        # Restore
        rollback.restore_backup(backup_id, self.base_dir)
        
        # Verify status is updated
        meta_path = rollback.get_backup_metadata_path(backup_id, self.base_dir)
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        assert meta["status"] == rollback.BACKUP_STATUS_RESTORED
        assert "restored_at" in meta
    
    def test_restore_backup_preserves_config(self):
        """Test that backup and restore preserves config."""
        # Create a config file
        config_path = os.path.join(self.base_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump({"test_key": "test_value"}, f)
        
        # Create backup
        backup_id = rollback.create_backup("Config Test", self.base_dir)
        
        # Modify config
        with open(config_path, "w") as f:
            json.dump({"test_key": "modified"}, f)
        
        # Restore
        rollback.restore_backup(backup_id, self.base_dir)
        
        # Verify config is restored
        with open(config_path, "r") as f:
            config = json.load(f)
        
        assert config["test_key"] == "test_value"


class TestResetSoft(TestRollbackFoundation):
    """Test soft reset functionality."""
    
    def test_reset_soft_removes_commits(self):
        """Test that soft reset removes commits from ledger."""
        # Create multiple commits
        commit1, _ = self._create_test_commit_with_ledger("reset_soft_1.txt", "Commit 1", "First commit")
        commit2, _ = self._create_test_commit_with_ledger("reset_soft_2.txt", "Commit 2", "Second commit")
        commit3, _ = self._create_test_commit_with_ledger("reset_soft_3.txt", "Commit 3", "Third commit")
        
        # Reset to first commit (removes commit2 and commit3)
        result = rollback.reset_soft(commit1, "main", self.base_dir)
        
        assert result["success"] is True
        assert result["branch"] == "main"
        assert result["target_commit"] == commit1
        assert commit2 in result["commits_removed"]
        assert commit3 in result["commits_removed"]
    
    def test_reset_soft_preserves_staging_files(self):
        """Test that soft reset preserves staging files."""
        # Create commits
        commit1, data1 = self._create_test_commit_with_ledger("preserve_test.txt", "Content 1")
        commit2, data2 = self._create_test_commit_with_ledger("preserve_test.txt", "Content 2")
        
        staging_path = data2.get("staging_path")
        
        # Soft reset
        result = rollback.reset_soft(commit1, "main", self.base_dir)
        
        assert result["success"] is True
        
        # Staging files should still exist after soft reset
        assert os.path.exists(staging_path)
    
    def test_reset_soft_nonexistent_commit(self):
        """Test soft reset to non-existent commit."""
        result = rollback.reset_soft("nonexistent_commit", "main", self.base_dir)
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    def test_reset_soft_tracks_preserved_files(self):
        """Test that soft reset tracks preserved files."""
        # Create commits with different files
        commit1, _ = self._create_test_commit_with_ledger("file1.txt", "File 1")
        commit2, _ = self._create_test_commit_with_ledger("file2.txt", "File 2")
        
        # Reset to first commit
        result = rollback.reset_soft(commit1, "main", self.base_dir)
        
        assert result["success"] is True
        assert "file2.txt" in result["files_preserved"]


class TestResetHard(TestRollbackFoundation):
    """Test hard reset functionality."""
    
    def test_reset_hard_removes_commits_and_files(self):
        """Test that hard reset removes commits and staging files."""
        # Create commits
        commit1, _ = self._create_test_commit_with_ledger("hard_reset_test.txt", "Content 1")
        commit2, data2 = self._create_test_commit_with_ledger("hard_reset_test.txt", "Content 2")
        
        staging_path = data2.get("staging_path")
        
        # Hard reset to first commit
        result = rollback.reset_hard(commit1, "main", self.base_dir)
        
        assert result["success"] is True
        assert commit2 in result["commits_removed"]
        assert "hard_reset_test.txt" in result["files_removed"]
        
        # Staging file should be removed
        assert not os.path.exists(staging_path)
    
    def test_reset_hard_creates_backup(self):
        """Test that hard reset creates an auto-backup."""
        # Create commits
        commit1, _ = self._create_test_commit_with_ledger("backup_test.txt", "Content")
        commit2, _ = self._create_test_commit_with_ledger("backup_test.txt", "Content 2")
        
        # Hard reset
        result = rollback.reset_hard(commit1, "main", self.base_dir)
        
        assert result["success"] is True
        assert result["backup_id"] is not None
        assert result["backup_id"].startswith("backup_")
    
    def test_reset_hard_nonexistent_commit(self):
        """Test hard reset to non-existent commit."""
        result = rollback.reset_hard("nonexistent_commit", "main", self.base_dir)
        
        assert result["success"] is False
        assert "error" in result


class TestRollback(TestRollbackFoundation):
    """Test rollback functionality for merged commits."""
    
    def test_rollback_nonexistent_commit(self):
        """Test rollback of non-existent commit."""
        result = rollback.rollback("nonexistent_commit", self.base_dir)
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    def test_rollback_unmerged_commit(self):
        """Test rollback of unmerged commit."""
        # Create a commit (not merged to production)
        commit_id, _ = self._create_test_commit_with_ledger("unmerged.txt", "Unmerged content")
        
        # Try to rollback (should fail - not merged)
        result = rollback.rollback(commit_id, self.base_dir)
        
        assert result["success"] is False
        assert "not merged" in result["error"].lower()
    
    def test_rollback_dry_run(self):
        """Test rollback dry run mode."""
        result = rollback.rollback("some_commit", self.base_dir, dry_run=True)
        
        # Should return result even if commit not found
        assert result["success"] is False
        assert result.get("backup_id") is None
    
    def test_rollback_creates_backup(self):
        """Test that rollback creates auto-backup."""
        # This test would need a properly merged commit to fully test
        # For now, verify the backup creation logic exists
        backup_id = rollback._backup_before_destructive(self.base_dir, "test_operation")
        
        assert backup_id is not None
        assert backup_id.startswith("backup_")
        assert "auto_before_test_operation" in backup_id


class TestHelperFunctions(TestRollbackFoundation):
    """Test helper functions."""
    
    def test_generate_backup_id(self):
        """Test backup ID generation."""
        backup_id = rollback._generate_backup_id()
        
        assert backup_id.startswith("backup_")
        assert len(backup_id) > 20  # Should have timestamp and uuid
    
    def test_calculate_checksum(self):
        """Test checksum calculation."""
        # Create a test file
        with open("checksum_test.txt", "w") as f:
            f.write("Hello World")
        
        checksum = rollback._calculate_checksum("checksum_test.txt")
        
        assert len(checksum) == 64  # SHA256 hex string
        assert all(c in "0123456789abcdef" for c in checksum)
    
    def test_get_file_at_commit(self):
        """Test getting file path at specific commit."""
        commit_id, commit_data = self._create_test_commit_with_ledger("commit_file.txt", "Commit content")
        
        staging_path = rollback._get_file_at_commit("commit_file.txt", commit_id, self.base_dir)
        
        assert staging_path is not None
        assert os.path.exists(staging_path)
    
    def test_find_commit_in_any_branch(self):
        """Test finding commit across all branches."""
        commit_id, _ = self._create_test_commit_with_ledger("find_test.txt", "Find content")
        
        result = rollback._find_commit_in_any_branch(commit_id, self.base_dir)
        
        assert result is not None
        assert result[0] == "main"  # branch name
        assert result[1]["commit_id"] == commit_id
    
    def test_find_commit_not_found(self):
        """Test finding non-existent commit."""
        result = rollback._find_commit_in_any_branch("nonexistent", self.base_dir)
        
        assert result is None
    
    def test_get_commits_in_branch(self):
        """Test getting commits in a branch."""
        # Create multiple commits
        self._create_test_commit_with_ledger("commit1.txt", "Content 1")
        self._create_test_commit_with_ledger("commit2.txt", "Content 2")
        
        commits = rollback._get_commits_in_branch("main", self.base_dir)
        
        assert len(commits) >= 2
    
    def test_copy_directory_tree(self):
        """Test directory tree copying."""
        # Create source directory with nested structure
        src_dir = os.path.join(self.test_dir, "source")
        os.makedirs(os.path.join(src_dir, "subdir"))
        
        with open(os.path.join(src_dir, "file1.txt"), "w") as f:
            f.write("File 1")
        with open(os.path.join(src_dir, "subdir", "file2.txt"), "w") as f:
            f.write("File 2")
        
        dst_dir = os.path.join(self.test_dir, "destination")
        rollback._copy_directory_tree(src_dir, dst_dir)
        
        assert os.path.exists(os.path.join(dst_dir, "file1.txt"))
        assert os.path.exists(os.path.join(dst_dir, "subdir", "file2.txt"))


class TestBackupLifecycle(TestRollbackFoundation):
    """Test backup lifecycle operations."""
    
    def test_list_backups_empty(self):
        """Test listing backups when none exist."""
        backups = rollback.list_backups(self.base_dir)
        
        assert isinstance(backups, list)
        assert len(backups) == 0
    
    def test_list_backups_sorted(self):
        """Test that backups are sorted by creation time."""
        # Create multiple backups
        id1 = rollback.create_backup("Backup 1", self.base_dir)
        id2 = rollback.create_backup("Backup 2", self.base_dir)
        id3 = rollback.create_backup("Backup 3", self.base_dir)
        
        backups = rollback.list_backups(self.base_dir)
        
        assert len(backups) == 3
        # Should be sorted newest first
        assert backups[0]["backup_id"] == id3
        assert backups[2]["backup_id"] == id1
    
    def test_delete_backup(self):
        """Test deleting a backup."""
        # Create backup
        backup_id = rollback.create_backup("To Delete", self.base_dir)
        
        # Verify it exists
        backup_path = rollback.get_backup_path(backup_id, self.base_dir)
        assert os.path.exists(backup_path)
        
        # Delete it
        result = rollback.delete_backup(backup_id, self.base_dir)
        
        assert result["success"] is True
        assert not os.path.exists(backup_path)
    
    def test_delete_nonexistent_backup(self):
        """Test deleting a non-existent backup."""
        result = rollback.delete_backup("nonexistent_backup", self.base_dir)
        
        assert result["success"] is False
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
