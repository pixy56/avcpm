#!/usr/bin/env python3
"""
AVCPM Work-in-Progress Tracking Module
Phase 3: Proactive Coordination

Provides file claim management to prevent editing conflicts between agents.
"""

import os
import sys
import json
import glob
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from avcpm_security import protect_avcpm_directory, safe_makedirs, safe_write_text, safe_read_text

DEFAULT_BASE_DIR = "."
WIP_DIR = ".avcpm"
WIP_REGISTRY = "wip_registry.json"


def _get_wip_path(base_dir: str = DEFAULT_BASE_DIR) -> str:
    """Get the path to the WIP registry file."""
    return os.path.join(base_dir, WIP_DIR, WIP_REGISTRY)


def _ensure_wip_dir(base_dir: str = DEFAULT_BASE_DIR) -> str:
    """Ensure the .avcpm directory exists with symlink protection."""
    protect_avcpm_directory(os.path.join(base_dir, WIP_DIR))
    wip_dir = os.path.join(base_dir, WIP_DIR)
    safe_makedirs(wip_dir, os.path.abspath(base_dir), exist_ok=True)
    return wip_dir


def _load_registry(base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """Load the WIP registry with symlink protection."""
    wip_path = _get_wip_path(base_dir)
    if os.path.exists(wip_path):
        try:
            content = safe_read_text(wip_path, os.path.abspath(base_dir))
            return json.loads(content)
        except (json.JSONDecodeError, IOError):
            return {"claims": {}}
    return {"claims": {}}


def _save_registry(registry: Dict[str, Any], base_dir: str = DEFAULT_BASE_DIR) -> None:
    """Save the WIP registry with symlink protection."""
    _ensure_wip_dir(base_dir)
    wip_path = _get_wip_path(base_dir)
    protect_avcpm_directory(os.path.join(base_dir, WIP_DIR))
    safe_write_text(wip_path, json.dumps(registry, indent=2), os.path.abspath(base_dir))


def _normalize_path(filepath: str, base_dir: str = DEFAULT_BASE_DIR) -> str:
    """Normalize a file path relative to base_dir."""
    abs_path = os.path.abspath(os.path.join(base_dir, filepath))
    base_abs = os.path.abspath(base_dir)
    try:
        rel_path = os.path.relpath(abs_path, base_abs)
        return rel_path
    except ValueError:
        return filepath


def claim_file(filepath: str, agent_id: str, task_id: Optional[str] = None,
               base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """
    Mark a file as being worked on by an agent.
    
    Args:
        filepath: Path to the file to claim
        agent_id: ID of the agent claiming the file
        task_id: Optional task ID associated with the claim
        base_dir: Base directory for the WIP registry
    
    Returns:
        Dict with 'success' boolean and 'message' or 'claim' details
    """
    registry = _load_registry(base_dir)
    normalized_path = _normalize_path(filepath, base_dir)
    
    # Check if already claimed by someone else
    if normalized_path in registry["claims"]:
        existing = registry["claims"][normalized_path]
        if existing["claimed_by"] != agent_id:
            return {
                "success": False,
                "message": f"File already claimed by {existing['claimed_by']} "
                           f"(task: {existing.get('task_id', 'N/A')})"
            }
    
    now = datetime.utcnow()
    expires = now + timedelta(hours=24)
    
    claim = {
        "file": normalized_path,
        "claimed_by": agent_id,
        "task_id": task_id,
        "claimed_at": now.isoformat(),
        "expires_at": expires.isoformat()
    }
    
    registry["claims"][normalized_path] = claim
    _save_registry(registry, base_dir)
    
    return {"success": True, "claim": claim}


def claim_files(pattern: str, agent_id: str, task_id: Optional[str] = None,
                base_dir: str = DEFAULT_BASE_DIR) -> List[Dict[str, Any]]:
    """
    Claim multiple files matching a glob pattern.
    
    Args:
        pattern: Glob pattern to match files
        agent_id: ID of the agent claiming the files
        task_id: Optional task ID associated with the claims
        base_dir: Base directory for the WIP registry
    
    Returns:
        List of result dicts for each file
    """
    matches = glob.glob(os.path.join(base_dir, pattern))
    results = []
    
    for match in matches:
        if os.path.isfile(match):
            rel_path = _normalize_path(match, base_dir)
            result = claim_file(rel_path, agent_id, task_id, base_dir)
            results.append({"file": rel_path, **result})
    
    return results


def release_file(filepath: str, agent_id: str, base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """
    Release a claim on a file.
    
    Args:
        filepath: Path to the file to release
        agent_id: ID of the agent releasing the file
        base_dir: Base directory for the WIP registry
    
    Returns:
        Dict with 'success' boolean and 'message'
    """
    registry = _load_registry(base_dir)
    normalized_path = _normalize_path(filepath, base_dir)
    
    if normalized_path not in registry["claims"]:
        return {"success": False, "message": "File not claimed"}
    
    existing = registry["claims"][normalized_path]
    if existing["claimed_by"] != agent_id:
        return {
            "success": False,
            "message": f"Cannot release: file claimed by {existing['claimed_by']}"
        }
    
    del registry["claims"][normalized_path]
    _save_registry(registry, base_dir)
    
    return {"success": True, "message": "Claim released"}


def release_all(agent_id: str, base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """
    Release all claims by an agent.
    
    Args:
        agent_id: ID of the agent releasing all claims
        base_dir: Base directory for the WIP registry
    
    Returns:
        Dict with 'success' boolean, 'released_count', and 'message'
    """
    registry = _load_registry(base_dir)
    released = []
    
    for filepath, claim in list(registry["claims"].items()):
        if claim["claimed_by"] == agent_id:
            del registry["claims"][filepath]
            released.append(filepath)
    
    _save_registry(registry, base_dir)
    
    return {
        "success": True,
        "released_count": len(released),
        "released_files": released,
        "message": f"Released {len(released)} claim(s)"
    }


def list_claims(base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """
    List all claimed files.
    
    Args:
        base_dir: Base directory for the WIP registry
    
    Returns:
        Dict with 'claims' list and 'count'
    """
    registry = _load_registry(base_dir)
    claims = list(registry["claims"].values())
    
    return {
        "count": len(claims),
        "claims": claims
    }


def list_my_claims(agent_id: str, base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """
    List all claims by a specific agent.
    
    Args:
        agent_id: ID of the agent to list claims for
        base_dir: Base directory for the WIP registry
    
    Returns:
        Dict with 'claims' list and 'count'
    """
    registry = _load_registry(base_dir)
    my_claims = [
        claim for claim in registry["claims"].values()
        if claim["claimed_by"] == agent_id
    ]
    
    return {
        "count": len(my_claims),
        "claims": my_claims
    }


def get_claim(filepath: str, base_dir: str = DEFAULT_BASE_DIR) -> Optional[Dict[str, Any]]:
    """
    Get claim details for a specific file.
    
    Args:
        filepath: Path to the file to check
        base_dir: Base directory for the WIP registry
    
    Returns:
        Claim dict or None if not claimed
    """
    registry = _load_registry(base_dir)
    normalized_path = _normalize_path(filepath, base_dir)
    
    return registry["claims"].get(normalized_path)


def is_claimed(filepath: str, base_dir: str = DEFAULT_BASE_DIR) -> bool:
    """
    Check if a file is claimed.
    
    Args:
        filepath: Path to the file to check
        base_dir: Base directory for the WIP registry
    
    Returns:
        True if claimed, False otherwise
    """
    return get_claim(filepath, base_dir) is not None


def check_wip_conflicts(files: List[str], agent_id: str,
                        base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """
    Check if files conflict with existing claims.
    
    Args:
        files: List of file paths to check
        agent_id: ID of the agent checking (to exclude own claims)
        base_dir: Base directory for the WIP registry
    
    Returns:
        Dict with 'has_conflicts', 'conflicts' list, and 'clear' list
    """
    registry = _load_registry(base_dir)
    conflicts = []
    clear = []
    
    for filepath in files:
        normalized_path = _normalize_path(filepath, base_dir)
        
        if normalized_path in registry["claims"]:
            claim = registry["claims"][normalized_path]
            if claim["claimed_by"] != agent_id:
                conflicts.append({
                    "file": normalized_path,
                    "claimed_by": claim["claimed_by"],
                    "task_id": claim.get("task_id")
                })
            else:
                clear.append({"file": normalized_path, "status": "self_claimed"})
        else:
            clear.append({"file": normalized_path, "status": "available"})
    
    return {
        "has_conflicts": len(conflicts) > 0,
        "conflicts": conflicts,
        "clear": clear
    }


def expire_stale_claims(max_age_hours: int = 24,
                        base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """
    Auto-release claims older than max_age_hours.
    
    Args:
        max_age_hours: Maximum age in hours before a claim is considered stale
        base_dir: Base directory for the WIP registry
    
    Returns:
        Dict with 'expired_count' and 'expired_files'
    """
    registry = _load_registry(base_dir)
    now = datetime.utcnow()
    expired = []
    
    for filepath, claim in list(registry["claims"].items()):
        try:
            claimed_at = datetime.fromisoformat(claim["claimed_at"])
            age = now - claimed_at
            if age > timedelta(hours=max_age_hours):
                del registry["claims"][filepath]
                expired.append({
                    "file": filepath,
                    "claimed_by": claim["claimed_by"],
                    "age_hours": age.total_seconds() / 3600
                })
        except (KeyError, ValueError):
            # Malformed claim, remove it
            del registry["claims"][filepath]
            expired.append({"file": filepath, "error": "malformed"})
    
    if expired:
        _save_registry(registry, base_dir)
    
    return {
        "expired_count": len(expired),
        "expired_files": expired
    }


# CLI Interface

def main():
    parser = argparse.ArgumentParser(
        description="AVCPM Work-in-Progress Tracking"
    )
    parser.add_argument(
        "--base-dir",
        default=DEFAULT_BASE_DIR,
        help="Base directory for WIP registry (default: current directory)"
    )
    parser.add_argument(
        "--agent",
        default=os.environ.get("AVCPM_AGENT_ID", "unknown"),
        help="Agent ID (default: env AVCPM_AGENT_ID or 'unknown')"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Claim command
    claim_parser = subparsers.add_parser("claim", help="Claim a file")
    claim_parser.add_argument("file", help="File to claim")
    claim_parser.add_argument("--task", help="Task ID associated with claim")
    
    # Release command
    release_parser = subparsers.add_parser("release", help="Release a claim")
    release_parser.add_argument("file", help="File to release")
    
    # Release-all command
    subparsers.add_parser("release-all", help="Release all claims")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List claims")
    list_parser.add_argument("--mine", action="store_true", help="Show only my claims")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check files for conflicts")
    check_parser.add_argument("files", nargs="+", help="Files to check")
    
    # Expire command
    expire_parser = subparsers.add_parser("expire", help="Expire stale claims")
    expire_parser.add_argument("--max-age", type=int, default=24,
                               help="Max age in hours (default: 24)")
    
    args = parser.parse_args()
    
    # Auto-expire stale claims on every command
    expire_stale_claims(base_dir=args.base_dir)
    
    if args.command == "claim":
        result = claim_file(args.file, args.agent, args.task, args.base_dir)
        if result["success"]:
            claim = result["claim"]
            print(f"✓ Claimed: {claim['file']}")
            print(f"  Agent: {claim['claimed_by']}")
            if claim.get('task_id'):
                print(f"  Task: {claim['task_id']}")
            print(f"  Expires: {claim['expires_at']}")
        else:
            print(f"✗ Failed: {result['message']}")
            sys.exit(1)
    
    elif args.command == "release":
        result = release_file(args.file, args.agent, args.base_dir)
        if result["success"]:
            print(f"✓ Released: {args.file}")
        else:
            print(f"✗ Failed: {result['message']}")
            sys.exit(1)
    
    elif args.command == "release-all":
        result = release_all(args.agent, args.base_dir)
        print(f"✓ {result['message']}")
        for f in result["released_files"]:
            print(f"  - {f}")
    
    elif args.command == "list":
        if args.mine:
            result = list_my_claims(args.agent, args.base_dir)
            print(f"My claims ({result['count']}):")
        else:
            result = list_claims(args.base_dir)
            print(f"All claims ({result['count']}):")
        
        for claim in result["claims"]:
            print(f"\n  {claim['file']}")
            print(f"    Agent: {claim['claimed_by']}")
            if claim.get('task_id'):
                print(f"    Task: {claim['task_id']}")
            print(f"    Since: {claim['claimed_at']}")
            print(f"    Expires: {claim['expires_at']}")
    
    elif args.command == "check":
        result = check_wip_conflicts(args.files, args.agent, args.base_dir)
        
        if result["has_conflicts"]:
            print(f"⚠ Conflicts found ({len(result['conflicts'])}):")
            for c in result["conflicts"]:
                print(f"  ✗ {c['file']} - claimed by {c['claimed_by']}")
            print(f"\n✓ Clear files ({len(result['clear'])}):")
            for c in result["clear"]:
                print(f"  ✓ {c['file']}")
            sys.exit(1)
        else:
            print(f"✓ All {len(result['clear'])} file(s) clear")
            for c in result["clear"]:
                print(f"  ✓ {c['file']}")
    
    elif args.command == "expire":
        result = expire_stale_claims(args.max_age, args.base_dir)
        if result["expired_count"] > 0:
            print(f"✓ Expired {result['expired_count']} stale claim(s):")
            for e in result["expired_files"]:
                print(f"  - {e['file']} ({e.get('age_hours', 'N/A'):.1f} hours old)")
        else:
            print("✓ No stale claims found")


if __name__ == "__main__":
    main()
