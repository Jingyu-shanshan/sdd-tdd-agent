# Tasks

## Task 1: Create session artifacts

Status: complete

1. [x] Add one pytest test for all required files, exact requirement, and state.
2. [x] Implement validated exclusive session creation with pending templates.
3. [x] Make the suite GREEN.

## Task 2: Activate the new session

Status: complete

1. [x] Add one failing test for replacing and appending `current_session` while
   preserving other metadata.
2. [x] Implement atomic project-metadata update and make the suite GREEN.

## Task 3: CLI command and validation

Status: complete

1. [x] Add one failing test for `agent feature` output and created Session.
2. [x] Implement CLI dispatch and make the suite GREEN.
3. [x] Add one failing test for a missing/blank request.
4. [x] Reject invalid input before filesystem mutation.
5. [x] Verify unsafe explicit IDs are rejected and CLI output reports the ID.

## Task 4: Ignore policy review

Status: complete

- [x] Ignore Ruff, coverage, virtualenv, build, and package artifacts.
- [x] Ignore `.agent/cache`, `.agent/logs`, and `.agent/metrics` runtime data.
- [x] Keep `.agent/sessions`, memories, architecture, and conventions tracked.
