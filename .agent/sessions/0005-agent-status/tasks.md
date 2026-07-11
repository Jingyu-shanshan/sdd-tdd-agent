# Tasks

## Task 1: Load a complete status snapshot

Status: complete

1. [x] Add one pytest test with project metadata and an active session state.
2. [x] Implement the smallest typed reader for the generated metadata subset.
3. [x] Make the suite GREEN.

## Task 2: Deterministic CLI output

Status: complete

1. [x] Add one failing pytest test for exact `status` output and exit code.
2. [x] Implement rendering and CLI dispatch.
3. [x] Make the suite GREEN.

## Task 3: Initialized project without a session

Status: complete

1. [x] Add one acceptance test for missing optional classification and session.
2. [x] Confirm the existing implementation already supplies the behavior.

## Task 4: Session identifier validation

Status: complete

1. [x] Add one failing security test for path traversal.
2. [x] Reject unsafe session identifiers before filesystem access.
3. [x] Make the suite GREEN.
