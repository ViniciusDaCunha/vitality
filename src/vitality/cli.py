"""Command line entry point for Codebase Vitality."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

from vitality.store import db

TOOL_ERROR_EXIT_CODE = 1
TEST_FAILURE_EXIT_CODE = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vitality",
        description="Local-first CLI for codebase vitality signals.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["init"]:
        return init_project(Path.cwd())
    if args == ["scan"]:
        return scan_project(Path.cwd())

    parser = build_parser()
    parser.parse_args(args)
    return 0


def init_project(project_root: Path) -> int:
    if not is_git_repository(project_root):
        print("error: not a git repository", file=sys.stderr)
        return TOOL_ERROR_EXIT_CODE

    vitality_dir = project_root / ".vitality"
    vitality_dir.mkdir(exist_ok=True)

    connection = db.get_connection(vitality_dir / "data.db")
    try:
        db.apply_schema(connection)
        connection.commit()
    finally:
        connection.close()

    ensure_gitignore_entry(project_root / ".gitignore", ".vitality/")
    print("initialized .vitality/data.db")
    return 0


def scan_project(project_root: Path) -> int:
    if not is_git_repository(project_root):
        print("error: not a git repository", file=sys.stderr)
        return TOOL_ERROR_EXIT_CODE

    from vitality.collector import dependency_manifest, git_history, runtime_trace

    started = time.monotonic()
    vitality_dir = project_root / ".vitality"
    vitality_dir.mkdir(exist_ok=True)

    connection = db.get_connection(vitality_dir / "data.db")
    scan_id = str(uuid.uuid4())
    try:
        db.apply_schema(connection)
        db.insert_scan(
            connection,
            scan_id=scan_id,
            started_at=utc_now(),
            finished_at=None,
        )
        connection.commit()

        git_history.collect(project_root, connection)
        commit_count = count_commits(connection)
        symbol_count = runtime_trace.collect(
            project_root,
            connection,
            last_scan_id=scan_id,
        )
        dependency_count = dependency_manifest.collect(project_root, connection)

        finished_at = utc_now()
        connection.execute(
            "UPDATE scans SET finished_at = ? WHERE scan_id = ?",
            (finished_at, scan_id),
        )
        connection.commit()
    except runtime_trace.TestSuiteFailed as error:
        connection.commit()
        print(f"error: {error}", file=sys.stderr)
        return TEST_FAILURE_EXIT_CODE
    except (git_history.GitHistoryError, runtime_trace.RuntimeTraceError) as error:
        connection.commit()
        print(f"error: {error}", file=sys.stderr)
        return TOOL_ERROR_EXIT_CODE
    finally:
        connection.close()

    duration = time.monotonic() - started
    print(f"scan_id: {scan_id}")
    print(f"commits parsed: {commit_count}")
    print(f"dependencies declared: {dependency_count}")
    print(f"symbols traced: {symbol_count}")
    print(f"duration: {duration:.2f}s")
    return 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def count_commits(connection: sqlite3.Connection) -> int:
    return connection.execute(
        "SELECT COUNT(DISTINCT commit_hash) FROM commits"
    ).fetchone()[0]


def is_git_repository(project_root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def ensure_gitignore_entry(gitignore_path: Path, entry: str) -> None:
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        if entry in lines:
            return
        prefix = "" if content == "" or content.endswith("\n") else "\n"
        gitignore_path.write_text(f"{content}{prefix}{entry}\n", encoding="utf-8")
        return

    gitignore_path.write_text(f"{entry}\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
