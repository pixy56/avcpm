"""Diff command handler."""
import sys


def diff_command(args):
    """Route diff commands."""
    from avcpm_diff import (
        diff_commits, show_commit, log, blame,
        format_diff_side_by_side, format_blame_output
    )

    subcommand = args.subcommand
    base_dir = _get_base_dir(args)

    if subcommand == "diff":
        if not args.commit_a or not args.commit_b:
            print("Error: diff requires commit_a and commit_b")
            sys.exit(1)
        try:
            result = diff_commits(args.commit_a, args.commit_b, base_dir)
            side_by_side = getattr(args, 'side_by_side', False)
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
        branch = getattr(args, 'branch', None)
        limit = getattr(args, 'limit', 10)
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
                show_timestamps = getattr(args, 'timestamps', False)
                print(format_blame_output(result, show_timestamps))
            else:
                print(f"No history found for {args.file}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    else:
        print(f"Unknown diff subcommand: {subcommand}")
        sys.exit(1)


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"