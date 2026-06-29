import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "docs" / "runtime-trace-benchmark.md"
TASKS_PATH = ROOT / "skills" / "TASKS.md"


class RuntimeTraceBenchmarkDocTests(unittest.TestCase):
    def test_benchmark_document_exists_and_names_runtime_trace_overhead(self):
        self.assertTrue(BENCHMARK_PATH.is_file())

        document = BENCHMARK_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("runtime trace", document)
        self.assertIn("coverage.py", document)
        self.assertIn("overhead", document)

    def test_benchmark_covers_two_or_three_real_repositories(self):
        rows = benchmark_rows()

        self.assertGreaterEqual(len(rows), 2)
        self.assertLessEqual(len(rows), 3)
        for row in rows:
            self.assertNotIn("demo_repo", row["repository"])
            self.assertNotIn("fixture", row["repository"].lower())

    def test_each_benchmark_row_has_reproducible_numbers(self):
        for row in benchmark_rows():
            self.assertTrue(row["test_command"])
            self.assertGreater(row["baseline_seconds"], 0)
            self.assertGreater(row["coverage_seconds"], 0)
            self.assertGreaterEqual(row["overhead_percent"], 0)

    def test_document_validates_rnf2_target(self):
        document = BENCHMARK_PATH.read_text(encoding="utf-8")

        self.assertIn("## RNF2 Decision", document)
        self.assertIn("20%", document)
        self.assertIn("within target", document.lower())

    def test_document_records_sample_mode_mitigation_decision(self):
        rows = benchmark_rows()
        document = BENCHMARK_PATH.read_text(encoding="utf-8").lower()

        if any(row["overhead_percent"] > 20 for row in rows):
            self.assertIn("--sample mode", document)
            self.assertIn("mitigation", document)
        else:
            self.assertIn("no mitigation task", document)

    def test_over_target_result_opens_sample_mode_task(self):
        rows = benchmark_rows()
        if not any(row["overhead_percent"] > 20 for row in rows):
            self.skipTest("all benchmark rows are within RNF2 target")

        tasks = TASKS_PATH.read_text(encoding="utf-8")
        self.assertIn("--sample mode", tasks)
        self.assertIn("overhead", tasks.lower())


def benchmark_rows() -> list[dict[str, object]]:
    document = BENCHMARK_PATH.read_text(encoding="utf-8")
    table = markdown_section(document, "## Results")
    rows = []
    for line in table.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped or "Repository" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 6:
            continue
        rows.append(
            {
                "repository": cells[0],
                "test_command": cells[2],
                "baseline_seconds": parse_seconds(cells[3]),
                "coverage_seconds": parse_seconds(cells[4]),
                "overhead_percent": parse_percent(cells[5]),
            }
        )
    return rows


def markdown_section(document: str, heading: str) -> str:
    start = document.find(heading)
    if start == -1:
        raise AssertionError(f"{BENCHMARK_PATH.name} is missing section {heading}")
    next_heading = document.find("\n## ", start + len(heading))
    if next_heading == -1:
        return document[start:]
    return document[start:next_heading]


def parse_seconds(value: str) -> float:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)s", value)
    if match is None:
        raise AssertionError(f"expected seconds value, got {value!r}")
    return float(match.group(1))


def parse_percent(value: str) -> float:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)%", value)
    if match is None:
        raise AssertionError(f"expected percent value, got {value!r}")
    return float(match.group(1))


if __name__ == "__main__":
    unittest.main()
