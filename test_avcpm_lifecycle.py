"""
Tests for AVCPM Task Lifecycle Management

Converted from unittest.TestCase to pytest fixtures.
Run with: python -m pytest test_avcpm_lifecycle.py -v
"""

import os
import sys
import json
import shutil
from datetime import datetime

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from avcpm_lifecycle import (
    # Configuration
    load_lifecycle_config, save_lifecycle_config, get_default_lifecycle_config,
    get_task_type_config, init_lifecycle_config,
    # Status management
    transition_task, get_task_commits, record_task_commit, is_first_commit,
    # Validation
    validate_commit_allowed, validate_merge_allowed,
    # Hooks
    on_commit, on_merge, on_review,
    # CLI
    cmd_status, cmd_transitions, cmd_validate,
    # Constants
    VALID_TRANSITIONS, AUTO_TRANSITIONS
)
from avcpm_task import (
    create_task, load_task, get_task_status, save_task,
    add_dependency, COLUMNS
)
from avcpm_agent import create_agent


# ----- Fixtures -----

@pytest.fixture
def lifecycle_env(tmp_avcpm_dir, mock_agent):
    """Set up lifecycle test environment with agent and initialized config."""
    # Create task directories
    tasks_dir = os.path.join(tmp_avcpm_dir, "tasks")
    for col in COLUMNS:
        os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
    
    # Init lifecycle config
    init_lifecycle_config(tmp_avcpm_dir)
    
    return {
        "base_dir": tmp_avcpm_dir,
        "agent": mock_agent,
        "agent_id": mock_agent["agent_id"]
    }


@pytest.fixture
def lifecycle_env_with_tasks(tmp_avcpm_dir, mock_agent):
    """Set up environment with task created."""
    env = lifecycle_env(tmp_avcpm_dir, mock_agent)
    
    # Create test task
    create_task("TASK-001", "Test task", base_dir=tmp_avcpm_dir)
    
    return env


# ----- Test Lifecycle Configuration -----

class TestLifecycleConfig:
    """Test lifecycle configuration management."""
    
    def test_default_config_structure(self):
        """Test default configuration has expected structure."""
        config = get_default_lifecycle_config()
        
        assert "version" in config
        assert "enabled" in config
        assert "task_types" in config
        assert "manual_override" in config
        
        # Check default task type
        assert "default" in config["task_types"]
        default = config["task_types"]["default"]
        
        assert "auto_transitions" in default
        assert "require_assignee_match" in default
        assert "require_dependencies_complete" in default
        assert "require_review_approval" in default
    
    def test_init_lifecycle_config(self, tmp_avcpm_dir):
        """Test initialization of lifecycle config."""
        result = init_lifecycle_config(tmp_avcpm_dir)
        assert result is True
        
        config_path = os.path.join(tmp_avcpm_dir, "lifecycle.json")
        assert os.path.exists(config_path)
        
        # Second init should return False
        result = init_lifecycle_config(tmp_avcpm_dir)
        assert result is False
    
    def test_load_and_save_config(self, tmp_avcpm_dir):
        """Test loading and saving configuration."""
        # First init
        init_lifecycle_config(tmp_avcpm_dir)
        
        config = load_lifecycle_config(tmp_avcpm_dir)
        assert config["enabled"] is True
        
        # Modify and save
        config["enabled"] = False
        save_lifecycle_config(config, tmp_avcpm_dir)
        
        # Reload
        config = load_lifecycle_config(tmp_avcpm_dir)
        assert config["enabled"] is False
    
    def test_get_task_type_config(self, tmp_avcpm_dir):
        """Test getting task type specific configuration."""
        init_lifecycle_config(tmp_avcpm_dir)
        
        default_config = get_task_type_config("default", tmp_avcpm_dir)
        assert default_config["auto_transitions"]["on_first_commit"] is True
        
        hotfix_config = get_task_type_config("hotfix", tmp_avcpm_dir)
        assert hotfix_config["require_assignee_match"] is False
        
        unknown_config = get_task_type_config("unknown", tmp_avcpm_dir)
        assert unknown_config == default_config


# ----- Test Status Transitions -----

class TestStatusTransitions:
    """Test task status transitions."""
    
    def test_valid_transitions(self, lifecycle_env):
        """Test valid status transitions."""
        base_dir = lifecycle_env["base_dir"]
        
        # Create task
        create_task("TASK-001", "Test task", base_dir=base_dir)
        
        # todo -> in-progress
        success, msg = transition_task("TASK-001", "in-progress", base_dir=base_dir)
        assert success, msg
        assert get_task_status("TASK-001", base_dir) == "in-progress"
        
        # in-progress -> review
        success, msg = transition_task("TASK-001", "review", base_dir=base_dir)
        assert success, msg
        assert get_task_status("TASK-001", base_dir) == "review"
        
        # review -> done
        success, msg = transition_task("TASK-001", "done", base_dir=base_dir)
        assert success, msg
        assert get_task_status("TASK-001", base_dir) == "done"
    
    def test_invalid_transitions(self, lifecycle_env):
        """Test invalid status transitions are blocked."""
        base_dir = lifecycle_env["base_dir"]
        
        # Create task
        create_task("TASK-001", "Test task", base_dir=base_dir)
        
        # todo -> review (invalid)
        success, msg = transition_task("TASK-001", "review", base_dir=base_dir)
        assert success is False
        assert "Invalid transition" in msg
        
        # todo -> done (invalid)
        success, msg = transition_task("TASK-001", "done", base_dir=base_dir)
        assert success is False
    
    def test_forced_transition(self, lifecycle_env):
        """Test forced transition bypasses validation."""
        base_dir = lifecycle_env["base_dir"]
        
        # Create task
        create_task("TASK-001", "Test task", base_dir=base_dir)
        
        # Force todo -> done
        success, msg = transition_task("TASK-001", "done", 
                                      base_dir=base_dir, force=True)
        assert success
        assert get_task_status("TASK-001", base_dir) == "done"
    
    def test_transition_records_history(self, lifecycle_env):
        """Test transitions record status history."""
        base_dir = lifecycle_env["base_dir"]
        
        # Create task
        create_task("TASK-001", "Test task", base_dir=base_dir)
        
        # Transition
        transition_task("TASK-001", "in-progress", 
                       "Starting work", base_dir=base_dir)
        
        task_data = load_task("TASK-001", base_dir)
        history = task_data.get("status_history", [])
        
        assert len(history) == 2  # created + transitioned
        assert history[1]["status"] == "in-progress"
        assert history[1]["reason"] == "Starting work"


# ----- Test Validation Rules -----

class TestValidationRules:
    """Test validation rules for commits and merges."""
    
    @pytest.fixture
    def validation_env(self, tmp_avcpm_dir, mock_agent):
        """Set up environment for validation tests."""
        # Create task directories
        tasks_dir = os.path.join(tmp_avcpm_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory
        agents_dir = os.path.join(tmp_avcpm_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # Init lifecycle config
        init_lifecycle_config(tmp_avcpm_dir)
        
        return {
            "base_dir": tmp_avcpm_dir,
            "agent_id": mock_agent["agent_id"]
        }
    
    def test_validate_task_exists(self, validation_env):
        """Test validation fails for non-existent task."""
        allowed, msg = validate_commit_allowed("NONEXISTENT", validation_env["agent_id"], validation_env["base_dir"])
        assert allowed is False
        assert "not found" in msg
    
    def test_validate_assignee_match(self, validation_env):
        """Test commit blocked if not assigned to agent."""
        # Create task assigned to someone else
        create_task("TASK-001", "Test task", assignee="other_agent",
                   base_dir=validation_env["base_dir"])
        
        allowed, msg = validate_commit_allowed("TASK-001", validation_env["agent_id"], validation_env["base_dir"])
        assert allowed is False
        assert "assigned to" in msg
    
    def test_validate_assignee_match_unassigned(self, validation_env):
        """Test commit allowed for unassigned task."""
        create_task("TASK-002", "Test task", assignee="unassigned",
                   base_dir=validation_env["base_dir"])
        
        allowed, msg = validate_commit_allowed("TASK-002", validation_env["agent_id"], validation_env["base_dir"])
        assert allowed is True
    
    def test_validate_dependencies_complete(self, validation_env):
        """Test commit blocked if dependencies incomplete."""
        base_dir = validation_env["base_dir"]
        
        # Create dependency task
        create_task("DEP-001", "Dependency task", base_dir=base_dir)
        
        # Create task depending on it
        create_task("TASK-003", "Test task", 
                   depends_on="DEP-001", base_dir=base_dir)
        
        # Move task to in-progress (force to bypass dependency check in move_task)
        from avcpm_task import move_task
        move_task("TASK-003", "in-progress", force=True, base_dir=base_dir)
        
        allowed, msg = validate_commit_allowed("TASK-003", validation_env["agent_id"], base_dir)
        assert allowed is False
        assert "incomplete dependencies" in msg
    
    def test_validate_dependencies_complete_when_done(self, validation_env):
        """Test commit allowed when dependencies are complete."""
        base_dir = validation_env["base_dir"]
        
        # Create and complete dependency
        create_task("DEP-002", "Dependency task", base_dir=base_dir)
        from avcpm_task import move_task
        move_task("DEP-002", "done", base_dir=base_dir)
        
        # Create task depending on it
        create_task("TASK-004", "Test task",
                   depends_on="DEP-002", base_dir=base_dir)
        move_task("TASK-004", "in-progress", base_dir=base_dir)
        
        allowed, msg = validate_commit_allowed("TASK-004", validation_env["agent_id"], base_dir)
        assert allowed is True
    
    def test_validate_merge_no_review(self, validation_env):
        """Test merge blocked without review."""
        base_dir = validation_env["base_dir"]
        
        create_task("TASK-005", "Test task", base_dir=base_dir)
        
        allowed, msg = validate_merge_allowed("TASK-005", "commit-001", base_dir)
        assert allowed is False
        assert "No review found" in msg
    
    def test_validate_merge_not_approved(self, validation_env):
        """Test merge blocked if review not approved."""
        base_dir = validation_env["base_dir"]
        
        create_task("TASK-006", "Test task", base_dir=base_dir)
        
        # Create review file (not approved)
        reviews_dir = os.path.join(base_dir, "reviews")
        os.makedirs(reviews_dir, exist_ok=True)
        with open(os.path.join(reviews_dir, "commit-002.review"), "w") as f:
            f.write("Task: TASK-006\nStatus: PENDING")
        
        allowed, msg = validate_merge_allowed("TASK-006", "commit-002", base_dir)
        assert allowed is False
        assert "not approved" in msg
    
    def test_validate_merge_approved(self, validation_env):
        """Test merge allowed with approved review."""
        base_dir = validation_env["base_dir"]
        
        create_task("TASK-007", "Test task", base_dir=base_dir)
        
        # Create approved review file
        reviews_dir = os.path.join(base_dir, "reviews")
        os.makedirs(reviews_dir, exist_ok=True)
        with open(os.path.join(reviews_dir, "commit-003.review"), "w") as f:
            f.write("Task: TASK-007\nStatus: APPROVED")
        
        allowed, msg = validate_merge_allowed("TASK-007", "commit-003", base_dir)
        assert allowed is True


# ----- Test Auto Transitions -----

class TestAutoTransitions:
    """Test automatic status transitions."""
    
    @pytest.fixture
    def auto_trans_env(self, tmp_avcpm_dir, mock_agent):
        """Set up environment for auto-transition tests."""
        # Create task directories
        tasks_dir = os.path.join(tmp_avcpm_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory
        agents_dir = os.path.join(tmp_avcpm_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # Init lifecycle config
        init_lifecycle_config(tmp_avcpm_dir)
        
        return {
            "base_dir": tmp_avcpm_dir,
            "agent_id": mock_agent["agent_id"]
        }
    
    def test_on_first_commit_transition(self, auto_trans_env):
        """Test todo -> in-progress on first commit."""
        base_dir = auto_trans_env["base_dir"]
        agent_id = auto_trans_env["agent_id"]
        
        create_task("TASK-001", "Test task", base_dir=base_dir)
        
        assert get_task_status("TASK-001", base_dir) == "todo"
        
        success, msg = on_commit("TASK-001", "commit-001", agent_id, base_dir)
        assert success
        
        assert get_task_status("TASK-001", base_dir) == "in-progress"
        assert "in-progress" in msg
    
    def test_on_commit_transition_to_review(self, auto_trans_env):
        """Test in-progress -> review on subsequent commit."""
        base_dir = auto_trans_env["base_dir"]
        agent_id = auto_trans_env["agent_id"]
        
        create_task("TASK-002", "Test task", base_dir=base_dir)
        
        # First commit - moves to in-progress
        on_commit("TASK-002", "commit-001", agent_id, base_dir)
        assert get_task_status("TASK-002", base_dir) == "in-progress"
        
        # Second commit - should move to review
        success, msg = on_commit("TASK-002", "commit-002", agent_id, base_dir)
        assert success
        
        assert get_task_status("TASK-002", base_dir) == "review"
        assert "review" in msg
    
    def test_on_commit_blocked_by_dependencies(self, auto_trans_env):
        """Test commit records but doesn't transition if blocked."""
        base_dir = auto_trans_env["base_dir"]
        agent_id = auto_trans_env["agent_id"]
        
        # Create dependency
        create_task("DEP-001", "Dependency", base_dir=base_dir)
        
        # Create task with dependency
        create_task("TASK-003", "Test task", depends_on="DEP-001", base_dir=base_dir)
        
        # Move to in-progress with force (bypassing dependency check)
        from avcpm_task import move_task
        move_task("TASK-003", "in-progress", force=True, base_dir=base_dir)
        
        # Commit should record but not transition (blocked by deps)
        success, msg = on_commit("TASK-003", "commit-001", agent_id, base_dir)
        assert success
        
        # Status should still be in-progress
        assert get_task_status("TASK-003", base_dir) == "in-progress"
        assert "blocked by dependencies" in msg
    
    def test_on_merge_approval_transition(self, auto_trans_env):
        """Test review -> done on merge approval."""
        base_dir = auto_trans_env["base_dir"]
        agent_id = auto_trans_env["agent_id"]
        
        create_task("TASK-004", "Test task", base_dir=base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-004", "review", base_dir=base_dir)
        
        # Create approved review
        reviews_dir = os.path.join(base_dir, "reviews")
        os.makedirs(reviews_dir, exist_ok=True)
        with open(os.path.join(reviews_dir, "commit-001.review"), "w") as f:
            f.write("Task: TASK-004\nStatus: APPROVED")
        
        success, msg = on_merge("TASK-004", "commit-001", agent_id, base_dir)
        assert success
        
        assert get_task_status("TASK-004", base_dir) == "done"
        assert "done" in msg
    
    def test_on_review_approved_transition(self, auto_trans_env):
        """Test review -> done on review approval."""
        base_dir = auto_trans_env["base_dir"]
        
        create_task("TASK-005", "Test task", base_dir=base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-005", "review", base_dir=base_dir)
        
        success, msg = on_review("TASK-005", "approved", base_dir)
        assert success
        
        assert get_task_status("TASK-005", base_dir) == "done"
    
    def test_on_review_rejected_transition(self, auto_trans_env):
        """Test review -> in-progress on review rejection."""
        base_dir = auto_trans_env["base_dir"]
        
        create_task("TASK-006", "Test task", base_dir=base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-006", "review", base_dir=base_dir)
        
        success, msg = on_review("TASK-006", "rejected", base_dir)
        assert success
        
        assert get_task_status("TASK-006", base_dir) == "in-progress"
    
    def test_commit_history_tracking(self, auto_trans_env):
        """Test commits are recorded for a task."""
        base_dir = auto_trans_env["base_dir"]
        agent_id = auto_trans_env["agent_id"]
        
        create_task("TASK-007", "Test task", base_dir=base_dir)
        
        # Initially no commits
        assert len(get_task_commits("TASK-007", base_dir)) == 0
        assert is_first_commit("TASK-007", base_dir) is True
        
        # First commit
        on_commit("TASK-007", "commit-001", agent_id, base_dir)
        
        commits = get_task_commits("TASK-007", base_dir)
        assert len(commits) == 1
        assert commits[0]["commit_id"] == "commit-001"
        assert commits[0]["agent_id"] == agent_id
        
        # No longer first commit
        assert is_first_commit("TASK-007", base_dir) is False


# ----- Test Task Type Config -----

class TestTaskTypeConfig:
    """Test per-task-type configuration."""
    
    @pytest.fixture
    def task_type_env(self, tmp_avcpm_dir, mock_agent):
        """Set up environment for task type tests."""
        # Create task directories
        tasks_dir = os.path.join(tmp_avcpm_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory
        agents_dir = os.path.join(tmp_avcpm_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # Init lifecycle config
        init_lifecycle_config(tmp_avcpm_dir)
        
        return {
            "base_dir": tmp_avcpm_dir,
            "agent_id": mock_agent["agent_id"]
        }
    
    def test_hotfix_bypasses_assignee_check(self, task_type_env):
        """Test hotfix tasks can bypass assignee validation."""
        base_dir = task_type_env["base_dir"]
        agent_id = task_type_env["agent_id"]
        
        # Create task assigned to someone else
        create_task("TASK-001", "Hotfix task", assignee="other_agent",
                   base_dir=base_dir)
        
        # Set task type to hotfix
        task_data = load_task("TASK-001", base_dir)
        task_data["type"] = "hotfix"
        save_task("TASK-001", task_data, base_dir=base_dir)
        
        # Should pass validation for hotfix
        allowed, msg = validate_commit_allowed("TASK-001", agent_id, base_dir)
        assert allowed, msg
    
    def test_hotfix_bypasses_deps_check(self, task_type_env):
        """Test hotfix tasks can bypass dependencies validation."""
        base_dir = task_type_env["base_dir"]
        agent_id = task_type_env["agent_id"]
        
        # Create incomplete dependency
        create_task("DEP-001", "Dependency", base_dir=base_dir)
        
        # Create hotfix task with dependency
        create_task("TASK-002", "Hotfix task", depends_on="DEP-001",
                   base_dir=base_dir)
        
        # Set task type to hotfix
        task_data = load_task("TASK-002", base_dir)
        task_data["type"] = "hotfix"
        save_task("TASK-002", task_data, base_dir=base_dir)
        
        # Move to in-progress (force to bypass dependency check in move_task)
        from avcpm_task import move_task
        move_task("TASK-002", "in-progress", force=True, base_dir=base_dir)
        
        # Should pass validation
        allowed, msg = validate_commit_allowed("TASK-002", agent_id, base_dir)
        assert allowed, msg
    
    def test_disabled_auto_transition(self, task_type_env):
        """Test auto-transitions can be disabled per task type."""
        base_dir = task_type_env["base_dir"]
        agent_id = task_type_env["agent_id"]
        
        # Modify config to disable first commit transition
        config = load_lifecycle_config(base_dir)
        config["task_types"]["default"]["auto_transitions"]["on_first_commit"] = False
        save_lifecycle_config(config, base_dir)
        
        create_task("TASK-003", "Test task", base_dir=base_dir)
        
        # Commit should record but not transition
        success, msg = on_commit("TASK-003", "commit-001", agent_id, base_dir)
        assert success
        
        # Should still be todo
        assert get_task_status("TASK-003", base_dir) == "todo"
        assert "disabled" in msg


# ----- Test CLI Commands -----

class TestCLICommands:
    """Test CLI commands."""
    
    @pytest.fixture
    def cli_env(self, tmp_avcpm_dir, mock_agent):
        """Set up environment for CLI tests."""
        # Create task directories
        tasks_dir = os.path.join(tmp_avcpm_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory
        agents_dir = os.path.join(tmp_avcpm_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # Init lifecycle config
        init_lifecycle_config(tmp_avcpm_dir)
        
        # Create test task
        create_task("TASK-001", "Test task description", 
                   assignee=mock_agent["agent_id"], base_dir=tmp_avcpm_dir)
        
        return {
            "base_dir": tmp_avcpm_dir,
            "agent_id": mock_agent["agent_id"]
        }
    
    def test_status_command(self, cli_env):
        """Test status command output."""
        base_dir = cli_env["base_dir"]
        agent_id = cli_env["agent_id"]
        
        output = cmd_status("TASK-001", base_dir)
        
        assert "TASK-001" in output
        assert "todo" in output
        assert "Test task description" in output
        assert agent_id in output
    
    def test_status_command_not_found(self, cli_env):
        """Test status command for non-existent task."""
        output = cmd_status("NONEXISTENT", cli_env["base_dir"])
        assert "not found" in output
    
    def test_transitions_command(self, cli_env):
        """Test transitions command output."""
        base_dir = cli_env["base_dir"]
        
        output = cmd_transitions("TASK-001", base_dir)
        
        assert "TASK-001" in output
        assert "todo" in output
        assert "Auto-Transition Settings" in output
        assert "todo -> in-progress" in output
    
    def test_validate_commit_command(self, cli_env):
        """Test validate command for commit action."""
        base_dir = cli_env["base_dir"]
        agent_id = cli_env["agent_id"]
        
        output = cmd_validate("TASK-001", "commit", agent_id, base_dir)
        
        assert "PASS" in output
        assert "Assignee" in output
        assert agent_id in output
    
    def test_validate_merge_command_no_review(self, cli_env):
        """Test validate command for merge without review."""
        base_dir = cli_env["base_dir"]
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-001", "review", base_dir=base_dir)
        
        output = cmd_validate("TASK-001", "merge", base_dir=base_dir)
        
        assert "FAIL" in output
        assert "No review found" in output


# ----- Test Integration -----

class TestIntegration:
    """Integration tests for the full lifecycle workflow."""
    
    @pytest.fixture
    def integration_env(self, tmp_avcpm_dir, mock_agent):
        """Set up environment for integration tests."""
        # Create task directories
        tasks_dir = os.path.join(tmp_avcpm_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory
        agents_dir = os.path.join(tmp_avcpm_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # Create reviews directory
        os.makedirs(os.path.join(tmp_avcpm_dir, "reviews"), exist_ok=True)
        
        # Init lifecycle config
        init_lifecycle_config(tmp_avcpm_dir)
        
        return {
            "base_dir": tmp_avcpm_dir,
            "agent_id": mock_agent["agent_id"]
        }
    
    def test_full_lifecycle_workflow(self, integration_env):
        """Test complete task lifecycle from todo to done."""
        base_dir = integration_env["base_dir"]
        agent_id = integration_env["agent_id"]
        
        # 1. Create task
        create_task("TASK-FULL", "Full lifecycle task",
                   assignee=agent_id, base_dir=base_dir)
        assert get_task_status("TASK-FULL", base_dir) == "todo"
        
        # 2. First commit - should auto-transition to in-progress
        success, msg = on_commit("TASK-FULL", "commit-001", agent_id, base_dir)
        assert success, msg
        assert get_task_status("TASK-FULL", base_dir) == "in-progress"
        
        # 3. Subsequent commit - should auto-transition to review
        success, msg = on_commit("TASK-FULL", "commit-002", agent_id, base_dir)
        assert success, msg
        assert get_task_status("TASK-FULL", base_dir) == "review"
        
        # 4. Create approved review
        with open(os.path.join(base_dir, "reviews", "commit-002.review"), "w") as f:
            f.write("Task: TASK-FULL\nStatus: APPROVED\nReviewer: reviewer1")
        
        # 5. Merge - should auto-transition to done
        success, msg = on_merge("TASK-FULL", "commit-002", agent_id, base_dir)
        assert success, msg
        assert get_task_status("TASK-FULL", base_dir) == "done"
        
        # 6. Verify commit history
        commits = get_task_commits("TASK-FULL", base_dir)
        assert len(commits) == 2
        
        # 7. Verify status history
        task_data = load_task("TASK-FULL", base_dir)
        history = task_data.get("status_history", [])
        statuses = [h["status"] for h in history]
        assert "todo" in statuses
        assert "in-progress" in statuses
        assert "review" in statuses
        assert "done" in statuses
    
    def test_rejected_review_workflow(self, integration_env):
        """Test workflow with rejected review."""
        base_dir = integration_env["base_dir"]
        
        # Create task
        create_task("TASK-REJ", "Rejected review task",
                   assignee=integration_env["agent_id"], base_dir=base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-REJ", "review", base_dir=base_dir)
        
        # Review rejected - should transition to in-progress
        success, msg = on_review("TASK-REJ", "rejected", base_dir)
        assert success, msg
        assert get_task_status("TASK-REJ", base_dir) == "in-progress"
    
    def test_blocked_merge_without_approval(self, integration_env):
        """Test merge blocked without approval."""
        base_dir = integration_env["base_dir"]
        agent_id = integration_env["agent_id"]
        
        # Create task
        create_task("TASK-BLOCK", "Blocked merge task",
                   assignee=agent_id, base_dir=base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-BLOCK", "review", base_dir=base_dir)
        
        # Try to merge without approval
        success, msg = on_merge("TASK-BLOCK", "commit-001", agent_id, base_dir)
        assert success is False
        assert "No review found" in msg
        assert get_task_status("TASK-BLOCK", base_dir) == "review"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])