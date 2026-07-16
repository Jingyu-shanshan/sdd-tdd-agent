# Implementation

## RED

Added focused tests for the exact two-command success path, CLI output,
individual command failures, runner timeouts, immutable audit/source checks,
concurrent source/state mutation, sanitized evidence, atomic collisions, and
invalid entry states. The first targeted run failed during collection because
the refactor-completion module did not exist.

## GREEN

Implemented an injected, shell-free final-verification service for exact
REFACTOR state. It validates the review report, canonical completion snapshot,
GREEN evidence, source records, safe paths, symlink chain, and actual digests;
runs the recorded current test then full suite under separate timeouts; and
revalidates the immutable context after each process. Only two zero exits write
sanitized bounded evidence and atomically enter DONE with an honest
`no_source_change` refactor record. Added exact `agent refactor` CLI dispatch.

Hardening tests cover malformed audit records, boolean return codes,
unsanitized retained evidence, missing/unsafe/symlinked files, and state/source
changes during either external process.

## Verification

- Ruff lint and formatting passed.
- Pyright passed with zero errors or warnings.
- Pytest passed: 652 tests, 93.74% total coverage.
- The new critical refactor-completion module has 91% coverage.
- Source distribution and wheel builds passed; Python bytecode compilation
  passed.
- All 36 Session JSON files parsed with duplicate-key rejection, and no
  credential-shaped values were introduced.
- Existing `.gitignore` covers build, distribution, cache, bytecode, coverage,
  and refactor atomic temporary files, so no update was needed.
- The active PDF Session remained unchanged in `REQUIREMENT_REVIEW`.
