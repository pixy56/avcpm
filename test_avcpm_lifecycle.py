#!/usr/bin/env python3
"""
Tests for AVCPM Task Lifecycle Management
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


class TestLifecycleConfig(unittest.TestCase):
    """Test lifecycle configuration management."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_default_config_structure(self):
        """Test default configuration has expected structure."""
        config = get_default_lifecycle_config()
        
        self.assertIn("version", config)
        self.assertIn("enabled", config)
        self.assertIn("task_types", config)
        self.assertIn("manual_override", config)
        
        # Check default task type
        self.assertIn("default", config["task_types"])
        default = config["task_types"]["default"]
        
        self.assertIn("auto_transitions", default)
        self.assertIn("require_assignee_match", default)
        self.assertIn("require_dependencies_complete", default)
        self.assertIn("require_review_approval", default)
    
    def test_init_lifecycle_config(self):
        """Test initialization of lifecycle config."""
        result = init_lifecycle_config(self.base_dir)
        self.assertTrue(result)
        
        config_path = os.path.join(self.base_dir, "lifecycle.json")
        self.assertTrue(os.path.exists(config_path))
        
        # Second init should return False
        result = init_lifecycle_config(self.base_dir)
        self.assertFalse(result)
    
    def test_load_and_save_config(self):
        """Test loading and saving configuration."""
        # First init
        init_lifecycle_config(self.base_dir)
        
        config = load_lifecycle_config(self.base_dir)
        self.assertTrue(config["enabled"])
        
        # Modify and save
        config["enabled"] = False
        save_lifecycle_config(config, self.base_dir)
        
        # Reload
        config = load_lifecycle_config(self.base_dir)
        self.assertFalse(config["enabled"])
    
    def test_get_task_type_config(self):
        """Test getting task type specific configuration."""
        init_lifecycle_config(self.base_dir)
        
        default_config = get_task_type_config("default", self.base_dir)
        self.assertTrue(default_config["auto_transitions"]["on_first_commit"])
        
        hotfix_config = get_task_type_config("hotfix", self.base_dir)
        self.assertFalse(hotfix_config["require_assignee_match"])
        
        unknown_config = get_task_type_config("unknown", self.base_dir)
        self.assertEqual(unknown_config, default_config)


class TestStatusTransitions(unittest.TestCase):
    """Test task status transitions."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create task directories
        tasks_dir = os.path.join(self.base_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create test task
        create_task("TASK-001", "Test task", base_dir=self.base_dir)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_valid_transitions(self):
        """Test valid status transitions."""
        # todo -> in-progress
        success, msg = transition_task("TASK-001", "in-progress", base_dir=self.base_dir)
        self.assertTrue(success, msg)
        self.assertEqual(get_task_status("TASK-001", self.base_dir), "in-progress")
        
        # in-progress -> review
        success, msg = transition_task("TASK-001", "review", base_dir=self.base_dir)
        self.assertTrue(success, msg)
        self.assertEqual(get_task_status("TASK-001", self.base_dir), "review")
        
        # review -> done
        success, msg = transition_task("TASK-001", "done", base_dir=self.base_dir)
        self.assertTrue(success, msg)
        self.assertEqual(get_task_status("TASK-001", self.base_dir), "done")
    
    def test_invalid_transitions(self):
        """Test invalid status transitions are blocked."""
        # todo -> review (invalid)
        success, msg = transition_task("TASK-001", "review", base_dir=self.base_dir)
        self.assertFalse(success)
        self.assertIn("Invalid transition", msg)
        
        # todo -> done (invalid)
        success, msg = transition_task("TASK-001", "done", base_dir=self.base_dir)
        self.assertFalse(success)
    
    def test_forced_transition(self):
        """Test forced transition bypasses validation."""
        # Force todo -> done
        success, msg = transition_task("TASK-001", "done", 
                                      base_dir=self.base_dir, force=True)
        self.assertTrue(success)
        self.assertEqual(get_task_status("TASK-001", self.base_dir), "done")
    
    def test_transition_records_history(self):
        """Test transitions record status history."""
        transition_task("TASK-001", "in-progress", 
                       "Starting work", base_dir=self.base_dir)
        
        task_data = load_task("TASK-001", self.base_dir)
        history = task_data.get("status_history", [])
        
        self.assertEqual(len(history), 2)  # created + transitioned
        self.assertEqual(history[1]["status"], "in-progress")
        self.assertEqual(history[1]["reason"], "Starting work")


class TestValidationRules(unittest.TestCase):
    """Test validation rules for commits and merges."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create task directories
        tasks_dir = os.path.join(self.base_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory
        agents_dir = os.path.join(self.base_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # Create test agent
        self.agent = create_agent("Test Agent", "test@example.com", 
                                  base_dir=self.base_dir)
        self.agent_id = self.agent["agent_id"]
        
        # Init lifecycle config
        init_lifecycle_config(self.base_dir)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_validate_task_exists(self):
        """Test validation fails for non-existent task."""
        allowed, msg = validate_commit_allowed("NONEXISTENT", self.agent_id, self.base_dir)
        self.assertFalse(allowed)
        self.assertIn("not found", msg)
    
    def test_validate_assignee_match(self):
        """Test commit blocked if not assigned to agent."""
        # Create task assigned to someone else
        create_task("TASK-001", "Test task", assignee="other_agent",
                   base_dir=self.base_dir)
        
        allowed, msg = validate_commit_allowed("TASK-001", self.agent_id, self.base_dir)
        self.assertFalse(allowed)
        self.assertIn("assigned to", msg)
    
    def test_validate_assignee_match_unassigned(self):
        """Test commit allowed for unassigned task."""
        create_task("TASK-002", "Test task", assignee="unassigned",
                   base_dir=self.base_dir)
        
        allowed, msg = validate_commit_allowed("TASK-002", self.agent_id, self.base_dir)
        self.assertTrue(allowed)
    
    def test_validate_dependencies_complete(self):
        """Test commit blocked if dependencies incomplete."""
        # Create dependency task
        create_task("DEP-001", "Dependency task", base_dir=self.base_dir)
        
        # Create task depending on it
        create_task("TASK-003", "Test task", 
                   depends_on="DEP-001", base_dir=self.base_dir)
        
        # Move task to in-progress
        from avcpm_task import move_task
        move_task("TASK-003", "in-progress", base_dir=self.base_dir)
        
        allowed, msg = validate_commit_allowed("TASK-003", self.agent_id, self.base_dir)
        self.assertFalse(allowed)
        self.assertIn("incomplete dependencies", msg)
    
    def test_validate_dependencies_complete_when_done(self):
        """Test commit allowed when dependencies are complete."""
        # Create and complete dependency
        create_task("DEP-002", "Dependency task", base_dir=self.base_dir)
        from avcpm_task import move_task
        move_task("DEP-002", "done", base_dir=self.base_dir)
        
        # Create task depending on it
        create_task("TASK-004", "Test task",
                   depends_on="DEP-002", base_dir=self.base_dir)
        move_task("TASK-004", "in-progress", base_dir=self.base_dir)
        
        allowed, msg = validate_commit_allowed("TASK-004", self.agent_id, self.base_dir)
        self.assertTrue(allowed)
    
    def test_validate_merge_no_review(self):
        """Test merge blocked without review."""
        create_task("TASK-005", "Test task", base_dir=self.base_dir)
        
        allowed, msg = validate_merge_allowed("TASK-005", "commit-001", self.base_dir)
        self.assertFalse(allowed)
        self.assertIn("No review found", msg)
    
    def test_validate_merge_not_approved(self):
        """Test merge blocked if review not approved."""
        create_task("TASK-006", "Test task", base_dir=self.base_dir)
        
        # Create review file (not approved)
        reviews_dir = os.path.join(self.base_dir, "reviews")
        os.makedirs(reviews_dir, exist_ok=True)
        with open(os.path.join(reviews_dir, "commit-002.review"), "w") as f:
            f.write("Task: TASK-006\nStatus: PENDING")
        
        allowed, msg = validate_merge_allowed("TASK-006", "commit-002", self.base_dir)
        self.assertFalse(allowed)
        self.assertIn("not approved", msg)
    
    def test_validate_merge_approved(self):
        """Test merge allowed with approved review."""
        create_task("TASK-007", "Test task", base_dir=self.base_dir)
        
        # Create approved review file
        reviews_dir = os.path.join(self.base_dir, "reviews")
        os.makedirs(reviews_dir, exist_ok=True)
        with open(os.path.join(reviews_dir, "commit-003.review"), "w") as f:
            f.write("Task: TASK-007\nStatus: APPROVED")
        
        allowed, msg = validate_merge_allowed("TASK-007", "commit-003", self.base_dir)
        self.assertTrue(allowed)


class TestAutoTransitions(unittest.TestCase):
    """Test automatic status transitions."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create task directories
        tasks_dir = os.path.join(self.base_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory and agent
        agents_dir = os.path.join(self.base_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        self.agent = create_agent("Test Agent", "test@example.com",
                                  base_dir=self.base_dir)
        self.agent_id = self.agent["agent_id"]
        
        # Init lifecycle config
        init_lifecycle_config(self.base_dir)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_on_first_commit_transition(self):
        """Test todo -> in-progress on first commit."""
        create_task("TASK-001", "Test task", base_dir=self.base_dir)
        
        self.assertEqual(get_task_status("TASK-001", self.base_dir), "todo")
        
        success, msg = on_commit("TASK-001", "commit-001", self.agent_id, self.base_dir)
        self.assertTrue(success)
        
        self.assertEqual(get_task_status("TASK-001", self.base_dir), "in-progress")
        self.assertIn("in-progress", msg)
    
    def test_on_commit_transition_to_review(self):
        """Test in-progress -> review on subsequent commit."""
        create_task("TASK-002", "Test task", base_dir=self.base_dir)
        
        # First commit - moves to in-progress
        on_commit("TASK-002", "commit-001", self.agent_id, self.base_dir)
        self.assertEqual(get_task_status("TASK-002", self.base_dir), "in-progress")
        
        # Second commit - should move to review
        success, msg = on_commit("TASK-002", "commit-002", self.agent_id, self.base_dir)
        self.assertTrue(success)
        
        self.assertEqual(get_task_status("TASK-002", self.base_dir), "review")
        self.assertIn("review", msg)
    
    def test_on_commit_blocked_by_dependencies(self):
        """Test commit records but doesn't transition if blocked."""
        # Create dependency
        create_task("DEP-001", "Dependency", base_dir=self.base_dir)
        
        # Create task with dependency
        create_task("TASK-003", "Test task", depends_on="DEP-001", base_dir=self.base_dir)
        
        # Move to in-progress with force (bypassing dependency check)
        from avcpm_task import move_task
        move_task("TASK-003", "in-progress", force=True, base_dir=self.base_dir)
        
        # Commit should record but not transition (blocked by deps)
        success, msg = on_commit("TASK-003", "commit-001", self.agent_id, self.base_dir)
        self.assertTrue(success)
        
        # Status should still be in-progress
        self.assertEqual(get_task_status("TASK-003", self.base_dir), "in-progress")
        self.assertIn("blocked by dependencies", msg)
    
    def test_on_merge_approval_transition(self):
        """Test review -> done on merge approval."""
        create_task("TASK-004", "Test task", base_dir=self.base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-004", "review", base_dir=self.base_dir)
        
        # Create approved review
        reviews_dir = os.path.join(self.base_dir, "reviews")
        os.makedirs(reviews_dir, exist_ok=True)
        with open(os.path.join(reviews_dir, "commit-001.review"), "w") as f:
            f.write("Task: TASK-004\nStatus: APPROVED")
        
        success, msg = on_merge("TASK-004", "commit-001", self.agent_id, self.base_dir)
        self.assertTrue(success)
        
        self.assertEqual(get_task_status("TASK-004", self.base_dir), "done")
        self.assertIn("done", msg)
    
    def test_on_review_approved_transition(self):
        """Test review -> done on review approval."""
        create_task("TASK-005", "Test task", base_dir=self.base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-005", "review", base_dir=self.base_dir)
        
        success, msg = on_review("TASK-005", "approved", self.base_dir)
        self.assertTrue(success)
        
        self.assertEqual(get_task_status("TASK-005", self.base_dir), "done")
    
    def test_on_review_rejected_transition(self):
        """Test review -> in-progress on review rejection."""
        create_task("TASK-006", "Test task", base_dir=self.base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-006", "review", base_dir=self.base_dir)
        
        success, msg = on_review("TASK-006", "rejected", self.base_dir)
        self.assertTrue(success)
        
        self.assertEqual(get_task_status("TASK-006", self.base_dir), "in-progress")
    
    def test_commit_history_tracking(self):
        """Test commits are recorded for a task."""
        create_task("TASK-007", "Test task", base_dir=self.base_dir)
        
        # Initially no commits
        self.assertEqual(len(get_task_commits("TASK-007", self.base_dir)), 0)
        self.assertTrue(is_first_commit("TASK-007", self.base_dir))
        
        # First commit
        on_commit("TASK-007", "commit-001", self.agent_id, self.base_dir)
        
        commits = get_task_commits("TASK-007", self.base_dir)
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]["commit_id"], "commit-001")
        self.assertEqual(commits[0]["agent_id"], self.agent_id)
        
        # No longer first commit
        self.assertFalse(is_first_commit("TASK-007", self.base_dir))


class TestTaskTypeConfig(unittest.TestCase):
    """Test per-task-type configuration."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create task directories
        tasks_dir = os.path.join(self.base_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory and agent
        agents_dir = os.path.join(self.base_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        self.agent = create_agent("Test Agent", "test@example.com",
                                  base_dir=self.base_dir)
        self.agent_id = self.agent["agent_id"]
        
        # Init lifecycle config
        init_lifecycle_config(self.base_dir)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_hotfix_bypasses_assignee_check(self):
        """Test hotfix tasks can bypass assignee validation."""
        # Create task assigned to someone else
        create_task("TASK-001", "Hotfix task", assignee="other_agent",
                   base_dir=self.base_dir)
        
        # Set task type to hotfix
        task_data = load_task("TASK-001", self.base_dir)
        task_data["type"] = "hotfix"
        save_task("TASK-001", task_data, base_dir=self.base_dir)
        
        # Should pass validation for hotfix
        allowed, msg = validate_commit_allowed("TASK-001", self.agent_id, self.base_dir)
        self.assertTrue(allowed, msg)
    
    def test_hotfix_bypasses_deps_check(self):
        """Test hotfix tasks can bypass dependencies validation."""
        # Create incomplete dependency
        create_task("DEP-001", "Dependency", base_dir=self.base_dir)
        
        # Create hotfix task with dependency
        create_task("TASK-002", "Hotfix task", depends_on="DEP-001",
                   base_dir=self.base_dir)
        
        # Set task type to hotfix
        task_data = load_task("TASK-002", self.base_dir)
        task_data["type"] = "hotfix"
        save_task("TASK-002", task_data, base_dir=self.base_dir)
        
        # Move to in-progress
        from avcpm_task import move_task
        move_task("TASK-002", "in-progress", base_dir=self.base_dir)
        
        # Should pass validation
        allowed, msg = validate_commit_allowed("TASK-002", self.agent_id, self.base_dir)
        self.assertTrue(allowed, msg)
    
    def test_disabled_auto_transition(self):
        """Test auto-transitions can be disabled per task type."""
        # Modify config to disable first commit transition
        config = load_lifecycle_config(self.base_dir)
        config["task_types"]["default"]["auto_transitions"]["on_first_commit"] = False
        save_lifecycle_config(config, self.base_dir)
        
        create_task("TASK-003", "Test task", base_dir=self.base_dir)
        
        # Commit should record but not transition
        success, msg = on_commit("TASK-003", "commit-001", self.agent_id, self.base_dir)
        self.assertTrue(success)
        
        # Should still be todo
        self.assertEqual(get_task_status("TASK-003", self.base_dir), "todo")
        self.assertIn("disabled", msg)


class TestCLICommands(unittest.TestCase):
    """Test CLI commands."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create task directories
        tasks_dir = os.path.join(self.base_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory and agent
        agents_dir = os.path.join(self.base_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        self.agent = create_agent("Test Agent", "test@example.com",
                                  base_dir=self.base_dir)
        self.agent_id = self.agent["agent_id"]
        
        # Create test task
        create_task("TASK-001", "Test task description", 
                   assignee=self.agent_id, base_dir=self.base_dir)
        
        # Init lifecycle config
        init_lifecycle_config(self.base_dir)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_status_command(self):
        """Test status command output."""
        output = cmd_status("TASK-001", self.base_dir)
        
        self.assertIn("TASK-001", output)
        self.assertIn("todo", output)
        self.assertIn("Test task description", output)
        self.assertIn(self.agent_id, output)
    
    def test_status_command_not_found(self):
        """Test status command for non-existent task."""
        output = cmd_status("NONEXISTENT", self.base_dir)
        self.assertIn("not found", output)
    
    def test_transitions_command(self):
        """Test transitions command output."""
        output = cmd_transitions("TASK-001", self.base_dir)
        
        self.assertIn("TASK-001", output)
        self.assertIn("todo", output)
        self.assertIn("Auto-Transition Settings", output)
        self.assertIn("todo -> in-progress", output)
    
    def test_validate_commit_command(self):
        """Test validate command for commit action."""
        output = cmd_validate("TASK-001", "commit", self.agent_id, self.base_dir)
        
        self.assertIn("PASS", output)
        self.assertIn("Assignee", output)
        self.assertIn(self.agent_id, output)
    
    def test_validate_merge_command_no_review(self):
        """Test validate command for merge without review."""
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-001", "review", base_dir=self.base_dir)
        
        output = cmd_validate("TASK-001", "merge", base_dir=self.base_dir)
        
        self.assertIn("FAIL", output)
        self.assertIn("No review found", output)


class TestIntegration(unittest.TestCase):
    """Integration tests for the full lifecycle workflow."""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, ".avcpm")
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create task directories
        tasks_dir = os.path.join(self.base_dir, "tasks")
        for col in COLUMNS:
            os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)
        
        # Create agents directory
        agents_dir = os.path.join(self.base_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # Create agent
        self.agent = create_agent("Test Agent", "test@example.com",
                                  base_dir=self.base_dir)
        self.agent_id = self.agent["agent_id"]
        
        # Create reviews directory
        os.makedirs(os.path.join(self.base_dir, "reviews"), exist_ok=True)
        
        # Init lifecycle config
        init_lifecycle_config(self.base_dir)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    
    def test_full_lifecycle_workflow(self):
        """Test complete task lifecycle from todo to done."""
        # 1. Create task
        create_task("TASK-FULL", "Full lifecycle task",
                   assignee=self.agent_id, base_dir=self.base_dir)
        self.assertEqual(get_task_status("TASK-FULL", self.base_dir), "todo")
        
        # 2. First commit - should auto-transition to in-progress
        success, msg = on_commit("TASK-FULL", "commit-001", self.agent_id, self.base_dir)
        self.assertTrue(success, msg)
        self.assertEqual(get_task_status("TASK-FULL", self.base_dir), "in-progress")
        
        # 3. Subsequent commit - should auto-transition to review
        success, msg = on_commit("TASK-FULL", "commit-002", self.agent_id, self.base_dir)
        self.assertTrue(success, msg)
        self.assertEqual(get_task_status("TASK-FULL", self.base_dir), "review")
        
        # 4. Create approved review
        with open(os.path.join(self.base_dir, "reviews", "commit-002.review"), "w") as f:
            f.write("Task: TASK-FULL\nStatus: APPROVED\nReviewer: reviewer1")
        
        # 5. Merge - should auto-transition to done
        success, msg = on_merge("TASK-FULL", "commit-002", self.agent_id, self.base_dir)
        self.assertTrue(success, msg)
        self.assertEqual(get_task_status("TASK-FULL", self.base_dir), "done")
        
        # 6. Verify commit history
        commits = get_task_commits("TASK-FULL", self.base_dir)
        self.assertEqual(len(commits), 2)
        
        # 7. Verify status history
        task_data = load_task("TASK-FULL", self.base_dir)
        history = task_data.get("status_history", [])
        statuses = [h["status"] for h in history]
        self.assertIn("todo", statuses)
        self.assertIn("in-progress", statuses)
        self.assertIn("review", statuses)
        self.assertIn("done", statuses)
    
    def test_rejected_review_workflow(self):
        """Test workflow with rejected review."""
        # Create task
        create_task("TASK-REJ", "Rejected review task",
                   assignee=self.agent_id, base_dir=self.base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-REJ", "review", base_dir=self.base_dir)
        
        # Review rejected - should transition to in-progress
        success, msg = on_review("TASK-REJ", "rejected", self.base_dir)
        self.assertTrue(success, msg)
        self.assertEqual(get_task_status("TASK-REJ", self.base_dir), "in-progress")
    
    def test_blocked_merge_without_approval(self):
        """Test merge blocked without approval."""
        # Create task
        create_task("TASK-BLOCK", "Blocked merge task",
                   assignee=self.agent_id, base_dir=self.base_dir)
        
        # Move to review
        from avcpm_task import move_task
        move_task("TASK-BLOCK", "review", base_dir=self.base_dir)
        
        # Try to merge without approval
        success, msg = on_merge("TASK-BLOCK", "commit-001", self.agent_id, self.base_dir)
        self.assertFalse(success)
        self.assertIn("No review found", msg)
        self.assertEqual(get_task_status("TASK-BLOCK", self.base_dir), "review")


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLifecycleConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestStatusTransitions))
    suite.addTests(loader.loadTestsFromTestCase(TestValidationRules))
    suite.addTests(loader.loadTestsFromTestCase(TestAutoTransitions))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskTypeConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestCLICommands))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
