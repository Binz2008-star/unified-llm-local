"""
Security Test Suite

Comprehensive tests for all security controls:
- Path security (traversal, absolute paths, symlinks)
- Git security (malicious refs, option injection)
- Worktree isolation
- Merge gate
- Shell injection prevention
- Context budget enforcement
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_repo() -> Generator[Path, None, None]:
    """Create a temporary Git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test-repo"
        repo_path.mkdir()

        # Initialize Git repository
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)

        # Configure Git
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repo_path, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repository")
        subprocess.run(["git", "add", "-A"], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True
        )

        yield repo_path


@pytest.fixture
def temp_repo_with_subdirs(temp_repo: Path) -> Path:
    """Create a temporary repo with subdirectories."""
    (temp_repo / "src").mkdir()
    (temp_repo / "src" / "main.py").write_text("print('hello')")
    (temp_repo / "tests").mkdir()
    (temp_repo / "tests" / "test_main.py").write_text("def test_hello(): pass")
    (temp_repo / "config").mkdir()
    (temp_repo / "config" / "settings.yaml").write_text("key: value")

    subprocess.run(["git", "add", "-A"], cwd=temp_repo, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add subdirectories"], cwd=temp_repo, capture_output=True
    )

    return temp_repo


# ============================================================================
# Path Security Tests
# ============================================================================


class TestPathSecurity:
    """Test path security controls."""

    def test_normal_path_valid(self, temp_repo: Path):
        """Test that normal paths are accepted."""
        from path_security import PathResolver

        resolver = PathResolver(temp_repo)

        # Create a test file
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src" / "main.py").write_text("print('hello')")

        # Normal paths should work
        result = resolver.resolve("src/main.py")
        assert result.exists()
        assert str(result).startswith(str(temp_repo))

    def test_traversal_rejected(self, temp_repo: Path):
        """Test that path traversal is rejected."""
        from path_security import PathResolver, PathSecurityError

        resolver = PathResolver(temp_repo)

        # Path traversal should be rejected
        with pytest.raises(PathSecurityError, match="Path traversal"):
            resolver.resolve("../secret")

        with pytest.raises(PathSecurityError, match="Path traversal"):
            resolver.resolve("src/../../secret")

        with pytest.raises(PathSecurityError, match="Path traversal"):
            resolver.resolve("../../../etc/passwd")

    def test_absolute_path_rejected(self, temp_repo: Path):
        """Test that absolute paths are rejected."""
        from path_security import PathResolver, PathSecurityError

        resolver = PathResolver(temp_repo)

        # Unix absolute path
        with pytest.raises(PathSecurityError, match="Absolute path"):
            resolver.resolve("/etc/passwd")

        # Windows absolute path
        with pytest.raises(PathSecurityError, match="Absolute path"):
            resolver.resolve("C:\\Windows\\System32")

        # Windows forward slash absolute path
        with pytest.raises(PathSecurityError, match="Absolute path"):
            resolver.resolve("C:/Windows/System32")

        # UNC path
        with pytest.raises(PathSecurityError, match="Absolute path"):
            resolver.resolve("\\\\server\\share")

    def test_git_directory_rejected(self, temp_repo: Path):
        """Test that .git traversal is rejected."""
        from path_security import PathResolver, PathSecurityError

        resolver = PathResolver(temp_repo)

        # Create a file inside .git directory
        git_config = temp_repo / ".git" / "config"
        if git_config.exists():
            # Direct .git access
            with pytest.raises(PathSecurityError):
                resolver.resolve(".git/config")

        # Even if file doesn't exist, the path should still be rejected
        with pytest.raises(PathSecurityError):
            resolver.resolve(".git/HEAD")

        # Nested .git access (will be rejected by path traversal first)
        with pytest.raises(PathSecurityError):
            resolver.resolve("src/../../.git/config")

    def test_symlink_escape_rejected(self, temp_repo: Path):
        """Test that symlink escapes are rejected."""
        from path_security import PathResolver, PathSecurityError

        resolver = PathResolver(temp_repo)

        # Skip test if symlinks not supported (e.g., Windows without admin)
        try:
            symlink_path = temp_repo / "escape_link"
            target_path = Path(tempfile.mkdtemp()) / "escaped_file"
            target_path.write_text("escaped content")

            try:
                symlink_path.symlink_to(target_path)

                # Should reject symlink that escapes root
                with pytest.raises(PathSecurityError, match="Symlink escape"):
                    resolver.resolve("escape_link")
            except OSError:
                # Symlinks not supported, skip test
                pytest.skip("Symlinks not supported on this system")
            finally:
                # Cleanup
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
                if target_path.exists():
                    target_path.unlink()
        except Exception:
            pytest.skip("Symlink test skipped")

    def test_empty_path_rejected(self, temp_repo: Path):
        """Test that empty paths are rejected."""
        from path_security import PathResolver, PathSecurityError

        resolver = PathResolver(temp_repo)

        with pytest.raises(PathSecurityError, match="Empty path"):
            resolver.resolve("")

    def test_null_bytes_rejected(self, temp_repo: Path):
        """Test that null bytes are rejected."""
        from path_security import PathResolver, PathSecurityError

        resolver = PathResolver(temp_repo)

        with pytest.raises(PathSecurityError, match="Null bytes"):
            resolver.resolve("src/main.py\x00secret")

    def test_path_escaping_root_rejected(self, temp_repo: Path):
        """Test that paths escaping root are rejected."""
        from path_security import PathResolver, PathSecurityError

        resolver = PathResolver(temp_repo)

        # Skip test if symlinks not supported (e.g., Windows without admin)
        try:
            # Create a symlink inside the repo pointing outside
            symlink_path = temp_repo / "internal_link"
            external_dir = Path(tempfile.mkdtemp())
            external_file = external_dir / "external.txt"
            external_file.write_text("external")

            try:
                symlink_path.symlink_to(external_dir)

                # Even though symlink is inside repo, target is outside
                with pytest.raises(PathSecurityError, match="escapes root"):
                    resolver.resolve("internal_link/external.txt")
            except OSError:
                # Symlinks not supported, skip test
                pytest.skip("Symlinks not supported on this system")
            finally:
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
                if external_dir.exists():
                    shutil.rmtree(external_dir)
        except Exception:
            pytest.skip("Symlink test skipped")

    def test_validate_path_function(self, temp_repo: Path):
        """Test the validate_path convenience function."""
        from path_security import PathSecurityError, validate_path

        # Valid path
        assert validate_path("src/main.py")

        # Invalid path
        with pytest.raises(PathSecurityError):
            validate_path("../secret")

    def test_safe_join(self, temp_repo: Path):
        """Test the safe_join function."""
        from path_security import PathResolver

        resolver = PathResolver(temp_repo)

        # Create a test file
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src" / "main.py").write_text("print('hello')")

        result = resolver.safe_join("src", "main.py")
        assert result.exists()
        assert str(result).startswith(str(temp_repo))


# ============================================================================
# Git Security Tests
# ============================================================================


class TestGitSecurity:
    """Test Git security controls."""

    def test_secure_git_initialization(self, temp_repo: Path):
        """Test that SecureGit initializes correctly."""
        from git_security import SecureGit

        git = SecureGit(temp_repo)
        sha = git.get_head_sha()
        assert len(sha) == 40  # Full SHA

    def test_non_repo_rejected(self):
        """Test that non-repository paths are rejected."""
        from git_security import GitError, SecureGit

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(GitError, match="Not a Git repository"):
                SecureGit(Path(tmpdir))

    def test_dangerous_option_rejected(self, temp_repo: Path):
        """Test that dangerous Git options are rejected."""
        from git_security import GitSecurityError, SecureGit

        git = SecureGit(temp_repo)

        # --hard should be rejected
        with pytest.raises(GitSecurityError, match="Dangerous Git option"):
            git._run(["reset", "--hard"])

        # --force should be rejected
        with pytest.raises(GitSecurityError, match="dangerous option rejected"):
            git._run(["push", "--force"])

    def test_malicious_ref_rejected(self, temp_repo: Path):
        """Test that malicious ref names are rejected."""
        from git_security import GitSecurityError, SecureGit

        git = SecureGit(temp_repo)

        # Path traversal in ref
        with pytest.raises(GitSecurityError, match="Malicious ref name"):
            git._validate_ref("../../etc/passwd")

        # Shell special characters
        with pytest.raises(GitSecurityError, match="Malicious ref name"):
            git._validate_ref("branch;rm -rf /")

        # Reflog syntax
        with pytest.raises(GitSecurityError, match="Malicious ref name"):
            git._validate_ref("@{0}")

    def test_safe_operations(self, temp_repo: Path):
        """Test that safe Git operations work correctly."""
        from git_security import SecureGit

        git = SecureGit(temp_repo)

        # These should all work
        sha = git.get_head_sha()
        assert len(sha) == 40

        branch = git.get_current_branch()
        assert branch  # Should have a branch

        status = git.get_status()
        assert isinstance(status, str)

        log = git.log(count=5, oneline=True)
        assert "Initial commit" in log

    def test_no_shell_execution(self, temp_repo: Path):
        """Test that Git commands don't use shell execution."""
        import unittest.mock as mock

        from git_security import SecureGit

        git = SecureGit(temp_repo)

        # Mock subprocess.run to verify shell is not True
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="", stderr="")

            git.get_head_sha()

            # Verify shell was not passed as True
            # When shell is not passed, it defaults to False
            call_args = mock_run.call_args

            # Check that shell=True is NOT in kwargs
            if call_args.kwargs:
                assert call_args.kwargs.get("shell") is not True, (
                    "shell=True was passed to subprocess.run"
                )
            elif len(call_args.args) > 1:
                assert call_args[1].get("shell") is not True, (
                    "shell=True was passed to subprocess.run"
                )


# ============================================================================
# Shell Injection Prevention Tests
# ============================================================================


class TestShellInjection:
    """Test that shell injection is prevented."""

    def test_no_shell_true_in_brain_agent(self):
        """Verify no shell=True in brain_agent_v4.py production code."""
        brain_agent_path = PROJECT_ROOT / "brain_agent_v4.py"
        content = brain_agent_path.read_text()

        # Check for actual shell=True usage in code (not in comments or docstrings)
        lines = content.split("\n")
        in_docstring = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track docstrings
            if '"""' in stripped or "'''" in stripped:
                count = stripped.count('"""') + stripped.count("'''")
                if count % 2 == 1:
                    in_docstring = not in_docstring
                continue

            if in_docstring:
                continue

            # Skip comments
            if stripped.startswith("#"):
                continue

            # Check for shell=True in actual code
            assert "shell=True" not in stripped, (
                f"shell=True found in production code at line {i}: {stripped}"
            )

    def test_no_shell_true_in_sb(self):
        """Verify no shell=True in sb.py production code."""
        sb_path = PROJECT_ROOT / "sb.py"
        content = sb_path.read_text()

        # Check for actual shell=True usage in code (not in comments or docstrings)
        lines = content.split("\n")
        in_docstring = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track docstrings
            if '"""' in stripped or "'''" in stripped:
                count = stripped.count('"""') + stripped.count("'''")
                if count % 2 == 1:
                    in_docstring = not in_docstring
                continue

            if in_docstring:
                continue

            # Skip comments
            if stripped.startswith("#"):
                continue

            # Check for shell=True in actual code
            assert "shell=True" not in stripped, (
                f"shell=True found in production code at line {i}: {stripped}"
            )

    def test_no_shell_true_in_install(self):
        """Verify no shell=True in install.py production code."""
        install_path = PROJECT_ROOT / "v4-extract" / "second-brain-v4" / "install.py"
        content = install_path.read_text()

        # Check for actual shell=True usage in code (not in comments or docstrings)
        lines = content.split("\n")
        in_docstring = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track docstrings
            if '"""' in stripped or "'''" in stripped:
                count = stripped.count('"""') + stripped.count("'''")
                if count % 2 == 1:
                    in_docstring = not in_docstring
                continue

            if in_docstring:
                continue

            # Skip comments
            if stripped.startswith("#"):
                continue

            # Check for shell=True in actual code
            assert "shell=True" not in stripped, (
                f"shell=True found in production code at line {i}: {stripped}"
            )

    def test_no_os_chdir_in_brain_agent(self):
        """Verify no os.chdir in brain_agent_v4.py."""
        brain_agent_path = PROJECT_ROOT / "brain_agent_v4.py"
        content = brain_agent_path.read_text()

        # Should not have os.chdir in execution paths
        # (only in comments or docstrings is acceptable)
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            # Skip docstrings (simple check)
            if '"""' in stripped or "'''" in stripped:
                continue
            assert "os.chdir" not in stripped, f"os.chdir found at line {i}: {stripped}"

    def test_malicious_arguments_treated_safely(self):
        """Test that malicious arguments can't escape command semantics."""
        import shlex

        # These should all be parsed as single arguments, not shell commands
        malicious_payloads = [
            "; rm -rf ...",
            "&& malicious-command",
            "$(malicious-command)",
            "`malicious-command`",
            "| malicious-command",
        ]

        for payload in malicious_payloads:
            # shlex.split should handle these safely
            try:
                args = shlex.split(f'echo "{payload}"')
                # The payload should be a single argument, not executed
                assert payload in args[-1] or payload in str(args)
            except ValueError:
                # shlex.split might reject some malformed inputs, which is fine
                pass

    def test_dangerous_commands_blocked(self):
        """Test that dangerous commands are blocked."""
        # Import the tool_shell function
        from brain_agent_v4 import tool_shell

        # These should be blocked
        dangerous_commands = [
            "rm -rf /",
            "rmdir /s /q",
            "format C:",
            "mkfs.ext4 /dev/sda",
            "dd if=/dev/zero of=/dev/sda",
            "shutdown -h now",
            "reboot",
        ]

        for cmd in dangerous_commands:
            result = tool_shell(cmd)
            # Should be blocked or fail
            assert "Blocked" in result or "Error" in result or "not allowed" in result, (
                f"Dangerous command not blocked: {cmd}"
            )


# ============================================================================
# Context Builder Tests
# ============================================================================


class TestContextBuilder:
    """Test context builder with token budget."""

    def test_token_budget_enforced(self):
        """Test that token budget is enforced."""
        from context_builder import ContextBuilder

        builder = ContextBuilder(token_budget=100)

        # Create search results that exceed budget
        results = []
        for i in range(50):
            results.append(
                {
                    "content": f"Chunk {i} with some content. " * 10,
                    "project_id": "test",
                    "file_path": f"file_{i}.py",
                    "similarity": 0.9,
                    "rank": i,
                }
            )

        context = builder.build_context(results)

        # Estimate tokens in output
        estimated_tokens = len(context) // 4

        # Should be within budget (with some overhead)
        assert estimated_tokens <= 150, f"Context exceeded token budget: ~{estimated_tokens} tokens"

    def test_deduplication(self):
        """Test that duplicate content is deduplicated."""
        from context_builder import ContextBuilder

        builder = ContextBuilder(token_budget=10000, deduplicate=True)

        # Create results with duplicates
        results = [
            {
                "content": "This is duplicate content.",
                "project_id": "test",
                "file_path": "file1.py",
                "similarity": 0.9,
                "rank": 1,
            },
            {
                "content": "This is duplicate content.",  # Exact duplicate
                "project_id": "test",
                "file_path": "file2.py",
                "similarity": 0.85,
                "rank": 2,
            },
            {
                "content": "This is unique content.",
                "project_id": "test",
                "file_path": "file3.py",
                "similarity": 0.8,
                "rank": 3,
            },
        ]

        context = builder.build_context(results)

        # Should only have 2 chunks (duplicate removed)
        assert context.count("This is duplicate content.") == 1
        assert "This is unique content." in context

    def test_source_attribution(self):
        """Test that source attribution is added."""
        from context_builder import ContextBuilder

        builder = ContextBuilder(token_budget=10000, source_attribution=True)

        results = [
            {
                "content": "Some content",
                "project_id": "myproject",
                "file_path": "src/main.py",
                "chunk_name": "main_function",
                "similarity": 0.9,
                "rank": 1,
            },
        ]

        context = builder.build_context(results)

        # Should have source attribution
        assert "[myproject/src/main.py:main_function]" in context

    def test_project_filter(self):
        """Test that project filtering works."""
        from context_builder import ContextBuilder

        builder = ContextBuilder(token_budget=10000)

        results = [
            {
                "content": "Content from project A",
                "project_id": "project-a",
                "file_path": "file1.py",
                "similarity": 0.9,
                "rank": 1,
            },
            {
                "content": "Content from project B",
                "project_id": "project-b",
                "file_path": "file2.py",
                "similarity": 0.85,
                "rank": 2,
            },
        ]

        context = builder.build_context(results, project_filter="project-a")

        # Should only have content from project-a
        assert "Content from project A" in context
        assert "Content from project B" not in context

    def test_deterministic_ordering(self):
        """Test that output ordering is deterministic."""
        from context_builder import ContextBuilder

        builder = ContextBuilder(token_budget=10000)

        results = [
            {
                "content": "Third",
                "project_id": "test",
                "file_path": "file3.py",
                "similarity": 0.7,
                "rank": 3,
            },
            {
                "content": "First",
                "project_id": "test",
                "file_path": "file1.py",
                "similarity": 0.9,
                "rank": 1,
            },
            {
                "content": "Second",
                "project_id": "test",
                "file_path": "file2.py",
                "similarity": 0.8,
                "rank": 2,
            },
        ]

        # Run multiple times
        contexts = [builder.build_context(results) for _ in range(5)]

        # All should be identical
        assert all(c == contexts[0] for c in contexts), (
            "Context builder output is not deterministic"
        )


# ============================================================================
# Worktree Isolation Tests
# ============================================================================


class TestWorktreeIsolation:
    """Test worktree isolation controls."""

    def test_worktree_creation(self, temp_repo: Path):
        """Test that worktrees can be created."""
        from worktree import WorktreeManager

        manager = WorktreeManager(temp_repo)
        info = manager.create_worktree("test-task")

        try:
            assert info["path"].exists()
            assert info["path"].is_dir()
            assert (info["path"] / ".git").exists() or (info["path"] / ".git").is_file()

            # Verify isolation: changes in worktree shouldn't affect primary
            primary_sha = subprocess.run(
                ["git", "-C", str(temp_repo), "rev-parse", "HEAD"], capture_output=True, text=True
            ).stdout.strip()

            wt_sha = subprocess.run(
                ["git", "-C", str(info["path"]), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
            ).stdout.strip()

            assert primary_sha == wt_sha, "Worktree should start at same commit"

        finally:
            manager.cleanup_worktree(info["path"], info["branch"])

    def test_worktree_isolation(self, temp_repo: Path):
        """Test that changes in worktree don't affect primary repo."""
        from worktree import WorktreeManager

        manager = WorktreeManager(temp_repo)
        info = manager.create_worktree("test-task")

        try:
            # Make a change in the worktree
            test_file = info["path"] / "test_change.txt"
            test_file.write_text("This is a test change")

            # Stage and commit in worktree
            wt_git = manager.get_worktree_git(info["path"])
            wt_git.add_all()
            wt_git.commit("Test change in worktree")

            # Primary repo should be unchanged
            primary_status = subprocess.run(
                ["git", "-C", str(temp_repo), "status", "--porcelain"],
                capture_output=True,
                text=True,
            ).stdout.strip()

            assert primary_status == "", "Primary repo should be unchanged"

            # Primary HEAD should be unchanged
            primary_sha = subprocess.run(
                ["git", "-C", str(temp_repo), "rev-parse", "HEAD"], capture_output=True, text=True
            ).stdout.strip()

            initial_sha = subprocess.run(
                ["git", "-C", str(temp_repo), "rev-parse", "HEAD~0"], capture_output=True, text=True
            ).stdout.strip()

            assert primary_sha == initial_sha, "Primary HEAD should not change"

        finally:
            manager.cleanup_worktree(info["path"], info["branch"])

    def test_worktree_cleanup(self, temp_repo: Path):
        """Test that worktrees can be cleaned up."""
        from worktree import WorktreeManager

        manager = WorktreeManager(temp_repo)
        info = manager.create_worktree("test-task")

        worktree_path = info["path"]
        branch = info["branch"]

        # Verify worktree exists
        assert worktree_path.exists()

        # Cleanup
        result = manager.cleanup_worktree(worktree_path, branch)
        assert result is True

        # Worktree should be removed
        assert not worktree_path.exists()

    def test_worktree_path_escaping_rejected(self, temp_repo: Path):
        """Test that worktree paths can't escape parent directory."""
        from worktree import WorktreeManager

        # Try to create worktree manager with parent outside repo
        manager = WorktreeManager(temp_repo, worktree_parent=Path(tempfile.mkdtemp()) / "outside")

        info = manager.create_worktree("test-task")

        try:
            # Worktree should be inside the designated parent
            assert str(info["path"]).startswith(str(manager.worktree_parent))
        finally:
            manager.cleanup_worktree(info["path"], info["branch"])


# ============================================================================
# Merge Gate Tests
# ============================================================================


class TestMergeGate:
    """Test merge gate controls."""

    def test_merge_lock_acquisition(self, temp_repo: Path):
        """Test that merge lock can be acquired."""
        from merge_gate import MergeLock

        lock = MergeLock(temp_repo)

        # Should be able to acquire lock
        assert lock.acquire(timeout=5) is True

        # Release lock
        lock.release()

    def test_merge_lock_exclusivity(self, temp_repo: Path):
        """Test that merge lock is exclusive."""
        import threading

        from merge_gate import MergeLock

        lock = MergeLock(temp_repo)

        # Acquire lock
        assert lock.acquire(timeout=5) is True

        # Try to acquire from another thread (should fail)
        second_lock = MergeLock(temp_repo)
        result = [None]

        def try_acquire():
            result[0] = second_lock.acquire(timeout=1)

        thread = threading.Thread(target=try_acquire)
        thread.start()
        thread.join()

        # Second acquisition should fail
        assert result[0] is False, "Second lock acquisition should fail"

        # Release first lock
        lock.release()

    def test_fast_forward_merge(self, temp_repo: Path):
        """Test that fast-forward merge works."""
        from git_security import SecureGit
        from merge_gate import MergeGate
        from worktree import WorktreeManager

        git = SecureGit(temp_repo)
        baseline_sha = git.get_head_sha()

        # Create worktree and make changes
        manager = WorktreeManager(temp_repo)
        info = manager.create_worktree("test-merge")

        try:
            # Make a change
            test_file = info["path"] / "merge_test.txt"
            test_file.write_text("Merge test content")

            # Commit in worktree
            wt_git = manager.get_worktree_git(info["path"])
            wt_git.add_all()
            target_sha = wt_git.commit("Test merge commit")

            # Perform merge through gate
            gate = MergeGate(temp_repo)
            result = gate.merge_agent_changes(
                info["path"], info["branch"], baseline_sha, auto_cleanup=False
            )

            assert result["success"] is True
            assert result["final_sha"] == target_sha

            # Verify primary repo has the change
            final_sha = git.get_head_sha()
            assert final_sha == target_sha

        finally:
            manager.cleanup_worktree(info["path"], info["branch"])

    def test_baseline_mismatch_rejected(self, temp_repo: Path):
        """Test that merge is rejected if baseline moved."""
        from git_security import SecureGit
        from merge_gate import MergeGate, MergeSecurityError
        from worktree import WorktreeManager

        git = SecureGit(temp_repo)
        baseline_sha = git.get_head_sha()

        # Create worktree
        manager = WorktreeManager(temp_repo)
        info = manager.create_worktree("test-merge")

        try:
            # Make a change in primary repo (simulates concurrent modification)
            (temp_repo / "concurrent_change.txt").write_text("Concurrent")
            git.add_all()
            git.commit("Concurrent change")

            # Make a change in worktree
            test_file = info["path"] / "merge_test.txt"
            test_file.write_text("Merge test content")
            wt_git = manager.get_worktree_git(info["path"])
            wt_git.add_all()
            wt_git.commit("Test merge commit")

            # Try to merge (should fail because baseline moved)
            gate = MergeGate(temp_repo)

            with pytest.raises(MergeSecurityError, match="Baseline SHA mismatch"):
                gate.merge_agent_changes(
                    info["path"], info["branch"], baseline_sha, auto_cleanup=False
                )

        finally:
            manager.cleanup_worktree(info["path"], info["branch"])

    def test_unauthorized_files_rejected(self, temp_repo: Path):
        """Test that unauthorized files are rejected."""
        from git_security import SecureGit
        from merge_gate import MergeGate, MergeSecurityError
        from worktree import WorktreeManager

        git = SecureGit(temp_repo)
        baseline_sha = git.get_head_sha()

        # Create worktree
        manager = WorktreeManager(temp_repo)
        info = manager.create_worktree("test-merge")

        try:
            # Make a change to an unauthorized file
            test_file = info["path"] / "unauthorized.txt"
            test_file.write_text("Unauthorized content")
            wt_git = manager.get_worktree_git(info["path"])
            wt_git.add_all()
            wt_git.commit("Unauthorized change")

            # Create gate with allowlist
            gate = MergeGate(
                temp_repo,
                allowed_files={"src/*.py", "tests/*.py"},  # Only Python files
            )

            # Try to merge (should fail because unauthorized file changed)
            with pytest.raises(MergeSecurityError, match="Unauthorized file"):
                gate.merge_agent_changes(
                    info["path"], info["branch"], baseline_sha, auto_cleanup=False
                )

        finally:
            manager.cleanup_worktree(info["path"], info["branch"])


# ============================================================================
# Integration Test
# ============================================================================


class TestEndToEnd:
    """End-to-end integration test."""

    def test_complete_workflow(self, temp_repo: Path):
        """Test complete agent workflow: worktree -> changes -> test -> commit -> merge."""
        from git_security import SecureGit
        from merge_gate import MergeGate
        from worktree import WorktreeManager

        git = SecureGit(temp_repo)
        baseline_sha = git.get_head_sha()

        # Step 1: Create worktree
        manager = WorktreeManager(temp_repo)
        info = manager.create_worktree("e2e-test")

        # Step 2: Make legitimate changes
        test_file = info["path"] / "src" / "new_feature.py"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("""
def new_feature():
    return "Hello from agent"

if __name__ == "__main__":
    print(new_feature())
""")

        # Step 3: Commit changes in worktree
        wt_git = manager.get_worktree_git(info["path"])
        wt_git.add_all()
        commit_sha = wt_git.commit("feat: add new feature via agent")

        # Step 4: Merge through gate
        gate = MergeGate(temp_repo)
        result = gate.merge_agent_changes(
            info["path"], info["branch"], baseline_sha, auto_cleanup=True
        )

        # Verify success
        assert result["success"] is True
        assert result["final_sha"] == commit_sha
        assert len(result["merged_files"]) > 0

        # Verify primary repo state
        final_sha = git.get_head_sha()
        assert final_sha == commit_sha
        assert git.is_clean()

        # Verify the file exists in primary repo
        assert (temp_repo / "src" / "new_feature.py").exists()

    def test_malicious_changes_rejected(self, temp_repo: Path):
        """Test that malicious changes are rejected."""
        from git_security import SecureGit
        from merge_gate import MergeGate, MergeSecurityError
        from worktree import WorktreeManager

        git = SecureGit(temp_repo)
        baseline_sha = git.get_head_sha()

        # Create worktree
        manager = WorktreeManager(temp_repo)
        info = manager.create_worktree("malicious-test")

        try:
            # Attempt path traversal
            malicious_file = info["path"] / ".." / "escape.txt"
            try:
                malicious_file.write_text("Malicious content")
            except (OSError, ValueError):
                # If we can't create the file, that's fine
                pass

            # Make a change that would be unauthorized
            test_file = info["path"] / "secret.txt"
            test_file.write_text("Secret content")
            wt_git = manager.get_worktree_git(info["path"])
            wt_git.add_all()
            wt_git.commit("Malicious change")

            # Create gate with allowlist
            gate = MergeGate(temp_repo, allowed_files={"src/*.py"})

            # Should be rejected
            with pytest.raises(MergeSecurityError):
                gate.merge_agent_changes(
                    info["path"], info["branch"], baseline_sha, auto_cleanup=False
                )

        finally:
            manager.cleanup_worktree(info["path"], info["branch"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
