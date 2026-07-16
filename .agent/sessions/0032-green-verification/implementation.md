# Implementation

## RED

Added focused tests for full-suite command planning, strict separate timeout
configuration, digest-bound two-gate execution, trusted RED recovery, evidence
sanitization, concurrency protection, and deterministic CLI integration. The
first targeted run failed during collection because the full-suite APIs and
GREEN verification module did not exist.

## GREEN

Implemented shell-free full-suite plans for Maven, Gradle, Jest, Vitest, and
Angular across supported package managers. Added the explicit
`full_test_suite_timeout_seconds` setting and a typed GREEN verifier that
revalidates current test, production source, and Session state around both
processes. Trustworthy failures atomically return to RED; two passes atomically
append the current test and enter GREEN. All stored output is sanitized and
bounded, and IMPLEMENT dispatch does not call a model.

The previously correct IMPLEMENT-rejection test became obsolete when this
phase gained its specified behavior. After explicit user continuation, it was
updated to retain its original no-second-model-call guarantee while asserting
the new two-process GREEN result.

## Verification

- Ruff lint and formatting passed.
- Pyright passed with zero errors or warnings.
- Pytest passed: 576 tests, 94.08% total coverage.
- GREEN verification, full-suite planning, execution configuration, and shared
  RED execution cover 90%, 91%, 100%, and 93% respectively.
- Source distribution and wheel builds passed; Python bytecode compilation
  passed.
- Existing `.gitignore` already covers build/cache/bytecode/coverage and the
  atomic Session temporary pattern, so no update was needed.
- All Session JSON parsed, no credential-shaped values were introduced, and
  the active PDF Session remained unchanged in `REQUIREMENT_REVIEW`.
