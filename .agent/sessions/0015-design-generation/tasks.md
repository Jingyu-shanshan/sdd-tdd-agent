# Tasks

## Task 1: Typed design context

Status: in progress

1. [ ] Add failing request-loading and Prompt-version tests.
2. [ ] Implement immutable request/proposal models and generator Protocol.

## Task 2: Rendering and workflow

Status: pending

1. [ ] Add failing deterministic rendering and transition tests.
2. [ ] Implement proposal validation, artifact rendering, and atomic writes.

## Task 3: Failure safety

Status: pending

1. [ ] Cover wrong state, missing approval, mismatched Session, malformed state,
   and invalid generator output.
2. [ ] Verify all failures occur before mutation.

## Task 4: Review

Status: pending

1. [ ] Update architecture/roadmap documentation and review `.gitignore`.
2. [ ] Run Ruff, Pyright, pytest, coverage, build, and compatibility checks.
3. [ ] Validate Session JSON and preserve active product Session state.
