# Implementation log

## Planning and `.gitignore` baseline

The roadmap now explicitly includes selectable single-provider execution,
conditional future adapters, and a formal Linux Mint test matrix. Provider
configuration uses an existing nested `.agent/**/*.tmp` ignore rule for atomic
temporary writes, so no new ignore pattern is expected.

## Cycle 1: Typed Registry

### RED

The first test failed during collection because `provider_registry` did not
exist.

### GREEN

An immutable Registry now reports Codex and custom JSON as adapter-ready and
Claude Code, Cursor, and Copilot as planned. Platform status is explicit, with
Linux Mint present only where the adapter contract is implemented.

## Cycle 2: Read commands

### RED

Status tests failed during collection because provider selection inference and
rendering did not exist.

### GREEN

Strict analyzer configuration maps to a typed selection without resolving or
executing an Agent. `provider list` and `provider status` render deterministic
output through the CLI.

## Cycle 3: Atomic selection

### RED

Selection tests failed during collection because the typed selection error and
write operation did not exist.

### GREEN

`provider use codex` validates the Registry definition, preserves the existing
timeout and unrelated settings, replaces only provider protocol/command through
an ignored atomic temporary file, and returns deterministic output. Unknown,
planned, and command-less Provider selections leave configuration and Session
state unchanged.

## Current verification

All 87 tests pass with 95.71% coverage. Ruff lint passes. The real provider
list/status commands report Codex selected without executing it. The active
support-PDF Session was observed at `REQUIREMENT_REVIEW` and remains untouched
by Provider operations.

The user authorized mechanical formatting of the three new test files and one
raw-string correction that did not alter assertion semantics. Final Ruff and
Pyright checks now pass with zero errors or warnings. All 87 tests still pass
with 95.71% coverage; Python 3.9 compilation and source/wheel builds pass.

All 12 Session state files are valid JSON without duplicate keys. The existing
`.agent/**/*.tmp`, build, coverage, and cache rules cover every generated
artifact, so `.gitignore` needs no change. The active support-PDF Session remains
at the externally established `REQUIREMENT_REVIEW` state.
