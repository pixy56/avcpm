"""Tests for AVCPM Task Dependencies (TASK-DEPS-01)"""
import os
import sys
import pytest
import shutil
import json
from datetime import datetime

# Add the workspace to path to import avcpm_task
sys.path.insert(0, '/home/user/.openclaw/workspace')

import avcpm_task as task


@pytest.fixture
def temp_base_dir(tmp_path):
    """Create a temporary base directory for tests."""
    base_dir = tmp_path / ".avcpm_test"
    base_dir.mkdir()
    return str(base_dir)


@pytest.fixture
def setup_tasks(temp_base_dir):
    """Set up test tasks for dependency testing."""
    task.ensure_directories(temp_base_dir)
    
    # Create task A (base task)
    task.create_task("task-A", "First task", base_dir=temp_base_dir)
    
    # Create task B (depends on A)
    task.create_task("task-B", "Second task", depends_on=["task-A"], base_dir=temp_base_dir)
    
    # Create task C (depends on B)
    task.create_task("task-C", "Third task", depends_on=["task-B"], base_dir=temp_base_dir)
    
    return temp_base_dir


class TestDependencyManagement:
    """Test dependency CRUD operations."""
    
    def test_add_dependency(self, setup_tasks):
        """Test adding a dependency to a task."""
        base_dir = setup_tasks
        
        # Create task D and add dependency on A
        task.create_task("task-D", "Fourth task", base_dir=base_dir)
        task.add_dependency("task-D", "task-A", base_dir)
        
        deps = task.get_dependencies("task-D", base_dir)
        assert "task-A" in deps
    
    def test_remove_dependency(self, setup_tasks):
        """Test removing a dependency from a task."""
        base_dir = setup_tasks
        
        # Remove B's dependency on A
        task.remove_dependency("task-B", "task-A", base_dir)
        
        deps = task.get_dependencies("task-B", base_dir)
        assert "task-A" not in deps
    
    def test_get_dependencies(self, setup_tasks):
        """Test getting task dependencies."""
        base_dir = setup_tasks
        
        deps = task.get_dependencies("task-B", base_dir)
        assert deps == ["task-A"]
        
        deps = task.get_dependencies("task-C", base_dir)
        assert deps == ["task-B"]
    
    def test_get_dependents(self, setup_tasks):
        """Test getting tasks that depend on a task."""
        base_dir = setup_tasks
        
        dependents = task.get_dependents("task-A", base_dir)
        assert "task-B" in dependents
        
        dependents = task.get_dependents("task-B", base_dir)
        assert "task-C" in dependents
    
    def test_add_duplicate_dependency(self, setup_tasks):
        """Test adding same dependency twice is idempotent."""
        base_dir = setup_tasks
        
        # Try to add A as dependency of B again (already has it)
        result = task.add_dependency("task-B", "task-A", base_dir)
        
        # Should return False or not error
        deps = task.get_dependencies("task-B", base_dir)
        assert deps.count("task-A") == 1  # Still only one


class TestBlockedStatus:
    """Test blocked status and progression checking."""
    
    def test_is_blocked_when_dependency_incomplete(self, setup_tasks):
        """Test task is blocked when dependency is not done."""
        base_dir = setup_tasks
        
        # B depends on A, A is in todo, so B should be blocked
        assert task.is_blocked("task-B", base_dir) is True
    
    def test_is_blocked_when_dependency_done(self, setup_tasks):
        """Test task is not blocked when dependency is done."""
        base_dir = setup_tasks
        
        # Move A to done
        task.move_task("task-A", "done", base_dir=base_dir)
        
        # B should no longer be blocked
        assert task.is_blocked("task-B", base_dir) is False
    
    def test_can_progress_no_deps(self, setup_tasks):
        """Test task with no dependencies can always progress."""
        base_dir = setup_tasks
        
        # Create task with no dependencies
        task.create_task("task-D", "No deps", base_dir=base_dir)
        
        assert task.can_progress("task-D", base_dir) is True
    
    def test_can_progress_with_complete_deps(self, setup_tasks):
        """Test task can progress when dependencies are complete."""
        base_dir = setup_tasks
        
        # Complete A
        task.move_task("task-A", "done", base_dir=base_dir)
        
        assert task.can_progress("task-B", base_dir) is True
    
    def test_can_progress_with_incomplete_deps(self, setup_tasks):
        """Test task cannot progress when dependencies are incomplete."""
        base_dir = setup_tasks
        
        # A is still in todo
        assert task.can_progress("task-B", base_dir) is False
    
    def test_get_blocked_tasks(self, setup_tasks):
        """Test getting all blocked tasks."""
        base_dir = setup_tasks
        
        blocked = task.get_blocked_tasks(base_dir)
        blocked_ids = [t["id"] for t in blocked]
        
        # B and C should be blocked (both depend on incomplete tasks)
        assert "task-B" in blocked_ids
        assert "task-C" in blocked_ids
        assert "task-A" not in blocked_ids


class TestMoveTaskBlocking:
    """Test that move_task respects dependencies."""
    
    def test_move_to_in_progress_blocked(self, setup_tasks):
        """Test cannot move to in-progress when blocked."""
        base_dir = setup_tasks
        
        with pytest.raises(SystemExit):
            task.move_task("task-B", "in-progress", base_dir=base_dir)
    
    def test_move_to_review_blocked(self, setup_tasks):
        """Test cannot move to review when blocked."""
        base_dir = setup_tasks
        
        with pytest.raises(SystemExit):
            task.move_task("task-B", "review", base_dir=base_dir)
    
    def test_move_to_in_progress_allowed(self, setup_tasks):
        """Test can move to in-progress when not blocked."""
        base_dir = setup_tasks
        
        # Complete A first
        task.move_task("task-A", "done", base_dir=base_dir)
        
        # Now B can move
        task.move_task("task-B", "in-progress", base_dir=base_dir)
        
        assert task.get_task_status("task-B", base_dir) == "in-progress"
    
    def test_move_to_done_always_allowed(self, setup_tasks):
        """Test can always move to done (no dependency check)."""
        base_dir = setup_tasks
        
        # Even though B is blocked, we can still move it to done
        task.move_task("task-B", "done", base_dir=base_dir)
        
        assert task.get_task_status("task-B", base_dir) == "done"
    
    def test_move_to_todo_always_allowed(self, setup_tasks):
        """Test can always move back to todo."""
        base_dir = setup_tasks
        
        # Move A to in-progress first
        task.move_task("task-A", "in-progress", base_dir=base_dir)
        
        # Can still move back to todo
        task.move_task("task-A", "todo", base_dir=base_dir)
        
        assert task.get_task_status("task-A", base_dir) == "todo"
    
    def test_force_move_bypasses_blocking(self, setup_tasks):
        """Test force parameter bypasses dependency check."""
        base_dir = setup_tasks
        
        # B is blocked, but force should allow move
        task.move_task("task-B", "in-progress", force=True, base_dir=base_dir)
        
        assert task.get_task_status("task-B", base_dir) == "in-progress"


class TestCircularDependencyPrevention:
    """Test circular dependency detection."""
    
    def test_self_dependency_rejected(self, setup_tasks):
        """Test task cannot depend on itself."""
        base_dir = setup_tasks
        
        with pytest.raises(ValueError, match="depend on itself"):
            task.add_dependency("task-A", "task-A", base_dir)
    
    def test_direct_circular_dependency_rejected(self, setup_tasks):
        """Test A→B and B→A is rejected."""
        base_dir = setup_tasks
        
        # B already depends on A, trying to make A depend on B should fail
        with pytest.raises(ValueError, match="circular"):
            task.add_dependency("task-A", "task-B", base_dir)
    
    def test_indirect_circular_dependency_rejected(self, setup_tasks):
        """Test A→B→C→A is rejected."""
        base_dir = setup_tasks
        
        # C depends on B, B depends on A
        # Trying to make A depend on C should fail
        with pytest.raises(ValueError, match="circular"):
            task.add_dependency("task-A", "task-C", base_dir)
    
    def test_chain_dependency_is_valid(self, setup_tasks):
        """Test A→B→C is valid (not circular)."""
        base_dir = setup_tasks
        
        # This is already set up: C depends on B, B depends on A
        # This should not raise any errors
        deps_b = task.get_dependencies("task-B", base_dir)
        deps_c = task.get_dependencies("task-C", base_dir)
        
        assert deps_b == ["task-A"]
        assert deps_c == ["task-B"]


class TestBackwardCompatibility:
    """Test that existing tasks without dependencies work correctly."""
    
    def test_task_without_deps_field(self, temp_base_dir):
        """Test task created before dependencies feature still works."""
        base_dir = temp_base_dir
        task.ensure_directories(base_dir)
        
        # Manually create a task without depends_on field (simulating old task)
        tasks_dir = task.get_tasks_dir(base_dir)
        old_task = {
            "id": "old-task",
            "description": "Old style task",
            "assignee": "unassigned",
            "priority": "medium",
            "status_history": [
                {"status": "todo", "timestamp": datetime.now().isoformat()}
            ]
        }
        
        os.makedirs(os.path.join(tasks_dir, "todo"), exist_ok=True)
        with open(os.path.join(tasks_dir, "todo", "old-task.json"), "w") as f:
            json.dump(old_task, f, indent=4)
        
        # Should be able to get dependencies (empty list)
        deps = task.get_dependencies("old-task", base_dir)
        assert deps == []
        
        # Should not be blocked
        assert task.is_blocked("old-task", base_dir) is False
        
        # Should be able to move
        task.move_task("old-task", "in-progress", base_dir=base_dir)
        assert task.get_task_status("old-task", base_dir) == "in-progress"


class TestVisualization:
    """Test dependency visualization features."""
    
    def test_show_dependency_graph(self, setup_tasks):
        """Test dependency tree visualization."""
        base_dir = setup_tasks
        
        graph = task.show_dependency_graph("task-C", base_dir)
        
        assert "task-C" in graph
        assert "task-B" in graph
        assert "task-A" in graph
        assert "[○]" in graph or "[⏸]" in graph  # Status indicators
    
    def test_show_dependents_graph(self, setup_tasks):
        """Test dependents visualization."""
        base_dir = setup_tasks
        
        graph = task.show_dependents_graph("task-A", base_dir)
        
        assert "task-B" in graph
        assert "[⏸]" in graph  # B should be blocked
    
    def test_list_tasks_shows_blocked_status(self, setup_tasks, capsys):
        """Test list_tasks shows blocked status."""
        base_dir = setup_tasks
        
        task.list_tasks(base_dir)
        captured = capsys.readouterr()
        
        assert "[BLOCKED]" in captured.out or "(deps:" in captured.out


class TestDependencyCreation:
    """Test creating tasks with dependencies."""
    
    def test_create_with_single_dependency(self, temp_base_dir):
        """Test creating task with single dependency."""
        base_dir = temp_base_dir
        
        task.create_task("task-1", "First", base_dir=base_dir)
        task.create_task("task-2", "Second", depends_on=["task-1"], base_dir=base_dir)
        
        deps = task.get_dependencies("task-2", base_dir)
        assert deps == ["task-1"]
    
    def test_create_with_multiple_dependencies(self, temp_base_dir):
        """Test creating task with multiple dependencies."""
        base_dir = temp_base_dir
        
        task.create_task("task-1", "First", base_dir=base_dir)
        task.create_task("task-2", "Second", base_dir=base_dir)
        task.create_task("task-3", "Third", depends_on=["task-1", "task-2"], base_dir=base_dir)
        
        deps = task.get_dependencies("task-3", base_dir)
        assert "task-1" in deps
        assert "task-2" in deps
    
    def test_create_with_string_dependencies(self, temp_base_dir):
        """Test creating task with comma-separated dependency string."""
        base_dir = temp_base_dir
        
        task.create_task("task-1", "First", base_dir=base_dir)
        task.create_task("task-2", "Second", base_dir=base_dir)
        
        # Create with string format
        task.create_task("task-3", "Third", depends_on="task-1, task-2", base_dir=base_dir)
        
        deps = task.get_dependencies("task-3", base_dir)
        assert "task-1" in deps
        assert "task-2" in deps
    
    def test_create_with_nonexistent_dependency_fails(self, temp_base_dir):
        """Test creating task with non-existent dependency fails."""
        base_dir = temp_base_dir
        
        with pytest.raises(SystemExit):
            task.create_task("task-2", "Second", depends_on=["nonexistent"], base_dir=base_dir)


class TestConfigurableBaseDir:
    """Test that all operations work with configurable base_dir."""
    
    def test_all_functions_respect_base_dir(self, temp_base_dir):
        """Test all operations use the specified base_dir."""
        base_dir = temp_base_dir
        
        # Create tasks
        task.create_task("A", "Task A", base_dir=base_dir)
        task.create_task("B", "Task B", depends_on=["A"], base_dir=base_dir)
        
        # Check deps
        assert task.get_dependencies("B", base_dir) == ["A"]
        
        # Check blocked status
        assert task.is_blocked("B", base_dir) is True
        
        # Move A to done
        task.move_task("A", "done", base_dir=base_dir)
        
        # B should no longer be blocked
        assert task.is_blocked("B", base_dir) is False
        
        # Verify files are in the correct location
        assert os.path.exists(os.path.join(base_dir, "tasks", "done", "A.json"))
        assert os.path.exists(os.path.join(base_dir, "tasks", "todo", "B.json"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
