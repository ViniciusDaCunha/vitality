# Codebase Vitality

Codebase Vitality is a local-first CLI for answering a practical maintenance
question with real project data: what code and dependencies are actually used?

The project combines Git history, runtime execution evidence from tests, and a
small SQLite store under `.vitality/`. It is designed to run locally, without a
server, telemetry, accounts, or external services.

## Status

This repository is in early MVP development. The foundation layer and collectors
are being built incrementally:

- `vitality init` creates `.vitality/data.db` and adds `.vitality/` to
  `.gitignore`.
- Git history collection records changed files per commit.
- Runtime trace collection uses `coverage.py` to record executed modules.
- `requirements.txt` parsing records declared Python dependencies.

The `scan`, `deps`, and `query` user-facing workflows are planned MVP commands
and are not complete yet.

## Goals

- Keep all analysis local to the developer machine or CI worker.
- Store results in SQLite using a small documented schema.
- Prefer simple Python modules over framework-heavy architecture.
- Provide machine-readable output for scripts and coding agents.
- Make dependency and usage audits reproducible from real repository data.

## Installation

For local development:

```bash
python3 -m pip install -e .
```

If your Python installation is externally managed, create a virtual environment
first or install dependencies in an isolated environment.

## Usage

Initialize a Git repository for Vitality:

```bash
vitality init
```

This creates:

- `.vitality/data.db`
- SQLite tables for commits, declared dependencies, runtime calls, and scans
- a `.vitality/` entry in `.gitignore`

Running outside a Git repository exits with a clear error.

## Development

Run the test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Runtime trace tests require `coverage`:

```bash
PYTHONPATH=src python3 -m pip install -e .
PYTHONPATH=src python3 -m unittest discover -s tests
```

The project follows a test-first workflow for behavior changes. Define the test
cases, write failing tests, implement the smallest working change, then run the
full suite.

## Project Layout

```text
src/vitality/
  cli.py
  collector/
    dependency_manifest.py
    git_history.py
    runtime_trace.py
  store/
    db.py
    schema.sql
  reports/
tests/
docs/
skills/
```

## Privacy and Security Model

Vitality does not send project data over the network. The SQLite database is
created locally under `.vitality/`, which is ignored by Git by default because it
may contain file paths, author names, and project-specific usage data.

Runtime tracing executes the target project's own test suite. Treat it with the
same trust boundary as running that test suite directly.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before
opening issues or pull requests.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
