"""Rollback command handler."""
import sys


def rollback_command(args):
    """Route rollback commands."""
    from avcpm_rollback import (
        rollback, unstage, restore_file, reset_soft, reset_hard,
        create_backup, list_backups, restore_backup, delete_backup
    )

    base_dir = _get_base_dir(args)

    if args.subcommand == "rollback":
        if not args.commit_id:
            print("Error: rollback requires commit_id")
            sys.exit(1)
        dry_run = getattr(args, 'dry_run', False)
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
        commit_id = getattr(args, 'commit_id', None)
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
        hard = getattr(args, 'hard', False)
        branch_name = getattr(args, 'branch', None)
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
        branch_name = getattr(args, 'branch', None)
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
            name = getattr(args, 'name', None)
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


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"