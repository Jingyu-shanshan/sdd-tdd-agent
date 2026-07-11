# sdd-tdd-agent

A CLI platform for software-design-driven development (SDD) and incremental
test-driven development (TDD), built around a single agent with isolated
contexts.

## Current increment

The first two slices provide a working CLI and project-workspace
initialization while establishing the specification and TDD record structure.

```bash
uv run agent hello
```

Expected output:

```text
Hello, World!
```

Initialize the current project's agent workspace with:

```bash
uv run agent init
```

The command creates `.agent/` metadata plus the `memories`, `sessions`,
`cache`, `logs`, and `metrics` directories. Re-running it preserves existing
metadata.

Run the test suite with:

```bash
uv run python -m unittest discover -v
```

The active and completed development records live under `.agent/sessions/`.
