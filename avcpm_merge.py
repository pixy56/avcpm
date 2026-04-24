from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union, Any
import os
import sys
import json
import shutil

from avcpm_agent import verify_commit_signature
from avcpm_branch import (
    get_current_branch,
    get_branch_staging_dir,
    get_branch_ledger_dir,
    get_branch,
    BRANCH_STATUS_MERGED
)
from avcpm_conflict import (
    detect_conflicts,
    resolve_conflict,
    get_conflicts,
    CONFLICT_STATUS_OPEN,
    auto_merge_possible
)
from avcpm_lifecycle import (
    on_merge,
    init_lifecycle_config
)
from avcpm_security import sanitize_path
from avcpm_audit import audit_log, EVENT_MERGE

DEFAULT_BASE_DIR = ".avcpm"

def get_reviews_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the reviews directory path."""
    return os.path.join(base_dir, "reviews")

def get_global_staging_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the global staging directory path (legacy)."""
    return os.path.join(base_dir, "staging")

def get_global_ledger_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the global ledger directory path (legacy)."""
    return os.path.join(base_dir, "ledger")

def get_staging_dir(branch_name=None, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the staging directory path for a branch."""
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    return get_branch_staging_dir(branch_name, base_dir)

def get_ledger_dir(branch_name=None, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the ledger directory path for a branch."""
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    return get_branch_ledger_dir(branch_name, base_dir)

def merge(commit_id, source_branch=None, target_branch=None, base_dir=DEFAULT_BASE_DIR, auto_resolve=False, agent_id=None) -> Any:
    """
    Merge a commit into a target branch.
    
    Args:
        commit_id: Commit ID to merge
        source_branch: Branch containing the commit (uses current branch if None)
        target_branch: Branch to merge into (uses current branch if None)
        base_dir: Base directory for AVCPM
        auto_resolve: If True, attempt to auto-resolve non-conflicting changes
        agent_id: Agent performing the merge (for lifecycle hooks)
    """
    # Initialize lifecycle config if needed
    init_lifecycle_config(base_dir)
    # Determine source and target branches
    if source_branch is None:
        source_branch = get_current_branch(base_dir)
    if target_branch is None:
        target_branch = get_current_branch(base_dir)
    
    reviews_dir = get_reviews_dir(base_dir)
    staging_dir = get_staging_dir(source_branch, base_dir)
    ledger_dir = get_ledger_dir(source_branch, base_dir)
    
    print(f"Merging commit {commit_id} from branch '{source_branch}' into '{target_branch}'")
    
    # Check for conflicts between branches before merging
    if source_branch != target_branch:
        print(f"Checking for conflicts between '{source_branch}' and '{target_branch}'...")
        conflict_result = detect_conflicts(source_branch, target_branch, base_dir)
        
        if conflict_result["conflict_count"] > 0:
            error_msg = (
                f"{conflict_result['conflict_count']} conflict(s) detected between "
                f"'{source_branch}' and '{target_branch}'. Merge aborted.\n"
            )
            for conflict in conflict_result["conflicts"]:
                error_msg += f"  - {conflict['file']} ({conflict['conflict_type']})\n"
            error_msg += (
                f"\nRun 'python avcpm_conflict.py list' to see all open conflicts.\n"
                f"Run 'python avcpm_conflict.py resolve <conflict_id> --strategy <ours|theirs|union>' to resolve."
            )
            raise ValueError(error_msg)
        else:
            print("No conflicts detected. Proceeding with merge...")
    
    # 1. Validate Approval
    review_path = os.path.join(reviews_dir, f"{commit_id}.review")
    if not os.path.exists(review_path):
        raise ValueError(f"No review file found for commit {commit_id} at {review_path}")
    
    with open(review_path, "r") as f:
        content = f.read()
    
    if "APPROVED" not in content:
        raise ValueError(f"Commit {commit_id} is not APPROVED. Merge aborted.")
    
    # 2. Identify files in the commit
    ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    if not os.path.exists(ledger_path):
        raise ValueError(f"Commit {commit_id} not found in ledger.")
    
    with open(ledger_path, "r") as f:
        commit_data = json.load(f)
    
    # 3. Verify commit signature before merging
    signature = commit_data.get("signature")
    agent_id = commit_data.get("agent_id")
    timestamp = commit_data.get("timestamp")
    changes = commit_data.get("changes", [])
    
    if not signature:
        raise ValueError(f"Commit {commit_id} has no signature. Merge aborted.")
    
    if not agent_id:
        raise ValueError(f"Commit {commit_id} has no agent_id. Merge aborted.")
    
    is_valid = verify_commit_signature(commit_id, timestamp, changes, agent_id, signature, base_dir)
    if not is_valid:
        raise ValueError(f"Commit {commit_id} has invalid signature. Merge aborted.")
    
    print(f"Signature verified for commit {commit_id} (agent: {agent_id})")
    
    # 4. Move files from staging to production (current directory)
    for change in commit_data["changes"]:
        staging_file = change["staging_path"]
        if os.path.exists(staging_file):
            dest_file = change["file"]
            # Sanitize destination path to prevent path traversal
            try:
                dest_file = sanitize_path(dest_file, os.getcwd())
            except ValueError as e:
                raise ValueError(f"Security Error: Path traversal detected for {dest_file}: {e}")
            # Simple copy/overwrite for Phase 1
            shutil.copy2(staging_file, dest_file)
            print(f"Merged: {dest_file}")
        else:
            print(f"Warning: Staging file {staging_file} missing.")

    # Update source branch status if it was merged
    if source_branch != target_branch:
        branch_meta = get_branch(source_branch, base_dir)
        if branch_meta:
            branch_meta["status"] = BRANCH_STATUS_MERGED
            from avcpm_branch import get_branch_metadata_path
            with open(get_branch_metadata_path(source_branch, base_dir), "w") as f:
                json.dump(branch_meta, f, indent=4)
            print(f"Marked branch '{source_branch}' as merged")
    
    print(f"Successfully merged commit {commit_id} into branch '{target_branch}'.")
    
    audit_log(EVENT_MERGE, merging_agent_id or "unknown", {
        "commit_id": commit_id,
        "source_branch": source_branch,
        "target_branch": target_branch,
        "files": [c["file"] for c in commit_data.get("changes", [])]
    })
    
    # Trigger lifecycle hook for auto-transition
    task_id = commit_data.get("task_id")
    merging_agent_id = agent_id or commit_data.get("agent_id")
    
    if task_id:
        try:
            success, msg = on_merge(task_id, commit_id, merging_agent_id, base_dir)
            if success:
                print(f"Lifecycle: {msg}")
        except Exception as e:
            print(f"Warning: Lifecycle hook failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python avcpm_merge.py <commit_id> [--auto-resolve]")
        sys.exit(1)
    
    commit_id = sys.argv[1]
    auto_resolve = "--auto-resolve" in sys.argv
    
    try:
        merge(commit_id, auto_resolve=auto_resolve)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
