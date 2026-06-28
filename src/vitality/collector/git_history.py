"""Collect changed files from git history."""

from __future__ import annotations

import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path

from vitality.store import db


COMMIT_SEPARATOR = "\x1e"
FIELD_SEPARATOR = "\x1f"
GIT_LOG_FORMAT = f"{COMMIT_SEPARATOR}%H{FIELD_SEPARATOR}%an{FIELD_SEPARATOR}%aI"


class GitHistoryError(RuntimeError):
    """Raised when git history cannot be collected."""


@dataclass(frozen=True)
class CommitFileChange:
    commit_hash: str
    author: str
    committed_at: str
    file_path: str


def collect(repo_path: str | Path, connection: sqlite3.Connection) -> int:
    log_output = read_git_log(Path(repo_path))
    changes = parse_git_log(log_output)

    for change in changes:
        db.insert_commit(
            connection,
            commit_hash=change.commit_hash,
            author=change.author,
            committed_at=change.committed_at,
            file_path=change.file_path,
        )
    connection.commit()
    return len(changes)


def read_git_log(repo_path: Path) -> str:
    result = subprocess.run(
        [
            "git",
            "log",
            f"--pretty=format:{GIT_LOG_FORMAT}",
            "--name-only",
        ],
        cwd=repo_path,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitHistoryError("not a git repository")
    return result.stdout


def parse_git_log(text: str) -> list[CommitFileChange]:
    changes: list[CommitFileChange] = []

    for block in text.split(COMMIT_SEPARATOR):
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        commit_hash, author, committed_at = lines[0].split(FIELD_SEPARATOR)
        for file_path in lines[1:]:
            if file_path:
                changes.append(
                    CommitFileChange(
                        commit_hash=commit_hash,
                        author=author,
                        committed_at=committed_at,
                        file_path=file_path,
                    )
                )

    return changes
