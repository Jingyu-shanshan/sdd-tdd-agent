# Implementation

## Cycle 1: RED contracts

- Updated only the three explicitly approved existing Provider test files and
  added new structured CLI contracts.
- The focused run failed during collection because `structured_cli_runner` did
  not exist, proving the new behavior was absent before production changes.

## Cycle 2: Shared boundary GREEN

- Added one provider-protocol runner decorator around all existing JSON model
  adapters, including automated refactoring.
- Added bounded duplicate-free envelope/result decoding and safe fixed errors.
- Claude uses print/JSON/plan/non-persistent flags; Cursor uses print/JSON and
  deliberately receives no force/write flag.

## Cycle 3: Registry GREEN

- Registered exact Claude Code and Cursor protocols, executables, macOS/Linux
  Mint targets, and official guarded install plans.
- Preserved explicit single-provider selection, non-interactive no-install
  behavior, version verification, Codex, and custom JSON compatibility.
- After human review, updated two additional outdated existing tests that still
  asserted Claude Code was planned.

## Cycle 4: Verification

- `ruff check .` and `ruff format .`: passed; one new test file formatted.
- `pyright`: 0 errors, 0 warnings, 0 informations.
- `pytest`: 861 passed; total coverage 92.20%; shared model adapter 94%.
- Python compilation and source/wheel package build: passed.
- Secret-pattern, duplicate-JSON-key, diff, active-Session, and ignore audits:
  passed.
- `.gitignore` requires no change: generated build/cache artifacts are already
  ignored and 0050 SDD evidence is intentionally tracked.
