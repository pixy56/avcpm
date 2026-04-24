"""WIP command handler."""
import os
import sys


def wip_command(args):
    """Route wip commands."""
    from avcpm_wip import (
        claim_file, release_file, release_all, list_claims,
        list_my_claims, check_wip_conflicts, expire_stale_claims
    )

    base_dir = _get_base_dir(args)
    agent_id = getattr(args, 'agent', None) or os.environ.get("AVCPM_AGENT_ID", "unknown")

    # Auto-expire stale claims
    expire_stale_claims(base_dir=base_dir)

    if args.subcommand == "claim":
        if not args.file:
            print("Error: wip claim requires file path")
            sys.exit(1)
        task_id = getattr(args, 'task', None)
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
        mine = getattr(args, 'mine', False)
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


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"