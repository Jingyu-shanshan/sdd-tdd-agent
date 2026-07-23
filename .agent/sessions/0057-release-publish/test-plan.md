# Test plan

## Documentation checks

- Confirm the obsolete deferral sentence is absent.
- Confirm the installation URL matches the built 0.1.0 wheel filename.
- Confirm Linux Mint remains explicitly pending real-host evidence.

## Regression

- Run Ruff format/check, Pyright, all tests with coverage, compileall, and build.
- Validate every Session state JSON file and preserve the active user Session.
- Audit secrets, changed-test scope, whitespace, generated artifacts, and
  `.gitignore` coverage.
