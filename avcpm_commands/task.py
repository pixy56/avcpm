"""Task command handler."""
import sys


def task_command(args):
    """Route task commands."""
    from avcpm_task import (
        create_task, move_task, list_tasks, list_blocked,
        deps_add, deps_remove, deps_show, deps_dependents
    )

    subcommand = args.subcommand
    base_dir = _get_base_dir(args)

    if subcommand == "create":
        if not args.task_id or not args.description:
            print("Error: task create requires task_id and description")
            sys.exit(1)
        assignee = getattr(args, 'assignee', None) or "unassigned"
        depends_on = getattr(args, 'depends_on', None)
        try:
            create_task(args.task_id, args.description, assignee, depends_on, base_dir)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif subcommand == "move":
        if not args.task_id or not args.status:
            print("Error: task move requires task_id and status")
            sys.exit(1)
        force = getattr(args, 'force', False)
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


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"