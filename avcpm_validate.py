#!/usr/bin/env python3
"""
AVCPM Checksum Validator

Validates SHA256 checksums of files in .avcpm/staging against ledger entries.
Can be used as a CLI tool or imported as a module.

Usage:
    python avcpm_validate.py              # Validate all files
    python avcpm_validate.py --fix        # Fix mismatched checksums
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# Default paths (can be overridden for testing)
DEFAULT_STAGING_DIR = ".avcpm/staging"
DEFAULT_LEDGER_DIR = ".avcpm/ledger"


@dataclass
class ValidationResult:
    """Result of a single file validation."""
    file: str
    staging_path: str
    expected_checksum: str
    actual_checksum: str
    status: str  # 'passed', 'failed', 'missing_file', 'orphaned_entry'


@dataclass
class ValidationReport:
    """Complete validation report."""
    files_checked: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    results: List[ValidationResult] = field(default_factory=list)
    orphaned_entries: List[Dict] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Returns True if all validations passed with no errors."""
        return self.failed == 0 and self.errors == 0 and len(self.orphaned_entries) == 0


def calculate_checksum(filepath: str) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_ledger_entries(ledger_dir: str) -> List[Dict]:
    """Load all ledger entries from the ledger directory."""
    entries = []
    ledger_path = Path(ledger_dir)
    
    if not ledger_path.exists():
        return entries

    for ledger_file in sorted(ledger_path.glob("*.json")):
        try:
            with open(ledger_file, "r") as f:
                data = json.load(f)
                data["_ledger_file"] = str(ledger_file)
                entries.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read ledger file {ledger_file}: {e}")
    
    return entries


def build_checksum_index(entries: List[Dict]) -> Dict[str, Dict]:
    """
    Build an index of expected checksums from ledger entries.
    Returns a dict mapping staging_path -> checksum info.
    """
    index = {}
    for entry in entries:
        for change in entry.get("changes", []):
            staging_path = change.get("staging_path", "")
            if staging_path:
                index[staging_path] = {
                    "file": change.get("file"),
                    "checksum": change.get("checksum"),
                    "commit_id": entry.get("commit_id"),
                    "ledger_file": entry.get("_ledger_file")
                }
    return index


def get_staging_files(staging_dir: str) -> List[str]:
    """Get all files in the staging directory (recursively)."""
    staging_path = Path(staging_dir)
    if not staging_path.exists():
        return []
    
    files = []
    for item in staging_path.rglob("*"):
        if item.is_file():
            files.append(str(item.relative_to(staging_path)))
    return files


def validate_checksums(
    staging_dir: str = DEFAULT_STAGING_DIR,
    ledger_dir: str = DEFAULT_LEDGER_DIR
) -> ValidationReport:
    """
    Validate checksums of all files in staging against ledger entries.
    
    Args:
        staging_dir: Path to staging directory
        ledger_dir: Path to ledger directory
    
    Returns:
        ValidationReport with complete results
    """
    report = ValidationReport()
    
    # Load ledger entries
    entries = load_ledger_entries(ledger_dir)
    checksum_index = build_checksum_index(entries)
    
    # Get all files in staging
    staging_files = get_staging_files(staging_dir)
    
    # Track which ledger entries we've seen
    seen_ledger_paths = set()
    
    # Validate each staging file against ledger
    for rel_path in staging_files:
        full_path = os.path.join(staging_dir, rel_path)
        staging_key = f"{staging_dir}/{rel_path}"
        
        report.files_checked += 1
        
        if staging_key not in checksum_index:
            # File exists in staging but not in ledger (orphaned file)
            result = ValidationResult(
                file=rel_path,
                staging_path=staging_key,
                expected_checksum="",
                actual_checksum="",
                status="orphaned_entry"
            )
            report.results.append(result)
            report.errors += 1
            continue
        
        seen_ledger_paths.add(staging_key)
        expected = checksum_index[staging_key]
        
        # Check if file exists (should always be true here)
        if not os.path.exists(full_path):
            result = ValidationResult(
                file=expected["file"],
                staging_path=staging_key,
                expected_checksum=expected["checksum"],
                actual_checksum="",
                status="missing_file"
            )
            report.results.append(result)
            report.errors += 1
            continue
        
        # Calculate actual checksum
        actual_checksum = calculate_checksum(full_path)
        
        if actual_checksum == expected["checksum"]:
            result = ValidationResult(
                file=expected["file"],
                staging_path=staging_key,
                expected_checksum=expected["checksum"],
                actual_checksum=actual_checksum,
                status="passed"
            )
            report.passed += 1
        else:
            result = ValidationResult(
                file=expected["file"],
                staging_path=staging_key,
                expected_checksum=expected["checksum"],
                actual_checksum=actual_checksum,
                status="failed"
            )
            report.failed += 1
        
        report.results.append(result)
    
    # Check for orphaned ledger entries (in ledger but file missing)
    for staging_key, info in checksum_index.items():
        if staging_key not in seen_ledger_paths:
            report.orphaned_entries.append({
                "file": info["file"],
                "staging_path": staging_key,
                "expected_checksum": info["checksum"],
                "commit_id": info["commit_id"]
            })
            report.errors += 1
    
    return report


def fix_mismatches(
    report: ValidationReport,
    ledger_dir: str = DEFAULT_LEDGER_DIR
) -> int:
    """
    Fix mismatched checksums by updating ledger entries.
    
    Args:
        report: ValidationReport with failed validations
        ledger_dir: Path to ledger directory
    
    Returns:
        Number of fixes applied
    """
    fixes_applied = 0
    
    # Group failed results by ledger file
    ledger_updates: Dict[str, List[ValidationResult]] = {}
    
    for result in report.results:
        if result.status == "failed":
            # Find which ledger file contains this entry
            entries = load_ledger_entries(ledger_dir)
            for entry in entries:
                for change in entry.get("changes", []):
                    if change.get("staging_path") == result.staging_path:
                        ledger_file = entry.get("_ledger_file")
                        if ledger_file not in ledger_updates:
                            ledger_updates[ledger_file] = []
                        ledger_updates[ledger_file].append(result)
                        break
    
    # Update each ledger file
    for ledger_file, results in ledger_updates.items():
        try:
            with open(ledger_file, "r") as f:
                entry = json.load(f)
            
            # Update checksums for failed validations
            for change in entry.get("changes", []):
                for result in results:
                    if change.get("staging_path") == result.staging_path:
                        print(f"  Updating checksum for {result.file}")
                        print(f"    Old: {result.expected_checksum[:16]}...")
                        print(f"    New: {result.actual_checksum[:16]}...")
                        change["checksum"] = result.actual_checksum
                        fixes_applied += 1
            
            # Write updated ledger
            with open(ledger_file, "w") as f:
                json.dump(entry, f, indent=4)
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error updating ledger file {ledger_file}: {e}")
    
    return fixes_applied


def print_report(report: ValidationReport) -> None:
    """Print a formatted validation report to console."""
    print("=" * 70)
    print("AVCPM Checksum Validation Report")
    print("=" * 70)
    print()
    
    # Summary
    print(f"Files checked: {report.files_checked}")
    print(f"Passed:        {report.passed}")
    print(f"Failed:        {report.failed}")
    print(f"Errors:        {report.errors}")
    print()
    
    # Detailed results
    if report.results:
        print("-" * 70)
        print(f"{'File':<30} {'Status':<15} {'Checksum Match'}")
        print("-" * 70)
        
        for result in report.results:
            status_emoji = "✓" if result.status == "passed" else "✗"
            status_text = result.status.upper()
            
            if result.status == "passed":
                checksum_display = f"{result.actual_checksum[:16]}..."
            elif result.status == "failed":
                checksum_display = f"MISMATCH (exp: {result.expected_checksum[:8]}..., got: {result.actual_checksum[:8]}...)"
            elif result.status == "missing_file":
                checksum_display = "FILE NOT FOUND"
            elif result.status == "orphaned_entry":
                checksum_display = "NOT IN LEDGER"
            else:
                checksum_display = "N/A"
            
            print(f"{result.file:<30} {status_emoji} {status_text:<13} {checksum_display}")
    
    # Orphaned entries
    if report.orphaned_entries:
        print()
        print("-" * 70)
        print("ORPHANED LEDGER ENTRIES (file missing from staging):")
        print("-" * 70)
        for entry in report.orphaned_entries:
            print(f"  {entry['file']}")
            print(f"    Expected at: {entry['staging_path']}")
            print(f"    Commit:      {entry['commit_id']}")
    
    print()
    print("=" * 70)
    if report.success:
        print("RESULT: PASSED - All checksums validated successfully")
    else:
        print("RESULT: FAILED - Checksum validation detected issues")
    print("=" * 70)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate SHA256 checksums of files in .avcpm/staging against ledger entries."
    )
    parser.add_argument(
        "--staging-dir",
        default=DEFAULT_STAGING_DIR,
        help=f"Path to staging directory (default: {DEFAULT_STAGING_DIR})"
    )
    parser.add_argument(
        "--ledger-dir",
        default=DEFAULT_LEDGER_DIR,
        help=f"Path to ledger directory (default: {DEFAULT_LEDGER_DIR})"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix mismatched checksums by updating ledger entries"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON instead of table"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only output summary, skip detailed table"
    )
    
    args = parser.parse_args()
    
    # Run validation
    report = validate_checksums(args.staging_dir, args.ledger_dir)
    
    # Fix mismatches if requested
    if args.fix and report.failed > 0:
        print()
        print("Applying fixes for mismatched checksums...")
        fixes = fix_mismatches(report, args.ledger_dir)
        print(f"Fixed {fixes} checksum(s)")
        print()
        
        # Re-validate after fixes
        report = validate_checksums(args.staging_dir, args.ledger_dir)
    
    # Output report
    if args.json:
        # Convert to JSON-serializable dict
        report_dict = {
            "files_checked": report.files_checked,
            "passed": report.passed,
            "failed": report.failed,
            "errors": report.errors,
            "success": report.success,
            "results": [
                {
                    "file": r.file,
                    "staging_path": r.staging_path,
                    "expected_checksum": r.expected_checksum,
                    "actual_checksum": r.actual_checksum,
                    "status": r.status
                }
                for r in report.results
            ],
            "orphaned_entries": report.orphaned_entries
        }
        print(json.dumps(report_dict, indent=2))
    elif not args.quiet:
        print_report(report)
    else:
        # Quiet mode - just summary
        print(f"Checked: {report.files_checked}, Passed: {report.passed}, Failed: {report.failed}, Errors: {report.errors}")
    
    # Exit with appropriate code
    sys.exit(0 if report.success else 1)


if __name__ == "__main__":
    main()