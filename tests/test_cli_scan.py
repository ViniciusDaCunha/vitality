import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliScanTests(unittest.TestCase):
    def test_scan_populates_all_tables_and_marks_scan_finished(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            write_demo_repo(repo)

            result = run_vitality_scan(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((repo / ".vitality" / "data.db").is_file())

            with sqlite3.connect(repo / ".vitality" / "data.db") as connection:
                connection.row_factory = sqlite3.Row
                scans = fetch_dicts(connection, "SELECT * FROM scans")
                commits = fetch_dicts(connection, "SELECT * FROM commits")
                dependencies = fetch_dicts(
                    connection,
                    "SELECT * FROM declared_dependencies ORDER BY name",
                )
                runtime_calls = fetch_dicts(connection, "SELECT * FROM runtime_calls")

            self.assertEqual(len(scans), 1)
            self.assertTrue(scans[0]["scan_id"])
            self.assertTrue(scans[0]["started_at"])
            self.assertTrue(scans[0]["finished_at"])
            self.assertGreaterEqual(len(commits), 4)
            self.assertEqual(
                dependencies,
                [
                    {
                        "name": "coverage",
                        "version_spec": ">=7",
                        "source_file": "requirements.txt",
                    },
                    {
                        "name": "requests",
                        "version_spec": ">=2.31",
                        "source_file": "requirements.txt",
                    },
                ],
            )
            self.assertTrue(runtime_calls)
            self.assertEqual(
                {row["last_scan_id"] for row in runtime_calls},
                {scans[0]["scan_id"]},
            )
            self.assertIn("samplepkg.used", {row["symbol"] for row in runtime_calls})

    def test_scan_prints_basic_counts_and_duration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            write_demo_repo(repo)

            result = run_vitality_scan(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            stdout = result.stdout.lower()
            self.assertIn("commits parsed:", stdout)
            self.assertIn("dependencies declared:", stdout)
            self.assertIn("symbols traced:", stdout)
            self.assertIn("duration:", stdout)

    def test_scan_outside_git_repo_fails_without_stack_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)

            result = run_vitality_scan(repo)

            self.assertEqual(result.returncode, 1)
            self.assertIn("not a git repository", result.stderr.lower())
            self.assertNotIn("traceback", result.stderr.lower())
            self.assertFalse((repo / ".vitality" / "data.db").exists())

    def test_scan_with_failing_tests_preserves_partial_data_without_finished_at(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            write_demo_repo(repo, failing_test=True)

            result = run_vitality_scan(repo)

            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn("test command failed", result.stderr.lower())
            self.assertNotIn("traceback", result.stderr.lower())

            with sqlite3.connect(repo / ".vitality" / "data.db") as connection:
                connection.row_factory = sqlite3.Row
                scans = fetch_dicts(connection, "SELECT * FROM scans")
                commits = fetch_dicts(connection, "SELECT * FROM commits")
                runtime_calls = fetch_dicts(connection, "SELECT * FROM runtime_calls")

            self.assertEqual(len(scans), 1)
            self.assertTrue(scans[0]["scan_id"])
            self.assertTrue(scans[0]["started_at"])
            self.assertIsNone(scans[0]["finished_at"])
            self.assertGreaterEqual(len(commits), 4)
            self.assertIn("samplepkg.used", {row["symbol"] for row in runtime_calls})
            self.assertEqual(
                {row["last_scan_id"] for row in runtime_calls},
                {scans[0]["scan_id"]},
            )


def write_demo_repo(repo: Path, *, failing_test: bool = False) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

    write_file(repo / "requirements.txt", "requests>=2.31\ncoverage>=7\n")
    write_file(repo / "samplepkg" / "__init__.py", "")
    write_file(
        repo / "samplepkg" / "used.py",
        "def add_one(value):\n"
        "    return value + 1\n",
    )
    write_file(
        repo / "samplepkg" / "unused.py",
        "def never_called():\n"
        "    return 'unused'\n",
    )
    write_file(
        repo / "tests" / "test_used.py",
        "import unittest\n"
        "from samplepkg.used import add_one\n\n"
        "class UsedTests(unittest.TestCase):\n"
        "    def test_add_one(self):\n"
        f"        self.assertEqual(add_one(1), {3 if failing_test else 2})\n",
    )
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
            "initial demo repo",
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


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_vitality_scan(cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(ROOT / "src")
        if not existing_pythonpath
        else f"{ROOT / 'src'}{os.pathsep}{existing_pythonpath}"
    )
    return subprocess.run(
        [sys.executable, "-m", "vitality.cli", "scan"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def fetch_dicts(connection: sqlite3.Connection, query: str) -> list[dict[str, object]]:
    return [dict(row) for row in connection.execute(query).fetchall()]


if __name__ == "__main__":
    unittest.main()
