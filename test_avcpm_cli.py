#!/usr/bin/env python3
"""
Tests for AVCPM Unified CLI.

Run with:
    python -m pytest test_avcpm_cli.py -v
    python test_avcpm_cli.py
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from avcpm_cli import (
    load_config, get_base_dir, create_parser, main,
    task_command, branch_command, agent_command,
    __version__
)


class TestCLIConfiguration(unittest.TestCase):
    """Test configuration loading."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_load_config_from_file(self):
        """Test loading config from file."""
        config_data = {"base_dir": "/custom/path", "verbose": True}
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f)
        
        config = load_config(self.config_path)
        self.assertEqual(config["base_dir"], "/custom/path")
        self.assertEqual(config["verbose"], True)
    
    def test_load_config_nonexistent(self):
        """Test loading config when file doesn't exist."""
        config = load_config("/nonexistent/config.json")
        self.assertEqual(config, {})
    
    def test_load_config_invalid_json(self):
        """Test loading config with invalid JSON."""
        with open(self.config_path, 'w') as f:
            f.write("invalid json")
        
        # Should return empty config with warning printed
        config = load_config(self.config_path)
        self.assertEqual(config, {})


class TestCLIParser(unittest.TestCase):
    """Test CLI argument parsing."""
    
    def setUp(self):
        self.parser = create_parser()
    
    def test_version_flag(self):
        """Test --version flag."""
        with self.assertRaises(SystemExit) as cm:
            self.parser.parse_args(["--version"])
        self.assertEqual(cm.exception.code, 0)
    
    def test_global_base_dir(self):
        """Test --base-dir global option."""
        args = self.parser.parse_args(["--base-dir", "/custom", "task", "list"])
        self.assertEqual(args.base_dir, "/custom")
    
    def test_global_verbose(self):
        """Test --verbose global option."""
        args = self.parser.parse_args(["--verbose", "task", "list"])
        self.assertTrue(args.verbose)
    
    def test_task_create_parsing(self):
        """Test task create argument parsing."""
        args = self.parser.parse_args(["task", "create", "TASK-001", "Test description"])
        self.assertEqual(args.command, "task")
        self.assertEqual(args.subcommand, "create")
        self.assertEqual(args.task_id, "TASK-001")
        self.assertEqual(args.description, "Test description")
    
    def test_task_move_parsing(self):
        """Test task move argument parsing."""
        args = self.parser.parse_args(["task", "move", "TASK-001", "done", "--force"])
        self.assertEqual(args.subcommand, "move")
        self.assertEqual(args.task_id, "TASK-001")
        self.assertEqual(args.status, "done")
        self.assertTrue(args.force)
    
    def test_branch_create_parsing(self):
        """Test branch create argument parsing."""
        args = self.parser.parse_args([
            "branch", "create", "feature-x",
            "--parent", "develop",
            "--task-id", "TASK-001"
        ])
        self.assertEqual(args.subcommand, "create")
        self.assertEqual(args.branch_name, "feature-x")
        self.assertEqual(args.parent, "develop")
        self.assertEqual(args.task_id, "TASK-001")
    
    def test_commit_parsing(self):
        """Test commit argument parsing."""
        args = self.parser.parse_args([
            "commit", "TASK-001", "agent-1", "Test commit", "file1.py", "file2.py"
        ])
        self.assertEqual(args.task_id, "TASK-001")
        self.assertEqual(args.agent_id, "agent-1")
        self.assertEqual(args.rationale, "Test commit")
        self.assertEqual(args.files, ["file1.py", "file2.py"])
    
    def test_merge_parsing(self):
        """Test merge argument parsing."""
        args = self.parser.parse_args([
            "merge", "abc123",
            "--source-branch", "feature",
            "--target-branch", "main",
            "--auto-resolve"
        ])
        self.assertEqual(args.commit_id, "abc123")
        self.assertEqual(args.source_branch, "feature")
        self.assertEqual(args.target_branch, "main")
        self.assertTrue(args.auto_resolve)
    
    def test_diff_parsing(self):
        """Test diff argument parsing."""
        args = self.parser.parse_args(["diff", "diff", "abc123", "def456", "--side-by-side"])
        self.assertEqual(args.subcommand, "diff")
        self.assertEqual(args.commit_a, "abc123")
        self.assertEqual(args.commit_b, "def456")
        self.assertTrue(args.side_by_side)
    
    def test_conflict_parsing(self):
        """Test conflict argument parsing."""
        args = self.parser.parse_args([
            "conflict", "resolve", "conflict-123", "--strategy", "ours"
        ])
        self.assertEqual(args.subcommand, "resolve")
        self.assertEqual(args.conflict_id, "conflict-123")
        self.assertEqual(args.strategy, "ours")
    
    def test_rollback_parsing(self):
        """Test rollback argument parsing."""
        args = self.parser.parse_args([
            "rollback", "reset", "abc123", "--hard", "--branch", "main"
        ])
        self.assertEqual(args.subcommand, "reset")
        self.assertEqual(args.commit_id, "abc123")
        self.assertTrue(args.hard)
        self.assertEqual(args.branch, "main")
    
    def test_wip_parsing(self):
        """Test wip argument parsing."""
        args = self.parser.parse_args([
            "wip", "claim", "myfile.py", "--task", "TASK-001", "--agent", "agent-1"
        ])
        self.assertEqual(args.subcommand, "claim")
        self.assertEqual(args.file, "myfile.py")
        self.assertEqual(args.task, "TASK-001")
        self.assertEqual(args.agent, "agent-1")
    
    def test_status_parsing(self):
        """Test status argument parsing."""
        args = self.parser.parse_args(["status", "--tasks", "--json"])
        self.assertTrue(args.tasks)
        self.assertTrue(args.json)
    
    def test_agent_parsing(self):
        """Test agent argument parsing."""
        args = self.parser.parse_args(["agent", "create", "Test Agent", "agent@test.com"])
        self.assertEqual(args.subcommand, "create")
        self.assertEqual(args.name, "Test Agent")
        self.assertEqual(args.email, "agent@test.com")


class TestCommandRouting(unittest.TestCase):
    """Test command routing."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.parser = create_parser()
        self.orig_argv = sys.argv
    
    def tearDown(self):
        sys.argv = self.orig_argv
        shutil.rmtree(self.temp_dir)
    
    @patch('avcpm_cli.list_tasks')
    def test_task_list_routing(self, mock_list):
        """Test task list command routing."""
        sys.argv = ['avcpm', '--base-dir', self.temp_dir, 'task', 'list']
        try:
            main()
        except SystemExit:
            pass
        mock_list.assert_called_once()
    
    @patch('avcpm_cli.create_branch')
    def test_branch_create_routing(self, mock_create):
        """Test branch create command routing."""
        sys.argv = ['avcpm', '--base-dir', self.temp_dir, 'branch', 'create', 'feature']
        try:
            main()
        except SystemExit:
            pass
        mock_create.assert_called_once()
    
    @patch('avcpm_cli.list_agents')
    def test_agent_list_routing(self, mock_list):
        """Test agent list command routing."""
        sys.argv = ['avcpm', '--base-dir', self.temp_dir, 'agent', 'list']
        try:
            main()
        except SystemExit:
            pass
        mock_list.assert_called_once()


class TestHelpSystem(unittest.TestCase):
    """Test help system."""
    
    def setUp(self):
        self.parser = create_parser()
    
    def test_main_help(self):
        """Test main help output."""
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            with self.assertRaises(SystemExit) as cm:
                self.parser.parse_args([])
            output = fake_stdout.getvalue()
            self.assertIn("AVCPM Unified CLI", output)
            self.assertEqual(cm.exception.code, 2)
    
    def test_task_help(self):
        """Test task help output."""
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            with self.assertRaises(SystemExit) as cm:
                self.parser.parse_args(["task", "-h"])
            output = fake_stdout.getvalue()
            self.assertIn("Task management", output)
            self.assertEqual(cm.exception.code, 0)
    
    def test_branch_help(self):
        """Test branch help output."""
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            with self.assertRaises(SystemExit) as cm:
                self.parser.parse_args(["branch", "-h"])
            output = fake_stdout.getvalue()
            self.assertIn("Branch management", output)
            self.assertEqual(cm.exception.code, 0)


class TestErrorHandling(unittest.TestCase):
    """Test error handling."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.parser = create_parser()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_missing_subcommand(self, mock_stderr):
        """Test error for missing subcommand."""
        args = self.parser.parse_args(["task"])
        args.base_dir = self.temp_dir
        with self.assertRaises(SystemExit) as cm:
            task_command(args)
        self.assertEqual(cm.exception.code, 1)
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_invalid_task_move_status(self, mock_stderr):
        """Test error for invalid task move status."""
        # This is handled by argparse choices, so the parsing should fail
        with self.assertRaises(SystemExit) as cm:
            self.parser.parse_args(["task", "move", "TASK-001", "invalid-status"])
        self.assertEqual(cm.exception.code, 2)


class TestIntegration(unittest.TestCase):
    """Integration tests with actual AVCPM modules."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.temp_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        self.orig_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_task_workflow(self):
        """Test full task workflow."""
        # Create task
        from avcpm_task import create_task, list_tasks, get_task_status
        create_task("TEST-001", "Test task", "tester", None, self.base_dir)
        
        status = get_task_status("TEST-001", self.base_dir)
        self.assertEqual(status, "todo")
        
        # Move task
        from avcpm_task import move_task
        move_task("TEST-001", "in-progress", False, self.base_dir)
        
        status = get_task_status("TEST-001", self.base_dir)
        self.assertEqual(status, "in-progress")
    
    def test_branch_workflow(self):
        """Test full branch workflow."""
        from avcpm_branch import create_branch, list_branches, get_current_branch
        
        # Create branch
        create_branch("feature-test", "main", None, None, self.base_dir)
        
        branches = list_branches(self.base_dir)
        branch_names = [b["name"] for b in branches]
        self.assertIn("feature-test", branch_names)
        
        # Switch branch
        from avcpm_branch import switch_branch
        switch_branch("feature-test", self.base_dir)
        
        current = get_current_branch(self.base_dir)
        self.assertEqual(current, "feature-test")
    
    def test_agent_workflow(self):
        """Test agent workflow."""
        from avcpm_agent import create_agent, list_agents, get_agent
        
        # Create agent
        agent = create_agent("Test Agent", "test@example.com", self.base_dir)
        self.assertIn("agent_id", agent)
        
        # List agents
        agents = list_agents(self.base_dir)
        self.assertIn(agent["agent_id"], agents)
        
        # Get agent
        retrieved = get_agent(agent["agent_id"], self.base_dir)
        self.assertEqual(retrieved["name"], "Test Agent")


class TestGlobalOptions(unittest.TestCase):
    """Test global options work correctly."""
    
    def test_version_output(self):
        """Test version output."""
        self.assertEqual(__version__, "3.0.0")
    
    def test_base_dir_propagation(self):
        """Test base-dir propagates to commands."""
        parser = create_parser()
        args = parser.parse_args(["--base-dir", "/custom/path", "task", "list"])
        self.assertEqual(args.base_dir, "/custom/path")
        self.assertEqual(args.command, "task")


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCLIConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestCLIParser))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandRouting))
    suite.addTests(loader.loadTestsFromTestCase(TestHelpSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestGlobalOptions))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
