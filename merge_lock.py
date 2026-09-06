"""
MergeLock — Cross-process mutual exclusion for merge/commit operations.

LOCK-01/02: Prevents two tasks from merging/committing to the same project
simultaneously, and handles stale locks safely.

Lock location: <repo_parent>/.second-brain-locks/<repo_identity>.merge.lock
"""

import json
import logging
import os
import platform
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

LOCK_DIR_NAME = ".second-brain-locks"
DEFAULT_LEASE_TTL_SECONDS = 600
RENEWAL_INTERVAL_SECONDS = 120
LOCK_FILE_SUFFIX = ".merge.lock"


class LockError(Exception):
    pass


class LockAcquisitionError(LockError):
    pass


class LockOwnershipError(LockError):
    pass


class LockStaleError(LockError):
    pass


class LockMalformedError(LockError):
    pass


# ── Platform-safe atomic file creation ───────────────────────────
def _atomic_create_lock(lock_path: Path, content: str) -> bool:
    """
    Atomically create a lock file. Returns True if created, False if exists.
    Uses O_CREAT | O_EXCL (works on both Unix and Windows).
    """
    try:
        fd = os.open(
            str(lock_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError as e:
        raise LockError(f"Failed to create lock: {e}") from e


def _read_lock_file(lock_path: Path) -> dict[str, Any] | None:
    """Read and parse lock file. Returns None if not found."""
    try:
        data = lock_path.read_text(encoding="utf-8")
        return json.loads(data)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise LockMalformedError(f"Lock file is malformed: {e}") from e


def _write_lock_file(lock_path: Path, metadata: dict[str, Any]) -> None:
    """Write lock metadata to file."""
    lock_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _is_process_alive(pid: int, hostname: str) -> bool:
    """Check if a process is alive. Does not trust PID alone."""
    if hostname != platform.node():
        return True

    if pid == os.getpid():
        return True

    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


# ── MergeLock class ─────────────────────────────────────────────
class MergeLock:
    """
    Cross-process mutual exclusion lock for merge/commit operations.

    Usage:
        lock = MergeLock("unified-llm-local", "task_abc")
        if lock.acquire():
            try:
                # perform merge
                ...
            finally:
                lock.release()
    """

    def __init__(
        self,
        project_id: str,
        task_id: str,
        *,
        lease_ttl: int = DEFAULT_LEASE_TTL_SECONDS,
        repo_path: Path | None = None,
    ):
        self.project_id = project_id
        self.task_id = task_id
        self.lease_ttl = lease_ttl
        self.lock_id: str | None = None
        self._lock_path: Path | None = None
        self._acquired = False
        self._renewal_timer: threading.Timer | None = None

        if repo_path:
            repo_parent = repo_path.parent
        else:
            repo_parent = Path.cwd().parent

        self._lock_dir = repo_parent / LOCK_DIR_NAME
        self._lock_dir.mkdir(parents=True, exist_ok=True)

        safe_name = project_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        self._lock_path = self._lock_dir / f"{safe_name}{LOCK_FILE_SUFFIX}"

    def acquire(self, *, force: bool = False) -> bool:
        """
        Attempt to acquire the lock.

        Stale-lock policy:
        - No lock exists → create and acquire
        - Unexpired lock, different owner → deny
        - Expired lock, owner alive → deny (process may still work)
        - Expired lock, owner dead → recover
        - Malformed lock → fail closed (raise), force=True → recover
        - Re-entrant (same lock_id + pid + hostname) → acquire

        Returns:
            True if lock acquired, False if held by another active process.

        Raises:
            LockAcquisitionError: If lock cannot be acquired.
            LockMalformedError: If existing lock is malformed and not force.
        """
        now = time.time()

        try:
            lock_data = _read_lock_file(self._lock_path)
        except LockMalformedError:
            if force:
                logger.warning("Force-acquiring malformed lock: %s", self._lock_path)
                try:
                    self._lock_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return self._create_lock(now)
            raise

        if lock_data is None:
            return self._create_lock(now)

        # Validate structure
        try:
            self._validate_lock_data(lock_data)
        except LockMalformedError:
            if force:
                logger.warning("Force-acquiring malformed lock: %s", self._lock_path)
                try:
                    self._lock_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return self._create_lock(now)
            raise

        expires_at = lock_data.get("expires_at", 0)
        owner_pid = lock_data.get("pid")
        owner_hostname = lock_data.get("hostname")
        owner_task = lock_data.get("task_id")

        # Re-entrant: same lock_id + pid + hostname
        if self._is_owner(lock_data):
            self.lock_id = lock_data["lock_id"]
            self._acquired = True
            self._start_renewal()
            return True

        # Unexpired lock from another owner → deny
        if now <= expires_at:
            logger.info(
                "Lock held by task %s (pid=%s, expires in %ds)",
                owner_task,
                owner_pid,
                int(expires_at - now),
            )
            return False

        # Expired lock — check if owner is alive
        owner_alive = _is_process_alive(owner_pid, owner_hostname)
        if owner_alive:
            if force:
                logger.warning(
                    "Force-acquiring expired lock from alive process (pid=%s)",
                    owner_pid,
                )
                try:
                    self._lock_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return self._create_lock(now)
            raise LockAcquisitionError(
                f"Lock held by active process {owner_pid} with expired lease"
            )

        # Expired lock from dead process → recover
        logger.info("Recovering stale lock from dead process (pid=%s)", owner_pid)
        # Delete the stale lock file before creating new one
        try:
            self._lock_path.unlink(missing_ok=True)
        except OSError:
            pass
        return self._create_lock(now)

    def release(self, *, force: bool = False) -> bool:
        """
        Release the lock. Only the owner can release.

        Args:
            force: If True, release even if not owner (for cleanup).

        Raises:
            LockOwnershipError: If not owner and force=False.
        """
        if not self._lock_path or not self._lock_path.exists():
            return True

        lock_data = _read_lock_file(self._lock_path)
        if lock_data is None:
            return True

        if not self._is_owner(lock_data) and not force:
            raise LockOwnershipError(
                f"Cannot release lock owned by task {lock_data.get('task_id')}"
            )

        self._stop_renewal()

        try:
            self._lock_path.unlink(missing_ok=True)
            logger.info("Lock released: %s", self.project_id)
            return True
        except OSError as e:
            logger.error("Failed to release lock: %s", e)
            return False

    def renew(self) -> bool:
        """Renew the lease TTL. Returns True if renewed."""
        if not self._acquired or not self._lock_path:
            return False

        lock_data = _read_lock_file(self._lock_path)
        if lock_data is None or not self._is_owner(lock_data):
            self._acquired = False
            return False

        now = time.time()
        lock_data["expires_at"] = now + self.lease_ttl
        lock_data["renewed_at"] = datetime.fromtimestamp(now, tz=UTC).isoformat()
        _write_lock_file(self._lock_path, lock_data)
        return True

    def get_lock_info(self) -> dict[str, Any] | None:
        """Get current lock metadata without acquiring."""
        if not self._lock_path:
            return None
        return _read_lock_file(self._lock_path)

    def is_locked(self) -> bool:
        """Check if lock is currently held (by anyone) and unexpired."""
        if not self._lock_path or not self._lock_path.exists():
            return False
        lock_data = _read_lock_file(self._lock_path)
        if lock_data is None:
            return False
        return time.time() <= lock_data.get("expires_at", 0)

    def is_mine(self) -> bool:
        """Check if we hold this lock."""
        if not self._lock_path or not self._lock_path.exists():
            return False
        lock_data = _read_lock_file(self._lock_path)
        if lock_data is None:
            return False
        return self._is_owner(lock_data)

    # ── Private helpers ──────────────────────────────────────────
    def _create_lock(self, now: float) -> bool:
        """Create a new lock file with metadata."""
        self.lock_id = str(uuid.uuid4())
        now_dt = datetime.fromtimestamp(now, tz=UTC)

        metadata = {
            "lock_id": self.lock_id,
            "pid": os.getpid(),
            "hostname": platform.node(),
            "task_id": self.task_id,
            "project_id": self.project_id,
            "operation": "merge",
            "created_at": now_dt.isoformat(),
            "expires_at": now + self.lease_ttl,
            "renewed_at": now_dt.isoformat(),
        }

        if _atomic_create_lock(self._lock_path, json.dumps(metadata, indent=2)):
            self._acquired = True
            self._start_renewal()
            logger.info(
                "Lock acquired: project=%s task=%s pid=%d",
                self.project_id,
                self.task_id,
                os.getpid(),
            )
            return True

        return False

    def _is_owner(self, lock_data: dict) -> bool:
        """Check if we own this lock (by lock_id + pid + hostname)."""
        return (
            lock_data.get("lock_id") == self.lock_id
            and lock_data.get("pid") == os.getpid()
            and lock_data.get("hostname") == platform.node()
        )

    def _validate_lock_data(self, lock_data: dict) -> None:
        """Validate lock file structure."""
        required = {"lock_id", "pid", "hostname", "task_id", "project_id", "expires_at"}
        if not required.issubset(lock_data.keys()):
            missing = required - lock_data.keys()
            raise LockMalformedError(f"Lock missing required fields: {missing}")

        if not isinstance(lock_data["pid"], int):
            raise LockMalformedError("Lock pid must be an integer")

    def _start_renewal(self) -> None:
        """Start periodic lease renewal."""
        self._stop_renewal()

        def _renew():
            if self._acquired:
                self.renew()
                self._renewal_timer = threading.Timer(RENEWAL_INTERVAL_SECONDS, _renew)
                self._renewal_timer.daemon = True
                self._renewal_timer.start()

        self._renewal_timer = threading.Timer(RENEWAL_INTERVAL_SECONDS, _renew)
        self._renewal_timer.daemon = True
        self._renewal_timer.start()

    def _stop_renewal(self) -> None:
        """Stop periodic lease renewal."""
        if self._renewal_timer:
            self._renewal_timer.cancel()
            self._renewal_timer = None

    def __enter__(self):
        if not self.acquire():
            raise LockAcquisitionError(f"Cannot acquire lock for {self.project_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    def __del__(self):
        self._stop_renewal()


def merge_lock(
    project_id: str,
    task_id: str,
    **kwargs,
):
    """Context manager for merge operations."""
    return MergeLock(project_id, task_id, **kwargs)
