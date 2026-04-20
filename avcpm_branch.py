"""
AVCPM Branch Management System

Provides git-like branching functionality for AVCPM.
Each branch has its own staging area and metadata.
"""

import os
import sys
import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path

DEFAULT_BASE_DIR = ".avcpm"

# Branch statuses
BRANCH_STATUS_ACTIVE = "active"
BRANCH_STATUS_MERGED = "merged"
BRANCH_STATUS_DELETED = "deleted"


def get_branches_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the branches directory path."""
    return os.path.join(base_dir, "branches")


def get_branch_dir(branch_name, base_dir=DEFAULT_BASE_DIR):
    """Get a specific branch's directory path."""
    return os.path.join(get_branches_dir(base_dir), branch_name)


def get_branch_metadata_path(branch_name, base_dir=DEFAULT_BASE_DIR):
    """Get the path to a branch's metadata file."""
    return os.path.join(get_branch_dir(branch_name, base_dir), "branch.json")


def get_branch_staging_dir(branch_name, base_dir=DEFAULT_BASE_DIR):
    """Get the staging directory for a specific branch."""
    return os.path.join(get_branch_dir(branch_name, base_dir), "staging")


def get_branch_ledger_dir(branch_name, base_dir=DEFAULT_BASE_DIR):
    """Get the ledger directory for a specific branch."""
    return os.path.join(get_branch_dir(branch_name, base_dir), "ledger")


def get_config_path(base_dir=DEFAULT_BASE_DIR):
    """Get the config.json file path."""
    return os.path.join(base_dir, "config.json")


def _load_config(base_dir=DEFAULT_BASE_DIR):
    """Load the AVCPM config."""
    config_path = get_config_path(base_dir)
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


def _save_config(config, base_dir=DEFAULT_BASE_DIR):
    """Save the AVCPM config."""
    os.makedirs(base_dir, exist_ok=True)
    config_path = get_config_path(base_dir)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def _generate_branch_id():
    """Generate a unique branch ID."""
    return str(uuid.uuid4())[:12]


def _ensure_main_branch(base_dir=DEFAULT_BASE_DIR):
    """Ensure the main branch exists, creating it if necessary."""
    branches_dir = get_branches_dir(base_dir)
    main_branch_dir = get_branch_dir("main", base_dir)
    
    if not os.path.exists(main_branch_dir):
        os.makedirs(main_branch_dir, exist_ok=True)
        os.makedirs(get_branch_staging_dir("main", base_dir), exist_ok=True)
        os.makedirs(get_branch_ledger_dir("main", base_dir), exist_ok=True)
        
        # Create main branch metadata
        branch_metadata = {
            "branch_id": _generate_branch_id(),
            "name": "main",
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "parent_branch": None,
            "parent_commit": None,
            "task_id": None,
            "status": BRANCH_STATUS_ACTIVE
        }
        
        with open(get_branch_metadata_path("main", base_dir), "w") as f:
            json.dump(branch_metadata, f, indent=4)


def _is_ancestor(branch_name, potential_ancestor, base_dir=DEFAULT_BASE_DIR):
    """Check if potential_ancestor is in the ancestry chain of branch_name."""
    visited = set()
    current = branch_name
    
    while current:
        if current in visited:
            # Circular reference detected
            return True
        visited.add(current)
        
        if current == potential_ancestor:
            return True
        
        # Get parent of current branch
        metadata_path = get_branch_metadata_path(current, base_dir)
        if not os.path.exists(metadata_path):
            break
        
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        current = metadata.get("parent_branch")
    
    return False


def create_branch(name, parent_branch="main", task_id=None, agent_id=None, base_dir=DEFAULT_BASE_DIR):
    """
    Create a new branch.
    
    Args:
        name: Name of the new branch
        parent_branch: Parent branch to branch from (default: "main")
        task_id: Optional task ID associated with this branch
        agent_id: Optional agent ID who created this branch
        base_dir: Base directory for AVCPM
        
    Returns:
        dict: Branch metadata
        
    Raises:
        ValueError: If branch name is invalid or already exists
    """
    # Ensure main branch exists first
    _ensure_main_branch(base_dir)
    
    # Validate branch name
    if not name or not isinstance(name, str):
        raise ValueError("Branch name must be a non-empty string")
    
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError(f"Invalid branch name: {name}")
    
    if name in [".", ".."]:
        raise ValueError(f"Reserved branch name: {name}")
    
    branch_dir = get_branch_dir(name, base_dir)
    if os.path.exists(branch_dir):
        raise ValueError(f"Branch '{name}' already exists")
    
    # Validate parent branch exists
    parent_branch_dir = get_branch_dir(parent_branch, base_dir)
    if not os.path.exists(parent_branch_dir):
        raise ValueError(f"Parent branch '{parent_branch}' does not exist")
    
    # Check for circular parent (branch can't be its own ancestor)
    if _is_ancestor(parent_branch, name, base_dir):
        raise ValueError(f"Circular parent reference: '{parent_branch}' is derived from '{name}'")
    
    # Get parent branch's latest commit
    parent_commit = None
    parent_ledger_dir = get_branch_ledger_dir(parent_branch, base_dir)
    if os.path.exists(parent_ledger_dir):
        commits = sorted([f for f in os.listdir(parent_ledger_dir) if f.endswith(".json")])
        if commits:
            # Get the latest commit ID from the most recent commit file
            latest_commit_file = commits[-1]
            parent_commit = latest_commit_file.replace(".json", "")
    
    # Create branch directory structure
    os.makedirs(branch_dir, exist_ok=True)
    os.makedirs(get_branch_staging_dir(name, base_dir), exist_ok=True)
    os.makedirs(get_branch_ledger_dir(name, base_dir), exist_ok=True)
    
    # Create branch metadata
    branch_metadata = {
        "branch_id": _generate_branch_id(),
        "name": name,
        "created_by": agent_id or "unknown",
        "created_at": datetime.now().isoformat(),
        "parent_branch": parent_branch,
        "parent_commit": parent_commit,
        "task_id": task_id,
        "status": BRANCH_STATUS_ACTIVE
    }
    
    metadata_path = get_branch_metadata_path(name, base_dir)
    with open(metadata_path, "w") as f:
        json.dump(branch_metadata, f, indent=4)
    
    return branch_metadata


def list_branches(base_dir=DEFAULT_BASE_DIR):
    """
    List all branches with their metadata.
    
    Args:
        base_dir: Base directory for AVCPM
        
    Returns:
        list: List of branch metadata dictionaries
    """
    _ensure_main_branch(base_dir)
    
    branches = []
    branches_dir = get_branches_dir(base_dir)
    
    if not os.path.exists(branches_dir):
        return branches
    
    for branch_name in sorted(os.listdir(branches_dir)):
        branch_dir = os.path.join(branches_dir, branch_name)
        if os.path.isdir(branch_dir):
            metadata = get_branch(branch_name, base_dir)
            if metadata:
                branches.append(metadata)
    
    return branches


def get_branch(name, base_dir=DEFAULT_BASE_DIR):
    """
    Get branch details/metadata.
    
    Args:
        name: Branch name
        base_dir: Base directory for AVCPM
        
    Returns:
        dict: Branch metadata or None if branch doesn't exist
    """
    metadata_path = get_branch_metadata_path(name, base_dir)
    if not os.path.exists(metadata_path):
        return None
    
    with open(metadata_path, "r") as f:
        return json.load(f)


def switch_branch(name, base_dir=DEFAULT_BASE_DIR):
    """
    Set the current/active branch.
    
    Args:
        name: Branch name to switch to
        base_dir: Base directory for AVCPM
        
    Returns:
        dict: Branch metadata of the switched-to branch
        
    Raises:
        ValueError: If branch doesn't exist
    """
    # Ensure main branch exists
    _ensure_main_branch(base_dir)
    
    # Validate branch exists
    branch_dir = get_branch_dir(name, base_dir)
    if not os.path.exists(branch_dir):
        raise ValueError(f"Branch '{name}' does not exist")
    
    # Update config
    config = _load_config(base_dir)
    config["current_branch"] = name
    _save_config(config, base_dir)
    
    return get_branch(name, base_dir)


def get_current_branch(base_dir=DEFAULT_BASE_DIR):
    """
    Get the name of the currently active branch.
    
    Args:
        base_dir: Base directory for AVCPM
        
    Returns:
        str: Name of current branch, or "main" if not set
    """
    _ensure_main_branch(base_dir)
    
    config = _load_config(base_dir)
    return config.get("current_branch", "main")


def delete_branch(name, force=False, base_dir=DEFAULT_BASE_DIR):
    """
    Delete a branch.
    
    Args:
        name: Branch name to delete
        force: If True, delete even if branch is protected or has unmerged changes
        base_dir: Base directory for AVCPM
        
    Returns:
        bool: True if deleted successfully
        
    Raises:
        ValueError: If branch doesn't exist, is protected, or has unmerged changes
    """
    # Cannot delete current branch
    current = get_current_branch(base_dir)
    if name == current:
        raise ValueError(f"Cannot delete the currently active branch '{name}'. Switch to another branch first.")
    
    # Main branch is protected
    if name == "main" and not force:
        raise ValueError("Cannot delete 'main' branch without force flag")
    
    branch_dir = get_branch_dir(name, base_dir)
    if not os.path.exists(branch_dir):
        raise ValueError(f"Branch '{name}' does not exist")
    
    # Check if branch has unmerged changes (commits not in any other branch)
    if not force:
        branch_ledger_dir = get_branch_ledger_dir(name, base_dir)
        if os.path.exists(branch_ledger_dir):
            branch_commits = set(f for f in os.listdir(branch_ledger_dir) if f.endswith(".json"))
            
            # Check if these commits exist in other branches
            branches_dir = get_branches_dir(base_dir)
            for other_branch in os.listdir(branches_dir):
                if other_branch == name:
                    continue
                other_ledger_dir = get_branch_ledger_dir(other_branch, base_dir)
                if os.path.exists(other_ledger_dir):
                    other_commits = set(f for f in os.listdir(other_ledger_dir) if f.endswith(".json"))
                    branch_commits -= other_commits
            
            if branch_commits:
                raise ValueError(f"Branch '{name}' has unmerged commits. Use force=True to delete anyway.")
    
    # Check if other branches depend on this one
    if not force:
        branches = list_branches(base_dir)
        dependents = [b["name"] for b in branches if b.get("parent_branch") == name and b["status"] == BRANCH_STATUS_ACTIVE]
        if dependents:
            raise ValueError(f"Cannot delete '{name}': branches {dependents} depend on it. Use force=True to delete anyway.")
    
    # Delete the branch directory
    shutil.rmtree(branch_dir)
    
    return True


def rename_branch(old_name, new_name, base_dir=DEFAULT_BASE_DIR):
    """
    Rename a branch.
    
    Args:
        old_name: Current branch name
        new_name: New branch name
        base_dir: Base directory for AVCPM
        
    Returns:
        dict: Updated branch metadata
        
    Raises:
        ValueError: If old branch doesn't exist or new name is invalid/ taken
    """
    # Validate old branch exists
    old_branch_dir = get_branch_dir(old_name, base_dir)
    if not os.path.exists(old_branch_dir):
        raise ValueError(f"Branch '{old_name}' does not exist")
    
    # Validate new name
    if not new_name or not isinstance(new_name, str):
        raise ValueError("New branch name must be a non-empty string")
    
    if "/" in new_name or "\\" in new_name or new_name.startswith("."):
        raise ValueError(f"Invalid branch name: {new_name}")
    
    new_branch_dir = get_branch_dir(new_name, base_dir)
    if os.path.exists(new_branch_dir):
        raise ValueError(f"Branch '{new_name}' already exists")
    
    # Rename directory
    os.rename(old_branch_dir, new_branch_dir)
    
    # Update metadata
    metadata_path = get_branch_metadata_path(new_name, base_dir)
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    metadata["name"] = new_name
    
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    
    # Update current branch if it was the renamed one
    config = _load_config(base_dir)
    if config.get("current_branch") == old_name:
        config["current_branch"] = new_name
        _save_config(config, base_dir)
    
    # Update parent_branch references in child branches
    branches = list_branches(base_dir)
    for branch in branches:
        if branch.get("parent_branch") == old_name:
            branch_meta_path = get_branch_metadata_path(branch["name"], base_dir)
            with open(branch_meta_path, "r") as f:
                branch_meta = json.load(f)
            branch_meta["parent_branch"] = new_name
            with open(branch_meta_path, "w") as f:
                json.dump(branch_meta, f, indent=4)
    
    return metadata


def get_staging_dir_for_branch(branch_name=None, base_dir=DEFAULT_BASE_DIR):
    """
    Get the staging directory for a specific branch or the current branch.
    
    Args:
        branch_name: Branch name (uses current branch if None)
        base_dir: Base directory for AVCPM
        
    Returns:
        str: Path to staging directory
    """
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    
    _ensure_main_branch(base_dir)
    return get_branch_staging_dir(branch_name, base_dir)


def get_ledger_dir_for_branch(branch_name=None, base_dir=DEFAULT_BASE_DIR):
    """
    Get the ledger directory for a specific branch or the current branch.
    
    Args:
        branch_name: Branch name (uses current branch if None)
        base_dir: Base directory for AVCPM
        
    Returns:
        str: Path to ledger directory
    """
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    
    _ensure_main_branch(base_dir)
    return get_branch_ledger_dir(branch_name, base_dir)


def _print_branch_list(branches, current_branch):
    """Print branch list in a formatted way."""
    print(f"{'*' if current_branch else ' '} {'Branch Name':<20} {'Status':<10} {'Parent':<15} {'Created At'}")
    print("-" * 70)
    
    for branch in branches:
        marker = "*" if branch["name"] == current_branch else " "
        status = branch.get("status", "unknown")
        parent = branch.get("parent_branch") or "-"
        created = branch.get("created_at", "unknown")[:19]  # Trim to date+time
        print(f"{marker} {branch['name']:<20} {status:<10} {parent:<15} {created}")


def main():
    """CLI interface for branch management."""
    if len(sys.argv) < 2:
        print("Usage: python avcpm_branch.py <command> [args...]")
        print("\nCommands:")
        print("  create <name> [--parent <branch>] [--task <task_id>]")
        print("  list")
        print("  switch <name>")
        print("  delete <name> [--force]")
        print("  rename <old> <new>")
        print("  current")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_branch.py create <name> [--parent <branch>] [--task <task_id>]")
            sys.exit(1)
        
        name = sys.argv[2]
        parent = "main"
        task_id = None
        
        # Parse optional args
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--parent" and i + 1 < len(sys.argv):
                parent = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--task" and i + 1 < len(sys.argv):
                task_id = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        try:
            metadata = create_branch(name, parent, task_id)
            print(f"Created branch '{name}' from '{parent}'")
            print(f"  Branch ID: {metadata['branch_id']}")
            print(f"  Task ID: {task_id or 'None'}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "list":
        branches = list_branches()
        current = get_current_branch()
        _print_branch_list(branches, current)
    
    elif command == "switch":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_branch.py switch <name>")
            sys.exit(1)
        
        name = sys.argv[2]
        try:
            switch_branch(name)
            print(f"Switched to branch '{name}'")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_branch.py delete <name> [--force]")
            sys.exit(1)
        
        name = sys.argv[2]
        force = "--force" in sys.argv
        
        try:
            delete_branch(name, force)
            print(f"Deleted branch '{name}'")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "rename":
        if len(sys.argv) < 4:
            print("Usage: python avcpm_branch.py rename <old> <new>")
            sys.exit(1)
        
        old_name = sys.argv[2]
        new_name = sys.argv[3]
        
        try:
            rename_branch(old_name, new_name)
            print(f"Renamed branch '{old_name}' to '{new_name}'")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "current":
        current = get_current_branch()
        print(current)
    
    else:
        print(f"Unknown command: {command}")
        print("\nCommands: create, list, switch, delete, rename, current")
        sys.exit(1)


if __name__ == "__main__":
    main()
