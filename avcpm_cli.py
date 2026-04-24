#!/usr/bin/env python3
"""
AVCPM Unified CLI - Single entry point for all AVCPM commands.

Usage:
    python avcpm_cli.py <command> [args...]
    python -m avcpm_cli <command>

Commands:
    task       Task management (create, move, list, deps)
    commit     Commit files to ledger
    merge      Merge commits between branches
    branch     Branch management (create, switch, list, delete)
    diff       Diff and history (diff, show, log, blame)
    conflict   Conflict detection and resolution
    rollback   Rollback and recovery operations
    wip        Work-in-progress tracking
    status     Status dashboard
    validate   Checksum validation
    agent      Agent identity management

Global Options:
    --base-dir <path>   Override base directory
    --config <file>     Config file path
    --verbose           Enable debug output
    --version           Show AVCPM version

Examples:
    avcpm task list
    avcpm branch create feature-x
    avcpm status --json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any

# AVCPM version
__version__ = "3.0.0"

# Import all AVCPM modules
from avcpm_task import (
    create_task, move_task, list_tasks, list_blocked,
    deps_add, deps_remove, deps_show, deps_dependents
)
from avcpm_commit import commit
from avcpm_merge import merge
from avcpm_branch import (
    create_branch, list_branches, get_current_branch,
    switch_branch, delete_branch, rename_branch
)
from avcpm_diff import (
    diff_commits, show_commit, log, blame, file_history,
    format_diff_side_by_side, format_blame_output
)
from avcpm_conflict import (
    detect_conflicts, get_conflicts, resolve_conflict,
    auto_merge_possible, CONFLICT_STATUS_OPEN
)
from avcpm_rollback import (
    rollback, unstage, restore_file, reset_soft, reset_hard,
    create_backup, list_backups, restore_backup, delete_backup
)
from avcpm_wip import (
    claim_file, release_file, release_all, list_claims,
    list_my_claims, check_wip_conflicts, expire_stale_claims
)
from avcpm_status import main as status_main
from avcpm_validate import validate_checksums, fix_mismatches, print_report
from avcpm_agent import create_agent, list_agents, get_agent


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

DEFAULT_CONFIG_FILES = [".avcpmrc", ".avcpm/config.json"]


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file(s)."""
    config = {}
    
    # Load from default locations if no specific config provided
    if config_path is None:
        for default_path in DEFAULT_CONFIG_FILES:
            if os.path.exists(default_path):
                try:
                    with open(default_path, 'r') as f:
                        config.update(json.load(f))
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not load config from {default_path}: {e}")
    elif os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config.update(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    return config


def get_base_dir(args) -> str:
    """Get base directory from args or config."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"


# ============================================================================
# COMMAND ROUTERS
# ============================================================================

def task_command(args):
    """Route task commands."""
    subcommand = args.subcommand
    base_dir = get_base_dir(args)
    
    if subcommand == "create":
        if not args.task_id or not args.description:
            print("Error: task create requires task_id and description")
            sys.exit(1)
        assignee = args.assignee if hasattr(args, 'assignee') and args.assignee else "unassigned"
        depends_on = args.depends_on if hasattr(args, 'depends_on') and args.depends_on else None
        try:
            create_task(args.task_id, args.description, assignee, depends_on, base_dir)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "move":
        if not args.task_id or not args.status:
            print("Error: task move requires task_id and status")
            sys.exit(1)
        force = args.force if hasattr(args, 'force') else False
        try:
            move_task(args.task_id, args.status, force, base_dir)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "list":
        list_tasks(base_dir)
    
    elif subcommand == "blocked":
        list_blocked(base_dir)
    
    elif subcommand == "deps":
        deps_subcommand = args.deps_subcommand
        if deps_subcommand == "add":
            if not args.task_id or not args.dep_task_id:
                print("Error: deps add requires task_id and dep_task_id")
                sys.exit(1)
            try:
                deps_add(args.task_id, args.dep_task_id, base_dir)
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)
        elif deps_subcommand == "remove":
            if not args.task_id or not args.dep_task_id:
                print("Error: deps remove requires task_id and dep_task_id")
                sys.exit(1)
            try:
                deps_remove(args.task_id, args.dep_task_id, base_dir)
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)
        elif deps_subcommand == "show":
            if not args.task_id:
                print("Error: deps show requires task_id")
                sys.exit(1)
            deps_show(args.task_id, base_dir)
        elif deps_subcommand == "dependents":
            if not args.task_id:
                print("Error: deps dependents requires task_id")
                sys.exit(1)
            deps_dependents(args.task_id, base_dir)
        else:
            print(f"Unknown deps subcommand: {deps_subcommand}")
            sys.exit(1)
    
    else:
        print(f"Unknown task subcommand: {subcommand}")
        sys.exit(1)


def commit_command(args):
    """Route commit commands."""
    base_dir = get_base_dir(args)
    
    if not args.task_id or not args.agent_id or not args.rationale:
        print("Error: commit requires task_id, agent_id, and rationale")
        sys.exit(1)
    
    if not args.files:
        print("Error: commit requires at least one file")
        sys.exit(1)
    
    skip_validation = args.skip_validation if hasattr(args, 'skip_validation') else False
    try:
        commit(args.task_id, args.agent_id, args.rationale, args.files, None, base_dir, skip_validation)
    except (ValueError, PermissionError) as e:
        print(f"Error: {e}")
        sys.exit(1)


def merge_command(args):
    """Route merge commands."""
    base_dir = get_base_dir(args)
    
    if not args.commit_id:
        print("Error: merge requires commit_id")
        sys.exit(1)
    
    auto_resolve = args.auto_resolve if hasattr(args, 'auto_resolve') else False
    try:
        merge(args.commit_id, args.source_branch, args.target_branch, base_dir, auto_resolve, args.agent_id)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def branch_command(args):
    """Route branch commands."""
    subcommand = args.subcommand
    base_dir = get_base_dir(args)
    
    if subcommand == "create":
        if not args.branch_name:
            print("Error: branch create requires branch_name")
            sys.exit(1)
        parent = args.parent if hasattr(args, 'parent') and args.parent else "main"
        task_id = args.task_id if hasattr(args, 'task_id') and args.task_id else None
        try:
            metadata = create_branch(args.branch_name, parent, task_id, None, base_dir)
            print(f"Created branch '{args.branch_name}' from '{parent}'")
            print(f"  Branch ID: {metadata['branch_id']}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "list":
        branches = list_branches(base_dir)
        current = get_current_branch(base_dir)
        print(f"{'*' if current else ' '} {'Branch Name':<20} {'Status':<10} {'Parent':<15} {'Created At'}")
        print("-" * 70)
        for branch in branches:
            marker = "*" if branch["name"] == current else " "
            status = branch.get("status", "unknown")
            parent = branch.get("parent_branch") or "-"
            created = branch.get("created_at", "unknown")[:19]
            print(f"{marker} {branch['name']:<20} {status:<10} {parent:<15} {created}")
    
    elif subcommand == "switch":
        if not args.branch_name:
            print("Error: branch switch requires branch_name")
            sys.exit(1)
        try:
            switch_branch(args.branch_name, base_dir)
            print(f"Switched to branch '{args.branch_name}'")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "delete":
        if not args.branch_name:
            print("Error: branch delete requires branch_name")
            sys.exit(1)
        force = args.force if hasattr(args, 'force') else False
        try:
            delete_branch(args.branch_name, force, base_dir)
            print(f"Deleted branch '{args.branch_name}'")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "rename":
        if not args.old_name or not args.new_name:
            print("Error: branch rename requires old_name and new_name")
            sys.exit(1)
        try:
            rename_branch(args.old_name, args.new_name, base_dir)
            print(f"Renamed branch '{args.old_name}' to '{args.new_name}'")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "current":
        current = get_current_branch(base_dir)
        print(current)
    
    else:
        print(f"Unknown branch subcommand: {subcommand}")
        sys.exit(1)


def diff_command(args):
    """Route diff commands."""
    subcommand = args.subcommand
    base_dir = get_base_dir(args)
    
    if subcommand == "diff":
        if not args.commit_a or not args.commit_b:
            print("Error: diff requires commit_a and commit_b")
            sys.exit(1)
        try:
            result = diff_commits(args.commit_a, args.commit_b, base_dir)
            side_by_side = args.side_by_side if hasattr(args, 'side_by_side') else False
            if side_by_side:
                print(format_diff_side_by_side(result["diff"]))
            else:
                print(result["diff"])
                print()
                print(f"Files changed: {result['stats']['files_changed']}")
                print(f"Insertions: {result['stats']['insertions']}")
                print(f"Deletions: {result['stats']['deletions']}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "show":
        if not args.commit_id:
            print("Error: show requires commit_id")
            sys.exit(1)
        try:
            result = show_commit(args.commit_id, base_dir)
            print(f"commit {result['commit_id']}")
            print(f"Author: {result['agent_id']}")
            print(f"Date: {result['timestamp']}")
            if result.get('branch'):
                print(f"Branch: {result['branch']}")
            if result.get('parent_commit'):
                print(f"Parent: {result['parent_commit']}")
            print(f"Task: {result['task_id']}")
            print(f"Signature: {result.get('signature', 'N/A')}")
            print()
            print(f"    {result['rationale']}")
            print()
            print("Changes:")
            for change in result.get("changes", []):
                print(f"    {change.get('file')}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "log":
        branch = args.branch if hasattr(args, 'branch') else None
        limit = args.limit if hasattr(args, 'limit') else 10
        commits = log(branch, limit, base_dir)
        if commits:
            print(f"{'Commit ID':<18} {'Timestamp':<20} {'Agent':<15} {'Task':<15} {'Changes':<8} {'Rationale'}")
            print("-" * 100)
            for commit_entry in commits:
                ts = commit_entry.get("timestamp", "unknown")[:19]
                agent = commit_entry.get("agent_id", "unknown")[:14]
                task = commit_entry.get("task_id", "-")[:14]
                changes = str(commit_entry.get("changes_count", 0))
                rationale = commit_entry.get("rationale", "-")[:40]
                print(f"{commit_entry['commit_id']:<18} {ts:<20} {agent:<15} {task:<15} {changes:<8} {rationale}")
        else:
            print(f"No commits found" + (f" in branch '{branch}'" if branch else ""))
    
    elif subcommand == "blame":
        if not args.file:
            print("Error: blame requires file path")
            sys.exit(1)
        try:
            result = blame(args.file, base_dir)
            if result:
                show_timestamps = args.timestamps if hasattr(args, 'timestamps') else False
                print(format_blame_output(result, show_timestamps))
            else:
                print(f"No history found for {args.file}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown diff subcommand: {subcommand}")
        sys.exit(1)


def conflict_command(args):
    """Route conflict commands."""
    subcommand = args.subcommand
    base_dir = get_base_dir(args)
    
    if subcommand == "detect":
        if not args.branch_a or not args.branch_b:
            print("Error: conflict detect requires branch_a and branch_b")
            sys.exit(1)
        try:
            result = detect_conflicts(args.branch_a, args.branch_b, base_dir)
            if result["conflict_count"] == 0:
                print(f"No conflicts detected between '{args.branch_a}' and '{args.branch_b}'")
                print(f"Base commit: {result['base_commit'] or 'none'}")
                print("Auto-merge is safe.")
            else:
                print(f"Detected {result['conflict_count']} conflict(s):")
                for conflict in result["conflicts"]:
                    print(f"  Conflict ID: {conflict['conflict_id']}")
                    print(f"  File: {conflict['file']}")
                    print(f"  Type: {conflict['conflict_type']}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "list":
        status = args.status if hasattr(args, 'status') else "open"
        conflicts = get_conflicts(status, base_dir)
        if not conflicts:
            print(f"No {status} conflicts found.")
        else:
            print(f"{'Conflict ID':<30} {'Status':<10} {'Type':<15} {'File'}")
            print("-" * 100)
            for conflict in conflicts:
                cid = conflict.get("conflict_id", "unknown")
                cstatus = conflict.get("status", "unknown")
                ctype = conflict.get("conflict_type", "unknown")
                file_path = conflict.get("file", "unknown")
                if len(file_path) > 40:
                    file_path = "..." + file_path[-37:]
                print(f"{cid:<30} {cstatus:<10} {ctype:<15} {file_path}")
    
    elif subcommand == "resolve":
        if not args.conflict_id:
            print("Error: conflict resolve requires conflict_id")
            sys.exit(1)
        strategy = args.strategy if hasattr(args, 'strategy') else None
        if not strategy:
            print("Error: --strategy is required (ours|theirs|union|manual)")
            sys.exit(1)
        try:
            result = resolve_conflict(args.conflict_id, strategy, base_dir)
            print(f"Resolved conflict '{args.conflict_id}' using '{strategy}' strategy")
            print(f"File: {result['file']}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif subcommand == "check":
        if not args.branch_a or not args.branch_b:
            print("Error: conflict check requires branch_a and branch_b")
            sys.exit(1)
        try:
            is_safe = auto_merge_possible(args.branch_a, args.branch_b, base_dir)
            if is_safe:
                print(f"Auto-merge is SAFE between '{args.branch_a}' and '{args.branch_b}'")
            else:
                print(f"Auto-merge is NOT SAFE between '{args.branch_a}' and '{args.branch_b}'")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown conflict subcommand: {subcommand}")
        sys.exit(1)


def rollback_command(args):
    """Route rollback commands."""
    base_dir = get_base_dir(args)
    
    if args.subcommand == "rollback":
        if not args.commit_id:
            print("Error: rollback requires commit_id")
            sys.exit(1)
        dry_run = args.dry_run if hasattr(args, 'dry_run') else False
        result = rollback(args.commit_id, base_dir, dry_run)
        if result["success"]:
            print(f"Successfully rolled back commit {result['commit_id']}")
            if result.get("backup_id"):
                print(f"  Auto-backup created: {result['backup_id']}")
            print(f"  Files restored: {len(result.get('files_restored', []))}")
        else:
            print(f"Rollback failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    elif args.subcommand == "restore":
        if not args.file:
            print("Error: restore requires file path")
            sys.exit(1)
        commit_id = args.commit_id if hasattr(args, 'commit_id') else None
        result = restore_file(args.file, commit_id, base_dir)
        if result["success"]:
            print(f"Successfully restored {result['filepath']} from commit {result['commit_id']}")
        else:
            print(f"Restore failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    elif args.subcommand == "reset":
        if not args.commit_id:
            print("Error: reset requires commit_id")
            sys.exit(1)
        hard = args.hard if hasattr(args, 'hard') else False
        branch_name = args.branch if hasattr(args, 'branch') else None
        if hard:
            result = reset_hard(args.commit_id, branch_name, base_dir)
        else:
            result = reset_soft(args.commit_id, branch_name, base_dir)
        if result["success"]:
            print(f"Successfully reset branch '{result['branch']}' to commit {result['target_commit']}")
            if result.get("backup_id"):
                print(f"  Auto-backup created: {result['backup_id']}")
        else:
            print(f"Reset failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    elif args.subcommand == "unstage":
        if not args.commit_id:
            print("Error: unstage requires commit_id")
            sys.exit(1)
        branch_name = args.branch if hasattr(args, 'branch') else None
        result = unstage(args.commit_id, branch_name, base_dir)
        if result["success"]:
            print(f"Successfully unstaged commit {result['commit_id']}")
            print(f"  Files removed from staging: {len(result.get('files_removed', []))}")
        else:
            print(f"Unstage failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    
    elif args.subcommand == "backup":
        backup_subcommand = args.backup_subcommand
        
        if backup_subcommand == "create":
            name = args.name if hasattr(args, 'name') else None
            backup_id = create_backup(name, base_dir)
            print(f"Backup created: {backup_id}")
        
        elif backup_subcommand == "list":
            backups = list_backups(base_dir)
            if not backups:
                print("No backups found.")
            else:
                print(f"{'Backup ID':<40} {'Name':<30} {'Created':<20} {'Status'}")
                print("-" * 100)
                for backup in backups:
                    backup_id = backup.get("backup_id", "N/A")[:38]
                    name = backup.get("name", "N/A")[:28]
                    created = backup.get("created_at", "N/A")[:19]
                    status = backup.get("status", "unknown")
                    print(f"{backup_id:<40} {name:<30} {created:<20} {status}")
        
        elif backup_subcommand == "restore":
            if not args.backup_id:
                print("Error: backup restore requires backup_id")
                sys.exit(1)
            result = restore_backup(args.backup_id, base_dir)
            if result["success"]:
                print(f"Successfully restored from backup {result['backup_id']}")
                print(f"  Branches restored: {', '.join(result['branches_restored'])}")
            else:
                print(f"Restore failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        elif backup_subcommand == "delete":
            if not args.backup_id:
                print("Error: backup delete requires backup_id")
                sys.exit(1)
            result = delete_backup(args.backup_id, base_dir)
            if result["success"]:
                print(f"Backup {args.backup_id} deleted")
            else:
                print(f"Delete failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        else:
            print(f"Unknown backup subcommand: {backup_subcommand}")
            sys.exit(1)
    
    else:
        print(f"Unknown rollback subcommand: {args.subcommand}")
        sys.exit(1)


def wip_command(args):
    """Route wip commands."""
    base_dir = get_base_dir(args)
    agent_id = args.agent if hasattr(args, 'agent') else os.environ.get("AVCPM_AGENT_ID", "unknown")
    
    # Auto-expire stale claims
    expire_stale_claims(base_dir=base_dir)
    
    if args.subcommand == "claim":
        if not args.file:
            print("Error: wip claim requires file path")
            sys.exit(1)
        task_id = args.task if hasattr(args, 'task') else None
        result = claim_file(args.file, agent_id, task_id, base_dir)
        if result["success"]:
            print(f"Claimed: {result['claim']['file']}")
            print(f"  Agent: {result['claim']['claimed_by']}")
            print(f"  Expires: {result['claim']['expires_at']}")
        else:
            print(f"Failed: {result['message']}")
            sys.exit(1)
    
    elif args.subcommand == "release":
        if not args.file:
            print("Error: wip release requires file path")
            sys.exit(1)
        result = release_file(args.file, agent_id, base_dir)
        if result["success"]:
            print(f"Released: {args.file}")
        else:
            print(f"Failed: {result['message']}")
            sys.exit(1)
    
    elif args.subcommand == "release-all":
        result = release_all(agent_id, base_dir)
        print(f"Released {result['released_count']} claim(s)")
        for f in result["released_files"]:
            print(f"  - {f}")
    
    elif args.subcommand == "list":
        mine = args.mine if hasattr(args, 'mine') else False
        if mine:
            result = list_my_claims(agent_id, base_dir)
            print(f"My claims ({result['count']}):")
        else:
            result = list_claims(base_dir)
            print(f"All claims ({result['count']}):")
        
        for claim in result["claims"]:
            print(f"\n  {claim['file']}")
            print(f"    Agent: {claim['claimed_by']}")
            if claim.get('task_id'):
                print(f"    Task: {claim['task_id']}")
            print(f"    Expires: {claim['expires_at']}")
    
    elif args.subcommand == "check":
        if not args.files:
            print("Error: wip check requires file paths")
            sys.exit(1)
        result = check_wip_conflicts(args.files, agent_id, base_dir)
        if result["has_conflicts"]:
            print(f"Conflicts found ({len(result['conflicts'])}):")
            for c in result["conflicts"]:
                print(f"  {c['file']} - claimed by {c['claimed_by']}")
            sys.exit(1)
        else:
            print(f"All {len(result['clear'])} file(s) clear")
    
    else:
        print(f"Unknown wip subcommand: {args.subcommand}")
        sys.exit(1)


def agent_command(args):
    """Route agent commands."""
    import getpass as _getpass
    import warnings as _warnings
    
    base_dir = get_base_dir(args)
    
    if args.subcommand == "create":
        if not args.name or not args.email:
            print("Error: agent create requires name and email")
            sys.exit(1)
        
        encrypt = not getattr(args, 'no_encrypt', False)
        passphrase = None
        
        if encrypt:
            # Check --passphrase arg, then env var, then prompt
            passphrase = getattr(args, 'passphrase', None)
            if not passphrase:
                passphrase = os.environ.get("AVCPM_KEY_PASSPHRASE")
            if not passphrase:
                passphrase = _getpass.getpass("Enter passphrase for private key encryption: ")
                confirm = _getpass.getpass("Confirm passphrase: ")
                if passphrase != confirm:
                    print("Error: Passphrases do not match")
                    sys.exit(1)
            if len(passphrase) < 8:
                print("Error: Passphrase must be at least 8 characters")
                sys.exit(1)
        else:
            _warnings.warn(
                "Private key will be stored unencrypted. This is NOT recommended "
                "for production use. Anyone with filesystem access can read the key.",
                UserWarning,
                stacklevel=2,
            )
        
        try:
            agent = create_agent(args.name, args.email, base_dir, passphrase=passphrase, encrypt=encrypt)
            print(f"Agent created successfully!")
            print(f"  ID: {agent['agent_id']}")
            print(f"  Name: {agent['name']}")
            print(f"  Email: {agent['email']}")
            if encrypt:
                print(f"  Encryption: Enabled (AES-256-GCM)")
            else:
                print(f"  Encryption: DISABLED (private key stored unencrypted)")
        except Exception as e:
            print(f"Error creating agent: {e}")
            sys.exit(1)
    
    elif args.subcommand == "list":
        agents = list_agents(base_dir)
        if not agents:
            print("No agents registered.")
        else:
            print("Registered Agents:")
            print("-" * 60)
            for agent_id, info in agents.items():
                print(f"  ID: {agent_id}")
                print(f"  Name: {info.get('name', 'N/A')}")
                print(f"  Email: {info.get('email', 'N/A')}")
                print("-" * 60)
    
    elif args.subcommand == "show":
        if not args.agent_id:
            print("Error: agent show requires agent_id")
            sys.exit(1)
        agent = get_agent(args.agent_id, base_dir)
        if agent:
            print(f"Agent: {agent['name']}")
            print(f"  ID: {agent['agent_id']}")
            print(f"  Email: {agent['email']}")
            print(f"  Created: {agent['created_at']}")
        else:
            print(f"Agent {args.agent_id} not found.")
            sys.exit(1)
    
    else:
        print(f"Unknown agent subcommand: {args.subcommand}")
        sys.exit(1)


def validate_command(args):
    """Route validate commands."""
    base_dir = get_base_dir(args)
    staging_dir = os.path.join(base_dir, "staging")
    ledger_dir = os.path.join(base_dir, "ledger")
    
    if hasattr(args, 'staging_dir') and args.staging_dir:
        staging_dir = args.staging_dir
    if hasattr(args, 'ledger_dir') and args.ledger_dir:
        ledger_dir = args.ledger_dir
    
    report = validate_checksums(staging_dir, ledger_dir)
    
    if args.fix if hasattr(args, 'fix') else False:
        if report.failed > 0:
            print("Applying fixes for mismatched checksums...")
            fixes = fix_mismatches(report, ledger_dir)
            print(f"Fixed {fixes} checksum(s)")
            report = validate_checksums(staging_dir, ledger_dir)
    
    print_report(report)
    
    if not report.success:
        sys.exit(1)


def status_command(args):
    """Route status command to avcpm_status module with direct parameter passing."""
    base_dir = get_base_dir(args)
    try:
        status_main(base_dir=base_dir, json_output=args.json, tasks_only=args.tasks,
                    ledger_only=args.ledger, staging_only=args.staging, health_only=args.health)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# ============================================================================
# MAIN PARSER SETUP
# ============================================================================

def create_parser():
    """Create the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="avcpm",
        description="AVCPM Unified CLI - Single entry point for all AVCPM commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    avcpm task list
    avcpm task create TASK-001 "Implement feature"
    avcpm branch create feature-x
    avcpm commit TASK-001 agent-1 "Initial commit" file.py
    avcpm status
    avcpm --version
        """
    )
    
    # Global options
    parser.add_argument(
        "--base-dir",
        default=".avcpm",
        help="Override base directory (default: .avcpm)"
    )
    parser.add_argument(
        "--config",
        help="Config file path"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"AVCPM {__version__}"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # ========================================================================
    # task command
    # ========================================================================
    task_parser = subparsers.add_parser(
        "task",
        help="Task management (create, move, list, deps)"
    )
    task_subparsers = task_parser.add_subparsers(dest="subcommand")
    
    # task create
    task_create = task_subparsers.add_parser("create", help="Create a new task")
    task_create.add_argument("task_id", help="Task ID")
    task_create.add_argument("description", help="Task description")
    task_create.add_argument("--assignee", default="unassigned", help="Task assignee")
    task_create.add_argument("--depends-on", help="Comma-separated dependency task IDs")
    
    # task move
    task_move = task_subparsers.add_parser("move", help="Move task to new status")
    task_move.add_argument("task_id", help="Task ID")
    task_move.add_argument("status", choices=["todo", "in-progress", "review", "done"], help="New status")
    task_move.add_argument("--force", action="store_true", help="Bypass dependency checks")
    
    # task list
    task_subparsers.add_parser("list", help="List all tasks")
    
    # task blocked
    task_subparsers.add_parser("blocked", help="List blocked tasks")
    
    # task deps
    task_deps = task_subparsers.add_parser("deps", help="Dependency management")
    task_deps_subparsers = task_deps.add_subparsers(dest="deps_subcommand")
    
    deps_add = task_deps_subparsers.add_parser("add", help="Add dependency")
    deps_add.add_argument("task_id", help="Task ID")
    deps_add.add_argument("dep_task_id", help="Dependency task ID")
    
    deps_remove = task_deps_subparsers.add_parser("remove", help="Remove dependency")
    deps_remove.add_argument("task_id", help="Task ID")
    deps_remove.add_argument("dep_task_id", help="Dependency task ID")
    
    deps_show = task_deps_subparsers.add_parser("show", help="Show dependency tree")
    deps_show.add_argument("task_id", help="Task ID")
    
    deps_dependents = task_deps_subparsers.add_parser("dependents", help="Show tasks depending on this")
    deps_dependents.add_argument("task_id", help="Task ID")
    
    # ========================================================================
    # commit command
    # ========================================================================
    commit_parser = subparsers.add_parser(
        "commit",
        help="Commit files to ledger"
    )
    commit_parser.add_argument("task_id", help="Task ID")
    commit_parser.add_argument("agent_id", help="Agent ID")
    commit_parser.add_argument("rationale", help="Commit message")
    commit_parser.add_argument("files", nargs="+", help="Files to commit")
    commit_parser.add_argument("--skip-validation", action="store_true", help="Skip validation")
    
    # ========================================================================
    # merge command
    # ========================================================================
    merge_parser = subparsers.add_parser(
        "merge",
        help="Merge commits between branches"
    )
    merge_parser.add_argument("commit_id", help="Commit ID to merge")
    merge_parser.add_argument("--source-branch", help="Source branch (default: current)")
    merge_parser.add_argument("--target-branch", help="Target branch (default: current)")
    merge_parser.add_argument("--auto-resolve", action="store_true", help="Auto-resolve conflicts")
    merge_parser.add_argument("--agent-id", help="Agent performing merge")
    
    # ========================================================================
    # branch command
    # ========================================================================
    branch_parser = subparsers.add_parser(
        "branch",
        help="Branch management (create, switch, list, delete)"
    )
    branch_subparsers = branch_parser.add_subparsers(dest="subcommand")
    
    # branch create
    branch_create = branch_subparsers.add_parser("create", help="Create new branch")
    branch_create.add_argument("branch_name", help="Branch name")
    branch_create.add_argument("--parent", default="main", help="Parent branch")
    branch_create.add_argument("--task-id", help="Associated task ID")
    
    # branch list
    branch_subparsers.add_parser("list", help="List branches")
    
    # branch switch
    branch_switch = branch_subparsers.add_parser("switch", help="Switch to branch")
    branch_switch.add_argument("branch_name", help="Branch name")
    
    # branch delete
    branch_delete = branch_subparsers.add_parser("delete", help="Delete branch")
    branch_delete.add_argument("branch_name", help="Branch name")
    branch_delete.add_argument("--force", action="store_true", help="Force delete")
    
    # branch rename
    branch_rename = branch_subparsers.add_parser("rename", help="Rename branch")
    branch_rename.add_argument("old_name", help="Current name")
    branch_rename.add_argument("new_name", help="New name")
    
    # branch current
    branch_subparsers.add_parser("current", help="Show current branch")
    
    # ========================================================================
    # diff command
    # ========================================================================
    diff_parser = subparsers.add_parser(
        "diff",
        help="Diff and history (diff, show, log, blame)"
    )
    diff_subparsers = diff_parser.add_subparsers(dest="subcommand")
    
    # diff diff
    diff_diff = diff_subparsers.add_parser("diff", help="Compare two commits")
    diff_diff.add_argument("commit_a", help="First commit ID")
    diff_diff.add_argument("commit_b", help="Second commit ID")
    diff_diff.add_argument("--side-by-side", action="store_true", help="Show side-by-side diff")
    
    # diff show
    diff_show = diff_subparsers.add_parser("show", help="Show commit details")
    diff_show.add_argument("commit_id", help="Commit ID")
    
    # diff log
    diff_log = diff_subparsers.add_parser("log", help="Show commit log")
    diff_log.add_argument("--branch", help="Branch to show")
    diff_log.add_argument("--limit", type=int, default=10, help="Number of commits")
    
    # diff blame
    diff_blame = diff_subparsers.add_parser("blame", help="Show line authorship")
    diff_blame.add_argument("file", help="File path")
    diff_blame.add_argument("--timestamps", action="store_true", help="Show timestamps")
    
    # ========================================================================
    # conflict command
    # ========================================================================
    conflict_parser = subparsers.add_parser(
        "conflict",
        help="Conflict detection and resolution"
    )
    conflict_subparsers = conflict_parser.add_subparsers(dest="subcommand")
    
    # conflict detect
    conflict_detect = conflict_subparsers.add_parser("detect", help="Detect conflicts")
    conflict_detect.add_argument("branch_a", help="First branch")
    conflict_detect.add_argument("branch_b", help="Second branch")
    
    # conflict list
    conflict_list = conflict_subparsers.add_parser("list", help="List conflicts")
    conflict_list.add_argument("--status", default="open", choices=["open", "resolved", "aborted", "all"], help="Filter by status")
    
    # conflict resolve
    conflict_resolve = conflict_subparsers.add_parser("resolve", help="Resolve conflict")
    conflict_resolve.add_argument("conflict_id", help="Conflict ID")
    conflict_resolve.add_argument("--strategy", choices=["ours", "theirs", "union", "manual"], help="Resolution strategy")
    
    # conflict check
    conflict_check = conflict_subparsers.add_parser("check", help="Check if merge is safe")
    conflict_check.add_argument("branch_a", help="First branch")
    conflict_check.add_argument("branch_b", help="Second branch")
    
    # ========================================================================
    # rollback command
    # ========================================================================
    rollback_parser = subparsers.add_parser(
        "rollback",
        help="Rollback and recovery operations"
    )
    rollback_subparsers = rollback_parser.add_subparsers(dest="subcommand")
    
    # rollback rollback
    rb_rollback = rollback_subparsers.add_parser("rollback", help="Undo a merged commit")
    rb_rollback.add_argument("commit_id", help="Commit ID")
    rb_rollback.add_argument("--dry-run", action="store_true", help="Preview only")
    
    # rollback restore
    rb_restore = rollback_subparsers.add_parser("restore", help="Restore file to version")
    rb_restore.add_argument("file", help="File path")
    rb_restore.add_argument("--commit-id", help="Commit ID (default: latest)")
    
    # rollback reset
    rb_reset = rollback_subparsers.add_parser("reset", help="Reset branch to commit")
    rb_reset.add_argument("commit_id", help="Commit ID")
    rb_reset.add_argument("--hard", action="store_true", help="Hard reset (remove staging files)")
    rb_reset.add_argument("--branch", help="Branch to reset (default: current)")
    
    # rollback unstage
    rb_unstage = rollback_subparsers.add_parser("unstage", help="Remove commit from staging")
    rb_unstage.add_argument("commit_id", help="Commit ID")
    rb_unstage.add_argument("--branch", help="Branch (default: current)")
    
    # rollback backup
    rb_backup = rollback_subparsers.add_parser("backup", help="Backup management")
    rb_backup_subparsers = rb_backup.add_subparsers(dest="backup_subcommand")
    
    backup_create = rb_backup_subparsers.add_parser("create", help="Create backup")
    backup_create.add_argument("--name", help="Backup name")
    
    rb_backup_subparsers.add_parser("list", help="List backups")
    
    backup_restore = rb_backup_subparsers.add_parser("restore", help="Restore backup")
    backup_restore.add_argument("backup_id", help="Backup ID")
    
    backup_delete = rb_backup_subparsers.add_parser("delete", help="Delete backup")
    backup_delete.add_argument("backup_id", help="Backup ID")
    
    # ========================================================================
    # wip command
    # ========================================================================
    wip_parser = subparsers.add_parser(
        "wip",
        help="Work-in-progress tracking"
    )
    wip_subparsers = wip_parser.add_subparsers(dest="subcommand")
    
    # wip claim
    wip_claim = wip_subparsers.add_parser("claim", help="Claim a file")
    wip_claim.add_argument("file", help="File path")
    wip_claim.add_argument("--task", help="Task ID")
    wip_claim.add_argument("--agent", help="Agent ID (default: env AVCPM_AGENT_ID)")
    
    # wip release
    wip_release = wip_subparsers.add_parser("release", help="Release a claim")
    wip_release.add_argument("file", help="File path")
    wip_release.add_argument("--agent", help="Agent ID (default: env AVCPM_AGENT_ID)")
    
    # wip release-all
    wip_release_all = wip_subparsers.add_parser("release-all", help="Release all claims")
    wip_release_all.add_argument("--agent", help="Agent ID (default: env AVCPM_AGENT_ID)")
    
    # wip list
    wip_list = wip_subparsers.add_parser("list", help="List claims")
    wip_list.add_argument("--mine", action="store_true", help="Show only my claims")
    wip_list.add_argument("--agent", help="Agent ID (default: env AVCPM_AGENT_ID)")
    
    # wip check
    wip_check = wip_subparsers.add_parser("check", help="Check files for conflicts")
    wip_check.add_argument("files", nargs="+", help="Files to check")
    wip_check.add_argument("--agent", help="Agent ID (default: env AVCPM_AGENT_ID)")
    
    # ========================================================================
    # status command
    # ========================================================================
    status_parser = subparsers.add_parser(
        "status",
        help="Status dashboard"
    )
    status_parser.add_argument("--tasks", action="store_true", help="Show only tasks")
    status_parser.add_argument("--ledger", action="store_true", help="Show only ledger")
    status_parser.add_argument("--staging", action="store_true", help="Show only staging")
    status_parser.add_argument("--health", action="store_true", help="Show only health")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # ========================================================================
    # validate command
    # ========================================================================
    validate_parser = subparsers.add_parser(
        "validate",
        help="Checksum validation"
    )
    validate_parser.add_argument("--staging-dir", help="Staging directory")
    validate_parser.add_argument("--ledger-dir", help="Ledger directory")
    validate_parser.add_argument("--fix", action="store_true", help="Fix mismatches")
    
    # ========================================================================
    # agent command
    # ========================================================================
    agent_parser = subparsers.add_parser(
        "agent",
        help="Agent identity management"
    )
    agent_subparsers = agent_parser.add_subparsers(dest="subcommand")
    
    # agent create
    agent_create = agent_subparsers.add_parser("create", help="Create agent")
    agent_create.add_argument("name", help="Agent name")
    agent_create.add_argument("email", help="Agent email")
    agent_create.add_argument("--no-encrypt", action="store_true", help="Store private key unencrypted (NOT recommended)")
    agent_create.add_argument("--passphrase", help="Encryption passphrase (or set AVCPM_KEY_PASSPHRASE env var)")
    
    # agent list
    agent_subparsers.add_parser("list", help="List agents")
    
    # agent show
    agent_show = agent_subparsers.add_parser("show", help="Show agent details")
    agent_show.add_argument("agent_id", help="Agent ID")
    
    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Load config if available
    config = load_config(getattr(args, 'config', None))
    
    # Route to appropriate command handler
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    command_handlers = {
        "task": task_command,
        "commit": commit_command,
        "merge": merge_command,
        "branch": branch_command,
        "diff": diff_command,
        "conflict": conflict_command,
        "rollback": rollback_command,
        "wip": wip_command,
        "status": status_command,
        "validate": validate_command,
        "agent": agent_command,
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(130)
        except Exception as e:
            if args.verbose if hasattr(args, 'verbose') else False:
                import traceback
                traceback.print_exc()
            else:
                print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
