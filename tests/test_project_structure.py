import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectStructureTests(unittest.TestCase):
    def test_project_has_minimum_architecture_layout(self):
        expected_paths = [
            "pyproject.toml",
            "LICENSE",
            "src/vitality/__init__.py",
            "src/vitality/cli.py",
            "src/vitality/collector/__init__.py",
            "src/vitality/store/__init__.py",
            "src/vitality/reports/__init__.py",
            "tests",
            "docs",
        ]

        missing = [path for path in expected_paths if not (ROOT / path).exists()]

        self.assertEqual(missing, [])

    def test_pyproject_declares_vitality_console_script(self):
        pyproject = ROOT / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")

        self.assertIn("[project.scripts]", content)
        self.assertIn('vitality = "vitality.cli:main"', content)

    def test_vitality_help_runs_without_subcommands(self):
        result = subprocess.run(
            [sys.executable, "-m", "vitality.cli", "--help"],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: vitality", result.stdout)

    def test_unknown_command_fails_predictably(self):
        result = subprocess.run(
            [sys.executable, "-m", "vitality.cli", "unknown"],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments: unknown", result.stderr)


if __name__ == "__main__":
    unittest.main()
