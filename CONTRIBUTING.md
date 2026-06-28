# Contributing to Codebase Vitality

Thanks for taking the time to improve Codebase Vitality. This project is early,
so small, focused contributions are easier to review and merge than broad
rewrites.

## Ground Rules

- Keep changes scoped to one behavior or one documentation topic.
- Add or update tests for behavior changes.
- Preserve the local-first privacy model: no telemetry, no hosted service, and
  no network calls during analysis.
- Prefer the existing architecture: simple Python modules, SQLite via
  `sqlite3`, and no ORM.
- Do not commit `.vitality/`, local databases, virtual environments, coverage
  output, or build artifacts.

## Development Setup

Install the project locally:

```bash
python3 -m pip install -e .
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

If your environment does not allow system package installs, use a virtual
environment or another isolated Python environment.

## Test-First Workflow

For behavior changes:

1. Define the expected cases first.
2. Write tests that fail before the implementation.
3. Implement the smallest change that makes the tests pass.
4. Run the relevant tests and then the full suite.
5. Keep refactors separate from behavior changes when possible.

## Pull Requests

Before opening a pull request:

- Confirm the full test suite passes.
- Explain the user-facing behavior changed.
- Mention any limitations or follow-up work.
- Link related issues when available.
- Avoid unrelated formatting churn.

## Reporting Bugs

Please include:

- Vitality version or commit SHA.
- Python version and operating system.
- The command you ran.
- Expected behavior.
- Actual behavior and error output.
- A minimal reproduction if possible.

## Proposing Features

Open an issue first for larger features. Describe the use case, why it belongs
in the MVP or roadmap, and how it fits the local-first design.
