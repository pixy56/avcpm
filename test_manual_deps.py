"""Manual tests for AVCPM Task Dependencies (TASK-DEPS-01)"""
import os
import sys
import shutil
import tempfile

sys.path.insert(0, '/home/user/.openclaw/workspace')
import avcpm_task as task

def test_basic():
    """Run basic functionality tests."""
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, ".avcpm_test")
        os.makedirs(base_dir)
        
        print("=" * 60)
        print("TEST 1: Creating tasks with dependencies")
        print("=" * 60)
        
        # Create task A
        task.create_task("task-A", "First task to complete", base_dir=base_dir)
        
        # Create task B depending on A
        task.create_task("task-B", "Second task depending on A", depends_on=["task-A"], base_dir=base_dir)
        
        # Create task C depending on B
        task.create_task("task-C", "Third task depending on B", depends_on=["task-B"], base_dir=base_dir)
        
        print("\n✓ Tasks created successfully")
        
        print("\n" + "=" * 60)
        print("TEST 2: Checking blocked status")
        print("=" * 60)
        
        # Check blocked status
        assert task.is_blocked("task-A", base_dir) == False, "Task A should not be blocked"
        assert task.is_blocked("task-B", base_dir) == True, "Task B should be blocked"
        assert task.is_blocked("task-C", base_dir) == True, "Task C should be blocked"
        
        print("✓ Task A is not blocked (no deps)")
        print("✓ Task B is blocked by A")
        print("✓ Task C is blocked by B")
        
        print("\n" + "=" * 60)
        print("TEST 3: Dependency retrieval")
        print("=" * 60)
        
        deps_b = task.get_dependencies("task-B", base_dir)
        deps_c = task.get_dependencies("task-C", base_dir)
        
        assert deps_b == ["task-A"], f"Expected ['task-A'], got {deps_b}"
        assert deps_c == ["task-B"], f"Expected ['task-B'], got {deps_c}"
        
        print(f"✓ Task B depends on: {deps_b}")
        print(f"✓ Task C depends on: {deps_c}")
        
        dependents_a = task.get_dependents("task-A", base_dir)
        dependents_b = task.get_dependents("task-B", base_dir)
        
        assert "task-B" in dependents_a, f"task-B should depend on task-A"
        assert "task-C" in dependents_b, f"task-C should depend on task-B"
        
        print(f"✓ Tasks depending on A: {dependents_a}")
        print(f"✓ Tasks depending on B: {dependents_b}")
        
        print("\n" + "=" * 60)
        print("TEST 4: Move task blocking")
        print("=" * 60)
        
        # Try to move B to in-progress (should fail)
        try:
            task.move_task("task-B", "in-progress", base_dir=base_dir)
            assert False, "Should have raised SystemExit"
        except SystemExit:
            print("✓ Cannot move task-B to in-progress (blocked by A)")
        
        # Complete A
        task.move_task("task-A", "done", base_dir=base_dir)
        print("✓ Moved task-A to done")
        
        # Now B can move
        task.move_task("task-B", "in-progress", base_dir=base_dir)
        print("✓ Moved task-B to in-progress (A is done)")
        
        # But C still blocked
        assert task.is_blocked("task-C", base_dir) == True, "C should still be blocked"
        print("✓ Task C is still blocked (B is in-progress, not done)")
        
        print("\n" + "=" * 60)
        print("TEST 5: Force move bypass")
        print("=" * 60)
        
        task.move_task("task-C", "in-progress", force=True, base_dir=base_dir)
        print("✓ Forced task-C to in-progress (bypassed blocking)")
        
        print("\n" + "=" * 60)
        print("TEST 6: Circular dependency prevention")
        print("=" * 60)
        
        # Try to make A depend on C (would create cycle A->B->C->A)
        try:
            task.add_dependency("task-A", "task-C", base_dir)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"✓ Circular dependency rejected: {e}")
        
        # Try self-dependency
        try:
            task.add_dependency("task-A", "task-A", base_dir)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"✓ Self-dependency rejected: {e}")
        
        print("\n" + "=" * 60)
        print("TEST 7: Dependency visualization")
        print("=" * 60)
        
        graph = task.show_dependency_graph("task-C", base_dir)
        print("Dependency graph for task-C:")
        print(graph)
        
        print("\n" + "=" * 60)
        print("TEST 8: List blocked tasks")
        print("=" * 60)
        
        # Create task E
        task.create_task("task-E", "Prerequisite for D", base_dir=base_dir)
        
        # Create task D depending on E
        task.create_task("task-D", "Blocked task", depends_on=["task-E"], base_dir=base_dir)
        
        blocked = task.get_blocked_tasks(base_dir)
        print(f"Blocked tasks: {[b['id'] for b in blocked]}")
        
        # E is in todo, so D should be blocked
        assert any(b['id'] == 'task-D' for b in blocked), "task-D should be blocked"
        print("✓ get_blocked_tasks() works correctly")
        
        print("\n" + "=" * 60)
        print("TEST 9: Add/remove dependencies")
        print("=" * 60)
        
        # Create task F
        task.create_task("task-F", "New task", base_dir=base_dir)
        
        # Add dependency
        task.add_dependency("task-F", "task-A", base_dir)
        deps = task.get_dependencies("task-F", base_dir)
        assert "task-A" in deps
        print("✓ Added dependency: task-F -> task-A")
        
        # Remove dependency
        task.remove_dependency("task-F", "task-A", base_dir)
        deps = task.get_dependencies("task-F", base_dir)
        assert "task-A" not in deps
        print("✓ Removed dependency: task-F no longer depends on task-A")
        
        print("\n" + "=" * 60)
        print("TEST 10: Backward compatibility")
        print("=" * 60)
        
        # Create a task manually without depends_on field
        tasks_dir = task.get_tasks_dir(base_dir)
        old_task = {
            "id": "old-task",
            "description": "Task without deps field",
            "assignee": "unassigned",
            "priority": "medium",
            "status_history": [{"status": "todo", "timestamp": "2025-01-01T00:00:00"}]
        }
        with open(os.path.join(tasks_dir, "todo", "old-task.json"), "w") as f:
            import json
            json.dump(old_task, f, indent=4)
        
        # Should handle gracefully
        deps = task.get_dependencies("old-task", base_dir)
        assert deps == []
        print("✓ Task without depends_on field handled correctly")
        
        blocked = task.is_blocked("old-task", base_dir)
        assert blocked == False
        print("✓ Task without deps is not blocked")
        
        # Should be able to move
        task.move_task("old-task", "in-progress", base_dir=base_dir)
        print("✓ Task without deps can be moved to in-progress")
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)


if __name__ == "__main__":
    test_basic()
