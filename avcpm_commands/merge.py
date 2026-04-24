"""Merge command handler."""
import sys


def merge_command(args):
    """Route merge commands."""
    from avcpm_merge import merge

    base_dir = _get_base_dir(args)

    if not args.commit_id:
        print("Error: merge requires commit_id")
        sys.exit(1)

    auto_resolve = getattr(args, 'auto_resolve', False)
    try:
        merge(args.commit_id, args.source_branch, args.target_branch, base_dir, auto_resolve, args.agent_id)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"