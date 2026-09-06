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


class TestCommandInjection:
    """SEC-02: Verify command injection is prevented."""

    def test_semicolon_injection(self, tmp_path):
        """Semicolons should be blocked as shell metacharacters or dangerous args."""
        with pytest.raises(PermissionError):
            validate_command("git status; curl evil.com", tmp_path)

    def test_pipe_injection(self, tmp_path):
        """Pipe characters should be blocked."""
        with pytest.raises(PermissionError, match="metacharacter"):
            validate_command("git status | cat /etc/passwd", tmp_path)

    def test_dollar_paren_injection(self, tmp_path):
        """Command substitution should be blocked."""
        with pytest.raises(PermissionError, match="metacharacter"):
            validate_command("git status $(curl evil.com)", tmp_path)

    def test_backtick_injection(self, tmp_path):
        """Backtick command substitution should be blocked."""
        with pytest.raises(PermissionError, match="metacharacter"):
            validate_command("git status `curl evil.com`", tmp_path)

    def test_ampersand_injection(self, tmp_path):
        """Background execution should be blocked."""
        with pytest.raises(PermissionError):
            validate_command("git status & rm -rf /", tmp_path)

    def test_python_c_injection(self, tmp_path):
        """Python -c with dangerous code should be blocked."""
        with pytest.raises(PermissionError, match="metacharacter"):
            validate_command("python -c 'import os; os.system(\"rm -rf /\")'", tmp_path)

    def test_semicolon_in_single_arg(self, tmp_path):
        """Semicolons inside a single argument should be blocked."""
        with pytest.raises(PermissionError, match="metacharacter"):
            validate_command("git", tmp_path)
            # Even if we pass parts manually, semicolons in args are blocked
            validate_command("python -c 'a; b'", tmp_path)

    def test_no_file_created_by_injection(self, tmp_path):
        """Verify injection attempts don't create files."""
        # This should be blocked and no file should be created
        try:
            asyncio.get_event_loop().run_until_complete(
                run_command(
                    "git status; touch pwned.txt",
                    tmp_path,
                    timeout_seconds=10,
                )
            )
        except (PermissionError, Exception):
            pass

        assert not (tmp_path / "pwned.txt").exists()

    def test_subprocess_exec_prevents_shell(self, tmp_path):
        """Verify asyncio.create_subprocess_exec is used (not Popen with shell)."""
        # This is a structural test - verify the module uses safe subprocess
        import inspect
        import tool_security

        source = inspect.getsource(tool_security)
        assert "create_subprocess_exec" in source
        assert (
            "shell=True" not in source or "shell=True" in source.split("def ")[0]
        )  # only in comments

    def test_no_raw_subprocess_in_brain_agent(self):
        """Verify brain_agent_v4.py doesn't use raw subprocess.run."""
        import ast
        from pathlib import Path

        ba_path = Path(__file__).parent.parent / "brain_agent_v4.py"
        source = ba_path.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for subprocess.run calls
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "run":
                        if isinstance(node.func.value, ast.Name):
                            if node.func.value.id == "subprocess":
                                # Allow in comments/docstrings only
                                assert False, (
                                    f"brain_agent_v4.py line {node.lineno}: "
                                    "raw subprocess.run found — must use tool_security.run_command"
                                )
