#!/usr/bin/env python3
"""
AVCPM Status Reporting Dashboard
Provides unified CLI reporting for the AVCPM project.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

DEFAULT_BASE_DIR = ".avcpm"
COLUMNS = ["todo", "in-progress", "review", "done"]


def get_tasks_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the tasks directory path."""
    return os.path.join(base_dir, "tasks")


def get_ledger_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the ledger directory path."""
    return os.path.join(base_dir, "ledger")


def get_staging_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the staging directory path."""
    return os.path.join(base_dir, "staging")


def get_reviews_dir(base_dir=DEFAULT_BASE_DIR) -> Optional[Dict]:
    """Get the reviews directory path."""
    return os.path.join(base_dir, "reviews")


def print_table(title: str, headers: List[str], rows: List[List[str]], 
                footer: Optional[str] = None) -> None:
    """Print a simple terminal table."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)
    
    if not rows:
        print("  (empty)")
    else:
        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        
        # Print headers
        header_row = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
        print(f"  {header_row}")
        print("  " + "-" * len(header_row))
        
        # Print rows
        for row in rows:
            print("  " + "  ".join(str(cell).ljust(w) for cell, w in zip(row, widths)))
    
    if footer:
        print(f"\n  {footer}")
    print('=' * 60)


def get_tasks_by_status(base_dir=DEFAULT_BASE_DIR) -> Dict[str, List[Dict]]:
    """Load all tasks organized by status."""
    tasks = {col: [] for col in COLUMNS}
    tasks_dir = get_tasks_dir(base_dir)
    
    for col in COLUMNS:
        col_path = os.path.join(tasks_dir, col)
        if not os.path.exists(col_path):
            continue
        
        for filename in os.listdir(col_path):
            if filename.endswith('.json'):
                filepath = os.path.join(col_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        task = json.load(f)
                        task['_status'] = col
                        tasks[col].append(task)
                except (json.JSONDecodeError, IOError):
                    continue
    
    return tasks


def get_ledger_entries(limit: int = 10, base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    """Get recent ledger entries sorted by timestamp."""
    entries = []
    ledger_dir = get_ledger_dir(base_dir)
    
    if not os.path.exists(ledger_dir):
        return entries
    
    for filename in os.listdir(ledger_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(ledger_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    entries.append(entry)
            except (json.JSONDecodeError, IOError):
                continue
    
    # Sort by timestamp descending
    entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return entries[:limit]


def get_staging_files(base_dir=DEFAULT_BASE_DIR) -> List[Dict]:
    """Get files currently in staging."""
    files = []
    staging_dir = get_staging_dir(base_dir)
    
    if not os.path.exists(staging_dir):
        return files
    
    for filename in os.listdir(staging_dir):
        filepath = os.path.join(staging_dir, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                'name': filename,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    return files


def check_system_health(base_dir=DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """Check for system health issues."""
    issues = []
    warnings = []
    
    tasks_dir = get_tasks_dir(base_dir)
    ledger_dir = get_ledger_dir(base_dir)
    staging_dir = get_staging_dir(base_dir)
    
    # Check for orphaned tasks (tasks in ledger but not in any status)
    ledger_tasks = set()
    if os.path.exists(ledger_dir):
        for entry in get_ledger_entries(limit=100, base_dir=base_dir):
            if 'task_id' in entry:
                ledger_tasks.add(entry['task_id'])
    
    all_tasks = set()
    for col in COLUMNS:
        col_path = os.path.join(tasks_dir, col)
        if os.path.exists(col_path):
            for filename in os.listdir(col_path):
                if filename.endswith('.json'):
                    task_id = filename[:-5]  # Remove .json
                    all_tasks.add(task_id)
    
    orphaned_in_ledger = ledger_tasks - all_tasks
    if orphaned_in_ledger:
        issues.append(f"Tasks in ledger but not found in board: {', '.join(orphaned_in_ledger)}")
    
    # Check for staging files without ledger entries
    staging_files = get_staging_files(base_dir)
    if staging_files:
        # Check if these files are tracked in any ledger entry
        ledger_entries = get_ledger_entries(limit=100, base_dir=base_dir)
        staged_names = {f['name'] for f in staging_files}
        tracked_names = set()
        
        for entry in ledger_entries:
            for change in entry.get('changes', []):
                if 'staging_path' in change:
                    tracked_names.add(os.path.basename(change['staging_path']))
        
        untracked = staged_names - tracked_names
        if untracked:
            warnings.append(f"Untracked files in staging: {', '.join(untracked)}")
    
    # Check for duplicate task IDs across columns
    task_locations = {}
    for col in COLUMNS:
        col_path = os.path.join(tasks_dir, col)
        if not os.path.exists(col_path):
            continue
        for filename in os.listdir(col_path):
            if filename.endswith('.json'):
                task_id = filename[:-5]
                if task_id in task_locations:
                    issues.append(f"Task {task_id} found in multiple columns: {task_locations[task_id]} and {col}")
                else:
                    task_locations[task_id] = col
    
    return {
        'healthy': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }


def format_task_row(task: Dict) -> List[str]:
    """Format a task for display."""
    return [
        task.get('id', 'N/A'),
        task.get('title', task.get('description', 'No title')[:40]),
        task.get('assignee', 'unassigned'),
        task.get('priority', 'medium')
    ]


def format_ledger_row(entry: Dict) -> List[str]:
    """Format a ledger entry for display."""
    timestamp = entry.get('timestamp', 'N/A')
    if len(timestamp) > 16:
        timestamp = timestamp[:16]  # Trim to YYYY-MM-DD HH:MM
    
    files = len(entry.get('changes', []))
    
    return [
        entry.get('commit_id', 'N/A'),
        timestamp,
        entry.get('agent_id', 'N/A'),
        entry.get('task_id', 'N/A'),
        str(files)
    ]


def format_staging_row(file: Dict) -> List[str]:
    """Format a staging file for display."""
    size = file.get('size', 0)
    size_str = f"{size}B" if size < 1024 else f"{size // 1024}KB"
    
    modified = file.get('modified', 'N/A')
    if len(modified) > 16:
        modified = modified[:16]
    
    return [
        file.get('name', 'N/A'),
        size_str,
        modified
    ]


def generate_tasks_report(base_dir=DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """Generate task board report."""
    tasks = get_tasks_by_status(base_dir)
    
    report = {
        'summary': {},
        'columns': {}
    }
    
    for col in COLUMNS:
        report['summary'][col] = len(tasks[col])
        report['columns'][col] = tasks[col]
    
    return report


def generate_ledger_report(base_dir=DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """Generate ledger activity report."""
    return {
        'entries': get_ledger_entries(limit=10, base_dir=base_dir)
    }


def generate_staging_report(base_dir=DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """Generate staging status report."""
    return {
        'files': get_staging_files(base_dir)
    }


def generate_health_report(base_dir=DEFAULT_BASE_DIR) -> Dict[str, Any]:
    """Generate system health report."""
    return check_system_health(base_dir)


def display_tasks_report(report: Dict[str, Any]) -> None:
    """Display task board report in terminal format."""
    summary = report['summary']
    total = sum(summary.values())
    
    footer = f"Total: {total} tasks ({summary['todo']} todo, {summary['in-progress']} in-progress, {summary['review']} review, {summary['done']} done)"
    
    # Combine all tasks for display
    all_rows = []
    for col in COLUMNS:
        for task in report['columns'][col]:
            row = format_task_row(task)
            row.append(col)
            all_rows.append(row)
    
    print_table(
        "TASK BOARD SUMMARY",
        ["ID", "Title/Description", "Assignee", "Priority", "Status"],
        all_rows,
        footer
    )


def display_ledger_report(report: Dict[str, Any], base_dir=DEFAULT_BASE_DIR) -> None:
    """Display ledger activity report in terminal format."""
    rows = [format_ledger_row(entry) for entry in report['entries']]
    
    ledger_dir = get_ledger_dir(base_dir)
    total_commits = len([f for f in os.listdir(ledger_dir) if f.endswith('.json')]) if os.path.exists(ledger_dir) else 0
    
    print_table(
        "LEDGER ACTIVITY (Last 10 commits)",
        ["Commit ID", "Timestamp", "Agent", "Task ID", "Files"],
        rows,
        f"Total commits in ledger: {total_commits}"
    )


def display_staging_report(report: Dict[str, Any]) -> None:
    """Display staging status report in terminal format."""
    rows = [format_staging_row(f) for f in report['files']]
    
    print_table(
        "STAGING STATUS",
        ["File", "Size", "Modified"],
        rows,
        f"Total files in staging: {len(report['files'])}"
    )


def display_health_report(report: Dict[str, Any]) -> None:
    """Display system health report in terminal format."""
    if report['healthy'] and not report['warnings']:
        print("\n" + "=" * 60)
        print("  SYSTEM HEALTH")
        print("=" * 60)
        print("  ✓ All systems operational")
        print("=" * 60)
    else:
        rows = []
        for issue in report['issues']:
            rows.append(["ERROR", issue])
        for warning in report['warnings']:
            rows.append(["WARNING", warning])
        
        print_table(
            "SYSTEM HEALTH",
            ["Level", "Message"],
            rows
        )


def output_json(data: Dict[str, Any]) -> None:
    """Output report as JSON."""
    print(json.dumps(data, indent=2))


def main(base_dir: str = DEFAULT_BASE_DIR, json_output: bool = False,
            tasks_only: bool = False, ledger_only: bool = False,
            staging_only: bool = False, health_only: bool = False):
    """"Main entry point with optional direct parameters.
    
    Args:
        base_dir: Base directory for AVCPM
        json_output: Output as JSON
        tasks_only: Show only task board
        ledger_only: Show only ledger
        staging_only: Show only staging
        health_only: Show only health
    """
    # If run directly (not imported), parse CLI args
    if base_dir == DEFAULT_BASE_DIR and not any([json_output, tasks_only, ledger_only, staging_only, health_only]):
        parser = argparse.ArgumentParser(
            description="AVCPM Status Reporting Dashboard",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python avcpm_status.py              # Show all sections
  python avcpm_status.py --tasks      # Show only task board
  python avcpm_status.py --json       # Machine-readable output
        """
        )
        
        parser.add_argument(
            '--base-dir',
            default=DEFAULT_BASE_DIR,
            help='Base directory for AVCPM'
        )
        parser.add_argument(
            '--tasks',
            action='store_true',
            help='Show only task board summary'
        )
        parser.add_argument(
            '--ledger',
            action='store_true',
            help='Show only ledger activity'
        )
        parser.add_argument(
            '--staging',
            action='store_true',
            help='Show only staging status'
        )
        parser.add_argument(
            '--health',
            action='store_true',
            help='Show only system health'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output in JSON format'
        )
        
        cli_args = parser.parse_args()
        base_dir = cli_args.base_dir
        json_output = cli_args.json
        tasks_only = cli_args.tasks
        ledger_only = cli_args.ledger
        staging_only = cli_args.staging
        health_only = cli_args.health
    
    # If no specific section requested, show all
    show_all = not (tasks_only or ledger_only or staging_only or health_only)
    
    # Generate reports
    reports = {}
    
    if show_all or tasks_only:
        reports['tasks'] = generate_tasks_report(base_dir)
    
    if show_all or ledger_only:
        reports['ledger'] = generate_ledger_report(base_dir)
    
    if show_all or staging_only:
        reports['staging'] = generate_staging_report(base_dir)
    
    if show_all or health_only:
        reports['health'] = generate_health_report(base_dir)
    
    # Output
    if json_output:
        output_json(reports)
    else:
        if 'tasks' in reports:
            display_tasks_report(reports['tasks'])
        
        if 'ledger' in reports:
            display_ledger_report(reports['ledger'], base_dir)
        
        if 'staging' in reports:
            display_staging_report(reports['staging'])
        
        if 'health' in reports:
            display_health_report(reports['health'])
