"""LOCK-01/02: Tests for cross-process MergeLock."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from merge_lock import (
    LockAcquisitionError,
    LockMalformedError,
    LockOwnershipError,
    MergeLock,
    merge_lock,
)


@pytest.fixture
def make_lock(tmp_path):
    """Factory for MergeLock instances with isolated lock dirs."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)

    def _make(project_id="test-project", task_id="task_abc", **kwargs):
        lock = MergeLock(project_id, task_id, repo_path=repo, **kwargs)
        return lock

    return _make


class TestAtomicAcquisition:
    def test_acquire_creates_lock(self, make_lock):
        lock = make_lock()
        assert lock.acquire() is True
        assert lock._lock_path.exists()
        lock.release()

    def test_acquire_returns_false_when_held(self, make_lock):
        lock1 = make_lock(task_id="task_1")
        lock2 = make_lock(task_id="task_2")

        assert lock1.acquire() is True
        assert lock2.acquire() is False

        lock1.release()

    def test_acquire_after_release(self, make_lock):
        lock1 = make_lock(task_id="task_1")
        lock2 = make_lock(task_id="task_2")

        assert lock1.acquire() is True
        lock1.release()

        assert lock2.acquire() is True
        lock2.release()

    def test_reentrant_acquire(self, make_lock):
        lock = make_lock()
        assert lock.acquire() is True
        # Re-entrant with same lock_id
        assert lock.acquire() is True
        lock.release()

    def test_different_projects_can_lock_concurrently(self, make_lock):
        lock1 = make_lock(project_id="project-a", task_id="task_1")
        lock2 = make_lock(project_id="project-b", task_id="task_2")

        assert lock1.acquire() is True
        assert lock2.acquire() is True

        lock1.release()
        lock2.release()


class TestLockMetadata:
    def test_metadata_contains_required_fields(self, make_lock):
        lock = make_lock()
        lock.acquire()

        info = lock.get_lock_info()
        assert info is not None
        for field in (
            "lock_id",
            "pid",
            "hostname",
            "task_id",
            "project_id",
            "created_at",
            "expires_at",
            "operation",
        ):
            assert field in info
        assert info["operation"] == "merge"

        lock.release()

    def test_metadata_pid_is_integer(self, make_lock):
        lock = make_lock()
        lock.acquire()

        info = lock.get_lock_info()
        assert isinstance(info["pid"], int)

        lock.release()

    def test_metadata_no_secrets(self, make_lock):
        lock = make_lock()
        lock.acquire()

        info = lock.get_lock_info()
        info_str = json.dumps(info).lower()

        assert "password" not in info_str
        assert "secret" not in info_str
        assert "dsn" not in info_str
        assert "neon_" not in info_str

        lock.release()


class TestOwnershipCheckedRelease:
    def test_owner_can_release(self, make_lock):
        lock = make_lock()
        lock.acquire()
        assert lock.release() is True

    def test_non_owner_cannot_release(self, make_lock):
        lock1 = make_lock(task_id="task_1")
        lock2 = make_lock(task_id="task_2")

        lock1.acquire()

        with pytest.raises(LockOwnershipError):
            lock2.release()

        lock1.release()

    def test_force_release_by_non_owner(self, make_lock):
        lock1 = make_lock(task_id="task_1")
        lock2 = make_lock(task_id="task_2")

        lock1.acquire()
        assert lock2.release(force=True) is True

        # lock1's release should be no-op (file already deleted)
        assert lock1.release() is True


class TestLeaseTTL:
    def test_expired_lock_with_dead_process_recoverable(self, make_lock):
        """Expired lock from dead process (non-existent PID) should be recoverable."""
        lock1 = make_lock(task_id="task_1", lease_ttl=1)
        lock1.acquire()

        # Manually expire the lock and fake a dead process
        info = lock1.get_lock_info()
        info["expires_at"] = time.time() - 10
        info["pid"] = 99999
        lock1._lock_path.write_text(json.dumps(info), encoding="utf-8")

        # Different task should be able to acquire
        lock2 = make_lock(task_id="task_2")
        assert lock2.acquire() is True
        lock2.release()

    def test_expired_lock_with_live_process_denied(self, make_lock):
        """Expired lock from live process (same pid) should be denied without force."""
        lock1 = make_lock(task_id="task_1", lease_ttl=1)
        lock1.acquire()

        # Manually expire but keep same pid (current process is alive)
        info = lock1.get_lock_info()
        info["expires_at"] = time.time() - 10
        lock1._lock_path.write_text(json.dumps(info), encoding="utf-8")

        lock2 = make_lock(task_id="task_2")
        with pytest.raises(LockAcquisitionError):
            lock2.acquire()

        # Force=True should succeed for expired lock from alive process
        lock3 = make_lock(task_id="task_3")
        assert lock3.acquire(force=True) is True
        lock3.release()

    def test_active_lock_cannot_be_force_recovered(self, make_lock):
        """Unexpired lock cannot be force-recovered."""
        lock1 = make_lock(task_id="task_1", lease_ttl=600)
        lock1.acquire()

        lock2 = make_lock(task_id="task_2")
        # Unexpired lock → deny even with force=True
        assert lock2.acquire(force=True) is False

        lock1.release()

    def test_renewal_extends_ttl(self, make_lock):
        lock = make_lock(lease_ttl=10)
        lock.acquire()

        now_before = time.time()
        info_before = lock.get_lock_info()
        expires_before = info_before["expires_at"]

        time.sleep(0.2)
        lock.renew()

        now_after = time.time()
        info_after = lock.get_lock_info()
        expires_after = info_after["expires_at"]

        # Renewal sets expires_at = now + lease_ttl
        # So expires_after should be approximately now_after + 10
        assert expires_after > now_after + 9.0
        # And expires_after should be significantly later than expires_before
        # (because we renewed after 0.2s, new expiry is ~10s from now)
        assert expires_after > expires_before
        lock.release()

    def test_lease_expiry_aborts(self, make_lock):
        lock = make_lock(lease_ttl=1)
        lock.acquire()

        info = lock.get_lock_info()
        info["expires_at"] = time.time() + 1
        lock._lock_path.write_text(json.dumps(info), encoding="utf-8")

        time.sleep(1.5)

        assert lock.is_locked() is False
        # Release should work (file still exists, just expired)
        lock.release()
        assert not lock._lock_path.exists()


class TestStaleLockRecovery:
    def test_malformed_lock_rejected(self, make_lock):
        lock = make_lock()
        lock._lock_path.write_text("not json {{{", encoding="utf-8")

        with pytest.raises(LockMalformedError):
            lock.acquire()

    def test_malformed_lock_force_recovered(self, make_lock):
        lock1 = make_lock(task_id="task_1")
        lock1._lock_path.write_text("not json", encoding="utf-8")

        lock2 = make_lock(task_id="task_2")
        assert lock2.acquire(force=True) is True
        lock2.release()

    def test_missing_fields_lock_rejected(self, make_lock):
        lock = make_lock()
        lock._lock_path.write_text(
            json.dumps({"lock_id": "abc", "pid": 123}),
            encoding="utf-8",
        )

        with pytest.raises(LockMalformedError):
            lock.acquire()

    def test_pid_reuse_does_not_grant_ownership(self, make_lock):
        """PID reuse without matching lock_id should not grant ownership."""
        lock1 = make_lock(task_id="task_1")
        lock1.acquire()

        # Simulate PID reuse: change lock_id but keep same pid
        info = lock1.get_lock_info()
        info["pid"] = os.getpid()
        info["lock_id"] = "different-lock-id"
        lock1._lock_path.write_text(json.dumps(info), encoding="utf-8")

        lock2 = make_lock(task_id="task_2")
        # Should deny because lock_id differs (even though pid matches)
        assert lock2.acquire() is False

        # Clean up
        lock1._lock_path.unlink(missing_ok=True)


class TestExceptionSafety:
    def test_exception_releases_lock(self, make_lock):
        lock = make_lock()
        lock.acquire()

        try:
            raise ValueError("test error")
        except ValueError:
            pass
        finally:
            lock.release()

        assert lock.is_locked() is False

    def test_context_manager_releases_on_exception(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()

        lock = MergeLock("test-project", "task_1", repo_path=repo)
        try:
            with lock:
                assert lock.is_mine() is True
                raise ValueError("test")
        except ValueError:
            pass

        assert not lock._lock_path.exists()


class TestLockPath:
    def test_lock_outside_repository(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        lock = MergeLock("my-project", "task_1", repo_path=repo)

        assert ".second-brain-locks" in str(lock._lock_path)
        assert str(repo) not in str(lock._lock_path)

    def test_no_repo_name_collision(self, tmp_path):
        lock1 = MergeLock("org/project-a", "task_1", repo_path=tmp_path)
        lock2 = MergeLock("org/project-b", "task_2", repo_path=tmp_path)

        assert lock1._lock_path != lock2._lock_path

    def test_special_chars_in_project_id(self, tmp_path):
        lock = MergeLock("org/sub:project", "task_1", repo_path=tmp_path)
        assert lock.acquire() is True
        lock.release()


class TestCrossProcessContention:
    def test_two_processes_cannot_acquire_same_lock(self, tmp_path):
        """Prove mutual exclusion with real subprocesses."""
        repo = tmp_path / "repo"
        repo.mkdir()

        lock1 = MergeLock("test-project", "main_task", repo_path=repo)
        lock1.acquire()

        code = f"""\
import sys
sys.path.insert(0, {str(Path(__file__).parent.parent)!r})
from merge_lock import MergeLock
from pathlib import Path

lock = MergeLock("test-project", "subprocess_task", repo_path=Path({str(repo)!r}))
result = lock.acquire()
print("ACQUIRED" if result else "DENIED")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert "DENIED" in result.stdout
        lock1.release()

    def test_sequential_acquisition_works(self, tmp_path):
        """Two processes acquiring sequentially should work."""
        repo = tmp_path / "repo"
        repo.mkdir()

        code = f"""\
import sys
sys.path.insert(0, {str(Path(__file__).parent.parent)!r})
from merge_lock import MergeLock
from pathlib import Path
import time

lock = MergeLock("test-project", "seq_task", repo_path=Path({str(repo)!r}))
result = lock.acquire()
if result:
    time.sleep(0.5)
    lock.release()
    print("SUCCESS")
else:
    print("FAILED")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert "SUCCESS" in result.stdout

    def test_dead_process_lock_recoverable_via_force(self, tmp_path):
        """Lock from dead process (fake pid) should be recoverable with force."""
        repo = tmp_path / "repo"
        repo.mkdir()

        lock1 = MergeLock("test-project", "dead_task", repo_path=repo)
        lock1.acquire()

        # Fake a dead process (non-existent PID) and expired lease
        info = lock1.get_lock_info()
        info["pid"] = 99999
        info["expires_at"] = time.time() - 10
        lock1._lock_path.write_text(json.dumps(info), encoding="utf-8")

        # New task should recover (expired + dead process)
        lock2 = MergeLock("test-project", "new_task", repo_path=repo)
        assert lock2.acquire() is True
        lock2.release()
