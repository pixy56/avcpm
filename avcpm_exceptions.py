"""
AVCPM Exception Hierarchy

All AVCPM-specific exceptions inherit from AVCPMError, allowing
callers to catch the base class for uniform error handling.
"""


from __future__ import annotations

class AVCPMError(Exception):
    """Base exception for all AVCPM errors."""
    pass
from typing import Any, Dict, List, Optional, Tuple, Union


class AuthError(AVCPMError):
    """Authentication or authorization failures."""
    pass


class LedgerError(AVCPMError):
    """Ledger integrity issues."""
    pass


class SecurityError(AVCPMError):
    """Security violations such as path traversal or symlink attacks."""
    pass


class ValidationError(AVCPMError):
    """Input validation failures."""
    pass


class CommitError(AVCPMError):
    """Commit workflow failures."""
    pass


class MergeError(AVCPMError):
    """Merge workflow failures."""
    pass