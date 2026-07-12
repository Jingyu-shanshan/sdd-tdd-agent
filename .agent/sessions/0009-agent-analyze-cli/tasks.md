# Tasks

## Task 1: Analyzer configuration loader

Status: complete

1. [x] Add one test for valid command list, explicit timeout, and unrelated keys.
2. [x] Implement strict subset parsing into `CommandAnalyzerConfig`.
3. [x] Make the suite GREEN.

## Task 2: Active analysis composition

Status: complete

1. [x] Add one test with active Session and injected fake runner.
2. [x] Compose status, adapter, and requirement workflow.
3. [x] Verify Session reaches REQUIREMENT_REVIEW.

## Task 3: CLI and configuration failures

Status: complete

1. [x] Add exact CLI output/exit test.
2. [x] Add missing/malformed/duplicate configuration and no-session cases.
3. [x] Ensure failures occur before runner invocation or Session mutation.
4. [x] Reject whitespace-only and NUL-byte command arguments.

## Task 4: Review

Status: complete

- [x] Verify no `.gitignore` update or dependency is needed.
- [x] Run quality, package, Python 3.9, Session JSON, and active Session checks.
