from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union, Any
"""
AVCPM Conflict Detection & Resolution Module

Provides three-way merge capabilities and conflict detection for AVCPM branching.
"""

import os
import sys
import json
import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

from avcpm_branch import (
    get_branch_dir,
    get_branch_ledger_dir,
    get_branch_staging_dir,
    get_branch,
    get_current_branch,
    DEFAULT_BASE_DIR
)

# Conflict statuses
CONFLICT_STATUS_OPEN = "open"
CONFLICT_STATUS_RESOLVED = "resolved"
CONFLICT_STATUS_ABORTED = "aborted"

# Resolution strategies
RESOLUTION_STRATEGIES = ["ours", "theirs", "union", "manual"]


def get_conflicts_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the conflicts directory path."""
    return os.path.join(base_dir, "conflicts")


def get_conflict_path(conflict_id, base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the path to a conflict file."""
    return os.path.join(get_conflicts_dir(base_dir), f"{conflict_id}.json")


def _generate_conflict_id():
    """Generate a unique conflict ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = hashlib.md5(os.urandom(8)).hexdigest()[:6]
    return f"conflict_{timestamp}_{rand}"


def _calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    if not os.path.exists(filepath):
        return None
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def _read_file_content(filepath):
    """Read file content, return empty string if file doesn't exist."""
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _write_file_content(filepath, content):
    """Write content to file, creating parent directories if needed."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def list_modified_files(branch, since_commit=None, base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    """
    List files modified in a branch since a specific commit.
    
    Args:
        branch: Branch name
        since_commit: Commit ID to start from (if None, returns all files in branch)
        base_dir: Base directory for AVCPM
        
    Returns:
        dict: {file_path: latest_commit_id} for modified files
    """
    ledger_dir = get_branch_ledger_dir(branch, base_dir)
    if not os.path.exists(ledger_dir):
        return {}
    
    # Get all commits in chronological order
    commit_files = sorted([f for f in os.listdir(ledger_dir) if f.endswith(".json")])
    
    modified_files = {}
    found_since = since_commit is None
    
    for commit_file in commit_files:
        commit_id = commit_file.replace(".json", "")
        
        # Skip commits before since_commit
        if not found_since:
            if commit_id == since_commit:
                found_since = True
            continue
        
        # Read commit data
        commit_path = os.path.join(ledger_dir, commit_file)
        try:
            with open(commit_path, "r") as f:
                commit_data = json.load(f)
        except Exception:
            continue
        
        # Track modified files
        for change in commit_data.get("changes", []):
            file_path = change.get("file")
            if file_path:
                modified_files[file_path] = commit_id
    
    return modified_files


def _get_file_at_commit(file_path, commit_id, branch, base_dir=DEFAULT_BASE_DIR):
    """
    Get the content of a file at a specific commit.
    
    Args:
        file_path: Path to the file
        commit_id: Commit ID
        branch: Branch name
        base_dir: Base directory for AVCPM
        
    Returns:
        str: File content or None if not found
    """
    ledger_dir = get_branch_ledger_dir(branch, base_dir)
    commit_path = os.path.join(ledger_dir, f"{commit_id}.json")
    
    if not os.path.exists(commit_path):
        return None
    
    with open(commit_path, "r") as f:
        commit_data = json.load(f)
    
    # Find the file in the commit
    for change in commit_data.get("changes", []):
        if change.get("file") == file_path:
            staging_path = change.get("staging_path")
            if staging_path and os.path.exists(staging_path):
                return _read_file_content(staging_path)
    
    return None


def _find_common_ancestor(branch_a, branch_b, base_dir=DEFAULT_BASE_DIR):
    """
    Find the common ancestor commit between two branches.
    
    Args:
        branch_a: First branch name
        branch_b: Second branch name
        base_dir: Base directory for AVCPM
        
    Returns:
        str: Commit ID of common ancestor or None
    """
    # Get branch metadata
    meta_a = get_branch(branch_a, base_dir)
    meta_b = get_branch(branch_b, base_dir)
    
    if not meta_a or not meta_b:
        return None
    
    # Get all commits from branch_a
    ledger_a = get_branch_ledger_dir(branch_a, base_dir)
    commits_a = set()
    if os.path.exists(ledger_a):
        commits_a = set(f.replace(".json", "") for f in os.listdir(ledger_a) if f.endswith(".json"))
    
    # Get all commits from branch_b
    ledger_b = get_branch_ledger_dir(branch_b, base_dir)
    commits_b = set()
    if os.path.exists(ledger_b):
        commits_b = set(f.replace(".json", "") for f in os.listdir(ledger_b) if f.endswith(".json"))
    
    # Common commits are the intersection
    common = commits_a & commits_b
    
    if not common:
        # No common commits - use parent_commit if available
        parent_a = meta_a.get("parent_commit")
        parent_b = meta_b.get("parent_commit")
        if parent_a and parent_a == parent_b:
            return parent_a
        return None
    
    # Return the most recent common commit (sorted, last one)
    return sorted(common)[-1]


def check_file_conflict(file_a, file_b, base_file) -> bool:
    """
    Check if a single file has conflicts between versions.
    
    Args:
        file_a: Path to file in branch A (or content string)
        file_b: Path to file in branch B (or content string)
        base_file: Path to base file (or content string, or None)
        
    Returns:
        dict: {
            "has_conflict": bool,
            "conflict_type": str ("content"|"add_add"|"delete_modify"|"none"),
            "details": str
        }
    """
    # Handle file paths vs content
    def get_content(f) -> Optional[Dict]:
        if f is None:
            return None
        if os.path.exists(f):
            return _read_file_content(f)
        return f
    
    content_a = get_content(file_a)
    content_b = get_content(file_b)
    content_base = get_content(base_file) if base_file else None
    
    # Both files don't exist - no conflict
    if content_a is None and content_b is None:
        return {"has_conflict": False, "conflict_type": "none", "details": "Both files deleted"}
    
    # File deleted in A, modified in B
    if content_a is None and content_b is not None:
        if content_base is None:
            # Added in B, deleted in A (edge case)
            return {"has_conflict": True, "conflict_type": "add_delete", "details": "File added in one branch, deleted in other"}
        return {"has_conflict": True, "conflict_type": "delete_modify", "details": "File deleted in branch A, modified in branch B"}
    
    # File deleted in B, modified in A
    if content_b is None and content_a is not None:
        if content_base is None:
            return {"has_conflict": True, "conflict_type": "add_delete", "details": "File added in one branch, deleted in other"}
        return {"has_conflict": True, "conflict_type": "delete_modify", "details": "File deleted in branch B, modified in branch A"}
    
    # Both files added (no base)
    if content_base is None:
        if content_a != content_b:
            return {"has_conflict": True, "conflict_type": "add_add", "details": "File added in both branches with different content"}
        return {"has_conflict": False, "conflict_type": "none", "details": "File added in both branches with same content"}
    
    # Both files exist - check for content conflicts
    if content_a == content_b:
        return {"has_conflict": False, "conflict_type": "none", "details": "Files are identical"}
    
    # Check if one is just the base (no changes)
    if content_a == content_base:
        return {"has_conflict": False, "conflict_type": "none", "details": "Only branch B modified the file"}
    
    if content_b == content_base:
        return {"has_conflict": False, "conflict_type": "none", "details": "Only branch A modified the file"}
    
    # Both modified from base differently - potential conflict
    return {"has_conflict": True, "conflict_type": "content", "details": "Both branches modified the file"}


def merge_three_way(base_content, a_content, b_content) -> Any:
    """
    Perform a three-way merge.
    
    Args:
        base_content: Base version content (or None)
        a_content: Branch A version content (or None)
        b_content: Branch B version content (or None)
        
    Returns:
        dict: {
            "merged_content": str,
            "has_conflict": bool,
            "conflict_sections": list of (start, end) tuples
        }
    """
    result = {
        "merged_content": "",
        "has_conflict": False,
        "conflict_sections": []
    }
    
    # Handle None values
    if base_content is None:
        base_content = ""
    if a_content is None:
        a_content = ""
    if b_content is None:
        b_content = ""
    
    # Simple cases first
    if a_content == b_content:
        result["merged_content"] = a_content
        return result
    
    if a_content == base_content:
        result["merged_content"] = b_content
        return result
    
    if b_content == base_content:
        result["merged_content"] = a_content
        return result
    
    # Line-by-line merge
    base_lines = base_content.splitlines(keepends=True)
    a_lines = a_content.splitlines(keepends=True)
    b_lines = b_content.splitlines(keepends=True)
    
    # Add newlines if missing at end
    if base_lines and not base_lines[-1].endswith('\n'):
        base_lines[-1] += '\n'
    if a_lines and not a_lines[-1].endswith('\n'):
        a_lines[-1] += '\n'
    if b_lines and not b_lines[-1].endswith('\n'):
        b_lines[-1] += '\n'
    
    matcher_a = SequenceMatcher(None, base_lines, a_lines)
    matcher_b = SequenceMatcher(None, base_lines, b_lines)
    
    # Get opcodes for both diffs
    ops_a = list(matcher_a.get_opcodes())
    ops_b = list(matcher_b.get_opcodes())
    
    merged_lines = []
    i = 0
    
    # Process line by line through base
    while i < len(base_lines):
        # Find operations affecting this line in both branches
        op_a = None
        op_b = None
        
        for tag, i1, i2, j1, j2 in ops_a:
            if i1 <= i < i2:
                op_a = (tag, i1, i2, j1, j2)
                break
        
        for tag, i1, i2, j1, j2 in ops_b:
            if i1 <= i < i2:
                op_b = (tag, i1, i2, j1, j2)
                break
        
        if op_a is None:
            op_a = ('equal', i, i+1, i, i+1)
        if op_b is None:
            op_b = ('equal', i, i+1, i, i+1)
        
        tag_a, a_i1, a_i2, a_j1, a_j2 = op_a
        tag_b, b_i1, b_i2, b_j1, b_j2 = op_b
        
        # Both equal - keep base
        if tag_a == 'equal' and tag_b == 'equal':
            merged_lines.append(base_lines[i])
            i += 1
            continue
        
        # Only A changed
        if tag_b == 'equal':
            if tag_a == 'delete':
                # A deleted, skip this line
                i = a_i2
            elif tag_a == 'replace' or tag_a == 'insert':
                # A modified/added
                merged_lines.extend(a_lines[a_j1:a_j2])
                i = a_i2
            continue
        
        # Only B changed
        if tag_a == 'equal':
            if tag_b == 'delete':
                i = b_i2
            elif tag_b == 'replace' or tag_b == 'insert':
                merged_lines.extend(b_lines[b_j1:b_j2])
                i = b_i2
            continue
        
        # Both changed - potential conflict
        # Get the changes
        a_changed = a_lines[a_j1:a_j2] if tag_a in ('replace', 'insert') else []
        b_changed = b_lines[b_j1:b_j2] if tag_b in ('replace', 'insert') else []
        
        # If changes are identical, no conflict
        if a_changed == b_changed:
            merged_lines.extend(a_changed)
            i = max(a_i2, b_i2)
            continue
        
        # CONFLICT - mark it
        start_idx = len(merged_lines)
        merged_lines.append("<<<<<<< branch_a\n")
        merged_lines.extend(a_changed if a_changed else ["(deleted)\n"])
        merged_lines.append("=======\n")
        merged_lines.extend(b_changed if b_changed else ["(deleted)\n"])
        merged_lines.append(">>>>>>> branch_b\n")
        end_idx = len(merged_lines)
        
        result["has_conflict"] = True
        result["conflict_sections"].append((start_idx, end_idx))
        
        i = max(a_i2, b_i2)
    
    # Handle any remaining insertions at end
    for tag, i1, i2, j1, j2 in ops_a:
        if tag in ('insert', 'replace') and i1 >= len(base_lines):
            merged_lines.extend(a_lines[j1:j2])
    
    for tag, i1, i2, j1, j2 in ops_b:
        if tag in ('insert', 'replace') and i1 >= len(base_lines):
            # Check if already added from A
            b_new = b_lines[j1:j2]
            if b_new not in [a_lines[x:y] for _, x, y, _, _ in ops_a if _ in ('insert', 'replace')]:
                # If A also added here, it's a conflict
                merged_lines.append("<<<<<<< branch_a\n")
                merged_lines.append("(no changes)\n")
                merged_lines.append("=======\n")
                merged_lines.extend(b_new)
                merged_lines.append(">>>>>>> branch_b\n")
                result["has_conflict"] = True
                result["conflict_sections"].append((len(merged_lines) - 5 - len(b_new), len(merged_lines)))
            else:
                merged_lines.extend(b_new)
    
    result["merged_content"] = "".join(merged_lines)
    return result


def merge_files(base_file, a_file, b_file, output_file) -> Any:
    """
    Merge files with conflict markers.
    
    Args:
        base_file: Path to base file (or None)
        a_file: Path to file in branch A
        b_file: Path to file in branch B
        output_file: Path to write merged output
        
    Returns:
        dict: {"success": bool, "has_conflict": bool, "output_file": str}
    """
    base_content = _read_file_content(base_file) if base_file and os.path.exists(base_file) else None
    a_content = _read_file_content(a_file) if a_file and os.path.exists(a_file) else None
    b_content = _read_file_content(b_file) if b_file and os.path.exists(b_file) else None
    
    # Check for file-level conflicts first
    conflict_check = check_file_conflict(
        a_content if a_content else a_file,
        b_content if b_content else b_file,
        base_content if base_content else base_file
    )
    
    if not conflict_check["has_conflict"]:
        # Use whichever side has content (prefer a if both)
        merged = a_content if a_content else b_content
        if merged is None:
            merged = ""
        _write_file_content(output_file, merged)
        return {"success": True, "has_conflict": False, "output_file": output_file}
    
    # Perform three-way merge
    result = merge_three_way(base_content, a_content, b_content)
    _write_file_content(output_file, result["merged_content"])
    
    return {
        "success": True,
        "has_conflict": result["has_conflict"],
        "output_file": output_file,
        "conflict_sections": result["conflict_sections"]
    }


def detect_conflicts(branch_a, branch_b, base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    """
    Find conflicts between two branches.
    
    Args:
        branch_a: First branch name
        branch_b: Second branch name
        base_dir: Base directory for AVCPM
        
    Returns:
        dict: {
            "conflicts": list of conflict dicts,
            "conflict_count": int,
            "auto_mergeable": bool,
            "base_commit": str
        }
    """
    # Find common ancestor
    base_commit = _find_common_ancestor(branch_a, branch_b, base_dir)
    
    # Get modified files in both branches
    files_a = list_modified_files(branch_a, base_commit, base_dir)
    files_b = list_modified_files(branch_b, base_commit, base_dir)
    
    # Find overlapping files
    overlapping = set(files_a.keys()) & set(files_b.keys())
    
    conflicts = []
    conflicts_dir = get_conflicts_dir(base_dir)
    os.makedirs(conflicts_dir, exist_ok=True)
    
    for file_path in overlapping:
        # Get file content at base, branch_a, branch_b
        base_content = None
        if base_commit:
            base_content = _get_file_at_commit(file_path, base_commit, branch_a, base_dir)
            if base_content is None:
                base_content = _get_file_at_commit(file_path, base_commit, branch_b, base_dir)
        
        # Get latest content in each branch
        a_content = _get_file_at_commit(file_path, files_a[file_path], branch_a, base_dir)
        b_content = _get_file_at_commit(file_path, files_b[file_path], branch_b, base_dir)
        
        # Check for conflict
        conflict_check = check_file_conflict(
            a_content if a_content else None,
            b_content if b_content else None,
            base_content
        )
        
        if conflict_check["has_conflict"]:
            conflict_id = _generate_conflict_id()
            conflict_data = {
                "conflict_id": conflict_id,
                "file": file_path,
                "branch_a": branch_a,
                "branch_b": branch_b,
                "base_commit": base_commit,
                "commit_a": files_a[file_path],
                "commit_b": files_b[file_path],
                "status": CONFLICT_STATUS_OPEN,
                "conflict_type": conflict_check["conflict_type"],
                "details": conflict_check["details"],
                "detected_at": datetime.now().isoformat(),
                "resolved_at": None,
                "resolution": None,
                "resolution_strategy": None
            }
            
            # Save conflict
            conflict_path = get_conflict_path(conflict_id, base_dir)
            with open(conflict_path, "w") as f:
                json.dump(conflict_data, f, indent=4)
            
            conflicts.append(conflict_data)
    
    return {
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "auto_mergeable": len(conflicts) == 0,
        "base_commit": base_commit,
        "files_a": files_a,
        "files_b": files_b
    }


def auto_merge_possible(branch_a, branch_b, base_dir=DEFAULT_BASE_DIR) -> bool:
    """
    Check if auto-merge is safe between two branches.
    
    Args:
        branch_a: First branch name
        branch_b: Second branch name
        base_dir: Base directory for AVCPM
        
    Returns:
        bool: True if auto-merge is safe (no conflicts)
    """
    result = detect_conflicts(branch_a, branch_b, base_dir)
    return result["auto_mergeable"]


def get_conflicts(status="open", base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """
    List conflicts with optional status filter.
    
    Args:
        status: "open", "resolved", "aborted", or "all"
        base_dir: Base directory for AVCPM
        
    Returns:
        list: List of conflict dictionaries
    """
    conflicts_dir = get_conflicts_dir(base_dir)
    if not os.path.exists(conflicts_dir):
        return []
    
    conflicts = []
    for filename in os.listdir(conflicts_dir):
        if not filename.endswith(".json"):
            continue
        
        conflict_path = os.path.join(conflicts_dir, filename)
        try:
            with open(conflict_path, "r") as f:
                conflict_data = json.load(f)
        except Exception:
            continue
        
        if status == "all" or conflict_data.get("status") == status:
            conflicts.append(conflict_data)
    
    # Sort by detection time
    conflicts.sort(key=lambda x: x.get("detected_at", ""), reverse=True)
    return conflicts


def resolve_conflict(conflict_id, resolution_strategy, base_dir=DEFAULT_BASE_DIR, **kwargs) -> bool:
    """
    Mark a conflict as resolved with a given strategy.
    
    Args:
        conflict_id: Conflict ID to resolve
        resolution_strategy: One of "ours", "theirs", "union", "manual"
        base_dir: Base directory for AVCPM
        **kwargs: Additional arguments (e.g., manual_content for manual resolution)
        
    Returns:
        dict: Resolution result
        
    Raises:
        ValueError: If conflict not found or invalid strategy
    """
    if resolution_strategy not in RESOLUTION_STRATEGIES:
        raise ValueError(f"Invalid resolution strategy: {resolution_strategy}. Must be one of: {RESOLUTION_STRATEGIES}")
    
    conflict_path = get_conflict_path(conflict_id, base_dir)
    if not os.path.exists(conflict_path):
        raise ValueError(f"Conflict '{conflict_id}' not found")
    
    with open(conflict_path, "r") as f:
        conflict_data = json.load(f)
    
    if conflict_data.get("status") != CONFLICT_STATUS_OPEN:
        raise ValueError(f"Conflict '{conflict_id}' is already {conflict_data.get('status')}")
    
    # Apply resolution strategy
    branch_a = conflict_data["branch_a"]
    branch_b = conflict_data["branch_b"]
    file_path = conflict_data["file"]
    commit_a = conflict_data["commit_a"]
    commit_b = conflict_data["commit_b"]
    
    # Get file contents
    a_content = _get_file_at_commit(file_path, commit_a, branch_a, base_dir)
    b_content = _get_file_at_commit(file_path, commit_b, branch_b, base_dir)
    base_commit = conflict_data.get("base_commit")
    base_content = None
    if base_commit:
        base_content = _get_file_at_commit(file_path, base_commit, branch_a, base_dir)
    
    resolved_content = None
    
    if resolution_strategy == "ours":
        resolved_content = a_content if a_content is not None else ""
    elif resolution_strategy == "theirs":
        resolved_content = b_content if b_content is not None else ""
    elif resolution_strategy == "union":
        merge_result = merge_three_way(base_content, a_content, b_content)
        if merge_result["has_conflict"]:
            # Take both without conflict markers
            lines_a = (a_content or "").splitlines(keepends=True)
            lines_b = (b_content or "").splitlines(keepends=True)
            # Simple union: unique lines from both
            all_lines = list(dict.fromkeys(lines_a + lines_b))
            resolved_content = "".join(all_lines)
        else:
            resolved_content = merge_result["merged_content"]
    elif resolution_strategy == "manual":
        resolved_content = kwargs.get("manual_content")
        if resolved_content is None:
            raise ValueError("manual_content required for 'manual' resolution strategy")
    
    # Update conflict data
    conflict_data["status"] = CONFLICT_STATUS_RESOLVED
    conflict_data["resolution_strategy"] = resolution_strategy
    conflict_data["resolved_at"] = datetime.now().isoformat()
    conflict_data["resolution"] = resolved_content
    
    # Save updated conflict
    with open(conflict_path, "w") as f:
        json.dump(conflict_data, f, indent=4)
    
    return {
        "success": True,
        "conflict_id": conflict_id,
        "strategy": resolution_strategy,
        "file": file_path,
        "resolved_content": resolved_content
    }


def _print_conflict_list(conflicts):
    """Print conflict list in a formatted way."""
    if not conflicts:
        print("No conflicts found.")
        return
    
    print(f"{'Conflict ID':<30} {'Status':<10} {'Type':<15} {'File'}")
    print("-" * 100)
    
    for conflict in conflicts:
        cid = conflict.get("conflict_id", "unknown")
        status = conflict.get("status", "unknown")
        ctype = conflict.get("conflict_type", "unknown")
        file_path = conflict.get("file", "unknown")
        # Truncate long file paths
        if len(file_path) > 40:
            file_path = "..." + file_path[-37:]
        print(f"{cid:<30} {status:<10} {ctype:<15} {file_path}")


def main() -> Any:
    """CLI interface for conflict detection and resolution."""
    if len(sys.argv) < 2:
        print("Usage: python avcpm_conflict.py <command> [args...]")
        print("\nCommands:")
        print("  detect <branch_a> <branch_b>")
        print("  list [--status open|resolved|aborted|all]")
        print("  resolve <conflict_id> --strategy <ours|theirs|union>")
        print("  check <branch_a> <branch_b>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "detect":
        if len(sys.argv) < 4:
            print("Usage: python avcpm_conflict.py detect <branch_a> <branch_b>")
            sys.exit(1)
        
        branch_a = sys.argv[2]
        branch_b = sys.argv[3]
        
        try:
            result = detect_conflicts(branch_a, branch_b)
            
            if result["conflict_count"] == 0:
                print(f"No conflicts detected between '{branch_a}' and '{branch_b}'")
                print(f"Base commit: {result['base_commit'] or 'none'}")
                print("Auto-merge is safe.")
            else:
                print(f"Detected {result['conflict_count']} conflict(s) between '{branch_a}' and '{branch_b}':")
                print()
                for conflict in result["conflicts"]:
                    print(f"  Conflict ID: {conflict['conflict_id']}")
                    print(f"  File: {conflict['file']}")
                    print(f"  Type: {conflict['conflict_type']}")
                    print(f"  Details: {conflict['details']}")
                    print()
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "list":
        status = "open"
        
        # Parse optional args
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                status = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        conflicts = get_conflicts(status)
        print(f"Conflicts (status: {status}):")
        _print_conflict_list(conflicts)
    
    elif command == "resolve":
        if len(sys.argv) < 4:
            print("Usage: python avcpm_conflict.py resolve <conflict_id> --strategy <ours|theirs|union>")
            sys.exit(1)
        
        conflict_id = sys.argv[2]
        strategy = None
        
        # Parse args
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--strategy" and i + 1 < len(sys.argv):
                strategy = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        if strategy is None:
            print("Error: --strategy is required")
            sys.exit(1)
        
        try:
            result = resolve_conflict(conflict_id, strategy)
            print(f"Resolved conflict '{conflict_id}' using '{strategy}' strategy")
            print(f"File: {result['file']}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "check":
        if len(sys.argv) < 4:
            print("Usage: python avcpm_conflict.py check <branch_a> <branch_b>")
            sys.exit(1)
        
        branch_a = sys.argv[2]
        branch_b = sys.argv[3]
        
        try:
            is_safe = auto_merge_possible(branch_a, branch_b)
            if is_safe:
                print(f"Auto-merge is SAFE between '{branch_a}' and '{branch_b}'")
            else:
                print(f"Auto-merge is NOT SAFE between '{branch_a}' and '{branch_b}'")
                print("Run 'detect' command to see conflicts.")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print("\nCommands: detect, list, resolve, check")
        sys.exit(1)


if __name__ == "__main__":
    main()
