"""Structured module query report."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class ModuleNotFoundError(RuntimeError):
    """Raised when a module has no scan data."""


class NoScanFoundError(RuntimeError):
    """Raised when query data is requested before any scan exists."""


def build_module_report(
    connection: sqlite3.Connection,
    *,
    module_path: str,
    generated_at: str,
) -> dict[str, Any]:
    scan = connection.execute(
        """
        SELECT scan_id
        FROM scans
        ORDER BY started_at DESC, scan_id DESC
        LIMIT 1
        """
    ).fetchone()
    if scan is None:
        raise NoScanFoundError("no scan found; run vitality scan first")

    symbol = module_symbol(module_path)
    module_commits = connection.execute(
        """
        SELECT commit_hash, author, committed_at
        FROM commits
        WHERE file_path = ?
        """,
        (module_path,),
    ).fetchall()
    runtime_calls = connection.execute(
        """
        SELECT COALESCE(SUM(call_count), 0)
        FROM runtime_calls
        WHERE symbol = ? AND last_scan_id = ?
        """,
        (symbol, scan["scan_id"]),
    ).fetchone()[0]

    if not module_commits and runtime_calls == 0:
        raise ModuleNotFoundError("module not found in scan data")

    recent_commits = commits_within_90_days(module_commits, generated_at)
    return {
        "schema_version": "1.0",
        "module": module_path,
        "runtime_calls": runtime_calls,
        "change_frequency_90d": len({row["commit_hash"] for row in recent_commits}),
        "primary_authors": primary_authors(recent_commits),
        "has_test_coverage": runtime_calls > 0,
    }


def module_symbol(module_path: str) -> str:
    return ".".join(Path(module_path).with_suffix("").parts)


def commits_within_90_days(
    commits: list[sqlite3.Row],
    generated_at: str,
) -> list[sqlite3.Row]:
    cutoff = parse_timestamp(generated_at) - timedelta(days=90)
    return [row for row in commits if parse_timestamp(row["committed_at"]) >= cutoff]


def primary_authors(commits: list[sqlite3.Row]) -> list[str]:
    counts: dict[str, int] = {}
    for row in commits:
        counts[row["author"]] = counts.get(row["author"], 0) + 1
    return [
        author
        for author, _count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
