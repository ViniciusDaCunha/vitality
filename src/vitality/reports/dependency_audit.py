"""Dependency audit report formatting."""

from __future__ import annotations

import sqlite3
from typing import Any


class NoScanFoundError(RuntimeError):
    """Raised when dependency data exists but no scan is available."""


def build_report(
    connection: sqlite3.Connection,
    *,
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

    cursor = connection.execute(
        """
        SELECT
            declared_dependencies.name AS name,
            COALESCE(SUM(runtime_calls.call_count), 0) AS runtime_calls
        FROM declared_dependencies
        LEFT JOIN runtime_calls
            ON runtime_calls.symbol = declared_dependencies.name
            AND runtime_calls.last_scan_id = ?
        GROUP BY declared_dependencies.name
        ORDER BY declared_dependencies.name
        """,
        (scan["scan_id"],),
    )

    rows = []
    for row in cursor.fetchall():
        runtime_calls = row["runtime_calls"]
        rows.append(
            {
                "name": row["name"],
                "declared": True,
                "runtime_calls": runtime_calls,
                "status": "used" if runtime_calls > 0 else "unused",
            }
        )
    return {
        "schema_version": "1.0",
        "scan_id": scan["scan_id"],
        "generated_at": generated_at,
        "dependencies": rows,
    }


def build_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return build_report(connection, generated_at="")["dependencies"]


def format_human_table(rows: list[dict[str, Any]]) -> str:
    name_width = max([len("Dependency"), *(len(row["name"]) for row in rows)])
    lines = [
        f"{'Dependency'.ljust(name_width)}  Status",
        f"{'-' * name_width}  ------",
    ]
    lines.extend(f"{row['name'].ljust(name_width)}  {row['status']}" for row in rows)
    return "\n".join(lines)
