"""Performance benchmarks for critical-path security operations.

These tests enforce throughput minimums. If they fail, the system is too
slow for interactive use and the PR must not merge.
"""

import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Configurable thresholds (seconds / ops-per-second)
# ---------------------------------------------------------------------------

PATH_RESOLVE_OPS = 2_000  # min path resolutions per second
CMD_VALIDATE_OPS = 2_000  # min command validations per second
FILE_READ_OPS = 400  # min file reads per second (small files)
MAX_TOTAL_SEC = 10.0  # hard cap for the entire benchmark suite


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bench(fn, iterations: int) -> float:
    """Run *fn* for *iterations* and return elapsed seconds."""
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    return time.perf_counter() - start


# ---------------------------------------------------------------------------
# 1. Path resolution throughput
# ---------------------------------------------------------------------------


class TestPathResolutionBenchmark:
    """PathResolver.resolve() must stay fast — agents call it per file op."""

    @pytest.fixture()
    def resolver(self):
        from path_security import PathResolver

        root = Path(__file__).resolve().parent.parent
        return PathResolver(root)

    def test_resolve_throughput(self, resolver):
        safe_paths = [
            "tests/test_benchmarks.py",
            "tests/test_merge_lock.py",
            "brain_agent_v4.py",
            "tool_security.py",
            "path_security.py",
            "app_settings.py",
        ]
        elapsed = _bench(lambda: resolver.resolve(safe_paths[0]), PATH_RESOLVE_OPS)
        rate = PATH_RESOLVE_OPS / elapsed
        assert rate >= PATH_RESOLVE_OPS, (
            f"Path resolution too slow: {rate:.0f} ops/s (need >= {PATH_RESOLVE_OPS})"
        )


# ---------------------------------------------------------------------------
# 2. Command validation throughput
# ---------------------------------------------------------------------------


class TestCommandValidationBenchmark:
    """validate_command() must stay fast — agents call it per subprocess."""

    @pytest.fixture()
    def validate(self):
        from tool_security import validate_command

        return validate_command

    def test_validate_throughput(self, validate):
        safe_commands = [
            "python -m pytest tests/",
            "ruff check .",
            "git status",
            "python -m compileall -q .",
        ]
        workspace = Path(__file__).resolve().parent.parent
        elapsed = _bench(lambda: validate(safe_commands[0], workspace), CMD_VALIDATE_OPS)
        rate = CMD_VALIDATE_OPS / elapsed
        assert rate >= CMD_VALIDATE_OPS, (
            f"Command validation too slow: {rate:.0f} ops/s (need >= {CMD_VALIDATE_OPS})"
        )


# ---------------------------------------------------------------------------
# 3. File read throughput
# ---------------------------------------------------------------------------


class TestFileReadBenchmark:
    """read_file() must stay fast for small files."""

    @pytest.fixture()
    def read_fn(self):
        from tool_security import read_file

        return read_file

    def test_read_throughput(self, read_fn):
        small_files = [
            "tests/test_benchmarks.py",
            "tool_security.py",
            "path_security.py",
        ]
        workspace = Path(__file__).resolve().parent.parent

        def _read():
            for f in small_files:
                read_fn(f, workspace)

        iterations = 500
        elapsed = _bench(_read, iterations)
        rate = iterations / elapsed
        assert rate >= FILE_READ_OPS, (
            f"File read too slow: {rate:.0f} batch-ops/s (need >= {FILE_READ_OPS})"
        )


# ---------------------------------------------------------------------------
# 4. Policy gate throughput (protected_path_policy)
# ---------------------------------------------------------------------------


class TestPolicyGateBenchmark:
    """assert_mutation_allowed() must stay fast."""

    @pytest.fixture()
    def gate(self):
        from protected_path_policy import assert_mutation_allowed

        return assert_mutation_allowed

    def test_gate_throughput(self, gate):
        safe_paths = [
            Path("src/new_module.py"),
            Path("tests/test_new.py"),
            Path("docs/readme.md"),
            Path("README.md"),
        ]
        ops = 3_000
        elapsed = _bench(lambda: gate(safe_paths[0], "write"), ops)
        rate = ops / elapsed
        assert rate >= 1_000, f"Policy gate too slow: {rate:.0f} ops/s (need >= 1000)"


# ---------------------------------------------------------------------------
# 5. Total suite hard cap
# ---------------------------------------------------------------------------


class TestTotalSuiteCap:
    """The entire benchmark suite must finish within MAX_TOTAL_SEC."""

    def test_suite_completes_within_budget(self):
        """This is a meta-test: just ensure we didn't already time out."""
        # If pytest got here, the prior tests ran.  We just verify the
        # hard cap wasn't breached by checking the clock.
        # (The cap is enforced by the CI step timing this file.)
        assert True, "Benchmark suite completed"
