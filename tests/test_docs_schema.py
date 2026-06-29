import json
import re
import sqlite3
import unittest
from pathlib import Path

from vitality.reports import dependency_audit, query
from vitality.store import db


ROOT = Path(__file__).resolve().parents[1]
DOCS_SCHEMA_PATH = ROOT / "docs" / "schema.md"
SQL_SCHEMA_PATH = ROOT / "src" / "vitality" / "store" / "schema.sql"


class DocsSchemaTests(unittest.TestCase):
    def test_documents_every_sqlite_table_and_column(self):
        documented = DOCS_SCHEMA_PATH.read_text(encoding="utf-8")
        sql_schema = SQL_SCHEMA_PATH.read_text(encoding="utf-8")

        for table_name, columns in parse_sql_schema(sql_schema).items():
            section = markdown_section(documented, f"### `{table_name}`")
            for column_name in columns:
                self.assertIn(
                    f"`{column_name}`",
                    section,
                    f"docs/schema.md must document {table_name}.{column_name}",
                )

    def test_documents_deps_json_contract_and_real_example(self):
        documented_schema = load_marked_json("deps-json-schema")
        self.assertEqual(documented_schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(
            set(documented_schema["required"]),
            {"schema_version", "scan_id", "generated_at", "dependencies"},
        )
        dependency_item = documented_schema["properties"]["dependencies"]["items"]
        self.assertEqual(
            set(dependency_item["required"]),
            {"name", "declared", "runtime_calls", "status"},
        )

        self.assertEqual(load_marked_json("deps-json-example"), build_deps_example())

    def test_documents_query_json_contract_and_real_example(self):
        documented_schema = load_marked_json("query-json-schema")
        self.assertEqual(documented_schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(
            set(documented_schema["required"]),
            {
                "schema_version",
                "module",
                "runtime_calls",
                "change_frequency_90d",
                "primary_authors",
                "has_test_coverage",
            },
        )

        self.assertEqual(load_marked_json("query-json-example"), build_query_example())

    def test_documents_json_versioning_rules(self):
        documented = DOCS_SCHEMA_PATH.read_text(encoding="utf-8")

        section = markdown_section(documented, "## Versionamento")
        self.assertIn('`schema_version`', section)
        self.assertIn('`"1.0"`', section)
        self.assertIn("major", section.lower())
        self.assertIn("minor", section.lower())


def parse_sql_schema(sql_schema: str) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    for match in re.finditer(
        r"CREATE TABLE (\w+) \(\s*(.*?)\s*\);",
        sql_schema,
        re.DOTALL,
    ):
        table_name = match.group(1)
        body = match.group(2)
        columns = []
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line or line.startswith("PRIMARY KEY"):
                continue
            columns.append(line.split()[0])
        tables[table_name] = columns
    return tables


def markdown_section(documented: str, heading: str) -> str:
    start = documented.find(heading)
    if start == -1:
        raise AssertionError(f"docs/schema.md is missing section {heading}")
    next_heading = documented.find("\n##", start + len(heading))
    if next_heading == -1:
        return documented[start:]
    return documented[start:next_heading]


def load_marked_json(marker_name: str) -> object:
    documented = DOCS_SCHEMA_PATH.read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- {marker_name}:start -->\s*```json\s*(.*?)\s*```\s*<!-- {marker_name}:end -->",
        documented,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"docs/schema.md is missing {marker_name}")
    return json.loads(match.group(1))


def build_deps_example() -> dict[str, object]:
    connection = create_example_database()
    try:
        db.insert_scan(
            connection,
            scan_id="scan-docs",
            started_at="2026-06-24T12:00:00Z",
            finished_at="2026-06-24T12:01:00Z",
        )
        db.insert_declared_dependency(
            connection,
            name="pytest",
            version_spec=None,
            source_file="requirements.txt",
        )
        db.insert_declared_dependency(
            connection,
            name="requests",
            version_spec=">=2.31",
            source_file="requirements.txt",
        )
        db.insert_runtime_call(
            connection,
            symbol="requests",
            call_count=12,
            last_scan_id="scan-docs",
        )
        connection.commit()
        return dependency_audit.build_report(
            connection,
            generated_at="2026-06-24T12:02:00Z",
        )
    finally:
        connection.close()


def build_query_example() -> dict[str, object]:
    connection = create_example_database()
    try:
        db.insert_scan(
            connection,
            scan_id="scan-docs",
            started_at="2026-06-24T12:00:00Z",
            finished_at="2026-06-24T12:01:00Z",
        )
        db.insert_commit(
            connection,
            commit_hash="commit-1",
            author="maria",
            committed_at="2026-06-20T12:00:00Z",
            file_path="src/payments/webhook.py",
        )
        db.insert_commit(
            connection,
            commit_hash="commit-2",
            author="ana",
            committed_at="2026-06-01T12:00:00Z",
            file_path="src/payments/webhook.py",
        )
        db.insert_runtime_call(
            connection,
            symbol="src.payments.webhook",
            call_count=12,
            last_scan_id="scan-docs",
        )
        connection.commit()
        return query.build_module_report(
            connection,
            module_path="src/payments/webhook.py",
            generated_at="2026-06-24T12:02:00Z",
        )
    finally:
        connection.close()


def create_example_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    db.apply_schema(connection)
    return connection


if __name__ == "__main__":
    unittest.main()
