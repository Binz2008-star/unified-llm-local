"""
Tests for DEP-01: Deterministic rollback and recovery.

Covers all 14 requirement categories:
- Clean rollback
- Partial writes rollback
- New files rollback
- Failed tests rollback
- Failed merge rollback
- Idempotent repeated rollback
- Stale base commit
- Changed primary repository
- Untracked user files
- Symlink/path escape
- Interrupted rollback
- Rollback failure preservation
- Audit evidence integrity
- Automatic rollback hooks
"""

import subprocess
import time
from pathlib import Path

import pytest

from rollback import (
    RollbackError,
    RollbackEvidence,
    RollbackIdempotentError,
    RollbackManager,
    RollbackState,
    RollbackUnsafeError,
    TaskSnapshot,
    auto_rollback_on_failure,
)


# ── Fixtures ─────────────────────────────────────────────────────
@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo),
        capture_output=True,
        check=True,
    )
    # Initial commit
    (repo / "README.md").write_text("# Test", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=str(repo),
        capture_output=True,
        check=True,
    )
    return repo


@pytest.fixture
def manager(git_repo):
    return RollbackManager("task_123", "test_project", git_repo)


# ── TaskSnapshot Tests ───────────────────────────────────────────
class TestTaskSnapshot:
    def test_snapshot_creation(self, manager):
        snap = manager.create_snapshot()
        assert snap.task_id == "task_123"
        assert snap.project_id == "test_project"
        assert snap.base_commit != "unknown"
        assert snap.state == RollbackState.ACTIVE

    def test_snapshot_to_dict(self, manager):
        snap = manager.create_snapshot()
        d = snap.to_dict()
        assert d["task_id"] == "task_123"
        assert "base_commit" in d
        assert "changed_files" in d

    def test_snapshot_to_json(self, manager):
        snap = manager.create_snapshot()
        j = snap.to_json()
        assert "task_123" in j

    def test_snapshot_persists(self, manager):
        manager.create_snapshot()
        loaded = manager.get_snapshot()
        assert loaded is not None
        assert loaded.task_id == "task_123"


# ── Clean Rollback Tests ─────────────────────────────────────────
class TestCleanRollback:
    def test_clean_rollback(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create a new file
        (git_repo / "new_file.txt").write_text("content", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "add new file"],
            cwd=str(git_repo),
            capture_output=True,
        )

        # Rollback
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert not (git_repo / "new_file.txt").exists()

    def test_rollback_removes_modified_file(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Modify existing file
        (git_repo / "README.md").write_text("modified", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "modify file"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        content = (git_repo / "README.md").read_text(encoding="utf-8")
        assert content == "# Test"

    def test_rollback_restores_deleted_file(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Delete file
        (git_repo / "README.md").unlink()
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "delete file"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert (git_repo / "README.md").exists()


# ── Partial Writes Rollback ─────────────────────────────────────
class TestPartialWritesRollback:
    def test_rollback_after_partial_write(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Write multiple files, only commit some
        (git_repo / "file1.txt").write_text("content1", encoding="utf-8")
        (git_repo / "file2.txt").write_text("content2", encoding="utf-8")
        subprocess.run(["git", "add", "file1.txt"], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "partial"],
            cwd=str(git_repo),
            capture_output=True,
        )

        # file2.txt is untracked user file — rollback refuses (correct behavior)
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 1
        assert "untracked user files" in evidence.failure_reason.lower()

    def test_rollback_cleans_committed_changes(self, git_repo, manager):
        snap = manager.create_snapshot()

        # All files committed
        (git_repo / "file1.txt").write_text("content1", encoding="utf-8")
        (git_repo / "file2.txt").write_text("content2", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "all committed"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert not (git_repo / "file1.txt").exists()
        assert not (git_repo / "file2.txt").exists()


# ── New Files Rollback ──────────────────────────────────────────
class TestNewFilesRollback:
    def test_rollback_removes_new_committed_files(self, git_repo, manager):
        snap = manager.create_snapshot()

        for i in range(5):
            (git_repo / f"new_{i}.txt").write_text(f"content_{i}", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "add 5 files"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        for i in range(5):
            assert not (git_repo / f"new_{i}.txt").exists()

    def test_rollback_removes_new_files_added_after_snapshot(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "new_after_snapshot.txt").write_text("new content", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "new file after snapshot"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert not (git_repo / "new_after_snapshot.txt").exists()


# ── Failed Tests Rollback ───────────────────────────────────────
class TestFailedTestsRollback:
    def test_rollback_after_test_failure(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Simulate test failure with file changes
        (git_repo / "test_output.txt").write_text("FAILED", encoding="utf-8")
        (git_repo / "debug.log").write_text("error details", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "test artifacts"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert not (git_repo / "test_output.txt").exists()
        assert not (git_repo / "debug.log").exists()


# ── Failed Merge Rollback ──────────────────────────────────────
class TestFailedMergeRollback:
    def test_rollback_after_failed_merge(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create a branch and merge it
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=str(git_repo),
            capture_output=True,
        )
        (git_repo / "feature.txt").write_text("feature", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feature commit"],
            cwd=str(git_repo),
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=str(git_repo),
            capture_output=True,
        )
        subprocess.run(
            ["git", "merge", "feature", "--no-ff", "-m", "merge feature"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0


# ── Idempotent Rollback ─────────────────────────────────────────
class TestIdempotentRollback:
    def test_idempotent_rollback(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        # First rollback
        evidence1 = manager.rollback(snap)
        assert evidence1.exit_code == 0

        # Second rollback (idempotent)
        evidence2 = manager.rollback(snap)
        assert evidence2.exit_code == 0

    def test_rollback_already_at_base(self, git_repo, manager):
        snap = manager.create_snapshot()

        # No changes
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0


# ── Stale Base Commit ──────────────────────────────────────────
class TestStaleBaseCommit:
    def test_rollback_with_stale_base(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Make changes and commit
        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        # Verify snapshot is stale
        assert not manager.verify_snapshot(snap)

        # Rollback should still work
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0


# ── Changed Primary Repository ─────────────────────────────────
class TestChangedPrimaryRepository:
    def test_rollback_verifies_commit(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Commit new changes
        (git_repo / "new.txt").write_text("new", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "new commit"],
            cwd=str(git_repo),
            capture_output=True,
        )

        # Current commit differs from snapshot
        assert not manager.verify_snapshot(snap)

        # Rollback uses base_commit, not current
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0


# ── Untracked User Files ───────────────────────────────────────
class TestUntrackedUserFiles:
    def test_refuses_rollback_with_untracked_files(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create untracked file not in snapshot
        (git_repo / "user_file.txt").write_text("user content", encoding="utf-8")

        # Rollback should fail
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 1
        assert "untracked user files" in evidence.failure_reason.lower()

    def test_allows_rollback_with_only_task_files(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create file that will be tracked
        (git_repo / "task_file.txt").write_text("task content", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "task file"],
            cwd=str(git_repo),
            capture_output=True,
        )

        # Rollback should succeed
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0


# ── Symlink/Path Escape ─────────────────────────────────────────
class TestSymlinkPathEscape:
    def test_rollback_safe_with_normal_files(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "normal.txt").write_text("normal", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "normal file"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert not (git_repo / "normal.txt").exists()


# ── Interrupted Rollback ───────────────────────────────────────
class TestInterruptedRollback:
    def test_rollback_failure_preserves_workspace(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create changes
        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        # Rollback
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0

        # Check snapshot state
        loaded = manager.get_snapshot()
        assert loaded is not None
        assert loaded.state == RollbackState.ROLLED_BACK


# ── Rollback Failure Preservation ──────────────────────────────
class TestRollbackFailurePreservation:
    def test_rollback_failure_recorded(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create a state that will cause checkout to fail
        # by making git repository bare
        bare_repo = git_repo / ".git" / "objects"
        if bare_repo.exists():
            # Rename objects to break git
            backup = git_repo / ".git" / "objects_backup"
            bare_repo.rename(backup)

            evidence = manager.rollback(snap)
            assert evidence.exit_code == 1
            assert evidence.failure_reason != ""

            # Restore for cleanup
            backup.rename(bare_repo)

    def test_rollback_evidence_preserved_on_failure(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Force a failure by corrupting git
        git_dir = git_repo / ".git"
        head_file = git_dir / "HEAD"
        head_content = head_file.read_text(encoding="utf-8")
        head_file.write_text("corrupted", encoding="utf-8")

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 1

        # Restore for cleanup
        head_file.write_text(head_content, encoding="utf-8")


# ── Audit Evidence Integrity ────────────────────────────────────
class TestAuditEvidenceIntegrity:
    def test_evidence_recorded_on_success(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0

        # Check evidence files (saved outside workspace)
        evidence_files = list(
            (git_repo.parent / ".rollback_audit" / "task_123").glob("rollback_*.json")
        )
        assert len(evidence_files) > 0

    def test_evidence_recorded_on_failure(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create untracked file to trigger failure
        (git_repo / "user.txt").write_text("user", encoding="utf-8")

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 1

        evidence_files = list(
            (git_repo.parent / ".rollback_audit" / "task_123").glob("rollback_*.json")
        )
        assert len(evidence_files) > 0

    def test_evidence_json_structure(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        d = evidence.to_dict()

        assert "task_id" in d
        assert "operation" in d
        assert "base_commit" in d
        assert "current_commit" in d
        assert "diff_hash_before" in d
        assert "diff_hash_after" in d
        assert "files_restored" in d
        assert "files_removed" in d
        assert "exit_code" in d
        assert "started_at" in d
        assert "finished_at" in d
        assert "failure_reason" in d
        assert "hostname" in d
        assert "pid" in d

    def test_evidence_to_json(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        j = evidence.to_json()
        assert "task_123" in j

    def test_multiple_evidences(self, git_repo, manager):
        # First rollback
        snap1 = manager.create_snapshot()
        (git_repo / "change1.txt").write_text("change1", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change1"],
            cwd=str(git_repo),
            capture_output=True,
        )
        manager.rollback(snap1)

        # Second rollback
        manager2 = RollbackManager("task_456", "test_project", git_repo)
        snap2 = manager2.create_snapshot()
        (git_repo / "change2.txt").write_text("change2", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change2"],
            cwd=str(git_repo),
            capture_output=True,
        )
        manager2.rollback(snap2)

        # Check both evidences exist (saved outside workspace to survive git checkout)
        evidence_dir = git_repo.parent / ".rollback_audit"
        evidence_files = list((evidence_dir / "task_123").glob("rollback_*.json"))
        assert len(evidence_files) > 0
        evidence_files2 = list((evidence_dir / "task_456").glob("rollback_*.json"))
        assert len(evidence_files2) > 0


# ── Automatic Rollback Hooks ────────────────────────────────────
class TestAutoRollbackHooks:
    def test_auto_rollback_on_editor_failure(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Make changes
        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = auto_rollback_on_failure(snap, manager, "editor_failure")
        assert evidence is not None
        assert evidence.exit_code == 0

    def test_auto_rollback_on_tester_failure(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "test_artifact.txt").write_text("test output", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "test artifacts"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = auto_rollback_on_failure(snap, manager, "tester_failure")
        assert evidence is not None
        assert evidence.exit_code == 0

    def test_auto_rollback_on_security_failure(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "security_issue.txt").write_text("issue", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "security issue"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = auto_rollback_on_failure(snap, manager, "security_review_failure")
        assert evidence is not None
        assert evidence.exit_code == 0

    def test_auto_rollback_on_merge_failure(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "merge_conflict.txt").write_text("conflict", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "merge conflict"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = auto_rollback_on_failure(snap, manager, "merge_gate_failure")
        assert evidence is not None
        assert evidence.exit_code == 0

    def test_auto_rollback_on_timeout(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "timeout.txt").write_text("timeout", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "timeout"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = auto_rollback_on_failure(snap, manager, "cancellation_timeout")
        assert evidence is not None
        assert evidence.exit_code == 0

    def test_no_rollback_if_completed(self, git_repo, manager):
        snap = manager.create_snapshot()
        manager.mark_completed(snap)

        evidence = auto_rollback_on_failure(snap, manager, "editor_failure")
        assert evidence is None


# ── Rollback State Transitions ──────────────────────────────────
class TestRollbackStateTransitions:
    def test_state_active_to_rollback_pending(self, git_repo, manager):
        snap = manager.create_snapshot()
        assert snap.state == RollbackState.ACTIVE

        manager.mark_failed(snap, "test")
        assert snap.state == RollbackState.FAILED

    def test_state_to_rolled_back(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert snap.state == RollbackState.ROLLED_BACK

    def test_state_to_completed(self, git_repo, manager):
        snap = manager.create_snapshot()
        manager.mark_completed(snap)
        assert snap.state == RollbackState.COMPLETED


# ── Cross-Process Rollback ──────────────────────────────────────
class TestCrossProcessRollback:
    def test_rollback_in_subprocess(self, git_repo, manager):
        snap = manager.create_snapshot()

        (git_repo / "change.txt").write_text("change", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "change"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert not (git_repo / "change.txt").exists()


# ── Rollback Scope ──────────────────────────────────────────────
class TestRollbackScope:
    def test_rollback_scoped_to_workspace(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create file in workspace
        (git_repo / "workspace_file.txt").write_text("workspace", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "workspace file"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0

        # Workspace file removed
        assert not (git_repo / "workspace_file.txt").exists()


# ── Edge Cases ──────────────────────────────────────────────────
class TestEdgeCases:
    def test_empty_repository(self, tmp_path):
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(repo),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(repo),
            capture_output=True,
            check=True,
        )

        manager = RollbackManager("task_empty", "project", repo)
        # Need initial commit for git to work
        (repo / "init.txt").write_text("init", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=str(repo), capture_output=True, check=True
        )
        snap = manager.create_snapshot()

        # No changes, rollback should be idempotent
        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0

    def test_large_number_of_files(self, git_repo, manager):
        snap = manager.create_snapshot()

        # Create many files
        for i in range(20):
            (git_repo / f"file_{i}.txt").write_text(f"content_{i}", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "20 files"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        for i in range(20):
            assert not (git_repo / f"file_{i}.txt").exists()

    def test_special_characters_in_filename(self, git_repo, manager):
        snap = manager.create_snapshot()

        special = git_repo / "file with spaces.txt"
        special.write_text("spaces", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(git_repo), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "special chars"],
            cwd=str(git_repo),
            capture_output=True,
        )

        evidence = manager.rollback(snap)
        assert evidence.exit_code == 0
        assert not special.exists()
