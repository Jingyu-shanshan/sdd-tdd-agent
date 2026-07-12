# Tasks

## Task 1: Provider doctor

Status: complete

1. [x] Add failing ready/missing/planned diagnostic tests.
2. [x] Implement typed executable location and version diagnostics.
3. [x] Add `provider doctor` CLI output.

## Task 2: Guarded installer

Status: complete

1. [x] Add failing download/install/verify contract tests.
2. [x] Implement the official Codex standalone plan without shell pipelines.
3. [x] Cover redacted failures and post-install verification.

## Task 3: Interactive selection

Status: complete

1. [x] Add confirm/decline/non-interactive CLI tests.
2. [x] Install and select only after interactive confirmation and verification.
3. [x] Preserve config and Session state for cancellation/failure.

## Task 4: Review

Status: pending

1. [ ] Update README and review `.gitignore`.
2. [ ] Run Ruff, Pyright, pytest, coverage, build, and Python 3.9 checks.
3. [ ] Validate Session JSON and preserve the active product Session.
