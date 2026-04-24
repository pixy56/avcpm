"""Conflict command handler."""
import sys


def conflict_command(args):
    """Route conflict commands."""
    from avcpm_conflict import (
        detect_conflicts, get_conflicts, resolve_conflict,
        auto_merge_possible
    )

    subcommand = args.subcommand
    base_dir = _get_base_dir(args)

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
        status = getattr(args, 'status', "open")
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
        strategy = getattr(args, 'strategy', None)
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


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"