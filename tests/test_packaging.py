import os
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
RELEASE_DOC_PATH = ROOT / "docs" / "release.md"


class PackagingTests(unittest.TestCase):
    def test_pyproject_declares_publishable_package_metadata(self):
        pyproject = load_pyproject()

        project = pyproject["project"]
        build_system = pyproject["build-system"]
        self.assertIn("wheel>=0.42", build_system["requires"])
        self.assertEqual(project["name"], "codebase-vitality")
        self.assertEqual(project["version"], "0.1.0")
        self.assertEqual(project["requires-python"], ">=3.10")
        self.assertIn("coverage>=7", project["dependencies"])
        self.assertEqual(project["scripts"]["vitality"], "vitality.cli:main")

    def test_pyproject_includes_runtime_schema_sql_in_wheel_package_data(self):
        pyproject = load_pyproject()

        package_data = pyproject["tool"]["setuptools"]["package-data"]
        self.assertIn("store/schema.sql", package_data["vitality"])

    def test_built_wheel_can_apply_schema_from_installed_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            wheelhouse = temp_path / "wheelhouse"
            target = temp_path / "target"

            build_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--wheel-dir",
                    str(wheelhouse),
                    ".",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(build_result.returncode, 0, build_result.stderr)

            wheels = sorted(wheelhouse.glob("codebase_vitality-0.1.0-*.whl"))
            self.assertEqual(len(wheels), 1)

            install_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--target",
                    str(target),
                    str(wheels[0]),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(install_result.returncode, 0, install_result.stderr)

            connection = sqlite3.connect(":memory:")
            try:
                env = os.environ.copy()
                env["PYTHONPATH"] = str(target)
                smoke_result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        (
                            "import sqlite3; "
                            "from vitality.store import db; "
                            "connection = sqlite3.connect(':memory:'); "
                            "db.apply_schema(connection); "
                            "print(connection.execute("
                            "'SELECT COUNT(*) FROM sqlite_master WHERE type = \"table\"'"
                            ").fetchone()[0])"
                        ),
                    ],
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
            finally:
                connection.close()

            self.assertEqual(smoke_result.returncode, 0, smoke_result.stderr)
            self.assertEqual(smoke_result.stdout.strip(), "4")

    def test_release_document_covers_build_upload_and_install_verification(self):
        document = RELEASE_DOC_PATH.read_text(encoding="utf-8")

        self.assertIn("python3 -m build", document)
        self.assertIn("twine check", document)
        self.assertIn("twine upload", document)
        self.assertIn("pip install codebase-vitality", document)

    def test_release_document_requires_pypi_credentials(self):
        document = RELEASE_DOC_PATH.read_text(encoding="utf-8").lower()

        self.assertIn("pypi", document)
        self.assertIn("token", document)
        self.assertIn("credentials", document)


def load_pyproject() -> dict[str, object]:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
