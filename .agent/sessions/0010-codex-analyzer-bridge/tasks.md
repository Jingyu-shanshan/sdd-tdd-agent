# Tasks

## Task 1: Codex adapter

Status: complete

1. [x] Add a failing adapter exchange test.
2. [x] Implement strict schema and shell-free Codex command construction.
3. [x] Add failure-path coverage.

## Task 2: Configuration and composition

Status: complete

1. [x] Add protocol parser tests.
2. [x] Select the adapter explicitly during `agent analyze` composition.
3. [x] Configure and document the repository bridge.

## Task 3: Review

Status: complete

1. [x] Review `.gitignore` and tracked/generated artifacts.
2. [x] Run Ruff, Pyright, pytest, coverage, build, and Python 3.9 checks.
3. [x] Validate Session JSON and preserve the active real Session.

## Task 4: Terminal PATH compatibility

Status: complete

1. [x] Reproduce the configured command startup failure as a PATH difference.
2. [x] Add a failing test for a typed, injectable Codex command resolver.
3. [x] Fall back to the verified macOS ChatGPT executable only for `codex`.
4. [x] Verify startup with the ChatGPT path removed from PATH.
