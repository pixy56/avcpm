"""
AVCPM Security Module - Safe File Operations

Provides symlink-safe file operations to prevent directory traversal attacks.
All file operations verify that symlinks point within allowed base directories.
"""

import os
import shutil
from typing import Optional


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


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


def safe_copy(src: str, dst: str, base_dir: str) -> None:
    """
    Safely copy a file, preventing symlink attacks.
    
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
    
    # Check if src is a symlink
    if _is_symlink(src):
        # Get the symlink target
        link_target = _get_symlink_target(src)
        
        # If target is relative, resolve it relative to the symlink's directory
        if not os.path.isabs(link_target):
            symlink_dir = os.path.dirname(os.path.abspath(src))
            link_target = os.path.join(symlink_dir, link_target)
        
        # Verify the symlink target is within the allowed base directory
        if not _is_path_within_base(link_target, base_dir):
            raise SecurityError(
                f"Security violation: Symlink '{src}' points outside allowed "
                f"directory to '{link_target}'. Copy rejected."
            )
        
        # Symlink is safe - copy the target content, not the symlink itself
        # Use shutil.copy2 which will copy the file content (following the safe symlink)
        shutil.copy2(src, dst)
    else:
        # Regular file - safe to copy
        shutil.copy2(src, dst)


def safe_read(filepath: str, base_dir: str) -> bytes:
    """
    Safely read a file, preventing symlink attacks.
    
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
    
    # Check if filepath is a symlink
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
                f"directory to '{link_target}'. Read rejected."
            )
    
    # Safe to read (either regular file or safe symlink)
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
    If the file is a dangerous symlink, it will be rejected.
    
    Args:
        filepath: File to write
        content: Content to write
        base_dir: Allowed base directory for symlinks
        
    Raises:
        SecurityError: If filepath is a symlink pointing outside base_dir
    """
    # Check if filepath is a symlink
    if os.path.islink(filepath):
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
                f"directory to '{link_target}'. Write rejected."
            )
    
    # Ensure parent directory exists
    parent_dir = os.path.dirname(filepath)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    
    # Safe to write
    with open(filepath, "wb") as f:
        f.write(content)


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
