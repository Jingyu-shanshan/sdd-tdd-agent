# Implementation

## Cycle 1: Refactor contract (RED)

The focused test module failed during collection because no automated-refactor
boundary existed.

## Cycle 2: Minimal generation and verification (GREEN)

Added one versioned Prompt and one typed module that reuses the existing audit
loader, Provider configuration, process contracts, final test commands, and
evidence writer. Exact same-path validation, optimistic atomic source/state
writes, digest binding, and failed-test rollback pass focused tests.

## Cycle 3: Provider and failure contracts (GREEN)

Added strict JSON and project-external ephemeral read-only Codex exchange,
source-free provider errors, Schema/type validation, concurrency rejection, and
temporary-collision preservation. The critical module reaches 90% coverage.

## Cycle 4: Verification

All 776 tests pass with 93.01% total coverage. Ruff, formatting, Pyright,
compile, build, Schema serialization, secret scan, active-Session integrity,
and ignore audits pass. Added the narrow `*.agent-refactor*.tmp` rule for
source-adjacent apply/rollback files; existing rules already cover build output,
caches, provider exchange, and Session-state temporary files.
