"""Branch command handler."""
import sys


def branch_command(args):
    """Route branch commands."""
    from avcpm_branch import (
        create_branch, list_branches, get_current_branch,
        switch_branch, delete_branch, rename_branch
    )

    subcommand = args.subcommand
    base_dir = _get_base_dir(args)

    if subcommand == "create":
        if not args.branch_name:
            print("Error: branch create requires branch_name")
            sys.exit(1)
        parent = getattr(args, 'parent', None) or "main"
        task_id = getattr(args, 'task_id', None)
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
        force = getattr(args, 'force', False)
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


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"