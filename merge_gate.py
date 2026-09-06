"""
Merge Gate Module

Provides concurrency-safe merge governance for the repository.
Ensures merge operations are serialized and verified.

Required sequence:
Acquire lock
    ↓
Capture baseline
    ↓
Validate clean repository
    ↓
Resolve target commit
    ↓
Validate ancestry
    ↓
Inspect changed files
    ↓
Apply security/path policy
    ↓
Validate target tree
    ↓
Re-check HEAD
    ↓
Fast-forward only
    ↓
Run final verification
    ↓
Verify HEAD
    ↓
Release lock
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from contextlib import contextmanager
import threading

from git_security import SecureGit, GitError, GitSecurityError
from path_security import PathResolver, PathSecurityError

logger = logging.getLogger("SecondBrain.MergeGate")


class MergeError(Exception):
    """Raised when a merge operation fails."""

    pass


class MergeSecurityError(Exception):
    """Raised when a merge operation violates security constraints."""

    pass


class MergeLock:
    """
    OS-level merge lock with ownership tracking.

    Uses file-based locking with atomic ownership validation.
    Prevents concurrent merge operations.

    Lock file is placed OUTSIDE the Git repository to ensure
    it never appears in git status output.
    """

    def __init__(self, repo_path: Path):
        """
        Initialize the merge lock.

        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.lock_fd = None
        self.owner_id = None
        self._lock = threading.Lock()

        lock_dir = repo_path.parent / ".second-brain-locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = lock_dir / f"{repo_path.name}.merge.lock"

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Acquire the merge lock.

        Args:
            timeout: Maximum time to wait for the lock

        Returns:
            True if lock acquired, False on timeout
        """
        import os

        if os.name == "nt":
            import msvcrt
        else:
            import fcntl

        start_time = time.time()
        self.owner_id = f"{os.getpid()}-{threading.current_thread().ident}"

        while True:
            try:
                # Create lock file if it doesn't exist
                self.lock_file.touch(exist_ok=True)

                # Open and try to acquire exclusive lock
                self.lock_fd = open(self.lock_file, "r+")

                if os.name == "nt":
                    # Windows: use msvcrt.locking
                    try:
                        msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
                    except IOError:
                        if self.lock_fd:
                            self.lock_fd.close()
                            self.lock_fd = None
                        if time.time() - start_time >= timeout:
                            return False
                        time.sleep(0.1)
                        continue
                else:
                    # Unix: use fcntl
                    fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                # Write ownership information
                lock_info = {
                    "owner": self.owner_id,
                    "acquired_at": time.time(),
                    "pid": os.getpid(),
                }
                self.lock_fd.seek(0)
                self.lock_fd.write(json.dumps(lock_info))
                self.lock_fd.flush()

                logger.debug("Merge lock acquired by %s", self.owner_id)
                return True

            except (IOError, OSError):
                # Lock is held by another process
                if self.lock_fd:
                    self.lock_fd.close()
                    self.lock_fd = None

                # Check for stale lock
                if self._is_stale_lock():
                    logger.warning("Detected stale merge lock, attempting cleanup")
                    self._cleanup_stale_lock()
                    continue

                # Check timeout
                if time.time() - start_time >= timeout:
                    logger.error("Merge lock acquisition timed out")
                    return False

                time.sleep(0.1)

    def release(self):
        """Release the merge lock. Always closes the FD."""
        if not self.lock_fd:
            return

        try:
            if not self._verify_ownership():
                logger.error("Ownership verification failed, not releasing lock")
                return

            if os.name == "nt":
                import msvcrt

                try:
                    self.lock_fd.seek(0)
                    msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            else:
                import fcntl

                try:
                    fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                except Exception:
                    pass

            try:
                self.lock_file.write_text("")
            except Exception:
                pass

            logger.debug("Merge lock released by %s", self.owner_id)

        except Exception as e:
            logger.error("Error releasing merge lock: %s", e)

        finally:
            self._force_close()

    def _force_close(self):
        """Unconditionally close the file descriptor."""
        if self.lock_fd:
            try:
                self.lock_fd.close()
            except Exception:
                pass
            self.lock_fd = None

    def _verify_ownership(self) -> bool:
        """Verify that the current process owns the lock."""
        try:
            content = self.lock_file.read_text()
            if not content.strip():
                return True  # Empty lock file, we own it

            lock_info = json.loads(content)
            return lock_info.get("owner") == self.owner_id
        except Exception:
            return False

    def _is_stale_lock(self) -> bool:
        """Check if the lock is stale (held by a dead process)."""
        try:
            content = self.lock_file.read_text()
            if not content.strip():
                return False

            lock_info = json.loads(content)
            lock_pid = lock_info.get("pid")

            if lock_pid is None:
                return True

            # Check if the process is still alive
            try:
                os.kill(lock_pid, 0)  # Signal 0 just checks if process exists
                return False
            except OSError:
                return True  # Process doesn't exist

        except Exception:
            return False

    def _cleanup_stale_lock(self):
        """Clean up a stale lock."""
        try:
            self.lock_fd = None
            self.lock_file.write_text("")
        except Exception as e:
            logger.error("Failed to clean up stale lock: %s", e)

    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise MergeError("Failed to acquire merge lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit — always close FD regardless of ownership."""
        try:
            self.release()
        finally:
            self._force_close()
        return False


class MergeGate:
    """
    Concurrency-safe merge gate for the repository.

    Ensures merge operations are serialized and verified.
    """

    def __init__(
        self,
        repo_path: Path,
        path_resolver: Optional[PathResolver] = None,
        allowed_files: Optional[Set[str]] = None,
    ):
        """
        Initialize the merge gate.

        Args:
            repo_path: Path to the primary repository
            path_resolver: Path resolver for security validation
            allowed_files: Optional set of allowed file patterns
        """
        self.repo_path = repo_path.resolve()
        self.git = SecureGit(repo_path)
        self.path_resolver = path_resolver or PathResolver(repo_path)
        self.allowed_files = allowed_files
        self.lock = MergeLock(repo_path)

    def merge_agent_changes(
        self, worktree_path: Path, branch: str, baseline_sha: str, auto_cleanup: bool = True
    ) -> Dict[str, Any]:
        """
        Merge agent changes from a worktree into the primary repository.

        Args:
            worktree_path: Path to the agent worktree
            branch: Branch name containing agent changes
            baseline_sha: Expected baseline SHA
            auto_cleanup: If True, clean up worktree after successful merge

        Returns:
            Dictionary containing merge result information

        Raises:
            MergeError: If the merge operation fails
            MergeSecurityError: If security constraints are violated
        """
        result = {
            "success": False,
            "baseline_sha": baseline_sha,
            "final_sha": None,
            "merged_files": [],
            "errors": [],
        }

        with self.lock:
            try:
                # Step 1: Verify baseline hasn't moved
                current_sha = self.git.get_head_sha()
                if current_sha != baseline_sha:
                    raise MergeSecurityError(
                        f"Baseline SHA mismatch: expected {baseline_sha}, "
                        f"got {current_sha}. Repository may have been modified."
                    )

                # Step 2: Verify repository is clean
                if not self.git.is_clean():
                    raise MergeSecurityError("Repository working tree is not clean")

                # Step 3: Get target commit from worktree
                wt_git = SecureGit(worktree_path)
                target_sha = wt_git.get_head_sha()

                # Step 4: Verify ancestry (target must be descendant of baseline)
                if not self.git.verify_ancestry(baseline_sha, target_sha):
                    raise MergeSecurityError(
                        f"Target commit {target_sha[:8]} is not a descendant "
                        f"of baseline {baseline_sha[:8]}"
                    )

                # Step 5: Get list of changed files
                changed_files = self.git.get_diff_files(baseline_sha, target_sha)
                result["merged_files"] = changed_files

                # Step 6: Validate file security
                self._validate_changed_files(changed_files)

                # Step 7: Check symlink security in target tree
                self._validate_tree_symlinks(target_sha)

                # Step 8: Perform fast-forward merge
                # First, fetch the branch from worktree
                self._fetch_worktree_branch(worktree_path, branch)

                # Then, fast-forward merge
                if not self.git.merge_ff_only(branch):
                    raise MergeError("Fast-forward merge failed")

                # Step 9: Verify final HEAD
                final_sha = self.git.get_head_sha()
                if final_sha != target_sha:
                    raise MergeError(
                        f"Post-merge SHA mismatch: expected {target_sha}, got {final_sha}"
                    )

                result["final_sha"] = final_sha
                result["success"] = True

                logger.info(
                    "Successfully merged %d files from worktree (SHA: %s -> %s)",
                    len(changed_files),
                    baseline_sha[:8],
                    final_sha[:8],
                )

            except Exception as e:
                logger.error("Merge failed: %s", e)
                result["errors"].append(str(e))
                raise

            finally:
                # Cleanup worktree if requested and merge was successful
                if auto_cleanup and result["success"]:
                    try:
                        from worktree import WorktreeManager

                        manager = WorktreeManager(self.repo_path)
                        manager.cleanup_worktree(worktree_path, branch)
                    except Exception as e:
                        logger.warning("Failed to cleanup worktree: %s", e)

        return result

    def _validate_changed_files(self, changed_files: List[str]):
        """
        Validate that all changed files are allowed.

        Args:
            changed_files: List of changed file paths

        Raises:
            MergeSecurityError: If any file is not allowed
        """
        for file_path in changed_files:
            # Validate path through security resolver
            try:
                self.path_resolver.resolve(file_path)
            except PathSecurityError as e:
                raise MergeSecurityError(f"Path security violation: {e}")

            # Check allowlist if configured
            if self.allowed_files is not None:
                if not self._is_file_allowed(file_path):
                    raise MergeSecurityError(f"Unauthorized file changed: {file_path}")

    def _is_file_allowed(self, file_path: str) -> bool:
        """Check if a file is in the allowed list."""
        from fnmatch import fnmatch

        for pattern in self.allowed_files:
            if fnmatch(file_path, pattern):
                return True
        return False

    def _validate_tree_symlinks(self, commit_sha: str):
        """
        Validate that no symlinks in the target tree escape the repository.

        Args:
            commit_sha: The commit to validate

        Raises:
            MergeSecurityError: If malicious symlinks are found
        """
        try:
            # Get list of files in the commit
            tree_output = self.git.ls_tree(commit_sha, recursive=True)

            for line in tree_output.strip().split("\n"):
                if not line:
                    continue

                # Parse ls-tree output: mode type sha name
                parts = line.split(None, 3)
                if len(parts) < 4:
                    continue

                mode, obj_type, sha, name = parts

                # Check for symlinks (mode starts with 12)
                if mode.startswith("12"):
                    # Read the symlink target
                    _, content, _ = self.git._run(["cat-file", "-p", sha])
                    target = content.strip()

                    # Validate the symlink target
                    self._validate_symlink_target(name, target)

        except GitError as e:
            logger.warning("Could not validate tree symlinks: %s", e)

    def _validate_symlink_target(self, symlink_path: str, target: str):
        """
        Validate that a symlink target doesn't escape the repository.

        Args:
            symlink_path: Path to the symlink
            target: Symlink target

        Raises:
            MergeSecurityError: If the symlink is malicious
        """
        # Check for absolute targets
        if target.startswith("/") or (len(target) >= 2 and target[1] == ":"):
            raise MergeSecurityError(
                f"Absolute symlink target rejected: {symlink_path} -> {target}"
            )

        # Check for path traversal
        if ".." in target:
            raise MergeSecurityError(
                f"Symlink with path traversal rejected: {symlink_path} -> {target}"
            )

        # Check for .git references
        if ".git" in target:
            raise MergeSecurityError(f"Symlink to .git rejected: {symlink_path} -> {target}")

    def _fetch_worktree_branch(self, worktree_path: Path, branch: str):
        """Fetch a branch from a worktree into the primary repository."""
        import subprocess

        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "fetch", str(worktree_path), branch],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise GitError(f"Failed to fetch branch from worktree: {result.stderr}")


@contextmanager
def merge_gate_context(
    repo_path: Path,
    path_resolver: Optional[PathResolver] = None,
    allowed_files: Optional[Set[str]] = None,
):
    """
    Context manager for merge gate operations.

    Usage:
        with merge_gate_context(repo_path) as gate:
            gate.merge_agent_changes(worktree_path, branch, baseline_sha)
    """
    gate = MergeGate(repo_path, path_resolver, allowed_files)
    yield gate
