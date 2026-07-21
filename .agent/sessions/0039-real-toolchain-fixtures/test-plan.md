# Test Plan

## RED

- Require all five absent fixture roots to produce supported project profiles,
  exact single-test commands, and exact full-suite commands.
- Require the absent workflow to define explicit Java and Node matrices,
  immutable Actions, pinned runtimes, locked installs, and exact test commands.

## GREEN

- Add the smallest behaviorally meaningful projects and manager lockfiles.
- Add only the workflow declarations needed by the contracts.
- Re-run focused tests without repository coverage enforcement.

## Regression

- Run Ruff lint and formatting, Pyright, and full pytest coverage.
- Parse workflow YAML and Agent JSON.
- Build the Python distribution and compile production modules.
- Scan for secrets, preserve the active Session, and audit ignored artifacts.
- Push the task, inspect every remote matrix job, and fix only evidence-backed
  failures through a new RED/GREEN cycle.
