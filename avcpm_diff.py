"""
AVCPM Diff & History System

Provides git-like diff, blame, and history functionality for AVCPM.
"""

import os
import sys
import json
import difflib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union

from avcpm_branch import (
    get_current_branch,
    get_branch_ledger_dir,
    get_branch_staging_dir,
    get_branch,
    list_branches,
    DEFAULT_BASE_DIR
)


def _get_commit_path(commit_id: str, branch_name: Optional[str] = None, base_dir: str = DEFAULT_BASE_DIR) -> Optional[str]:
    """Get the path to a commit file, searching all branches if branch not specified."""
    if branch_name:
        ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
        commit_path = os.path.join(ledger_dir, f"{commit_id}.json")
        if os.path.exists(commit_path):
            return commit_path
        return None
    
    # Search all branches
    branches = list_branches(base_dir)
    for branch in branches:
        ledger_dir = get_branch_ledger_dir(branch["name"], base_dir)
        commit_path = os.path.join(ledger_dir, f"{commit_id}.json")
        if os.path.exists(commit_path):
            return commit_path
    return None


def _load_commit(commit_id: str, branch_name: Optional[str] = None, base_dir: str = DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Load a commit's metadata."""
    commit_path = _get_commit_path(commit_id, branch_name, base_dir)
    if not commit_path:
        return None
    
    with open(commit_path, "r") as f:
        return json.load(f)


def _get_file_from_commit(commit_id: str, filepath: str, branch_name: Optional[str] = None, 
                          base_dir: str = DEFAULT_BASE_DIR) -> Optional[str]:
    """Get the content of a file at a specific commit."""
    commit_data = _load_commit(commit_id, branch_name, base_dir)
    if not commit_data:
        return None
    
    # Find the file in the commit's changes
    for change in commit_data.get("changes", []):
        if change["file"] == filepath:
            staging_path = change.get("staging_path")
            if staging_path and os.path.exists(staging_path):
                with open(staging_path, "r") as f:
                    return f.read()
    return None


def _get_file_lines(filepath: str) -> List[str]:
    """Read a file and return its lines."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return f.readlines()


def diff_files(file_a: str, file_b: str, context_lines: int = 3) -> str:
    """
    Compare two files and return a unified diff.
    
    Args:
        file_a: Path to first file
        file_b: Path to second file
        context_lines: Number of context lines in diff
        
    Returns:
        Unified diff string
    """
    lines_a = _get_file_lines(file_a)
    lines_b = _get_file_lines(file_b)
    
    # Ensure lines end with newline for proper diff
    lines_a = [line if line.endswith('\n') else line + '\n' for line in lines_a]
    lines_b = [line if line.endswith('\n') else line + '\n' for line in lines_b]
    
    diff = difflib.unified_diff(
        lines_a,
        lines_b,
        fromfile=file_a,
        tofile=file_b,
        n=context_lines
    )
    
    return ''.join(diff)


def diff_commits(commit_a: str, commit_b: str, base_dir: str = DEFAULT_BASE_DIR) -> Dict:
    """
    Compare two commits and return differences.
    
    Args:
        commit_a: First commit ID
        commit_b: Second commit ID
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with diff information
    """
    commit_a_data = _load_commit(commit_a, base_dir=base_dir)
    commit_b_data = _load_commit(commit_b, base_dir=base_dir)
    
    if not commit_a_data:
        raise ValueError(f"Commit {commit_a} not found")
    if not commit_b_data:
        raise ValueError(f"Commit {commit_b} not found")
    
    # Get file lists from each commit
    files_a = {c["file"]: c for c in commit_a_data.get("changes", [])}
    files_b = {c["file"]: c for c in commit_b_data.get("changes", [])}
    
    all_files = set(files_a.keys()) | set(files_b.keys())
    
    diffs = []
    stats = {"files_changed": 0, "insertions": 0, "deletions": 0}
    
    for filepath in sorted(all_files):
        file_a_path = None
        file_b_path = None
        
        if filepath in files_a:
            file_a_path = files_a[filepath].get("staging_path")
        if filepath in files_b:
            file_b_path = files_b[filepath].get("staging_path")
        
        # Skip if neither file exists (both deleted)
        if not file_a_path and not file_b_path:
            continue
        
        # Read file contents
        content_a = ""
        content_b = ""
        
        if file_a_path and os.path.exists(file_a_path):
            with open(file_a_path, "r") as f:
                content_a = f.read()
        if file_b_path and os.path.exists(file_b_path):
            with open(file_b_path, "r") as f:
                content_b = f.read()
        
        lines_a = content_a.splitlines(keepends=True)
        lines_b = content_b.splitlines(keepends=True)
        
        # Ensure lines end with newline
        lines_a = [line if line.endswith('\n') else line + '\n' for line in lines_a] if lines_a else []
        lines_b = [line if line.endswith('\n') else line + '\n' for line in lines_b] if lines_b else []
        
        file_diff = difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            n=3
        )
        
        diff_text = ''.join(file_diff)
        if diff_text:
            diffs.append(diff_text)
            stats["files_changed"] += 1
            
            # Calculate insertions and deletions
            for line in diff_text.split('\n'):
                if line.startswith('+') and not line.startswith('+++'):
                    stats["insertions"] += 1
                elif line.startswith('-') and not line.startswith('---'):
                    stats["deletions"] += 1
    
    return {
        "commit_a": commit_a,
        "commit_b": commit_b,
        "diff": '\n'.join(diffs),
        "stats": stats
    }


def diff_branches(branch_a: str, branch_b: str, base_dir: str = DEFAULT_BASE_DIR) -> Dict:
    """
    Compare the tips of two branches.
    
    Args:
        branch_a: First branch name
        branch_b: Second branch name
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with diff information
    """
    # Get latest commits from each branch
    branch_a_data = get_branch(branch_a, base_dir)
    branch_b_data = get_branch(branch_b, base_dir)
    
    if not branch_a_data:
        raise ValueError(f"Branch {branch_a} not found")
    if not branch_b_data:
        raise ValueError(f"Branch {branch_b} not found")
    
    # Get latest commit IDs
    ledger_a_dir = get_branch_ledger_dir(branch_a, base_dir)
    ledger_b_dir = get_branch_ledger_dir(branch_b, base_dir)
    
    commits_a = sorted([f for f in os.listdir(ledger_a_dir) if f.endswith('.json')]) if os.path.exists(ledger_a_dir) else []
    commits_b = sorted([f for f in os.listdir(ledger_b_dir) if f.endswith('.json')]) if os.path.exists(ledger_b_dir) else []
    
    if not commits_a:
        raise ValueError(f"Branch {branch_a} has no commits")
    if not commits_b:
        raise ValueError(f"Branch {branch_b} has no commits")
    
    latest_a = commits_a[-1].replace('.json', '')
    latest_b = commits_b[-1].replace('.json', '')
    
    result = diff_commits(latest_a, latest_b, base_dir)
    result["branch_a"] = branch_a
    result["branch_b"] = branch_b
    
    return result


def show_commit(commit_id: str, base_dir: str = DEFAULT_BASE_DIR) -> Dict:
    """
    Show full details of a commit.
    
    Args:
        commit_id: Commit ID to show
        base_dir: Base directory for AVCPM
        
    Returns:
        Dictionary with commit details
    """
    commit_data = _load_commit(commit_id, base_dir=base_dir)
    if not commit_data:
        raise ValueError(f"Commit {commit_id} not found")
    
    # Find which branch this commit belongs to
    branches = list_branches(base_dir)
    commit_branch = None
    for branch in branches:
        ledger_dir = get_branch_ledger_dir(branch["name"], base_dir)
        if os.path.exists(os.path.join(ledger_dir, f"{commit_id}.json")):
            commit_branch = branch["name"]
            break
    
    # Get parent commit (previous commit in branch)
    parent_commit = None
    if commit_branch:
        ledger_dir = get_branch_ledger_dir(commit_branch, base_dir)
        if os.path.exists(ledger_dir):
            commits = sorted([f for f in os.listdir(ledger_dir) if f.endswith('.json')])
            try:
                idx = commits.index(f"{commit_id}.json")
                if idx > 0:
                    parent_commit = commits[idx - 1].replace('.json', '')
            except ValueError:
                pass
    
    result = {
        "commit_id": commit_data.get("commit_id"),
        "timestamp": commit_data.get("timestamp"),
        "agent_id": commit_data.get("agent_id"),
        "task_id": commit_data.get("task_id"),
        "rationale": commit_data.get("rationale"),
        "branch": commit_branch,
        "parent_commit": parent_commit,
        "changes": commit_data.get("changes", []),
        "signature": commit_data.get("signature"),
        "changes_hash": commit_data.get("changes_hash")
    }
    
    return result


def log(branch: Optional[str] = None, limit: int = 10, base_dir: str = DEFAULT_BASE_DIR) -> List[Dict]:
    """
    Get commit history.
    
    Args:
        branch: Branch to get history for (None = current branch)
        limit: Maximum number of commits to return
        base_dir: Base directory for AVCPM
        
    Returns:
        List of commit metadata dictionaries
    """
    if branch is None:
        branch = get_current_branch(base_dir)
    
    ledger_dir = get_branch_ledger_dir(branch, base_dir)
    if not os.path.exists(ledger_dir):
        return []
    
    commit_files = sorted([f for f in os.listdir(ledger_dir) if f.endswith('.json')], reverse=True)
    
    commits = []
    for commit_file in commit_files[:limit]:
        commit_path = os.path.join(ledger_dir, commit_file)
        with open(commit_path, "r") as f:
            commit_data = json.load(f)
            commits.append({
                "commit_id": commit_data.get("commit_id"),
                "timestamp": commit_data.get("timestamp"),
                "agent_id": commit_data.get("agent_id"),
                "task_id": commit_data.get("task_id"),
                "rationale": commit_data.get("rationale"),
                "changes_count": len(commit_data.get("changes", []))
            })
    
    return commits


def file_history(filepath: str, base_dir: str = DEFAULT_BASE_DIR) -> List[Dict]:
    """
    Show all versions of a file across commits.
    
    Args:
        filepath: Path to the file
        base_dir: Base directory for AVCPM
        
    Returns:
        List of commits that modified this file
    """
    branches = list_branches(base_dir)
    history = []
    
    for branch_info in branches:
        branch_name = branch_info["name"]
        ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
        
        if not os.path.exists(ledger_dir):
            continue
        
        commit_files = sorted([f for f in os.listdir(ledger_dir) if f.endswith('.json')])
        
        for commit_file in commit_files:
            commit_path = os.path.join(ledger_dir, commit_file)
            with open(commit_path, "r") as f:
                commit_data = json.load(f)
            
            for change in commit_data.get("changes", []):
                if change["file"] == filepath:
                    history.append({
                        "commit_id": commit_data.get("commit_id"),
                        "timestamp": commit_data.get("timestamp"),
                        "agent_id": commit_data.get("agent_id"),
                        "task_id": commit_data.get("task_id"),
                        "rationale": commit_data.get("rationale"),
                        "checksum": change.get("checksum"),
                        "branch": branch_name
                    })
                    break
    
    # Sort by timestamp (newest first)
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return history


def blame(filepath: str, base_dir: str = DEFAULT_BASE_DIR) -> List[Dict]:
    """
    Show line-by-line authorship for a file.
    
    Args:
        filepath: Path to the file
        base_dir: Base directory for AVCPM
        
    Returns:
        List of lines with author information
    """
    history = file_history(filepath, base_dir)
    
    if not history:
        return []
    
    # Get the current version of the file
    current_content = ""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            current_content = f.read()
    
    lines = current_content.splitlines()
    
    # Track which commit introduced/modified each line
    blamed_lines = []
    
    for line_num, line_content in enumerate(lines, 1):
        # Find the most recent commit that touched this line
        # For simplicity, we attribute to the most recent commit that modified the file
        # A more sophisticated implementation would track individual line changes
        most_recent = history[0] if history else None
        
        blamed_lines.append({
            "line_number": line_num,
            "content": line_content,
            "commit_id": most_recent.get("commit_id") if most_recent else None,
            "agent_id": most_recent.get("agent_id") if most_recent else None,
            "timestamp": most_recent.get("timestamp") if most_recent else None
        })
    
    return blamed_lines


def format_diff_side_by_side(diff_text: str, width: int = 80) -> str:
    """
    Format a unified diff as side-by-side for human readability.
    
    Args:
        diff_text: Unified diff text
        width: Total width for display
        
    Returns:
        Side-by-side formatted diff
    """
    lines = diff_text.split('\n')
    output = []
    
    left_width = width // 2 - 2
    right_width = width // 2 - 2
    
    left_buffer = []
    right_buffer = []
    
    for line in lines:
        if line.startswith('---') or line.startswith('+++'):
            output.append(line)
        elif line.startswith('@@'):
            output.append(line)
        elif line.startswith('-'):
            left_buffer.append(line[1:])
        elif line.startswith('+'):
            right_buffer.append(line[1:])
        elif line.startswith(' '):
            left_buffer.append(line[1:])
            right_buffer.append(line[1:])
        elif line == '':
            # Flush buffers
            max_lines = max(len(left_buffer), len(right_buffer))
            for i in range(max_lines):
                left = left_buffer[i] if i < len(left_buffer) else ""
                right = right_buffer[i] if i < len(right_buffer) else ""
                
                left_trunc = left[:left_width].ljust(left_width)
                right_trunc = right[:right_width].ljust(right_width)
                
                if i < len(left_buffer) and i < len(right_buffer):
                    marker = " "  # Context
                elif i < len(left_buffer):
                    marker = "-"  # Deletion
                else:
                    marker = "+"  # Addition
                
                output.append(f"{marker} {left_trunc} | {right_trunc}")
            
            left_buffer = []
            right_buffer = []
    
    return '\n'.join(output)


def format_diff_json(diff_result: Dict) -> str:
    """
    Format diff result as JSON.
    
    Args:
        diff_result: Diff result dictionary
        
    Returns:
        JSON formatted string
    """
    return json.dumps(diff_result, indent=2)


def format_blame_output(blame_result: List[Dict], show_timestamps: bool = False) -> str:
    """
    Format blame output for display.
    
    Args:
        blame_result: Blame result from blame()
        show_timestamps: Whether to show timestamps
        
    Returns:
        Formatted blame string
    """
    lines = []
    for entry in blame_result:
        commit_id = entry.get("commit_id", "?")[:8] if entry.get("commit_id") else "?" * 8
        agent_id = entry.get("agent_id", "?")[:12] if entry.get("agent_id") else "?" * 12
        
        if show_timestamps and entry.get("timestamp"):
            ts = entry["timestamp"][:10]  # Just the date
            prefix = f"{commit_id} {agent_id} {ts}"
        else:
            prefix = f"{commit_id} {agent_id}"
        
        content = entry.get("content", "")
        lines.append(f"{prefix:30} {content}")
    
    return '\n'.join(lines)


def _print_commit_list(commits: List[Dict]):
    """Print a list of commits in a formatted way."""
    print(f"{'Commit ID':<18} {'Timestamp':<20} {'Agent':<15} {'Task':<15} {'Changes':<8} {'Rationale'}")
    print("-" * 100)
    
    for commit in commits:
        ts = commit.get("timestamp", "unknown")[:19]
        agent = commit.get("agent_id", "unknown")[:14]
        task = commit.get("task_id", "-")[:14]
        changes = str(commit.get("changes_count", 0))
        rationale = commit.get("rationale", "-")[:40]
        print(f"{commit['commit_id']:<18} {ts:<20} {agent:<15} {task:<15} {changes:<8} {rationale}")


def _print_commit_details(commit_data: Dict):
    """Print detailed commit information."""
    print(f"commit {commit_data.get('commit_id')}")
    print(f"Author: {commit_data.get('agent_id')}")
    print(f"Date: {commit_data.get('timestamp')}")
    if commit_data.get('branch'):
        print(f"Branch: {commit_data.get('branch')}")
    if commit_data.get('parent_commit'):
        print(f"Parent: {commit_data.get('parent_commit')}")
    print(f"Task: {commit_data.get('task_id')}")
    print(f"Signature: {commit_data.get('signature', 'N/A')[:16]}..." if commit_data.get('signature') else "Signature: N/A")
    print()
    print(f"    {commit_data.get('rationale', 'No rationale')}")
    print()
    print("Changes:")
    for change in commit_data.get("changes", []):
        print(f"    {change.get('file')} ({change.get('checksum', 'N/A')[:16]}...)")


def _print_diff_stats(stats: Dict):
    """Print diff statistics."""
    print(f"Files changed: {stats.get('files_changed', 0)}")
    print(f"Insertions: {stats.get('insertions', 0)}")
    print(f"Deletions: {stats.get('deletions', 0)}")


def main():
    """CLI interface for diff and history commands."""
    if len(sys.argv) < 2:
        print("Usage: python avcpm_diff.py <command> [args...]")
        print("\nCommands:")
        print("  diff <commit_a> <commit_b> [--json] [--side-by-side]")
        print("  show <commit_id>")
        print("  log [--branch <name>] [--limit N]")
        print("  blame <file> [--timestamp]")
        print("  history <file> [--json]")
        print("\nExamples:")
        print("  python avcpm_diff.py diff abc123 def456")
        print("  python avcpm_diff.py log --limit 20")
        print("  python avcpm_diff.py blame myfile.py")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "diff":
        if len(sys.argv) < 4:
            print("Usage: python avcpm_diff.py diff <commit_a> <commit_b> [--json] [--side-by-side]")
            sys.exit(1)
        
        commit_a = sys.argv[2]
        commit_b = sys.argv[3]
        output_json = "--json" in sys.argv
        side_by_side = "--side-by-side" in sys.argv
        
        try:
            result = diff_commits(commit_a, commit_b)
            
            if output_json:
                print(format_diff_json(result))
            elif side_by_side:
                print(format_diff_side_by_side(result["diff"]))
            else:
                print(result["diff"])
                print()
                _print_diff_stats(result["stats"])
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "show":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_diff.py show <commit_id>")
            sys.exit(1)
        
        commit_id = sys.argv[2]
        
        try:
            result = show_commit(commit_id)
            _print_commit_details(result)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "log":
        branch = None
        limit = 10
        
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--branch" and i + 1 < len(sys.argv):
                branch = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                try:
                    limit = int(sys.argv[i + 1])
                except ValueError:
                    print(f"Invalid limit: {sys.argv[i + 1]}")
                    sys.exit(1)
                i += 2
            else:
                i += 1
        
        commits = log(branch, limit)
        if commits:
            _print_commit_list(commits)
        else:
            print(f"No commits found" + (f" in branch '{branch}'" if branch else ""))
    
    elif command == "blame":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_diff.py blame <file> [--timestamp]")
            sys.exit(1)
        
        filepath = sys.argv[2]
        show_timestamps = "--timestamp" in sys.argv
        
        try:
            result = blame(filepath)
            if result:
                print(format_blame_output(result, show_timestamps))
            else:
                print(f"No history found for {filepath}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == "history":
        if len(sys.argv) < 3:
            print("Usage: python avcpm_diff.py history <file> [--json]")
            sys.exit(1)
        
        filepath = sys.argv[2]
        output_json = "--json" in sys.argv
        
        try:
            result = file_history(filepath)
            if output_json:
                print(json.dumps(result, indent=2))
            else:
                if result:
                    print(f"History for {filepath}:")
                    print(f"{'Commit ID':<18} {'Timestamp':<20} {'Agent':<15} {'Task':<15} {'Branch'}")
                    print("-" * 90)
                    for entry in result:
                        ts = entry.get("timestamp", "unknown")[:19]
                        agent = entry.get("agent_id", "unknown")[:14]
                        task = entry.get("task_id", "-")[:14]
                        branch_name = entry.get("branch", "-")
                        print(f"{entry['commit_id']:<18} {ts:<20} {agent:<15} {task:<15} {branch_name}")
                else:
                    print(f"No history found for {filepath}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print("\nCommands: diff, show, log, blame, history")
        sys.exit(1)


if __name__ == "__main__":
    main()
