"""Collect runtime execution evidence from a project's test suite."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
import coverage

from vitality.store import db


class RuntimeTraceError(RuntimeError):
    """Raised when runtime tracing cannot complete successfully."""


class TestSuiteFailed(RuntimeTraceError):
    """Raised after runtime data is persisted when the target test suite fails."""


@dataclass(frozen=True)
class RuntimeCall:
    symbol: str
    call_count: int


def collect(
    repo_path: str | Path,
    connection: sqlite3.Connection,
    *,
    last_scan_id: str,
    test_command: list[str] | None = None,
) -> int:
    repo = Path(repo_path)
    command = test_command or [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        coverage_data_path = Path(temp_dir) / ".coverage"
        test_returncode = run_tests_with_coverage(repo, command, coverage_data_path)
        calls = read_runtime_calls(repo, coverage_data_path)

    for call in calls:
        db.insert_runtime_call(
            connection,
            symbol=call.symbol,
            call_count=call.call_count,
            last_scan_id=last_scan_id,
        )
    connection.commit()
    if test_returncode != 0:
        raise TestSuiteFailed("test command failed")
    return len(calls)


def run_tests_with_coverage(
    repo: Path,
    test_command: list[str],
    coverage_data_path: Path,
) -> int:
    result = subprocess.run(
        coverage_command(test_command, coverage_data_path),
        cwd=repo,
        env=pythonpath_env(repo),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode


def coverage_command(test_command: list[str], coverage_data_path: Path) -> list[str]:
    if len(test_command) >= 3 and test_command[0] == sys.executable and test_command[1] == "-m":
        return [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--data-file",
            str(coverage_data_path),
            "-m",
            *test_command[2:],
        ]

    raise RuntimeTraceError("test command must be a Python module command")


def read_runtime_calls(repo: Path, coverage_data_path: Path) -> list[RuntimeCall]:
    data = coverage.CoverageData(basename=str(coverage_data_path))
    data.read()

    calls: list[RuntimeCall] = []
    for measured_file in data.measured_files():
        path = Path(measured_file)
        if not is_project_module(repo, path):
            continue

        lines = data.lines(measured_file) or []
        if lines:
            calls.append(
                RuntimeCall(
                    symbol=module_symbol(repo, path),
                    call_count=len(lines),
                )
            )

    return sorted(calls, key=lambda call: call.symbol)


def is_project_module(repo: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return False

    return (
        path.suffix == ".py"
        and relative.parts[0] != "tests"
        and path.name != "__init__.py"
    )


def module_symbol(repo: Path, path: Path) -> str:
    relative = path.resolve().relative_to(repo.resolve()).with_suffix("")
    return ".".join(relative.parts)


def pythonpath_env(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(repo)
        if not existing_pythonpath
        else f"{repo}{os.pathsep}{existing_pythonpath}"
    )
    return env
