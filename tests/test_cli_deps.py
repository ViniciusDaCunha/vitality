import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from vitality.store import db


ROOT = Path(__file__).resolve().parents[1]
DOCS_SCHEMA_PATH = ROOT / "docs" / "schema.md"


class CliDepsTests(unittest.TestCase):
    def test_deps_prints_human_table_for_latest_scan(self):
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
                insert_dependency(connection, "click")
                insert_dependency(connection, "pytest")
                insert_dependency(connection, "requests")
                db.insert_runtime_call(
                    connection,
                    symbol="requests",
                    call_count=5,
                    last_scan_id="scan-old",
                )
                db.insert_runtime_call(
                    connection,
                    symbol="pytest",
                    call_count=2,
                    last_scan_id="scan-new",
                )
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_deps(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Dependency", result.stdout)
            self.assertIn("Status", result.stdout)
            self.assertRegex(result.stdout, r"(?m)^click\s+unused$")
            self.assertRegex(result.stdout, r"(?m)^pytest\s+used$")
            self.assertRegex(result.stdout, r"(?m)^requests\s+unused$")

    def test_deps_marks_declared_dependency_without_runtime_calls_as_unused(self):
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
                insert_dependency(connection, "requests")
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_deps(repo)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r"(?m)^requests\s+unused$")

    def test_deps_without_scan_fails_without_stack_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            try:
                insert_dependency(connection, "requests")
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_deps(repo)

            self.assertEqual(result.returncode, 1)
            self.assertIn("run vitality scan first", result.stderr.lower())
            self.assertNotIn("traceback", result.stderr.lower())

    def test_deps_format_json_without_scan_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            connection.close()

            result = run_vitality_deps(repo, "--format", "json")

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

    def test_deps_format_json_prints_contract_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            try:
                insert_dependency(connection, "pytest")
                insert_dependency(connection, "requests")
                db.insert_scan(
                    connection,
                    scan_id="scan-1",
                    started_at="2026-06-24T12:00:00Z",
                    finished_at="2026-06-24T12:01:00Z",
                )
                db.insert_runtime_call(
                    connection,
                    symbol="pytest",
                    call_count=2,
                    last_scan_id="scan-1",
                )
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_deps(repo, "--format", "json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertEqual(payload["scan_id"], "scan-1")
            self.assertRegex(payload["generated_at"], r"^\d{4}-\d{2}-\d{2}T")
            self.assertEqual(
                payload["dependencies"],
                [
                    {
                        "name": "pytest",
                        "declared": True,
                        "runtime_calls": 2,
                        "status": "used",
                    },
                    {
                        "name": "requests",
                        "declared": True,
                        "runtime_calls": 0,
                        "status": "unused",
                    },
                ],
            )

    def test_deps_format_json_uses_latest_scan_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            try:
                insert_dependency(connection, "pytest")
                insert_dependency(connection, "requests")
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
                db.insert_runtime_call(
                    connection,
                    symbol="requests",
                    call_count=5,
                    last_scan_id="scan-old",
                )
                db.insert_runtime_call(
                    connection,
                    symbol="pytest",
                    call_count=2,
                    last_scan_id="scan-new",
                )
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_deps(repo, "--format", "json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["scan_id"], "scan-new")
            self.assertEqual(
                payload["dependencies"],
                [
                    {
                        "name": "pytest",
                        "declared": True,
                        "runtime_calls": 2,
                        "status": "used",
                    },
                    {
                        "name": "requests",
                        "declared": True,
                        "runtime_calls": 0,
                        "status": "unused",
                    },
                ],
            )

    def test_deps_format_json_matches_documented_schema(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)
            connection = create_vitality_database(repo)
            try:
                insert_dependency(connection, "requests")
                db.insert_scan(
                    connection,
                    scan_id="scan-1",
                    started_at="2026-06-24T12:00:00Z",
                    finished_at="2026-06-24T12:01:00Z",
                )
                connection.commit()
            finally:
                connection.close()

            result = run_vitality_deps(repo, "--format", "json")

            self.assertEqual(result.returncode, 0, result.stderr)
            assert_matches_schema(
                json.loads(result.stdout),
                load_documented_deps_schema(),
            )

    def test_deps_unknown_format_fails_without_stack_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            init_git_repo(repo)

            result = run_vitality_deps(repo, "--format", "xml")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsupported format", result.stderr.lower())
            self.assertNotIn("traceback", result.stderr.lower())


def init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)


def create_vitality_database(repo: Path) -> sqlite3.Connection:
    vitality_dir = repo / ".vitality"
    vitality_dir.mkdir()
    connection = db.get_connection(vitality_dir / "data.db")
    db.apply_schema(connection)
    return connection


def insert_dependency(connection: sqlite3.Connection, name: str) -> None:
    db.insert_declared_dependency(
        connection,
        name=name,
        version_spec=None,
        source_file="requirements.txt",
    )


def run_vitality_deps(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(ROOT / "src")
        if not existing_pythonpath
        else f"{ROOT / 'src'}{os.pathsep}{existing_pythonpath}"
    )
    return subprocess.run(
        [sys.executable, "-m", "vitality.cli", "deps", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def load_documented_deps_schema() -> dict[str, object]:
    content = DOCS_SCHEMA_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- deps-json-schema:start -->\s*```json\s*(.*?)\s*```\s*<!-- deps-json-schema:end -->",
        content,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError("docs/schema.md does not document deps JSON Schema")
    return json.loads(match.group(1))


def assert_matches_schema(value: object, schema: dict[str, object]) -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(value, dict):
            raise AssertionError(f"expected object, got {type(value).__name__}")
        for key in schema.get("required", []):
            if key not in value:
                raise AssertionError(f"missing required property: {key}")
        properties = schema.get("properties", {})
        for key, child_schema in properties.items():
            if key in value:
                assert_matches_schema(value[key], child_schema)
        return
    if schema_type == "array":
        if not isinstance(value, list):
            raise AssertionError(f"expected array, got {type(value).__name__}")
        item_schema = schema["items"]
        for item in value:
            assert_matches_schema(item, item_schema)
        return
    if schema_type == "string":
        if not isinstance(value, str):
            raise AssertionError(f"expected string, got {type(value).__name__}")
        if "const" in schema and value != schema["const"]:
            raise AssertionError(f"expected {schema['const']!r}, got {value!r}")
        if "enum" in schema and value not in schema["enum"]:
            raise AssertionError(f"expected one of {schema['enum']!r}, got {value!r}")
        return
    if schema_type == "boolean":
        if not isinstance(value, bool):
            raise AssertionError(f"expected boolean, got {type(value).__name__}")
        return
    if schema_type == "integer":
        if not isinstance(value, int):
            raise AssertionError(f"expected integer, got {type(value).__name__}")
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise AssertionError(f"expected integer >= {minimum}, got {value}")


if __name__ == "__main__":
    unittest.main()
