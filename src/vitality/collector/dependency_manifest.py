"""Collect declared dependencies from requirements.txt."""

from __future__ import annotations

import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from vitality.store import db


REQUIREMENTS_FILE = "requirements.txt"
REQUIREMENT_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9_.-]*)"
    r"(?P<version_spec>(?:==|>=|<=|~=|!=|>|<).+)?$"
)


@dataclass(frozen=True)
class DeclaredDependency:
    name: str
    version_spec: str | None
    source_file: str


def collect(repo_path: str | Path, connection: sqlite3.Connection) -> int:
    manifest_path = Path(repo_path) / REQUIREMENTS_FILE
    dependencies = parse_requirements(manifest_path)

    for dependency in dependencies:
        db.insert_declared_dependency(
            connection,
            name=dependency.name,
            version_spec=dependency.version_spec,
            source_file=dependency.source_file,
        )
    connection.commit()
    return len(dependencies)


def parse_requirements(path: Path) -> list[DeclaredDependency]:
    if not path.exists():
        return []

    dependencies: list[DeclaredDependency] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        line = strip_inline_comment(raw_line).strip()
        if not line:
            continue

        dependency = parse_requirement_line(line)
        if dependency is None:
            warn_malformed_line(path.name, line_number, raw_line)
            continue

        dependencies.append(dependency)

    return dependencies


def parse_requirement_line(line: str) -> DeclaredDependency | None:
    match = REQUIREMENT_PATTERN.match(line)
    if not match:
        return None

    version_spec = match.group("version_spec")
    return DeclaredDependency(
        name=match.group("name"),
        version_spec=version_spec.strip() if version_spec else None,
        source_file=REQUIREMENTS_FILE,
    )


def strip_inline_comment(line: str) -> str:
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return ""
    return line.split(" #", 1)[0]


def warn_malformed_line(source_file: str, line_number: int, line: str) -> None:
    print(
        f"warning: skipped malformed dependency in {source_file}:{line_number}: {line}",
        file=sys.stderr,
    )
