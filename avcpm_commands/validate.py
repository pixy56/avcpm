"""Validate command handler."""
import os
import sys


def validate_command(args):
    """Route validate commands."""
    from avcpm_validate import validate_checksums, fix_mismatches, print_report

    base_dir = _get_base_dir(args)
    staging_dir = os.path.join(base_dir, "staging")
    ledger_dir = os.path.join(base_dir, "ledger")

    if getattr(args, 'staging_dir', None):
        staging_dir = args.staging_dir
    if getattr(args, 'ledger_dir', None):
        ledger_dir = args.ledger_dir

    report = validate_checksums(staging_dir, ledger_dir)

    if getattr(args, 'fix', False):
        if report.failed > 0:
            print("Applying fixes for mismatched checksums...")
            fixes = fix_mismatches(report, ledger_dir)
            print(f"Fixed {fixes} checksum(s)")
            report = validate_checksums(staging_dir, ledger_dir)

    print_report(report)

    if not report.success:
        sys.exit(1)


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"