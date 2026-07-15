# Tasks

## Task 1: Typed request and plan model

Status: complete

1. [x] Add failing request-loading and Prompt-version tests.
2. [x] Add immutable request/case/plan/run models and generator Protocol.
3. [x] Add deterministic Markdown rendering tests.

## Task 2: Incremental plan validation

Status: complete

1. [x] Cover IDs, task coverage, phase ordering, and preceding dependencies.
2. [x] Cover required content and safe relative target paths.
3. [x] Prove invalid output leaves plan/state unchanged.

## Task 3: Workflow transition and review

Status: complete

1. [x] Require exact state plus all three human approval records.
2. [x] Implement atomic plan/state writes and enter IMPLEMENTATION.
3. [x] Update docs, review `.gitignore`, and run all quality/package checks.
