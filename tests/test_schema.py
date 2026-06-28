import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "src" / "vitality" / "store" / "schema.sql"


def apply_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def table_columns(connection: sqlite3.Connection, table_name: str) -> list[dict]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [
        {
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": row[3],
            "default": row[4],
            "pk": row[5],
        }
        for row in rows
    ]


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")

    def tearDown(self):
        self.connection.close()

    def test_schema_applies_to_empty_database(self):
        apply_schema(self.connection)

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

    def test_commits_table_matches_architecture(self):
        apply_schema(self.connection)

        columns = table_columns(self.connection, "commits")

        self.assertEqual(
            columns,
            [
                {
                    "cid": 0,
                    "name": "commit_hash",
                    "type": "TEXT",
                    "notnull": 1,
                    "default": None,
                    "pk": 1,
                },
                {
                    "cid": 1,
                    "name": "author",
                    "type": "TEXT",
                    "notnull": 1,
                    "default": None,
                    "pk": 0,
                },
                {
                    "cid": 2,
                    "name": "committed_at",
                    "type": "TEXT",
                    "notnull": 1,
                    "default": None,
                    "pk": 0,
                },
                {
                    "cid": 3,
                    "name": "file_path",
                    "type": "TEXT",
                    "notnull": 1,
                    "default": None,
                    "pk": 2,
                },
            ],
        )

    def test_declared_dependencies_table_matches_architecture(self):
        apply_schema(self.connection)

        columns = table_columns(self.connection, "declared_dependencies")

        self.assertEqual(
            columns,
            [
                {
                    "cid": 0,
                    "name": "name",
                    "type": "TEXT",
                    "notnull": 0,
                    "default": None,
                    "pk": 1,
                },
                {
                    "cid": 1,
                    "name": "version_spec",
                    "type": "TEXT",
                    "notnull": 0,
                    "default": None,
                    "pk": 0,
                },
                {
                    "cid": 2,
                    "name": "source_file",
                    "type": "TEXT",
                    "notnull": 1,
                    "default": None,
                    "pk": 0,
                },
            ],
        )

    def test_runtime_calls_table_matches_architecture(self):
        apply_schema(self.connection)

        columns = table_columns(self.connection, "runtime_calls")

        self.assertEqual(
            columns,
            [
                {
                    "cid": 0,
                    "name": "symbol",
                    "type": "TEXT",
                    "notnull": 1,
                    "default": None,
                    "pk": 1,
                },
                {
                    "cid": 1,
                    "name": "call_count",
                    "type": "INTEGER",
                    "notnull": 1,
                    "default": "0",
                    "pk": 0,
                },
                {
                    "cid": 2,
                    "name": "last_scan_id",
                    "type": "TEXT",
                    "notnull": 1,
                    "default": None,
                    "pk": 2,
                },
            ],
        )

    def test_scans_table_matches_architecture(self):
        apply_schema(self.connection)

        columns = table_columns(self.connection, "scans")

        self.assertEqual(
            columns,
            [
                {
                    "cid": 0,
                    "name": "scan_id",
                    "type": "TEXT",
                    "notnull": 0,
                    "default": None,
                    "pk": 1,
                },
                {
                    "cid": 1,
                    "name": "started_at",
                    "type": "TEXT",
                    "notnull": 1,
                    "default": None,
                    "pk": 0,
                },
                {
                    "cid": 2,
                    "name": "finished_at",
                    "type": "TEXT",
                    "notnull": 0,
                    "default": None,
                    "pk": 0,
                },
            ],
        )

    def test_commits_rejects_missing_required_author(self):
        apply_schema(self.connection)

        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                """
                INSERT INTO commits (commit_hash, committed_at, file_path)
                VALUES ('abc123', '2026-06-24T12:00:00Z', 'src/example.py')
                """
            )


if __name__ == "__main__":
    unittest.main()
