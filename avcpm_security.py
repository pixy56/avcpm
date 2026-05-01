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


# ============================================================================
# DIRECTORY PROTECTION
# ============================================================================

def safe_makedirs(path: str, base_dir: str, exist_ok: bool = False) -> None:
    """
    Safely create directories, preventing symlink attacks.
    
    This function:
    1. Resolves the path using realpath to follow symlinks
    2. Verifies the resolved path is within base_dir
    3. Rejects creation if any parent directory is a dangerous symlink
    
    Args:
        path: Directory path to create
        base_dir: Allowed base directory
        exist_ok: If True, don't raise error if directory exists
        
    Raises:
        SecurityError: If path is a symlink pointing outside base_dir
        ValueError: If path would be created outside base_dir
    """
    # Resolve the full path
    abs_path = os.path.abspath(path)
    real_path = os.path.realpath(abs_path)
    real_base = os.path.realpath(os.path.abspath(base_dir))
    
    # Verify the resolved path is within base_dir
    if not _is_path_within_base(real_path, real_base):
        raise SecurityError(
            f"Security violation: Directory '{path}' resolves outside allowed "
            f"base directory to '{real_path}'. Directory creation rejected."
        )
    
    # Check if the path itself is a symlink
    if os.path.islink(path):
        link_target = os.readlink(path)
        if not os.path.isabs(link_target):
            link_target = os.path.join(os.path.dirname(abs_path), link_target)
        if not _is_path_within_base(link_target, real_base):
            raise SecurityError(
                f"Security violation: Directory '{path}' is a symlink pointing "
                f"outside allowed directory to '{link_target}'. Directory creation rejected."
            )
        # Symlink is safe and exists
        return
    
    # Check each parent directory for dangerous symlinks
    current = abs_path
    while current and current != os.path.dirname(current):
        if os.path.islink(current):
            link_target = os.readlink(current)
            if not os.path.isabs(link_target):
                link_target = os.path.join(os.path.dirname(current), link_target)
            if not _is_path_within_base(link_target, real_base):
                raise SecurityError(
                    f"Security violation: Parent directory '{current}' is a symlink "
                    f"pointing outside allowed directory to '{link_target}'. "
                    f"Directory creation rejected."
                )
        current = os.path.dirname(current)
    
    # Safe to create directory
    os.makedirs(path, exist_ok=exist_ok)


def safe_remove(filepath: str, base_dir: str) -> None:
    """
    Safely remove a file, preventing symlink attacks.
    
    Args:
        filepath: File to remove
        base_dir: Allowed base directory for symlinks
        
    Raises:
        SecurityError: If filepath is a symlink pointing outside base_dir
    """
    if not os.path.lexists(filepath):
        return
    
    # Check if filepath is a symlink
    if os.path.islink(filepath):
        link_target = os.readlink(filepath)
        
        # If target is relative, resolve it relative to the symlink's directory
        if not os.path.isabs(link_target):
            symlink_dir = os.path.dirname(os.path.abspath(filepath))
            link_target = os.path.join(symlink_dir, link_target)
        
        # Verify the symlink target is within the allowed base directory
        if not _is_path_within_base(link_target, base_dir):
            raise SecurityError(
                f"Security violation: Symlink '{filepath}' points outside allowed "
                f"directory to '{link_target}'. Remove rejected."
            )
    
    # Safe to remove
    os.remove(filepath)


def safe_rmtree(path: str, base_dir: str) -> None:
    """
    Safely remove a directory tree, preventing symlink attacks.
    
    This function will not follow symlinks when removing directories.
    
    Args:
        path: Directory to remove
        base_dir: Allowed base directory for symlinks
        
    Raises:
        SecurityError: If path or any subdirectory is a symlink pointing outside base_dir
    """
    if not os.path.exists(path) and not os.path.islink(path):
        return
    
    # Check if path itself is a symlink
    if os.path.islink(path):
        link_target = os.readlink(path)
        if not os.path.isabs(link_target):
            link_target = os.path.join(os.path.dirname(os.path.abspath(path)), link_target)
        if not _is_path_within_base(link_target, base_dir):
            raise SecurityError(
                f"Security violation: Directory '{path}' is a symlink pointing "
                f"outside allowed directory to '{link_target}'. Removal rejected."
            )
        # Safe symlink - remove it
        os.remove(path)
        return
    
    if os.path.isdir(path):
        # First check all items for dangerous symlinks
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            safe_rmtree(item_path, base_dir)
        # Remove the directory itself
        os.rmdir(path)
    else:
        safe_remove(path, base_dir)


# ============================================================================
# AVCPM DIRECTORY PROTECTION
# ============================================================================

def protect_avcpm_directory(base_dir: str = ".avcpm") -> None:
    """
    Protect the .avcpm directory from symlink attacks.
    
    This function:
    1. Verifies the base_dir is not a symlink
    2. Creates the base_dir if it doesn't exist
    3. Sets appropriate permissions
    
    Args:
        base_dir: Path to the AVCPM base directory (default: .avcpm)
        
    Raises:
        SecurityError: If base_dir is a symlink or cannot be secured
    """
    abs_base = os.path.abspath(base_dir)
    
    # Check if base_dir is a symlink
    if os.path.islink(base_dir):
        link_target = os.readlink(base_dir)
        raise SecurityError(
            f"Security violation: '{base_dir}' is a symlink pointing to "
            f"'{link_target}'. Remove the symlink and create a regular directory."
        )
    
    # Check parent directories for symlinks
    current = abs_base
    while current and current != os.path.dirname(current):
        if os.path.islink(current):
            link_target = os.readlink(current)
            raise SecurityError(
                f"Security violation: Parent directory '{current}' is a symlink "
                f"pointing to '{link_target}'. AVCPM directory cannot be secured."
            )
        current = os.path.dirname(current)
    
    # Create the directory if it doesn't exist
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
    elif not os.path.isdir(base_dir):
        raise SecurityError(
            f"Security violation: '{base_dir}' exists but is not a directory."
        )


def ensure_avcpm_directory_secure(base_dir: str = ".avcpm") -> str:
    """
    Ensure the .avcpm directory exists and is secure from symlink attacks.
    
    Args:
        base_dir: Path to the AVCPM base directory (default: .avcpm)
        
    Returns:
        The absolute path to the secured base directory
        
    Raises:
        SecurityError: If the directory cannot be secured
    """
    protect_avcpm_directory(base_dir)
    return os.path.abspath(base_dir)
