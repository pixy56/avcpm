"""
AVCPM Security Module - Safe File Operations

Provides symlink-safe file operations to prevent directory traversal attacks.
All file operations verify that symlinks point within allowed base directories.

Uses O_NOFOLLOW on Unix to atomically reject symlinks, closing the TOCTOU
race between checking islink() and opening the file.
"""

import os
import shutil
import re
import sys
import io
from typing import Optional


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


# Agent ID validation regex: alphanumeric, underscore, hyphen only
AGENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def validate_agent_id(agent_id: str) -> str:
    """
    Validate an agent_id to prevent path traversal attacks.

    Args:
        agent_id: The agent ID string to validate

    Returns:
        The validated agent_id

    Raises:
        ValueError: If the agent_id contains unsafe characters or is too long
    """
    if not agent_id:
        raise ValueError("agent_id cannot be empty")
    if not isinstance(agent_id, str):
        raise ValueError("agent_id must be a string")
    if not AGENT_ID_PATTERN.match(agent_id):
        raise ValueError(
            f"Invalid agent_id '{agent_id}'. Must match regex "
            f"^[a-zA-Z0-9_-]{{1,64}}$ (alphanumeric, underscore, hyphen only, 1-64 chars)"
        )
    return agent_id


def safe_join(base_dir: str, agent_id: str, *tail: str) -> str:
    """
    Safely join a base directory with a validated agent_id and optional sub-paths.

    Validates agent_id before joining. Verifies the final path is within base_dir.

    Args:
        base_dir: The base directory
        agent_id: The agent ID (will be validated)
        *tail: Additional path components

    Returns:
        The joined path

    Raises:
        ValueError: If agent_id is invalid or final path escapes base_dir
    """
    validated = validate_agent_id(agent_id)
    path = os.path.join(base_dir, validated, *tail)
    resolved = os.path.realpath(os.path.abspath(path))
    base_resolved = os.path.realpath(os.path.abspath(base_dir))
    # Ensure base ends with separator for prefix check
    if not base_resolved.endswith(os.sep):
        base_resolved += os.sep
    if not (resolved == base_resolved.rstrip(os.sep) or resolved.startswith(base_resolved)):
        raise ValueError(f"Resolved path '{resolved}' is outside base directory '{base_dir}'")
    return resolved


def _resolve_real_path(path: str) -> str:
    """Get the real absolute path of a file."""
    return os.path.realpath(os.path.abspath(path))


def _is_path_within_base(target_path: str, base_dir: str) -> bool:
    """
    Check if target_path is within base_dir.
    Both paths are resolved to their real absolute paths.
    """
    real_target = _resolve_real_path(target_path)
    real_base = _resolve_real_path(base_dir)
    
    # Ensure base ends with separator for prefix check
    if not real_base.endswith(os.sep):
        real_base += os.sep
    
    return real_target.startswith(real_base) or real_target == real_base.rstrip(os.sep)


def _is_symlink(filepath: str) -> bool:
    """Check if filepath is a symlink (not following symlinks)."""
    return os.path.islink(filepath)


def _get_symlink_target(filepath: str) -> str:
    """Get the target of a symlink."""
    return os.readlink(filepath)


def safe_open_nofollow(filepath: str, mode: str = "rb") -> bytes:
    """
    Open a file safely, rejecting symlinks via O_NOFOLLOW on Unix.
    
    Uses os.open() with O_NOFOLLOW on Unix to atomically check that
    the path is not a symlink before opening. On Windows, falls back to
    checking with os.path.islink() since O_NOFOLLOW is unavailable.
    
    Args:
        filepath: Path to the file to open.
        mode: File open mode (default: "rb"). Supports "rb", "r", "wb", "w", "ab", "a".
    
    Returns:
        A file object.
    
    Raises:
        SecurityError: If filepath is a symlink.
        FileNotFoundError: If the file does not exist (for read modes).
    """
    if os.path.islink(filepath):
        raise SecurityError(
            f"Security violation: '{filepath}' is a symlink. Open rejected."
        )
    
    # On Unix, use O_NOFOLLOW for atomic symlink rejection
    if sys.platform != "win32":
        # Map mode strings to os.open flags
        binary = "b" in mode
        base_mode = mode.replace("b", "")
        
        if base_mode == "r":
            flags = os.O_RDONLY | os.O_NOFOLLOW
        elif base_mode == "w":
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
        elif base_mode == "a":
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW
        else:
            flags = os.O_RDONLY | os.O_NOFOLLOW
        
        try:
            fd = os.open(filepath, flags)
        except OSError as e:
            # O_NOFOLLOW causes ELOOP when path is a symlink
            if e.errno == 40:  # ELOOP
                raise SecurityError(
                    f"Security violation: '{filepath}' is a symlink. Open rejected."
                )
            raise
        
        try:
            if binary:
                return os.fdopen(fd, mode)
            else:
                return os.fdopen(fd, mode, encoding="utf-8")
        except:
            os.close(fd)
            raise
    else:
        # Windows fallback: islink check already done above
        return open(filepath, mode)


def safe_copy(src: str, dst: str, base_dir: str) -> None:
    """
    Safely copy a file, preventing symlink attacks.
    
    Uses safe_open_nofollow() to atomically reject symlinks on Unix,
    avoiding the TOCTOU race between checking and opening.
    
    Args:
        src: Source file path
        dst: Destination file path
        base_dir: Allowed base directory for symlinks
        
    Raises:
        SecurityError: If src is a symlink pointing outside base_dir
        IOError: If copy fails for other reasons
    """
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source file not found: {src}")
    
    # Try O_NOFOLLOW on Unix to atomically reject symlinks
    try:
        with safe_open_nofollow(src, "rb") as f:
            data = f.read()
        # Write destination normally
        parent_dir = os.path.dirname(dst)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)
    except SecurityError:
        # Re-check symlink target for base_dir enforcement
        if _is_symlink(src):
            link_target = _get_symlink_target(src)
            if not os.path.isabs(link_target):
                symlink_dir = os.path.dirname(os.path.abspath(src))
                link_target = os.path.join(symlink_dir, link_target)
            if not _is_path_within_base(link_target, base_dir):
                raise SecurityError(
                    f"Security violation: Symlink '{src}' points outside allowed "
                    f"directory to '{link_target}'. Copy rejected."
                )
            # Symlink target is within base_dir — copy the content
            shutil.copy2(src, dst)
        else:
            raise


def safe_read(filepath: str, base_dir: str) -> bytes:
    """
    Safely read a file, preventing symlink attacks.
    
    Uses safe_open_nofollow() to atomically reject symlinks on Unix,
    avoiding the TOCTOU race between checking and opening.
    
    Args:
        filepath: File to read
        base_dir: Allowed base directory for symlinks
        
    Returns:
        File contents as bytes
        
    Raises:
        SecurityError: If filepath is a symlink pointing outside base_dir
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Use O_NOFOLLOW to reject symlinks atomically on Unix
    try:
        with safe_open_nofollow(filepath, "rb") as f:
            return f.read()
    except SecurityError:
        # Re-check symlink target for base_dir enforcement on platforms
        # where O_NOFOLLOW isn't available (Windows)
        link_target = _get_symlink_target(filepath)
        if not os.path.isabs(link_target):
            symlink_dir = os.path.dirname(os.path.abspath(filepath))
            link_target = os.path.join(symlink_dir, link_target)
        if not _is_path_within_base(link_target, base_dir):
            raise SecurityError(
                f"Security violation: Symlink '{filepath}' points outside allowed "
                f"directory to '{link_target}'. Read rejected."
            )
        # Symlink target is within base_dir — follow it safely
        with open(filepath, "rb") as f:
            return f.read()


def safe_read_text(filepath: str, base_dir: str, encoding: str = "utf-8") -> str:
    """
    Safely read a file as text, preventing symlink attacks.
    
    Args:
        filepath: File to read
        base_dir: Allowed base directory for symlinks
        encoding: Text encoding (default: utf-8)
        
    Returns:
        File contents as string
        
    Raises:
        SecurityError: If filepath is a symlink pointing outside base_dir
        FileNotFoundError: If file doesn't exist
    """
    content = safe_read(filepath, base_dir)
    return content.decode(encoding)


def safe_exists(filepath: str, base_dir: str) -> bool:
    """
    Safely check if a file exists, rejecting dangerous symlinks.
    
    Args:
        filepath: File to check
        base_dir: Allowed base directory for symlinks
        
    Returns:
        True if file exists and is safe, False otherwise
        
    Raises:
        SecurityError: If filepath is a symlink pointing outside base_dir
    """
    # Use lexists to check if the symlink itself exists (even if target doesn't)
    if not os.path.lexists(filepath):
        return False
    
    # Check if it's a symlink
    if _is_symlink(filepath):
        # Get the symlink target
        link_target = _get_symlink_target(filepath)
        
        # If target is relative, resolve it relative to the symlink's directory
        if not os.path.isabs(link_target):
            symlink_dir = os.path.dirname(os.path.abspath(filepath))
            link_target = os.path.join(symlink_dir, link_target)
        
        # Verify the symlink target is within the allowed base directory
        if not _is_path_within_base(link_target, base_dir):
            raise SecurityError(
                f"Security violation: Symlink '{filepath}' points outside allowed "
                f"directory to '{link_target}'. Exists check rejected."
            )
        
        # Symlink is safe - check if the target actually exists
        return os.path.exists(filepath)
    
    # Regular file or directory
    return os.path.exists(filepath)


def safe_write(filepath: str, content: bytes, base_dir: str) -> None:
    """
    Safely write to a file, preventing symlink attacks.
    
    Uses safe_open_nofollow() to atomically reject symlinks on Unix,
    avoiding the TOCTOU race between checking and writing.
    
    Args:
        filepath: File to write
        content: Content to write
        base_dir: Allowed base directory for symlinks
        
    Raises:
        SecurityError: If filepath is a symlink pointing outside base_dir
    """
    # Ensure parent directory exists
    parent_dir = os.path.dirname(filepath)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    
    # Try O_NOFOLLOW first (Unix)
    if os.path.lexists(filepath) and os.path.islink(filepath):
        link_target = _get_symlink_target(filepath)
        if not os.path.isabs(link_target):
            symlink_dir = os.path.dirname(os.path.abspath(filepath))
            link_target = os.path.join(symlink_dir, link_target)
        if not _is_path_within_base(link_target, base_dir):
            raise SecurityError(
                f"Security violation: Symlink '{filepath}' points outside allowed "
                f"directory to '{link_target}'. Write rejected."
            )
        # Symlink target is within base_dir — write through the link
        with open(filepath, "wb") as f:
            f.write(content)
        return
    
    # For non-symlink files (or new files), use safe_open_nofollow
    try:
        with safe_open_nofollow(filepath, "wb") as f:
            f.write(content)
    except SecurityError:
        # On Windows without O_NOFOLLOW, re-check the symlink
        if os.path.islink(filepath):
            link_target = _get_symlink_target(filepath)
            if not os.path.isabs(link_target):
                symlink_dir = os.path.dirname(os.path.abspath(filepath))
                link_target = os.path.join(symlink_dir, link_target)
            if not _is_path_within_base(link_target, base_dir):
                raise SecurityError(
                    f"Security violation: Symlink '{filepath}' points outside allowed "
                    f"directory to '{link_target}'. Write rejected."
                )
            with open(filepath, "wb") as f:
                f.write(content)
        else:
            raise


def safe_write_text(filepath: str, content: str, base_dir: str, encoding: str = "utf-8") -> None:
    """
    Safely write text to a file, preventing symlink attacks.
    
    Args:
        filepath: File to write
        content: Text content to write
        base_dir: Allowed base directory for symlinks
        encoding: Text encoding (default: utf-8)
        
    Raises:
        SecurityError: If filepath is a symlink pointing outside base_dir
    """
    safe_write(filepath, content.encode(encoding), base_dir)


def safe_copytree(src: str, dst: str, base_dir: str) -> None:
    """
    Safely copy a directory tree, preventing symlink attacks.
    
    Args:
        src: Source directory
        dst: Destination directory
        base_dir: Allowed base directory for symlinks
        
    Raises:
        SecurityError: If any file is a symlink pointing outside base_dir
    """
    if not os.path.isdir(src):
        raise ValueError(f"Source is not a directory: {src}")
    
    os.makedirs(dst, exist_ok=True)
    
    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        dst_path = os.path.join(dst, item)
        
        if os.path.isdir(src_path):
            safe_copytree(src_path, dst_path, base_dir)
        else:
            safe_copy(src_path, dst_path, base_dir)


def validate_path_is_safe(filepath: str, base_dir: str) -> bool:
    """
    Validate that a file path is safe (not a dangerous symlink).
    
    Args:
        filepath: Path to validate
        base_dir: Allowed base directory for symlinks
        
    Returns:
        True if safe, False if file doesn't exist
        
    Raises:
        SecurityError: If filepath is a symlink pointing outside base_dir
    """
    if not os.path.lexists(filepath):
        return False
    
    if _is_symlink(filepath):
        link_target = _get_symlink_target(filepath)
        
        if not os.path.isabs(link_target):
            symlink_dir = os.path.dirname(os.path.abspath(filepath))
            link_target = os.path.join(symlink_dir, link_target)
        
        if not _is_path_within_base(link_target, base_dir):
            raise SecurityError(
                f"Security violation: Symlink '{filepath}' points outside allowed "
                f"directory to '{link_target}'. Path validation failed."
            )
    
    return True


# ============================================================================
# PATH TRAVERSAL PROTECTION
# ============================================================================

def sanitize_path(path: str, base_dir: str) -> str:
    """
    Sanitize a file path to prevent path traversal attacks.
    
    This function:
    1. Resolves all symlinks
    2. Normalizes the path
    3. Ensures the resolved path is within base_dir
    4. Rejects absolute paths and parent directory traversal
    
    Args:
        path: The file path to sanitize
        base_dir: The base directory that the path must be within
        
    Returns:
        The sanitized, normalized path
        
    Raises:
        ValueError: If the path is outside base_dir, is absolute, or contains traversal
    """
    import re
    
    # Reject empty paths
    if not path or not path.strip():
        raise ValueError("Path cannot be empty")
    
    # Check for parent directory traversal patterns
    # Match ../ or ..\\ patterns anywhere in the path
    traversal_pattern = r'\.\.[\\/]'
    if re.search(traversal_pattern, path):
        raise ValueError(f"Path traversal detected in: {path}")
    
    # Reject absolute paths
    if os.path.isabs(path):
        raise ValueError(f"Absolute paths are not allowed: {path}")
    
    # Normalize the base directory (must exist and be absolute)
    base_dir = os.path.abspath(base_dir)
    
    # Join base_dir with the given path and resolve
    # Use os.path.join to combine paths safely
    full_path = os.path.join(base_dir, path)
    
    # Resolve all symlinks and normalize the path
    try:
        resolved_path = os.path.realpath(full_path)
    except Exception as e:
        raise ValueError(f"Failed to resolve path: {path}") from e
    
    # Ensure the resolved path is within base_dir
    # Add a trailing separator to base_dir for proper prefix checking
    base_dir_with_sep = os.path.normpath(base_dir) + os.sep
    resolved_with_sep = os.path.normpath(resolved_path) + os.sep
    
    if not resolved_with_sep.startswith(base_dir_with_sep):
        raise ValueError(f"Path is outside allowed directory: {path}")
    
    # Also check using commonpath for additional safety
    try:
        common = os.path.commonpath([base_dir, resolved_path])
        if common != base_dir:
            raise ValueError(f"Path is outside allowed directory: {path}")
    except ValueError:
        # commonpath raises ValueError if paths are on different drives (Windows)
        raise ValueError(f"Path is outside allowed directory: {path}")
    
    return resolved_path


def sanitize_path_list(paths: list, base_dir: str) -> list:
    """
    Sanitize a list of file paths.
    
    Args:
        paths: List of file paths to sanitize
        base_dir: The base directory that paths must be within
        
    Returns:
        List of sanitized paths
        
    Raises:
        ValueError: If any path fails sanitization
    """
    return [sanitize_path(p, base_dir) for p in paths]


def is_path_within_base(path: str, base_dir: str) -> bool:
    """
    Check if a path is within the base directory without raising exceptions.
    
    Args:
        path: The file path to check
        base_dir: The base directory
        
    Returns:
        True if path is within base_dir, False otherwise
    """
    try:
        sanitize_path(path, base_dir)
        return True
    except ValueError:
        return False