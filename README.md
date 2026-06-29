# Codebase Vitality

Codebase Vitality is a local-first CLI for answering a practical maintenance
question with real project data: what code and dependencies are actually used?

The project combines Git history, runtime execution evidence from tests, and a
small SQLite store under `.vitality/`. It is designed to run locally, without a
server, telemetry, accounts, or external services.

## Status

This repository is in early MVP development. The core local CLI workflow is now
available for MVP validation:

- `vitality init` creates `.vitality/data.db` and adds `.vitality/` to
  `.gitignore`.
- Git history collection records changed files per commit.
- Runtime trace collection uses `coverage.py` to record executed modules.
- `requirements.txt` parsing records declared Python dependencies.
- `vitality scan` collects Git history, declared dependencies, runtime trace
  data, and records a scan.
- `vitality deps` reports declared dependencies as `used` or `unused`.
- `vitality query --module <path> --format json` returns module-level JSON for
  agent and script consumption.

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

From a Git repository, run a scan and then inspect dependency usage:

```bash
vitality scan
vitality deps
```

`vitality scan` creates `.vitality/data.db` if needed, collects Git history,
parses `requirements.txt`, and executes the target project's own test suite under
runtime tracing. Treat it with the same trust boundary as running that test
suite directly.

You can also prepare the local database explicitly:

```bash
vitality init
```

That creates `.vitality/data.db`, applies the SQLite schema, and adds
`.vitality/` to `.gitignore`. Running outside a Git repository exits with a
clear error.

### Real Output Example

The following output was captured against the Codebase Vitality repository.
This repository currently does not have a `requirements.txt`, so the dependency
table is empty while the scan still records Git history and runtime trace data.

```bash
PYTHONPATH=src python3 -m vitality.cli scan
```

<!-- scan-output:start -->
```text
scan_id: 1877ebb1-c701-4505-a5a1-e35363779cfe
commits parsed: 5
dependencies declared: 0
symbols traced: 6
duration: 6.92s
```
<!-- scan-output:end -->

```bash
PYTHONPATH=src python3 -m vitality.cli deps
```

<!-- deps-output:start -->
```text
Dependency  Status
----------  ------
```
<!-- deps-output:end -->

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
