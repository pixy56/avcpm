"""
Tests for AVCPM Conflict Detection & Resolution Module

Converted from unittest.TestCase to pytest fixtures (M-T5).
Run with: pytest test_avcpm_conflict.py -v
"""

import os
import sys
import json
import shutil
import tempfile
import pytest
from pathlib import Path

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


@pytest.fixture
def branch_env(tmp_path):
    """Set up test environment with branch and agent."""
    test_dir = str(tmp_path)
    base_dir = os.path.join(test_dir, ".avcpm")
    os.makedirs(base_dir, exist_ok=True)
    old_cwd = os.getcwd()
    os.chdir(test_dir)

    create_branch("main", base_dir=base_dir)
    switch_branch("main", base_dir=base_dir)
    create_agent("test_agent", "Test Agent", base_dir=base_dir)

    yield {"test_dir": test_dir, "base_dir": base_dir}

    os.chdir(old_cwd)


@pytest.fixture
def file_env(tmp_path):
    """Set up test environment for file operations."""
    test_dir = str(tmp_path)
    old_cwd = os.getcwd()
    os.chdir(test_dir)

    yield {"test_dir": test_dir}

    os.chdir(old_cwd)


class TestConflictDetection:
    """Test conflict detection functionality."""

    def test_check_file_conflict_no_conflict(self, file_env):
        """Test file conflict check - no conflict."""
        with open("file_a.txt", "w") as f:
            f.write("Hello World")

        result = check_file_conflict("file_a.txt", "file_a.txt", "file_a.txt")
        assert result["has_conflict"] is False
        assert result["conflict_type"] == "none"

    def test_check_file_conflict_content_conflict(self, file_env):
        """Test file conflict check - content conflict."""
        with open("base.txt", "w") as f:
            f.write("Hello World")
        with open("a.txt", "w") as f:
            f.write("Hello World Modified A")
        with open("b.txt", "w") as f:
            f.write("Hello World Modified B")

        result = check_file_conflict("a.txt", "b.txt", "base.txt")
        assert result["has_conflict"] is True
        assert result["conflict_type"] == "content"

    def test_check_file_conflict_delete_modify(self, file_env):
        """Test file conflict check - delete/modify conflict."""
        with open("base.txt", "w") as f:
            f.write("Hello World")
        with open("modified.txt", "w") as f:
            f.write("Hello World Modified")

        result = check_file_conflict(None, "modified.txt", "base.txt")
        assert result["has_conflict"] is True
        assert result["conflict_type"] == "delete_modify"

    def test_check_file_conflict_add_add_same(self, file_env):
        """Test file conflict check - add/add same content."""
        with open("a.txt", "w") as f:
            f.write("New File Content")
        with open("b.txt", "w") as f:
            f.write("New File Content")

        result = check_file_conflict("a.txt", "b.txt", None)
        assert result["has_conflict"] is False
        assert result["conflict_type"] == "none"

    def test_check_file_conflict_add_add_different(self, file_env):
        """Test file conflict check - add/add different content."""
        with open("a.txt", "w") as f:
            f.write("Content A")
        with open("b.txt", "w") as f:
            f.write("Content B")

        result = check_file_conflict("a.txt", "b.txt", None)
        assert result["has_conflict"] is True
        assert result["conflict_type"] == "add_add"

    def test_check_file_conflict_only_one_modified(self, file_env):
        """Test file conflict check - only one branch modified."""
        with open("base.txt", "w") as f:
            f.write("Hello World")
        with open("modified.txt", "w") as f:
            f.write("Hello World Modified")

        result = check_file_conflict("modified.txt", "base.txt", "base.txt")
        assert result["has_conflict"] is False
        assert result["conflict_type"] == "none"


class TestThreeWayMerge:
    """Test three-way merge functionality."""

    def test_merge_identical(self):
        result = merge_three_way("Hello", "Hello", "Hello")
        assert result["has_conflict"] is False
        assert result["merged_content"] == "Hello"

    def test_merge_base_equals_a(self):
        result = merge_three_way("Hello", "Hello", "World")
        assert result["has_conflict"] is False
        assert result["merged_content"] == "World"

    def test_merge_base_equals_b(self):
        result = merge_three_way("Hello", "World", "Hello")
        assert result["has_conflict"] is False
        assert result["merged_content"] == "World"

    def test_merge_no_conflict_different_lines(self):
        base = "Line 1\nLine 2\nLine 3\n"
        a = "Line 1 Modified\nLine 2\nLine 3\n"
        b = "Line 1\nLine 2\nLine 3 Modified\n"

        result = merge_three_way(base, a, b)
        assert result["has_conflict"] is False
        assert "Line 1 Modified" in result["merged_content"]
        assert "Line 3 Modified" in result["merged_content"]

    def test_merge_conflict_same_line(self):
        base = "Hello World"
        a = "Hello Modified A"
        b = "Hello Modified B"

        result = merge_three_way(base, a, b)
        assert result["has_conflict"] is True
        assert "<<<<<<" in result["merged_content"]
        assert "=======" in result["merged_content"]
        assert ">>>>>>>" in result["merged_content"]

    def test_merge_with_deletion(self):
        base = "Hello World\nLine 2\n"
        a = None
        b = "Hello World\nLine 2 Modified\n"

        result = merge_three_way(base, a, b)
        assert result["has_conflict"] is True
        assert "<<<<<<" in result["merged_content"]

    def test_merge_empty_base(self):
        a = "Content A"
        b = "Content B"

        result = merge_three_way(None, a, b)
        assert result["has_conflict"] is True

    def test_merge_lines_added_end(self):
        base = "Line 1\nLine 2\n"
        a = "Line 1\nLine 2\nLine 3 A\n"
        b = "Line 1\nLine 2\nLine 3 B\n"

        result = merge_three_way(base, a, b)
        assert result["has_conflict"] is True
        assert "<<<<<<" in result["merged_content"]


class TestMergeFiles:
    """Test file merging operations."""

    def test_merge_files_no_conflict(self, file_env):
        """Test merging files with no conflict."""
        with open("base.txt", "w") as f:
            f.write("Hello World")
        with open("a.txt", "w") as f:
            f.write("Hello World Modified")
        with open("b.txt", "w") as f:
            f.write("Hello World")

        result = merge_files("base.txt", "a.txt", "b.txt", "output.txt")

        assert result["success"] is True
        assert result["has_conflict"] is False
        assert os.path.exists("output.txt")

        with open("output.txt", "r") as f:
            content = f.read()
        assert content == "Hello World Modified"

    def test_merge_files_with_conflict(self, file_env):
        """Test merging files with conflict."""
        with open("base.txt", "w") as f:
            f.write("Hello World")
        with open("a.txt", "w") as f:
            f.write("Hello World A")
        with open("b.txt", "w") as f:
            f.write("Hello World B")

        result = merge_files("base.txt", "a.txt", "b.txt", "output.txt")

        assert result["success"] is True
        assert result["has_conflict"] is True
        assert os.path.exists("output.txt")

        with open("output.txt", "r") as f:
            content = f.read()
        assert "<<<<<<" in content
        assert "=======" in content
        assert ">>>>>>>" in content

    def test_merge_files_new_file(self, file_env):
        """Test merging new files."""
        with open("a.txt", "w") as f:
            f.write("Content A")
        with open("b.txt", "w") as f:
            f.write("Content A")

        result = merge_files(None, "a.txt", "b.txt", "output.txt")

        assert result["success"] is True
        assert result["has_conflict"] is False

        with open("output.txt", "r") as f:
            content = f.read()
        assert content == "Content A"


class TestBranchConflicts:
    """Test branch-level conflict detection."""

    def test_list_modified_files_empty(self, branch_env):
        files = list_modified_files("main", base_dir=branch_env["base_dir"])
        assert files == {}

    def test_list_modified_files_with_commits(self, branch_env):
        with open("test.py", "w") as f:
            f.write("print('hello')")

        commit("TASK-001", "test_agent", "Initial commit", ["test.py"], base_dir=branch_env["base_dir"])

        files = list_modified_files("main", base_dir=branch_env["base_dir"])
        assert "test.py" in files

    def test_auto_merge_possible_no_changes(self, branch_env):
        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])

        result = auto_merge_possible("main", "feature", base_dir=branch_env["base_dir"])
        assert result is True

    def test_auto_merge_possible_no_conflict(self, branch_env):
        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])
        switch_branch("feature", base_dir=branch_env["base_dir"])

        with open("feature_file.py", "w") as f:
            f.write("print('feature')")

        commit("TASK-002", "test_agent", "Feature commit", ["feature_file.py"], base_dir=branch_env["base_dir"])

        result = auto_merge_possible("main", "feature", base_dir=branch_env["base_dir"])
        assert result is True

    def test_detect_conflicts_with_overlap(self, branch_env):
        with open("shared.py", "w") as f:
            f.write("print('main')")

        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=branch_env["base_dir"])

        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])
        switch_branch("feature", base_dir=branch_env["base_dir"])

        with open("shared.py", "w") as f:
            f.write("print('feature')")

        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=branch_env["base_dir"])

        switch_branch("main", base_dir=branch_env["base_dir"])
        with open("shared.py", "w") as f:
            f.write("print('main modified')")

        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=branch_env["base_dir"])

        result = detect_conflicts("main", "feature", base_dir=branch_env["base_dir"])

        assert result["conflict_count"] == 1
        assert result["auto_mergeable"] is False
        assert result["conflicts"][0]["file"] == "shared.py"
        assert result["conflicts"][0]["conflict_type"] == "content"


class TestConflictResolution:
    """Test conflict resolution functionality."""

    def test_resolution_strategies_defined(self):
        assert "ours" in RESOLUTION_STRATEGIES
        assert "theirs" in RESOLUTION_STRATEGIES
        assert "union" in RESOLUTION_STRATEGIES
        assert "manual" in RESOLUTION_STRATEGIES

    def test_get_conflicts_empty(self, branch_env):
        conflicts = get_conflicts(status="open", base_dir=branch_env["base_dir"])
        assert conflicts == []

    def test_resolve_conflict_not_found(self, branch_env):
        with pytest.raises(ValueError, match="not found"):
            resolve_conflict("non_existent", "ours", base_dir=branch_env["base_dir"])

    def test_resolve_conflict_invalid_strategy(self, branch_env):
        with pytest.raises(ValueError, match="Invalid resolution strategy"):
            resolve_conflict("test", "invalid_strategy", base_dir=branch_env["base_dir"])

    def test_resolve_conflict_ours(self, branch_env):
        with open("shared.py", "w") as f:
            f.write("print('base')")

        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=branch_env["base_dir"])

        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])
        switch_branch("feature", base_dir=branch_env["base_dir"])

        with open("shared.py", "w") as f:
            f.write("print('feature')")

        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=branch_env["base_dir"])

        switch_branch("main", base_dir=branch_env["base_dir"])
        with open("shared.py", "w") as f:
            f.write("print('main')")

        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=branch_env["base_dir"])

        result = detect_conflicts("main", "feature", base_dir=branch_env["base_dir"])
        conflict_id = result["conflicts"][0]["conflict_id"]

        resolution = resolve_conflict(conflict_id, "ours", base_dir=branch_env["base_dir"])

        assert resolution["success"] is True
        assert resolution["strategy"] == "ours"
        assert resolution["resolved_content"] == "print('main')"

        conflicts = get_conflicts(status="resolved", base_dir=branch_env["base_dir"])
        assert len(conflicts) == 1

    def test_resolve_conflict_theirs(self, branch_env):
        with open("shared.py", "w") as f:
            f.write("print('base')")

        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=branch_env["base_dir"])

        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])
        switch_branch("feature", base_dir=branch_env["base_dir"])

        with open("shared.py", "w") as f:
            f.write("print('feature')")

        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=branch_env["base_dir"])

        switch_branch("main", base_dir=branch_env["base_dir"])
        with open("shared.py", "w") as f:
            f.write("print('main')")

        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=branch_env["base_dir"])

        result = detect_conflicts("main", "feature", base_dir=branch_env["base_dir"])
        conflict_id = result["conflicts"][0]["conflict_id"]

        resolution = resolve_conflict(conflict_id, "theirs", base_dir=branch_env["base_dir"])

        assert resolution["success"] is True
        assert resolution["strategy"] == "theirs"
        assert resolution["resolved_content"] == "print('feature')"

    def test_resolve_conflict_union(self, branch_env):
        with open("shared.py", "w") as f:
            f.write("line1\nline2\n")

        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=branch_env["base_dir"])

        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])
        switch_branch("feature", base_dir=branch_env["base_dir"])

        with open("shared.py", "w") as f:
            f.write("line1\nline2_feature\nline3\n")

        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=branch_env["base_dir"])

        switch_branch("main", base_dir=branch_env["base_dir"])
        with open("shared.py", "w") as f:
            f.write("line1\nline2_main\n")

        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=branch_env["base_dir"])

        result = detect_conflicts("main", "feature", base_dir=branch_env["base_dir"])
        conflict_id = result["conflicts"][0]["conflict_id"]

        resolution = resolve_conflict(conflict_id, "union", base_dir=branch_env["base_dir"])

        assert resolution["success"] is True
        assert resolution["strategy"] == "union"
        assert "line1" in resolution["resolved_content"]

    def test_resolve_conflict_manual(self, branch_env):
        with open("shared.py", "w") as f:
            f.write("print('base')")

        commit("TASK-001", "test_agent", "Initial commit", ["shared.py"], base_dir=branch_env["base_dir"])

        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])
        switch_branch("feature", base_dir=branch_env["base_dir"])

        with open("shared.py", "w") as f:
            f.write("print('feature')")

        commit("TASK-002", "test_agent", "Feature commit", ["shared.py"], base_dir=branch_env["base_dir"])

        switch_branch("main", base_dir=branch_env["base_dir"])
        with open("shared.py", "w") as f:
            f.write("print('main')")

        commit("TASK-003", "test_agent", "Main commit", ["shared.py"], base_dir=branch_env["base_dir"])

        result = detect_conflicts("main", "feature", base_dir=branch_env["base_dir"])
        conflict_id = result["conflicts"][0]["conflict_id"]

        manual_content = "print('manual_resolution')"
        resolution = resolve_conflict(conflict_id, "manual", base_dir=branch_env["base_dir"], manual_content=manual_content)

        assert resolution["success"] is True
        assert resolution["strategy"] == "manual"
        assert resolution["resolved_content"] == manual_content


class TestUtilityFunctions:
    """Test utility functions."""

    def test_calculate_file_hash(self, file_env):
        with open("test.txt", "w") as f:
            f.write("Hello World")

        hash1 = _calculate_file_hash("test.txt")
        hash2 = _calculate_file_hash("test.txt")

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_calculate_file_hash_nonexistent(self):
        hash_result = _calculate_file_hash("nonexistent.txt")
        assert hash_result is None

    def test_generate_conflict_id(self):
        id1 = _generate_conflict_id()
        id2 = _generate_conflict_id()

        assert id1 != id2
        assert id1.startswith("conflict_")
        assert id2.startswith("conflict_")


class TestIntegration:
    """Integration tests for conflict detection and resolution workflow."""

    def test_full_conflict_workflow(self, branch_env):
        """Test complete conflict detection and resolution workflow."""
        with open("app.py", "w") as f:
            f.write("def main():\n    print('Hello')\n")

        commit("TASK-001", "test_agent", "Initial commit", ["app.py"], base_dir=branch_env["base_dir"])

        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])
        switch_branch("feature", base_dir=branch_env["base_dir"])

        with open("app.py", "w") as f:
            f.write("def main():\n    print('Hello from feature')\n")

        commit("TASK-002", "test_agent", "Feature changes", ["app.py"], base_dir=branch_env["base_dir"])

        switch_branch("main", base_dir=branch_env["base_dir"])

        with open("app.py", "w") as f:
            f.write("def main():\n    print('Hello from main')\n")

        commit("TASK-003", "test_agent", "Main changes", ["app.py"], base_dir=branch_env["base_dir"])

        result = detect_conflicts("main", "feature", base_dir=branch_env["base_dir"])

        assert result["conflict_count"] == 1
        assert result["conflicts"][0]["file"] == "app.py"
        assert result["conflicts"][0]["status"] == CONFLICT_STATUS_OPEN

        assert auto_merge_possible("main", "feature", base_dir=branch_env["base_dir"]) is False

        open_conflicts = get_conflicts(status="open", base_dir=branch_env["base_dir"])
        assert len(open_conflicts) == 1

        conflict_id = open_conflicts[0]["conflict_id"]
        resolution = resolve_conflict(conflict_id, "ours", base_dir=branch_env["base_dir"])

        assert resolution["success"] is True

        open_conflicts = get_conflicts(status="open", base_dir=branch_env["base_dir"])
        assert len(open_conflicts) == 0

        resolved_conflicts = get_conflicts(status="resolved", base_dir=branch_env["base_dir"])
        assert len(resolved_conflicts) == 1
        assert resolved_conflicts[0]["conflict_id"] == conflict_id

    def test_multiple_conflicts(self, branch_env):
        with open("file1.py", "w") as f:
            f.write("print('file1')")
        with open("file2.py", "w") as f:
            f.write("print('file2')")

        commit("TASK-001", "test_agent", "Initial", ["file1.py", "file2.py"], base_dir=branch_env["base_dir"])

        create_branch("feature", parent_branch="main", base_dir=branch_env["base_dir"])
        switch_branch("feature", base_dir=branch_env["base_dir"])

        with open("file1.py", "w") as f:
            f.write("print('file1 feature')")
        with open("file2.py", "w") as f:
            f.write("print('file2 feature')")

        commit("TASK-002", "test_agent", "Feature changes", ["file1.py", "file2.py"], base_dir=branch_env["base_dir"])

        switch_branch("main", base_dir=branch_env["base_dir"])

        with open("file1.py", "w") as f:
            f.write("print('file1 main')")
        with open("file2.py", "w") as f:
            f.write("print('file2 main')")

        commit("TASK-003", "test_agent", "Main changes", ["file1.py", "file2.py"], base_dir=branch_env["base_dir"])

        result = detect_conflicts("main", "feature", base_dir=branch_env["base_dir"])

        assert result["conflict_count"] == 2
        files = [c["file"] for c in result["conflicts"]]
        assert "file1.py" in files
        assert "file2.py" in files