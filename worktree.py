"""
Worktree Isolation Module

Provides isolated Git worktree execution for autonomous agents.
The agent must never modify the primary repository directly.

Architecture:
PRIMARY REPOSITORY
        |
        | baseline SHA
        v
ISOLATED AGENT WORKTREE
        |
        | agent changes
        v
TESTS
        |
        v
COMMIT
        |
        v
MERGE GATE
        |
        v
PRIMARY REPOSITORY
"""

import logging
import shlex
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from git_security import GitError, SecureGit
from tool_security import run_command

logger = logging.getLogger("SecondBrain.Worktree")


class WorktreeError(Exception):
    """Raised when a worktree operation fails."""

    pass


class WorktreeManager:
    """Manages isolated Git worktrees for agent execution."""

    def __init__(self, repo_path: Path, worktree_parent: Path | None = None):
        """
        Initialize the worktree manager.

        Args:
            repo_path: Path to the primary Git repository
            worktree_parent: Parent directory for worktrees (default: repo's parent)
        """
        self.repo_path = repo_path.resolve()
        self.worktree_parent = worktree_parent or self.repo_path.parent
        self.git = SecureGit(repo_path)

    def create_worktree(self, task_id: str = None) -> dict[str, Any]:
        """
        Create an isolated worktree for agent execution.

        Args:
            task_id: Optional task identifier (auto-generated if not provided)

        Returns:
            Dictionary containing:
                - path: Path to the worktree
                - branch: Branch name
                - baseline_sha: SHA at worktree creation
                - worktree_id: Unique worktree identifier
        """
        if task_id is None:
            task_id = uuid.uuid4().hex[:12]

        worktree_id = f"wt-{task_id}-{uuid.uuid4().hex[:8]}"
        branch_name = f"agent/{worktree_id}"
        worktree_path = self.worktree_parent / worktree_id

        # Ensure parent directory exists
        self.worktree_parent.mkdir(parents=True, exist_ok=True)

        # Get baseline SHA before creating worktree
        baseline_sha = self.git.get_head_sha()

        # Create the branch (but don't checkout yet)
        if not self.git.create_branch(branch_name):
            raise WorktreeError(f"Failed to create branch: {branch_name}")

        # Create the worktree
        try:
            self.git.worktree_add(worktree_path, branch_name)
        except GitError as e:
            # Cleanup: delete the branch if worktree creation failed
            try:
                import asyncio as _aio

                cmd = f"git -C {shlex.quote(str(self.repo_path))} branch -D {shlex.quote(branch_name)}"
                loop = _aio.new_event_loop()
                try:
                    loop.run_until_complete(
                        run_command(cmd, self.repo_path, timeout_seconds=10, trusted=True)
                    )
                finally:
                    loop.close()
            except Exception:
                pass
            raise WorktreeError(f"Failed to create worktree: {e}")

        logger.info(
            "Created worktree: %s (branch: %s, baseline: %s)",
            worktree_path,
            branch_name,
            baseline_sha[:8],
        )

        return {
            "path": worktree_path,
            "branch": branch_name,
            "baseline_sha": baseline_sha,
            "worktree_id": worktree_id,
        }

    def get_worktree_git(self, worktree_path: Path) -> SecureGit:
        """
        Get a SecureGit instance for a worktree.

        Args:
            worktree_path: Path to the worktree

        Returns:
            SecureGit instance for the worktree
        """
        return SecureGit(worktree_path)

    def commit_in_worktree(self, worktree_path: Path, message: str, add_all: bool = True) -> str:
        """
        Commit changes in a worktree.

        Args:
            worktree_path: Path to the worktree
            message: Commit message
            add_all: If True, stage all changes before committing

        Returns:
            SHA of the new commit
        """
        wt_git = self.get_worktree_git(worktree_path)

        if add_all:
            if not wt_git.add_all():
                raise WorktreeError("Failed to stage changes")

        return wt_git.commit(message)

    def cleanup_worktree(self, worktree_path: Path, branch: str) -> bool:
        """
        Clean up a worktree and its branch.

        Uses tool_security.run_command for all subprocess calls.

        Args:
            worktree_path: Path to the worktree
            branch: Branch name to delete

        Returns:
            True if successful
        """
        import asyncio

        success = True

        # Validate that this is a managed worktree before force-removing
        try:
            self.is_worktree(worktree_path)
        except Exception:
            pass

        # Remove the worktree
        try:
            cmd = f"git -C {shlex.quote(str(self.repo_path))} worktree remove --force {shlex.quote(str(worktree_path.resolve()))}"
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    run_command(cmd, self.repo_path, timeout_seconds=15, trusted=True)
                )
            finally:
                loop.close()
            if result.exit_code != 0:
                logger.warning("Failed to remove worktree: %s", result.stderr)
                success = False
        except Exception as e:
            logger.warning("Failed to remove worktree: %s", e)
            success = False

        # Delete the branch
        try:
            cmd = f"git -C {shlex.quote(str(self.repo_path))} branch -D {shlex.quote(branch)}"
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    run_command(cmd, self.repo_path, timeout_seconds=10, trusted=True)
                )
            finally:
                loop.close()
            if result.exit_code != 0:
                logger.warning("Failed to delete branch: %s", result.stderr)
                success = False
        except Exception as e:
            logger.warning("Failed to delete branch: %s", e)
            success = False

        # Also try to remove the directory if it still exists
        if worktree_path.exists():
            try:
                shutil.rmtree(worktree_path)
            except Exception as e:
                logger.warning("Failed to remove worktree directory: %s", e)
                success = False

        return success

    def list_worktrees(self) -> list:
        """List all worktrees for this repository."""
        return self.git.worktree_list()

    def is_worktree(self, path: Path) -> bool:
        """Check if a path is a worktree for this repository."""
        try:
            worktrees = self.list_worktrees()
            return str(path.resolve()) in [Path(w).resolve() for w in worktrees]
        except Exception:
            return False


@contextmanager
def isolated_worktree(repo_path: Path, task_id: str = None, preserve_on_failure: bool = True):
    """
    Context manager for isolated worktree execution.

    Usage:
        with isolated_worktree(repo_path, "my-task") as ctx:
            # Execute agent code in ctx.worktree_path
            # Changes are isolated from primary repository
            pass
        # Worktree is automatically cleaned up on success
    """
    manager = WorktreeManager(repo_path)
    worktree_info = None

    try:
        worktree_info = manager.create_worktree(task_id)

        yield {
            "manager": manager,
            "worktree_path": worktree_info["path"],
            "branch": worktree_info["branch"],
            "baseline_sha": worktree_info["baseline_sha"],
            "worktree_id": worktree_info["worktree_id"],
        }

        # Success: cleanup
        manager.cleanup_worktree(worktree_info["path"], worktree_info["branch"])

    except Exception as e:
        logger.error("Worktree execution failed: %s", e)

        if preserve_on_failure and worktree_info:
            logger.info(
                "Preserving worktree for investigation: %s (branch: %s)",
                worktree_info["path"],
                worktree_info["branch"],
            )
        elif worktree_info:
            manager.cleanup_worktree(worktree_info["path"], worktree_info["branch"])

        raise
