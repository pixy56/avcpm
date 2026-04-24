from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union, Any
import os
import sys
import shutil
import json
from datetime import datetime

DEFAULT_BASE_DIR = ".avcpm"
COLUMNS = ["todo", "in-progress", "review", "done"]

def get_tasks_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the tasks directory path."""
    return os.path.join(base_dir, "tasks")

def ensure_directories(base_dir=DEFAULT_BASE_DIR) -> None:
    """Ensure task directories exist."""
    tasks_dir = get_tasks_dir(base_dir)
    for col in COLUMNS:
        os.makedirs(os.path.join(tasks_dir, col), exist_ok=True)

def get_task_path(task_id, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Find the full path of a task file regardless of status."""
    tasks_dir = get_tasks_dir(base_dir)
    for col in COLUMNS:
        path = os.path.join(tasks_dir, col, f"{task_id}.json")
        if os.path.exists(path):
            return path
    return None

def get_task_status(task_id, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the current status of a task."""
    tasks_dir = get_tasks_dir(base_dir)
    for col in COLUMNS:
        path = os.path.join(tasks_dir, col, f"{task_id}.json")
        if os.path.exists(path):
            return col
    return None

def load_task(task_id, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Load task data from file."""
    path = get_task_path(task_id, base_dir)
    if path:
        with open(path, "r") as f:
            return json.load(f)
    return None

def save_task(task_id, task_data, status=None, base_dir=DEFAULT_BASE_DIR) -> Any:
    """Save task data to file. If status not provided, use current status."""
    if status is None:
        status = get_task_status(task_id, base_dir)
    if status is None:
        return False
    
    tasks_dir = get_tasks_dir(base_dir)
    path = os.path.join(tasks_dir, status, f"{task_id}.json")
    with open(path, "w") as f:
        json.dump(task_data, f, indent=4)
    return True

def get_all_tasks(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get all tasks across all statuses."""
    tasks = []
    tasks_dir = get_tasks_dir(base_dir)
    for col in COLUMNS:
        col_path = os.path.join(tasks_dir, col)
        if os.path.exists(col_path):
            for f in os.listdir(col_path):
                if f.endswith(".json"):
                    with open(os.path.join(col_path, f), "r") as task_f:
                        tasks.append(json.load(task_f))
    return tasks

# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================

def get_dependencies(task_id, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get list of task IDs that this task depends on."""
    task_data = load_task(task_id, base_dir)
    if task_data:
        return task_data.get("depends_on", [])
    return []

def get_dependents(task_id, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get list of task IDs that depend on this task."""
    dependents = []
    all_tasks = get_all_tasks(base_dir)
    for task in all_tasks:
        deps = task.get("depends_on", [])
        if task_id in deps:
            dependents.append(task["id"])
    return dependents

def is_dependency_complete(dep_task_id, base_dir=DEFAULT_BASE_DIR) -> bool:
    """Check if a dependency task is complete (in 'done' status)."""
    return get_task_status(dep_task_id, base_dir) == "done"

def get_blocked_by(task_id, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get list of incomplete dependencies blocking this task."""
    deps = get_dependencies(task_id, base_dir)
    blocked_by = []
    for dep in deps:
        if not is_dependency_complete(dep, base_dir):
            blocked_by.append(dep)
    return blocked_by

def is_blocked(task_id, base_dir=DEFAULT_BASE_DIR) -> bool:
    """Check if task is blocked by incomplete dependencies."""
    return len(get_blocked_by(task_id, base_dir)) > 0

def can_progress(task_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """Check if task can progress (all dependencies complete)."""
    deps = get_dependencies(task_id, base_dir)
    if not deps:
        return True
    return all(is_dependency_complete(dep, base_dir) for dep in deps)

def get_blocked_tasks(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get all tasks that are blocked by incomplete dependencies."""
    blocked = []
    all_tasks = get_all_tasks(base_dir)
    for task in all_tasks:
        if is_blocked(task["id"], base_dir):
            blocked.append({
                "id": task["id"],
                "description": task.get("description", ""),
                "blocked_by": get_blocked_by(task["id"], base_dir)
            })
    return blocked

def _detect_cycle_dfs(task_id, visited, recursion_stack, base_dir=DEFAULT_BASE_DIR):
    """DFS helper for cycle detection."""
    visited.add(task_id)
    recursion_stack.add(task_id)
    
    deps = get_dependencies(task_id, base_dir)
    for dep in deps:
        if dep not in visited:
            if _detect_cycle_dfs(dep, visited, recursion_stack, base_dir):
                return True
        elif dep in recursion_stack:
            return True
    
    recursion_stack.remove(task_id)
    return False

def has_cycle(task_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """Check if adding dependencies would create a cycle."""
    visited = set()
    recursion_stack = set()
    return _detect_cycle_dfs(task_id, visited, recursion_stack, base_dir)

def would_create_cycle(task_id, new_dep_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """Check if adding new_dep_id as dependency would create a cycle."""
    # Temporarily add the dependency and check for cycle
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return False
    
    # If the new dep is not done and depends on task_id, it's a cycle
    current_deps = task_data.get("depends_on", [])
    if new_dep_id in current_deps:
        return False  # Already a dependency
    
    # Check if new_dep_id directly or indirectly depends on task_id
    # This is equivalent to checking if task_id is reachable from new_dep_id
    def reaches(from_id, to_id, visited=None) -> Any:
        if visited is None:
            visited = set()
        if from_id in visited:
            return False
        if from_id == to_id:
            return True
        visited.add(from_id)
        deps = get_dependencies(from_id, base_dir)
        for dep in deps:
            if reaches(dep, to_id, visited):
                return True
        return False
    
    return reaches(new_dep_id, task_id)

def add_dependency(task_id, depends_on_task_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """Add a dependency to a task. Returns True if successful, raises exception on error."""
    if task_id == depends_on_task_id:
        raise ValueError(f"Task cannot depend on itself")
    
    task_data = load_task(task_id, base_dir)
    if not task_data:
        raise ValueError(f"Task {task_id} not found")
    
    dep_task = load_task(depends_on_task_id, base_dir)
    if not dep_task:
        raise ValueError(f"Dependency task {depends_on_task_id} not found")
    
    # Check for circular dependency
    if would_create_cycle(task_id, depends_on_task_id, base_dir):
        raise ValueError(f"Cannot add dependency: would create circular dependency")
    
    # Add dependency
    deps = task_data.get("depends_on", [])
    if depends_on_task_id not in deps:
        deps.append(depends_on_task_id)
        task_data["depends_on"] = deps
        save_task(task_id, task_data, base_dir=base_dir)
        return True
    return False

def remove_dependency(task_id, depends_on_task_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """Remove a dependency from a task. Returns True if removed, False if not found."""
    task_data = load_task(task_id, base_dir)
    if not task_data:
        raise ValueError(f"Task {task_id} not found")
    
    deps = task_data.get("depends_on", [])
    if depends_on_task_id in deps:
        deps.remove(depends_on_task_id)
        task_data["depends_on"] = deps
        save_task(task_id, task_data, base_dir=base_dir)
        return True
    return False

# ============================================================================
# VISUALIZATION
# ============================================================================

def _build_dependency_tree(task_id, base_dir=DEFAULT_BASE_DIR, visited=None, prefix="", is_last=True, is_root=True):
    """Build ASCII tree representation of dependencies."""
    if visited is None:
        visited = set()
    
    if task_id in visited:
        return [f"{prefix}{'└── ' if not is_root else ''}{task_id} [CYCLIC REFERENCE]"]
    
    visited.add(task_id)
    
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return [f"{prefix}{'└── ' if not is_root else ''}{task_id} [NOT FOUND]"]
    
    status = get_task_status(task_id, base_dir)
    blocked = is_blocked(task_id, base_dir)
    status_indicator = "✓" if status == "done" else ("⏸" if blocked else "○")
    
    lines = []
    connector = "└── " if is_last and not is_root else "├── " if not is_root else ""
    lines.append(f"{prefix}{connector}[{status_indicator}] {task_id}: {task_data.get('description', 'No description')}")
    
    deps = get_dependencies(task_id, base_dir)
    if deps:
        new_prefix = prefix + ("    " if is_last or is_root else "│   ")
        for i, dep in enumerate(deps):
            is_last_dep = (i == len(deps) - 1)
            lines.extend(_build_dependency_tree(dep, base_dir, visited.copy(), new_prefix, is_last_dep, False))
    
    return lines

def show_dependency_graph(task_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """Show ASCII art tree of dependencies for a task."""
    lines = _build_dependency_tree(task_id, base_dir)
    return "\n".join(lines)

def show_dependents_graph(task_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """Show tasks that depend on this one (reverse dependency view)."""
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return f"Task {task_id} not found"
    
    lines = [f"Tasks depending on {task_id}:"]
    dependents = get_dependents(task_id, base_dir)
    if not dependents:
        lines.append("  (none)")
    else:
        for dep_id in dependents:
            dep_data = load_task(dep_id, base_dir)
            if dep_data:
                blocked = is_blocked(dep_id, base_dir)
                status = get_task_status(dep_id, base_dir)
                status_indicator = "✓" if status == "done" else ("⏸" if blocked else "○")
                lines.append(f"  [{status_indicator}] {dep_id}: {dep_data.get('description', 'No description')}")
    return "\n".join(lines)

# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_help() -> None:
    print("AVCPM Task Tooling")
    print("Usage:")
    print("  python avcpm_task.py create <id> <description> [assignee] [depends_on,...]")
    print("  python avcpm_task.py move <id> <new_status> [--force]")
    print("  python avcpm_task.py list")
    print("  python avcpm_task.py deps add <task_id> <depends_on_id>")
    print("  python avcpm_task.py deps remove <task_id> <depends_on_id>")
    print("  python avcpm_task.py deps show <task_id>")
    print("  python avcpm_task.py deps dependents <task_id>")
    print("  python avcpm_task.py blocked")

def create_task(task_id, description, assignee="unassigned", depends_on=None, base_dir=DEFAULT_BASE_DIR) -> Dict:
    tasks_dir = get_tasks_dir(base_dir)
    ensure_directories(base_dir)
    
    path = os.path.join(tasks_dir, "todo", f"{task_id}.json")
    if os.path.exists(path):
        raise ValueError(f"Task {task_id} already exists.")
    
    # Validate dependencies if provided
    deps_list = []
    if depends_on:
        if isinstance(depends_on, str):
            deps_list = [d.strip() for d in depends_on.split(",") if d.strip()]
        elif isinstance(depends_on, list):
            deps_list = depends_on
        
        # Validate all dependencies exist
        for dep in deps_list:
            if not load_task(dep, base_dir):
                raise ValueError(f"Dependency task '{dep}' not found")
            if dep == task_id:
                raise ValueError(f"Task cannot depend on itself")
        # M-A3: Check for dependency cycles
        for dep in deps_list:
            if would_create_cycle(task_id, dep, base_dir):
                raise ValueError(f"Cannot add dependency: would create circular dependency via {dep}")
    
    task_data = {
        "id": task_id,
        "description": description,
        "assignee": assignee,
        "priority": "medium",
        "depends_on": deps_list,
        "status_history": [
            {"status": "todo", "timestamp": datetime.now().isoformat()}
        ]
    }
    
    with open(path, "w") as f:
        json.dump(task_data, f, indent=4)
    
    if deps_list:
        print(f"Task {task_id} created in 'todo' with dependencies: {', '.join(deps_list)}")
    else:
        print(f"Task {task_id} created in 'todo'.")

def move_task(task_id, new_status, force=False, base_dir=DEFAULT_BASE_DIR) -> None:
    if new_status not in COLUMNS:
        raise ValueError(f"Invalid status '{new_status}'. Use {COLUMNS}")
    
    tasks_dir = get_tasks_dir(base_dir)
    
    # Find where the task is currently
    current_path = None
    current_status = None
    for col in COLUMNS:
        p = os.path.join(tasks_dir, col, f"{task_id}.json")
        if os.path.exists(p):
            current_path = p
            current_status = col
            break
    
    if not current_path:
        raise ValueError(f"Task {task_id} not found.")
    
    # Load task data
    with open(current_path, "r") as f:
        task_data = json.load(f)
    
    # Check dependencies before moving to in-progress or review or done
    if new_status in ["in-progress", "review", "done"] and not force:
        blocked_by = get_blocked_by(task_id, base_dir)
        if blocked_by:
            raise ValueError(f"Task {task_id} is blocked by incomplete dependencies: {', '.join(blocked_by)}. Use --force to override.")
    
    # Update status history
    task_data["status_history"].append({
        "status": new_status,
        "timestamp": datetime.now().isoformat()
    })
    
    # Write updated data atomically to current path first, then move
    new_path = os.path.join(tasks_dir, new_status, f"{task_id}.json")
    
    # Write updated JSON to temp file in same dir, then atomic replace
    import tempfile
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(current_path), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(task_data, f, indent=4)
        os.replace(tmp_path, current_path)
    except Exception:
        os.remove(tmp_path) if os.path.exists(tmp_path) else None
        raise
    
    # Move the fully-updated file to the new column
    shutil.move(current_path, new_path)
    
    if force and new_status in ["in-progress", "review"]:
        print(f"Task {task_id} moved to {new_status} (forced, bypassed dependency check).")
    else:
        print(f"Task {task_id} moved to {new_status}.")

def list_tasks(base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    tasks_dir = get_tasks_dir(base_dir)
    
    for col in COLUMNS:
        print(f"\n--- {col.upper()} ---")
        col_path = os.path.join(tasks_dir, col)
        if not os.path.exists(col_path):
            print(" (empty)")
            continue
        files = [f for f in os.listdir(col_path) if f.endswith(".json")]
        if not files:
            print(" (empty)")
        for f in files:
            with open(os.path.join(col_path, f), "r") as task_f:
                data = json.load(task_f)
                deps = data.get("depends_on", [])
                blocked = is_blocked(data['id'], base_dir) if deps else False
                status_marker = " [BLOCKED]" if blocked else ""
                deps_info = f" (deps: {', '.join(deps)})" if deps else ""
                print(f"[{data['id']}] {data['description']} ({data['assignee']}){deps_info}{status_marker}")

def list_blocked(base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    """List all tasks blocked by incomplete dependencies."""
    blocked = get_blocked_tasks(base_dir)
    if not blocked:
        print("No tasks are currently blocked.")
        return
    
    print("\n--- BLOCKED TASKS ---")
    for task in blocked:
        print(f"[{task['id']}] {task['description']}")
        print(f"    Blocked by: {', '.join(task['blocked_by'])}")

def deps_add(task_id, depends_on_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """CLI handler for adding dependencies. Returns True on success, raises ValueError on error."""
    add_dependency(task_id, depends_on_id, base_dir)
    print(f"Added dependency: {task_id} now depends on {depends_on_id}")

def deps_remove(task_id, depends_on_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """CLI handler for removing dependencies. Returns True on success, raises ValueError on error."""
    removed = remove_dependency(task_id, depends_on_id, base_dir)
    if removed:
        print(f"Removed dependency: {task_id} no longer depends on {depends_on_id}")
    else:
        raise ValueError(f"Task {task_id} did not depend on {depends_on_id}")

def deps_show(task_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """CLI handler for showing dependency graph."""
    print(show_dependency_graph(task_id, base_dir))

def deps_dependents(task_id, base_dir=DEFAULT_BASE_DIR) -> Any:
    """CLI handler for showing tasks that depend on this one."""
    print(show_dependents_graph(task_id, base_dir))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    try:
        if cmd == "create":
            if len(sys.argv) < 4:
                print_help()
                sys.exit(1)
            assignee = sys.argv[4] if len(sys.argv) > 4 else "unassigned"
            depends_on = sys.argv[5] if len(sys.argv) > 5 else None
            create_task(sys.argv[2], sys.argv[3], assignee, depends_on)
        
        elif cmd == "move":
            if len(sys.argv) < 4:
                print_help()
                sys.exit(1)
            force = "--force" in sys.argv
            new_status = sys.argv[3]
            if new_status == "--force":
                new_status = sys.argv[4] if len(sys.argv) > 4 else None
            move_task(sys.argv[2], new_status, force)
        
        elif cmd == "list":
            list_tasks()
        
        elif cmd == "blocked":
            list_blocked()
        
        elif cmd == "deps":
            if len(sys.argv) < 4:
                print_help()
                sys.exit(1)
            
            subcmd = sys.argv[2]
            
            if subcmd == "add" and len(sys.argv) == 5:
                deps_add(sys.argv[3], sys.argv[4])
            elif subcmd == "remove" and len(sys.argv) == 5:
                deps_remove(sys.argv[3], sys.argv[4])
            elif subcmd == "show" and len(sys.argv) == 4:
                deps_show(sys.argv[3])
            elif subcmd == "dependents" and len(sys.argv) == 4:
                deps_dependents(sys.argv[3])
            else:
                print_help()
                sys.exit(1)
        
        else:
            print_help()
            sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
