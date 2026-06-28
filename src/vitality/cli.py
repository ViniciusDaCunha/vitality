"""Command line entry point for Codebase Vitality."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from vitality.store import db


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

    parser = build_parser()
    parser.parse_args(args)
    return 0


def init_project(project_root: Path) -> int:
    if not is_git_repository(project_root):
        print("error: not a git repository", file=sys.stderr)
        return 1

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
