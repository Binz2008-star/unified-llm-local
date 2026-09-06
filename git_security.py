"""
Secure Git Operations Module

Provides centralized, secure Git command execution.
All Git commands must use this module to ensure security.

Security requirements:
- All commands use argument arrays (never shell=True)
- Explicit repository/worktree location
- Interactive prompts disabled
- Timeouts configured
- Output captured
- Return codes validated
- Dangerous options rejected
- User-controlled values validated
"""

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger("SecondBrain.GitSecurity")


class GitError(Exception):
    """Raised when a Git operation fails."""

    pass


class GitSecurityError(Exception):
    """Raised when a Git operation violates security constraints."""

    pass


# Dangerous Git options that should never be used in automated execution
DANGEROUS_OPTIONS = {
    "--hard",
    "--cleanup=always",
    "--abort",
    "reset",  # when used as subcommand without proper validation
}

# Patterns for malicious branch/ref names
MALICIOUS_REF_PATTERNS = [
    r"\.\.",  # Path traversal
    r"[~^:?\*\[\]\\]",  # Shell special characters
    r"^-",  # Starts with dash (could be interpreted as option)
    r"@{",  # Reflog syntax
    r"\s",  # Whitespace
    r"\x00",  # Null byte
]


class SecureGit:
    """Secure Git operations wrapper."""

    def __init__(self, repo_path: Path, timeout: int = 60):
        """
        Initialize secure Git operations.

        Args:
            repo_path: Path to the Git repository
            timeout: Command timeout in seconds
        """
        self.repo_path = repo_path.resolve()
        self.timeout = timeout

        # Verify this is a Git repository
        if not (self.repo_path / ".git").exists():
            raise GitError(f"Not a Git repository: {self.repo_path}")

    def _run(self, args: list[str], check: bool = True) -> tuple[int, str, str]:
        """
        Run a Git command securely.

        Args:
            args: Git command arguments (without 'git' prefix)
            check: If True, raise on non-zero exit code

        Returns:
            Tuple of (return_code, stdout, stderr)

        Raises:
            GitSecurityError: If the command contains dangerous options
            GitError: If the command fails
        """
        # Validate no dangerous options
        self._validate_args(args)

        # Build full command
        cmd = ["git", "-C", str(self.repo_path)] + args

        logger.debug("Running git: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={
                    "GIT_TERMINAL_PROMPT": "0",  # Disable interactive prompts
                    "GIT_ASKPASS": "echo",  # Disable credential helper
                    "GIT_EDITOR": "true",  # Disable editor
                    "EDITOR": "true",
                },
            )

            if check and result.returncode != 0:
                raise GitError(
                    f"Git command failed: {' '.join(args)}\n"
                    f"Exit code: {result.returncode}\n"
                    f"Stderr: {result.stderr[:1000]}"
                )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            raise GitError(f"Git command timed out after {self.timeout}s: {' '.join(args)}")
        except FileNotFoundError:
            raise GitError("Git executable not found")

    def _validate_args(self, args: list[str]):
        """Validate Git command arguments for security."""
        for arg in args:
            # Check for dangerous options
            if arg in DANGEROUS_OPTIONS:
                raise GitSecurityError(f"Dangerous Git option rejected: {arg}")

            # Check for option injection (starts with -)
            if arg.startswith("-") and arg not in ("--", "-"):
                # Allow numeric args like -5 (for log count)
                if re.match(r"^-\d+$", arg):
                    continue

                # Allow common safe options
                safe_options = {
                    "--oneline",
                    "--short",
                    "--porcelain",
                    "--porcelain=v1",
                    "--json",
                    "--name-only",
                    "--name-status",
                    "--stat",
                    "--all",
                    "--branch",
                    "--list",
                    "--show",
                    "--format",
                    "--no-color",
                    "--no-pager",
                    "--ff-only",
                    "--no-ff",
                    "--squash",
                    "--set-upstream",
                    "--unset-upstream",
                    "--track",
                    "--no-track",
                    "--depth",
                    "--shallow",
                    "--work-tree",
                    "--git-dir",
                    "--show-current",
                    "--no-renames",
                    "--force-with-lease",
                    "--is-ancestor",
                    "-C",
                    "-c",
                    "-m",
                    "-r",
                    "-a",
                    "-p",
                    "-A",
                    "-u",
                }
                if arg not in safe_options:
                    raise GitSecurityError(f"Potentially dangerous option rejected: {arg}")

    def _validate_ref(self, ref: str):
        """Validate a Git ref name for security."""
        for pattern in MALICIOUS_REF_PATTERNS:
            if re.search(pattern, ref):
                raise GitSecurityError(f"Malicious ref name rejected: {ref}")

    def get_head_sha(self) -> str:
        """Get the current HEAD commit SHA."""
        _, stdout, _ = self._run(["rev-parse", "HEAD"])
        return stdout.strip()

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        _, stdout, _ = self._run(["branch", "--show-current"], check=False)
        return stdout.strip()

    def get_status(self, porcelain: bool = True) -> str:
        """Get Git status."""
        args = ["status"]
        if porcelain:
            args.append("--porcelain=v1")
        _, stdout, _ = self._run(args)
        return stdout

    def get_diff(self, base: str = "HEAD", target: str = None, name_only: bool = False) -> str:
        """Get diff between commits."""
        args = ["diff"]
        if name_only:
            args.append("--name-only")
        args.append(base)
        if target:
            args.append(target)
        _, stdout, _ = self._run(args)
        return stdout

    def get_diff_files(self, base: str, target: str = None) -> list[str]:
        """Get list of changed files between commits."""
        args = ["diff", "--name-only", base]
        if target:
            args.append(target)
        _, stdout, _ = self._run(args)
        return [f for f in stdout.strip().split("\n") if f]

    def create_branch(self, branch_name: str) -> bool:
        """Create a new branch from current HEAD."""
        self._validate_ref(branch_name)
        try:
            self._run(["branch", branch_name])
            return True
        except GitError:
            return False

    def checkout(self, ref: str, create: bool = False) -> bool:
        """Checkout a ref."""
        self._validate_ref(ref)
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(ref)
        try:
            self._run(args)
            return True
        except GitError:
            return False

    def commit(self, message: str, allow_empty: bool = False) -> str:
        """Create a commit and return the new HEAD SHA."""
        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
        self._run(args)
        return self.get_head_sha()

    def add_all(self) -> bool:
        """Stage all changes."""
        try:
            self._run(["add", "-A"])
            return True
        except GitError:
            return False

    def merge_ff_only(self, branch: str) -> bool:
        """Fast-forward merge a branch."""
        self._validate_ref(branch)
        try:
            self._run(["merge", "--ff-only", branch])
            return True
        except GitError:
            return False

    def log(self, count: int = 10, oneline: bool = False) -> str:
        """Get Git log."""
        args = ["log", f"-{count}"]
        if oneline:
            args.append("--oneline")
        _, stdout, _ = self._run(args)
        return stdout

    def is_clean(self) -> bool:
        """Check if working tree is clean."""
        status = self.get_status(porcelain=True)
        return len(status.strip()) == 0

    def stash(self) -> bool:
        """Stash current changes."""
        try:
            self._run(["stash"])
            return True
        except GitError:
            return False

    def stash_pop(self) -> bool:
        """Pop the most recent stash."""
        try:
            self._run(["stash", "pop"])
            return True
        except GitError:
            return False

    def worktree_list(self) -> list[str]:
        """List all worktrees."""
        _, stdout, _ = self._run(["worktree", "list"])
        return [line.split()[0] for line in stdout.strip().split("\n") if line]

    def worktree_add(self, path: Path, branch: str) -> bool:
        """Add a new worktree."""
        self._validate_ref(branch)
        try:
            self._run(["worktree", "add", str(path), branch])
            return True
        except GitError:
            return False

    def worktree_remove(self, path: Path, force: bool = False) -> bool:
        """Remove a worktree."""
        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(path))
        try:
            self._run(args)
            return True
        except GitError:
            return False

    def ls_tree(self, ref: str = "HEAD", recursive: bool = False) -> str:
        """List tree contents."""
        args = ["ls-tree"]
        if recursive:
            args.append("-r")
        args.append(ref)
        _, stdout, _ = self._run(args)
        return stdout

    def rev_parse(self, ref: str) -> str:
        """Parse a ref to a SHA."""
        self._validate_ref(ref)
        _, stdout, _ = self._run(["rev-parse", ref])
        return stdout.strip()

    def verify_ancestry(self, ancestor: str, descendant: str) -> bool:
        """Verify that ancestor is an ancestor of descendant."""
        try:
            self._run(["merge-base", "--is-ancestor", ancestor, descendant])
            return True
        except GitError:
            return False


def get_secure_git(repo_path: Path, timeout: int = 60) -> SecureGit:
    """Create a SecureGit instance."""
    return SecureGit(repo_path, timeout)
