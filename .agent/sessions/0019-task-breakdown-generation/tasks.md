# Tasks

## Task 1: Typed request and task model

Status: complete

1. [x] Add failing request-loading and Prompt-version tests.
2. [x] Implement immutable request/task/breakdown/run models and Protocol.

## Task 2: Validation and rendering

Status: complete

1. [x] Add deterministic Markdown rendering tests.
2. [x] Add unique ID, ordered dependency, required field, and tuple validation.
3. [x] Prove invalid output leaves Session files unchanged.

## Task 3: Workflow transition

Status: complete

1. [x] Cover state, Session identity, and both approval records.
2. [x] Implement atomic tasks/state writes and enter TASK_REVIEW.

## Task 4: Review

Status: complete

1. [x] Update architecture/roadmap/README and review `.gitignore`.
2. [x] Run Ruff, Pyright, pytest, coverage, build, and compatibility checks.
3. [x] Validate Session JSON and preserve active product Session state.
