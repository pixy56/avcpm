"""
Tests for AVCPM Diff & History System

Run with: python3 test_avcpm_diff.py
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

# Ensure the module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_diff as diff
import avcpm_branch as branch
import avcpm_commit as commit
import avcpm_agent as agent


class TestDiffFoundation(unittest.TestCase):
    """Test basic diff functionality."""
    
    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create an agent for commits - use the base_dir in setup
        os.environ['AVCPM_TEST_DIR'] = self.base_dir
        agent.create_agent("test-agent", "Test Agent", base_dir=self.base_dir)
    
    def tearDown(self):
        """Cleanup."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_diff_files(self):
        """Test comparing two files."""
        # Create two test files
        file_a = os.path.join(self.test_dir, "file_a.txt")
        file_b = os.path.join(self.test_dir, "file_b.txt")
        
        with open(file_a, "w") as f:
            f.write("line1\nline2\nline3\n")
        
        with open(file_b, "w") as f:
            f.write("line1\nmodified\nline3\nline4\n")
        
        result = diff.diff_files(file_a, file_b)
        
        self.assertIn("---", result)
        self.assertIn("+++", result)
        self.assertIn("@@", result)
        self.assertIn("-line2", result)
        self.assertIn("+modified", result)
        self.assertIn("+line4", result)
    
    def test_diff_files_identical(self):
        """Test comparing identical files."""
        file_a = os.path.join(self.test_dir, "file_a.txt")
        file_b = os.path.join(self.test_dir, "file_b.txt")
        
        with open(file_a, "w") as f:
            f.write("content\n")
        
        with open(file_b, "w") as f:
            f.write("content\n")
        
        result = diff.diff_files(file_a, file_b)
        self.assertEqual(result, "")
    
    def test_diff_files_nonexistent(self):
        """Test comparing with non-existent file."""
        file_a = os.path.join(self.test_dir, "file_a.txt")
        file_b = os.path.join(self.test_dir, "nonexistent.txt")
        
        with open(file_a, "w") as f:
            f.write("content\n")
        
        result = diff.diff_files(file_a, file_b)
        # Should handle missing file gracefully
        self.assertIn("---", result)


class TestCommitDiff(unittest.TestCase):
    """Test diff between commits."""
    
    def setUp(self):
        """Create a temporary directory with commits."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create agent with base_dir
        agent.create_agent("test-agent", "Test Agent", base_dir=self.base_dir)
        
        # Create test files
        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    return 'hello'\n")
        
        # Make first commit
        commit.commit("TASK-001", "test-agent", "Initial commit", [self.test_file], base_dir=self.base_dir)
        
        # Get commit ID
        ledger_dir = branch.get_branch_ledger_dir("main", self.base_dir)
        commits = sorted([f for f in os.listdir(ledger_dir) if f.endswith(".json")])
        self.commit_a = commits[0].replace(".json", "")
        
        # Modify file and make second commit
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    return 'world'\n")
        
        commit.commit("TASK-002", "test-agent", "Update return value", [self.test_file], base_dir=self.base_dir)
        
        commits = sorted([f for f in os.listdir(ledger_dir) if f.endswith(".json")])
        self.commit_b = commits[-1].replace(".json", "")
    
    def tearDown(self):
        """Cleanup."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_diff_commits(self):
        """Test diff between two commits."""
        result = diff.diff_commits(self.commit_a, self.commit_b, self.base_dir)
        
        self.assertIn("commit_a", result)
        self.assertIn("commit_b", result)
        self.assertEqual(result["commit_a"], self.commit_a)
        self.assertEqual(result["commit_b"], self.commit_b)
        self.assertIn("diff", result)
        self.assertIn("stats", result)
        self.assertEqual(result["stats"]["files_changed"], 1)
    
    def test_diff_commits_invalid_commit(self):
        """Test diff with invalid commit ID."""
        with self.assertRaises(ValueError) as context:
            diff.diff_commits("invalid", self.commit_b, self.base_dir)
        
        self.assertIn("not found", str(context.exception))
    
    def test_show_commit(self):
        """Test showing commit details."""
        result = diff.show_commit(self.commit_a, self.base_dir)
        
        self.assertEqual(result["commit_id"], self.commit_a)
        self.assertIn("timestamp", result)
        self.assertEqual(result["agent_id"], "test-agent")
        self.assertEqual(result["task_id"], "TASK-001")
        self.assertIn("rationale", result)
        self.assertIn("changes", result)
        self.assertEqual(len(result["changes"]), 1)
    
    def test_show_commit_invalid(self):
        """Test showing invalid commit."""
        with self.assertRaises(ValueError) as context:
            diff.show_commit("nonexistent", self.base_dir)
        
        self.assertIn("not found", str(context.exception))


class TestHistory(unittest.TestCase):
    """Test history tracking."""
    
    def setUp(self):
        """Create a temporary directory with history."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create agent
        agent.create_agent("test-agent", "Test Agent", self.base_dir)
        
        # Create test file
        self.test_file = os.path.join(self.test_dir, "test.py")
        
        # Make multiple commits
        for i in range(3):
            with open(self.test_file, "w") as f:
                f.write(f"# Version {i + 1}\n")
            
            commit.commit(f"TASK-00{i+1}", "test-agent", f"Commit {i+1}", 
                        [self.test_file], base_dir=self.base_dir)
    
    def tearDown(self):
        """Cleanup."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_log(self):
        """Test getting commit log."""
        commits = diff.log(branch="main", limit=10, base_dir=self.base_dir)
        
        self.assertEqual(len(commits), 3)
        self.assertTrue(all("commit_id" in c for c in commits))
        self.assertTrue(all("timestamp" in c for c in commits))
        self.assertTrue(all("agent_id" in c for c in commits))
    
    def test_log_limit(self):
        """Test log with limit."""
        commits = diff.log(branch="main", limit=2, base_dir=self.base_dir)
        
        self.assertEqual(len(commits), 2)
    
    def test_file_history(self):
        """Test getting file history."""
        history = diff.file_history(self.test_file, self.base_dir)
        
        self.assertEqual(len(history), 3)
        self.assertTrue(all("commit_id" in h for h in history))
        self.assertTrue(all("timestamp" in h for h in history))
        self.assertTrue(all("checksum" in h for h in history))
    
    def test_file_history_no_history(self):
        """Test file with no history."""
        history = diff.file_history("/nonexistent/file.py", self.base_dir)
        
        self.assertEqual(len(history), 0)


class TestBlame(unittest.TestCase):
    """Test blame functionality."""
    
    def setUp(self):
        """Create a temporary directory with commits."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create agent
        agent.create_agent("test-agent", "Test Agent", self.base_dir)
        
        # Create test file with content
        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("line1\nline2\nline3\n")
        
        # Make commit
        commit.commit("TASK-001", "test-agent", "Initial commit", 
                    [self.test_file], base_dir=self.base_dir)
    
    def tearDown(self):
        """Cleanup."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_blame(self):
        """Test blame functionality."""
        result = diff.blame(self.test_file, self.base_dir)
        
        self.assertEqual(len(result), 3)
        
        for line in result:
            self.assertIn("line_number", line)
            self.assertIn("content", line)
            self.assertIn("commit_id", line)
            self.assertIn("agent_id", line)
            self.assertEqual(line["agent_id"], "test-agent")
    
    def test_blame_no_history(self):
        """Test blame on file with no history."""
        result = diff.blame("/nonexistent/file.py", self.base_dir)
        
        self.assertEqual(len(result), 0)


class TestBranchDiff(unittest.TestCase):
    """Test branch comparison."""
    
    def setUp(self):
        """Create a temporary directory with multiple branches."""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create agent
        agent.create_agent("test-agent", "Test Agent", self.base_dir)
        
        # Create file and commit to main
        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("# Main version\n")
        
        commit.commit("TASK-001", "test-agent", "Main commit", 
                    [self.test_file], base_dir=self.base_dir)
        
        # Create feature branch
        branch.create_branch("feature", parent_branch="main", base_dir=self.base_dir)
        
        # Modify file in feature branch
        with open(self.test_file, "w") as f:
            f.write("# Feature version\n")
        
        commit.commit("TASK-002", "test-agent", "Feature commit", 
                    [self.test_file], branch_name="feature", base_dir=self.base_dir)
    
    def tearDown(self):
        """Cleanup."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_diff_branches(self):
        """Test diff between two branches."""
        result = diff.diff_branches("main", "feature", self.base_dir)
        
        self.assertIn("branch_a", result)
        self.assertIn("branch_b", result)
        self.assertEqual(result["branch_a"], "main")
        self.assertEqual(result["branch_b"], "feature")
        self.assertIn("diff", result)
        self.assertIn("stats", result)
    
    def test_diff_branches_invalid(self):
        """Test diff with invalid branch."""
        with self.assertRaises(ValueError) as context:
            diff.diff_branches("main", "nonexistent", self.base_dir)
        
        self.assertIn("not found", str(context.exception))


class TestOutputFormats(unittest.TestCase):
    """Test different output formats."""
    
    def test_format_diff_json(self):
        """Test JSON formatting."""
        diff_result = {
            "commit_a": "abc123",
            "commit_b": "def456",
            "diff": "some diff content",
            "stats": {"files_changed": 1, "insertions": 2, "deletions": 1}
        }
        
        result = diff.format_diff_json(diff_result)
        parsed = json.loads(result)
        
        self.assertEqual(parsed["commit_a"], "abc123")
        self.assertEqual(parsed["stats"]["files_changed"], 1)
    
    def test_format_blame_output(self):
        """Test blame formatting."""
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
        
        self.assertIn("abc123de", result)
        self.assertIn("test-agent", result)
        self.assertIn("hello", result)
    
    def test_format_blame_output_with_timestamp(self):
        """Test blame formatting with timestamps."""
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
        
        self.assertIn("2024-01-01", result)
    
    def test_format_diff_side_by_side(self):
        """Test side-by-side formatting."""
        diff_text = """--- a/file.py
+++ b/file.py
@@ -1,2 +1,2 @@
-line1
+modified
 line2
"""
        
        result = diff.format_diff_side_by_side(diff_text)
        
        # Should contain both versions
        self.assertTrue("line1" in result or "modified" in result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
