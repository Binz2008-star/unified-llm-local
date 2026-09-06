"""
Rollback — Deterministic rollback and recovery for task operations.

DEP-01: Provides:
- TaskSnapshot: immutable record before mutation
- RollbackManager: manages rollback lifecycle
- Automatic rollback hooks for failures
- Audit evidence for all rollback operations
"""

import hashlib
import json
import logging
import os
import platform
import subprocess
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RollbackState(StrEnum):
    ACTIVE = "active"
    FAILED = "failed"
    ROLLBACK_PENDING = "rollback_pending"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"
    COMPLETED = "completed"


class RollbackError(Exception):
    pass


class RollbackUnsafeError(RollbackError):
    pass


class RollbackIdempotentError(RollbackError):
    pass


# ── Task Snapshot ────────────────────────────────────────────────
class TaskSnapshot:
    """
    Immutable record of workspace state before mutation.
    Created before any file changes, merge, or commit.
    """

    def __init__(
        self,
        task_id: str,
        project_id: str,
        workspace: Path,
        base_commit: str,
        *,
        changed_files: list[str] | None = None,
        diff_hash: str = "unknown",
    ):
        self.task_id = task_id
        self.project_id = project_id
        self.workspace = str(workspace)
        self.base_commit = base_commit
        self.current_commit = base_commit
        self.diff_hash = diff_hash
        self.changed_files = changed_files or []
        self.created_at = datetime.now(tz=UTC).isoformat()
        self.state = RollbackState.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "workspace": self.workspace,
            "base_commit": self.base_commit,
            "current_commit": self.current_commit,
            "diff_hash": self.diff_hash,
            "changed_files": self.changed_files,
            "created_at": self.created_at,
            "state": self.state,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ── Rollback Audit Evidence ─────────────────────────────────────
class RollbackEvidence:
    """Immutable record of a rollback operation."""

    def __init__(
        self,
        task_id: str,
        operation: str,
        base_commit: str,
        current_commit: str,
        diff_hash_before: str,
        diff_hash_after: str,
        files_restored: list[str],
        files_removed: list[str],
        exit_code: int,
        started_at: float,
        finished_at: float,
        failure_reason: str = "",
    ):
        self.task_id = task_id
        self.operation = operation
        self.base_commit = base_commit
        self.current_commit = current_commit
        self.diff_hash_before = diff_hash_before
        self.diff_hash_after = diff_hash_after
        self.files_restored = files_restored
        self.files_removed = files_removed
        self.exit_code = exit_code
        self.started_at = datetime.fromtimestamp(started_at, tz=UTC).isoformat()
        self.finished_at = datetime.fromtimestamp(finished_at, tz=UTC).isoformat()
        self.failure_reason = failure_reason
        self.hostname = platform.node()
        self.pid = os.getpid()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "operation": self.operation,
            "base_commit": self.base_commit,
            "current_commit": self.current_commit,
            "diff_hash_before": self.diff_hash_before,
            "diff_hash_after": self.diff_hash_after,
            "files_restored": self.files_restored,
            "files_removed": self.files_removed,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "failure_reason": self.failure_reason,
            "hostname": self.hostname,
            "pid": self.pid,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ── Git Operations ───────────────────────────────────────────────
def _git_run(args: list[str], cwd: Path, trusted: bool = False) -> tuple[int, str, str]:
    """Run a git command safely. No shell=True."""
    if not trusted:
        from tool_security import validate_command

        cmd_str = "git " + " ".join(args)
        validate_command(cmd_str, cwd, trusted=True)

    cmd = ["git"] + args
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _get_current_commit(workspace: Path) -> str:
    code, out, _ = _git_run(["rev-parse", "HEAD"], workspace, trusted=True)
    if code != 0:
        return "unknown"
    return out.strip()


def _get_changed_files(workspace: Path, base_commit: str) -> list[str]:
    code, out, _ = _git_run(["diff", "--name-only", base_commit, "HEAD"], workspace, trusted=True)
    if code != 0:
        return []
    return [f for f in out.strip().split("\n") if f]


def _get_untracked_files(workspace: Path) -> list[str]:
    code, out, _ = _git_run(["ls-files", "--others", "--exclude-standard"], workspace, trusted=True)
    if code != 0:
        return []
    # Exclude rollback audit directory
    return [f for f in out.strip().split("\n") if f and not f.startswith(".rollback_audit")]


def _compute_diff_hash(workspace: Path, files: list[str]) -> str:
    if not files:
        return "empty"
    hasher = hashlib.sha256()
    for f in sorted(files):
        fp = workspace / f
        if fp.exists():
            hasher.update(fp.read_bytes())
    return hasher.hexdigest()[:16]


# ── Rollback Manager ────────────────────────────────────────────
class RollbackManager:
    """
    Manages rollback lifecycle for task operations.

    Usage:
        rm = RollbackManager("task_1", "project", workspace)
        snapshot = rm.create_snapshot()
        try:
            # perform mutations
            ...
        except Exception:
            rm.rollback(snapshot)
    """

    def __init__(
        self,
        task_id: str,
        project_id: str,
        workspace: Path,
    ):
        self.task_id = task_id
        self.project_id = project_id
        self.workspace = workspace
        # Audit dir outside workspace to survive git checkout --force
        self._audit_dir = workspace.parent / ".rollback_audit" / task_id
        self._audit_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self) -> TaskSnapshot:
        """Create a snapshot before mutation."""
        base_commit = _get_current_commit(self.workspace)
        changed = _get_changed_files(self.workspace, base_commit)
        diff_hash = _compute_diff_hash(self.workspace, changed)

        snapshot = TaskSnapshot(
            task_id=self.task_id,
            project_id=self.project_id,
            workspace=self.workspace,
            base_commit=base_commit,
            changed_files=changed,
            diff_hash=diff_hash,
        )

        self._save_snapshot(snapshot)
        logger.info("Snapshot created: task=%s base=%s", self.task_id, base_commit[:8])
        return snapshot

    def verify_snapshot(self, snapshot: TaskSnapshot) -> bool:
        """Verify workspace hasn't changed unexpectedly."""
        current = _get_current_commit(self.workspace)
        if current != snapshot.current_commit:
            logger.warning(
                "Commit changed: expected %s, got %s",
                snapshot.current_commit[:8],
                current[:8],
            )
            return False
        return True

    def has_untracked_user_files(self, snapshot: TaskSnapshot) -> bool:
        """Check for untracked files not created by this task."""
        untracked = _get_untracked_files(self.workspace)
        task_files = set(snapshot.changed_files)
        user_files = [f for f in untracked if f not in task_files]
        if user_files:
            logger.warning("Untracked user files found: %s", user_files)
            return True
        return False

    def rollback(self, snapshot: TaskSnapshot) -> RollbackEvidence:
        """
        Rollback workspace to snapshot state.

        Steps:
        1. Verify workspace identity
        2. Check for untracked user files
        3. Restore to base commit
        4. Remove task-created files
        5. Record audit evidence
        """
        start = time.time()
        snapshot.state = RollbackState.ROLLBACK_PENDING
        self._save_snapshot(snapshot)

        files_restored: list[str] = []
        files_removed: list[str] = []
        failure_reason = ""

        try:
            # Step 1: Verify workspace identity
            current_commit = _get_current_commit(self.workspace)
            if current_commit == "unknown":
                raise RollbackUnsafeError("Cannot determine current commit")

            # Step 2: Check for untracked user files
            if self.has_untracked_user_files(snapshot):
                raise RollbackUnsafeError(
                    "Workspace contains untracked user files — refusing rollback"
                )

            # Step 3: Restore to base commit
            diff_hash_before = _compute_diff_hash(
                self.workspace, _get_changed_files(self.workspace, snapshot.base_commit)
            )

            code, _, stderr = _git_run(
                ["checkout", "--force", snapshot.base_commit],
                self.workspace,
                trusted=True,
            )
            if code != 0:
                raise RollbackError(f"Git checkout failed: {stderr}")

            # Recreate audit directory (checkout may have removed it)
            self._audit_dir.mkdir(parents=True, exist_ok=True)

            files_restored = _get_changed_files(self.workspace, snapshot.base_commit)

            # Step 4: Remove task-created files
            for f in snapshot.changed_files:
                fp = self.workspace / f
                if fp.exists() and f not in files_restored:
                    try:
                        fp.unlink()
                        files_removed.append(f)
                    except OSError:
                        pass

            # Step 5: Record success
            diff_hash_after = _compute_diff_hash(
                self.workspace, _get_changed_files(self.workspace, snapshot.base_commit)
            )

            evidence = RollbackEvidence(
                task_id=self.task_id,
                operation="rollback",
                base_commit=snapshot.base_commit,
                current_commit=current_commit,
                diff_hash_before=diff_hash_before,
                diff_hash_after=diff_hash_after,
                files_restored=files_restored,
                files_removed=files_removed,
                exit_code=0,
                started_at=start,
                finished_at=time.time(),
            )

            snapshot.state = RollbackState.ROLLED_BACK
            self._save_snapshot(snapshot)
            self._save_evidence(evidence)

            logger.info(
                "Rollback complete: task=%s restored=%d removed=%d",
                self.task_id,
                len(files_restored),
                len(files_removed),
            )
            return evidence

        except Exception as e:
            failure_reason = str(e)
            snapshot.state = RollbackState.ROLLBACK_FAILED
            self._save_snapshot(snapshot)

            evidence = RollbackEvidence(
                task_id=self.task_id,
                operation="rollback",
                base_commit=snapshot.base_commit,
                current_commit=_get_current_commit(self.workspace),
                diff_hash_before="unknown",
                diff_hash_after="unknown",
                files_restored=files_restored,
                files_removed=files_removed,
                exit_code=1,
                started_at=start,
                finished_at=time.time(),
                failure_reason=failure_reason,
            )
            self._save_evidence(evidence)

            logger.error("Rollback failed: task=%s reason=%s", self.task_id, failure_reason)
            return evidence

    def mark_completed(self, snapshot: TaskSnapshot) -> None:
        """Mark task as completed (no rollback needed)."""
        snapshot.state = RollbackState.COMPLETED
        self._save_snapshot(snapshot)

    def mark_failed(self, snapshot: TaskSnapshot, reason: str = "") -> None:
        """Mark task as failed (rollback pending)."""
        snapshot.state = RollbackState.FAILED
        self._save_snapshot(snapshot)
        logger.info("Task marked failed: %s reason=%s", self.task_id, reason)

    def _save_snapshot(self, snapshot: TaskSnapshot) -> None:
        path = self._audit_dir / "snapshot.json"
        path.write_text(snapshot.to_json(), encoding="utf-8")

    def _save_evidence(self, evidence: RollbackEvidence) -> None:
        path = self._audit_dir / f"rollback_{int(time.time())}.json"
        path.write_text(evidence.to_json(), encoding="utf-8")

    def get_snapshot(self) -> TaskSnapshot | None:
        path = self._audit_dir / "snapshot.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        snap = TaskSnapshot(
            task_id=data["task_id"],
            project_id=data["project_id"],
            workspace=Path(data["workspace"]),
            base_commit=data["base_commit"],
            changed_files=data.get("changed_files", []),
            diff_hash=data.get("diff_hash", "unknown"),
        )
        snap.current_commit = data.get("current_commit", data["base_commit"])
        snap.created_at = data.get("created_at", "")
        snap.state = RollbackState(data.get("state", "active"))
        return snap

    def get_evidence(self) -> list[RollbackEvidence]:
        evidences = []
        for p in sorted(self._audit_dir.glob("rollback_*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            evidences.append(
                RollbackEvidence(
                    task_id=data["task_id"],
                    operation=data["operation"],
                    base_commit=data["base_commit"],
                    current_commit=data["current_commit"],
                    diff_hash_before=data.get("diff_hash_before", "unknown"),
                    diff_hash_after=data.get("diff_hash_after", "unknown"),
                    files_restored=data.get("files_restored", []),
                    files_removed=data.get("files_removed", []),
                    exit_code=data.get("exit_code", 1),
                    started_at=0,
                    finished_at=0,
                    failure_reason=data.get("failure_reason", ""),
                )
            )
        return evidences


# ── Automatic Rollback Hooks ────────────────────────────────────
def auto_rollback_on_failure(
    snapshot: TaskSnapshot,
    manager: RollbackManager,
    failure_type: str,
) -> RollbackEvidence | None:
    """
    Automatic rollback hook for failures.
    Called by agent pipeline when editor/tester/security/merge fails.
    """
    if snapshot.state == RollbackState.COMPLETED:
        return None

    logger.info("Auto-rollback triggered: task=%s type=%s", snapshot.task_id, failure_type)
    manager.mark_failed(snapshot, reason=failure_type)
    return manager.rollback(snapshot)
