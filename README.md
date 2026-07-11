# sdd-tdd-agent

A CLI platform for software-design-driven development (SDD) and incremental
test-driven development (TDD), built around a single agent with isolated
contexts.

## Current increment

The bootstrap slice provides a working Hello World command while establishing
the project's specification and TDD record structure.

```bash
uv run agent hello
```

Expected output:

```text
Hello, World!
```

Run the test suite with:

```bash
uv run python -m unittest discover -v
```

The active and completed development records live under `.agent/sessions/`.
