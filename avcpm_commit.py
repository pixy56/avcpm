import os
import sys
import json
import hashlib
from datetime import datetime
import shutil

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

def calculate_checksum(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

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
    
    # Validate agent_id exists
    agent = get_agent(agent_id, base_dir)
    if agent is None:
        raise ValueError(f"Agent {agent_id} not found. Create agent first using avcpm_agent.create_agent()")
    
    # Validate commit is allowed (lifecycle rules)
    if not skip_validation:
        allowed, msg = validate_commit_allowed(task_id, agent_id, base_dir)
        if not allowed:
            print(f"Error: {msg}")
            sys.exit(1)
    
    staging_dir = get_staging_dir(branch_name, base_dir)
    ledger_dir = get_ledger_dir(branch_name, base_dir)

    commit_id = datetime.now().strftime("%Y%m%d%H%M%S")
    timestamp = datetime.now().isoformat()
    
    commit_meta = {
        "commit_id": commit_id,
        "timestamp": timestamp,
        "agent_id": agent_id,
        "task_id": task_id,
        "rationale": rationale,
        "changes": []
    }

    for filepath in files_to_commit:
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} not found. Skipping.")
            continue
        
        checksum = calculate_checksum(filepath)
        # Copy file to staging
        staging_path = os.path.join(staging_dir, os.path.basename(filepath))
        shutil.copy2(filepath, staging_path)
        
        commit_meta["changes"].append({
            "file": filepath,
            "checksum": checksum,
            "staging_path": staging_path
        })

    # Generate signature for the commit
    signature_data = sign_commit(commit_id, timestamp, commit_meta["changes"], agent_id, base_dir)
    commit_meta["signature"] = signature_data["signature"]
    commit_meta["changes_hash"] = signature_data["changes_hash"]
    
    # Write to ledger
    ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    with open(ledger_path, "w") as f:
        json.dump(commit_meta, f, indent=4)
    
    current_branch = branch_name or get_current_branch(base_dir)
    print(f"Commit {commit_id} written to ledger (branch: {current_branch}). Files moved to staging.")
    
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
    
    commit(task_id, agent_id, rationale, files)
