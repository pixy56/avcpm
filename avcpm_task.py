import os
import sys
import shutil
import json
from datetime import datetime

from avcpm_security import sanitize_path, safe_read_text, safe_write_text, safe_exists, safe_makedirs, protect_avcpm_directory
from avcpm_auth import validate_session, get_authenticated_agent_from_env

DEFAULT_BASE_DIR = ".avcpm"
COLUMNS = ["todo", "in-progress", "review", "done"]


def verify_task_permission(task_id, agent_id, base_dir=DEFAULT_BASE_DIR, require_auth=True):
    """
    Verify that an agent has permission to modify a task.
    
    Args:
        task_id: The task ID being modified
        agent_id: The agent attempting the modification
        base_dir: Base directory for AVCPM
        require_auth: Whether authentication is required
    
    Returns:
        tuple: (is_permitted: bool, error_message: str or None)
    """
    if not require_auth:
        return True, None
    
    # Check if agent is authenticated via environment
    auth_agent_id, session_token = get_authenticated_agent_from_env(base_dir)
    
    if auth_agent_id is None:
        return False, f"Agent authentication required. Run 'avcpm agent authenticate {agent_id}' and set AVCPM_AGENT_ID and AVCPM_SESSION_TOKEN environment variables."
    
    # Verify the authenticated agent matches the claimed agent
    if auth_agent_id != agent_id:
        return False, f"Agent ID mismatch: authenticated as {auth_agent_id} but claiming to be {agent_id}. Possible impersonation attempt."
    
    # Validate the session
    if not validate_session(agent_id, session_token, base_dir):
        return False, f"Session invalid or expired. Re-authenticate with 'avcpm agent authenticate {agent_id}'."
    
    # Verify agent identity matches signing key
    from avcpm_agent import get_agent, get_public_key
    agent = get_agent(agent_id, base_dir)
    if agent is None:
        return False, f"Agent {agent_id} not found in registry"
    
    if agent.get('agent_id') != agent_id:
        return False, f"Agent ID mismatch in registry data"
    
    # Verify public key exists (prevents impersonation)
    public_key = get_public_key(agent_id, base_dir)
    if not public_key:
        return False, f"Public key not found for agent {agent_id}"
    
    return True, None


def _sanitize_task_id(task_id):
    """Sanitize task ID to prevent path traversal in task filenames."""
    if not task_id or not isinstance(task_id, str):
        raise ValueError("Task ID must be a non-empty string")
    # Reject task IDs with path traversal sequences
    import re
    if re.search(r'\.{2,}[/\\]', task_id) or re.search(r'[/\\]\.{2,}', task_id):
        raise ValueError(f"Invalid task ID (contains path traversal): {task_id}")
    # Reject task IDs with absolute paths
    if os.path.isabs(task_id):
        raise ValueError(f"Absolute paths not allowed in task ID: {task_id}")
    # Reject task IDs with directory separators
    if '/' in task_id or '\\' in task_id:
        raise ValueError(f"Directory separators not allowed in task ID: {task_id}")
    return task_id

def get_tasks_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the tasks directory path."""
    return os.path.join(base_dir, "tasks")

def ensure_directories(base_dir=DEFAULT_BASE_DIR):
    """Ensure task directories exist with symlink protection."""
    protect_avcpm_directory(base_dir)
    tasks_dir = get_tasks_dir(base_dir)
    for col in COLUMNS:
        safe_makedirs(os.path.join(tasks_dir, col), base_dir, exist_ok=True)

def get_task_path(task_id, base_dir=DEFAULT_BASE_DIR):
    """Find the full path of a task file regardless of status."""
    tasks_dir = get_tasks_dir(base_dir)
    sanitized_task_id = _sanitize_task_id(task_id)
    for col in COLUMNS:
        path = os.path.join(tasks_dir, col, f"{sanitized_task_id}.json")
        try:
            # Validate the path is within the base_dir
            safe_path = sanitize_path(os.path.join("tasks", col, f"{sanitized_task_id}.json"), base_dir)
            if os.path.exists(safe_path):
                return safe_path
        except ValueError:
            # Path traversal detected
            continue
    return None

def get_task_status(task_id, base_dir=DEFAULT_BASE_DIR):
    """Get the current status of a task."""
    tasks_dir = get_tasks_dir(base_dir)
    for col in COLUMNS:
        path = os.path.join(tasks_dir, col, f"{task_id}.json")
        if os.path.exists(path):
            return col
    return None

def load_task(task_id, base_dir=DEFAULT_BASE_DIR):
    """Load task data from file."""
    path = get_task_path(task_id, base_dir)
    if path:
        try:
            content = safe_read_text(path, base_dir)
            return json.loads(content)
        except (ValueError, FileNotFoundError, json.JSONDecodeError):
            return None
    return None

def save_task(task_id, task_data, status=None, base_dir=DEFAULT_BASE_DIR):
    """Save task data to file. If status not provided, use current status."""
    if status is None:
        status = get_task_status(task_id, base_dir)
    if status is None:
        return False
    
    tasks_dir = get_tasks_dir(base_dir)
    sanitized_task_id = _sanitize_task_id(task_id)
    
    # Validate status is in allowed columns
    if status not in COLUMNS:
        raise ValueError(f"Invalid status: {status}")
    
    # Build and sanitize the path
    rel_path = os.path.join("tasks", status, f"{sanitized_task_id}.json")
    try:
        safe_path = sanitize_path(rel_path, base_dir)
    except ValueError as e:
        raise ValueError(f"Invalid task path: {e}")
    
    # Ensure directory exists
    safe_makedirs(os.path.dirname(safe_path), base_dir, exist_ok=True)
    
    # Safe write
    safe_write_text(safe_path, json.dumps(task_data, indent=4), base_dir)
    return True

def get_all_tasks(base_dir=DEFAULT_BASE_DIR):
    """Get all tasks across all statuses."""
    tasks = []
    tasks_dir = get_tasks_dir(base_dir)
    for col in COLUMNS:
        col_path = os.path.join(tasks_dir, col)
        try:
            # Sanitize the column path
            safe_col_path = sanitize_path(os.path.join("tasks", col), base_dir)
        except ValueError:
            continue
        
        if os.path.exists(safe_col_path):
            for f in os.listdir(safe_col_path):
                if f.endswith(".json"):
                    task_path = os.path.join(safe_col_path, f)
                    try:
                        content = safe_read_text(task_path, base_dir)
                        tasks.append(json.loads(content))
                    except (ValueError, FileNotFoundError, json.JSONDecodeError, json.JSONDecodeError):
                        continue
    return tasks

# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================

def get_dependencies(task_id, base_dir=DEFAULT_BASE_DIR):
    """Get list of task IDs that this task depends on."""
    task_data = load_task(task_id, base_dir)
    if task_data:
        return task_data.get("depends_on", [])
    return []

def get_dependents(task_id, base_dir=DEFAULT_BASE_DIR):
    """Get list of task IDs that depend on this task."""
    dependents = []
    all_tasks = get_all_tasks(base_dir)
    for task in all_tasks:
        deps = task.get("depends_on", [])
        if task_id in deps:
            dependents.append(task["id"])
    return dependents

def is_dependency_complete(dep_task_id, base_dir=DEFAULT_BASE_DIR):
    """Check if a dependency task is complete (in 'done' status)."""
    return get_task_status(dep_task_id, base_dir) == "done"

def get_blocked_by(task_id, base_dir=DEFAULT_BASE_DIR):
    """Get list of incomplete dependencies blocking this task."""
    deps = get_dependencies(task_id, base_dir)
    blocked_by = []
    for dep in deps:
        if not is_dependency_complete(dep, base_dir):
            blocked_by.append(dep)
    return blocked_by

def is_blocked(task_id, base_dir=DEFAULT_BASE_DIR):
    """Check if task is blocked by incomplete dependencies."""
    return len(get_blocked_by(task_id, base_dir)) > 0

def can_progress(task_id, base_dir=DEFAULT_BASE_DIR):
    """Check if task can progress (all dependencies complete)."""
    deps = get_dependencies(task_id, base_dir)
    if not deps:
        return True
    return all(is_dependency_complete(dep, base_dir) for dep in deps)

def get_blocked_tasks(base_dir=DEFAULT_BASE_DIR):
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

def has_cycle(task_id, base_dir=DEFAULT_BASE_DIR):
    """Check if adding dependencies would create a cycle."""
    visited = set()
    recursion_stack = set()
    return _detect_cycle_dfs(task_id, visited, recursion_stack, base_dir)

def would_create_cycle(task_id, new_dep_id, base_dir=DEFAULT_BASE_DIR):
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
    def reaches(from_id, to_id, visited=None):
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

def add_dependency(task_id, depends_on_task_id, base_dir=DEFAULT_BASE_DIR):
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

def remove_dependency(task_id, depends_on_task_id, base_dir=DEFAULT_BASE_DIR):
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

def show_dependency_graph(task_id, base_dir=DEFAULT_BASE_DIR):
    """Show ASCII art tree of dependencies for a task."""
    lines = _build_dependency_tree(task_id, base_dir)
    return "\n".join(lines)

def show_dependents_graph(task_id, base_dir=DEFAULT_BASE_DIR):
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

def print_help():
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

def create_task(task_id, description, assignee="unassigned", depends_on=None, base_dir=DEFAULT_BASE_DIR):
    tasks_dir = get_tasks_dir(base_dir)
    ensure_directories(base_dir)
    
    # Sanitize task ID
    try:
        sanitized_task_id = _sanitize_task_id(task_id)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    path = os.path.join(tasks_dir, "todo", f"{sanitized_task_id}.json")
    if os.path.exists(path):
        print(f"Error: Task {task_id} already exists.")
        sys.exit(1)
    
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
                print(f"Error: Dependency task '{dep}' not found")
                sys.exit(1)
            if dep == task_id:
                print(f"Error: Task cannot depend on itself")
                sys.exit(1)
    
    task_data = {
        "id": sanitized_task_id,
        "description": description,
        "assignee": assignee,
        "priority": "medium",
        "depends_on": deps_list,
        "status_history": [
            {"status": "todo", "timestamp": datetime.now().isoformat()}
        ]
    }
    
    # Use safe_write for creating the task file
    safe_write_text(path, json.dumps(task_data, indent=4), base_dir)
    
    if deps_list:
        print(f"Task {task_id} created in 'todo' with dependencies: {', '.join(deps_list)}")
    else:
        print(f"Task {task_id} created in 'todo'.")

def move_task(task_id, new_status, force=False, base_dir=DEFAULT_BASE_DIR):
    if new_status not in COLUMNS:
        print(f"Error: Invalid status. Use {COLUMNS}")
        sys.exit(1)
    
    tasks_dir = get_tasks_dir(base_dir)
    
    # Sanitize task ID
    try:
        sanitized_task_id = _sanitize_task_id(task_id)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Find where the task is currently
    current_path = None
    current_status = None
    for col in COLUMNS:
        p = os.path.join(tasks_dir, col, f"{sanitized_task_id}.json")
        try:
            # Validate path is within base_dir
            safe_p = sanitize_path(os.path.join("tasks", col, f"{sanitized_task_id}.json"), base_dir)
            if os.path.exists(safe_p):
                current_path = safe_p
                current_status = col
                break
        except ValueError:
            continue
    
    if not current_path:
        print(f"Error: Task {task_id} not found.")
        sys.exit(1)
    
    # Load task data
    try:
        task_data = json.loads(safe_read_text(current_path, base_dir))
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: Failed to load task: {e}")
        sys.exit(1)
    
    # Check dependencies before moving to in-progress or review
    if new_status in ["in-progress", "review"] and not force:
        blocked_by = get_blocked_by(task_id, base_dir)
        if blocked_by:
            print(f"Error: Task {task_id} is blocked by incomplete dependencies: {', '.join(blocked_by)}")
            print(f"Use --force to override (admin/debug)")
            sys.exit(1)
    
    # Update status history
    task_data["status_history"].append({
        "status": new_status,
        "timestamp": datetime.now().isoformat()
    })
    
    # Move file
    new_path = os.path.join(tasks_dir, new_status, f"{sanitized_task_id}.json")
    try:
        safe_new_path = sanitize_path(os.path.join("tasks", new_status, f"{sanitized_task_id}.json"), base_dir)
    except ValueError as e:
        print(f"Error: Invalid destination path: {e}")
        sys.exit(1)
    
    # Ensure destination directory exists
    safe_makedirs(os.path.dirname(safe_new_path), base_dir, exist_ok=True)
    
    # Move using shutil (moving within same base_dir is safe)
    shutil.move(current_path, safe_new_path)
    
    # Write updated task data
    safe_write_text(safe_new_path, json.dumps(task_data, indent=4), base_dir)
    
    if force and new_status in ["in-progress", "review"]:
        print(f"Task {task_id} moved to {new_status} (forced, bypassed dependency check).")
    else:
        print(f"Task {task_id} moved to {new_status}.")

def list_tasks(base_dir=DEFAULT_BASE_DIR):
    tasks_dir = get_tasks_dir(base_dir)
    
    for col in COLUMNS:
        print(f"\n--- {col.upper()} ---")
        try:
            col_path = sanitize_path(os.path.join("tasks", col), base_dir)
        except ValueError:
            print(" (empty)")
            continue
            
        if not os.path.exists(col_path):
            print(" (empty)")
            continue
        files = [f for f in os.listdir(col_path) if f.endswith(".json")]
        if not files:
            print(" (empty)")
        for f in files:
            task_path = os.path.join(col_path, f)
            try:
                content = safe_read_text(task_path, base_dir)
                data = json.loads(content)
                deps = data.get("depends_on", [])
                blocked = is_blocked(data['id'], base_dir) if deps else False
                status_marker = " [BLOCKED]" if blocked else ""
                deps_info = f" (deps: {', '.join(deps)})" if deps else ""
                print(f"[{data['id']}] {data['description']} ({data['assignee']}){deps_info}{status_marker}")
            except (ValueError, FileNotFoundError, json.JSONDecodeError):
                continue

def list_blocked(base_dir=DEFAULT_BASE_DIR):
    """List all tasks blocked by incomplete dependencies."""
    blocked = get_blocked_tasks(base_dir)
    if not blocked:
        print("No tasks are currently blocked.")
        return
    
    print("\n--- BLOCKED TASKS ---")
    for task in blocked:
        print(f"[{task['id']}] {task['description']}")
        print(f"    Blocked by: {', '.join(task['blocked_by'])}")

def deps_add(task_id, depends_on_id, base_dir=DEFAULT_BASE_DIR):
    """CLI handler for adding dependencies."""
    try:
        add_dependency(task_id, depends_on_id, base_dir)
        print(f"Added dependency: {task_id} now depends on {depends_on_id}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

def deps_remove(task_id, depends_on_id, base_dir=DEFAULT_BASE_DIR):
    """CLI handler for removing dependencies."""
    try:
        if remove_dependency(task_id, depends_on_id, base_dir):
            print(f"Removed dependency: {task_id} no longer depends on {depends_on_id}")
        else:
            print(f"Task {task_id} did not depend on {depends_on_id}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

def deps_show(task_id, base_dir=DEFAULT_BASE_DIR):
    """CLI handler for showing dependency graph."""
    print(show_dependency_graph(task_id, base_dir))

def deps_dependents(task_id, base_dir=DEFAULT_BASE_DIR):
    """CLI handler for showing tasks that depend on this one."""
    print(show_dependents_graph(task_id, base_dir))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    
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
        # Remove --force from args if present
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
