import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"


class ReadmeTests(unittest.TestCase):
    def test_documents_installation_for_new_users(self):
        readme = README_PATH.read_text(encoding="utf-8")

        self.assertIn("python3 -m pip install -e .", readme)
        self.assertRegex(readme.lower(), r"virtual environment|venv|isolated")

    def test_documents_reproducible_scan_and_deps_flow(self):
        readme = README_PATH.read_text(encoding="utf-8")
        usage_section = markdown_section(readme, "## Usage")

        self.assertIn("vitality scan", usage_section)
        self.assertIn("vitality deps", usage_section)
        self.assertNotIn("not complete yet", usage_section.lower())
        self.assertNotIn("planned mvp commands", usage_section.lower())

    def test_documents_real_repository_scan_output(self):
        readme = README_PATH.read_text(encoding="utf-8")
        section = markdown_section(readme, "## Usage")

        self.assertIn("Codebase Vitality repository", section)
        self.assertNotIn("demo_repo", section)
        output = marked_block(readme, "scan-output")
        self.assertRegex(output, r"(?m)^scan_id: [0-9a-f-]{36}$")
        self.assertRegex(output, r"(?m)^commits parsed: \d+$")
        self.assertRegex(output, r"(?m)^dependencies declared: \d+$")
        self.assertRegex(output, r"(?m)^symbols traced: \d+$")
        self.assertRegex(output, r"(?m)^duration: \d+\.\d{2}s$")

    def test_documents_real_repository_deps_output(self):
        readme = README_PATH.read_text(encoding="utf-8")
        output = marked_block(readme, "deps-output")

        self.assertIn("Dependency", output)
        self.assertIn("Status", output)
        self.assertRegex(output, r"(?m)^----------\s+------$")

    def test_documents_scan_trust_boundary(self):
        readme = README_PATH.read_text(encoding="utf-8").lower()

        self.assertIn("vitality scan", readme)
        self.assertIn("executes the target project's own test suite", readme)


def markdown_section(document: str, heading: str) -> str:
    start = document.find(heading)
    if start == -1:
        raise AssertionError(f"README.md is missing section {heading}")
    next_heading = document.find("\n## ", start + len(heading))
    if next_heading == -1:
        return document[start:]
    return document[start:next_heading]


def marked_block(document: str, marker_name: str) -> str:
    match = re.search(
        rf"<!-- {marker_name}:start -->\s*```text\s*(.*?)\s*```\s*<!-- {marker_name}:end -->",
        document,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"README.md is missing {marker_name}")
    return match.group(1)


if __name__ == "__main__":
    unittest.main()
