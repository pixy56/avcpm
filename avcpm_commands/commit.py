"""Commit command handler."""
import sys


def commit_command(args):
    """Route commit commands."""
    from avcpm_commit import commit

    base_dir = _get_base_dir(args)

    if not args.task_id or not args.agent_id or not args.rationale:
        print("Error: commit requires task_id, agent_id, and rationale")
        sys.exit(1)

    if not args.files:
        print("Error: commit requires at least one file")
        sys.exit(1)

    skip_validation = getattr(args, 'skip_validation', False)
    try:
        commit(args.task_id, args.agent_id, args.rationale, args.files, None, base_dir, skip_validation)
    except (ValueError, PermissionError) as e:
        print(f"Error: {e}")
        sys.exit(1)


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"