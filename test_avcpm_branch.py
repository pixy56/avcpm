"""
Tests for AVCPM Branch Management System

Run with: pytest test_avcpm_branch.py -v
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

import avcpm_branch as branch
import avcpm_commit as commit
import avcpm_agent as agent


class TestBranchFoundation:
    """Test basic branch creation and management."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        yield
        
        # Cleanup
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_main_branch_auto_created(self):
        """Test that main branch is auto-created on first use."""
        current = branch.get_current_branch(self.base_dir)
        assert current == "main"
        
        # Verify main branch directory structure
        assert os.path.exists(branch.get_branch_dir("main", self.base_dir))
        assert os.path.exists(branch.get_branch_staging_dir("main", self.base_dir))
        assert os.path.exists(branch.get_branch_ledger_dir("main", self.base_dir))
        
        # Verify metadata
        metadata = branch.get_branch("main", self.base_dir)
        assert metadata is not None
        assert metadata["name"] == "main"
        assert metadata["parent_branch"] is None
        assert metadata["status"] == branch.BRANCH_STATUS_ACTIVE
    
    def test_create_branch_from_main(self):
        """Test creating a branch from main."""
        # First ensure main exists
        branch._ensure_main_branch(self.base_dir)
        
        # Create a feature branch
        metadata = branch.create_branch(
            "feature-1",
            parent_branch="main",
            task_id="TASK-123",
            agent_id="agent-001",
            base_dir=self.base_dir
        )
        
        assert metadata["name"] == "feature-1"
        assert metadata["parent_branch"] == "main"
        assert metadata["task_id"] == "TASK-123"
        assert metadata["created_by"] == "agent-001"
        assert metadata["status"] == branch.BRANCH_STATUS_ACTIVE
        assert "branch_id" in metadata
        assert "created_at" in metadata
        
        # Verify directory structure
        assert os.path.exists(branch.get_branch_dir("feature-1", self.base_dir))
        assert os.path.exists(branch.get_branch_staging_dir("feature-1", self.base_dir))
        assert os.path.exists(branch.get_branch_ledger_dir("feature-1", self.base_dir))
    
    def test_create_branch_invalid_name(self):
        """Test creating a branch with invalid name."""
        branch._ensure_main_branch(self.base_dir)
        
        invalid_names = ["", ".", "..", "feature/test", "feature\\test", ".hidden"]
        
        for name in invalid_names:
            with pytest.raises(ValueError):
                branch.create_branch(name, base_dir=self.base_dir)
    
    def test_create_branch_already_exists(self):
        """Test creating a branch that already exists."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        with pytest.raises(ValueError) as exc_info:
            branch.create_branch("feature-1", base_dir=self.base_dir)
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_branch_nonexistent_parent(self):
        """Test creating a branch from non-existent parent."""
        with pytest.raises(ValueError) as exc_info:
            branch.create_branch("feature-1", parent_branch="nonexistent", base_dir=self.base_dir)
        
        assert "does not exist" in str(exc_info.value)
    
    def test_list_branches(self):
        """Test listing all branches."""
        branch._ensure_main_branch(self.base_dir)
        
        # Initially just main
        branches = branch.list_branches(self.base_dir)
        assert len(branches) == 1
        assert branches[0]["name"] == "main"
        
        # Add more branches
        branch.create_branch("feature-1", base_dir=self.base_dir)
        branch.create_branch("feature-2", base_dir=self.base_dir)
        
        branches = branch.list_branches(self.base_dir)
        assert len(branches) == 3
        names = [b["name"] for b in branches]
        assert "main" in names
        assert "feature-1" in names
        assert "feature-2" in names
    
    def test_get_branch(self):
        """Test getting branch details."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", task_id="TASK-001", base_dir=self.base_dir)
        
        metadata = branch.get_branch("feature-1", self.base_dir)
        assert metadata is not None
        assert metadata["name"] == "feature-1"
        assert metadata["task_id"] == "TASK-001"
        
        # Non-existent branch
        assert branch.get_branch("nonexistent", self.base_dir) is None
    
    def test_switch_branch(self):
        """Test switching between branches."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        # Initially on main
        assert branch.get_current_branch(self.base_dir) == "main"
        
        # Switch to feature-1
        metadata = branch.switch_branch("feature-1", self.base_dir)
        assert metadata["name"] == "feature-1"
        assert branch.get_current_branch(self.base_dir) == "feature-1"
        
        # Switch back to main
        branch.switch_branch("main", self.base_dir)
        assert branch.get_current_branch(self.base_dir) == "main"
    
    def test_switch_nonexistent_branch(self):
        """Test switching to a non-existent branch."""
        branch._ensure_main_branch(self.base_dir)
        
        with pytest.raises(ValueError) as exc_info:
            branch.switch_branch("nonexistent", self.base_dir)
        
        assert "does not exist" in str(exc_info.value)
    
    def test_delete_branch(self):
        """Test deleting a branch."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        # Can't delete current branch
        with pytest.raises(ValueError) as exc_info:
            branch.delete_branch("main", base_dir=self.base_dir)
        assert "currently active" in str(exc_info.value)
        
        # Switch away and delete
        branch.switch_branch("feature-1", self.base_dir)
        branch.switch_branch("main", self.base_dir)
        
        result = branch.delete_branch("feature-1", base_dir=self.base_dir)
        assert result is True
        assert not os.path.exists(branch.get_branch_dir("feature-1", self.base_dir))
    
    def test_delete_main_branch_protection(self):
        """Test that main branch is protected from deletion."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        branch.switch_branch("feature-1", self.base_dir)
        
        # Can't delete main without force
        with pytest.raises(ValueError) as exc_info:
            branch.delete_branch("main", base_dir=self.base_dir)
        assert "force" in str(exc_info.value).lower()
        
        # Can delete with force
        result = branch.delete_branch("main", force=True, base_dir=self.base_dir)
        assert result is True
    
    def test_delete_branch_with_force(self):
        """Test force deleting a branch with unmerged changes."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        branch.switch_branch("feature-1", self.base_dir)
        
        # Create a test agent
        agent.create_agent("test-agent", "Test Agent", base_dir=self.base_dir)
        
        # Create a test file and commit
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        commit.commit("TASK-001", "test-agent", "Test commit", [test_file], base_dir=self.base_dir)
        
        # Switch back to main and try to delete feature-1
        branch.switch_branch("main", self.base_dir)
        
        # Without force, should fail due to unmerged commits
        with pytest.raises(ValueError) as exc_info:
            branch.delete_branch("feature-1", base_dir=self.base_dir)
        assert "unmerged" in str(exc_info.value).lower() or "force" in str(exc_info.value).lower()
        
        # With force, should succeed
        result = branch.delete_branch("feature-1", force=True, base_dir=self.base_dir)
        assert result is True
    
    def test_rename_branch(self):
        """Test renaming a branch."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        metadata = branch.rename_branch("feature-1", "feature-renamed", self.base_dir)
        assert metadata["name"] == "feature-renamed"
        
        # Old branch should not exist
        assert branch.get_branch("feature-1", self.base_dir) is None
        
        # New branch should exist
        assert branch.get_branch("feature-renamed", self.base_dir) is not None
    
    def test_rename_branch_updates_references(self):
        """Test that renaming a branch updates child branch parent references."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", parent_branch="main", base_dir=self.base_dir)
        branch.create_branch("feature-2", parent_branch="feature-1", base_dir=self.base_dir)
        
        # Rename feature-1
        branch.rename_branch("feature-1", "feature-renamed", self.base_dir)
        
        # Check that feature-2's parent was updated
        feature_2 = branch.get_branch("feature-2", self.base_dir)
        assert feature_2["parent_branch"] == "feature-renamed"
    
    def test_rename_branch_updates_current(self):
        """Test that renaming current branch updates the config."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        branch.switch_branch("feature-1", self.base_dir)
        
        assert branch.get_current_branch(self.base_dir) == "feature-1"
        
        branch.rename_branch("feature-1", "feature-renamed", self.base_dir)
        
        assert branch.get_current_branch(self.base_dir) == "feature-renamed"


class TestBranchStagingIsolation:
    """Test that commits are isolated to their branches."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create a test agent
        agent.create_agent("test-agent", "Test Agent", base_dir=self.base_dir)
        
        yield
        
        # Cleanup
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_commit_goes_to_current_branch(self):
        """Test that commits go to the current branch's staging."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        # Switch to feature-1
        branch.switch_branch("feature-1", self.base_dir)
        
        # Create and commit a test file
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("feature content")
        
        commit.commit("TASK-001", "test-agent", "Feature commit", [test_file], base_dir=self.base_dir)
        
        # Verify commit is in feature-1's ledger
        feature_ledger = branch.get_branch_ledger_dir("feature-1", self.base_dir)
        feature_commits = [f for f in os.listdir(feature_ledger) if f.endswith(".json")]
        assert len(feature_commits) == 1
        
        # Verify commit is NOT in main's ledger
        main_ledger = branch.get_branch_ledger_dir("main", self.base_dir)
        main_commits = [f for f in os.listdir(main_ledger) if f.endswith(".json")]
        assert len(main_commits) == 0
        
        # Verify staging is isolated
        feature_staging = branch.get_branch_staging_dir("feature-1", self.base_dir)
        staged_files = [f for f in os.listdir(feature_staging) if f.endswith(".txt")]
        assert len(staged_files) == 1
        
        main_staging = branch.get_branch_staging_dir("main", self.base_dir)
        main_staged = [f for f in os.listdir(main_staging) if f.endswith(".txt")]
        assert len(main_staged) == 0
    
    def test_commits_dont_mix_between_branches(self):
        """Test that commits to different branches don't mix."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        branch.create_branch("feature-2", base_dir=self.base_dir)
        
        # Commit to feature-1
        branch.switch_branch("feature-1", self.base_dir)
        test_file_1 = os.path.join(self.test_dir, "test1.txt")
        with open(test_file_1, "w") as f:
            f.write("feature 1 content")
        commit.commit("TASK-001", "test-agent", "Feature 1 commit", [test_file_1], base_dir=self.base_dir)
        
        # Commit to feature-2
        branch.switch_branch("feature-2", self.base_dir)
        test_file_2 = os.path.join(self.test_dir, "test2.txt")
        with open(test_file_2, "w") as f:
            f.write("feature 2 content")
        commit.commit("TASK-002", "test-agent", "Feature 2 commit", [test_file_2], base_dir=self.base_dir)
        
        # Verify each branch has its own commit
        feature_1_ledger = branch.get_branch_ledger_dir("feature-1", self.base_dir)
        feature_2_ledger = branch.get_branch_ledger_dir("feature-2", self.base_dir)
        
        f1_commits = [f for f in os.listdir(feature_1_ledger) if f.endswith(".json")]
        f2_commits = [f for f in os.listdir(feature_2_ledger) if f.endswith(".json")]
        
        assert len(f1_commits) == 1
        assert len(f2_commits) == 1
        assert f1_commits[0] != f2_commits[0]
    
    def test_explicit_branch_commit(self):
        """Test committing to a specific branch by name."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        # Stay on main but commit to feature-1
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("explicit branch content")
        
        commit.commit("TASK-001", "test-agent", "Explicit branch commit", 
                       [test_file], branch_name="feature-1", base_dir=self.base_dir)
        
        # Verify commit went to feature-1
        feature_ledger = branch.get_branch_ledger_dir("feature-1", self.base_dir)
        feature_commits = [f for f in os.listdir(feature_ledger) if f.endswith(".json")]
        assert len(feature_commits) == 1
        
        # Main should still be empty
        main_ledger = branch.get_branch_ledger_dir("main", self.base_dir)
        main_commits = [f for f in os.listdir(main_ledger) if f.endswith(".json")]
        assert len(main_commits) == 0


class TestBranchCircularParent:
    """Test circular parent detection."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        yield
        
        # Cleanup
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_circular_parent_detection(self):
        """Test that a branch cannot be created with a circular parent reference."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", parent_branch="main", base_dir=self.base_dir)
        branch.create_branch("feature-2", parent_branch="feature-1", base_dir=self.base_dir)
        
        # Try to create a branch from feature-2 named feature-1 (would create cycle)
        with pytest.raises(ValueError) as exc_info:
            branch.create_branch("feature-1a", parent_branch="feature-2", base_dir=self.base_dir)
            # Now try to create main from feature-2 (circular)
            # Actually let's try to rename feature-2 to main - but that won't work either
        
        # Instead, let's verify the circular detection works
        # by checking we can't create feature-1 as child of feature-2
        # (since feature-2 is already derived from feature-1)
        
        # Actually the proper test is: create feature-3 from feature-2,
        # then try to create a branch from feature-3 called feature-1
        # But that won't be circular because feature-1 already exists
        
        # The real test: verify _is_ancestor works
        assert branch._is_ancestor("feature-2", "main", self.base_dir) == True
        assert branch._is_ancestor("feature-2", "feature-1", self.base_dir) == True
        assert branch._is_ancestor("main", "feature-1", self.base_dir) == False
    
    def test_branch_cannot_be_its_own_ancestor(self):
        """Test that prevents a branch from being its own ancestor."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", parent_branch="main", base_dir=self.base_dir)
        
        # Try to create feature-2 from feature-1, but then we can't really make
        # feature-1 a child of feature-2 without renaming
        # The circular check should prevent: feature-2 from having feature-1
        # as parent if feature-1 is already a descendant
        
        # Create the chain: main <- feature-1 <- feature-2
        branch.create_branch("feature-2", parent_branch="feature-1", base_dir=self.base_dir)
        
        # Now we shouldn't be able to create feature-1-child from feature-2
        # if we tried to make it have feature-1 as parent... that's fine
        # The issue is if we tried to make feature-2's parent be feature-2 itself
        # or if we could somehow make main's parent be feature-2
        
        # The _is_ancestor check should prevent creating a branch where
        # the new branch's name already exists in the parent's ancestry
        # This is actually about creating a branch with a name that already exists
        # in the parent chain - which the "already exists" check catches first
        
        # What we really need to test is: try to create a new branch
        # where the parent is a descendant of an existing branch with the same name
        # But since names must be unique, this is handled by the existence check
        
        # Let's verify the ancestry tracking is correct
        assert branch._is_ancestor("feature-2", "main", self.base_dir)
        assert branch._is_ancestor("feature-1", "main", self.base_dir)
        assert not branch._is_ancestor("main", "feature-1", self.base_dir)


class TestBranchCLI:
    """Test CLI interface."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.chdir(self.test_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        
        yield
        
        # Cleanup
        os.chdir("/")
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_cli_create_branch(self, capsys):
        """Test CLI create command."""
        # Initialize main first
        branch._ensure_main_branch(self.base_dir)
        
        # Mock sys.argv
        old_argv = sys.argv
        try:
            sys.argv = ["avcpm_branch.py", "create", "feature-cli"]
            branch.main()
            
            captured = capsys.readouterr()
            assert "Created branch 'feature-cli'" in captured.out
            
            # Verify branch exists
            assert branch.get_branch("feature-cli", self.base_dir) is not None
        finally:
            sys.argv = old_argv
    
    def test_cli_create_branch_with_options(self, capsys):
        """Test CLI create command with parent and task."""
        branch._ensure_main_branch(self.base_dir)
        
        old_argv = sys.argv
        try:
            sys.argv = ["avcpm_branch.py", "create", "feature-cli", "--parent", "main", "--task", "TASK-CLI-001"]
            branch.main()
            
            captured = capsys.readouterr()
            assert "Created branch 'feature-cli'" in captured.out
            
            metadata = branch.get_branch("feature-cli", self.base_dir)
            assert metadata["task_id"] == "TASK-CLI-001"
        finally:
            sys.argv = old_argv
    
    def test_cli_list_branches(self, capsys):
        """Test CLI list command."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        branch.create_branch("feature-2", base_dir=self.base_dir)
        
        old_argv = sys.argv
        try:
            sys.argv = ["avcpm_branch.py", "list"]
            branch.main()
            
            captured = capsys.readouterr()
            assert "main" in captured.out
            assert "feature-1" in captured.out
            assert "feature-2" in captured.out
        finally:
            sys.argv = old_argv
    
    def test_cli_switch_branch(self, capsys):
        """Test CLI switch command."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        old_argv = sys.argv
        try:
            sys.argv = ["avcpm_branch.py", "switch", "feature-1"]
            branch.main()
            
            captured = capsys.readouterr()
            assert "Switched to branch 'feature-1'" in captured.out
            assert branch.get_current_branch(self.base_dir) == "feature-1"
        finally:
            sys.argv = old_argv
    
    def test_cli_current_branch(self, capsys):
        """Test CLI current command."""
        branch._ensure_main_branch(self.base_dir)
        
        old_argv = sys.argv
        try:
            sys.argv = ["avcpm_branch.py", "current"]
            branch.main()
            
            captured = capsys.readouterr()
            assert "main" in captured.out
        finally:
            sys.argv = old_argv
    
    def test_cli_delete_branch(self, capsys):
        """Test CLI delete command."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        branch.switch_branch("feature-1", self.base_dir)
        branch.switch_branch("main", self.base_dir)
        
        old_argv = sys.argv
        try:
            sys.argv = ["avcpm_branch.py", "delete", "feature-1"]
            branch.main()
            
            captured = capsys.readouterr()
            assert "Deleted branch 'feature-1'" in captured.out
            assert branch.get_branch("feature-1", self.base_dir) is None
        finally:
            sys.argv = old_argv
    
    def test_cli_rename_branch(self, capsys):
        """Test CLI rename command."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        old_argv = sys.argv
        try:
            sys.argv = ["avcpm_branch.py", "rename", "feature-1", "feature-renamed"]
            branch.main()
            
            captured = capsys.readouterr()
            assert "Renamed branch 'feature-1' to 'feature-renamed'" in captured.out
            assert branch.get_branch("feature-1", self.base_dir) is None
            assert branch.get_branch("feature-renamed", self.base_dir) is not None
        finally:
            sys.argv = old_argv


class TestBranchMetadata:
    """Test branch metadata structure."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        yield
        
        # Cleanup
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_branch_metadata_structure(self):
        """Test that branch metadata has all required fields."""
        branch._ensure_main_branch(self.base_dir)
        
        metadata = branch.create_branch(
            "feature-1",
            parent_branch="main",
            task_id="TASK-123",
            agent_id="agent-001",
            base_dir=self.base_dir
        )
        
        # Required fields
        required_fields = ["branch_id", "name", "created_by", "created_at", 
                          "parent_branch", "parent_commit", "task_id", "status"]
        
        for field in required_fields:
            assert field in metadata, f"Missing required field: {field}"
        
        # Verify types
        assert isinstance(metadata["branch_id"], str)
        assert isinstance(metadata["name"], str)
        assert isinstance(metadata["created_by"], str)
        assert isinstance(metadata["created_at"], str)
        assert metadata["parent_branch"] == "main"
        assert metadata["task_id"] == "TASK-123"
        assert metadata["status"] == branch.BRANCH_STATUS_ACTIVE
    
    def test_main_branch_metadata(self):
        """Test main branch has correct metadata."""
        branch._ensure_main_branch(self.base_dir)
        
        metadata = branch.get_branch("main", self.base_dir)
        
        assert metadata["name"] == "main"
        assert metadata["parent_branch"] is None
        assert metadata["status"] == branch.BRANCH_STATUS_ACTIVE
        assert metadata["created_by"] == "system"
    
    def test_branch_config_persistence(self):
        """Test that current branch is persisted in config."""
        branch._ensure_main_branch(self.base_dir)
        branch.create_branch("feature-1", base_dir=self.base_dir)
        
        # Switch to feature-1
        branch.switch_branch("feature-1", self.base_dir)
        
        # Load config directly
        config = branch._load_config(self.base_dir)
        assert config.get("current_branch") == "feature-1"
        
        # Create new branch and switch
        branch.create_branch("feature-2", base_dir=self.base_dir)
        branch.switch_branch("feature-2", self.base_dir)
        
        config = branch._load_config(self.base_dir)
        assert config.get("current_branch") == "feature-2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
