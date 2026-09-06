"""
Protected Path Policy — SEC-05

Prevents agent/tool mutation of secret and credential files.
Applied at every file mutation entry point: write, delete, rename, copy, patch.

Fixes:
- Template files only writable (not deletable/renamed/copied/patched)
- Secret content validation integrated into write_file
- build_runtime_env uses allowlist for task_env keys
- All entry points (write, delete, rename, copy, patch) covered
"""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Protected files ──────────────────────────────────────────────
PROTECTED_BASENAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".env.local",
        ".env.development",
        ".env.test",
        ".env.production",
        ".env.prod",
        ".env.staging",
        ".env.backup",
        "credentials.json",
        "secrets.json",
        "token.json",
        "client_secret.json",
        "id_rsa",
        "id_ed25519",
        "id_dsa",
        "id_ecdsa",
    }
)

PROTECTED_SUFFIXES: tuple[str, ...] = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
)

# Template files: ONLY write is allowed (no delete/rename/copy/patch)
WRITEABLE_TEMPLATES: frozenset[str] = frozenset(
    {
        ".env.example",
        ".env.template",
        ".env.sample",
    }
)

# ── Task environment allowlist ───────────────────────────────────
ALLOWED_TASK_ENV_KEYS: frozenset[str] = frozenset(
    {
        "CI",
        "PYTHONUNBUFFERED",
        "NODE_ENV",
        "RUST_BACKTRACE",
        "HOME",
        "PATH",
        "LANG",
        "LC_ALL",
    }
)


class ProtectedPathError(Exception):
    """Raised when a mutation targets a protected file."""

    pass


def is_protected_path(path: Path) -> bool:
    """
    Check if a path targets a protected file.
    Checks the FINAL component of the path (not resolved).
    """
    name = path.name.lower()

    if name in PROTECTED_BASENAMES:
        return True

    if name.endswith(PROTECTED_SUFFIXES):
        return True

    return False


def is_writeable_template(path: Path) -> bool:
    """Check if a path is an allowed template file."""
    return path.name.lower() in WRITEABLE_TEMPLATES


def assert_mutation_allowed(
    path: Path,
    operation: str,
    *,
    allow_template_write: bool = False,
) -> None:
    """
    Assert that a file mutation is allowed.

    Rules:
    - Protected files: ALL operations blocked
    - Template files: ONLY write allowed (when allow_template_write=True)
    """
    if is_protected_path(path):
        msg = f"SEC-05: {operation} blocked — protected file: {path.name}"
        logger.warning(msg)
        raise ProtectedPathError(msg)

    if is_writeable_template(path):
        if operation != "write" or not allow_template_write:
            msg = f"SEC-05: {operation} blocked — template mutation not allowed: {path.name}"
            logger.warning(msg)
            raise ProtectedPathError(msg)


# ── Secret content detection ─────────────────────────────────────
SECRET_PATTERNS: tuple[str, ...] = (
    "API_KEY=",
    "AWS_SECRET_ACCESS_KEY=",
    "DATABASE_URL=postgresql://",
    "DATABASE_URL=mysql://",
    "DATABASE_URL=postgres://",
    "PRIVATE_KEY=",
    "SECRET_KEY=",
    "CLIENT_SECRET=",
    "TOKEN=",
    "OAUTH_TOKEN=",
    "NEON_DSN=postgresql://",
    "NEON_DSN=postgres://",
    "OPENAI_API_KEY=",
    "GITHUB_TOKEN=",
    "BEARER_TOKEN=",
    "NGROK_AUTH_TOKEN=",
    "STRIPE_SECRET_KEY=",
    "MAILGUN_API_KEY=",
    "SENDGRID_API_KEY=",
)

# Files where content validation is enforced
SECRET_CONTENT_CHECK_PATHS: frozenset[str] = frozenset(
    {
        ".env.example",
        ".env.template",
        ".env.sample",
    }
)

# Files where content validation is always enforced
SECRET_CONTENT_ALWAYS_CHECK: frozenset[str] = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        "credentials.json",
        "secrets.json",
    }
)


def contains_secret_content(text: str) -> bool:
    """Check if text content likely contains secret values."""
    text_upper = text.upper()
    for pattern in SECRET_PATTERNS:
        if pattern.upper() in text_upper:
            return True
    # Check private key blocks
    if "-----BEGIN" in text.upper() and "PRIVATE KEY" in text.upper():
        return True
    return False


def validate_file_content(
    path: Path,
    content: str,
    *,
    allow_secret_placeholders: bool = False,
) -> None:
    """
    Validate file content for secrets.
    Raises ProtectedPathError if content contains real secrets.
    """
    name = path.name.lower()

    # Template files: check unless placeholders allowed
    if name in WRITEABLE_TEMPLATES:
        if not allow_secret_placeholders and contains_secret_content(content):
            msg = f"SEC-05: secret content blocked for template {path.name}"
            logger.warning(msg)
            raise ProtectedPathError(msg)
        return

    # All other files: block if they contain secrets
    if contains_secret_content(content):
        msg = f"SEC-05: secret content blocked for {path.name}"
        logger.warning(msg)
        raise ProtectedPathError(msg)


# ── File operation wrappers with policy enforcement ──────────────
def delete_file(file_path: str, workspace: Path) -> str:
    """Delete a file within workspace bounds. SEC-05: blocks protected files."""
    from tool_security import validate_path

    p = validate_path(file_path, workspace)
    assert_mutation_allowed(p, "delete")

    if not p.exists():
        return f"Not found: {file_path}"

    p.unlink()
    return f"Deleted {p.relative_to(workspace)}"


def rename_file(source: str, target: str, workspace: Path) -> str:
    """Rename/move a file within workspace bounds. SEC-05: checks both paths."""
    from tool_security import validate_path

    src = validate_path(source, workspace)
    dst = validate_path(target, workspace)

    # Check BOTH source and target
    assert_mutation_allowed(src, "rename")
    assert_mutation_allowed(dst, "rename")

    if not src.exists():
        return f"Not found: {source}"

    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    return f"Renamed {src.relative_to(workspace)} to {dst.relative_to(workspace)}"


def copy_file(source: str, target: str, workspace: Path) -> str:
    """Copy a file within workspace bounds. SEC-05: checks both paths."""
    import shutil

    from tool_security import validate_path

    src = validate_path(source, workspace)
    dst = validate_path(target, workspace)

    # Check BOTH source and target
    assert_mutation_allowed(src, "copy")
    assert_mutation_allowed(dst, "copy")

    if not src.exists():
        return f"Not found: {source}"

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"Copied {src.relative_to(workspace)} to {dst.relative_to(workspace)}"


# ── Runtime environment (in-memory, not file) ───────────────────
def build_runtime_env(task_env: dict[str, str] | None = None) -> dict[str, str]:
    """
    Build environment dict for subprocess execution.
    Only allows specific safe task_env keys.
    Secrets passed in-memory only, never writes to .env.
    """
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONUNBUFFERED": "1",
    }

    if task_env:
        invalid = set(task_env.keys()) - ALLOWED_TASK_ENV_KEYS
        if invalid:
            raise PermissionError(f"SEC-05: task environment keys not allowed: {sorted(invalid)}")
        env.update(task_env)

    return env


# ── Audit log secret scrubbing ───────────────────────────────────
def scrub_secrets(text: str) -> str:
    """Remove potential secret values from text for logging/display."""
    # KEY=VALUE patterns
    for pattern in SECRET_PATTERNS:
        key = pattern.split("=")[0] if "=" in pattern else pattern
        regex = rf"({re.escape(key)}\s*=\s*)([^\s&\n]+)"
        text = re.sub(regex, r"\1***", text, flags=re.IGNORECASE)

    # URL passwords: ://user:password@host
    text = re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1***\3", text)

    # Bearer tokens
    text = re.sub(r"(Bearer\s+)(\S{8})\S+", r"\1\2***", text, flags=re.IGNORECASE)

    # GitHub/GitLab tokens
    text = re.sub(r"(ghp_|glpat-|github_pat_)\S+", r"***", text)

    # OpenAI keys
    text = re.sub(r"(sk-)\S{8}\S+", r"\1***", text)

    # AWS keys
    text = re.sub(r"(AKIA)\S{12}\S+", r"***", text)

    # Private key blocks
    text = re.sub(
        r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----",
        "-----BEGIN***KEY-----***-----END***KEY-----",
        text,
        flags=re.IGNORECASE,
    )

    return text
