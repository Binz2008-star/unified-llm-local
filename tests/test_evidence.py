"""P1.2: Tests for deterministic test evidence."""

import asyncio
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from test_evidence import (
    PolicyGate,
    TestEvidence,
    Verdict,
    collect_evidence,
    load_evidence,
    save_evidence,
)


def _make_evidence(
    task_id: str = "task_1",
    command: tuple[str, ...] = ("pytest", "-q"),
    exit_code: int = 0,
    timed_out: bool = False,
    workspace: str = "/tmp/workspace",
    base_commit: str = "abc123",
    current_commit: str = "def456",
    diff_hash: str = "hash1",
) -> TestEvidence:
    """Create a TestEvidence for testing."""
    now = time.time()
    return collect_evidence(
        task_id=task_id,
        command=command,
        exit_code=exit_code,
        timed_out=timed_out,
        started_at=now - 1,
        finished_at=now,
        stdout="test output",
        stderr="",
        workspace=Path(workspace),
        base_commit=base_commit,
        current_commit=current_commit,
        diff_hash=diff_hash,
    )


class TestEvidenceModel:
    def test_evidence_is_immutable(self):
        e = _make_evidence()
        with pytest.raises(AttributeError):
            e.exit_code = 1

    def test_evidence_passed_success(self):
        e = _make_evidence(exit_code=0, timed_out=False)
        assert e.passed is True

    def test_evidence_passed_failure(self):
        e = _make_evidence(exit_code=1, timed_out=False)
        assert e.passed is False

    def test_evidence_passed_timeout(self):
        e = _make_evidence(exit_code=0, timed_out=True)
        assert e.passed is False

    def test_evidence_to_dict(self):
        e = _make_evidence()
        d = e.to_dict()
        assert d["task_id"] == "task_1"
        assert d["exit_code"] == 0
        assert "command" in d

    def test_evidence_to_json(self):
        e = _make_evidence()
        j = e.to_json()
        data = json.loads(j)
        assert data["task_id"] == "task_1"

    def test_evidence_sha256_computed(self):
        e = _make_evidence()
        expected = hashlib.sha256(b"test output").hexdigest()
        assert e.stdout_sha256 == expected

    def test_evidence_stderr_sha256_computed(self):
        e = _make_evidence()
        expected = hashlib.sha256(b"").hexdigest()
        assert e.stderr_sha256 == expected


class TestEvidencePersistence:
    def test_save_and_load(self, tmp_path):
        e = _make_evidence()
        path = save_evidence(e, tmp_path / "evidence")
        assert path.exists()

        loaded = load_evidence(path)
        assert loaded.task_id == e.task_id
        assert loaded.exit_code == e.exit_code
        assert loaded.stdout_sha256 == e.stdout_sha256

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_evidence(Path("/nonexistent/evidence.json"))

    def test_load_tampered_stdout(self, tmp_path):
        e = _make_evidence()
        evidence_dir = tmp_path / "evidence"
        path = save_evidence(e, evidence_dir)

        # Tamper with stdout artifact (using the path from evidence)
        stdout_path = Path(e.stdout_path)
        stdout_path.write_text("tampered output", encoding="utf-8")

        with pytest.raises(ValueError, match="tampered"):
            load_evidence(path)

    def test_artifacts_created(self, tmp_path):
        e = _make_evidence()
        # Artifacts are created by collect_evidence, check they exist
        assert Path(e.stdout_path).exists()
        assert Path(e.stderr_path).exists()


class TestPolicyGate:
    def test_no_evidence_fails(self):
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        verdict, issues = gate.evaluate([])
        assert verdict == Verdict.FAIL
        assert "No evidence" in issues[0]

    def test_missing_command_fails(self):
        gate = PolicyGate(required_commands=frozenset({("pytest",), ("ruff",)}))
        evidence = [_make_evidence(command=("pytest",))]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL
        assert any("Missing" in i for i in issues)

    def test_all_commands_present_passes(self):
        gate = PolicyGate(required_commands=frozenset({("pytest",), ("ruff",)}))
        evidence = [
            _make_evidence(command=("pytest",)),
            _make_evidence(command=("ruff",)),
        ]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.PASS

    def test_non_zero_exit_code_fails(self):
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        evidence = [_make_evidence(command=("pytest",), exit_code=1)]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL
        assert any("failed" in i.lower() for i in issues)

    def test_timeout_fails(self):
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        evidence = [_make_evidence(command=("pytest",), timed_out=True)]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL
        assert any("timed out" in i.lower() for i in issues)

    def test_diff_hash_mismatch_fails(self):
        gate = PolicyGate(
            required_commands=frozenset({("pytest",)}),
            required_diff_hash="expected_hash",
        )
        evidence = [_make_evidence(command=("pytest",), diff_hash="wrong_hash")]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL
        assert any("Diff hash" in i for i in issues)

    def test_diff_hash_match_passes(self):
        gate = PolicyGate(
            required_commands=frozenset({("pytest",)}),
            required_diff_hash="expected_hash",
        )
        evidence = [_make_evidence(command=("pytest",), diff_hash="expected_hash")]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.PASS

    def test_base_commit_mismatch_fails(self):
        gate = PolicyGate(
            required_commands=frozenset({("pytest",)}),
            required_base_commit="abc123",
        )
        evidence = [_make_evidence(command=("pytest",), base_commit="wrong")]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL
        assert any("Base commit" in i for i in issues)

    def test_conflicting_task_ids_fails(self):
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        evidence = [
            _make_evidence(task_id="task_1", command=("pytest",)),
            _make_evidence(task_id="task_2", command=("pytest",)),
        ]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL
        assert any("Conflicting task" in i for i in issues)

    def test_conflicting_workspaces_fails(self):
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        evidence = [
            _make_evidence(command=("pytest",), workspace="/tmp/a"),
            _make_evidence(command=("pytest",), workspace="/tmp/b"),
        ]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL
        assert any("Conflicting workspace" in i for i in issues)

    def test_missing_artifact_fails(self, tmp_path):
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        e = _make_evidence(command=("pytest",))
        evidence_dir = tmp_path / "evidence"
        path = save_evidence(e, evidence_dir)

        # Delete stdout artifact
        Path(e.stdout_path).unlink()

        loaded = load_evidence(path)
        verdict, issues = gate.evaluate([loaded])
        assert verdict == Verdict.FAIL
        assert any("Missing stdout" in i for i in issues)


class TestEvidenceFromExecution:
    def test_collect_evidence_computes_sha256(self):
        e = collect_evidence(
            task_id="test",
            command=("echo", "hello"),
            exit_code=0,
            timed_out=False,
            started_at=time.time(),
            finished_at=time.time(),
            stdout="hello\n",
            stderr="",
            workspace=Path("/tmp"),
        )
        expected = hashlib.sha256(b"hello\n").hexdigest()
        assert e.stdout_sha256 == expected

    def test_collect_evidence_records_platform(self):
        e = collect_evidence(
            task_id="test",
            command=("echo",),
            exit_code=0,
            timed_out=False,
            started_at=time.time(),
            finished_at=time.time(),
            stdout="",
            stderr="",
            workspace=Path("/tmp"),
        )
        assert e.platform in ("Windows", "Linux", "Darwin")

    def test_collect_evidence_records_pid(self):
        e = collect_evidence(
            task_id="test",
            command=("echo",),
            exit_code=0,
            timed_out=False,
            started_at=time.time(),
            finished_at=time.time(),
            stdout="",
            stderr="",
            workspace=Path("/tmp"),
        )
        assert e.pid == os.getpid()

    def test_collect_evidence_saves_artifacts(self, tmp_path):
        e = collect_evidence(
            task_id="test",
            command=("echo",),
            exit_code=0,
            timed_out=False,
            started_at=time.time(),
            finished_at=time.time(),
            stdout="output",
            stderr="error",
            workspace=Path("/tmp"),
        )
        # Artifacts saved to artifacts/test/
        assert Path(e.stdout_path).exists()
        assert Path(e.stderr_path).exists()


class TestIntegrationWithToolSecurity:
    def test_run_command_collects_evidence(self, tmp_path):
        from tool_security import run_command

        async def _run():
            result = await run_command(
                "python --version",
                tmp_path,
                task_id="integration_test",
                collect_evidence_flag=True,
            )
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result.exit_code == 0
        assert result.evidence is not None
        assert result.evidence.passed is True
        assert result.evidence.task_id == "integration_test"

    def test_run_command_timeout_collects_evidence(self, tmp_path):
        from tool_security import run_command

        # Create a script that sleeps
        script = tmp_path / "slow.py"
        script.write_text("import time\ntime.sleep(10)", encoding="utf-8")

        async def _run():
            result = await run_command(
                f'python "{script}"',
                tmp_path,
                timeout_seconds=1,
                task_id="timeout_test",
                collect_evidence_flag=True,
            )
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result.timed_out is True
        assert result.evidence is not None
        assert result.evidence.timed_out is True
        assert result.evidence.passed is False

    def test_run_command_failure_collects_evidence(self, tmp_path):
        from tool_security import run_command

        # Create a script that exits with code 1
        script = tmp_path / "fail.py"
        script.write_text("import sys\nsys.exit(1)", encoding="utf-8")

        async def _run():
            result = await run_command(
                f'python "{script}"',
                tmp_path,
                task_id="failure_test",
                collect_evidence_flag=True,
            )
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result.exit_code == 1
        assert result.evidence is not None
        assert result.evidence.passed is False


class TestModelClaimsPassWithoutEvidence:
    def test_verdict_requires_actual_evidence(self):
        """PolicyGate should not accept model prose as evidence."""
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))

        # Model claims "tests passed" — but no actual evidence
        verdict, issues = gate.evaluate([])
        assert verdict == Verdict.FAIL

    def test_verdict_requires_correct_exit_code(self):
        """Even with evidence, non-zero exit = fail."""
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        evidence = [_make_evidence(command=("pytest",), exit_code=1)]
        verdict, _ = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL

    def test_verdict_requires_timeout_status(self):
        """Even with evidence, timeout = fail."""
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        evidence = [_make_evidence(command=("pytest",), timed_out=True)]
        verdict, _ = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL


class TestCrossTaskEvidence:
    def test_different_tasks_cannot_mix(self):
        gate = PolicyGate(required_commands=frozenset({("pytest",)}))
        evidence = [
            _make_evidence(task_id="task_a", command=("pytest",)),
            _make_evidence(task_id="task_b", command=("pytest",)),
        ]
        verdict, issues = gate.evaluate(evidence)
        assert verdict == Verdict.FAIL
        assert any("Conflicting task" in i for i in issues)


class TestInterruptedProcess:
    def test_exception_evidence_not_collected(self):
        """When process raises exception, evidence is not collected."""
        from tool_security import run_command

        async def _run():
            result = await run_command(
                "nonexistent_command_xyz",
                Path(tempfile.mkdtemp()),
                task_id="interrupt_test",
                collect_evidence_flag=True,
            )
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result.exit_code == -1
        # Evidence not collected on exception (command was blocked)
        assert result.evidence is None
