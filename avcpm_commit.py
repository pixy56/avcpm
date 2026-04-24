import os
import sys
import json
import hashlib
import secrets
from datetime import datetime

from avcpm_agent import get_agent, sign_commit
from avcpm_branch import (
    get_current_branch,
    get_branch_staging_dir,
    get_branch_ledger_dir,
    _ensure_main_branch
)
from avcpm_lifecycle import (
    on_commit,
    validate_commit_allowed,
    init_lifecycle_config
)
from avcpm_security import sanitize_path, sanitize_path_list, safe_copy, safe_read
from avcpm_ledger_integrity import (
    calculate_entry_hash,
    get_last_commit_hash
)
from avcpm_auth import (
    require_auth,
    get_session_token_from_env,
    validate_session
)
from avcpm_audit import audit_log, EVENT_COMMIT

DEFAULT_BASE_DIR = ".avcpm"

def get_global_ledger_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the global ledger directory path (legacy)."""
    return os.path.join(base_dir, "ledger")

def get_global_staging_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the global staging directory path (legacy)."""
    return os.path.join(base_dir, "staging")

def get_ledger_dir(branch_name=None, base_dir=DEFAULT_BASE_DIR):
    """Get the ledger directory path for a branch."""
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    return get_branch_ledger_dir(branch_name, base_dir)

def get_staging_dir(branch_name=None, base_dir=DEFAULT_BASE_DIR):
    """Get the staging directory path for a branch."""
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    return get_branch_staging_dir(branch_name, base_dir)

def ensure_directories(branch_name=None, base_dir=DEFAULT_BASE_DIR):
    """Ensure ledger and staging directories exist for a branch."""
    _ensure_main_branch(base_dir)
    os.makedirs(get_ledger_dir(branch_name, base_dir), exist_ok=True)
    os.makedirs(get_staging_dir(branch_name, base_dir), exist_ok=True)

def calculate_checksum(filepath, base_dir=DEFAULT_BASE_DIR):
    """Calculate SHA256 checksum of a file using safe read."""
    content = safe_read(filepath, base_dir)
    return hashlib.sha256(content).hexdigest()

def commit(task_id, agent_id, rationale, files_to_commit, branch_name=None, base_dir=DEFAULT_BASE_DIR, skip_validation=False):
    """
    Commit files to a branch.
    
    Args:
        task_id: Task ID for the commit
        agent_id: Agent making the commit
        rationale: Commit message/rationale
        files_to_commit: List of file paths to commit
        branch_name: Branch to commit to (uses current branch if None)
        base_dir: Base directory for AVCPM
        skip_validation: Skip validation (for admin/debug)
    """
    ensure_directories(branch_name, base_dir)
    
    # Initialize lifecycle config if needed
    init_lifecycle_config(base_dir)
    
    # Validate agent exists and is authenticated
    agent = get_agent(agent_id, base_dir)
    if agent is None:
        raise ValueError(f"Agent {agent_id} not found. Create agent first using avcpm_agent.create_agent()")
    
    # Require authentication for commit
    success, error_msg = require_auth(agent_id, base_dir)
    if not success:
        raise PermissionError(error_msg)
    
    # Validate commit is allowed (lifecycle rules)
    if not skip_validation:
        allowed, msg = validate_commit_allowed(task_id, agent_id, base_dir)
        if not allowed:
            raise ValueError(f"Commit not allowed: {msg}")

    staging_dir = get_staging_dir(branch_name, base_dir)
    ledger_dir = get_ledger_dir(branch_name, base_dir)
    
    # Sanitize file paths to prevent path traversal attacks
    try:
        # Files must be within the current working directory (production)
        files_to_commit = [sanitize_path(f, os.getcwd()) for f in files_to_commit]
    except ValueError as e:
        raise ValueError(f"Security Error: {e}")

    commit_id = datetime.now().strftime("%Y%m%d%H%M%S") + f"-{secrets.token_hex(4)}"
    timestamp = datetime.now().isoformat()
    
    # Get the previous commit's hash for the integrity chain
    current_branch = branch_name or get_current_branch(base_dir)
    previous_hash = get_last_commit_hash(current_branch, base_dir)
    
    # Ensure commit_id is unique
    ledger_dir = get_branch_ledger_dir(current_branch, base_dir)
    ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    if os.path.exists(ledger_path):
        commit_id = datetime.now().strftime("%Y%m%d%H%M%S") + f"-{secrets.token_hex(8)}"
        ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    
    commit_meta = {
        "commit_id": commit_id,
        "timestamp": timestamp,
        "agent_id": agent_id,
        "task_id": task_id,
        "rationale": rationale,
        "changes": [],
        "previous_hash": previous_hash
    }

    for filepath in files_to_commit:
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} not found. Skipping.")
            continue
        
        checksum = calculate_checksum(filepath, base_dir)
        # M-V4: Use relative path with / encoded as _ to prevent basename collision
        # e.g., dir1/foo.txt -> staging/dir1_foo.txt, dir2/foo.txt -> staging/dir2_foo.txt
        rel_path = filepath.lstrip('./')
        safe_staging_name = rel_path.replace('/', '_')
        staging_path = os.path.join(staging_dir, safe_staging_name)
        try:
            safe_copy(filepath, staging_path, base_dir)
        except Exception as e:
            print(f"Security error copying {filepath}: {e}")
            continue
        
        commit_meta["changes"].append({
            "file": filepath,
            "checksum": checksum,
            "staging_path": staging_path
        })

    # Generate signature for the commit
    signature_data = sign_commit(commit_id, timestamp, commit_meta["changes"], agent_id, base_dir)
    commit_meta["signature"] = signature_data["signature"]
    commit_meta["changes_hash"] = signature_data["changes_hash"]
    
    # Calculate and store the entry hash for integrity chain
    commit_meta["entry_hash"] = calculate_entry_hash(commit_meta)
    
    # Write to ledger
    ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    with open(ledger_path, "w") as f:
        json.dump(commit_meta, f, indent=4)
    
    print(f"Commit {commit_id} written to ledger (branch: {current_branch}). Files moved to staging.")
    
    audit_log(EVENT_COMMIT, agent_id, {
        "commit_id": commit_id,
        "task_id": task_id,
        "branch": current_branch,
        "files": [c["file"] for c in commit_meta["changes"]]
    })
    
    # Trigger lifecycle hook for auto-transition
    try:
        success, msg = on_commit(task_id, commit_id, agent_id, base_dir)
        if success:
            print(f"Lifecycle: {msg}")
    except Exception as e:
        print(f"Warning: Lifecycle hook failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python avcpm_commit.py <task_id> <agent_id> <rationale> <file1> [file2...]")
        sys.exit(1)
    
    task_id = sys.argv[1]
    agent_id = sys.argv[2]
    rationale = sys.argv[3]
    files = sys.argv[4:]
    
    try:
        commit(task_id, agent_id, rationale, files)
    except (ValueError, PermissionError) as e:
        print(f"Error: {e}")
        sys.exit(1)
