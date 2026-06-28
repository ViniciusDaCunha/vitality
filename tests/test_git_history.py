import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from vitality.collector import git_history
from vitality.store import db


class GitHistoryTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        db.apply_schema(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_collect_git_history_writes_one_row_per_changed_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_repo(repo)
            commit_file(repo, "README.md", "first\n", "initial commit")
            first_hash = git_stdout(repo, "rev-parse", "HEAD")
            commit_files(
                repo,
                {
                    "src/app.py": "print('hello')\n",
                    "tests/test_app.py": "def test_app():\n    assert True\n",
                },
                "add app and tests",
            )
            second_hash = git_stdout(repo, "rev-parse", "HEAD")

            inserted = git_history.collect(repo, self.connection)

            self.assertEqual(inserted, 3)
            rows = sorted(
                db.select_commits(self.connection),
                key=lambda row: row["file_path"],
            )
            self.assertEqual(
                rows,
                [
                    {
                        "commit_hash": first_hash,
                        "author": "Test Author",
                        "committed_at": "2026-06-24T12:00:00+00:00",
                        "file_path": "README.md",
                    },
                    {
                        "commit_hash": second_hash,
                        "author": "Test Author",
                        "committed_at": "2026-06-24T12:00:00+00:00",
                        "file_path": "src/app.py",
                    },
                    {
                        "commit_hash": second_hash,
                        "author": "Test Author",
                        "committed_at": "2026-06-24T12:00:00+00:00",
                        "file_path": "tests/test_app.py",
                    },
                ],
            )

    def test_parse_git_log_preserves_multiple_files_for_same_commit(self):
        text = "\x1eabc123\x1fMaria\x1f2026-06-24T12:00:00+00:00\nsrc/app.py\ntests/test_app.py\n"

        records = git_history.parse_git_log(text)

        self.assertEqual(
            records,
            [
                git_history.CommitFileChange(
                    commit_hash="abc123",
                    author="Maria",
                    committed_at="2026-06-24T12:00:00+00:00",
                    file_path="src/app.py",
                ),
                git_history.CommitFileChange(
                    commit_hash="abc123",
                    author="Maria",
                    committed_at="2026-06-24T12:00:00+00:00",
                    file_path="tests/test_app.py",
                ),
            ],
        )

    def test_collect_git_history_outside_git_repo_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)

            with self.assertRaisesRegex(git_history.GitHistoryError, "not a git repository"):
                git_history.collect(repo, self.connection)

            self.assertEqual(db.select_commits(self.connection), [])


def init_repo(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)


def commit_file(repo: Path, relative_path: str, content: str, message: str) -> None:
    commit_files(repo, {relative_path: content}, message)


def commit_files(repo: Path, files: dict[str, str], message: str) -> None:
    for relative_path, content in files.items():
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test Author",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--date=2026-06-24T12:00:00+00:00",
            "-m",
            message,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-06-24T12:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-06-24T12:00:00+00:00",
        },
    )


def git_stdout(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


if __name__ == "__main__":
    unittest.main()
