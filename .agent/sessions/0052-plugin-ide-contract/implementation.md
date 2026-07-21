# Implementation

## Cycle 1: RED contract

- Added exact versioned plugin, IDE, Provider, determinism, and CLI contracts.
- The focused run failed during collection because `integration_api` did not
  exist, proving discovery was absent.

## Cycle 2: Manifest GREEN

- Reused the existing explicit JSON command protocol as the plugin API.
- Added one versioned deterministic manifest with all model operations, stable
  read-only IDE commands/exit codes, and Registry-derived Provider status.
- Added `agent integration manifest` with no workspace or process effects.

## Cycle 3: Verification

- Focused integration tests: 3 passed; Ruff and Pyright passed.
- Full suite: 874 passed; total coverage 92.25%; integration API 100%.
- Ruff lint/format, Pyright, compilation, and source/wheel build passed.
- Duplicate-key, secret-pattern, diff, active-Session, and ignore audits passed.
- `.gitignore` requires no change because the manifest creates no runtime file
  and all build/cache artifacts remain covered.
