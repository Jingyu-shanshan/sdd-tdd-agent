# Implementation

## RED

Added focused tests for exhausted-plan completion, next-case generation,
per-cycle evidence cleanup, strict final GREEN evidence, artifact changes,
atomic collisions, filesystem failures, and deterministic CLI output. The
first targeted run failed during collection because `cycle_completion` did not
exist.

## GREEN

Implemented typed final GREEN validation and atomic IMPLEMENTATION -> REVIEW
completion. Exact current/full-suite commands, zero exits, sanitized bounded
streams, completed-plan order, and both source digests are required. GREEN with
remaining work reuses the existing isolated test-source generator for exactly
the next case and clears every stale per-cycle artifact. Exhausted completion
invokes neither model nor test runner.

## Verification

- Ruff lint and formatting passed.
- Pyright passed with zero errors or warnings.
- Pytest passed: 595 tests, 94.04% total coverage.
- The new critical cycle-completion module has 92% coverage.
- Source distribution and wheel builds passed; Python bytecode compilation
  passed.
- Existing `.gitignore` covers build/cache/bytecode/coverage and the new atomic
  Session temporary path, so no update was needed.
- All Session JSON parsed, no credential-shaped values were introduced, and
  the active PDF Session remained unchanged in `REQUIREMENT_REVIEW`.
