"""Tests for tool_security allowlist-based command execution."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from tool_security import (
    ALLOWED_EXECUTABLES,
    BLOCKED_ARGUMENT_PATTERNS,
    AuditEntry,
    CommandResult,
    get_audit_log,
    read_file,
    run_command,
    validate_command,
    validate_path,
    write_file,
)


class TestAllowlist:
    def test_allowed_executables_include_python(self):
        assert "python" in ALLOWED_EXECUTABLES
        assert "python3" in ALLOWED_EXECUTABLES

    def test_allowed_executables_include_pytest(self):
        assert "pytest" in ALLOWED_EXECUTABLES

    def test_allowed_executables_include_ruff(self):
        assert "ruff" in ALLOWED_EXECUTABLES

    def test_allowed_executables_include_git(self):
        assert "git" in ALLOWED_EXECUTABLES

    def test_dangerous_not_in_allowlist(self):
        dangerous = {"sudo", "rm", "dd", "mkfs", "shutdown", "reboot", "curl", "wget"}
        assert dangerous.isdisjoint(ALLOWED_EXECUTABLES)


class TestBlockedArguments:
    def test_push_blocked(self):
        assert "push" in BLOCKED_ARGUMENT_PATTERNS

    def test_force_blocked(self):
        assert "force" in BLOCKED_ARGUMENT_PATTERNS

    def test_hard_blocked(self):
        assert "--hard" in BLOCKED_ARGUMENT_PATTERNS

    def test_sudo_blocked(self):
        assert "sudo" in BLOCKED_ARGUMENT_PATTERNS

    def test_rm_blocked(self):
        assert "rm" in BLOCKED_ARGUMENT_PATTERNS


class TestValidateCommand:
    def test_simple_python_command(self, tmp_path):
        args = validate_command("python --version", tmp_path)
        assert args[0] == "python"

    def test_pytest_command(self, tmp_path):
        args = validate_command("pytest tests/", tmp_path)
        assert args[0] == "pytest"

    def test_ruff_check(self, tmp_path):
        args = validate_command("ruff check .", tmp_path)
        assert args[0] == "ruff"

    def test_empty_command_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match="Empty command"):
            validate_command("", tmp_path)

    def test_unknown_executable_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match="not allowed"):
            validate_command("malware --do-something", tmp_path)

    def test_sudo_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match="not allowed"):
            validate_command("sudo rm -rf /", tmp_path)

    def test_rm_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match="not allowed"):
            validate_command("rm -rf /", tmp_path)

    def test_curl_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match="not allowed"):
            validate_command("curl http://evil.com", tmp_path)

    def test_git_push_blocked(self, tmp_path):
        with pytest.raises(PermissionError, match="Blocked"):
            validate_command("git push origin main", tmp_path)

    def test_git_reset_hard_blocked(self, tmp_path):
        with pytest.raises(PermissionError, match="Blocked"):
            validate_command("git reset --hard HEAD", tmp_path)

    def test_git_status_allowed(self, tmp_path):
        args = validate_command("git status", tmp_path)
        assert args == ["git", "status"]

    def test_git_log_allowed(self, tmp_path):
        args = validate_command("git log --oneline", tmp_path)
        assert args == ["git", "log", "--oneline"]

    def test_git_diff_allowed(self, tmp_path):
        args = validate_command("git diff HEAD", tmp_path)
        assert args == ["git", "diff", "HEAD"]


class TestValidatePath:
    def test_relative_path_valid(self, tmp_path):
        p = validate_path("src/main.py", tmp_path)
        assert p == tmp_path / "src/main.py"

    def test_absolute_path_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match="Absolute path"):
            validate_path("/etc/passwd", tmp_path)

    def test_traversal_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match="traversal"):
            validate_path("../../etc/passwd", tmp_path)

    def test_git_access_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match=".git"):
            validate_path(".git/config", tmp_path)

    def test_empty_path_rejected(self, tmp_path):
        with pytest.raises(PermissionError, match="Empty path"):
            validate_path("", tmp_path)


class TestReadFile:
    def test_read_existing_file(self, tmp_path):
        (tmp_path / "test.py").write_text("print('hello')")
        content = read_file("test.py", tmp_path)
        assert content == "print('hello')"

    def test_read_nonexistent_file(self, tmp_path):
        content = read_file("missing.py", tmp_path)
        assert "Not found" in content

    def test_read_outside_workspace_rejected(self, tmp_path):
        with pytest.raises(PermissionError):
            read_file("../../etc/passwd", tmp_path)


class TestWriteFile:
    def test_write_file(self, tmp_path):
        result = write_file("output.py", "print('world')", tmp_path)
        assert "Wrote" in result
        assert (tmp_path / "output.py").read_text() == "print('world')"

    def test_write_creates_directories(self, tmp_path):
        write_file("sub/dir/file.py", "content", tmp_path)
        assert (tmp_path / "sub/dir/file.py").exists()

    def test_write_outside_workspace_rejected(self, tmp_path):
        with pytest.raises(PermissionError):
            write_file("../../evil.py", "content", tmp_path)


class TestRunCommand:
    def test_python_version(self, tmp_path):
        result = asyncio.get_event_loop().run_until_complete(
            run_command("python --version", tmp_path, timeout_seconds=10)
        )
        assert result.exit_code == 0
        assert "Python" in result.stdout

    def test_failing_python_command(self, tmp_path):
        # Write a test script that exits with code 1
        script = tmp_path / "fail.py"
        script.write_text("import sys; sys.exit(1)")
        result = asyncio.get_event_loop().run_until_complete(
            run_command(f"python {script.name}", tmp_path, timeout_seconds=10)
        )
        assert result.exit_code == 1

    def test_blocked_command(self, tmp_path):
        result = asyncio.get_event_loop().run_until_complete(
            run_command("sudo reboot", tmp_path, timeout_seconds=10)
        )
        assert result.blocked is True
        assert "not allowed" in result.block_reason

    def test_timeout(self, tmp_path):
        # Write a script that sleeps
        script = tmp_path / "slow.py"
        script.write_text("import time; time.sleep(60)")
        result = asyncio.get_event_loop().run_until_complete(
            run_command(f"python {script.name}", tmp_path, timeout_seconds=2)
        )
        assert result.timed_out is True
        assert result.exit_code == 124

    def test_audit_log_recorded(self, tmp_path):
        initial_len = len(get_audit_log())
        asyncio.get_event_loop().run_until_complete(
            run_command("python --version", tmp_path, timeout_seconds=10)
        )
        assert len(get_audit_log()) > initial_len
