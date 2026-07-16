# Tasks

## Task 1: Recoverable cycle preparation

- [x] Resume one existing `WRITE_TEST` cycle without mutation.
- [x] Start the next eligible cycle after no progress or GREEN.
- [x] Reject continuation from RED or IMPLEMENT.

## Task 2: Safe source collection and atomic write

- [x] Collect bounded deterministic source snapshots with exclusions.
- [x] Detect target concurrency and reject symlink/unsafe destinations.
- [x] Write only the planned file through an exclusive atomic temporary.
- [x] Update `.gitignore` for atomic-write remnants.

## Task 3: Active command and CLI

- [x] Compose JSON and isolated Codex generation for the active Session.
- [x] Add exact `agent continue` dispatch, output, and safe failures.
- [x] Keep successful state in `WRITE_TEST` for RED execution.

## Task 4: Verification and documentation

- [x] Run targeted RED and GREEN tests.
- [x] Run all repository quality gates and build verification.
- [x] Validate Session JSON and preserve the active user Session.
- [x] Update architecture, roadmap, and README.
