import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from vitality.store import db


ROOT = Path(__file__).resolve().parents[1]


class CliQueryTests(unittest.TestCase):
    def test_query_module_format_json_returns_module_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            try:
                db.insert_scan(
                    connection,
                    scan_id="scan-1",
                    started_at="2026-06-24T12:00:00Z",
                    finished_at="2026-06-24T12:01:00Z",
                )
                insert_commit(
                    connection,
                    "commit-1",
                    "maria",
                    "2026-06-20T12:00:00Z",
                    "src/payments/webhook.py",
                )
                insert_commit(
                    connection,
                    "commit-2",
                    "ana",
                    "2026-06-01T12:00:00Z",
                    "src/payments/webhook.py",
                )
                insert_commit(
                    connection,
                    "commit-3",
                    "maria",
                    "2026-02-01T12:00:00Z",
                    "src/payments/webhook.py",
                )
                db.insert_runtime_call(
                    connection,
                    symbol="src.payments.webhook",
                    call_count=12,
                    last_scan_id="scan-1",
                )
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_query(
                repo,
                "--module",
                "src/payments/webhook.py",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "schema_version": "1.0",
                    "module": "src/payments/webhook.py",
                    "runtime_calls": 12,
                    "change_frequency_90d": 2,
                    "primary_authors": ["ana", "maria"],
                    "has_test_coverage": True,
                },
            )

    def test_query_module_without_runtime_calls_reports_no_test_coverage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            try:
                db.insert_scan(
                    connection,
                    scan_id="scan-1",
                    started_at="2026-06-24T12:00:00Z",
                    finished_at="2026-06-24T12:01:00Z",
                )
                insert_commit(
                    connection,
                    "commit-1",
                    "maria",
                    "2026-06-20T12:00:00Z",
                    "src/payments/unused.py",
                )
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_query(
                repo,
                "--module",
                "src/payments/unused.py",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["runtime_calls"], 0)
            self.assertEqual(payload["change_frequency_90d"], 1)
            self.assertEqual(payload["primary_authors"], ["maria"])
            self.assertFalse(payload["has_test_coverage"])

    def test_query_module_ignores_runtime_calls_from_old_scans(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            try:
                db.insert_scan(
                    connection,
                    scan_id="scan-old",
                    started_at="2026-06-24T12:00:00Z",
                    finished_at="2026-06-24T12:01:00Z",
                )
                db.insert_scan(
                    connection,
                    scan_id="scan-new",
                    started_at="2026-06-25T12:00:00Z",
                    finished_at="2026-06-25T12:01:00Z",
                )
                insert_commit(
                    connection,
                    "commit-1",
                    "maria",
                    "2026-06-20T12:00:00Z",
                    "src/payments/webhook.py",
                )
                db.insert_runtime_call(
                    connection,
                    symbol="src.payments.webhook",
                    call_count=12,
                    last_scan_id="scan-old",
                )
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_query(
                repo,
                "--module",
                "src/payments/webhook.py",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["runtime_calls"], 0)
            self.assertFalse(payload["has_test_coverage"])

    def test_query_missing_module_returns_structured_json_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            try:
                db.insert_scan(
                    connection,
                    scan_id="scan-1",
                    started_at="2026-06-24T12:00:00Z",
                    finished_at="2026-06-24T12:01:00Z",
                )
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_query(
                repo,
                "--module",
                "src/missing.py",
                "--format",
                "json",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(
                json.loads(result.stderr),
                {
                    "error": "module not found in scan data",
                    "code": "module_not_found",
                },
            )
            self.assertNotIn("traceback", result.stderr.lower())

    def test_query_without_scan_returns_structured_json_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            connection.close()

            result = run_vitality_query(
                repo,
                "--module",
                "src/payments/webhook.py",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertEqual(
                json.loads(result.stderr),
                {
                    "error": "no scan found; run vitality scan first",
                    "code": "no_scan_found",
                },
            )
            self.assertNotIn("traceback", result.stderr.lower())

    def test_query_requires_json_format_without_stack_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)

            result = run_vitality_query(repo, "--module", "src/example.py")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("usage", result.stderr.lower())
            self.assertIn("--format json", result.stderr.lower())
            self.assertNotIn("traceback", result.stderr.lower())


def init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)


def create_vitality_database(repo: Path) -> sqlite3.Connection:
    vitality_dir = repo / ".vitality"
    vitality_dir.mkdir()
    connection = db.get_connection(vitality_dir / "data.db")
    db.apply_schema(connection)
    return connection


def insert_commit(
    connection: sqlite3.Connection,
    commit_hash: str,
    author: str,
    committed_at: str,
    file_path: str,
) -> None:
    db.insert_commit(
        connection,
        commit_hash=commit_hash,
        author=author,
        committed_at=committed_at,
        file_path=file_path,
    )


def run_vitality_query(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(ROOT / "src")
        if not existing_pythonpath
        else f"{ROOT / 'src'}{os.pathsep}{existing_pythonpath}"
    )
    return subprocess.run(
        [sys.executable, "-m", "vitality.cli", "query", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
