import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from vitality.collector import dependency_manifest
from vitality.store import db


class DependencyManifestTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        db.apply_schema(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_collect_requirements_txt_writes_declared_dependencies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "requirements.txt").write_text(
                "requests>=2.31\n"
                "pytest==8.0.0\n"
                "click\n",
                encoding="utf-8",
            )

            count = dependency_manifest.collect(repo, self.connection)

            self.assertEqual(count, 3)
            self.assertEqual(
                db.select_declared_dependencies(self.connection),
                [
                    {
                        "name": "click",
                        "version_spec": None,
                        "source_file": "requirements.txt",
                    },
                    {
                        "name": "pytest",
                        "version_spec": "==8.0.0",
                        "source_file": "requirements.txt",
                    },
                    {
                        "name": "requests",
                        "version_spec": ">=2.31",
                        "source_file": "requirements.txt",
                    },
                ],
            )

    def test_collect_requirements_txt_ignores_comments_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "requirements.txt").write_text(
                "# runtime dependencies\n"
                "\n"
                "requests>=2.31  # HTTP client\n"
                "   \n"
                "click\n",
                encoding="utf-8",
            )
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                count = dependency_manifest.collect(repo, self.connection)

            self.assertEqual(count, 2)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(
                db.select_declared_dependencies(self.connection),
                [
                    {
                        "name": "click",
                        "version_spec": None,
                        "source_file": "requirements.txt",
                    },
                    {
                        "name": "requests",
                        "version_spec": ">=2.31",
                        "source_file": "requirements.txt",
                    },
                ],
            )

    def test_collect_requirements_txt_warns_and_continues_after_malformed_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "requirements.txt").write_text(
                "requests>=2.31\n"
                "not a valid requirement ???\n"
                "click\n",
                encoding="utf-8",
            )
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                count = dependency_manifest.collect(repo, self.connection)

            self.assertEqual(count, 2)
            self.assertIn("warning:", stderr.getvalue().lower())
            self.assertIn("requirements.txt:2", stderr.getvalue())
            self.assertEqual(
                db.select_declared_dependencies(self.connection),
                [
                    {
                        "name": "click",
                        "version_spec": None,
                        "source_file": "requirements.txt",
                    },
                    {
                        "name": "requests",
                        "version_spec": ">=2.31",
                        "source_file": "requirements.txt",
                    },
                ],
            )


if __name__ == "__main__":
    unittest.main()
