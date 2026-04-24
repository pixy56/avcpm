"""
Tests for AVCPM Diff & History System

Converted from unittest.TestCase to pytest fixtures (M-T5).
Run with: pytest test_avcpm_diff.py -v
"""

import os
import sys
import json
import shutil
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_diff as diff
import avcpm_branch as branch
import avcpm_commit as commit
import avcpm_agent as agent


class TestDiffFoundation:
    """Test basic diff functionality."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.test_dir = str(tmp_path)
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        yield

    def test_diff_files(self):
        """Test comparing two files."""
        file_a = os.path.join(self.test_dir, "file_a.txt")
        file_b = os.path.join(self.test_dir, "file_b.txt")

        with open(file_a, "w") as f:
            f.write("line1\nline2\nline3\n")
        with open(file_b, "w") as f:
            f.write("line1\nmodified\nline3\nline4\n")

        result = diff.diff_files(file_a, file_b)

        assert "---" in result
        assert "+++" in result
        assert "@@" in result
        assert "-line2" in result
        assert "+modified" in result
        assert "+line4" in result

    def test_diff_files_identical(self):
        """Test comparing identical files."""
        file_a = os.path.join(self.test_dir, "file_a.txt")
        file_b = os.path.join(self.test_dir, "file_b.txt")

        with open(file_a, "w") as f:
            f.write("content\n")
        with open(file_b, "w") as f:
            f.write("content\n")

        result = diff.diff_files(file_a, file_b)
        assert result == ""

    def test_diff_files_nonexistent(self):
        """Test comparing with non-existent file."""
        file_a = os.path.join(self.test_dir, "file_a.txt")
        file_b = os.path.join(self.test_dir, "nonexistent.txt")

        with open(file_a, "w") as f:
            f.write("content\n")

        result = diff.diff_files(file_a, file_b)
        assert "---" in result


class TestCommitDiff:
    """Test diff between commits."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.test_dir = str(tmp_path)
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)

        agent_data = agent.create_agent("Test Agent", "test@example.com", base_dir=self.base_dir)
        self.agent_id = agent_data["agent_id"]

        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    return 'hello'\n")

        commit.commit("TASK-001", self.agent_id, "Initial commit", [self.test_file], base_dir=self.base_dir)

        ledger_dir = branch.get_branch_ledger_dir("main", self.base_dir)
        commits = sorted([f for f in os.listdir(ledger_dir) if f.endswith(".json")])
        self.commit_a = commits[0].replace(".json", "")

        with open(self.test_file, "w") as f:
            f.write("def hello():\n    return 'world'\n")

        commit.commit("TASK-002", self.agent_id, "Update return value", [self.test_file], base_dir=self.base_dir)

        commits = sorted([f for f in os.listdir(ledger_dir) if f.endswith(".json")])
        self.commit_b = commits[-1].replace(".json", "")
        yield

    def test_diff_commits(self):
        result = diff.diff_commits(self.commit_a, self.commit_b, self.base_dir)

        assert "commit_a" in result
        assert "commit_b" in result
        assert result["commit_a"] == self.commit_a
        assert result["commit_b"] == self.commit_b
        assert "diff" in result
        assert "stats" in result
        assert result["stats"]["files_changed"] == 1

    def test_diff_commits_invalid_commit(self):
        with pytest.raises(ValueError, match="not found"):
            diff.diff_commits("invalid", self.commit_b, self.base_dir)

    def test_show_commit(self):
        result = diff.show_commit(self.commit_a, self.base_dir)

        assert result["commit_id"] == self.commit_a
        assert "timestamp" in result
        assert result["agent_id"] == self.agent_id
        assert result["task_id"] == "TASK-001"
        assert "rationale" in result
        assert "changes" in result
        assert len(result["changes"]) == 1

    def test_show_commit_invalid(self):
        with pytest.raises(ValueError, match="not found"):
            diff.show_commit("nonexistent", self.base_dir)


class TestHistory:
    """Test history tracking."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.test_dir = str(tmp_path)
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)

        agent_data = agent.create_agent("Test Agent", "test@example.com", base_dir=self.base_dir)
        self.agent_id = agent_data["agent_id"]

        self.test_file = os.path.join(self.test_dir, "test.py")

        for i in range(3):
            with open(self.test_file, "w") as f:
                f.write(f"# Version {i + 1}\n")
            commit.commit(f"TASK-00{i+1}", self.agent_id, f"Commit {i+1}",
                         [self.test_file], base_dir=self.base_dir)
        yield

    def test_log(self):
        commits = diff.log(branch="main", limit=10, base_dir=self.base_dir)

        assert len(commits) == 3
        assert all("commit_id" in c for c in commits)
        assert all("timestamp" in c for c in commits)
        assert all("agent_id" in c for c in commits)

    def test_log_limit(self):
        commits = diff.log(branch="main", limit=2, base_dir=self.base_dir)
        assert len(commits) == 2

    def test_file_history(self):
        history = diff.file_history(self.test_file, self.base_dir)

        assert len(history) == 3
        assert all("commit_id" in h for h in history)
        assert all("timestamp" in h for h in history)
        assert all("checksum" in h for h in history)

    def test_file_history_no_history(self):
        history = diff.file_history("/nonexistent/file.py", self.base_dir)
        assert len(history) == 0


class TestBlame:
    """Test blame functionality."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.test_dir = str(tmp_path)
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)

        agent_data = agent.create_agent("Test Agent", "test@example.com", base_dir=self.base_dir)
        self.agent_id = agent_data["agent_id"]

        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("line1\nline2\nline3\n")

        commit.commit("TASK-001", self.agent_id, "Initial commit",
                     [self.test_file], base_dir=self.base_dir)
        yield

    def test_blame(self):
        result = diff.blame(self.test_file, self.base_dir)

        assert len(result) == 3
        for line in result:
            assert "line_number" in line
            assert "content" in line
            assert "commit_id" in line
            assert "agent_id" in line
            assert line["agent_id"] == self.agent_id

    def test_blame_no_history(self):
        result = diff.blame("/nonexistent/file.py", self.base_dir)
        assert len(result) == 0


class TestBranchDiff:
    """Test branch comparison."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.test_dir = str(tmp_path)
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)

        agent_data = agent.create_agent("Test Agent", "test@example.com", base_dir=self.base_dir)
        self.agent_id = agent_data["agent_id"]

        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("# Main version\n")

        commit.commit("TASK-001", self.agent_id, "Main commit",
                     [self.test_file], base_dir=self.base_dir)

        branch.create_branch("feature", parent_branch="main", base_dir=self.base_dir)

        with open(self.test_file, "w") as f:
            f.write("# Feature version\n")

        commit.commit("TASK-002", self.agent_id, "Feature commit",
                     [self.test_file], branch_name="feature", base_dir=self.base_dir)
        yield

    def test_diff_branches(self):
        result = diff.diff_branches("main", "feature", self.base_dir)

        assert "branch_a" in result
        assert "branch_b" in result
        assert result["branch_a"] == "main"
        assert result["branch_b"] == "feature"
        assert "diff" in result
        assert "stats" in result

    def test_diff_branches_invalid(self):
        with pytest.raises(ValueError, match="not found"):
            diff.diff_branches("main", "nonexistent", self.base_dir)


class TestOutputFormats:
    """Test different output formats."""

    def test_format_diff_json(self):
        diff_result = {
            "commit_a": "abc123",
            "commit_b": "def456",
            "diff": "some diff content",
            "stats": {"files_changed": 1, "insertions": 2, "deletions": 1}
        }

        result = diff.format_diff_json(diff_result)
        parsed = json.loads(result)

        assert parsed["commit_a"] == "abc123"
        assert parsed["stats"]["files_changed"] == 1

    def test_format_blame_output(self):
        blame_result = [
            {
                "line_number": 1,
                "content": "hello",
                "commit_id": "abc123def456",
                "agent_id": "test-agent",
                "timestamp": "2024-01-01T00:00:00"
            }
        ]

        result = diff.format_blame_output(blame_result)

        assert "abc123de" in result
        assert "test-agent" in result
        assert "hello" in result

    def test_format_blame_output_with_timestamp(self):
        blame_result = [
            {
                "line_number": 1,
                "content": "hello",
                "commit_id": "abc123def456",
                "agent_id": "test-agent",
                "timestamp": "2024-01-01T00:00:00"
            }
        ]

        result = diff.format_blame_output(blame_result, show_timestamps=True)
        assert "2024-01-01" in result

    def test_format_diff_side_by_side(self):
        diff_text = """--- a/file.py
+++ b/file.py
@@ -1,2 +1,2 @@
-line1
+modified
 line2
"""

        result = diff.format_diff_side_by_side(diff_text)
        assert "line1" in result or "modified" in result