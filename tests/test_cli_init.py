import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliInitTests(unittest.TestCase):
    def test_init_in_git_repo_creates_store_and_gitignore_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

            result = run_vitality_init(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((repo / ".vitality").is_dir())
            self.assertTrue((repo / ".vitality" / "data.db").is_file())
            self.assertIn(".vitality/", (repo / ".gitignore").read_text())

            with sqlite3.connect(repo / ".vitality" / "data.db") as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }

            self.assertEqual(
                tables,
                {"commits", "declared_dependencies", "runtime_calls", "scans"},
            )

    def test_init_does_not_duplicate_existing_gitignore_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / ".gitignore").write_text("build/\n.vitality/\n", encoding="utf-8")

            result = run_vitality_init(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (repo / ".gitignore").read_text(encoding="utf-8").splitlines().count(
                    ".vitality/"
                ),
                1,
            )

    def test_init_outside_git_repo_fails_without_stack_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)

            result = run_vitality_init(repo)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a git repository", result.stderr.lower())
            self.assertNotIn("traceback", result.stderr.lower())
            self.assertFalse((repo / ".vitality").exists())


def run_vitality_init(cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "vitality.cli", "init"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
