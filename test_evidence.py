"""
Test Evidence — Deterministic verification of test execution.

P1.2: Never infer test success from model prose or chat history.
Evidence is created by CommandExecutor after actual process execution.
Persisted outside model conversation output.
"""

import hashlib
import json
import logging
import platform
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

EVIDENCE_DIR = Path("artifacts")


class Verdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class TestEvidence:
    """
    Immutable record of actual test execution.
    Created by CommandExecutor after process completes.
    Never created from model output.
    """

    task_id: str
    command: tuple[str, ...]
    exit_code: int
    timed_out: bool
    started_at: str  # ISO 8601
    finished_at: str  # ISO 8601
    stdout_path: str
    stderr_path: str
    stdout_sha256: str
    stderr_sha256: str
    workspace: str
    base_commit: str
    current_commit: str
    diff_hash: str
    platform: str
    hostname: str
    pid: int

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass(frozen=True)
class PolicyGate:
    """
    Fail-closed gate that validates evidence before allowing commit.
    Missing, stale, conflicting, or tampered evidence = FAIL.
    """

    required_commands: frozenset[tuple[str, ...]]
    required_diff_hash: str | None = None
    required_base_commit: str | None = None
    task_id: str | None = None
    workspace: str | None = None

    def evaluate(self, evidence_list: list[TestEvidence]) -> tuple[Verdict, list[str]]:
        """
        Evaluate evidence list against policy requirements.
        Returns (verdict, list_of_issues).
        """
        issues: list[str] = []

        if not evidence_list:
            issues.append("No evidence provided")
            return Verdict.FAIL, issues

        # Check task identity consistency
        task_ids = {e.task_id for e in evidence_list}
        if len(task_ids) > 1:
            issues.append(f"Conflicting task IDs: {task_ids}")

        # Check workspace identity consistency
        workspaces = {e.workspace for e in evidence_list}
        if len(workspaces) > 1:
            issues.append(f"Conflicting workspaces: {workspaces}")

        # Check required commands were executed
        executed = {e.command for e in evidence_list}
        missing = self.required_commands - executed
        if missing:
            issues.append(f"Missing required commands: {missing}")

        # Check all evidence passed
        failed = [e for e in evidence_list if not e.passed]
        for e in failed:
            if e.timed_out:
                issues.append(f"Command timed out: {' '.join(e.command)}")
            else:
                issues.append(f"Command failed (exit={e.exit_code}): {' '.join(e.command)}")

        # Check diff hash if required
        if self.required_diff_hash:
            diff_hashes = {e.diff_hash for e in evidence_list}
            if self.required_diff_hash not in diff_hashes:
                issues.append(
                    f"Diff hash mismatch: expected {self.required_diff_hash}, got {diff_hashes}"
                )

        # Check base commit if required
        if self.required_base_commit:
            base_commits = {e.base_commit for e in evidence_list}
            if self.required_base_commit not in base_commits:
                issues.append(
                    f"Base commit mismatch: expected {self.required_base_commit}, "
                    f"got {base_commits}"
                )

        # Check commit identity (all evidence should agree on current commit)
        current_commits = {e.current_commit for e in evidence_list}
        if len(current_commits) > 1:
            issues.append(f"Conflicting current commits: {current_commits}")

        # Check artifact integrity
        for e in evidence_list:
            if not Path(e.stdout_path).exists():
                issues.append(f"Missing stdout artifact: {e.stdout_path}")
            if not Path(e.stderr_path).exists():
                issues.append(f"Missing stderr artifact: {e.stderr_path}")

        # Check for stale evidence (timestamps too far apart)
        if len(evidence_list) > 1:
            timestamps = []
            for e in evidence_list:
                try:
                    t = datetime.fromisoformat(e.finished_at)
                    timestamps.append(t)
                except ValueError:
                    pass
            if timestamps:
                duration = (max(timestamps) - min(timestamps)).total_seconds()
                if duration > 3600:  # More than 1 hour spread
                    issues.append(
                        f"Evidence timestamps spread over {duration:.0f}s — possible stale evidence"
                    )

        if issues:
            return Verdict.FAIL, issues
        return Verdict.PASS, []


# ── Evidence persistence ─────────────────────────────────────────
def save_evidence(evidence: TestEvidence, evidence_dir: Path | None = None) -> Path:
    """Save evidence to disk as JSON."""
    if evidence_dir is None:
        evidence_dir = Path("artifacts") / evidence.task_id

    evidence_dir.mkdir(parents=True, exist_ok=True)

    evidence_path = evidence_dir / "test_evidence.json"
    evidence_path.write_text(evidence.to_json(), encoding="utf-8")

    logger.info("Evidence saved: %s", evidence_path)
    return evidence_path


def load_evidence(evidence_path: Path) -> TestEvidence:
    """Load evidence from disk. Raises on missing/tampered evidence."""
    if not evidence_path.exists():
        raise FileNotFoundError(f"Evidence not found: {evidence_path}")

    data = json.loads(evidence_path.read_text(encoding="utf-8"))

    # Verify artifact integrity
    for key in ("stdout_sha256", "stderr_sha256"):
        artifact_path = data.get(key.replace("_sha256", "_path"))
        if artifact_path and Path(artifact_path).exists():
            actual_hash = hashlib.sha256(Path(artifact_path).read_bytes()).hexdigest()
            if actual_hash != data[key]:
                raise ValueError(
                    f"Artifact tampered: {artifact_path} (expected {data[key]}, got {actual_hash})"
                )

    # Convert command from list to tuple (JSON doesn't have tuples)
    data["command"] = tuple(data["command"])

    return TestEvidence(**data)


def collect_evidence(
    task_id: str,
    command: tuple[str, ...],
    exit_code: int,
    timed_out: bool,
    started_at: float,
    finished_at: float,
    stdout: str,
    stderr: str,
    workspace: Path,
    base_commit: str = "unknown",
    current_commit: str = "unknown",
    diff_hash: str = "unknown",
) -> TestEvidence:
    """
    Create TestEvidence from actual execution results.
    Called by CommandExecutor after process completes.
    """
    # Compute SHA-256 of stdout/stderr
    stdout_hash = hashlib.sha256(stdout.encode("utf-8")).hexdigest()
    stderr_hash = hashlib.sha256(stderr.encode("utf-8")).hexdigest()

    # Save stdout/stderr as artifacts
    evidence_dir = Path("artifacts") / task_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = evidence_dir / "stdout.txt"
    stderr_path = evidence_dir / "stderr.txt"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")

    return TestEvidence(
        task_id=task_id,
        command=command,
        exit_code=exit_code,
        timed_out=timed_out,
        started_at=datetime.fromtimestamp(started_at, tz=UTC).isoformat(),
        finished_at=datetime.fromtimestamp(finished_at, tz=UTC).isoformat(),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        stdout_sha256=stdout_hash,
        stderr_sha256=stderr_hash,
        workspace=str(workspace),
        base_commit=base_commit,
        current_commit=current_commit,
        diff_hash=diff_hash,
        platform=platform.system(),
        hostname=platform.node(),
        pid=__import__("os").getpid(),
    )
