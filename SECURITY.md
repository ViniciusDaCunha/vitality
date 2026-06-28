# Security Policy

## Supported Versions

Codebase Vitality is currently pre-1.0. Security fixes are applied to the main
development line unless a release branch is explicitly announced.

## Reporting a Vulnerability

Please do not open a public issue for a vulnerability.

Until a dedicated security email is published, report vulnerabilities through a
private maintainer contact or GitHub private vulnerability reporting if it is
enabled for the repository.

Include as much detail as you can safely share:

- Affected version or commit SHA.
- Operating system and Python version.
- Steps to reproduce.
- Impact and affected data.
- Any suggested mitigation.

## Security Model

Vitality is designed to run locally and store data locally in `.vitality/`.
Project data should not leave the machine unless the user explicitly shares it.

Important trust boundaries:

- `vitality init` creates local state under `.vitality/`.
- Runtime tracing executes the target project's test suite. This has the same
  risk as running that test suite directly.
- The local SQLite database may contain file paths, author names, dependency
  names, and runtime usage evidence. It should remain ignored by Git unless a
  team intentionally decides otherwise.

## What We Consider Security Issues

- Unexpected network transmission of project data.
- Arbitrary command execution beyond the documented test runner behavior.
- Unsafe handling of `.vitality/data.db` contents.
- Leaking local paths, author data, or scan data in unintended outputs.
- Dependency vulnerabilities that affect normal Vitality usage.

## Non-Security Bugs

Incorrect counts, parser mistakes, and usability issues are usually regular bugs
unless they expose sensitive data or enable code execution.
