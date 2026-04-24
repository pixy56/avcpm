"""Status command handler."""
import sys


def status_command(args):
    """Route status command to avcpm_status module with direct parameter passing."""
    from avcpm_status import main as status_main

    base_dir = _get_base_dir(args)
    try:
        status_main(
            base_dir=base_dir,
            json_output=args.json,
            tasks_only=args.tasks,
            ledger_only=args.ledger,
            staging_only=args.staging,
            health_only=args.health
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"