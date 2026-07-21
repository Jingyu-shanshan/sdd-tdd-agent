# Implementation

## Cycle 1: RED contract

- Added exact supported-matrix, deterministic output, and side-effect-free CLI
  contracts.
- The focused run failed during collection because `ecosystem_registry` did not
  exist, proving capability discovery was absent.

## Cycle 2: Capability GREEN

- Added one immutable typed matrix containing only Java and TypeScript
  capabilities verified by existing detection, planners, TDD, and fixtures.
- Added `agent ecosystem list` without project or toolchain side effects.

## Cycle 3: Verification

- Focused ecosystem tests: 3 passed; Ruff and Pyright passed.
- Full suite: 877 passed; total coverage 92.28%; ecosystem Registry 100%.
- Ruff lint/format, Pyright, compilation, and source/wheel build passed.
- Duplicate-key, secret-pattern, diff, active-Session, and ignore audits passed.
- `.gitignore` requires no change because discovery creates no runtime file and
  existing build/cache rules remain sufficient.
