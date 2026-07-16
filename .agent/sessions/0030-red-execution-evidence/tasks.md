# Tasks

## Task 1: Generated-source identity

- [x] Record exact source ID/path/digest after atomic test write.
- [x] Validate digest before and after execution.
- [x] Clear stale evidence when starting a new cycle.

## Task 2: Shell-free RED execution

- [x] Add typed injected runner with timeout/start failure translation.
- [x] Detect one-test command and execute it from the project root.
- [x] Reject pass, signal, no-test, bad-option, and unattributed failures.

## Task 3: Sanitized evidence and state

- [x] Strip control/ANSI data, paths, and common credentials.
- [x] Bound stdout/stderr and atomically record RED evidence.
- [x] Preserve Session state for all invalid execution outcomes.

## Task 4: Continue orchestration and verification

- [x] Add strict timeout config and two-stage `agent continue` dispatch.
- [x] Run targeted RED/GREEN and all quality gates.
- [x] Check `.gitignore`, Session JSON, and active user Session preservation.
- [x] Update architecture, roadmap, and README.
