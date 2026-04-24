"""
AVCPM Security Audit Logging System

Provides append-only audit logging for security-critical operations.
Events are written to .avcpm/audit.log with log rotation at 10MB (5 backups).
"""

import os
import json
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_BASE_DIR = ".avcpm"
AUDIT_LOG_FILENAME = "audit.log"
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_BACKUP_COUNT = 5

# Event types
EVENT_AUTH_SUCCESS = "auth_success"
EVENT_AUTH_FAILURE = "auth_failure"
EVENT_COMMIT = "commit"
EVENT_MERGE = "merge"
EVENT_ROLLBACK = "rollback"
EVENT_AGENT_CREATE = "agent_create"
EVENT_AGENT_DELETE = "agent_delete"


def get_audit_log_path(base_dir: str = DEFAULT_BASE_DIR) -> str:
    """Get the path to the audit log file."""
    return os.path.join(base_dir, AUDIT_LOG_FILENAME)


def _ensure_audit_dir(base_dir: str = DEFAULT_BASE_DIR) -> None:
    """Ensure the base directory exists."""
    os.makedirs(base_dir, exist_ok=True)


def _rotate_log_if_needed(log_path: str) -> None:
    """
    Rotate the audit log if it exceeds MAX_LOG_SIZE_BYTES.
    Keeps up to MAX_BACKUP_COUNT compressed backups.
    """
    if not os.path.exists(log_path):
        return

    file_size = os.path.getsize(log_path)
    if file_size < MAX_LOG_SIZE_BYTES:
        return

    # Rotate: audit.log.4.gz -> delete, audit.log.3.gz -> audit.log.4.gz, etc.
    backups = []
    for i in range(MAX_BACKUP_COUNT - 1, -1, -1):
        if i == 0:
            old_path = log_path
        else:
            old_path = f"{log_path}.{i}.gz"
        if os.path.exists(old_path):
            backups.append(old_path)

    # Remove the oldest backup if we've reached the limit
    if len(backups) >= MAX_BACKUP_COUNT:
        oldest = backups[-1]
        try:
            os.remove(oldest)
        except OSError:
            pass

    # Shift remaining backups
    for i in range(len(backups) - 1, -1, -1):
        old_path = backups[i]
        if i == 0:
            new_path = f"{log_path}.1.gz"
        else:
            new_path = f"{log_path}.{i + 1}.gz"
        try:
            with open(old_path, "rb") as f_in:
                with gzip.open(new_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(old_path)
        except OSError:
            pass

    # Compress current log to .1.gz
    try:
        with open(log_path, "rb") as f_in:
            with gzip.open(f"{log_path}.1.gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
    except OSError:
        pass

    # Truncate the current log
    try:
        with open(log_path, "w") as f:
            pass  # Truncate to zero
    except OSError:
        pass


def audit_log(event_type: str, agent_id: str, details: Optional[Dict[str, Any]] = None) -> bool:
    """
    Write an audit log entry.

    Args:
        event_type: Type of event (auth_success, auth_failure, commit, merge,
                    rollback, agent_create, agent_delete)
        agent_id: ID of the agent performing the action
        details: Additional event-specific details

    Returns:
        bool: True if logged successfully, False otherwise
    """
    _ensure_audit_dir()

    log_path = get_audit_log_path()

    # Rotate if needed before writing
    _rotate_log_if_needed(log_path)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "agent_id": agent_id,
        "details": details or {}
    }

    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return True
    except OSError:
        return False


def read_audit_log(limit: Optional[int] = None, base_dir: str = DEFAULT_BASE_DIR) -> list:
    """
    Read audit log entries (does not read compressed backups).

    Args:
        limit: Maximum number of entries to return (most recent)
        base_dir: Base directory for AVCPM

    Returns:
        List of audit log entries (dicts)
    """
    log_path = get_audit_log_path(base_dir)

    if not os.path.exists(log_path):
        return []

    entries = []
    try:
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []

    if limit:
        return entries[-limit:]
    return entries
