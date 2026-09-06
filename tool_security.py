"""
Tool Security — Allowlist-based command execution with workspace isolation.

Replaces the denylist approach with:
- Explicit allowlist of safe executables
- Blocked argument patterns
- Workspace boundary enforcement
- Timeout and output limits
- Audit logging
- No shell=True
"""

import asyncio
import logging
import os
import shlex
import time
from dataclasses import dataclass
from pathlib import Path

from protected_path_policy import (
    ProtectedPathError,
    assert_mutation_allowed,
    contains_secret_content,
    delete_file as policy_delete_file,
    is_protected_path,
    rename_file as policy_rename_file,
    copy_file as policy_copy_file,
    validate_file_content,
)

logger = logging.getLogger(__name__)

# ── Allowlist ────────────────────────────────────────────────────
# Only these executables may be invoked by the agent.
ALLOWED_EXECUTABLES: set[str] = {
    # Python
    "python",
    "python3",
    "pip",
    "pip3",
    "pytest",
    "ruff",
    "mypy",
    "bandit",
    # Node
    "node",
    "npm",
    "npx",
    "pnpm",
    "yarn",
    # Git (read-only operations handled separately)
    "git",
    # Make / build
    "make",
    "cargo",
    "go",
    # System utilities (safe)
    "cat",
    "head",
    "tail",
    "wc",
    "grep",
    "find",
    "ls",
    "echo",
    "pwd",
    "which",
    "uname",
    "date",
}

# ── Blocked arguments ────────────────────────────────────────────
# These patterns in command arguments cause rejection.
BLOCKED_ARGUMENT_PATTERNS: list[str] = [
    # Git destructive
    "push",
    "force",
    "--hard",
    "--force-with-lease",
    "reset",
    "clean",
    "checkout",
    "branch",
    "-d",
    "-D",
    # Destructive filesystem
    "rm",
    "rmdir",
    "del",
    "format",
    "mkfs",
    "dd",
    # System
    "sudo",
    "chmod",
    "chown",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init",
    # Network (dangerous)
    "curl",
    "wget",
    "nc",
    "ncat",
    "socat",
    "ssh",
    "scp",
    "rsync",
    # Eval / code execution
    "eval",
    "exec",
]

# ── Git read-only commands (always allowed) ──────────────────────
GIT_SAFE_COMMANDS: set[str] = {
    "status",
    "log",
    "diff",
    "show",
    "branch",
    "remote",
    "rev-parse",
    "rev-list",
    "describe",
    "tag",
    "stash",
    "blame",
}


# ── Data classes ─────────────────────────────────────────────────
@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    blocked: bool = False
    block_reason: str = ""


@dataclass
class AuditEntry:
    timestamp: float
    command: str
    workspace: str
    exit_code: int
    blocked: bool
    block_reason: str
    duration_ms: int
    output_bytes: int


# ── Audit log ────────────────────────────────────────────────────
_audit_log: list[AuditEntry] = []


def get_audit_log() -> list[AuditEntry]:
    return list(_audit_log)


def _audit(entry: AuditEntry) -> None:
    _audit_log.append(entry)
    if entry.blocked:
        logger.warning(
            "BLOCKED command=%s workspace=%s reason=%s",
            entry.command,
            entry.workspace,
            entry.block_reason,
        )
    elif entry.exit_code != 0:
        logger.info(
            "FAILED command=%s exit=%d workspace=%s",
            entry.command,
            entry.exit_code,
            entry.workspace,
        )


# ── Validation ───────────────────────────────────────────────────
def validate_command(command: str, workspace: Path, trusted: bool = False) -> list[str]:
    """
    Validate and parse a command string.

    Returns parsed args list if allowed, raises PermissionError otherwise.

    Args:
        trusted: If True, bypasses argument checks for internal operations
                 (worktree cleanup, etc.). Never expose to agent/LLM.
    """
    if not command or not command.strip():
        raise PermissionError("Empty command")

    try:
        parts = shlex.split(command)
    except ValueError as e:
        raise PermissionError(f"Invalid command syntax: {e}")

    if not parts:
        raise PermissionError("Empty command after parsing")

    executable = Path(parts[0]).name.lower()

    # Check if executable is in allowlist
    if executable not in ALLOWED_EXECUTABLES:
        raise PermissionError(f"Executable not allowed: {executable}")

    # For non-trusted commands, check blocked arguments
    if not trusted:
        # For git, check if the subcommand is safe
        if executable == "git" and len(parts) > 1:
            subcmd = parts[1].lower().lstrip("-")
            if subcmd not in GIT_SAFE_COMMANDS:
                # Check if it's a blocked argument
                for arg in parts[1:]:
                    if arg.lower().lstrip("-") in BLOCKED_ARGUMENT_PATTERNS:
                        raise PermissionError(f"Blocked git argument: {arg}")

        # Check blocked argument patterns
        for arg in parts[1:]:
            arg_lower = arg.lower().lstrip("-")
            if arg_lower in BLOCKED_ARGUMENT_PATTERNS:
                raise PermissionError(f"Blocked argument: {arg}")

        # Check for shell metacharacters
        dangerous_chars = set("|;&$`!{}()[]")
        for part in parts:
            if any(c in part for c in dangerous_chars):
                raise PermissionError(f"Shell metacharacter not allowed in: {part}")

    return parts


def validate_path(file_path: str, workspace: Path) -> Path:
    """
    Validate that a file path stays within the workspace.
    """
    if not file_path:
        raise PermissionError("Empty path")

    # Normalize separators
    normalized = file_path.replace("\\", "/")

    # Reject absolute paths
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        raise PermissionError(f"Absolute path not allowed: {file_path}")

    # Reject traversal
    if ".." in normalized.split("/"):
        raise PermissionError(f"Path traversal not allowed: {file_path}")

    # Reject .git access
    parts = normalized.split("/")
    if any(p.lower() == ".git" for p in parts):
        raise PermissionError(f".git access not allowed: {file_path}")

    resolved = (workspace / normalized).resolve()

    # Verify inside workspace
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError:
        raise PermissionError(f"Path escapes workspace: {file_path}")

    return resolved


# ── Execution ────────────────────────────────────────────────────
async def run_command(
    command: str,
    workspace: Path,
    timeout_seconds: int = 120,
    max_output_bytes: int = 200_000,
    trusted: bool = False,
) -> CommandResult:
    """
    Execute a command with full security validation.

    - Validates against allowlist
    - Runs inside workspace
    - Enforces timeout
    - Limits output size
    - Logs audit entry

    Args:
        trusted: If True, bypasses argument checks for internal operations
                 (worktree cleanup, etc.). Never expose to agent/LLM.
    """
    start = time.monotonic()

    try:
        args = validate_command(command, workspace, trusted=trusted)
    except PermissionError as e:
        entry = AuditEntry(
            timestamp=time.time(),
            command=command,
            workspace=str(workspace),
            exit_code=-1,
            blocked=True,
            block_reason=str(e),
            duration_ms=0,
            output_bytes=0,
        )
        _audit(entry)
        return CommandResult(
            exit_code=-1,
            stdout="",
            stderr=str(e),
            blocked=True,
            block_reason=str(e),
        )

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(workspace),
        "PYTHONUNBUFFERED": "1",
        # Prevent agent from inheriting sensitive env vars
        "NEON_DSN": "",
        "DATABASE_URL": "",
        "GITHUB_TOKEN": "",
        "HF_TOKEN": "",
    }

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            duration_ms = int((time.monotonic() - start) * 1000)
            entry = AuditEntry(
                timestamp=time.time(),
                command=command,
                workspace=str(workspace),
                exit_code=124,
                blocked=False,
                block_reason="",
                duration_ms=duration_ms,
                output_bytes=0,
            )
            _audit(entry)
            return CommandResult(
                exit_code=124,
                stdout="",
                stderr=f"Command timed out after {timeout_seconds}s",
                timed_out=True,
            )

        # Truncate output
        stdout_str = stdout_bytes.decode(errors="replace")[:max_output_bytes]
        stderr_str = stderr_bytes.decode(errors="replace")[:max_output_bytes]

        duration_ms = int((time.monotonic() - start) * 1000)
        entry = AuditEntry(
            timestamp=time.time(),
            command=command,
            workspace=str(workspace),
            exit_code=process.returncode or 0,
            blocked=False,
            block_reason="",
            duration_ms=duration_ms,
            output_bytes=len(stdout_str) + len(stderr_str),
        )
        _audit(entry)

        return CommandResult(
            exit_code=process.returncode or 0,
            stdout=stdout_str,
            stderr=stderr_str,
        )

    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        entry = AuditEntry(
            timestamp=time.time(),
            command=command,
            workspace=str(workspace),
            exit_code=-1,
            blocked=False,
            block_reason=str(e),
            duration_ms=duration_ms,
            output_bytes=0,
        )
        _audit(entry)
        return CommandResult(
            exit_code=-1,
            stdout="",
            stderr=str(e),
        )


def run_command_sync(
    command: str,
    workspace: Path,
    timeout_seconds: int = 120,
    max_output_bytes: int = 200_000,
) -> CommandResult:
    """Synchronous wrapper for run_command."""
    return asyncio.get_event_loop().run_until_complete(
        run_command(command, workspace, timeout_seconds, max_output_bytes)
    )


# ── File operations ──────────────────────────────────────────────
def read_file(file_path: str, workspace: Path) -> str:
    """Read a file within workspace bounds."""
    p = validate_path(file_path, workspace)
    if not p.exists():
        return f"Not found: {file_path}"
    return p.read_text(encoding="utf-8", errors="ignore")[:8000]


def delete_file(file_path: str, workspace: Path) -> str:
    """Delete a file within workspace bounds. SEC-05: blocks protected files."""
    return policy_delete_file(file_path, workspace)


def rename_file(source: str, target: str, workspace: Path) -> str:
    """Rename a file within workspace bounds. SEC-05: checks both paths."""
    return policy_rename_file(source, target, workspace)


def copy_file(source: str, target: str, workspace: Path) -> str:
    """Copy a file within workspace bounds. SEC-05: checks both paths."""
    return policy_copy_file(source, target, workspace)


def write_file(file_path: str, content: str, workspace: Path) -> str:
    """Write a file within workspace bounds. SEC-05: blocks protected files + secret content."""
    p = validate_path(file_path, workspace)
    assert_mutation_allowed(p, "write", allow_template_write=True)
    validate_file_content(p, content)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {p.relative_to(workspace)}"


def apply_patch(patch_content: str, workspace: Path) -> str:
    """Apply a unified diff patch within workspace bounds. SEC-05: blocks protected files."""
    lines = patch_content.split("\n")
    for line in lines:
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            path = line.split("/", 1)[1] if "/" in line else ""
            if path:
                try:
                    p = validate_path(path, workspace)
                    assert_mutation_allowed(p, "patch")
                except (PermissionError, ProtectedPathError) as e:
                    return f"Security error: patch touches protected or outside file: {e}"

    # Write patch to temp file and apply
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(patch_content)
        patch_file = f.name

    try:
        result = run_command_sync(
            f"git apply --check {patch_file}",
            workspace,
        )
        if result.exit_code != 0:
            return f"Patch check failed: {result.stderr}"

        result = run_command_sync(
            f"git apply {patch_file}",
            workspace,
        )
        if result.exit_code != 0:
            return f"Patch apply failed: {result.stderr}"

        return "Patch applied successfully"
    finally:
        os.unlink(patch_file)
