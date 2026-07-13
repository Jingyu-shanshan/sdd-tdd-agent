# Tasks

## Task 1: Typed design context

Status: complete

1. [x] Add failing request-loading and Prompt-version tests.
2. [x] Implement immutable request/proposal models and generator Protocol.

## Task 2: Rendering and workflow

Status: complete

1. [x] Add failing deterministic rendering and transition tests.
2. [x] Implement proposal validation, artifact rendering, and atomic writes.

## Task 3: Failure safety

Status: complete

1. [x] Cover wrong state, missing approval, mismatched Session, malformed state,
   and invalid generator output.
2. [x] Verify all failures occur before mutation.

## Task 4: Review

Status: complete

1. [x] Update architecture/roadmap documentation and review `.gitignore`.
2. [x] Run Ruff, Pyright, pytest, coverage, build, and compatibility checks.
3. [x] Validate Session JSON and preserve active product Session state.
