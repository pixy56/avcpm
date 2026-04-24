"""
AVCPM Rollback & Recovery System (Phase 3)

Provides undo operations, backup management, and recovery functionality.
"""

import os
import sys
import json
import shutil
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from avcpm_branch import (
    get_current_branch,
    get_branch_staging_dir,
    get_branch_ledger_dir,
    get_branch,
    list_branches,
    switch_branch,
    BRANCH_STATUS_MERGED,
    BRANCH_STATUS_ACTIVE,
    DEFAULT_BASE_DIR
)
from avcpm_security import safe_copy, safe_read
from avcpm_audit import audit_log, EVENT_ROLLBACK

# Backup metadata
BACKUP_STATUS_ACTIVE = "active"
BACKUP_STATUS_RESTORED = "restored"


def get_backups_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the backups directory path."""
    return os.path.join(base_dir, "backups")


def get_backup_path(backup_id: str, base_dir=DEFAULT_BASE_DIR) -> str:
    """Get the path to a specific backup directory."""
    return os.path.join(get_backups_dir(base_dir), backup_id)


def get_backup_metadata_path(backup_id: str, base_dir=DEFAULT_BASE_DIR) -> str:
    """Get the path to a backup's metadata file."""
    return os.path.join(get_backup_path(backup_id, base_dir), "backup.json")


def _generate_backup_id() -> str:
    """Generate a unique backup ID."""
    return f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"


def _ensure_backups_dir(base_dir=DEFAULT_BASE_DIR):
    """Ensure the backups directory exists."""
    os.makedirs(get_backups_dir(base_dir), exist_ok=True)


def _copy_directory_tree(src: str, dst: str, base_dir: str = DEFAULT_BASE_DIR):
    """Copy a directory tree, preserving metadata and using safe_copy."""
    if not os.path.exists(src):
        return
    
    os.makedirs(dst, exist_ok=True)
    
    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        dst_path = os.path.join(dst, item)
        
        if os.path.isdir(src_path):
            _copy_directory_tree(src_path, dst_path, base_dir)
        else:
            safe_copy(src_path, dst_path, base_dir)


def _get_production_file_path(filepath: str) -> str:
    """Get the production path for a file (relative to current dir)."""
    # Remove leading ./ if present
    if filepath.startswith("./"):
        filepath = filepath[2:]
    return filepath


def _get_commits_in_branch(branch_name: str, base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    """Get all commits in a branch, sorted by timestamp."""
    ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
    if not os.path.exists(ledger_dir):
        return []
    
    commits = []
    for filename in sorted(os.listdir(ledger_dir)):
        if filename.endswith(".json"):
            commit_path = os.path.join(ledger_dir, filename)
            with open(commit_path, "r") as f:
                commit_data = json.load(f)
                commits.append(commit_data)
    
    # Sort by commit_id (which is timestamp-based)
    commits.sort(key=lambda x: x.get("commit_id", ""))
    return commits


def _find_commit_in_any_branch(commit_id: str, base_dir=DEFAULT_BASE_DIR) -> Optional[tuple]:
    """Find a commit across all branches. Returns (branch_name, commit_data) or None."""
    branches = list_branches(base_dir)
    for branch in branches:
        branch_name = branch["name"]
        ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
        commit_path = os.path.join(ledger_dir, f"{commit_id}.json")
        if os.path.exists(commit_path):
            with open(commit_path, "r") as f:
                return (branch_name, json.load(f))
    return None


def _find_commit_in_staging(commit_id: str, branch_name: str, base_dir=DEFAULT_BASE_DIR) -> bool:
    """Check if a commit exists in a branch's staging."""
    ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
    return os.path.exists(os.path.join(ledger_dir, f"{commit_id}.json"))


def _is_commit_merged(commit_id: str, branch_name: str, base_dir=DEFAULT_BASE_DIR) -> bool:
    """Check if a commit has been merged to production."""
    commit_info = _find_commit_in_any_branch(commit_id, base_dir)
    if not commit_info:
        return False
    
    branch_name_found, commit_data = commit_info
    
    # Check if any of the files from this commit exist in production
    # and match the checksum
    for change in commit_data.get("changes", []):
        filepath = change.get("file")
        staging_path = change.get("staging_path")
        
        if staging_path and os.path.exists(filepath):
            # File exists in production - check if it's from this commit
            prod_checksum = _calculate_checksum(filepath)
            commit_checksum = change.get("checksum")
            if prod_checksum == commit_checksum:
                return True
    
    return False


def _calculate_checksum(filepath: str) -> str:
    """Calculate SHA256 checksum of a file."""
    import hashlib
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def _get_file_at_commit(filepath: str, commit_id: str, base_dir=DEFAULT_BASE_DIR) -> Optional[str]:
    """Get the staging path for a file at a specific commit."""
    commit_info = _find_commit_in_any_branch(commit_id, base_dir)
    if not commit_info:
        return None
    
    _, commit_data = commit_info
    for change in commit_data.get("changes", []):
        if change.get("file") == filepath:
            staging_path = change.get("staging_path")
            if staging_path and os.path.exists(staging_path):
                return staging_path
    return None


def _backup_before_destructive(base_dir=DEFAULT_BASE_DIR, operation_name: str = "") -> str:
    """Auto-backup before destructive operations. Returns backup_id."""
    return create_backup(
        name=f"auto_before_{operation_name}_{datetime.now().strftime('%H%M%S')}" if operation_name else None,
        base_dir=base_dir
    )


# ============================================================================
# ROLLBACK OPERATIONS
# ============================================================================

def rollback(commit_id: str, base_dir=DEFAULT_BASE_DIR, dry_run: bool = False) -> Dict:
    """
    Undo a merged commit by restoring files to their state before the commit.
    
    Args:
        commit_id: The commit ID to rollback
        base_dir: Base directory for AVCPM
        dry_run: If True, only show what would be done
        
    Returns:
        Dictionary with rollback results
    """
    result = {
        "success": False,
        "commit_id": commit_id,
        "files_restored": [],
        "files_not_found": [],
        "files_skipped": [],
        "backup_id": None
    }
    
    # Find the commit
    commit_info = _find_commit_in_any_branch(commit_id, base_dir)
    if not commit_info:
        result["error"] = f"Commit {commit_id} not found in any branch"
        return result
    
    branch_name, commit_data = commit_info
    
    # Check if commit is merged
    if not _is_commit_merged(commit_id, branch_name, base_dir):
        result["error"] = f"Commit {commit_id} has not been merged. Use unstage() instead."
        return result
    
    # Find the parent commit (previous commit in the branch)
    commits = _get_commits_in_branch(branch_name, base_dir)
    parent_commit = None
    for i, c in enumerate(commits):
        if c.get("commit_id") == commit_id and i > 0:
            parent_commit = commits[i - 1]
            break
    
    # Auto-backup before destructive operation
    if not dry_run:
        result["backup_id"] = _backup_before_destructive(base_dir, f"rollback_{commit_id}")
    
    # For each file in the commit, restore to parent version or remove if no parent
    for change in commit_data.get("changes", []):
        filepath = change.get("file")
        prod_path = _get_production_file_path(filepath)
        
        if parent_commit:
            # Try to restore from parent commit
            parent_staging = _get_file_at_commit(filepath, parent_commit.get("commit_id"), base_dir)
            # M-V2: Verify parent staging exists before deleting production file
            if parent_staging:
                if not dry_run:
                    try:
                        safe_copy(parent_staging, prod_path, base_dir)
                    except Exception as e:
                        print(f"Security error during rollback: {e}")
                        continue
                result["files_restored"].append({
                    "file": filepath,
                    "restored_from": parent_commit.get("commit_id")
                })
            else:
                # Parent commit exists but staging file is missing - verify before delete
                result["error"] = (
                    f"Parent commit {parent_commit.get('commit_id')} exists but staging file "
                    f"for '{filepath}' is missing. Cannot verify rollback. Aborting."
                )
                return result
        else:
            # No parent commit - file was added in this commit, remove it
            if os.path.exists(prod_path):
                if not dry_run:
                    os.remove(prod_path)
                result["files_restored"].append({
                    "file": filepath,
                    "action": "deleted"
                })
            else:
                result["files_not_found"].append(filepath)
    
    result["success"] = True
    
    audit_log(EVENT_ROLLBACK, commit_data.get("agent_id", "unknown"), {
        "commit_id": commit_id,
        "action": "rollback",
        "branch": branch_name,
        "files_restored": result["files_restored"],
        "backup_id": result.get("backup_id")
    })
    return result


def unstage(commit_id: str, branch_name: Optional[str] = None, base_dir=DEFAULT_BASE_DIR) -> Dict:
    """
    Remove a commit from staging (uncommitted state).
    
    Args:
        commit_id: The commit ID to unstage
        branch_name: Branch to unstage from (uses current if None)
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with unstaging results
    """
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    
    result = {
        "success": False,
        "commit_id": commit_id,
        "branch": branch_name,
        "files_removed": [],
        "ledger_removed": False
    }
    
    # Check if commit exists in this branch's staging
    ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
    commit_path = os.path.join(ledger_dir, f"{commit_id}.json")
    
    if not os.path.exists(commit_path):
        result["error"] = f"Commit {commit_id} not found in branch '{branch_name}' staging"
        return result
    
    # Load commit data
    with open(commit_path, "r") as f:
        commit_data = json.load(f)
    
    # Remove files from staging directory
    staging_dir = get_branch_staging_dir(branch_name, base_dir)
    for change in commit_data.get("changes", []):
        staging_path = change.get("staging_path")
        if staging_path and os.path.exists(staging_path):
            os.remove(staging_path)
            result["files_removed"].append(change.get("file"))
    
    # Remove the ledger entry
    os.remove(commit_path)
    result["ledger_removed"] = True
    result["success"] = True
    
    audit_log(EVENT_ROLLBACK, commit_data.get("agent_id", "unknown"), {
        "commit_id": commit_id,
        "action": "unstage",
        "branch": branch_name,
        "files_removed": result["files_removed"]
    })
    
    return result


def restore_file(filepath: str, commit_id: Optional[str] = None, base_dir=DEFAULT_BASE_DIR) -> Dict:
    """
    Restore a file to a specific version.
    
    Args:
        filepath: Path to the file to restore
        commit_id: Commit ID to restore from (uses latest if None)
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with restore results
    """
    result = {
        "success": False,
        "filepath": filepath,
        "commit_id": commit_id,
        "restored_from": None
    }
    
    # If no commit_id specified, find the latest commit that touched this file
    if commit_id is None:
        # Search all branches for file history
        branches = list_branches(base_dir)
        latest_commit = None
        for branch in branches:
            branch_name = branch["name"]
            commits = _get_commits_in_branch(branch_name, base_dir)
            for commit in commits:
                for change in commit.get("changes", []):
                    if change.get("file") == filepath:
                        if latest_commit is None or commit.get("commit_id", "") > latest_commit.get("commit_id", ""):
                            latest_commit = commit
        
        if latest_commit is None:
            result["error"] = f"No history found for file {filepath}"
            return result
        
        commit_id = latest_commit.get("commit_id")
        result["commit_id"] = commit_id
    
    # Get the file from the commit
    staging_path = _get_file_at_commit(filepath, commit_id, base_dir)
    
    if not staging_path:
        result["error"] = f"File {filepath} not found in commit {commit_id}"
        return result
    
    # Copy to production using safe_copy
    prod_path = _get_production_file_path(filepath)
    os.makedirs(os.path.dirname(prod_path) if os.path.dirname(prod_path) else ".", exist_ok=True)
    safe_copy(staging_path, prod_path, base_dir)
    
    result["restored_from"] = staging_path
    result["success"] = True
    
    audit_log(EVENT_ROLLBACK, "unknown", {
        "commit_id": commit_id,
        "action": "restore_file",
        "filepath": filepath,
        "restored_from": staging_path
    })
    
    return result


def reset_soft(target_commit: str, branch_name: Optional[str] = None, base_dir=DEFAULT_BASE_DIR) -> Dict:
    """
    Reset branch pointer to a specific commit, keeping changes in staging.
    
    Args:
        target_commit: Commit ID to reset to
        branch_name: Branch to reset (uses current if None)
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with reset results
    """
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    
    result = {
        "success": False,
        "branch": branch_name,
        "target_commit": target_commit,
        "commits_removed": [],
        "files_preserved": []
    }
    
    # Get all commits in the branch
    commits = _get_commits_in_branch(branch_name, base_dir)
    
    # Find commits to remove (those after target_commit)
    found_target = False
    commits_to_remove = []
    for commit in commits:
        if found_target:
            commits_to_remove.append(commit)
        if commit.get("commit_id") == target_commit:
            found_target = True
    
    if not found_target:
        result["error"] = f"Commit {target_commit} not found in branch '{branch_name}'"
        return result
    
    # Remove commits from ledger but keep staging files
    ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
    for commit in commits_to_remove:
        commit_id = commit.get("commit_id")
        commit_path = os.path.join(ledger_dir, f"{commit_id}.json")
        
        # Track files that were preserved
        for change in commit.get("changes", []):
            result["files_preserved"].append(change.get("file"))
        
        # Remove ledger entry
        if os.path.exists(commit_path):
            os.remove(commit_path)
            result["commits_removed"].append(commit_id)
    
    result["success"] = True
    
    audit_log(EVENT_ROLLBACK, "unknown", {
        "commit_id": target_commit,
        "action": "reset_soft",
        "branch": branch_name,
        "commits_removed": result["commits_removed"]
    })
    return result


def reset_hard(target_commit: str, branch_name: Optional[str] = None, base_dir=DEFAULT_BASE_DIR) -> Dict:
    """
    Reset branch to a specific commit, removing all changes after it.
    Creates an auto-backup before destructive operation.
    
    Args:
        target_commit: Commit ID to reset to
        branch_name: Branch to reset (uses current if None)
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with reset results
    """
    if branch_name is None:
        branch_name = get_current_branch(base_dir)
    
    result = {
        "success": False,
        "branch": branch_name,
        "target_commit": target_commit,
        "backup_id": None,
        "commits_removed": [],
        "files_removed": []
    }
    
    # Get all commits in the branch
    commits = _get_commits_in_branch(branch_name, base_dir)
    
    # Find commits to remove
    found_target = False
    commits_to_remove = []
    for commit in commits:
        if found_target:
            commits_to_remove.append(commit)
        if commit.get("commit_id") == target_commit:
            found_target = True
    
    if not found_target:
        result["error"] = f"Commit {target_commit} not found in branch '{branch_name}'"
        return result
    
    # Auto-backup before destructive operation
    result["backup_id"] = _backup_before_destructive(base_dir, f"hard_reset_{branch_name}")
    
    # First do soft reset
    soft_result = reset_soft(target_commit, branch_name, base_dir)
    if not soft_result["success"]:
        result["error"] = soft_result.get("error", "Soft reset failed")
        return result
    
    result["commits_removed"] = soft_result["commits_removed"]
    
    # Now remove staging files
    staging_dir = get_branch_staging_dir(branch_name, base_dir)
    for commit in commits_to_remove:
        for change in commit.get("changes", []):
            staging_path = change.get("staging_path")
            if staging_path and os.path.exists(staging_path):
                os.remove(staging_path)
                result["files_removed"].append(change.get("file"))
    
    result["success"] = True
    
    audit_log(EVENT_ROLLBACK, "unknown", {
        "commit_id": target_commit,
        "action": "reset_hard",
        "branch": branch_name,
        "commits_removed": result["commits_removed"],
        "files_removed": result["files_removed"],
        "backup_id": result.get("backup_id")
    })
    return result


# ============================================================================
# BACKUP SYSTEM
# ============================================================================

def create_backup(name: Optional[str] = None, base_dir=DEFAULT_BASE_DIR) -> str:
    """
    Create a manual checkpoint backup.
    
    Args:
        name: Optional name for the backup
        base_dir: Base directory for AVCPM
        
    Returns:
        Backup ID
    """
    _ensure_backups_dir(base_dir)
    
    backup_id = _generate_backup_id()
    backup_path = get_backup_path(backup_id, base_dir)
    os.makedirs(backup_path, exist_ok=True)
    
    # Create backup metadata
    backup_meta = {
        "backup_id": backup_id,
        "name": name or backup_id,
        "created_at": datetime.now().isoformat(),
        "status": BACKUP_STATUS_ACTIVE,
        "branches": []
    }
    
    # Backup all branches
    branches = list_branches(base_dir)
    for branch in branches:
        branch_name = branch["name"]
        branch_backup_dir = os.path.join(backup_path, "branches", branch_name)
        os.makedirs(branch_backup_dir, exist_ok=True)
        
        # Backup staging
        staging_dir = get_branch_staging_dir(branch_name, base_dir)
        staging_backup = os.path.join(branch_backup_dir, "staging")
        _copy_directory_tree(staging_dir, staging_backup)
        
        # Backup ledger
        ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
        ledger_backup = os.path.join(branch_backup_dir, "ledger")
        _copy_directory_tree(ledger_dir, ledger_backup)
        
        # Backup branch metadata
        from avcpm_branch import get_branch_metadata_path
        branch_meta_path = get_branch_metadata_path(branch_name, base_dir)
        if os.path.exists(branch_meta_path):
            safe_copy(branch_meta_path, os.path.join(branch_backup_dir, "branch.json"), base_dir)
        
        backup_meta["branches"].append(branch_name)
    
    # Backup config
    config_path = os.path.join(base_dir, "config.json")
    if os.path.exists(config_path):
        config_backup = os.path.join(backup_path, "config.json")
        safe_copy(config_path, config_backup, base_dir)
    
    # Save backup metadata
    with open(get_backup_metadata_path(backup_id, base_dir), "w") as f:
        json.dump(backup_meta, f, indent=4)
    
    return backup_id


def list_backups(base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    """
    List all available backups.
    
    Args:
        base_dir: Base directory for AVCPM
        
    Returns:
        List of backup metadata dictionaries
    """
    backups_dir = get_backups_dir(base_dir)
    if not os.path.exists(backups_dir):
        return []
    
    backups = []
    for backup_id in os.listdir(backups_dir):
        backup_path = get_backup_path(backup_id, base_dir)
        if os.path.isdir(backup_path):
            meta_path = get_backup_metadata_path(backup_id, base_dir)
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    backup_meta = json.load(f)
                    backups.append(backup_meta)
    
    # Sort by created_at (newest first)
    backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return backups


def restore_backup(backup_id: str, base_dir=DEFAULT_BASE_DIR) -> Dict:
    """
    Restore the entire AVCPM state from a backup.
    
    Args:
        backup_id: ID of the backup to restore
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with restore results
    """
    result = {
        "success": False,
        "backup_id": backup_id,
        "branches_restored": [],
        "branches_failed": []
    }
    
    backup_path = get_backup_path(backup_id, base_dir)
    if not os.path.exists(backup_path):
        result["error"] = f"Backup {backup_id} not found"
        return result
    
    meta_path = get_backup_metadata_path(backup_id, base_dir)
    if not os.path.exists(meta_path):
        result["error"] = f"Backup metadata not found for {backup_id}"
        return result
    
    with open(meta_path, "r") as f:
        backup_meta = json.load(f)
    
    # Restore each branch
    for branch_name in backup_meta.get("branches", []):
        try:
            branch_backup_dir = os.path.join(backup_path, "branches", branch_name)
            
            # Restore staging
            staging_backup = os.path.join(branch_backup_dir, "staging")
            staging_dir = get_branch_staging_dir(branch_name, base_dir)
            if os.path.exists(staging_backup):
                if os.path.exists(staging_dir):
                    shutil.rmtree(staging_dir)
                _copy_directory_tree(staging_backup, staging_dir)
            
            # Restore ledger
            ledger_backup = os.path.join(branch_backup_dir, "ledger")
            ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
            if os.path.exists(ledger_backup):
                if os.path.exists(ledger_dir):
                    shutil.rmtree(ledger_dir)
                _copy_directory_tree(ledger_backup, ledger_dir)
            
            # Restore branch metadata
            from avcpm_branch import get_branch_metadata_path
            branch_meta_backup = os.path.join(branch_backup_dir, "branch.json")
            if os.path.exists(branch_meta_backup):
                safe_copy(branch_meta_backup, get_branch_metadata_path(branch_name, base_dir), base_dir)
            
            result["branches_restored"].append(branch_name)
        except Exception as e:
            result["branches_failed"].append({"branch": branch_name, "error": str(e)})
    
    # Restore config using safe_copy
    config_backup = os.path.join(backup_path, "config.json")
    if os.path.exists(config_backup):
        safe_copy(config_backup, os.path.join(base_dir, "config.json"), base_dir)
    
    # Update backup metadata
    backup_meta["status"] = BACKUP_STATUS_RESTORED
    backup_meta["restored_at"] = datetime.now().isoformat()
    with open(meta_path, "w") as f:
        json.dump(backup_meta, f, indent=4)
    
    result["success"] = len(result["branches_failed"]) == 0
    return result


def delete_backup(backup_id: str, base_dir=DEFAULT_BASE_DIR) -> Dict:
    """
    Delete a backup.
    
    Args:
        backup_id: ID of the backup to delete
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with deletion results
    """
    result = {
        "success": False,
        "backup_id": backup_id
    }
    
    backup_path = get_backup_path(backup_id, base_dir)
    if not os.path.exists(backup_path):
        result["error"] = f"Backup {backup_id} not found"
        return result
    
    shutil.rmtree(backup_path)
    result["success"] = True
    
    return result


# ============================================================================
# CLI INTERFACE
# ============================================================================

def _print_rollback_result(result: Dict):
    """Print rollback result in a readable format."""
    if result["success"]:
        print(f"✓ Successfully rolled back commit {result['commit_id']}")
        if result.get("backup_id"):
            print(f"  Auto-backup created: {result['backup_id']}")
        print(f"\nFiles restored:")
        for f in result.get("files_restored", []):
            if "action" in f:
                print(f"  - {f['file']}: {f['action']}")
            else:
                print(f"  - {f['file']} (from commit {f.get('restored_from', 'unknown')})")
        
        if result.get("files_not_found"):
            print(f"\nFiles not found in production (skipped):")
            for f in result["files_not_found"]:
                print(f"  - {f}")
    else:
        print(f"✗ Rollback failed: {result.get('error', 'Unknown error')}")


def _print_restore_result(result: Dict):
    """Print restore result in a readable format."""
    if result["success"]:
        print(f"✓ Successfully restored {result['filepath']}")
        print(f"  From commit: {result['commit_id']}")
        print(f"  Source: {result['restored_from']}")
    else:
        print(f"✗ Restore failed: {result.get('error', 'Unknown error')}")


def _print_reset_result(result: Dict):
    """Print reset result in a readable format."""
    if result["success"]:
        print(f"✓ Successfully reset branch '{result['branch']}' to commit {result['target_commit']}")
        if result.get("backup_id"):
            print(f"  Auto-backup created: {result['backup_id']}")
        print(f"\nCommits removed: {len(result.get('commits_removed', []))}")
        for c in result.get("commits_removed", []):
            print(f"  - {c}")
        if result.get("files_removed"):
            print(f"\nFiles removed from staging: {len(result['files_removed'])}")
    else:
        print(f"✗ Reset failed: {result.get('error', 'Unknown error')}")


def _print_backup_list(backups: List[Dict]):
    """Print backup list in a readable format."""
    if not backups:
        print("No backups found.")
        return
    
    print(f"{'Backup ID':<40} {'Name':<30} {'Created':<20} {'Status'}")
    print("-" * 100)
    
    for backup in backups:
        backup_id = backup.get("backup_id", "N/A")[:38]
        name = backup.get("name", "N/A")[:28]
        created = backup.get("created_at", "N/A")[:19]
        status = backup.get("status", "unknown")
        print(f"{backup_id:<40} {name:<30} {created:<20} {status}")


def _print_backup_create_result(backup_id: str):
    """Print backup creation result."""
    print(f"✓ Backup created: {backup_id}")


def _print_backup_restore_result(result: Dict):
    """Print backup restore result."""
    if result["success"]:
        print(f"✓ Successfully restored from backup {result['backup_id']}")
        print(f"\nBranches restored: {len(result['branches_restored'])}")
        for branch in result['branches_restored']:
            print(f"  - {branch}")
        if result.get("branches_failed"):
            print(f"\nBranches failed: {len(result['branches_failed'])}")
            for fail in result['branches_failed']:
                print(f"  - {fail['branch']}: {fail['error']}")
    else:
        print(f"✗ Restore failed: {result.get('error', 'Unknown error')}")


def main() -> Any:
    """CLI interface for rollback and recovery commands."""
    if len(sys.argv) < 2:
        print("Usage: python avcpm_rollback.py <command> [args...]")
        print("\nCommands:")
        print("  rollback <commit_id> [--dry-run]")
        print("  restore <file> [--commit <id>]")
        print("  reset <commit> [--hard] [--branch <name>]")
        print("  unstage <commit_id> [--branch <name>]")
        print("  backup create [name]")
        print("  backup list")
        print("  backup restore <id>")
        print("  backup delete <id>")
        print("\nExamples:")
        print("  python avcpm_rollback.py rollback abc123")
        print("  python avcpm_rollback.py restore myfile.py --commit def456")
        print("  python avcpm_rollback.py reset abc123 --hard")
        print("  python avcpm_rollback.py backup create pre-merge-checkpoint")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "rollback":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_rollback.py rollback <commit_id> [--dry-run]")
            sys.exit(1)
        
        commit_id = sys.argv[2]
        dry_run = "--dry-run" in sys.argv
        
        result = rollback(commit_id, dry_run=dry_run)
        _print_rollback_result(result)
        sys.exit(0 if result["success"] else 1)
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_rollback.py restore <file> [--commit <id>]")
            sys.exit(1)
        
        filepath = sys.argv[2]
        commit_id = None
        
        # Parse optional args
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--commit" and i + 1 < len(sys.argv):
                commit_id = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        result = restore_file(filepath, commit_id)
        _print_restore_result(result)
        sys.exit(0 if result["success"] else 1)
    
    elif command == "reset":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_rollback.py reset <commit> [--hard] [--branch <name>]")
            sys.exit(1)
        
        target_commit = sys.argv[2]
        hard = "--hard" in sys.argv
        branch_name = None
        
        # Parse optional args
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--branch" and i + 1 < len(sys.argv):
                branch_name = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        if hard:
            result = reset_hard(target_commit, branch_name)
        else:
            result = reset_soft(target_commit, branch_name)
        
        _print_reset_result(result)
        sys.exit(0 if result["success"] else 1)
    
    elif command == "unstage":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_rollback.py unstage <commit_id> [--branch <name>]")
            sys.exit(1)
        
        commit_id = sys.argv[2]
        branch_name = None
        
        # Parse optional args
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--branch" and i + 1 < len(sys.argv):
                branch_name = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        result = unstage(commit_id, branch_name)
        if result["success"]:
            print(f"✓ Successfully unstaged commit {result['commit_id']} from branch '{result['branch']}'")
            print(f"  Ledger entry removed: {result['ledger_removed']}")
            print(f"  Files removed from staging: {len(result['files_removed'])}")
            for f in result['files_removed']:
                print(f"    - {f}")
        else:
            print(f"✗ Unstage failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    elif command == "backup":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_rollback.py backup <subcommand>")
            print("\nBackup subcommands:")
            print("  create [name]        - Create a new backup")
            print("  list                 - List all backups")
            print("  restore <id>         - Restore from backup")
            print("  delete <id>          - Delete a backup")
            sys.exit(1)
        
        subcommand = sys.argv[2]
        
        if subcommand == "create":
            name = sys.argv[3] if len(sys.argv) > 3 else None
            backup_id = create_backup(name)
            _print_backup_create_result(backup_id)
        
        elif subcommand == "list":
            backups = list_backups()
            _print_backup_list(backups)
        
        elif subcommand == "restore":
            if len(sys.argv) < 4:
                print("Usage: python avcpm_rollback.py backup restore <backup_id>")
                sys.exit(1)
            
            backup_id = sys.argv[3]
            result = restore_backup(backup_id)
            _print_backup_restore_result(result)
            sys.exit(0 if result["success"] else 1)
        
        elif subcommand == "delete":
            if len(sys.argv) < 4:
                print("Usage: python avcpm_rollback.py backup delete <backup_id>")
                sys.exit(1)
            
            backup_id = sys.argv[3]
            result = delete_backup(backup_id)
            if result["success"]:
                print(f"✓ Backup {backup_id} deleted")
            else:
                print(f"✗ Delete failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        else:
            print(f"Unknown backup subcommand: {subcommand}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print("\nCommands: rollback, restore, reset, unstage, backup")
        sys.exit(1)


if __name__ == "__main__":
    main()
