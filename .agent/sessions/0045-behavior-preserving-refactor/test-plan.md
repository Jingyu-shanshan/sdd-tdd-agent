# Test Plan

## Contract tests

- Request contains only exact digest-bound review/source inputs.
- Generated result must be typed, changed, bounded, normalized, and same-path.
- JSON and isolated Codex adapters enforce the exact output Schema.

## Workflow tests

- Passing current/full suites enter DONE with before/after evidence.
- Either failing gate restores source and state.
- Concurrent source/state mutation and temporary collisions fail safely.
- Legacy no-source-change verification remains covered by existing tests.

## Repository gates

- Ruff lint/format, Pyright, pytest coverage, compile, build, Schema
  serialization, secret scan, active-Session integrity, ignore audit, and both
  hosted workflows.
