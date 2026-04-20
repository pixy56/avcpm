"""
Tests for AVCPM Conflict Detection & Resolution Module
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from avcpm_conflict import (
    check_file_conflict,
    merge_three_way,
    merge_files,
    detect_conflicts,
    get_conflicts,
    resolve_conflict,
    auto_merge_possible,
    list_modified_files,
    get_conflict_path,
    CONFLICT_STATUS_OPEN,
    CONFLICT_STATUS_RESOLVED,
    CONFLICT_STATUS_ABORTED,
    RESOLUTION_STRATEGIES,
    _find_common_ancestor,
    _calculate_file_hash,
    _generate_conflict_id,
    DEFAULT_BASE_DIR
)

from avcpm_branch import (
    create_branch,
    switch_branch,
    get_current_branch,
    delete_branch,
    _ensure_main_branch
)

from avcpm_commit import commit

from avcpm_agent import create_agent


class TestConflictDetection(unittest.TestCase):
    """Test conflict detection functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="avcpm_conflict_test_")
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize main branch
        create_branch("main", base_dir=self.base_dir)
        switch_branch("main", base_dir=self.base_dir)
        
        # Create test agent
        create_agent("test_agent", "Test Agent", base_dir=self.base_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_check_file_conflict_no_conflict(self):
        """Test file conflict check - no conflict."""
        # Create identical files
        with open("file_a.txt", "w") as f:
            f.write("Hello World")
        
        result = check_file_conflict("file_a.txt", "file_a.txt", "file_a.txt")
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["conflict_type"], "none")
    
    def test_check_file_conflict_content_conflict(self):
        """Test file conflict check - content conflict."""
        # Create base file
        with open("base.txt", "w") as f:
            f.write("Hello World")
        
        # Modified differently in each branch
        with open("a.txt", "w") as f:
            f.write("Hello World Modified A")
        
        with open("b.txt", "w") as f:
            f.write("Hello World Modified B")
        
        result = check_file_conflict("a.txt", "b.txt", "base.txt")
        self.assertTrue(result["has_conflict"])
        self.assertEqual(result["conflict_type"], "content")
    
    def test_check_file_conflict_delete_modify(self):
        """Test file conflict check - delete/modify conflict."""
        with open("base.txt", "w") as f:
            f.write("Hello World")
        
        with open("modified.txt", "w") as f:
            f.write("Hello World Modified")
        
        # Branch A deleted, Branch B modified
        result = check_file_conflict(None, "modified.txt", "base.txt")
        self.assertTrue(result["has_conflict"])
        self.assertEqual(result["conflict_type"], "delete_modify")
    
    def test_check_file_conflict_add_add_same(self):
        """Test file conflict check - add/add same content."""
        with open("a.txt", "w") as f:
            f.write("New File Content")
        
        with open("b.txt", "w") as f:
            f.write("New File Content")
        
        # Both added same content
        result = check_file_conflict("a.txt", "b.txt", None)
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["conflict_type"], "none")
    
    def test_check_file_conflict_add_add_different(self):
        """Test file conflict check - add/add different content."""
        with open("a.txt", "w") as f:
            f.write("Content A")
        
        with open("b.txt", "w") as f:
            f.write("Content B")
        
        # Both added different content
        result = check_file_conflict("a.txt", "b.txt", None)
        self.assertTrue(result["has_conflict"])
        self.assertEqual(result["conflict_type"], "add_add")
    
    def test_check_file_conflict_only_one_modified(self):
        """Test file conflict check - only one branch modified."""
        with open("base.txt", "w") as f:
            f.write("Hello World")
        
        with open("modified.txt", "w") as f:
            f.write("Hello World Modified")
        
        # Only branch A modified
        result = check_file_conflict("modified.txt", "base.txt", "base.txt")
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["conflict_type"], "none")


class TestThreeWayMerge(unittest.TestCase):
    """Test three-way merge functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="avcpm_merge_test_")
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_merge_identical(self):
        """Test merge with identical content."""
        result = merge_three_way("Hello", "Hello", "Hello")
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["merged_content"], "Hello")
    
    def test_merge_base_equals_a(self):
        """Test merge when base equals A (take B)."""
        result = merge_three_way("Hello", "Hello", "World")
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["merged_content"], "World")
    
    def test_merge_base_equals_b(self):
        """Test merge when base equals B (take A)."""
        result = merge_three_way("Hello", "World", "Hello")
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["merged_content"], "World")
    
    def test_merge_no_conflict_different_lines(self):
        """Test merge with changes on different lines."""
        base = "Line 1\nLine 2\nLine 3\n"
        a = "Line 1 Modified\nLine 2\nLine 3\n"
        b = "Line 1\nLine 2\nLine 3 Modified\n"
        
        result = merge_three_way(base, a, b)
        self.assertFalse(result["has_conflict"])
        self.assertIn("Line 1 Modified", result["merged_content"])
        self.assertIn("Line 3 Modified", result["merged_content"])
    
    def test_merge_conflict_same_line(self):
        """Test merge with conflicting changes on same line."""
        base = "Hello World"
        a = "Hello Modified A"
        b = "Hello Modified B"
        
        result = merge_three_way(base, a, b)
        self.assertTrue(result["has_conflict"])
        self.assertIn("<<<<<<<", result["merged_content"])
        self.assertIn("=======", result["merged_content"])
        self.assertIn(">>>>>>>", result["merged_content"])
    
    def test_merge_with_deletion(self):
        """Test merge with file deletion."""
        base = "Hello World\nLine 2\n"
        a = None  # Deleted
        b = "Hello World\nLine 2 Modified\n"
        
        result = merge_three_way(base, a, b)
        self.assertTrue(result["has_conflict"])
        # Should have conflict markers
        self.assertIn("<<<<<<<", result["merged_content"])
    
    def test_merge_empty_base(self):
        """Test merge with empty base (both added)."""
        a = "Content A"
        b = "Content B"
        
        result = merge_three_way(None, a, b)
        self.assertTrue(result["has_conflict"])
    
    def test_merge_lines_added_end(self):
        """Test merge with lines added at end."""
        base = "Line 1\nLine 2\n"
        a = "Line 1\nLine 2\nLine 3 A\n"
        b = "Line 1\nLine 2\nLine 3 B\n"
        
        result = merge_three_way(base, a, b)
        self.assertTrue(result["has_conflict"])
        # Both tried to add at same position
        self.assertIn("<<<<<<<", result["merged_content"])


class TestMergeFiles(unittest.TestCase):
    """Test file merging operations."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="avcpm_filemerge_test_")
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_merge_files_no_conflict(self):
        """Test merging files with no conflict."""
        # Create files
        with open("base.txt", "w") as f:
            f.write("Hello World")
        
        with open("a.txt", "w") as f:
            f.write("Hello World Modified")
        
        with open("b.txt", "w") as f:
            f.write("Hello World")  # Same as base
        
        result = merge_files("base.txt", "a.txt", "b.txt", "output.txt")
        
        self.assertTrue(result["success"])
        self.assertFalse(result["has_conflict"])
        self.assertTrue(os.path.exists("output.txt"))
        
        with open("output.txt", "r") as f:
            content = f.read()
        self.assertEqual(content, "Hello World Modified")
    
    def test_merge_files_with_conflict(self):
        """Test merging files with conflict."""
        with open("base.txt", "w") as f:
            f.write("Hello World")
        
        with open("a.txt", "w") as f:
            f.write("Hello World A")
        
        with open("b.txt", "w") as f:
            f.write("Hello World B")
        
        result = merge_files("base.txt", "a.txt", "b.txt", "output.txt")
        
        self.assertTrue(result["success"])
        self.assertTrue(result["has_conflict"])
        self.assertTrue(os.path.exists("output.txt"))
        
        with open("output.txt", "r") as f:
            content = f.read()
        self.assertIn("<<<<<<<", content)
        self.assertIn("=======", content)
        self.assertIn(">>>>>>>", content)
    
    def test_merge_files_new_file(self):
        """Test merging new files."""
        with open("a.txt", "w") as f:
            f.write("Content A")
        
        with open("b.txt", "w") as f:
            f.write("Content A")  # Same content
        
        result = merge_files(None, "a.txt", "b.txt", "output.txt")
        
        self.assertTrue(result["success"])
        self.assertFalse(result["has_conflict"])
        
        with open("output.txt", "r") as f:
            content = f.read()
        self.assertEqual(content, "Content A")


class TestBranchConflicts(unittest.TestCase):
    """Test branch-level conflict detection."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="avcpm_branch_conflict_test_")
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize main branch
        create_branch("main", base_dir=self.base_dir)
        switch_branch("main", base_dir=self.base_dir)
        
        # Create test agent
        create_agent("test_agent", "Test Agent", base_dir=self.base_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_list_modified_files_empty(self):
        """Test listing modified files - empty."""
        files = list_modified_files("main", base_dir=self.base_dir)
        self.assertEqual(files, {})
    
    def test_list_modified_files_with_commits(self):
        """Test listing modified files with commits."""
        # Create and commit a file
        with open("test.py", "w") as f:
            f.write("print('hello')")
        
        commit("TASK-001", "test_agent", "Initial commit", ["test.py"], base_dir=self.base_dir)
        
        files = list_modified_files("main", base_dir=self.base_dir)
        self.assertIn("test.py", files)
    
    def test_auto_merge_possible_no_changes(self):
        """Test auto-merge check - no changes."""
        # Create feature branch
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        
        result = auto_merge_possible("main", "feature", base_dir=self.base_dir)
        self.assertTrue(result)
    
    def test_auto_merge_possible_no_conflict(self):
        """Test auto-merge check - no conflict."""
        # Create feature branch
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        switch_branch("feature", base_dir=self.base_dir)
        
        # Add a file in feature
        with open("feature_file.py", "w") as f:
            f.write("print('feature')")
        
        commit("TASK-002", "test_agent", "Feature commit", ["feature_file.py"], base_dir=self.base_dir)
        
        result = auto_merge_possible("main", "feature", base_dir=self.base_dir)
        self.assertTrue(result)
    
    def test_detect_conflicts_with_overlap(self):
        """Test detecting conflicts with overlapping changes."""
        # Create and commit file in main
        with open("shared.py", "w") as f:
            f.write("print('main')")
        
        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=self.base_dir)
        
        # Create feature branch
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        switch_branch("feature", base_dir=self.base_dir)
        
        # Modify file in feature
        with open("shared.py", "w") as f:
            f.write("print('feature')")
        
        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=self.base_dir)
        
        # Switch back to main and modify
        switch_branch("main", base_dir=self.base_dir)
        with open("shared.py", "w") as f:
            f.write("print('main modified')")
        
        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=self.base_dir)
        
        # Detect conflicts
        result = detect_conflicts("main", "feature", base_dir=self.base_dir)
        
        self.assertEqual(result["conflict_count"], 1)
        self.assertFalse(result["auto_mergeable"])
        self.assertEqual(result["conflicts"][0]["file"], "shared.py")
        self.assertEqual(result["conflicts"][0]["conflict_type"], "content")


class TestConflictResolution(unittest.TestCase):
    """Test conflict resolution functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="avcpm_resolution_test_")
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize main branch
        create_branch("main", base_dir=self.base_dir)
        switch_branch("main", base_dir=self.base_dir)
        
        # Create test agent
        create_agent("test_agent", "Test Agent", base_dir=self.base_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_resolution_strategies_defined(self):
        """Test that resolution strategies are defined."""
        self.assertIn("ours", RESOLUTION_STRATEGIES)
        self.assertIn("theirs", RESOLUTION_STRATEGIES)
        self.assertIn("union", RESOLUTION_STRATEGIES)
        self.assertIn("manual", RESOLUTION_STRATEGIES)
    
    def test_get_conflicts_empty(self):
        """Test getting conflicts - empty."""
        conflicts = get_conflicts(status="open", base_dir=self.base_dir)
        self.assertEqual(conflicts, [])
    
    def test_resolve_conflict_not_found(self):
        """Test resolving non-existent conflict."""
        with self.assertRaises(ValueError) as ctx:
            resolve_conflict("non_existent", "ours", base_dir=self.base_dir)
        
        self.assertIn("not found", str(ctx.exception))
    
    def test_resolve_conflict_invalid_strategy(self):
        """Test resolving with invalid strategy."""
        with self.assertRaises(ValueError) as ctx:
            resolve_conflict("test", "invalid_strategy", base_dir=self.base_dir)
        
        self.assertIn("Invalid resolution strategy", str(ctx.exception))
    
    def test_resolve_conflict_ours(self):
        """Test resolving conflict with 'ours' strategy."""
        # Create and commit file in main
        with open("shared.py", "w") as f:
            f.write("print('base')")
        
        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=self.base_dir)
        
        # Create feature branch and modify
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        switch_branch("feature", base_dir=self.base_dir)
        
        with open("shared.py", "w") as f:
            f.write("print('feature')")
        
        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=self.base_dir)
        
        # Switch to main and modify
        switch_branch("main", base_dir=self.base_dir)
        with open("shared.py", "w") as f:
            f.write("print('main')")
        
        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=self.base_dir)
        
        # Detect conflicts
        result = detect_conflicts("main", "feature", base_dir=self.base_dir)
        conflict_id = result["conflicts"][0]["conflict_id"]
        
        # Resolve with 'ours' (main)
        resolution = resolve_conflict(conflict_id, "ours", base_dir=self.base_dir)
        
        self.assertTrue(resolution["success"])
        self.assertEqual(resolution["strategy"], "ours")
        self.assertEqual(resolution["resolved_content"], "print('main')")
        
        # Verify conflict is marked resolved
        conflicts = get_conflicts(status="resolved", base_dir=self.base_dir)
        self.assertEqual(len(conflicts), 1)
    
    def test_resolve_conflict_theirs(self):
        """Test resolving conflict with 'theirs' strategy."""
        # Create and commit file in main
        with open("shared.py", "w") as f:
            f.write("print('base')")
        
        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=self.base_dir)
        
        # Create feature branch and modify
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        switch_branch("feature", base_dir=self.base_dir)
        
        with open("shared.py", "w") as f:
            f.write("print('feature')")
        
        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=self.base_dir)
        
        # Switch to main and modify
        switch_branch("main", base_dir=self.base_dir)
        with open("shared.py", "w") as f:
            f.write("print('main')")
        
        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=self.base_dir)
        
        # Detect conflicts
        result = detect_conflicts("main", "feature", base_dir=self.base_dir)
        conflict_id = result["conflicts"][0]["conflict_id"]
        
        # Resolve with 'theirs' (feature)
        resolution = resolve_conflict(conflict_id, "theirs", base_dir=self.base_dir)
        
        self.assertTrue(resolution["success"])
        self.assertEqual(resolution["strategy"], "theirs")
        self.assertEqual(resolution["resolved_content"], "print('feature')")
    
    def test_resolve_conflict_union(self):
        """Test resolving conflict with 'union' strategy."""
        # Create and commit file in main
        with open("shared.py", "w") as f:
            f.write("line1\nline2\n")
        
        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=self.base_dir)
        
        # Create feature branch and modify
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        switch_branch("feature", base_dir=self.base_dir)
        
        with open("shared.py", "w") as f:
            f.write("line1\nline2_feature\nline3\n")
        
        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=self.base_dir)
        
        # Switch to main and modify
        switch_branch("main", base_dir=self.base_dir)
        with open("shared.py", "w") as f:
            f.write("line1\nline2_main\n")
        
        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=self.base_dir)
        
        # Detect conflicts
        result = detect_conflicts("main", "feature", base_dir=self.base_dir)
        conflict_id = result["conflicts"][0]["conflict_id"]
        
        # Resolve with 'union'
        resolution = resolve_conflict(conflict_id, "union", base_dir=self.base_dir)
        
        self.assertTrue(resolution["success"])
        self.assertEqual(resolution["strategy"], "union")
        # Union should have lines from both
        content = resolution["resolved_content"]
        self.assertIn("line1", content)
    
    def test_resolve_conflict_manual(self):
        """Test resolving conflict with 'manual' strategy."""
        # Create and commit file in main
        with open("shared.py", "w") as f:
            f.write("print('base')")
        
        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=self.base_dir)
        
        # Create feature branch and modify
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        switch_branch("feature", base_dir=self.base_dir)
        
        with open("shared.py", "w") as f:
            f.write("print('feature')")
        
        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=self.base_dir)
        
        # Switch to main and modify
        switch_branch("main", base_dir=self.base_dir)
        with open("shared.py", "w") as f:
            f.write("print('main')")
        
        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=self.base_dir)
        
        # Detect conflicts
        result = detect_conflicts("main", "feature", base_dir=self.base_dir)
        conflict_id = result["conflicts"][0]["conflict_id"]
        
        # Resolve with 'manual'
        manual_content = "print('manual_resolution')"
        resolution = resolve_conflict(conflict_id, "manual", base_dir=self.base_dir, manual_content=manual_content)
        
        self.assertTrue(resolution["success"])
        self.assertEqual(resolution["strategy"], "manual")
        self.assertEqual(resolution["resolved_content"], manual_content)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="avcpm_util_test_")
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        with open("test.txt", "w") as f:
            f.write("Hello World")
        
        hash1 = _calculate_file_hash("test.txt")
        hash2 = _calculate_file_hash("test.txt")
        
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 hex length
    
    def test_calculate_file_hash_nonexistent(self):
        """Test file hash for non-existent file."""
        hash_result = _calculate_file_hash("nonexistent.txt")
        self.assertIsNone(hash_result)
    
    def test_generate_conflict_id(self):
        """Test conflict ID generation."""
        id1 = _generate_conflict_id()
        id2 = _generate_conflict_id()
        
        self.assertNotEqual(id1, id2)
        self.assertTrue(id1.startswith("conflict_"))
        self.assertTrue(id2.startswith("conflict_"))


class TestIntegration(unittest.TestCase):
    """Integration tests for conflict detection and resolution workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="avcpm_integration_test_")
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize main branch
        create_branch("main", base_dir=self.base_dir)
        switch_branch("main", base_dir=self.base_dir)
        
        # Create test agent
        create_agent("test_agent", "Test Agent", base_dir=self.base_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_full_conflict_workflow(self):
        """Test complete conflict detection and resolution workflow."""
        # Step 1: Create initial commit
        with open("app.py", "w") as f:
            f.write("def main():\n    print('Hello')\n")
        
        commit("TASK-001", "test_agent", "Initial commit", ["app.py"], base_dir=self.base_dir)
        
        # Step 2: Create feature branch and modify
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        switch_branch("feature", base_dir=self.base_dir)
        
        with open("app.py", "w") as f:
            f.write("def main():\n    print('Hello from feature')\n")
        
        commit("TASK-002", "test_agent", "Feature changes", ["app.py"], base_dir=self.base_dir)
        
        # Step 3: Switch to main and modify differently
        switch_branch("main", base_dir=self.base_dir)
        
        with open("app.py", "w") as f:
            f.write("def main():\n    print('Hello from main')\n")
        
        commit("TASK-003", "test_agent", "Main changes", ["app.py"], base_dir=self.base_dir)
        
        # Step 4: Detect conflicts
        result = detect_conflicts("main", "feature", base_dir=self.base_dir)
        
        self.assertEqual(result["conflict_count"], 1)
        self.assertEqual(result["conflicts"][0]["file"], "app.py")
        self.assertEqual(result["conflicts"][0]["status"], CONFLICT_STATUS_OPEN)
        
        # Step 5: Check auto-merge not possible
        self.assertFalse(auto_merge_possible("main", "feature", base_dir=self.base_dir))
        
        # Step 6: List open conflicts
        open_conflicts = get_conflicts(status="open", base_dir=self.base_dir)
        self.assertEqual(len(open_conflicts), 1)
        
        # Step 7: Resolve the conflict
        conflict_id = open_conflicts[0]["conflict_id"]
        resolution = resolve_conflict(conflict_id, "ours", base_dir=self.base_dir)
        
        self.assertTrue(resolution["success"])
        
        # Step 8: Verify conflict is now resolved
        open_conflicts = get_conflicts(status="open", base_dir=self.base_dir)
        self.assertEqual(len(open_conflicts), 0)
        
        resolved_conflicts = get_conflicts(status="resolved", base_dir=self.base_dir)
        self.assertEqual(len(resolved_conflicts), 1)
        self.assertEqual(resolved_conflicts[0]["conflict_id"], conflict_id)
    
    def test_multiple_conflicts(self):
        """Test detecting multiple conflicts."""
        # Create initial files
        with open("file1.py", "w") as f:
            f.write("print('file1')")
        
        with open("file2.py", "w") as f:
            f.write("print('file2')")
        
        commit("TASK-001", "test_agent", "Initial", ["file1.py", "file2.py"], base_dir=self.base_dir)
        
        # Create feature branch
        create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        switch_branch("feature", base_dir=self.base_dir)
        
        with open("file1.py", "w") as f:
            f.write("print('file1 feature')")
        
        with open("file2.py", "w") as f:
            f.write("print('file2 feature')")
        
        commit("TASK-002", "test_agent", "Feature changes", ["file1.py", "file2.py"], base_dir=self.base_dir)
        
        # Switch to main and modify
        switch_branch("main", base_dir=self.base_dir)
        
        with open("file1.py", "w") as f:
            f.write("print('file1 main')")
        
        with open("file2.py", "w") as f:
            f.write("print('file2 main')")
        
        commit("TASK-003", "test_agent", "Main changes", ["file1.py", "file2.py"], base_dir=self.base_dir)
        
        # Detect conflicts
        result = detect_conflicts("main", "feature", base_dir=self.base_dir)
        
        self.assertEqual(result["conflict_count"], 2)
        files = [c["file"] for c in result["conflicts"]]
        self.assertIn("file1.py", files)
        self.assertIn("file2.py", files)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConflictDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestThreeWayMerge))
    suite.addTests(loader.loadTestsFromTestCase(TestMergeFiles))
    suite.addTests(loader.loadTestsFromTestCase(TestBranchConflicts))
    suite.addTests(loader.loadTestsFromTestCase(TestConflictResolution))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
