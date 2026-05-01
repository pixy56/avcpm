import os
import sys
import json
import hashlib
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
from avcpm_security import sanitize_path, safe_copy, safe_read, safe_makedirs
from avcpm_ledger_integrity import (
    calculate_entry_hash,
    get_last_commit_hash,
    verify_ledger_integrity,
    check_integrity_warning
)
from avcpm_auth import (
    require_auth,
    get_session_token_from_env,
    validate_session,
    get_authenticated_agent_from_env
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
    """Ensure ledger and staging directories exist for a branch with symlink protection."""
    _ensure_main_branch(base_dir)
    safe_makedirs(get_ledger_dir(branch_name, base_dir), base_dir, exist_ok=True)
    safe_makedirs(get_staging_dir(branch_name, base_dir), base_dir, exist_ok=True)

def calculate_checksum(filepath, base_dir=DEFAULT_BASE_DIR):
    """Calculate SHA256 checksum of a file using safe read."""
    content = safe_read(filepath, base_dir)
    return hashlib.sha256(content).hexdigest()

def verify_agent_identity(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Verify agent identity is valid and matches the signing key.
    
    Args:
        agent_id: The agent ID to verify
        base_dir: Base directory for AVCPM
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    # Check if agent exists in registry
    agent = get_agent(agent_id, base_dir)
    if agent is None:
        return False, f"Agent {agent_id} not found in registry"
    
    # Verify agent ID matches stored metadata
    if agent.get('agent_id') != agent_id:
        return False, f"Agent ID mismatch in registry data"
    
    # Verify public key exists
    from avcpm_agent import get_public_key
    public_key = get_public_key(agent_id, base_dir)
    if public_key is None:
        return False, f"Public key not found for agent {agent_id}"
    
    return True, None


def commit(task_id, agent_id, rationale, files_to_commit, branch_name=None, base_dir=DEFAULT_BASE_DIR, skip_validation=False, 
           require_authentication=True, session_token=None):
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
        require_authentication: Whether to require agent authentication
        session_token: Optional session token for authentication
    """
    ensure_directories(branch_name, base_dir)
    
    # Initialize lifecycle config if needed
    init_lifecycle_config(base_dir)
    
    # Validate agent_id exists
    agent = get_agent(agent_id, base_dir)
    if agent is None:
        raise ValueError(f"Agent {agent_id} not found. Create agent first using avcpm_agent.create_agent()")
    
    # Verify agent identity (cryptographic binding check)
    identity_valid, identity_error = verify_agent_identity(agent_id, base_dir)
    if not identity_valid:
        raise ValueError(f"Agent identity verification failed: {identity_error}")
    
    # Require agent authentication for commits (unless skipped)
    if require_authentication and not skip_validation:
        # Check for session token from env if not provided
        if session_token is None:
            _, session_token = get_authenticated_agent_from_env(base_dir)
        
        if session_token is None:
            # Try to get session from env token
            session_token = get_session_token_from_env()
        
        if session_token is None:
            raise ValueError(f"Agent {agent_id} is not authenticated. Run 'avcpm agent authenticate {agent_id}' first.")
        
        # Validate the session
        if not validate_session(agent_id, session_token, base_dir):
            raise ValueError(f"Agent {agent_id} has invalid or expired session. Re-authenticate with 'avcpm agent authenticate {agent_id}'.")
    
    # Validate commit is allowed (lifecycle rules)
    if not skip_validation:
        allowed, msg = validate_commit_allowed(task_id, agent_id, base_dir)
        if not allowed:
            print(f"Error: {msg}")
            sys.exit(1)
    
    staging_dir = get_staging_dir(branch_name, base_dir)
    ledger_dir = get_ledger_dir(branch_name, base_dir)
    
    # Sanitize file paths to prevent path traversal attacks
    try:
        # Files must be within the current working directory (production)
        files_to_commit = [sanitize_path(f, os.getcwd()) for f in files_to_commit]
    except ValueError as e:
        print(f"Security Error: {e}")
        sys.exit(1)
    
    # Sanitize file paths to prevent path traversal attacks
    try:
        # Files must be within the current working directory (production)
        files_to_commit = [sanitize_path(f, os.getcwd()) for f in files_to_commit]
    except ValueError as e:
        print(f"Security Error: {e}")
        sys.exit(1)

    commit_id = datetime.now().strftime("%Y%m%d%H%M%S")
    timestamp = datetime.now().isoformat()
    
    # Get the previous commit's hash for the integrity chain
    current_branch = branch_name or get_current_branch(base_dir)
    previous_hash = get_last_commit_hash(current_branch, base_dir)
    
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
        # Copy file to staging using safe copy
        staging_path = os.path.join(staging_dir, os.path.basename(filepath))
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
    
    # Verify ledger integrity before writing new commit
    integrity_report = verify_ledger_integrity(current_branch, base_dir)
    if not integrity_report.success:
        warning = check_integrity_warning(current_branch, base_dir)
        print(f"SECURITY WARNING: {warning}")
        print("Commit aborted. Run 'avcpm validate ledger' to see details.")
        sys.exit(1)
    
    # Write to ledger
    ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    with open(ledger_path, "w") as f:
        json.dump(commit_meta, f, indent=4)
    
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
