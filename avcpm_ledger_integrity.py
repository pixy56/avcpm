#!/usr/bin/env python3
"""
AVCPM Ledger Integrity Chain

Implements a blockchain-like integrity chain for ledger entries.
Each entry includes a hash of the previous entry, creating a tamper-evident chain.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from avcpm_branch import get_branch_ledger_dir, list_branches


DEFAULT_BASE_DIR = ".avcpm"


@dataclass
class IntegrityCheckResult:
    """Result of a ledger integrity check."""
    commit_id: str
    status: str  # 'valid', 'invalid_hash', 'invalid_chain', 'orphaned'
    message: str
    previous_hash: Optional[str] = None
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None


@dataclass
class IntegrityReport:
    """Complete integrity verification report."""
    branch: str
    total_entries: int = 0
    valid_entries: int = 0
    invalid_entries: int = 0
    tampered_entries: List[IntegrityCheckResult] = field(default_factory=list)
    healthy: bool = True
    
    @property
    def success(self) -> bool:
        """Returns True if all entries are valid."""
        return self.invalid_entries == 0 and len(self.tampered_entries) == 0


def calculate_entry_hash(entry: Dict) -> str:
    """
    Calculate SHA256 hash of a ledger entry (excluding entry_hash itself).
    
    Args:
        entry: Ledger entry dictionary
        
    Returns:
        str: SHA256 hex digest of the entry content
    """
    # Create a copy without the entry_hash field for calculation
    entry_copy = {k: v for k, v in entry.items() if k != 'entry_hash'}
    
    # Canonical JSON representation (sorted keys for consistency)
    content = json.dumps(entry_copy, sort_keys=True, indent=None, separators=(',', ':'))
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def get_previous_commit_hash(branch_name: str, commit_id: str, base_dir: str = DEFAULT_BASE_DIR) -> Optional[str]:
    """
    Get the hash of the commit immediately before commit_id in the ledger.
    
    Args:
        branch_name: Name of the branch
        commit_id: Current commit ID
        base_dir: Base directory for AVCPM
        
    Returns:
        str: SHA256 hash of the previous commit entry, or None if this is the first commit
    """
    ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
    
    if not os.path.exists(ledger_dir):
        return None
    
    # Get all commit files sorted by commit ID (which is timestamp-based)
    commit_files = sorted([f for f in os.listdir(ledger_dir) if f.endswith('.json')])
    
    # Find the index of current commit
    current_file = f"{commit_id}.json"
    try:
        current_index = commit_files.index(current_file)
    except ValueError:
        return None
    
    # If this is the first commit, there is no previous
    if current_index == 0:
        return None
    
    # Get the previous commit file
    previous_file = commit_files[current_index - 1]
    previous_path = os.path.join(ledger_dir, previous_file)
    
    try:
        with open(previous_path, 'r') as f:
            previous_entry = json.load(f)
        return previous_entry.get('entry_hash')
    except (json.JSONDecodeError, IOError):
        return None


def get_last_commit_hash(branch_name: str, base_dir: str = DEFAULT_BASE_DIR) -> Optional[str]:
    """
    Get the hash of the most recent commit in the ledger.
    
    Args:
        branch_name: Name of the branch
        base_dir: Base directory for AVCPM
        
    Returns:
        str: SHA256 hash of the last commit entry, or None if ledger is empty
    """
    ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
    
    if not os.path.exists(ledger_dir):
        return None
    
    # Get all commit files sorted by commit ID
    commit_files = sorted([f for f in os.listdir(ledger_dir) if f.endswith('.json')])
    
    if not commit_files:
        return None
    
    # Get the last commit file
    last_file = commit_files[-1]
    last_path = os.path.join(ledger_dir, last_file)
    
    try:
        with open(last_path, 'r') as f:
            last_entry = json.load(f)
        return last_entry.get('entry_hash')
    except (json.JSONDecodeError, IOError):
        return None


def verify_ledger_integrity(branch_name: str, base_dir: str = DEFAULT_BASE_DIR) -> IntegrityReport:
    """
    Verify the integrity chain of a branch's ledger.
    
    Walks through all ledger entries in order and verifies:
    1. Each entry's entry_hash matches its content
    2. Each entry's previous_hash matches the actual hash of the previous entry
    
    Args:
        branch_name: Name of the branch to verify
        base_dir: Base directory for AVCPM
        
    Returns:
        IntegrityReport with verification results
    """
    report = IntegrityReport(branch=branch_name)
    ledger_dir = get_branch_ledger_dir(branch_name, base_dir)
    
    if not os.path.exists(ledger_dir):
        report.healthy = False
        report.message = f"Ledger directory not found for branch '{branch_name}'"
        return report
    
    # Get all commit files sorted by commit ID (timestamp-based ordering)
    commit_files = sorted([f for f in os.listdir(ledger_dir) if f.endswith('.json')])
    
    if not commit_files:
        report.healthy = True
        return report
    
    report.total_entries = len(commit_files)
    
    # Load all entries first
    entries = []
    for commit_file in commit_files:
        commit_id = commit_file.replace('.json', '')
        commit_path = os.path.join(ledger_dir, commit_file)
        
        try:
            with open(commit_path, 'r') as f:
                entry = json.load(f)
                entry['_commit_id'] = commit_id
                entry['_file_path'] = commit_path
                entries.append(entry)
        except (json.JSONDecodeError, IOError) as e:
            report.invalid_entries += 1
            report.healthy = False
            report.tampered_entries.append(IntegrityCheckResult(
                commit_id=commit_id,
                status='invalid_hash',
                message=f"Failed to read commit file: {e}"
            ))
    
    # Verify each entry in the chain
    previous_hash = None
    
    for i, entry in enumerate(entries):
        commit_id = entry['_commit_id']
        
        # Verify this entry's own hash
        stored_hash = entry.get('entry_hash')
        if not stored_hash:
            report.invalid_entries += 1
            report.healthy = False
            report.tampered_entries.append(IntegrityCheckResult(
                commit_id=commit_id,
                status='invalid_hash',
                message="Missing entry_hash field",
                previous_hash=entry.get('previous_hash')
            ))
            continue
        
        calculated_hash = calculate_entry_hash(entry)
        if stored_hash != calculated_hash:
            report.invalid_entries += 1
            report.healthy = False
            report.tampered_entries.append(IntegrityCheckResult(
                commit_id=commit_id,
                status='invalid_hash',
                message="Entry content has been tampered with (entry_hash mismatch)",
                previous_hash=entry.get('previous_hash'),
                expected_hash=stored_hash,
                actual_hash=calculated_hash
            ))
            continue
        
        # Verify chain link (previous_hash)
        stored_previous_hash = entry.get('previous_hash')
        
        if i == 0:
            # First entry should have no previous_hash
            if stored_previous_hash is not None:
                report.invalid_entries += 1
                report.healthy = False
                report.tampered_entries.append(IntegrityCheckResult(
                    commit_id=commit_id,
                    status='invalid_chain',
                    message="First entry should not have previous_hash",
                    previous_hash=stored_previous_hash
                ))
                continue
        else:
            # Subsequent entries must match the actual previous hash
            if stored_previous_hash != previous_hash:
                report.invalid_entries += 1
                report.healthy = False
                report.tampered_entries.append(IntegrityCheckResult(
                    commit_id=commit_id,
                    status='invalid_chain',
                    message="Chain is broken (previous_hash does not match actual previous entry)",
                    previous_hash=stored_previous_hash,
                    expected_hash=previous_hash,
                    actual_hash=stored_previous_hash
                ))
                continue
        
        # Entry is valid
        report.valid_entries += 1
        previous_hash = stored_hash
    
    return report


def verify_all_ledgers(base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, IntegrityReport]:
    """
    Verify integrity of all branch ledgers.
    
    Args:
        base_dir: Base directory for AVCPM
        
    Returns:
        Dict mapping branch name to IntegrityReport
    """
    results = {}
    branches = list_branches(base_dir)
    
    for branch in branches:
        branch_name = branch['name']
        report = verify_ledger_integrity(branch_name, base_dir)
        results[branch_name] = report
    
    return results


def format_integrity_report(report: IntegrityReport) -> str:
    """Format an integrity report for display."""
    lines = []
    lines.append(f"\n{'=' * 60}")
    lines.append(f"  Ledger Integrity Report: {report.branch}")
    lines.append(f"{'=' * 60}")
    lines.append(f"  Total entries:   {report.total_entries}")
    lines.append(f"  Valid entries:   {report.valid_entries}")
    lines.append(f"  Invalid entries: {report.invalid_entries}")
    
    if report.tampered_entries:
        lines.append(f"\n  TAMPERED ENTRIES:")
        lines.append(f"  {'-' * 56}")
        for entry in report.tampered_entries:
            lines.append(f"  Commit: {entry.commit_id}")
            lines.append(f"    Status:  {entry.status}")
            lines.append(f"    Message: {entry.message}")
            if entry.expected_hash and entry.actual_hash:
                lines.append(f"    Expected: {entry.expected_hash[:16]}...")
                lines.append(f"    Actual:   {entry.actual_hash[:16]}...")
            lines.append("")
    
    if report.success:
        lines.append(f"\n  ✓ Ledger integrity verified - chain is intact")
    else:
        lines.append(f"\n  ✗ LEDGER INTEGRITY COMPROMISED")
    
    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


def print_integrity_report(report: IntegrityReport) -> None:
    """Print an integrity report to console."""
    print(format_integrity_report(report))


def check_integrity_warning(branch_name: str, base_dir: str = DEFAULT_BASE_DIR) -> Optional[str]:
    """
    Get a warning message if ledger integrity is compromised.
    
    Args:
        branch_name: Name of the branch to check
        base_dir: Base directory for AVCPM
        
    Returns:
        str: Warning message if integrity is compromised, None if healthy
    """
    report = verify_ledger_integrity(branch_name, base_dir)
    
    if report.success:
        return None
    
    return f"WARNING: Ledger integrity compromised on branch '{branch_name}'! {report.invalid_entries} tampered entries detected."


def validate_ledger_command(args) -> None:
    """Handle the 'avcpm validate ledger' command."""
    base_dir = getattr(args, 'base_dir', DEFAULT_BASE_DIR)
    branch = getattr(args, 'branch', None)
    json_output = getattr(args, 'json', False)
    
    if branch:
        # Validate specific branch
        report = verify_ledger_integrity(branch, base_dir)
        
        if json_output:
            result = {
                "branch": report.branch,
                "total_entries": report.total_entries,
                "valid_entries": report.valid_entries,
                "invalid_entries": report.invalid_entries,
                "healthy": report.success,
                "tampered_entries": [
                    {
                        "commit_id": e.commit_id,
                        "status": e.status,
                        "message": e.message,
                        "previous_hash": e.previous_hash,
                        "expected_hash": e.expected_hash,
                        "actual_hash": e.actual_hash
                    }
                    for e in report.tampered_entries
                ]
            }
            print(json.dumps(result, indent=2))
        else:
            print_integrity_report(report)
        
        sys.exit(0 if report.success else 1)
    else:
        # Validate all branches
        results = verify_all_ledgers(base_dir)
        all_healthy = all(r.success for r in results.values())
        
        if json_output:
            output = {
                branch: {
                    "total_entries": r.total_entries,
                    "valid_entries": r.valid_entries,
                    "invalid_entries": r.invalid_entries,
                    "healthy": r.success,
                    "tampered_entries": [
                        {
                            "commit_id": e.commit_id,
                            "status": e.status,
                            "message": e.message
                        }
                        for e in r.tampered_entries
                    ]
                }
                for branch, r in results.items()
            }
            print(json.dumps(output, indent=2))
        else:
            for branch, report in results.items():
                print_integrity_report(report)
        
        sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify AVCPM ledger integrity chain"
    )
    parser.add_argument(
        "--branch",
        help="Branch to verify (default: all branches)"
    )
    parser.add_argument(
        "--base-dir",
        default=DEFAULT_BASE_DIR,
        help="Base directory for AVCPM"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    validate_ledger_command(args)
