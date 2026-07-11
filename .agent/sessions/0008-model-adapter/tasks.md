# Tasks

## Task 1: Successful typed adapter exchange

Status: complete

1. [x] Add one test using a fake typed runner.
2. [x] Verify exact command, timeout, JSON request, and typed result.
3. [x] Implement immutable configuration/result, Protocol, and adapter happy path.

## Task 2: Failure and schema handling

Status: complete

1. [x] Add tests for non-zero exit, invalid JSON, key mismatch, and field types.
2. [x] Return safe dedicated errors without process/request content.

## Task 3: Production subprocess runner

Status: complete

1. [x] Add an integration test using the current Python executable as a fixture
   process.
2. [x] Implement `subprocess.run(..., shell=False)` and timeout translation.

## Task 4: Review

Status: complete

- [x] Confirm no new dependency or `.gitignore` rule is required.
- [x] Run all quality and Python 3.9 checks.
