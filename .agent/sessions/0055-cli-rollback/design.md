# Design

## Existing boundaries

Reuse the current GREEN context validation, exact two-path artifact set,
tokenized injected Git runner, bounded timeout, and atomic Session-state style
already implemented by Git integration.

## Git validation

The command requires both target paths to be clean, a single-parent HEAD whose
subject is exactly `feat: <session> <test>`, and a HEAD path set equal to the
validated GREEN artifacts. It then uses native Git restore from that parent for
the exact worktree paths; it does not reset, checkout, amend, or rewrite
history.

## State transition

After restore, atomically change the current phase from `GREEN` to `WRITE_TEST`,
remove the current test from the completed prefix, and clear only current-cycle
test/source/evidence records. If the state update fails, restore the same paths
from HEAD so the command is fail-safe and retryable.

## CLI

`agent rollback` returns exit code 0 only after both exact paths and state are
rolled back. Every rejected or failed operation returns the existing safe Git
integration error code 2 without exposing Git output.
