"""Thin SQLite helpers for the Vitality store."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection(database_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def apply_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def insert_commit(
    connection: sqlite3.Connection,
    *,
    commit_hash: str,
    author: str,
    committed_at: str,
    file_path: str,
) -> None:
    connection.execute(
        """
        INSERT INTO commits (commit_hash, author, committed_at, file_path)
        VALUES (?, ?, ?, ?)
        """,
        (commit_hash, author, committed_at, file_path),
    )


def select_commits(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT commit_hash, author, committed_at, file_path
        FROM commits
        ORDER BY commit_hash, file_path
        """
    )
    return _cursor_rows_to_dicts(cursor)


def insert_declared_dependency(
    connection: sqlite3.Connection,
    *,
    name: str,
    version_spec: str | None,
    source_file: str,
) -> None:
    connection.execute(
        """
        INSERT INTO declared_dependencies (name, version_spec, source_file)
        VALUES (?, ?, ?)
        """,
        (name, version_spec, source_file),
    )


def select_declared_dependencies(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT name, version_spec, source_file
        FROM declared_dependencies
        ORDER BY name
        """
    )
    return _cursor_rows_to_dicts(cursor)


def insert_runtime_call(
    connection: sqlite3.Connection,
    *,
    symbol: str,
    call_count: int,
    last_scan_id: str,
) -> None:
    connection.execute(
        """
        INSERT INTO runtime_calls (symbol, call_count, last_scan_id)
        VALUES (?, ?, ?)
        """,
        (symbol, call_count, last_scan_id),
    )


def select_runtime_calls(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT symbol, call_count, last_scan_id
        FROM runtime_calls
        ORDER BY symbol, last_scan_id
        """
    )
    return _cursor_rows_to_dicts(cursor)


def insert_scan(
    connection: sqlite3.Connection,
    *,
    scan_id: str,
    started_at: str,
    finished_at: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO scans (scan_id, started_at, finished_at)
        VALUES (?, ?, ?)
        """,
        (scan_id, started_at, finished_at),
    )


def select_scans(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    cursor = connection.execute(
        """
        SELECT scan_id, started_at, finished_at
        FROM scans
        ORDER BY scan_id
        """
    )
    return _cursor_rows_to_dicts(cursor)


def _cursor_rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    column_names = [column[0] for column in cursor.description]
    return [dict(zip(column_names, row)) for row in cursor.fetchall()]
