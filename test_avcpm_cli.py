#!/usr/bin/env python3
"""
Tests for AVCPM Unified CLI.

Converted from unittest.TestCase to pytest fixtures (M-T5).
Run with: pytest test_avcpm_cli.py -v
"""

import os
import sys
import json
import shutil
import tempfile
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from avcpm_cli import (
    load_config, get_base_dir, create_parser, main,
    task_command, branch_command, agent_command,
    __version__
)


class TestCLIConfiguration:
    """Test configuration loading."""

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from file."""
        config_path = str(tmp_path / "config.json")
        config_data = {"base_dir": "/custom/path", "verbose": True}
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        config = load_config(config_path)
        assert config["base_dir"] == "/custom/path"
        assert config["verbose"] is True

    def test_load_config_nonexistent(self):
        """Test loading config when file doesn't exist."""
        config = load_config("/nonexistent/config.json")
        assert config == {}

    def test_load_config_invalid_json(self, tmp_path):
        """Test loading config with invalid JSON."""
        config_path = str(tmp_path / "config.json")
        with open(config_path, 'w') as f:
            f.write("invalid json")

        config = load_config(config_path)
        assert config == {}


class TestCLIParser:
    """Test CLI argument parsing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = create_parser()

    def test_version_flag(self):
        """Test --version flag."""
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_global_base_dir(self):
        args = self.parser.parse_args(["--base-dir", "/custom", "task", "list"])
        assert args.base_dir == "/custom"

    def test_global_verbose(self):
        args = self.parser.parse_args(["--verbose", "task", "list"])
        assert args.verbose is True

    def test_task_create_parsing(self):
        args = self.parser.parse_args(["task", "create", "TASK-001", "Test description"])
        assert args.command == "task"
        assert args.subcommand == "create"
        assert args.task_id == "TASK-001"
        assert args.description == "Test description"

    def test_task_move_parsing(self):
        args = self.parser.parse_args(["task", "move", "TASK-001", "done", "--force"])
        assert args.subcommand == "move"
        assert args.task_id == "TASK-001"
        assert args.status == "done"
        assert args.force is True

    def test_branch_create_parsing(self):
        args = self.parser.parse_args([
            "branch", "create", "feature-x",
            "--parent", "develop",
            "--task-id", "TASK-001"
        ])
        assert args.subcommand == "create"
        assert args.branch_name == "feature-x"
        assert args.parent == "develop"
        assert args.task_id == "TASK-001"

    def test_commit_parsing(self):
        args = self.parser.parse_args([
            "commit", "TASK-001", "agent-1", "Test commit", "file1.py", "file2.py"
        ])
        assert args.task_id == "TASK-001"
        assert args.agent_id == "agent-1"
        assert args.rationale == "Test commit"
        assert args.files == ["file1.py", "file2.py"]

    def test_merge_parsing(self):
        args = self.parser.parse_args([
            "merge", "abc123",
            "--source-branch", "feature",
            "--target-branch", "main",
            "--auto-resolve"
        ])
        assert args.commit_id == "abc123"
        assert args.source_branch == "feature"
        assert args.target_branch == "main"
        assert args.auto_resolve is True

    def test_diff_parsing(self):
        args = self.parser.parse_args(["diff", "diff", "abc123", "def456", "--side-by-side"])
        assert args.subcommand == "diff"
        assert args.commit_a == "abc123"
        assert args.commit_b == "def456"
        assert args.side_by_side is True

    def test_conflict_parsing(self):
        args = self.parser.parse_args([
            "conflict", "resolve", "conflict-123", "--strategy", "ours"
        ])
        assert args.subcommand == "resolve"
        assert args.conflict_id == "conflict-123"
        assert args.strategy == "ours"

    def test_rollback_parsing(self):
        args = self.parser.parse_args([
            "rollback", "reset", "abc123", "--hard", "--branch", "main"
        ])
        assert args.subcommand == "reset"
        assert args.commit_id == "abc123"
        assert args.hard is True
        assert args.branch == "main"

    def test_wip_parsing(self):
        args = self.parser.parse_args([
            "wip", "claim", "myfile.py", "--task", "TASK-001", "--agent", "agent-1"
        ])
        assert args.subcommand == "claim"
        assert args.file == "myfile.py"
        assert args.task == "TASK-001"
        assert args.agent == "agent-1"

    def test_status_parsing(self):
        args = self.parser.parse_args(["status", "--tasks", "--json"])
        assert args.tasks is True
        assert args.json is True

    def test_agent_parsing(self):
        args = self.parser.parse_args(["agent", "create", "Test Agent", "agent@test.com"])
        assert args.subcommand == "create"
        assert args.name == "Test Agent"
        assert args.email == "agent@test.com"


class TestCommandRouting:
    """Test command routing."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.temp_dir = str(tmp_path)
        self.orig_argv = sys.argv
        yield
        sys.argv = self.orig_argv

    @patch('avcpm_cli.list_tasks')
    def test_task_list_routing(self, mock_list):
        sys.argv = ['avcpm', '--base-dir', self.temp_dir, 'task', 'list']
        try:
            main()
        except SystemExit:
            pass
        mock_list.assert_called_once()

    @patch('avcpm_cli.create_branch')
    def test_branch_create_routing(self, mock_create):
        sys.argv = ['avcpm', '--base-dir', self.temp_dir, 'branch', 'create', 'feature']
        try:
            main()
        except SystemExit:
            pass
        mock_create.assert_called_once()

    @patch('avcpm_cli.list_agents')
    def test_agent_list_routing(self, mock_list):
        sys.argv = ['avcpm', '--base-dir', self.temp_dir, 'agent', 'list']
        try:
            main()
        except SystemExit:
            pass
        mock_list.assert_called_once()


class TestHelpSystem:
    """Test help system."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = create_parser()

    def test_main_help(self):
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args([])
        assert exc_info.value.code == 2

    def test_task_help(self):
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args(["task", "-h"])
        assert exc_info.value.code == 0

    def test_branch_help(self):
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args(["branch", "-h"])
        assert exc_info.value.code == 0


class TestErrorHandling:
    """Test error handling."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.temp_dir = str(tmp_path)
        self.parser = create_parser()

    def test_missing_subcommand(self):
        args = self.parser.parse_args(["task"])
        args.base_dir = self.temp_dir
        with pytest.raises(SystemExit) as exc_info:
            task_command(args)
        assert exc_info.value.code == 1

    def test_invalid_task_move_status(self):
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args(["task", "move", "TASK-001", "invalid-status"])
        assert exc_info.value.code == 2


class TestIntegration:
    """Integration tests with actual AVCPM modules."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.temp_dir = str(tmp_path)
        self.base_dir = os.path.join(self.temp_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        self.orig_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        yield
        os.chdir(self.orig_cwd)

    def test_task_workflow(self):
        from avcpm_task import create_task, list_tasks, get_task_status
        create_task("TEST-001", "Test task", "tester", None, self.base_dir)

        task_status = get_task_status("TEST-001", self.base_dir)
        assert task_status == "todo"

        from avcpm_task import move_task
        move_task("TEST-001", "in-progress", False, self.base_dir)

        task_status = get_task_status("TEST-001", self.base_dir)
        assert task_status == "in-progress"

    def test_branch_workflow(self):
        from avcpm_branch import create_branch, list_branches, get_current_branch, switch_branch

        create_branch("feature-test", "main", None, None, self.base_dir)

        branches = list_branches(self.base_dir)
        branch_names = [b["name"] for b in branches]
        assert "feature-test" in branch_names

        switch_branch("feature-test", self.base_dir)
        current = get_current_branch(self.base_dir)
        assert current == "feature-test"

    def test_agent_workflow(self):
        from avcpm_agent import create_agent, list_agents, get_agent

        agent_data = create_agent("Test Agent", "test@example.com", self.base_dir)
        assert "agent_id" in agent_data

        agents = list_agents(self.base_dir)
        assert agent_data["agent_id"] in agents

        retrieved = get_agent(agent_data["agent_id"], self.base_dir)
        assert retrieved["name"] == "Test Agent"


class TestGlobalOptions:
    """Test global options work correctly."""

    def test_version_output(self):
        assert __version__ == "3.0.0"

    def test_base_dir_propagation(self):
        parser = create_parser()
        args = parser.parse_args(["--base-dir", "/custom/path", "task", "list"])
        assert args.base_dir == "/custom/path"
        assert args.command == "task"