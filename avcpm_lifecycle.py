#!/usr/bin/env python3
"""
AVCPM Task Lifecycle Management
Automated task transitions based on git-like events (commit, merge, review).
"""

import os
import sys
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# Import existing AVCPM modules
from avcpm_task import (
    load_task, save_task, get_task_status, get_task_path,
    get_all_tasks, get_blocked_by, can_progress, COLUMNS,
    DEFAULT_BASE_DIR as TASK_DEFAULT_BASE_DIR
)
from avcpm_agent import get_agent

DEFAULT_BASE_DIR = ".avcpm"

# Lifecycle configuration file
LIFECYCLE_CONFIG_FILE = "lifecycle.json"

# Valid status transitions (manual and automatic)
VALID_TRANSITIONS = {
    "todo": ["in-progress"],
    "in-progress": ["review", "todo"],
    "review": ["done", "in-progress"],
    "done": ["review"]  # Allow rollback for corrections
}

# Auto-transition rules
AUTO_TRANSITIONS = {
    "on_first_commit": {"from": "todo", "to": "in-progress"},
    "on_commit": {"from": "in-progress", "to": "review"},
    "on_merge_approval": {"from": "review", "to": "done"},
    "on_review_rejection": {"from": "review", "to": "in-progress"}
}


class LifecycleError(Exception):
    """Exception for lifecycle-related errors."""
    pass


class ValidationError(LifecycleError):
    """Exception for validation failures."""
    pass


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

def get_lifecycle_config_path(base_dir=DEFAULT_BASE_DIR) -> str:
    """Get the path to the lifecycle configuration file."""
    return os.path.join(base_dir, LIFECYCLE_CONFIG_FILE)


def load_lifecycle_config(base_dir=DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """
    Load lifecycle configuration.
    
    Returns:
        dict: Configuration with auto-transition settings per task type
    """
    config_path = get_lifecycle_config_path(base_dir)
    
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    
    # Return default configuration
    return get_default_lifecycle_config()


def get_default_lifecycle_config() -> Dict[str, Any]:
    """Get the default lifecycle configuration."""
    return {
        "version": "1.0",
        "enabled": True,
        "task_types": {
            "default": {
                "auto_transitions": {
                    "on_first_commit": True,
                    "on_commit": True,
                    "on_merge_approval": True,
                    "on_review_rejection": True
                },
                "require_assignee_match": True,
                "require_dependencies_complete": True,
                "require_review_approval": True
            },
            "bugfix": {
                "auto_transitions": {
                    "on_first_commit": True,
                    "on_commit": True,
                    "on_merge_approval": True,
                    "on_review_rejection": True
                },
                "require_assignee_match": True,
                "require_dependencies_complete": False,  # Bug fixes can bypass deps
                "require_review_approval": True
            },
            "hotfix": {
                "auto_transitions": {
                    "on_first_commit": True,
                    "on_commit": False,  # Hotfixes may skip review
                    "on_merge_approval": True,
                    "on_review_rejection": False
                },
                "require_assignee_match": False,  # Hotfixes can be committed by anyone
                "require_dependencies_complete": False,
                "require_review_approval": False  # Hotfixes may bypass review
            }
        },
        "manual_override": {
            "enabled": True,
            "requires_admin": False
        }
    }


def save_lifecycle_config(config: Dict[str, Any], base_dir=DEFAULT_BASE_DIR) -> bool:
    """Save lifecycle configuration."""
    config_path = get_lifecycle_config_path(base_dir)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    return True


def init_lifecycle_config(base_dir=DEFAULT_BASE_DIR) -> bool:
    """Initialize lifecycle configuration with defaults."""
    config_path = get_lifecycle_config_path(base_dir)
    
    if os.path.exists(config_path):
        return False  # Already exists
    
    config = get_default_lifecycle_config()
    return save_lifecycle_config(config, base_dir)


def get_task_type_config(task_type: str, base_dir=DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """Get configuration for a specific task type."""
    config = load_lifecycle_config(base_dir)
    task_types = config.get("task_types", {})
    
    # Return task type config or default
    return task_types.get(task_type, task_types.get("default", {}))


# ============================================================================
# STATUS MANAGEMENT
# ============================================================================

def get_task_commits_dir(base_dir=DEFAULT_BASE_DIR) -> str:
    """Get directory for storing task commit history."""
    return os.path.join(base_dir, "task_commits")


def ensure_task_commits_dir(base_dir=DEFAULT_BASE_DIR) -> None:
    """Ensure task commits directory exists."""
    os.makedirs(get_task_commits_dir(base_dir), exist_ok=True)


def get_task_commits(task_id: str, base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    """Get commit history for a task."""
    commits_file = os.path.join(get_task_commits_dir(base_dir), f"{task_id}.json")
    
    if os.path.exists(commits_file):
        with open(commits_file, "r") as f:
            return json.load(f)
    return []


def record_task_commit(task_id: str, commit_id: str, agent_id: str, 
                        base_dir=DEFAULT_BASE_DIR) -> bool:
    """Record a commit for a task."""
    ensure_task_commits_dir(base_dir)
    
    commits = get_task_commits(task_id, base_dir)
    commits.append({
        "commit_id": commit_id,
        "agent_id": agent_id,
        "timestamp": datetime.now().isoformat()
    })
    
    commits_file = os.path.join(get_task_commits_dir(base_dir), f"{task_id}.json")
    with open(commits_file, "w") as f:
        json.dump(commits, f, indent=4)
    
    return True


def is_first_commit(task_id: str, base_dir=DEFAULT_BASE_DIR) -> bool:
    """Check if this is the first commit for a task."""
    commits = get_task_commits(task_id, base_dir)
    return len(commits) == 0


def transition_task(task_id: str, new_status: str, reason: str = None,
                   base_dir=DEFAULT_BASE_DIR, force: bool = False) -> Tuple[bool, str]:
    """
    Transition a task to a new status.
    
    Args:
        task_id: Task ID
        new_status: Target status
        reason: Reason for transition
        base_dir: Base directory
        force: Force transition even if invalid
        
    Returns:
        Tuple of (success, message)
    """
    current_status = get_task_status(task_id, base_dir)
    
    if not current_status:
        return False, f"Task {task_id} not found"
    
    if current_status == new_status:
        return True, f"Task {task_id} already in {new_status}"
    
    # Validate transition
    if not force:
        valid_next = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next:
            return False, f"Invalid transition: {current_status} -> {new_status}"
    
    # Load task data
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return False, f"Failed to load task {task_id}"
    
    # Update status history
    if "status_history" not in task_data:
        task_data["status_history"] = []
    
    task_data["status_history"].append({
        "status": new_status,
        "timestamp": datetime.now().isoformat(),
        "reason": reason or "Manual transition"
    })
    
    # Move task file to new column
    tasks_dir = os.path.join(base_dir, "tasks")
    old_path = os.path.join(tasks_dir, current_status, f"{task_id}.json")
    new_path = os.path.join(tasks_dir, new_status, f"{task_id}.json")
    
    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    
    with open(old_path, "r") as f:
        data = json.load(f)
    
    data["status_history"] = task_data["status_history"]
    
    with open(new_path, "w") as f:
        json.dump(data, f, indent=4)
    
    os.remove(old_path)
    
    return True, f"Task {task_id} transitioned: {current_status} -> {new_status}"


# ============================================================================
# VALIDATION RULES
# ============================================================================

def validate_commit_allowed(task_id: str, agent_id: str, 
                            base_dir=DEFAULT_BASE_DIR) -> Tuple[bool, str]:
    """
    Validate if commit is allowed for this task.
    
    Checks:
    - Task exists
    - Task is assigned to committing agent (if required)
    - Task dependencies are complete (if required)
    
    Returns:
        Tuple of (allowed, message)
    """
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return False, f"Task {task_id} not found"
    
    task_type = task_data.get("type", "default")
    config = get_task_type_config(task_type, base_dir)
    
    # Check assignee match
    if config.get("require_assignee_match", True):
        assignee = task_data.get("assignee", "unassigned")
        agent = get_agent(agent_id, base_dir)
        
        if agent and assignee != "unassigned":
            # Allow if agent name matches assignee or agent_id matches
            agent_name = agent.get("name", "")
            if agent_id != assignee and agent_name != assignee:
                return False, f"Task {task_id} is assigned to {assignee}, not {agent_id}"
    
    # Check dependencies
    if config.get("require_dependencies_complete", True):
        blocked_by = get_blocked_by(task_id, base_dir)
        if blocked_by:
            return False, f"Task {task_id} has incomplete dependencies: {', '.join(blocked_by)}"
    
    return True, "Commit validation passed"


def validate_merge_allowed(task_id: str, commit_id: str = None,
                          base_dir=DEFAULT_BASE_DIR) -> Tuple[bool, str]:
    """
    Validate if merge is allowed for this task.
    
    Checks:
    - Task is in review status
    - Review has been approved
    
    Returns:
        Tuple of (allowed, message)
    """
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return False, f"Task {task_id} not found"
    
    status = get_task_status(task_id, base_dir)
    
    task_type = task_data.get("type", "default")
    config = get_task_type_config(task_type, base_dir)
    
    # Check if review is required
    if config.get("require_review_approval", True):
        reviews_dir = os.path.join(base_dir, "reviews")
        
        # Find review file for the commit
        if commit_id:
            review_path = os.path.join(reviews_dir, f"{commit_id}.review")
        else:
            # Look for any review for this task
            review_path = None
            if os.path.exists(reviews_dir):
                for f in os.listdir(reviews_dir):
                    if f.endswith(".review"):
                        path = os.path.join(reviews_dir, f)
                        with open(path, "r") as rf:
                            content = rf.read()
                            if f"Task: {task_id}" in content or f'"task_id": "{task_id}"' in content:
                                review_path = path
                                break
        
        if not review_path or not os.path.exists(review_path):
            return False, f"No review found for task {task_id}"
        
        with open(review_path, "r") as f:
            content = f.read()
        
        if "APPROVED" not in content:
            return False, f"Review not approved for task {task_id}"
    
    return True, "Merge validation passed"


# ============================================================================
# LIFECYCLE HOOKS
# ============================================================================

def on_commit(task_id: str, commit_id: str, agent_id: str, 
              base_dir=DEFAULT_BASE_DIR) -> Tuple[bool, str]:
    """
    Lifecycle hook called when a commit is made.
    
    Auto-transitions:
    - todo -> in-progress: On first commit
    - in-progress -> review: On commit creation (if enabled)
    
    Args:
        task_id: Task ID
        commit_id: Commit ID
        agent_id: Agent making the commit
        base_dir: Base directory
        
    Returns:
        Tuple of (success, message)
    """
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return False, f"Task {task_id} not found"
    
    task_type = task_data.get("type", "default")
    config = get_task_type_config(task_type, base_dir)
    
    # Record the commit
    record_task_commit(task_id, commit_id, agent_id, base_dir)
    
    # Check if auto-transitions are enabled
    if not config.get("auto_transitions", {}).get("on_commit", True):
        return True, f"Commit recorded for {task_id}. Auto-transitions disabled."
    
    current_status = get_task_status(task_id, base_dir)
    
    # First commit: todo -> in-progress
    if current_status == "todo":
        if not config.get("auto_transitions", {}).get("on_first_commit", True):
            return True, f"Commit recorded for {task_id}. First commit auto-transition disabled."
        
        success, msg = transition_task(
            task_id, "in-progress", 
            f"Auto-transition: first commit by {agent_id} ({commit_id})",
            base_dir
        )
        return success, f"Commit recorded. {msg}"
    
    # Subsequent commits: in-progress -> review
    elif current_status == "in-progress":
        if not config.get("auto_transitions", {}).get("on_commit", True):
            return True, f"Commit recorded for {task_id}. Commit auto-transition disabled."
        
        # Validate dependencies before transition
        if config.get("require_dependencies_complete", True):
            blocked_by = get_blocked_by(task_id, base_dir)
            if blocked_by:
                return True, f"Commit recorded for {task_id}. Transition to review blocked by dependencies: {', '.join(blocked_by)}"
        
        success, msg = transition_task(
            task_id, "review",
            f"Auto-transition: commit by {agent_id} ({commit_id})",
            base_dir
        )
        return success, f"Commit recorded. {msg}"
    
    return True, f"Commit recorded for {task_id}. No transition needed (status: {current_status})"


def on_merge(task_id: str, commit_id: str, agent_id: str,
             base_dir=DEFAULT_BASE_DIR) -> Tuple[bool, str]:
    """
    Lifecycle hook called when a commit is merged.
    
    Auto-transitions:
    - review -> done: On merge approval
    
    Args:
        task_id: Task ID
        commit_id: Commit ID being merged
        agent_id: Agent performing the merge
        base_dir: Base directory
        
    Returns:
        Tuple of (success, message)
    """
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return False, f"Task {task_id} not found"
    
    task_type = task_data.get("type", "default")
    config = get_task_type_config(task_type, base_dir)
    
    # Validate merge is allowed
    allowed, msg = validate_merge_allowed(task_id, commit_id, base_dir)
    if not allowed:
        return False, f"Merge validation failed: {msg}"
    
    current_status = get_task_status(task_id, base_dir)
    
    # review -> done on merge approval
    if current_status == "review":
        if not config.get("auto_transitions", {}).get("on_merge_approval", True):
            return True, f"Merge completed for {task_id}. Auto-transition to done disabled."
        
        success, msg = transition_task(
            task_id, "done",
            f"Auto-transition: merged by {agent_id} ({commit_id})",
            base_dir
        )
        return success, f"Merge completed. {msg}"
    
    return True, f"Merge completed for {task_id}. No transition needed (status: {current_status})"


def on_review(task_id: str, review_status: str, 
              base_dir=DEFAULT_BASE_DIR) -> Tuple[bool, str]:
    """
    Lifecycle hook called when a review is submitted.
    
    Auto-transitions:
    - review -> done: On review approval
    - review -> in-progress: On review rejection
    
    Args:
        task_id: Task ID
        review_status: "approved" or "rejected"
        base_dir: Base directory
        
    Returns:
        Tuple of (success, message)
    """
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return False, f"Task {task_id} not found"
    
    task_type = task_data.get("type", "default")
    config = get_task_type_config(task_type, base_dir)
    
    current_status = get_task_status(task_id, base_dir)
    
    if review_status == "approved":
        if current_status == "review":
            if not config.get("auto_transitions", {}).get("on_merge_approval", True):
                return True, f"Review approved for {task_id}. Auto-transition to done disabled."
            
            success, msg = transition_task(
                task_id, "done",
                "Auto-transition: review approved",
                base_dir
            )
            return success, f"Review approved. {msg}"
        
        return True, f"Review approved for {task_id}. No transition needed (status: {current_status})"
    
    elif review_status == "rejected":
        if current_status == "review":
            if not config.get("auto_transitions", {}).get("on_review_rejection", True):
                return True, f"Review rejected for {task_id}. Auto-transition to in-progress disabled."
            
            success, msg = transition_task(
                task_id, "in-progress",
                "Auto-transition: review rejected",
                base_dir
            )
            return success, f"Review rejected. {msg}"
        
        return True, f"Review rejected for {task_id}. No transition needed (status: {current_status})"
    
    return False, f"Invalid review status: {review_status}"


# ============================================================================
# CLI INTERFACE
# ============================================================================

def cmd_status(task_id: str, base_dir=DEFAULT_BASE_DIR) -> str:
    """Show current status of a task."""
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return f"Error: Task {task_id} not found"
    
    status = get_task_status(task_id, base_dir)
    task_type = task_data.get("type", "default")
    assignee = task_data.get("assignee", "unassigned")
    description = task_data.get("description", "No description")
    
    commits = get_task_commits(task_id, base_dir)
    
    lines = [
        f"Task: {task_id}",
        f"Description: {description}",
        f"Status: {status}",
        f"Type: {task_type}",
        f"Assignee: {assignee}",
        f"Commits: {len(commits)}"
    ]
    
    if commits:
        lines.append("Commit History:")
        for commit in commits:
            lines.append(f"  - {commit['commit_id']} by {commit['agent_id']} at {commit['timestamp']}")
    
    status_history = task_data.get("status_history", [])
    if status_history:
        lines.append("Status History:")
        for entry in status_history:
            reason = entry.get("reason", "")
            lines.append(f"  - {entry['status']} at {entry['timestamp']}{f' ({reason})' if reason else ''}")
    
    return "\n".join(lines)


def cmd_transitions(task_id: str, base_dir=DEFAULT_BASE_DIR) -> str:
    """Show possible transitions for a task."""
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return f"Error: Task {task_id} not found"
    
    status = get_task_status(task_id, base_dir)
    task_type = task_data.get("type", "default")
    config = get_task_type_config(task_type, base_dir)
    
    lines = [
        f"Task: {task_id}",
        f"Current Status: {status}",
        f"Type: {task_type}",
        "",
        "Valid Transitions:"
    ]
    
    valid = VALID_TRANSITIONS.get(status, [])
    if valid:
        for next_status in valid:
            lines.append(f"  {status} -> {next_status}")
    else:
        lines.append("  (none - terminal status)")
    
    lines.extend([
        "",
        "Auto-Transition Settings:",
        f"  On first commit (todo -> in-progress): {config.get('auto_transitions', {}).get('on_first_commit', True)}",
        f"  On commit (in-progress -> review): {config.get('auto_transitions', {}).get('on_commit', True)}",
        f"  On merge approval (review -> done): {config.get('auto_transitions', {}).get('on_merge_approval', True)}",
        f"  On review rejection (review -> in-progress): {config.get('auto_transitions', {}).get('on_review_rejection', True)}"
    ])
    
    # Check what's blocking transitions
    blocked_by = get_blocked_by(task_id, base_dir)
    if blocked_by:
        lines.extend([
            "",
            f"Blocked by incomplete dependencies: {', '.join(blocked_by)}"
        ])
    
    return "\n".join(lines)


def cmd_validate(task_id: str, action: str, agent_id: str = None,
                base_dir=DEFAULT_BASE_DIR) -> str:
    """Validate if an action is allowed."""
    task_data = load_task(task_id, base_dir)
    if not task_data:
        return f"Error: Task {task_id} not found"
    
    lines = [f"Validation for {action} on task {task_id}", ""]
    
    if action == "commit":
        if not agent_id:
            return "Error: agent_id required for commit validation"
        
        allowed, msg = validate_commit_allowed(task_id, agent_id, base_dir)
        lines.append(f"Result: {'PASS' if allowed else 'FAIL'}")
        lines.append(f"Message: {msg}")
        
        # Additional info
        assignee = task_data.get("assignee", "unassigned")
        blocked_by = get_blocked_by(task_id, base_dir)
        
        lines.extend([
            "",
            "Details:",
            f"  Assignee: {assignee}",
            f"  Committing Agent: {agent_id}",
            f"  Blocked by: {', '.join(blocked_by) if blocked_by else '(none)'}",
            f"  Dependencies Complete: {len(blocked_by) == 0}"
        ])
        
    elif action == "merge":
        allowed, msg = validate_merge_allowed(task_id, None, base_dir)
        lines.append(f"Result: {'PASS' if allowed else 'FAIL'}")
        lines.append(f"Message: {msg}")
        
        status = get_task_status(task_id, base_dir)
        lines.extend([
            "",
            "Details:",
            f"  Current Status: {status}",
            f"  In Review: {status == 'review'}"
        ])
        
    else:
        return f"Error: Unknown action '{action}'. Use 'commit' or 'merge'"
    
    return "\n".join(lines)


def cmd_init(base_dir=DEFAULT_BASE_DIR) -> str:
    """Initialize lifecycle configuration."""
    if init_lifecycle_config(base_dir):
        return f"Lifecycle configuration initialized at {get_lifecycle_config_path(base_dir)}"
    return f"Lifecycle configuration already exists at {get_lifecycle_config_path(base_dir)}"


def cmd_config(base_dir=DEFAULT_BASE_DIR) -> str:
    """Show lifecycle configuration."""
    config = load_lifecycle_config(base_dir)
    return json.dumps(config, indent=2)


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def get_task_from_commit(commit_id: str, base_dir=DEFAULT_BASE_DIR) -> Optional[str]:
    """Get task ID associated with a commit."""
    ledger_dir = os.path.join(base_dir, "ledger")
    ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    
    if os.path.exists(ledger_path):
        with open(ledger_path, "r") as f:
            data = json.load(f)
            return data.get("task_id")
    
    return None


def lifecycle_hook_enabled(hook_name: str, task_type: str = "default",
                            base_dir=DEFAULT_BASE_DIR) -> bool:
    """Check if a lifecycle hook is enabled for a task type."""
    config = load_lifecycle_config(base_dir)
    
    if not config.get("enabled", True):
        return False
    
    task_config = get_task_type_config(task_type, base_dir)
    return task_config.get("auto_transitions", {}).get(hook_name, True)


def print_help() -> None:
    """Print CLI help message."""
    print("AVCPM Task Lifecycle Management")
    print("Usage:")
    print("  python avcpm_lifecycle.py init")
    print("  python avcpm_lifecycle.py status <task_id>")
    print("  python avcpm_lifecycle.py transitions <task_id>")
    print("  python avcpm_lifecycle.py validate <task_id> --action <commit|merge> [--agent <agent_id>]")
    print("  python avcpm_lifecycle.py config")
    print("")
    print("Hooks (called by other modules):")
    print("  on_commit(task_id, commit_id, agent_id) - Auto-transition on commit")
    print("  on_merge(task_id, commit_id, agent_id) - Auto-transition on merge")
    print("  on_review(task_id, review_status) - Handle review approval/rejection")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        print(cmd_init())
    
    elif cmd == "status":
        if len(sys.argv) < 3:
            print("Error: status requires task_id")
            sys.exit(1)
        print(cmd_status(sys.argv[2]))
    
    elif cmd == "transitions":
        if len(sys.argv) < 3:
            print("Error: transitions requires task_id")
            sys.exit(1)
        print(cmd_transitions(sys.argv[2]))
    
    elif cmd == "validate":
        if len(sys.argv) < 4:
            print("Error: validate requires task_id and --action")
            sys.exit(1)
        
        task_id = sys.argv[2]
        action = None
        agent_id = None
        
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--action" and i + 1 < len(sys.argv):
                action = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--agent" and i + 1 < len(sys.argv):
                agent_id = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        if not action:
            print("Error: --action required")
            sys.exit(1)
        
        if action == "commit" and not agent_id:
            print("Error: --agent required for commit validation")
            sys.exit(1)
        
        print(cmd_validate(task_id, action, agent_id))
    
    elif cmd == "config":
        print(cmd_config())
    
    elif cmd == "--help" or cmd == "-h":
        print_help()
    
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        sys.exit(1)
