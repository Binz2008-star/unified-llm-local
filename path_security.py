"""
Central Path Security Module

Provides one authoritative path resolver for the entire repository.
All file operations must use this module to validate paths.

Security invariants:
- Rejects absolute paths when repository-relative paths are expected
- Rejects path traversal (..)
- Rejects paths escaping the repository root
- Rejects .git traversal
- Handles Windows-style drive paths
- Handles UNC paths
- Handles symlink chains
- Returns canonical Path inside allowed root
"""

import os
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional


class PathSecurityError(Exception):
    """Raised when a path violates security constraints."""

    pass


class PathResolver:
    """Central path resolver for repository security."""

    def __init__(self, root: Path):
        """
        Initialize the path resolver.

        Args:
            root: The allowed root directory. All resolved paths must be inside this.
        """
        self.root = root.resolve()

    def resolve(self, file_path: str, must_exist: bool = False) -> Path:
        """
        Validate and resolve a file path against the root directory.

        Args:
            file_path: The path to validate (relative to root)
            must_exist: If True, raise if the resolved path does not exist

        Returns:
            Canonical Path inside root

        Raises:
            PathSecurityError: If the path violates security constraints
        """
        if not file_path:
            raise PathSecurityError("Empty path not allowed")

        # Normalize path separators
        normalized = file_path.replace("\\", "/")

        # Check for null bytes
        if "\x00" in normalized:
            raise PathSecurityError(f"Null bytes not allowed in path: {file_path}")

        # Reject absolute paths
        if self._is_absolute(normalized):
            raise PathSecurityError(f"Absolute path not allowed: {file_path}")

        # Check for path traversal
        if ".." in normalized.split("/"):
            raise PathSecurityError(f"Path traversal not allowed: {file_path}")

        # Check for .git traversal
        parts = normalized.split("/")
        if any(part.lower() == ".git" for part in parts):
            raise PathSecurityError(f".git traversal not allowed: {file_path}")

        # Resolve the path
        p = Path(normalized)
        resolved = (self.root / p).resolve()

        # Verify the path is inside root using relative_to (more robust than string prefix)
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise PathSecurityError(f"Path escapes root directory: {file_path}")

        # Check for symlink escapes
        self._check_symlink_escape(resolved, file_path)

        if must_exist and not resolved.exists():
            raise PathSecurityError(f"Path does not exist: {file_path}")

        return resolved

    def _is_absolute(self, path: str) -> bool:
        """Check if a path is absolute, handling Windows and UNC paths."""
        # Unix absolute path
        if path.startswith("/"):
            return True

        # Windows absolute path (C:\, D:\, etc.)
        if re.match(r"^[a-zA-Z]:[\\/]", path):
            return True

        # Windows UNC path (\\server\share)
        if path.startswith("\\\\") or path.startswith("//"):
            return True

        return False

    def _check_symlink_escape(self, resolved: Path, original_path: str):
        """Check if a resolved path escapes the root through symlinks."""
        try:
            # Check each component of the path
            current = resolved
            while current != current.parent:
                if current.is_symlink():
                    # Resolve the symlink target
                    target = current.resolve()
                    try:
                        target.relative_to(self.root)
                    except ValueError:
                        raise PathSecurityError(
                            f"Symlink escape detected: {original_path} -> {target}"
                        )
                current = current.parent
        except OSError as e:
            raise PathSecurityError(f"Error checking symlinks: {e}")

    def validate_file_path(self, file_path: str) -> bool:
        """
        Validate a file path without resolving.

        Returns True if valid, raises PathSecurityError otherwise.
        """
        self.resolve(file_path)
        return True

    def safe_join(self, *parts: str) -> Path:
        """
        Safely join path parts and validate against root.

        Args:
            *parts: Path components to join

        Returns:
            Validated Path inside root
        """
        joined = "/".join(parts)
        return self.resolve(joined)

    def get_relative_path(self, absolute_path: Path) -> str:
        """
        Get a relative path from root for an absolute path.

        Args:
            absolute_path: Absolute path to convert

        Returns:
            Relative path string

        Raises:
            PathSecurityError: If the path is outside root
        """
        resolved = absolute_path.resolve()
        try:
            return str(resolved.relative_to(self.root))
        except ValueError:
            raise PathSecurityError(f"Path is outside root: {absolute_path}")


# Global resolver instance - initialized with the second-brain repository root
_resolver: Optional[PathResolver] = None


def init_resolver(root: Path) -> PathResolver:
    """Initialize the global path resolver."""
    global _resolver
    _resolver = PathResolver(root)
    return _resolver


def get_resolver() -> PathResolver:
    """Get the global path resolver."""
    global _resolver
    if _resolver is None:
        # Default to the directory containing this module
        _resolver = PathResolver(Path(__file__).parent)
    return _resolver


def resolve(file_path: str, must_exist: bool = False) -> Path:
    """
    Convenience function to resolve a path using the global resolver.

    Args:
        file_path: The path to validate
        must_exist: If True, raise if path doesn't exist

    Returns:
        Validated Path
    """
    return get_resolver().resolve(file_path, must_exist=must_exist)


def validate_path(file_path: str) -> bool:
    """
    Convenience function to validate a path using the global resolver.

    Returns True if valid, raises PathSecurityError otherwise.
    """
    return get_resolver().validate_file_path(file_path)
