import sqlite3
import tempfile
import unittest
from pathlib import Path

from vitality.store import db


class StoreDbTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")

    def tearDown(self):
        self.connection.close()

    def test_get_connection_returns_named_column_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "data.db"

            connection = db.get_connection(database_path)
            try:
                row = connection.execute(
                    "SELECT 'value' AS example_column"
                ).fetchone()
            finally:
                connection.close()

        self.assertEqual(row["example_column"], "value")

    def test_get_connection_without_initialized_store_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / ".vitality" / "data.db"

            with self.assertRaisesRegex(db.StoreDatabaseError, "database"):
                db.get_connection(database_path)

    def test_apply_schema_creates_all_tables(self):
        db.apply_schema(self.connection)

        tables = {
            row[0]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        self.assertEqual(
            tables,
            {"commits", "declared_dependencies", "runtime_calls", "scans"},
        )

    def test_insert_and_select_commit(self):
        db.apply_schema(self.connection)

        db.insert_commit(
            self.connection,
            commit_hash="abc123",
            author="maria",
            committed_at="2026-06-24T12:00:00Z",
            file_path="src/example.py",
        )

        self.assertEqual(
            db.select_commits(self.connection),
            [
                {
                    "commit_hash": "abc123",
                    "author": "maria",
                    "committed_at": "2026-06-24T12:00:00Z",
                    "file_path": "src/example.py",
                }
            ],
        )

    def test_insert_and_select_declared_dependency(self):
        db.apply_schema(self.connection)

        db.insert_declared_dependency(
            self.connection,
            name="requests",
            version_spec=">=2",
            source_file="requirements.txt",
        )

        self.assertEqual(
            db.select_declared_dependencies(self.connection),
            [
                {
                    "name": "requests",
                    "version_spec": ">=2",
                    "source_file": "requirements.txt",
                }
            ],
        )

    def test_insert_and_select_runtime_call(self):
        db.apply_schema(self.connection)

        db.insert_runtime_call(
            self.connection,
            symbol="requests",
            call_count=3,
            last_scan_id="scan-1",
        )

        self.assertEqual(
            db.select_runtime_calls(self.connection),
            [
                {
                    "symbol": "requests",
                    "call_count": 3,
                    "last_scan_id": "scan-1",
                }
            ],
        )

    def test_insert_and_select_scan(self):
        db.apply_schema(self.connection)

        db.insert_scan(
            self.connection,
            scan_id="scan-1",
            started_at="2026-06-24T12:00:00Z",
            finished_at="2026-06-24T12:01:00Z",
        )

        self.assertEqual(
            db.select_scans(self.connection),
            [
                {
                    "scan_id": "scan-1",
                    "started_at": "2026-06-24T12:00:00Z",
                    "finished_at": "2026-06-24T12:01:00Z",
                }
            ],
        )

    def test_insert_commit_preserves_required_author_constraint(self):
        db.apply_schema(self.connection)

        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_commit(
                self.connection,
                commit_hash="abc123",
                author=None,
                committed_at="2026-06-24T12:00:00Z",
                file_path="src/example.py",
            )


if __name__ == "__main__":
    unittest.main()
