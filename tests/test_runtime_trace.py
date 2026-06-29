import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from vitality.collector import runtime_trace
from vitality.store import db


class RuntimeTraceTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        db.apply_schema(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_collect_runtime_trace_records_executed_module(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            write_sample_project(repo)

            count = runtime_trace.collect(
                repo,
                self.connection,
                last_scan_id="scan-1",
                test_command=[sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            )

            self.assertGreater(count, 0)
            calls = {
                row["symbol"]: row
                for row in db.select_runtime_calls(self.connection)
            }
            self.assertIn("samplepkg.used", calls)
            self.assertGreater(calls["samplepkg.used"]["call_count"], 0)
            self.assertEqual(calls["samplepkg.used"]["last_scan_id"], "scan-1")

    def test_collect_runtime_trace_does_not_record_unexecuted_module(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            write_sample_project(repo)

            runtime_trace.collect(
                repo,
                self.connection,
                last_scan_id="scan-1",
                test_command=[sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            )

            symbols = {
                row["symbol"]
                for row in db.select_runtime_calls(self.connection)
            }

            self.assertIn("samplepkg.used", symbols)
            self.assertNotIn("samplepkg.unused", symbols)

    def test_collect_runtime_trace_failing_tests_persists_partial_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            write_sample_project(repo, failing_test=True)

            with self.assertRaisesRegex(runtime_trace.TestSuiteFailed, "test command failed"):
                runtime_trace.collect(
                    repo,
                    self.connection,
                    last_scan_id="scan-1",
                    test_command=[
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                    ],
                )

            calls = {
                row["symbol"]: row
                for row in db.select_runtime_calls(self.connection)
            }
            self.assertIn("samplepkg.used", calls)
            self.assertEqual(calls["samplepkg.used"]["last_scan_id"], "scan-1")


def write_sample_project(repo: Path, *, failing_test: bool = False) -> None:
    package_dir = repo / "samplepkg"
    tests_dir = repo / "tests"
    package_dir.mkdir()
    tests_dir.mkdir()

    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "used.py").write_text(
        "def add_one(value):\n"
        "    return value + 1\n",
        encoding="utf-8",
    )
    (package_dir / "unused.py").write_text(
        "def never_called():\n"
        "    return 'unused'\n",
        encoding="utf-8",
    )
    (tests_dir / "test_used.py").write_text(
        "import unittest\n"
        "from samplepkg.used import add_one\n\n"
        "class UsedTests(unittest.TestCase):\n"
        "    def test_add_one(self):\n"
        f"        self.assertEqual(add_one(1), {3 if failing_test else 2})\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
